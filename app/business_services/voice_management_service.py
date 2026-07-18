import shutil
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4
import os

from fastapi import UploadFile

from app.application_core.application_settings import settings
from app.application_core.metadata_storage import ensure_runtime_dirs, read_collection, write_collection
from app.request_schemas.voice_profile_schema import VoiceCreate, VoiceProfile
from app.shared_utils.filename_sanitizer import safe_filename


class VoiceManagementService:
    def __init__(self) -> None:
        self.upload_dir = Path(settings.upload_dir)
        self.voices_dir = Path(settings.voices_dir)
        self.output_dir = Path(settings.output_dir)
        self.temp_dir = Path(settings.temp_dir)

    def ensure_storage_dirs(self) -> None:
        ensure_runtime_dirs()

    def list_voices(self) -> list[VoiceProfile]:
        valid_voices: list[VoiceProfile] = []
        stale_rows_found = False
        for row in read_collection("voices"):
            voice = VoiceProfile(**row)
            if Path(voice.sample_path).exists():
                valid_voices.append(voice)
                continue
            stale_rows_found = True

        if stale_rows_found:
            write_collection("voices", [voice.model_dump(mode="json") for voice in valid_voices])

        return valid_voices

    def get_voice(self, voice_id: str) -> VoiceProfile | None:
        for voice in self.list_voices():
            if voice.id == voice_id:
                return voice
        return None

    def transcribe_voice_sample(self, voice_id: str) -> str:
        voice = self.get_voice(voice_id)
        if voice is None:
            raise ValueError(f"Voice not found: {voice_id}")

        sample_path = Path(voice.sample_path)
        if not sample_path.exists():
            raise ValueError(f"Voice sample not found: {sample_path}")

        try:
            self._configure_audio_dependencies()
            from f5_tts.infer.utils_infer import transcribe
        except ImportError as exc:
            raise RuntimeError("F5-TTS transcription dependencies are not installed.") from exc

        try:
            text = transcribe(str(sample_path)).strip()
        except Exception as exc:
            raise RuntimeError(f"Could not transcribe uploaded voice sample: {exc}") from exc

        if not text:
            raise RuntimeError("No speech text was detected in the uploaded voice sample.")

        updated_voice = voice.model_copy(update={"description": text})
        Path(updated_voice.profile_path).write_text(updated_voice.model_dump_json(indent=2), encoding="utf-8")

        voices = read_collection("voices")
        updated_voices = [
            updated_voice.model_dump(mode="json") if row["id"] == voice_id else row
            for row in voices
        ]
        write_collection("voices", updated_voices)
        return text

    def _configure_audio_dependencies(self) -> None:
        ffmpeg_path = self._normalize_configured_path(settings.ffmpeg_binary_path)
        ffprobe_path = self._normalize_configured_path(settings.ffprobe_binary_path)

        if ffmpeg_path:
            if not Path(ffmpeg_path).exists():
                raise RuntimeError(f"FFMPEG_BINARY_PATH does not exist: {ffmpeg_path}")
            self._add_executable_directory_to_path(ffmpeg_path)

        if ffprobe_path:
            if not Path(ffprobe_path).exists():
                raise RuntimeError(f"FFPROBE_BINARY_PATH does not exist: {ffprobe_path}")
            self._add_executable_directory_to_path(ffprobe_path)

        try:
            from pydub import AudioSegment
        except ImportError:
            return

        if ffmpeg_path:
            AudioSegment.converter = ffmpeg_path
            AudioSegment.ffmpeg = ffmpeg_path
        if ffprobe_path:
            AudioSegment.ffprobe = ffprobe_path

    def _normalize_configured_path(self, configured_path: str | None) -> str | None:
        if not configured_path:
            return None
        return configured_path.strip().strip('"').strip("'").replace("/", os.sep)

    def _add_executable_directory_to_path(self, executable_path: str) -> None:
        directory = str(Path(executable_path).parent)
        os.environ["PATH"] = f"{directory}{os.pathsep}{os.environ.get('PATH', '')}"

    def register_voice(self, payload: VoiceCreate, sample: UploadFile) -> VoiceProfile:
        self.ensure_storage_dirs()
        voice_id = uuid4().hex
        voice_dir = self.voices_dir / voice_id
        voice_dir.mkdir(parents=True, exist_ok=True)

        sample_name = safe_filename(sample.filename or "sample.wav")
        sample_path = voice_dir / sample_name
        with sample_path.open("wb") as handle:
            shutil.copyfileobj(sample.file, handle)

        profile_path = voice_dir / "profile.json"
        voice = VoiceProfile(
            id=voice_id,
            name=payload.name,
            language=payload.language,
            description=payload.description,
            sample_path=str(sample_path),
            profile_path=str(profile_path),
            created_at=datetime.now(UTC),
        )
        profile_path.write_text(voice.model_dump_json(indent=2), encoding="utf-8")

        voices = read_collection("voices")
        voices.append(voice.model_dump(mode="json"))
        write_collection("voices", voices)
        return voice

    def delete_voice(self, voice_id: str) -> bool:
        voices = read_collection("voices")
        remaining = [voice for voice in voices if voice["id"] != voice_id]
        if len(remaining) == len(voices):
            return False
        write_collection("voices", remaining)
        voice_dir = self.voices_dir / voice_id
        if voice_dir.exists():
            shutil.rmtree(voice_dir)
        return True
