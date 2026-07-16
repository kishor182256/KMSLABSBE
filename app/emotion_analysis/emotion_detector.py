def detect_emotion(text: str) -> str:
    lowered = text.lower()
    if any(word in lowered for word in ("cry", "sad", "tears")):
        return "sad"
    if any(word in lowered for word in ("battle", "epic", "victory")):
        return "epic"
    return "neutral"
