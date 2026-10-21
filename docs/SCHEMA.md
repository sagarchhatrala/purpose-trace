# Policy, trace, and manifest schemas

All files are UTF-8 JSON, except trace files, which contain one JSON object per
line. Duplicate JSON keys, non-finite numbers, unpaired surrogates, missing fields,
and unknown envelope fields are rejected. Numeric magnitude is bounded by
`2^53 - 1`; JSON nesting is limited to 32 and nodes to 100,000 per value. A record
or policy is limited to 1 MiB; trace files to 32 MiB and 20,000 records. Blank
JSONL lines are errors. IDs are ASCII identifiers, not free text.

## Policy version 1

Required keys: `version`, `name`, `mode`, `input`, `output`.

```json
{
  "version": 1,
  "name": "support-routing",
  "mode": "deterministic",
  "input": {
    "public": ["/request"],
    "authorized": ["/service_level", "/available_queues"],
    "protected": ["/private_account_note"]
  },
  "output": {
    "observe": ["/recipient", "/queue"],
    "ignore": ["/wording"],
    "unordered": []
  },
  "min_repeats": 2,
  "min_samples": 20,
  "permutations": 1999,
  "alpha": 0.01
}
```

| Field | Contract |
| --- | --- |
| `version` | Integer `1`. |
| `name` | 1–80 characters from letters, digits, `_`, `.`, `-`. |
| `mode` | `deterministic` or `statistical`. |
| `input.public` | Task and public context that must match across compared runs. May be empty. |
| `input.authorized` | Nonempty set of context fields allowed to influence disclosure. |
| `input.protected` | Nonempty set of private context fields varied by the experiment. |
| `output.observe` | Nonempty set of policy-relevant output fields. Include recipients and all meaningful choices. |
| `output.ignore` | Explicitly excluded output fields. May be empty. Exclusion is a security-relevant policy decision. |
| `output.unordered` | Observed array paths where ordering does not matter. Duplicates still matter. |
| `min_repeats` | 2–100, default 2; required within each deterministic context and seed. |
| `min_samples` | 10–1000, default 20; required per context in statistical mode. |
| `permutations` | 99–9999, default 1999. |
| `alpha` | 0.0001–0.1, default 0.01; family-wise significance budget for one audit. |

Paths are non-root RFC 6901 JSON pointers: `/customer/tier`; `~1` represents `/`
inside a key, and `~0` represents `~`. Each list has at most 64 paths, each path
at most 512 characters. Wildcards and the root pointer are unsupported. Array
indices must be canonical nonnegative integers. Prefer selecting entire arrays.

Input classifications must not overlap, including parent/child paths. All fields,
including empty objects and arrays, must be covered. Output fields must likewise
be observed or explicitly ignored. Every selected path must exist in every
trace: absent and `null` are different. Undeclared fields fail the audit.

Arrays are ordered by default. For an `unordered` observation, elements are
sorted by canonical JSON while preserving multiplicity. Object key order and
integer-valued float formatting do not matter. Strings receive no trimming,
case folding, Unicode normalization, or semantic interpretation.

Default values are expanded before computing the policy fingerprint. Changes
to any policy field, including the name, create a new evidence namespace.

## Trace version 1

```json
{
  "id": "campaign1:run0",
  "cohort": "support-agent-v7.environment-2026-10",
  "seed": 42,
  "input": {
    "request": "Route a billing request",
    "service_level": "standard",
    "available_queues": ["east", "west"],
    "private_account_note": "synthetic private value"
  },
  "output": {
    "recipient": "support-team",
    "queue": "east",
    "wording": "Your request has been routed."
  }
}
```

Exactly these five envelope fields are required. `input` and `output` must be
objects. `id` and `cohort` have 1–160 ASCII characters from letters, digits,
`_`, `.`, `:`, `@`, `+`, `-`. `seed` is an integer from 0 to `2^32 - 1`.

One trace represents a **whole execution's disclosure**, not necessarily its
last tool call. Include ordered message history in `output` when it matters.
Different IDs must represent actual separate executions. An identical ID with
identical evidence is deduplicated; a conflicting ID is rejected. Imported
records are trusted collector assertions, not authenticated events.

## Replay manifest version 1

Required fields: `version: 1`, `cohort`, `cases`, `seeds`, and `repeats`.
See [the executable example](../examples/manifest.json).

Each of 2–64 cases contains exactly `name` and `input`; names must be unique.
`seeds` holds 1–1000 unique integers. `repeats` is 1–100. A campaign may invoke
at most 2000 adapters. Cohort names are limited to 120 characters to leave room
for the adapter fingerprint suffix.

In deterministic mode, each case runs for each supplied seed and repeat, and
`repeats` must meet the policy minimum. In statistical mode, set `repeats` to 1;
the length of `seeds` selects samples per case. The runner generates distinct
32-bit seeds for every execution using the reproducible campaign order seed.
It does not reuse supplied seed values across statistical contexts.

The adapter receives `{"input": {...}, "seed": 42}` on stdin and must return one
JSON object on stdout. Logging belongs on stderr. Both streams count toward the
output limit. Adapter arguments are an argv list after `--`; no shell is used.
Existing argument files are resolved to absolute paths and fingerprinted.

## Report version 1

Top-level fields include `schema_version`, tool/version, UTC `created_at`, policy
fingerprint, `status`, `exit_code`, record/group counts, `coverage`, `results`,
an `evidence_digest`, and interpretation limitations. Deterministic witnesses
include two trace IDs, changed observation paths, and output hashes. Statistical
results include maximum empirical total variation, p-value, corrected alpha,
method name, and permutation count.

No raw values enter the report. Identifiers, policy paths, hashes, and sample
counts remain visible; treat them as potentially sensitive metadata.
