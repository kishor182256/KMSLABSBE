import json
from pathlib import Path
from typing import Any

from app.application_core.application_settings import settings


def ensure_runtime_dirs() -> None:
    for path in (
        settings.upload_dir,
        settings.voices_dir,
        settings.output_dir,
        settings.temp_dir,
        settings.metadata_dir,
    ):
        Path(path).mkdir(parents=True, exist_ok=True)


def metadata_path(name: str) -> Path:
    ensure_runtime_dirs()
    return Path(settings.metadata_dir) / f"{name}.json"


def read_collection(name: str) -> list[dict[str, Any]]:
    path = metadata_path(name)
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def write_collection(name: str, rows: list[dict[str, Any]]) -> None:
    path = metadata_path(name)
    path.write_text(json.dumps(rows, indent=2), encoding="utf-8")
