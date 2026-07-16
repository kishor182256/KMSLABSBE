from datetime import datetime, UTC
from pathlib import Path
from uuid import uuid4

from app.application_core.application_settings import settings
from app.application_core.metadata_storage import ensure_runtime_dirs
from app.voice_engines.voice_engine_base import VoiceEngine, VoiceOptions


class PlaceholderVoiceEngine(VoiceEngine):
    name = "dummy"

    def clone(self, voice_id: str, text: str, options: VoiceOptions) -> str:
        ensure_runtime_dirs()
        suffix = options.output_format.lstrip(".").lower() or "wav"
        output_path = Path(settings.output_dir) / f"{voice_id}_{uuid4().hex}.{suffix}"
        output_path.write_text(
            "\n".join(
                [
                    "AI Voice Studio placeholder audio file",
                    f"created_at={datetime.now(UTC).isoformat()}",
                    f"voice_id={voice_id}",
                    f"emotion={options.emotion}",
                    f"speed={options.speed}",
                    "",
                    text,
                ]
            ),
            encoding="utf-8",
        )
        return str(output_path)
