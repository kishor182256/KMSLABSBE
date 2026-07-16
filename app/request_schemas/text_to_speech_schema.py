from datetime import datetime
from pydantic import BaseModel, Field


class TextToSpeechGenerateRequest(BaseModel):
    voice_id: str
    text: str = Field(min_length=1)
    engine: str | None = None
    emotion: str = "neutral"
    speed: float = 1.0
    output_format: str = "wav"


class TextToSpeechJob(BaseModel):
    id: str
    status: str
    progress: int
    voice_id: str
    engine: str
    output_path: str | None = None
    created_at: datetime
    completed_at: datetime | None = None


TTSGenerateRequest = TextToSpeechGenerateRequest
TTSJob = TextToSpeechJob
