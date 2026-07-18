from datetime import datetime
from pydantic import BaseModel, Field


class TextToSpeechGenerateRequest(BaseModel):
    voice_id: str
    text: str = Field(min_length=1)
    engine: str | None = None
    emotion: str = "neutral"
    style_label: str | None = None
    style_reference: str | None = None
    speed: float = 1.0
    output_format: str = "wav"
    pause_seconds: float = 0.8
    quality_mode: str = "balanced"
    language: str | None = None


class TextToSpeechJob(BaseModel):
    id: str
    status: str
    progress: int
    voice_id: str
    engine: str
    model_name: str | None = None
    language: str | None = None
    request_key: str | None = None
    style_label: str | None = None
    style_reference: str | None = None
    output_path: str | None = None
    error_message: str | None = None
    created_at: datetime
    completed_at: datetime | None = None


TTSGenerateRequest = TextToSpeechGenerateRequest
TTSJob = TextToSpeechJob
