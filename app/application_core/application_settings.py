from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    project_name: str = "AI Voice Studio"
    version: str = "0.1.0"
    api_prefix: str = "/api/v1"
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    upload_dir: str = "uploaded_voice_samples"
    voices_dir: str = "voice_profiles"
    output_dir: str = "generated_audio_outputs"
    temp_dir: str = "temporary_processing_files"
    metadata_dir: str = "temporary_processing_files/metadata"
    default_voice_engine: str = "f5_tts"
    xtts_model_name: str = "tts_models/multilingual/multi-dataset/xtts_v2"
    xtts_device: str = "auto"
    f5_tts_model_name: str = "F5TTS_v1_Base"
    f5_tts_device: str = "auto"
    f5_tts_cache_dir: str | None = None
    f5_tts_allow_auto_transcription: bool = True
    f5_tts_default_reference_text: str = "This is a reference voice sample for voice cloning."
    f5_tts_max_chunk_characters: int = 420
    f5_tts_parallel_workers: int = 1
    indic_f5_model_name: str = "ai4bharat/IndicF5"
    indic_f5_device: str = "auto"
    indic_f5_cache_dir: str | None = None
    indic_f5_max_chunk_characters: int = 180
    huggingface_token: str | None = None
    hf_token: str | None = None
    ffmpeg_binary_path: str | None = None
    ffprobe_binary_path: str | None = None
    style_references_dir: str = "style_references"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
