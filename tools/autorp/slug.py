"""Utilities for normalising bot script descriptions to safe filenames."""
from __future__ import annotations

from typing import Final
import re
import unicodedata

_DEFAULT_MAX_LENGTH: Final[int] = 80

_DEFAULT_FALLBACK: Final[str] = "scenario"
_SAFE_CHAR_PATTERN: Final[re.Pattern[str]] = re.compile(r"[^a-z0-9._-]+")

_UNICODE_OVERRIDES: Final[dict[str, str]] = {
    "ß": "ss",
    "ẞ": "ss",
    "Ø": "O",
    "ø": "o",
    "Æ": "AE",
    "æ": "ae",
    "Œ": "OE",
    "œ": "oe",
}


def _normalise_text(value: str) -> str:
    """Normalise arbitrary unicode text to an ASCII-friendly representation."""

    normalised = unicodedata.normalize("NFKD", value)
    result: list[str] = []
    for char in normalised:
        if char.isascii():
            result.append(char)
            continue
        if unicodedata.category(char) == "Mn":
            continue
        override = _UNICODE_OVERRIDES.get(char)
        if override is not None:
            result.append(override)
            continue
        ascii_equiv = char.encode("ascii", "ignore").decode("ascii")
        if ascii_equiv:
            result.append(ascii_equiv)
            continue
        name = unicodedata.name(char, "")
        replacement: str | None = None
        if " LETTER " in name:
            base_part = name.split(" LETTER ", 1)[1]
            candidate = base_part.split(" ", 1)[0]
            if len(candidate) == 1 and candidate.isalpha():
                replacement = candidate
        if replacement:
            result.append(replacement)
    return "".join(result)


def slugify_description(
    text: str | None,
    fallback: str = _DEFAULT_FALLBACK,
    *,
    max_length: int = _DEFAULT_MAX_LENGTH,
) -> str:
    """Convert an arbitrary description into a filesystem-friendly slug.

    The resulting slug is lowercased, trimmed, and limited to alphanumeric
    characters plus ``.`` ``_`` and ``-`` to keep filenames predictable across
    platforms. If the description is blank (or consists entirely of unsafe
    characters) the provided ``fallback`` is returned instead.
    """

    stripped = (text or "").strip()
    if not stripped:
        return fallback
    ascii_text = _normalise_text(stripped)
    normalised = ascii_text.casefold()
    if not normalised:
        return fallback
    safe = _SAFE_CHAR_PATTERN.sub("_", normalised)
    safe = re.sub(r"_+", "_", safe)
    safe = re.sub(r"-+", "-", safe)
    safe = re.sub(r"\.+", ".", safe)
    safe = safe.strip("._-")
    if max_length > 0 and len(safe) > max_length:
        safe = safe[:max_length].rstrip("._-")
    return safe or fallback
