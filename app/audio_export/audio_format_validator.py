SUPPORTED_FORMATS = {"wav", "mp3"}


def validate_format(output_format: str) -> str:
    normalized = output_format.lower().lstrip(".")
    if normalized not in SUPPORTED_FORMATS:
        raise ValueError(f"Unsupported output format: {output_format}")
    return normalized
