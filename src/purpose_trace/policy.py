"""Explicit input classification and policy-relevant output projection."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from .util import InputError, canonical, decode, digest, fields, integer, validate_json


def tokens(path: str) -> tuple[str, ...]:
    if not isinstance(path, str) or len(path) > 512 or not path.startswith("/"):
        raise InputError("paths must be non-root RFC 6901 JSON pointers")
    if re.search(r"~(?![01])", path):
        raise InputError("invalid JSON pointer escape")
    return tuple(s.replace("~1", "/").replace("~0", "~") for s in path[1:].split("/"))


def get(value: Any, path: str) -> Any:
    for token in tokens(path):
        if isinstance(value, dict) and token in value:
            value = value[token]
        elif isinstance(value, list) and re.fullmatch(r"0|[1-9][0-9]*", token):
            index = int(token)
            if index >= len(value):
                raise InputError(f"required path absent: {path}")
            value = value[index]
        else:
            raise InputError(f"required path absent: {path}")
    return value


def path_list(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list) or len(value) > 64:
        raise InputError("path declarations must be arrays of at most 64 pointers")
    for path in value:
        tokens(path)
    if len(set(value)) != len(value):
        raise InputError("duplicate policy paths")
    return tuple(value)


def disjoint(paths: tuple[str, ...]) -> None:
    parts = [tokens(p) for p in paths]
    for i, left in enumerate(parts):
        for right in parts[i + 1:]:
            if left[:len(right)] == right or right[:len(left)] == left:
                raise InputError("policy paths overlap or have conflicting classifications")


def cover(value: Any, paths: tuple[str, ...]) -> None:
    """Reject unclassified fields, including otherwise invisible empty containers."""
    selected = {tokens(p) for p in paths}
    for path in paths:
        get(value, path)

    def walk(item: Any, at: tuple[str, ...]) -> None:
        if at in selected:
            return
        if isinstance(item, dict) and item:
            for key, child in item.items():
                walk(child, at + (key,))
        elif isinstance(item, list) and item:
            for i, child in enumerate(item):
                walk(child, at + (str(i),))
        else:
            raise InputError("unclassified input/output field; update the policy explicitly")

    walk(value, ())


@dataclass(frozen=True)
class Policy:
    """Validated immutable policy; construct through :meth:`from_dict`."""

    encoded: str
    fingerprint: str
    name: str
    mode: str
    public: tuple[str, ...]
    authorized: tuple[str, ...]
    protected: tuple[str, ...]
    observe: tuple[str, ...]
    ignore: tuple[str, ...]
    unordered: tuple[str, ...]
    min_repeats: int
    min_samples: int
    permutations: int
    alpha: float

    @classmethod
    def from_dict(cls, raw: dict) -> Policy:
        validate_json(raw)
        raw = decode(canonical(raw))
        fields(raw, {"version", "name", "mode", "input", "output"},
               {"min_repeats", "min_samples", "permutations", "alpha"})
        if type(raw["version"]) is not int or raw["version"] != 1:
            raise InputError("unsupported policy version")
        if not isinstance(raw["name"], str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,80}", raw["name"]):
            raise InputError("policy name must be a short ASCII identifier")
        if raw["mode"] not in ("deterministic", "statistical"):
            raise InputError("mode must be deterministic or statistical")
        fields(raw["input"], {"public", "authorized", "protected"})
        fields(raw["output"], {"observe", "ignore", "unordered"})
        public, authorized, protected = (path_list(raw["input"][k])
                                         for k in ("public", "authorized", "protected"))
        observe, ignore, unordered = (path_list(raw["output"][k])
                                     for k in ("observe", "ignore", "unordered"))
        if not authorized or not protected or not observe:
            raise InputError("authorized, protected, and observed paths must be nonempty")
        disjoint(public + authorized + protected)
        disjoint(observe + ignore)
        if not set(unordered) <= set(observe):
            raise InputError("unordered paths must also be observed paths")
        repeats = integer(raw.get("min_repeats", 2), "min_repeats", 2, 100)
        samples = integer(raw.get("min_samples", 20), "min_samples", 10, 1000)
        permutations = integer(raw.get("permutations", 1999), "permutations", 99, 9999)
        alpha = raw.get("alpha", 0.01)
        if type(alpha) not in (int, float) or not 0.0001 <= alpha <= 0.1:
            raise InputError("alpha must be between 0.0001 and 0.1")
        raw.update(min_repeats=repeats, min_samples=samples,
                   permutations=permutations, alpha=alpha)
        return cls(canonical(raw), digest(raw), raw["name"], raw["mode"], public,
                   authorized, protected, observe, ignore, unordered, repeats,
                   samples, permutations, float(alpha))

    def project_input(self, payload: dict) -> tuple[dict, dict]:
        cover(payload, self.public + self.authorized + self.protected)
        permitted = {p: get(payload, p) for p in self.public + self.authorized}
        protected = {p: get(payload, p) for p in self.protected}
        return permitted, protected

    def project_output(self, payload: dict) -> dict:
        cover(payload, self.observe + self.ignore)
        selected = {p: get(payload, p) for p in self.observe}
        for path in self.unordered:
            if not isinstance(selected[path], list):
                raise InputError(f"unordered observation is not an array: {path}")
            selected[path] = sorted(selected[path], key=canonical)
        return selected
