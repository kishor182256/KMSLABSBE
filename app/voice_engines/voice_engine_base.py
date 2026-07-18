from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class VoiceOptions:
    emotion: str = "neutral"
    style_label: str | None = None
    style_reference: str | None = None
    speed: float = 1.0
    output_format: str = "wav"
    pause_seconds: float = 0.8
    quality_mode: str = "balanced"
    language: str = "en"


class VoiceEngine(ABC):
    name: str

    @abstractmethod
    def clone(self, voice_id: str, text: str, options: VoiceOptions) -> str:
        """Generate speech and return the output file path."""
