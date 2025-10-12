"""Utility helpers for generating Pawn code snippets."""
from __future__ import annotations

import re
from typing import Iterable, Sequence

INDENT = "    "


def escape_pawn_string(value: str) -> str:
    """Escape quotes and backslashes for safe Pawn strings."""
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    escaped = escaped.replace("\n", "\\n")
    return escaped


def sanitize_identifier(value: str, prefix: str = "ID") -> str:
    """Convert arbitrary text into a Pawn-safe constant name."""
    upper = value.upper()
    upper = re.sub(r"[^A-Z0-9]+", "_", upper).strip("_")
    if not upper:
        upper = prefix
    if upper[0].isdigit():
        upper = f"{prefix}_{upper}"
    return upper


def indent_lines(lines: Sequence[str], level: int = 1) -> str:
    """Return a single string with the provided lines indented."""
    prefix = INDENT * level
    return "\n".join(f"{prefix}{line}" if line else "" for line in lines)


def block(name: str, body: Iterable[str], level: int = 0) -> str:
    """Create a Pawn function-like block using braces."""
    head_indent = INDENT * level
    body_indent = INDENT * (level + 1)
    body_lines = [f"{body_indent}{line}" for line in body]
    return "\n".join([f"{head_indent}{name}", f"{head_indent}{{"] + body_lines + [f"{head_indent}}}"])


__all__ = ["escape_pawn_string", "sanitize_identifier", "indent_lines", "block", "INDENT"]
