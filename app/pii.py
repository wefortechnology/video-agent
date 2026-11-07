"""Tiny guard so personal data does not end up in brand memory or prompts (EdZola policy)."""
import re

_PATTERNS = {
    "an email address": re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"),
    "a phone number": re.compile(r"(?<!\d)(?:\+?91[\s-]?)?[6-9]\d{9}(?!\d)"),
    "an Aadhaar-like number": re.compile(r"(?<!\d)\d{4}\s?\d{4}\s?\d{4}(?!\d)"),
    "an API key": re.compile(r"AIza[0-9A-Za-z_\-]{20,}"),
}


def find_pii(text: str):
    return [name for name, rx in _PATTERNS.items() if rx.search(text or "")]


def assert_clean(*texts: str):
    found = set()
    for t in texts:
        found.update(find_pii(t))
    if found:
        raise ValueError("Please remove " + ", ".join(sorted(found)) + " (no personal data or keys in prompts or memory).")
