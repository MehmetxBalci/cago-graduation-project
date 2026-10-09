"""Streamlit session-state helpers (kept free of Streamlit imports so they are unit-testable)."""
from __future__ import annotations

import json
from typing import Any, MutableMapping

RESULT_KEY = "cago_result"
SIGNATURE_KEY = "cago_result_signature"
DEFAULT_SEED = 0


def request_signature(raw_request: dict[str, Any], seed: int, budget: dict[str, Any]) -> str:
    """Stable signature of what produced a result (used to flag results that no longer match the current form)."""
    return json.dumps({"request": raw_request, "seed": seed, "budget": budget}, sort_keys=True, default=str)


def store_result(state: MutableMapping[str, Any], result: dict[str, Any]) -> None:
    state[RESULT_KEY] = result
    state[SIGNATURE_KEY] = request_signature(result["raw_request"], result["seed"], result["budget"])


def current_result(state: MutableMapping[str, Any]) -> dict[str, Any] | None:
    return state.get(RESULT_KEY)


def result_is_stale(state: MutableMapping[str, Any], raw_request: dict[str, Any], seed: int, budget: dict[str, Any]) -> bool:
    return RESULT_KEY in state and state.get(SIGNATURE_KEY) != request_signature(raw_request, seed, budget)
