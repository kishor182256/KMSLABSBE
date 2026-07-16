from pathlib import Path

from app.core.config import settings


class VoiceService:
    def __init__(self) -> None:
        self.upload_dir = Path(settings.upload_dir)
        self.voices_dir = Path(settings.voices_dir)
        self.output_dir = Path(settings.output_dir)
        self.temp_dir = Path(settings.temp_dir)

    def ensure_storage_dirs(self) -> None:
        for directory in (self.upload_dir, self.voices_dir, self.output_dir, self.temp_dir):
            directory.mkdir(parents=True, exist_ok=True)
