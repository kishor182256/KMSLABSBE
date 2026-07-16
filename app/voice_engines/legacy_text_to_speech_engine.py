from app.voice_engines.placeholder_voice_engine import PlaceholderVoiceEngine


class LegacyTextToSpeechEngine(PlaceholderVoiceEngine):
    """Compatibility wrapper for older imports."""

    name = "tts"


TTSEngine = LegacyTextToSpeechEngine
