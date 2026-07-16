from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from app.application_core.application_settings import settings
from app.application_core.metadata_storage import read_collection, write_collection
from app.business_services.voice_management_service import VoiceManagementService
from app.request_schemas.text_to_speech_schema import TextToSpeechGenerateRequest, TextToSpeechJob
from app.voice_engines.voice_engine_base import VoiceOptions
from app.voice_engines.voice_engine_registry import get_engine


class TextToSpeechGenerationService:
    def __init__(self) -> None:
        self.voice_service = VoiceManagementService()

    def list_jobs(self) -> list[TextToSpeechJob]:
        return [TextToSpeechJob(**row) for row in read_collection("jobs")]

    def get_job(self, job_id: str) -> TextToSpeechJob | None:
        for job in self.list_jobs():
            if job.id == job_id:
                return job
        return None

    def generate(self, payload: TextToSpeechGenerateRequest) -> TextToSpeechJob:
        voice = self.voice_service.get_voice(payload.voice_id)
        if voice is None:
            raise ValueError(f"Voice not found: {payload.voice_id}")

        engine = get_engine(payload.engine or settings.default_voice_engine)
        job = TextToSpeechJob(
            id=uuid4().hex,
            status="running",
            progress=25,
            voice_id=payload.voice_id,
            engine=engine.name,
            output_path=None,
            created_at=datetime.now(UTC),
        )
        self._save_job(job)

        output_path = engine.clone(
            payload.voice_id,
            payload.text,
            VoiceOptions(
                emotion=payload.emotion,
                speed=payload.speed,
                output_format=payload.output_format,
            ),
        )
        job.status = "completed"
        job.progress = 100
        job.output_path = output_path
        job.completed_at = datetime.now(UTC)
        self._save_job(job)
        return job

    def output_file(self, job_id: str) -> Path | None:
        job = self.get_job(job_id)
        if job is None or job.output_path is None:
            return None
        path = Path(job.output_path)
        return path if path.exists() else None

    def _save_job(self, job: TextToSpeechJob) -> None:
        jobs = read_collection("jobs")
        rows = [row for row in jobs if row["id"] != job.id]
        rows.append(job.model_dump(mode="json"))
        write_collection("jobs", rows)
