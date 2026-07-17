from pathlib import Path
from uuid import uuid4

from app.application_core.application_settings import settings
from app.application_core.metadata_storage import ensure_runtime_dirs
from app.audio_export.audio_file_converter import encode_wav_file_to_mp3
from app.business_services.voice_management_service import VoiceManagementService
from app.voice_engines.voice_engine_base import VoiceEngine, VoiceOptions


class XTTSEngine(VoiceEngine):
    name = "xtts_v2"
    _model = None

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
            raise ValueError(f"Unsupported output format for XTTS-v2: {output_format}")

        wav_path = Path(settings.output_dir) / f"{voice_id}_{uuid4().hex}.wav"
        model = self._load_model()
        generation_kwargs = {
            "text": text,
            "speaker_wav": str(sample_path),
            "language": voice.language or "en",
            "file_path": str(wav_path),
            "split_sentences": True,
        }

        try:
            model.tts_to_file(**generation_kwargs, speed=max(0.5, min(options.speed, 2.0)))
        except TypeError:
            model.tts_to_file(**generation_kwargs)

        if output_format == "wav":
            return str(wav_path)

        mp3_path = wav_path.with_suffix(".mp3")
        encode_wav_file_to_mp3(wav_path, mp3_path)
        wav_path.unlink(missing_ok=True)
        return str(mp3_path)

    def _load_model(self):
        if self._model is not None:
            return self._model

        try:
            from TTS.api import TTS
        except ImportError as exc:
            raise RuntimeError(
                "XTTS-v2 requires the Coqui TTS package. Install backend requirements, then restart the API."
            ) from exc

        model = TTS(settings.xtts_model_name)
        device = self._resolve_device()
        if device:
            model.to(device)
        self._model = model
        return self._model

    def _resolve_device(self) -> str | None:
        if settings.xtts_device != "auto":
            return settings.xtts_device

        try:
            import torch
        except ImportError:
            return None

        return "cuda" if torch.cuda.is_available() else "cpu"
