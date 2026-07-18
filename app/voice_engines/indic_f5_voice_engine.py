import os
import re
import sys
from importlib.resources import files
from pathlib import Path
from uuid import uuid4

import numpy as np

from app.application_core.application_settings import settings
from app.application_core.metadata_storage import ensure_runtime_dirs
from app.audio_export.audio_file_converter import encode_wav_file_to_mp3
from app.business_services.voice_management_service import VoiceManagementService
from app.voice_engines.voice_engine_base import VoiceEngine, VoiceOptions


GATED_MODEL_ERROR_MARKERS = (
    "gated repo",
    "401 client error",
    "unauthorized",
    "restricted",
    "authenticated",
)


class IndicF5VoiceEngine(VoiceEngine):
    name = "indic_f5"
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

        reference_text = (voice.description or "").strip()
        if not reference_text:
            reference_text = self.voice_service.transcribe_voice_sample(voice_id).strip()
            voice = self.voice_service.get_voice(voice_id) or voice
        if not reference_text:
            raise ValueError("IndicF5 could not detect transcript text from the uploaded reference voice.")

        output_format = options.output_format.lstrip(".").lower() or "wav"
        if output_format not in {"wav", "mp3"}:
            raise ValueError(f"Unsupported output format for IndicF5: {output_format}")

        style_reference = options.style_reference
        if style_reference is not None:
            reference_audio_path = Path(style_reference)
            if not reference_audio_path.exists():
                raise ValueError(f"Style reference audio not found: {style_reference}")
            ref_audio_path = str(reference_audio_path)
        else:
            ref_audio_path = str(sample_path)

        model = self._load_model()
        chunks = self._split_text_for_inference(text)
        audio = self._generate_and_stitch_audio(
            model=model,
            chunks=chunks,
            ref_audio_path=ref_audio_path,
            reference_text=reference_text,
            pause_seconds=options.pause_seconds,
        )

        try:
            import soundfile as sf
        except ImportError as exc:
            raise RuntimeError("IndicF5 needs soundfile installed to write audio.") from exc

        wav_path = Path(settings.output_dir) / f"{voice_id}_{uuid4().hex}.wav"
        sf.write(wav_path, np.array(audio, dtype=np.float32), samplerate=24000)
        if output_format == "wav":
            return str(wav_path)

        mp3_path = wav_path.with_suffix(".mp3")
        encode_wav_file_to_mp3(wav_path, mp3_path)
        wav_path.unlink(missing_ok=True)
        return str(mp3_path)

    def _generate_and_stitch_audio(
        self,
        model,
        chunks: list[str],
        ref_audio_path: str,
        reference_text: str,
        pause_seconds: float,
    ) -> np.ndarray:
        generated_segments = [
            self._normalize_audio(model(chunk, ref_audio_path=ref_audio_path, ref_text=reference_text))
            for chunk in chunks
        ]
        if len(generated_segments) == 1:
            return generated_segments[0]

        pause_samples = int(max(0.0, min(pause_seconds, 2.0)) * 24000)
        pause = np.zeros(pause_samples, dtype=np.float32)
        stitched: list[np.ndarray] = []
        for index, segment in enumerate(generated_segments):
            if index > 0 and pause_samples:
                stitched.append(pause)
            stitched.append(segment)
        return np.concatenate(stitched).astype(np.float32)

    def _normalize_audio(self, audio) -> np.ndarray:
        normalized = np.asarray(audio)
        if normalized.dtype == np.int16:
            normalized = normalized.astype(np.float32) / 32768.0
        else:
            normalized = normalized.astype(np.float32)
            peak = float(np.max(np.abs(normalized))) if normalized.size else 0.0
            if peak > 1.0:
                normalized = normalized / peak
        return np.clip(normalized, -1.0, 1.0)

    def _split_text_for_inference(self, text: str) -> list[str]:
        max_characters = max(80, settings.indic_f5_max_chunk_characters)
        sentences = [
            sentence.strip()
            for sentence in re.findall(r".+?(?:[।.!?]+|$)", text.strip(), flags=re.DOTALL)
            if sentence.strip()
        ]
        chunks: list[str] = []
        if len(sentences) > 1:
            for sentence in sentences:
                chunks.extend(self._split_long_text(sentence, max_characters))
            return chunks

        current = ""
        for sentence in sentences or [text.strip()]:
            candidate = f"{current} {sentence}".strip()
            if current and len(candidate) > max_characters:
                chunks.append(current)
                current = sentence
            else:
                current = candidate

            while len(current) > max_characters:
                split_at = current.rfind(" ", 0, max_characters)
                if split_at <= 0:
                    split_at = max_characters
                chunks.append(current[:split_at].strip())
                current = current[split_at:].strip()

        if current:
            chunks.append(current)
        return chunks or [text.strip()]

    def _split_long_text(self, text: str, max_characters: int) -> list[str]:
        chunks: list[str] = []
        current = text.strip()
        while len(current) > max_characters:
            split_at = current.rfind(" ", 0, max_characters)
            if split_at <= 0:
                split_at = max_characters
            chunks.append(current[:split_at].strip())
            current = current[split_at:].strip()
        if current:
            chunks.append(current)
        return chunks

    def _load_model(self):
        if self._model is not None:
            return self._model

        self._configure_audio_runtime()
        try:
            import f5_tts.infer.utils_infer as f5_utils
            from transformers import AutoConfig
            from transformers.dynamic_module_utils import get_class_from_dynamic_module
        except ImportError as exc:
            raise RuntimeError("IndicF5 needs transformers and f5-tts installed.") from exc

        token = settings.huggingface_token or settings.hf_token
        self._configure_huggingface_token(token)
        try:
            hub_kwargs = {
                "cache_dir": settings.indic_f5_cache_dir,
                "token": token,
            }
            config = AutoConfig.from_pretrained(
                settings.indic_f5_model_name,
                trust_remote_code=True,
                **hub_kwargs,
            )
            class_ref = config.auto_map["AutoModel"]
            model_class = get_class_from_dynamic_module(
                class_ref,
                settings.indic_f5_model_name,
                **hub_kwargs,
            )
            self._patch_remote_model_class(model_class, f5_utils)
            self._model = model_class.from_pretrained(
                settings.indic_f5_model_name,
                config=config,
                trust_remote_code=True,
                **hub_kwargs,
            )
        except OSError as exc:
            if self._is_gated_model_error(exc):
                raise RuntimeError(
                    "IndicF5 requires access to the gated Hugging Face model "
                    f"'{settings.indic_f5_model_name}'. Request access on Hugging Face, "
                    "then set HUGGINGFACE_TOKEN or HF_TOKEN in .env with a token that has access."
                ) from exc
            raise
        except RuntimeError as exc:
            if "expected device meta" in str(exc).lower():
                raise RuntimeError(
                    "IndicF5 could not start because the installed Transformers runtime tried to "
                    "initialize the custom model on the meta device. Restart the API so the "
                    "IndicF5 compatibility loader is active, or install the AI4Bharat IndicF5 "
                    "dependency set with transformers<4.50."
                ) from exc
            raise
        return self._model

    def _configure_huggingface_token(self, token: str | None) -> None:
        if not token:
            return
        os.environ.setdefault("HF_TOKEN", token)
        os.environ.setdefault("HUGGINGFACE_HUB_TOKEN", token)

    def _patch_remote_model_class(self, model_class, f5_utils) -> None:
        model_class.get_init_context = classmethod(lambda cls, *args, **kwargs: [])
        model_class.all_tied_weights_keys = {}

        remote_module = sys.modules[model_class.__module__]

        def construct_model_without_checkpoint(
            model_cls,
            model_cfg,
            mel_spec_type=f5_utils.mel_spec_type,
            vocab_file="",
            ode_method=f5_utils.ode_method,
            use_ema=True,
            device=f5_utils.device,
        ):
            if not vocab_file:
                vocab_file = str(files("f5_tts").joinpath("infer/examples/vocab.txt"))
            vocab_char_map, vocab_size = f5_utils.get_tokenizer(vocab_file, "custom")
            return f5_utils.CFM(
                transformer=model_cls(
                    **model_cfg,
                    text_num_embeds=vocab_size,
                    mel_dim=f5_utils.n_mel_channels,
                ),
                mel_spec_kwargs={
                    "n_fft": f5_utils.n_fft,
                    "hop_length": f5_utils.hop_length,
                    "win_length": f5_utils.win_length,
                    "n_mel_channels": f5_utils.n_mel_channels,
                    "target_sample_rate": f5_utils.target_sample_rate,
                    "mel_spec_type": mel_spec_type,
                },
                odeint_kwargs={"method": ode_method},
                vocab_char_map=vocab_char_map,
            ).to(device)

        remote_module.load_model = construct_model_without_checkpoint

    def _configure_audio_runtime(self) -> None:
        ffmpeg_path = self._normalize_executable_path(settings.ffmpeg_binary_path)
        ffprobe_path = self._normalize_executable_path(settings.ffprobe_binary_path)
        for executable_path in (ffmpeg_path, ffprobe_path):
            if executable_path:
                directory = Path(executable_path).parent
                os.environ["PATH"] = f"{directory}{os.pathsep}{os.environ.get('PATH', '')}"
                if os.name == "nt" and hasattr(os, "add_dll_directory") and directory.exists():
                    self._dll_directory_handles.append(os.add_dll_directory(str(directory)))

        try:
            from pydub import AudioSegment
        except ImportError:
            return

        if ffmpeg_path:
            AudioSegment.converter = ffmpeg_path
            AudioSegment.ffmpeg = ffmpeg_path
        if ffprobe_path:
            AudioSegment.ffprobe = ffprobe_path

    def _normalize_executable_path(self, configured_path: str | None) -> str | None:
        if not configured_path:
            return None
        path = configured_path.strip().strip('"').strip("'").replace("/", os.sep)
        return path if Path(path).exists() else None

    def _is_gated_model_error(self, exc: OSError) -> bool:
        message = str(exc).lower()
        return any(marker in message for marker in GATED_MODEL_ERROR_MARKERS)
