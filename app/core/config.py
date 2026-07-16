from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    project_name: str = "AI Voice Studio"
    version: str = "0.1.0"
    api_prefix: str = "/api/v1"
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    upload_dir: str = "uploads"
    voices_dir: str = "voices"
    output_dir: str = "output"
    temp_dir: str = "temp"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
