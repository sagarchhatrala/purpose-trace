"""Validated traces become minimized evidence before storage or reporting."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

from .policy import Policy
from .util import (InputError, MAX_FILE, MAX_RECORD, MAX_RECORDS, canonical,
                   decode, digest, fields, integer, validate_json)


def identifier(value, label: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_.:@+-]{1,160}", value):
        raise InputError(f"{label} must be a nonempty ASCII identifier, at most 160 characters")
    return value


def prepare(policy: Policy, trace: dict) -> dict:
    validate_json(trace)
    trace = decode(canonical(trace))
    fields(trace, {"id", "cohort", "seed", "input", "output"})
    identifier(trace["id"], "trace id")
    identifier(trace["cohort"], "cohort")
    integer(trace["seed"], "seed", 0, 2**32 - 1)
    if not isinstance(trace["input"], dict) or not isinstance(trace["output"], dict):
        raise InputError("input and output must be objects")
    permitted, protected = policy.project_input(trace["input"])
    output = policy.project_output(trace["output"])
    return {
        "version": 1, "policy": policy.fingerprint, "id": trace["id"],
        "cohort": trace["cohort"], "seed": trace["seed"],
        "input_hash": digest(permitted), "context_hash": digest(protected),
        "output_hash": digest(output), "record_hash": digest(trace),
        "observations": {p: digest(v) for p, v in output.items()},
    }


def validate_prepared(policy: Policy, record: dict) -> None:
    fields(record, {"version", "policy", "id", "cohort", "seed", "input_hash",
                    "context_hash", "output_hash", "record_hash", "observations"})
    if type(record["version"]) is not int or record["version"] != 1:
        raise InputError("unsupported stored evidence version")
    identifier(record["id"], "trace id")
    identifier(record["cohort"], "cohort")
    integer(record["seed"], "seed", 0, 2**32 - 1)
    if record["policy"] != policy.fingerprint:
        raise InputError("stored evidence policy mismatch")
    fields(record["observations"], set(policy.observe))
    hashes = [record[k] for k in ("policy", "input_hash", "context_hash", "output_hash", "record_hash")]
    hashes.extend(record["observations"].values())
    if any(not isinstance(h, str) or not re.fullmatch(r"[0-9a-f]{64}", h) for h in hashes):
        raise InputError("stored evidence contains an invalid digest")


def read_traces(path: str | Path) -> Iterable[dict]:
    consumed = 0
    with Path(path).open("rb") as stream:
        for index, raw in enumerate(iter(lambda: stream.readline(MAX_RECORD + 1), b""), 1):
            consumed += len(raw)
            if index > MAX_RECORDS or consumed > MAX_FILE:
                raise InputError("trace file exceeds record or byte limits")
            if not raw.strip():
                raise InputError(f"blank JSONL record at line {index}")
            try:
                yield decode(raw)
            except InputError as exc:
                raise InputError(f"invalid trace at line {index}: {exc}") from exc


def unique(records: Iterable[dict]) -> list[dict]:
    seen = {}
    for record in records:
        if len(seen) >= MAX_RECORDS and record["id"] not in seen:
            raise InputError("too many records")
        old = seen.get(record["id"])
        if old is not None and old != record:
            raise InputError("trace id was reused for different evidence")
        seen[record["id"]] = record
    return list(seen.values())
