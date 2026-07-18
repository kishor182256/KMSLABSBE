from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.business_services.voice_management_service import VoiceManagementService
from app.request_schemas.voice_profile_schema import VoiceCreate, VoiceProfile, VoiceTranscriptionResponse

router = APIRouter(prefix="/voices", tags=["voices"])
service = VoiceManagementService()


@router.post("/register", response_model=VoiceProfile, status_code=201)
def register_voice(
    name: str = Form(...),
    language: str = Form("en"),
    description: str | None = Form(None),
    sample: UploadFile = File(...),
) -> VoiceProfile:
    return service.register_voice(VoiceCreate(name=name, language=language, description=description), sample)


@router.get("", response_model=list[VoiceProfile])
def list_voices() -> list[VoiceProfile]:
    return service.list_voices()


@router.get("/{voice_id}", response_model=VoiceProfile)
def get_voice(voice_id: str) -> VoiceProfile:
    voice = service.get_voice(voice_id)
    if voice is None:
        raise HTTPException(status_code=404, detail="Voice not found")
    return voice


@router.post("/{voice_id}/transcribe", response_model=VoiceTranscriptionResponse)
def transcribe_voice(voice_id: str) -> VoiceTranscriptionResponse:
    try:
        text = service.transcribe_voice_sample(voice_id)
    except ValueError as exc:
        message = str(exc)
        status_code = 404 if "not found" in message.lower() else 503
        raise HTTPException(status_code=status_code, detail=message) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return VoiceTranscriptionResponse(voice_id=voice_id, text=text)


@router.delete("/{voice_id}", status_code=204)
def delete_voice(voice_id: str) -> None:
    if not service.delete_voice(voice_id):
        raise HTTPException(status_code=404, detail="Voice not found")
