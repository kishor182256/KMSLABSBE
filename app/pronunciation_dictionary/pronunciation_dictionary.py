DEFAULT_PRONUNCIATIONS: dict[str, str] = {
    "AI": "Artificial Intelligence",
    "XTTS": "ex tee tee ess",
}


def apply_pronunciations(text: str, dictionary: dict[str, str] | None = None) -> str:
    replacements = dictionary or DEFAULT_PRONUNCIATIONS
    for source, target in replacements.items():
        text = text.replace(source, target)
    return text
