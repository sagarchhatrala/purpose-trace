"""Deterministic witnesses and bounded, reproducible distribution comparisons."""

from __future__ import annotations

import itertools
import random
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Iterable

from .policy import Policy
from .records import prepare, unique, validate_prepared
from .util import InputError, digest

EXIT_CODES = {"CONSISTENT": 0, "NO_DIFFERENCE_DETECTED": 0,
              "VIOLATION": 1, "INCONCLUSIVE": 3}


def _deterministic(policy: Policy, contexts: dict) -> dict:
    if len(contexts) < 2:
        return {"status": "INCONCLUSIVE", "reason": "only_one_protected_context"}
    if any(len(records) < policy.min_repeats for records in contexts.values()):
        return {"status": "INCONCLUSIVE", "reason": "insufficient_repeats"}
    if any(len({r["output_hash"] for r in records}) > 1 for records in contexts.values()):
        return {"status": "INCONCLUSIVE", "reason": "unstable_within_context"}
    representatives = [sorted(rs, key=lambda r: r["id"])[0] for _, rs in sorted(contexts.items())]
    for left, right in itertools.combinations(representatives, 2):
        if left["output_hash"] != right["output_hash"]:
            changed = sorted(p for p in left["observations"]
                             if left["observations"][p] != right["observations"][p])
            return {"status": "VIOLATION", "reason": "protected_context_changes_observation",
                    "witness": {"trace_ids": [left["id"], right["id"]],
                                "changed_paths": changed,
                                "output_hashes": [left["output_hash"], right["output_hash"]]}}
    return {"status": "CONSISTENT", "reason": "observed_contexts_agree"}


def _tv(parts: list[list[str]]) -> float:
    counters = [Counter(p) for p in parts]
    largest = 0.0
    for i, j in itertools.combinations(range(len(parts)), 2):
        a, b = counters[i], counters[j]
        largest = max(largest, sum(abs(a[k] / len(parts[i]) - b[k] / len(parts[j]))
                                  for k in a.keys() | b.keys()) / 2)
    return largest


def _statistical(policy: Policy, contexts: dict, threshold: float, group_hash: str) -> dict:
    if len(contexts) < 2:
        return {"status": "INCONCLUSIVE", "reason": "only_one_protected_context"}
    if any(len(rs) < policy.min_samples for rs in contexts.values()):
        return {"status": "INCONCLUSIVE", "reason": "insufficient_samples"}
    records = [r for rs in contexts.values() for r in rs]
    if len({r["seed"] for r in records}) != len(records):
        return {"status": "INCONCLUSIVE", "reason": "samples_reuse_random_seeds"}
    if 1 / (policy.permutations + 1) > threshold:
        return {"status": "INCONCLUSIVE", "reason": "insufficient_permutation_resolution",
                "corrected_alpha": threshold}
    parts = [[r["output_hash"] for r in sorted(rs, key=lambda r: r["id"])]
             for _, rs in sorted(contexts.items())]
    observed = _tv(parts)
    pooled = [v for part in parts for v in part]
    rng = random.Random(int(group_hash, 16))
    bounds = [0]
    for part in parts:
        bounds.append(bounds[-1] + len(part))
    exceed = 0
    for _ in range(policy.permutations):
        rng.shuffle(pooled)
        shuffled = [pooled[bounds[i]:bounds[i + 1]] for i in range(len(parts))]
        if _tv(shuffled) >= observed - 1e-12:
            exceed += 1
    p_value = (exceed + 1) / (policy.permutations + 1)
    signal = p_value <= threshold
    return {"status": "VIOLATION" if signal else "NO_DIFFERENCE_DETECTED",
            "reason": "distribution_difference" if signal else "no_statistical_signal",
            "max_total_variation": round(observed, 8), "p_value": p_value,
            "corrected_alpha": threshold, "permutations": policy.permutations,
            "method": "label-permutation-max-pair-TV-with-Bonferroni"}


def audit_prepared(policy: Policy, prepared: Iterable[dict]) -> dict:
    validated = []
    for record in prepared:
        validate_prepared(policy, record)
        validated.append(record)
        if len(validated) > 20000:
            raise InputError("too many evidence records")
    records = unique(validated)
    if not records:
        raise InputError("an audit requires at least one trace")
    if any(r["policy"] != policy.fingerprint for r in records):
        raise InputError("evidence belongs to a different policy")
    groups = defaultdict(lambda: defaultdict(list))
    for record in records:
        key = (record["cohort"], record["input_hash"],
               record["seed"] if policy.mode == "deterministic" else None)
        groups[key][record["context_hash"]].append(record)
    if len(groups) > 1024 or any(len(c) > 16 for c in groups.values()):
        raise InputError("audit exceeds 1024 groups or 16 contexts per group")
    if policy.mode == "statistical" and policy.permutations * len(records) > 50_000_000:
        raise InputError("statistical workload exceeds 50 million sample permutations")
    results = []
    for key, contexts in sorted(groups.items()):
        group_hash = digest([policy.fingerprint, key])
        result = (_deterministic(policy, contexts) if policy.mode == "deterministic" else
                  _statistical(policy, contexts, policy.alpha / len(groups), group_hash))
        results.append({"group": group_hash, "cohort": key[0], "input_hash": key[1],
                        "seed": key[2], "contexts": len(contexts),
                        "samples": sum(len(rs) for rs in contexts.values()),
                        "samples_by_context": {h: len(rs) for h, rs in sorted(contexts.items())},
                        **result})
    counts = Counter(r["status"] for r in results)
    status = ("VIOLATION" if counts["VIOLATION"] else
              "INCONCLUSIVE" if counts["INCONCLUSIVE"] else
              "CONSISTENT" if policy.mode == "deterministic" else "NO_DIFFERENCE_DETECTED")
    return {"schema_version": 1, "tool": "purpose-trace", "tool_version": "1.0.0",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "policy": {"name": policy.name, "fingerprint": policy.fingerprint, "mode": policy.mode},
            "status": status, "exit_code": EXIT_CODES[status],
            "records": len(records), "groups": len(results),
            "coverage": dict(sorted(counts.items())), "results": results,
            "evidence_digest": digest(sorted(records, key=lambda r: r["id"])),
            "limitations": [
                "Results describe supplied observations under the declared policy, not universal safety.",
                "Cohorts, projections, completeness, and controlled inputs are trusted integration claims.",
                "Deterministic witnesses assume repeatable execution under matched seeds and environment.",
                "Statistical significance assumes independent exchangeable samples; it does not establish causality.",
                "A nonsignificant result does not prove independence; hashes do not anonymize low-entropy data.",
            ]}


def audit(policy: Policy, traces: Iterable[dict]) -> dict:
    """Audit raw trace dictionaries; invalid evidence raises InputError."""
    return audit_prepared(policy, (prepare(policy, trace) for trace in traces))
