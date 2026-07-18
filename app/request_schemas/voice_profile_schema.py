from datetime import datetime
from pydantic import BaseModel


class VoiceCreate(BaseModel):
    name: str
    language: str = "en"
    description: str | None = None


class VoiceProfile(BaseModel):
    id: str
    name: str
    language: str
    description: str | None = None
    sample_path: str
    profile_path: str
    created_at: datetime


class VoiceTranscriptionResponse(BaseModel):
    voice_id: str
    text: str
