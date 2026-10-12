"""Streamlit session-state helpers (kept free of Streamlit imports so they are unit-testable)."""
from __future__ import annotations

import json
from typing import Any, MutableMapping

RESULT_KEY = "cago_result"
SIGNATURE_KEY = "cago_result_signature"
LANG_KEY = "cago_lang"                                   # selected UI language ("en" / "tr"); presentation only
GENERATION_COUNT_KEY = "cago_generation_count"           # how often the generator ran in this session (no-regeneration checks)
DEFAULT_SEED = 0


def request_signature(raw_request: dict[str, Any], seed: int, budget: dict[str, Any]) -> str:
    """Stable signature of what produced a result (used to flag results that no longer match the current form).
    The UI language is deliberately NOT part of it: switching language never makes a result stale."""
    return json.dumps({"request": raw_request, "seed": seed, "budget": budget}, sort_keys=True, default=str)


def store_result(state: MutableMapping[str, Any], result: dict[str, Any]) -> None:
    state[RESULT_KEY] = result
    state[SIGNATURE_KEY] = request_signature(result["raw_request"], result["seed"], result["budget"])


def current_result(state: MutableMapping[str, Any]) -> dict[str, Any] | None:
    return state.get(RESULT_KEY)


def result_is_stale(state: MutableMapping[str, Any], raw_request: dict[str, Any], seed: int, budget: dict[str, Any]) -> bool:
    return RESULT_KEY in state and state.get(SIGNATURE_KEY) != request_signature(raw_request, seed, budget)


def record_generation(state: MutableMapping[str, Any]) -> int:
    state[GENERATION_COUNT_KEY] = state.get(GENERATION_COUNT_KEY, 0) + 1
    return state[GENERATION_COUNT_KEY]


DEFAULT_CATEGORY = "trousers"                            # initial category when it is available for the segment (V1 default)


def resolve_category(available: list[str], current: str | None, preferred: str = DEFAULT_CATEGORY) -> str | None:
    """Category to keep selected after the segment (and therefore the category options) changed.

    A still-valid selection is preserved; an invalid or stale one is replaced by `preferred` when available, otherwise by the
    first available category; None when the segment has no available category (generation is then disabled)."""
    if current in available:
        return current
    if not available:
        return None
    return preferred if preferred in available else available[0]
