"""Shared text helpers for LLM responses."""


def strip_code_fences(text: str) -> str:
    """Remove optional markdown ```json ... ``` wrapping."""
    raw = text.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
    if raw.endswith("```"):
        raw = raw.rsplit("```", 1)[0]
    return raw.strip()
