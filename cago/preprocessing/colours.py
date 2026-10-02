"""Colour normalization. No semantic merging, no substring matching."""
from __future__ import annotations

import re
import unicodedata
from typing import Any

_WS = re.compile(r"\s+")


def normalize_colour(raw: Any) -> str | None:
    """Unicode-normalize (NFKC), casefold, collapse whitespace, strip. None/blank -> None."""
    if not isinstance(raw, str):
        return None
    s = _WS.sub(" ", unicodedata.normalize("NFKC", raw).casefold()).strip()
    return s or None


def is_exact_black(normalized: str | None) -> bool:
    return normalized == "black"
