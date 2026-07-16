from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class VoiceOptions:
    emotion: str = "neutral"
    speed: float = 1.0
    output_format: str = "wav"


class VoiceEngine(ABC):
    name: str

    @abstractmethod
    def clone(self, voice_id: str, text: str, options: VoiceOptions) -> str:
        """Generate speech and return the output file path."""
