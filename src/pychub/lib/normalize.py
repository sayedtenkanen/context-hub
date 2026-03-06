"""Language normalization utilities.

Port of cli/src/lib/normalize.js
"""

ALIASES = {
    "js": "javascript",
    "ts": "typescript",
    "py": "python",
    "rb": "ruby",
    "cs": "csharp",
}

DISPLAY = {
    "javascript": "js",
    "typescript": "ts",
    "python": "py",
    "ruby": "rb",
    "csharp": "cs",
}


def normalize_language(lang: str | None) -> str | None:
    """Normalize language code (e.g., 'py' -> 'python')."""
    if not lang:
        return None
    lower = lang.lower()
    return ALIASES.get(lower, lower)


def display_language(lang: str) -> str:
    """Get display form of language (e.g., 'python' -> 'py')."""
    return DISPLAY.get(lang, lang)
