from app.voice_engines.f5_tts_voice_engine import F5TTSEngine
from app.voice_engines.fish_speech_voice_engine import FishSpeechEngine
from app.voice_engines.placeholder_voice_engine import PlaceholderVoiceEngine
from app.voice_engines.voice_engine_base import VoiceEngine
from app.voice_engines.xtts_v2_voice_engine import XTTSEngine
from app.application_core.application_settings import settings


ENGINES: dict[str, VoiceEngine] = {
    "dummy": PlaceholderVoiceEngine(),
    "placeholder": PlaceholderVoiceEngine(),
    "xtts": XTTSEngine(),
    "xtts_v2": XTTSEngine(),
    "f5tts": F5TTSEngine(),
    "f5_tts": F5TTSEngine(),
    "fishspeech": FishSpeechEngine(),
    "fish_speech": FishSpeechEngine(),
}


def get_engine(name: str | None) -> VoiceEngine:
    engine_name = (name or settings.default_voice_engine).lower()
    if engine_name not in ENGINES:
        raise ValueError(f"Unknown voice engine: {engine_name}")
    return ENGINES[engine_name]
