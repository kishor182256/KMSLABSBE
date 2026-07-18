import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from app.application_core.application_settings import settings
from app.application_core.metadata_storage import read_collection, write_collection
from app.business_services.voice_management_service import VoiceManagementService
from app.request_schemas.text_to_speech_schema import TextToSpeechGenerateRequest, TextToSpeechJob
from app.voice_engines.voice_engine_base import VoiceOptions
from app.voice_engines.voice_engine_registry import get_engine


INDIC_F5_LANGUAGE_CODES = {"as", "bn", "gu", "hi", "kn", "ml", "mr", "or", "pa", "ta", "te"}
LANGUAGE_ALIASES = {
    "assamese": "as",
    "asamiya": "as",
    "bengali": "bn",
    "bangla": "bn",
    "gujarati": "gu",
    "hindi": "hi",
    "\u0939\u093f\u0902\u0926\u0940": "hi",
    "\u0939\u093f\u0928\u094d\u0926\u0940": "hi",
    "kannada": "kn",
    "malayalam": "ml",
    "marathi": "mr",
    "odia": "or",
    "oriya": "or",
    "punjabi": "pa",
    "tamil": "ta",
    "telugu": "te",
    "english": "en",
}
DEVANAGARI_RANGE = range(ord("\u0900"), ord("\u097f") + 1)
STYLE_REFERENCE_LABEL_MAP = {
    "neutral": "neutral.wav",
    "happy": "happy.wav",
    "calm": "calm.wav",
    "podcast": "podcast.wav",
    "news": "news.wav",
    "storytelling": "storytelling.wav",
    "warm": "warm.wav",
    "excited": "excited.wav",
    "serious": "serious.wav",
    "confident": "confident.wav",
}


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
            raise ValueError(
                f"Voice not found or sample file is missing: {payload.voice_id}. "
                "Re-upload the voice sample before generating."
            )

        if not Path(voice.sample_path).exists():
            raise ValueError(
                f"Voice sample file is missing: {voice.sample_path}. "
                "Re-upload the voice sample before generating."
            )

        language = self._resolve_language(payload.language, voice.language, payload.text)
        engine = get_engine(payload.engine or self._default_engine_for_language(language))
        model_name = self._model_name_for_engine(engine.name)
        style_label, style_reference = self._resolve_style_reference(payload, engine.name)
        request_key = self._request_key(payload, engine.name, model_name, language, style_label, style_reference)
        reusable_job = self._find_reusable_job(request_key)
        if reusable_job is not None:
            return reusable_job

        job = TextToSpeechJob(
            id=uuid4().hex,
            status="running",
            progress=25,
            voice_id=payload.voice_id,
            engine=engine.name,
            model_name=model_name,
            language=language,
            request_key=request_key,
            style_label=style_label or payload.style_label,
            style_reference=style_reference or payload.style_reference,
            output_path=None,
            created_at=datetime.now(UTC),
        )
        self._save_job(job)

        try:
            output_path = engine.clone(
                payload.voice_id,
                payload.text,
                VoiceOptions(
                    emotion=payload.emotion,
                    style_label=style_label or payload.style_label,
                    style_reference=style_reference or payload.style_reference,
                    speed=payload.speed,
                    output_format=payload.output_format,
                    pause_seconds=payload.pause_seconds,
                    quality_mode=payload.quality_mode,
                    language=language,
                ),
            )
        except Exception as exc:
            job.status = "failed"
            job.progress = 100
            job.error_message = str(exc)
            job.completed_at = datetime.now(UTC)
            self._save_job(job)
            raise

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

    def _find_reusable_job(self, request_key: str) -> TextToSpeechJob | None:
        for job in reversed(self.list_jobs()):
            if job.request_key != request_key:
                continue
            if job.status == "completed" and job.output_path and Path(job.output_path).exists():
                return job
            if job.status == "running":
                return job
        return None

    def _request_key(
        self,
        payload: TextToSpeechGenerateRequest,
        engine_name: str,
        model_name: str | None,
        language: str,
        style_label: str | None,
        style_reference: str | None,
    ) -> str:
        request_data = {
            "voice_id": payload.voice_id,
            "text": " ".join(payload.text.split()),
            "engine": engine_name,
            "engine_runtime": self._engine_runtime_key(engine_name),
            "model_name": model_name,
            "emotion": payload.emotion,
            "style_label": style_label or payload.style_label,
            "style_reference": style_reference or payload.style_reference,
            "speed": round(payload.speed, 3),
            "output_format": payload.output_format.lower().lstrip("."),
            "pause_seconds": round(payload.pause_seconds, 3),
            "quality_mode": payload.quality_mode,
            "language": language,
        }
        encoded = json.dumps(request_data, sort_keys=True, ensure_ascii=True).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def _resolve_style_reference(
        self,
        payload: TextToSpeechGenerateRequest,
        engine_name: str,
    ) -> tuple[str | None, str | None]:
        style_label = payload.style_label
        style_reference = payload.style_reference

        if style_reference:
            resolved = Path(style_reference)
            if not resolved.is_absolute():
                resolved = Path(settings.style_references_dir) / style_reference
            if not resolved.exists():
                raise ValueError(f"Style reference audio not found: {resolved}")
            return style_label or resolved.stem, str(resolved)

        if style_label:
            if style_label not in STYLE_REFERENCE_LABEL_MAP:
                raise ValueError(
                    f"Unsupported style_label '{style_label}'. Valid values are: {', '.join(sorted(STYLE_REFERENCE_LABEL_MAP))}"
                )
            reference_file = Path(settings.style_references_dir) / STYLE_REFERENCE_LABEL_MAP[style_label]
            if not reference_file.exists():
                raise ValueError(
                    f"Style reference file for label '{style_label}' not found: {reference_file}"
                )
            return style_label, str(reference_file)

        if payload.emotion and payload.emotion in STYLE_REFERENCE_LABEL_MAP:
            reference_file = Path(settings.style_references_dir) / STYLE_REFERENCE_LABEL_MAP[payload.emotion]
            if reference_file.exists():
                return payload.emotion, str(reference_file)

        return None, None

    def _default_engine_for_language(self, language: str) -> str:
        return "indic_f5" if language in INDIC_F5_LANGUAGE_CODES else settings.default_voice_engine

    def _resolve_language(
        self,
        requested_language: str | None,
        voice_language: str | None,
        text: str,
    ) -> str:
        for language in (requested_language, voice_language):
            normalized = self._normalize_language(language)
            if normalized:
                return normalized
        if self._contains_devanagari(text):
            return "hi"
        return "en"

    def _normalize_language(self, language: str | None) -> str | None:
        if not language:
            return None
        normalized = language.strip().lower().replace("_", "-")
        if not normalized:
            return None
        if "-" in normalized:
            normalized = normalized.split("-", 1)[0]
        return LANGUAGE_ALIASES.get(normalized, normalized)

    def _contains_devanagari(self, text: str) -> bool:
        return any(ord(character) in DEVANAGARI_RANGE for character in text)

    def _model_name_for_engine(self, engine_name: str) -> str | None:
        if engine_name == "indic_f5":
            return settings.indic_f5_model_name
        if engine_name == "f5_tts":
            return settings.f5_tts_model_name
        if engine_name == "xtts_v2":
            return settings.xtts_model_name
        return None

    def _engine_runtime_key(self, engine_name: str) -> str:
        if engine_name == "indic_f5":
            return f"official_fork_sentence_chunks_{settings.indic_f5_max_chunk_characters}"
        return "default"
