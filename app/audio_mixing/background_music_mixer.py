def ducking_plan(voice_path: str, music_path: str) -> dict[str, str | float]:
    return {
        "voice_path": voice_path,
        "music_path": music_path,
        "music_gain_db": -18.0,
    }
