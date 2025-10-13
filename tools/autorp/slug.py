"""Utilities for normalising bot script descriptions to safe filenames."""
from __future__ import annotations

from typing import Final
import re

_DEFAULT_FALLBACK: Final[str] = "scenario"
_SAFE_CHAR_PATTERN: Final[re.Pattern[str]] = re.compile(r"[^a-z0-9._-]+")


def slugify_description(text: str | None, fallback: str = _DEFAULT_FALLBACK) -> str:
    """Convert an arbitrary description into a filesystem-friendly slug.

    The resulting slug is lowercased, trimmed, and limited to alphanumeric
    characters plus ``.`` ``_`` and ``-`` to keep filenames predictable across
    platforms. If the description is blank (or consists entirely of unsafe
    characters) the provided ``fallback`` is returned instead.
    """

    normalised = (text or "").strip().casefold()
    if not normalised:
        return fallback
    safe = _SAFE_CHAR_PATTERN.sub("_", normalised).strip("._-")
    return safe or fallback
