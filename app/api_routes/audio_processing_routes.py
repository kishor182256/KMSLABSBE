from fastapi import APIRouter

from app.business_services.audio_processing_service import AudioProcessingService
from app.request_schemas.audio_processing_schema import AudioProcessRequest, AudioProcessResponse

router = APIRouter(prefix="/audio", tags=["audio"])
service = AudioProcessingService()


def process_audio(payload: AudioProcessRequest, operation: str) -> AudioProcessResponse:
    output_path = service.process(payload.file_path, operation)
    return AudioProcessResponse(
        status="completed",
        input_path=payload.file_path,
        output_path=output_path,
        operation=operation,
    )


@router.post("/clean", response_model=AudioProcessResponse)
def clean_audio(payload: AudioProcessRequest) -> AudioProcessResponse:
    return process_audio(payload, "clean")


@router.post("/enhance", response_model=AudioProcessResponse)
def enhance_audio(payload: AudioProcessRequest) -> AudioProcessResponse:
    return process_audio(payload, "enhance")


@router.post("/normalize", response_model=AudioProcessResponse)
def normalize_audio(payload: AudioProcessRequest) -> AudioProcessResponse:
    return process_audio(payload, "normalize")
