from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api_routes.audio_processing_routes import router as audio_processing_router
from app.api_routes.health_check_routes import router as health_router
from app.api_routes.project_management_routes import router as project_router
from app.api_routes.text_to_speech_routes import router as text_to_speech_router
from app.api_routes.voice_management_routes import router as voice_router
from app.application_core.application_settings import settings


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.project_name,
        version=settings.version,
        description="Backend API for AI Voice Studio.",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_router, prefix=settings.api_prefix)
    app.include_router(voice_router, prefix=settings.api_prefix)
    app.include_router(text_to_speech_router, prefix=settings.api_prefix)
    app.include_router(audio_processing_router, prefix=settings.api_prefix)
    app.include_router(project_router, prefix=settings.api_prefix)
    return app


app = create_app()
