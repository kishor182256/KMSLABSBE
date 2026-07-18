from pathlib import Path
from uuid import uuid4
from datetime import UTC, datetime
import inspect
import os
import re
import shutil
import logging

from app.application_core.application_settings import settings
from app.application_core.metadata_storage import ensure_runtime_dirs
from app.audio_export.audio_file_converter import encode_wav_file_to_mp3
from app.business_services.voice_management_service import VoiceManagementService
from app.voice_engines.voice_engine_base import VoiceEngine, VoiceOptions


logger = logging.getLogger(__name__)


class F5TTSEngine(VoiceEngine):
    name = "f5_tts"
    _model = None
    _dll_directory_handles = []

    def __init__(self) -> None:
        self.voice_service = VoiceManagementService()

    def clone(self, voice_id: str, text: str, options: VoiceOptions) -> str:
        ensure_runtime_dirs()
        voice = self.voice_service.get_voice(voice_id)
        if voice is None:
            raise ValueError(f"Voice not found: {voice_id}")

        sample_path = Path(voice.sample_path)
        if not sample_path.exists():
            raise ValueError(f"Voice sample not found: {sample_path}")

        output_format = options.output_format.lstrip(".").lower() or "wav"
        if output_format not in {"wav", "mp3"}:
            raise ValueError(f"Unsupported output format for F5-TTS: {output_format}")

        reference_text, reference_text_source = self._resolve_reference_text(voice.description)
        if not reference_text and not settings.f5_tts_allow_auto_transcription:
            raise ValueError(
                "F5-TTS needs reference text or auto transcription. Set "
                "F5_TTS_DEFAULT_REFERENCE_TEXT, provide voice description text, or set "
                "F5_TTS_ALLOW_AUTO_TRANSCRIPTION=true to let F5-TTS use Whisper."
            )
        logger.info(
            "F5-TTS using uploaded voice sample voice_id=%s sample_path=%s reference_text_source=%s",
            voice_id,
            sample_path,
            reference_text_source,
        )

        wav_path = Path(settings.output_dir) / f"{voice_id}_{uuid4().hex}.wav"
        model = self._load_model()
        chunks = self._split_text_for_inference(text)
        nfe_step = self._nfe_step_for_quality(options.quality_mode)
        pause_ms = int(max(0.0, min(options.pause_seconds, 5.0)) * 1000)

        if len(chunks) == 1:
            started_at = datetime.now(UTC)
            logger.info("Generating segment 1 of 1 started at %s", started_at.isoformat())
            self._infer_chunk(model, sample_path, reference_text, chunks[0], wav_path, options.speed, nfe_step)
            finished_at = datetime.now(UTC)
            logger.info(
                "Generating segment 1 of 1 finished at %s duration_seconds=%.2f",
                finished_at.isoformat(),
                (finished_at - started_at).total_seconds(),
            )
        else:
            self._infer_and_stitch_chunks(
                model=model,
                sample_path=sample_path,
                reference_text=reference_text,
                chunks=chunks,
                output_wav_path=wav_path,
                speed=options.speed,
                nfe_step=nfe_step,
                pause_ms=pause_ms,
            )

        if output_format == "wav":
            return str(wav_path)

        mp3_path = wav_path.with_suffix(".mp3")
        encode_wav_file_to_mp3(wav_path, mp3_path)
        wav_path.unlink(missing_ok=True)
        return str(mp3_path)

    def _infer_chunk(
        self,
        model,
        sample_path: Path,
        reference_text: str,
        text: str,
        output_wav_path: Path,
        speed: float,
        nfe_step: int,
    ) -> None:
        model.infer(
            ref_file=str(sample_path),
            ref_text=reference_text,
            gen_text=text,
            speed=max(0.5, min(speed, 2.0)),
            nfe_step=nfe_step,
            file_wave=str(output_wav_path),
            remove_silence=True,
            show_info=lambda *_args, **_kwargs: None,
        )

    def _infer_and_stitch_chunks(
        self,
        model,
        sample_path: Path,
        reference_text: str,
        chunks: list[str],
        output_wav_path: Path,
        speed: float,
        nfe_step: int,
        pause_ms: int,
    ) -> None:
        from pydub import AudioSegment

        segment_paths: list[Path] = []
        try:
            for index, chunk in enumerate(chunks):
                chunk_path = Path(settings.temp_dir) / f"f5_chunk_{uuid4().hex}_{index}.wav"
                started_at = datetime.now(UTC)
                logger.info(
                    "Generating segment %s of %s started at %s characters=%s",
                    index + 1,
                    len(chunks),
                    started_at.isoformat(),
                    len(chunk),
                )
                self._infer_chunk(model, sample_path, reference_text, chunk, chunk_path, speed, nfe_step)
                finished_at = datetime.now(UTC)
                logger.info(
                    "Generating segment %s of %s finished at %s duration_seconds=%.2f",
                    index + 1,
                    len(chunks),
                    finished_at.isoformat(),
                    (finished_at - started_at).total_seconds(),
                )
                segment_paths.append(chunk_path)

            stitch_started_at = datetime.now(UTC)
            logger.info("Stitching %s generated segments started at %s pause_ms=%s", len(chunks), stitch_started_at.isoformat(), pause_ms)
            combined = AudioSegment.empty()
            pause = AudioSegment.silent(duration=pause_ms)
            for index, chunk_path in enumerate(segment_paths):
                if index > 0 and pause_ms > 0:
                    combined += pause
                combined += AudioSegment.from_wav(chunk_path)
            combined.export(output_wav_path, format="wav")
            stitch_finished_at = datetime.now(UTC)
            logger.info(
                "Stitching %s generated segments finished at %s duration_seconds=%.2f",
                len(chunks),
                stitch_finished_at.isoformat(),
                (stitch_finished_at - stitch_started_at).total_seconds(),
            )
        finally:
            for chunk_path in segment_paths:
                chunk_path.unlink(missing_ok=True)

    def _split_text_for_inference(self, text: str) -> list[str]:
        max_characters = max(120, settings.f5_tts_max_chunk_characters)
        paragraphs = [paragraph.strip() for paragraph in re.split(r"\n\s*\n+", text) if paragraph.strip()]
        chunks: list[str] = []

        for paragraph in paragraphs:
            if len(paragraph) <= max_characters:
                chunks.append(paragraph)
                continue

            current = ""
            sentences = [sentence.strip() for sentence in re.split(r"(?<=[.!?])\s+", paragraph) if sentence.strip()]
            for sentence in sentences:
                candidate = f"{current} {sentence}".strip()
                if current and len(candidate) > max_characters:
                    chunks.append(current)
                    current = sentence
                else:
                    current = candidate

                while len(current) > max_characters:
                    chunks.append(current[:max_characters].rsplit(" ", 1)[0].strip())
                    current = current[len(chunks[-1]):].strip()

            if current:
                chunks.append(current)

        return chunks or [text.strip()]

    def _nfe_step_for_quality(self, quality_mode: str) -> int:
        quality_steps = {
            "fast": 16,
            "standard": 16,
            "balanced": 24,
            "high": 32,
            "lossless": 32,
        }
        return quality_steps.get(quality_mode.lower(), 24)

    def _resolve_reference_text(self, voice_description: str | None) -> tuple[str, str]:
        if voice_description and voice_description.strip():
            return voice_description.strip(), "voice_description"
        if settings.f5_tts_allow_auto_transcription:
            return "", "auto_transcription_from_uploaded_sample"
        return settings.f5_tts_default_reference_text.strip(), "default_fallback_text"

    def _load_model(self):
        if self._model is not None:
            return self._model

        ffmpeg_path, ffprobe_path = self._resolve_ffmpeg_paths()
        self._configure_windows_dll_search_paths([Path(ffmpeg_path).parent, Path(ffprobe_path).parent])

        try:
            import imageio_ffmpeg
            import pandas  # noqa: F401
            import pyarrow  # noqa: F401
            import sklearn  # noqa: F401
            from pydub import AudioSegment
            from f5_tts.api import F5TTS
        except ImportError as exc:
            raise RuntimeError("F5-TTS is not installed. Install backend requirements, then restart the API.") from exc

        AudioSegment.converter = ffmpeg_path
        AudioSegment.ffmpeg = ffmpeg_path
        AudioSegment.ffprobe = ffprobe_path

        self._verify_torchcodec_runtime()

        try:
            self._model = F5TTS(**self._f5tts_constructor_kwargs(F5TTS))
        except RuntimeError as exc:
            raise RuntimeError(self._friendly_runtime_error(exc)) from exc
        return self._model

    def _f5tts_constructor_kwargs(self, model_class) -> dict:
        kwargs = {
            "device": self._resolve_device(),
            "hf_cache_dir": settings.f5_tts_cache_dir,
        }
        parameters = inspect.signature(model_class).parameters
        if "model" in parameters:
            kwargs["model"] = settings.f5_tts_model_name
        else:
            kwargs["model_type"] = self._f5_model_type(settings.f5_tts_model_name)
        return kwargs

    def _f5_model_type(self, model_name: str) -> str:
        normalized = model_name.lower().replace("_", "-")
        if normalized.startswith("e2"):
            return "E2-TTS"
        return "F5-TTS"

    def _resolve_ffmpeg_paths(self) -> tuple[str, str]:
        ffmpeg_path = self._resolve_executable_path(settings.ffmpeg_binary_path)
        ffprobe_path = self._resolve_executable_path(settings.ffprobe_binary_path)

        if not ffmpeg_path:
            try:
                import imageio_ffmpeg
            except ImportError as exc:
                raise RuntimeError("imageio-ffmpeg is not installed and FFMPEG_BINARY_PATH is not set.") from exc
            ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()

        if not ffprobe_path:
            ffprobe_path = shutil.which("ffprobe")

        if not Path(ffmpeg_path).exists():
            raise RuntimeError(f"FFMPEG_BINARY_PATH does not exist: {ffmpeg_path}")
        if not ffprobe_path:
            raise RuntimeError(
                "F5-TTS requires ffprobe from FFmpeg to read reference audio. "
                "Install FFmpeg locally, make ffprobe available on PATH, or set "
                "FFPROBE_BINARY_PATH in backend .env. No model generation was run."
            )
        if not Path(ffprobe_path).exists():
            raise RuntimeError(f"FFPROBE_BINARY_PATH does not exist: {ffprobe_path}")

        return ffmpeg_path, ffprobe_path

    def _configure_windows_dll_search_paths(self, directories: list[Path]) -> None:
        for directory in dict.fromkeys(directories):
            directory_text = str(directory)
            if not directory.exists():
                raise RuntimeError(f"FFmpeg DLL directory does not exist: {directory_text}")
            os.environ["PATH"] = f"{directory_text}{os.pathsep}{os.environ.get('PATH', '')}"
            if os.name == "nt" and hasattr(os, "add_dll_directory"):
                handle = os.add_dll_directory(directory_text)
                self._dll_directory_handles.append(handle)

    def _resolve_executable_path(self, configured_path: str | None) -> str | None:
        if not configured_path:
            return None
        return configured_path.strip().strip('"').strip("'").replace("/", os.sep)

    def _verify_torchcodec_runtime(self) -> None:
        try:
            import torchcodec  # noqa: F401
        except RuntimeError as exc:
            raise RuntimeError(self._friendly_runtime_error(exc)) from exc

    def _friendly_runtime_error(self, exc: RuntimeError) -> str:
        message = str(exc)
        if "Could not load libtorchcodec" in message:
            return (
                "F5-TTS cannot start because TorchCodec cannot load its native audio DLLs. "
                "On Windows, install a full-shared FFmpeg build and set FFMPEG_BINARY_PATH "
                "and FFPROBE_BINARY_PATH in backend .env. Also make sure torch, torchaudio, "
                "and torchcodec versions are compatible. Current generation was stopped "
                "before model inference."
            )
        return message

    def _resolve_device(self) -> str | None:
        if settings.f5_tts_device != "auto":
            return settings.f5_tts_device

        try:
            import torch
        except ImportError:
            return None

        return "cuda" if torch.cuda.is_available() else "cpu"
