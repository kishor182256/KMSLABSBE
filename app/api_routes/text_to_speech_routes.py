from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.business_services.text_to_speech_generation_service import TextToSpeechGenerationService
from app.request_schemas.text_to_speech_schema import TextToSpeechGenerateRequest, TextToSpeechJob

router = APIRouter(prefix="/tts", tags=["tts"])
service = TextToSpeechGenerationService()


@router.post("/generate", response_model=TextToSpeechJob, status_code=202)
def generate_text_to_speech(payload: TextToSpeechGenerateRequest) -> TextToSpeechJob:
    try:
        return service.generate(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/jobs/{job_id}", response_model=TextToSpeechJob)
def get_text_to_speech_job(job_id: str) -> TextToSpeechJob:
    job = service.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/download/{job_id}")
def download_job_output(job_id: str) -> FileResponse:
    path = service.output_file(job_id)
    if path is None:
        raise HTTPException(status_code=404, detail="Output file not found")
    return FileResponse(path, filename=path.name)
