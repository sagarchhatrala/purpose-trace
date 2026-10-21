"""Bounded JSON, stable hashes, and atomic private output files."""

from __future__ import annotations

import hashlib
import json
import math
import os
import tempfile
from pathlib import Path
from typing import Any

MAX_FILE = 32 * 1024 * 1024
MAX_RECORD = 1024 * 1024
MAX_RECORDS = 20_000


class InputError(ValueError):
    """The supplied evidence or policy cannot be evaluated safely."""


def _pairs(items: list[tuple[str, Any]]) -> dict:
    result = {}
    for key, value in items:
        if key in result:
            raise InputError("duplicate JSON object key")
        result[key] = value
    return result


def validate_json(value: Any, depth: int = 0, budget: list | None = None) -> None:
    if budget is None:
        budget = [100_000]
    budget[0] -= 1
    if budget[0] < 0 or depth > 32:
        raise InputError("JSON exceeds node or depth limit")
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise InputError("JSON object keys must be strings")
            validate_json(key, depth + 1, budget)
            validate_json(item, depth + 1, budget)
    elif isinstance(value, list):
        for item in value:
            validate_json(item, depth + 1, budget)
    elif isinstance(value, str):
        if len(value) > 100_000 or any(0xD800 <= ord(c) <= 0xDFFF for c in value):
            raise InputError("invalid or oversized JSON string")
    elif value is None or isinstance(value, bool):
        pass
    elif isinstance(value, (int, float)):
        if abs(value) > 2**53 - 1 or (isinstance(value, float) and not math.isfinite(value)):
            raise InputError("numbers must be finite and within the exact integer range")
    else:
        raise InputError("value is not JSON-compatible")


def decode(raw: str | bytes, limit: int = MAX_RECORD) -> Any:
    if len(raw) > limit:
        raise InputError("JSON exceeds size limit")
    try:
        value = json.loads(raw, object_pairs_hook=_pairs)
        validate_json(value)
        return value
    except InputError:
        raise
    except (ValueError, RecursionError, OverflowError) as exc:
        raise InputError("invalid JSON") from exc


def load(path: str | Path, limit: int = MAX_RECORD) -> Any:
    with Path(path).open("rb") as stream:
        return decode(stream.read(limit + 1), limit)


def canonical(value: Any) -> str:
    # Treat 1.0 and 1 as the same JSON number; preserve booleans as booleans.
    def normalize(item: Any) -> Any:
        if isinstance(item, float) and item.is_integer():
            return int(item)
        if isinstance(item, dict):
            return {k: normalize(v) for k, v in item.items()}
        if isinstance(item, list):
            return [normalize(v) for v in item]
        return item

    return json.dumps(normalize(value), sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), allow_nan=False)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def fields(value: Any, required: set, optional: set | None = None) -> None:
    if not isinstance(value, dict):
        raise InputError("expected a JSON object")
    if not required <= value.keys() or value.keys() - required - (optional or set()):
        raise InputError("missing or unknown object fields; see the schema documentation")


def integer(value: Any, label: str, low: int, high: int) -> int:
    if type(value) is not int or not low <= value <= high:
        raise InputError(f"{label} must be an integer from {low} to {high}")
    return value


def write_new(path: str | Path, data: str | bytes) -> None:
    """Publish a complete file atomically, without overwriting existing data."""
    target = Path(path)
    payload = data.encode("utf-8") if isinstance(data, str) else data
    fd, name = tempfile.mkstemp(prefix=".purposetrace-", dir=target.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(name, target)  # Exclusive publication, including dangling symlinks.
    finally:
        os.unlink(name)
