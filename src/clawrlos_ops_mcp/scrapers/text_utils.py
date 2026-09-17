DEFAULT_SUMMARY_MAX_LEN = 280


def clean_summary(text: str | None, max_len: int = DEFAULT_SUMMARY_MAX_LEN) -> str | None:
    """Collapse whitespace and truncate to max_len, appending an ellipsis if cut."""
    if not text:
        return None
    cleaned = " ".join(text.split())
    if not cleaned:
        return None
    if len(cleaned) > max_len:
        return cleaned[:max_len] + "..."
    return cleaned
