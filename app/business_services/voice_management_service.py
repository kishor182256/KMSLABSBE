import shutil
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

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
        return [VoiceProfile(**row) for row in read_collection("voices")]

    def get_voice(self, voice_id: str) -> VoiceProfile | None:
        for voice in self.list_voices():
            if voice.id == voice_id:
                return voice
        return None

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
