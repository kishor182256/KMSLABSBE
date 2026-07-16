from pathlib import Path
from shutil import copyfile

from app.application_core.application_settings import settings
from app.application_core.metadata_storage import ensure_runtime_dirs


class AudioProcessingService:
    def process(self, file_path: str, operation: str) -> str:
        ensure_runtime_dirs()
        source = Path(file_path)
        suffix = source.suffix or ".wav"
        output = Path(settings.output_dir) / f"{source.stem}_{operation}{suffix}"
        if source.exists() and source.is_file():
            copyfile(source, output)
        else:
            output.write_text(f"Placeholder {operation} output for {file_path}", encoding="utf-8")
        return str(output)
