"""Source reading. Row numbers are 1-based physical line numbers in the file."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def read_jsonl(path: Path) -> tuple[list[tuple[int, dict[str, Any]]], list[tuple[int, str]], int]:
    """Return (records[(row_number, dict)], malformed[(row_number, error)], blank_line_count).

    Non-object JSON values count as malformed.
    """
    records: list[tuple[int, dict[str, Any]]] = []
    malformed: list[tuple[int, str]] = []
    blank = 0
    with Path(path).open(encoding="utf-8-sig") as fh:
        for row_no, line in enumerate(fh, start=1):
            if not line.strip():
                blank += 1
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as exc:
                malformed.append((row_no, str(exc)))
                continue
            if not isinstance(obj, dict):
                malformed.append((row_no, f"top-level JSON is {type(obj).__name__}, expected object"))
                continue
            records.append((row_no, obj))
    return records, malformed, blank
