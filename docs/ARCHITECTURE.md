# Architecture

```text
Reviewed policy + raw executions
              |
      bounded JSON validation
              |
   complete field classification
              |
 canonical projections and hashes
              |
    +---------+-----------+
    |                     |
direct audit       SQLite evidence store
    |                     |
    +---------+-----------+
              |
  cohort / authorized-input grouping
              |
repeatability or permutation comparison
              |
 JSON evidence + static HTML + exit code
```

`util.py` owns bounded JSON, canonicalization, hashes, and exclusive output
publication. `policy.py` compiles a strict policy and applies complete field
coverage. `records.py` validates raw traces, computes minimized evidence, and
deduplicates identities. `audit.py` groups evidence and computes verdicts.
`store.py` handles SQLite transactions and backup. `report.py` emits escaped
script-free HTML. `replay.py` invokes trusted local adapters; `cli.py` exposes
the same operations with stable exit codes.

The core data model is intentionally independent of agent frameworks. An adapter
collects complete disclosure objects and trusted execution controls. That keeps
security claims at a reviewable boundary instead of guessing what a framework's
internal event stream means.

## Storage

SQLite schema version 1 has `policies(fingerprint, body)` and
`records(policy, id, body, checksum)`. A composite primary key prevents duplicate
sample insertion. Imports use `BEGIN IMMEDIATE`, foreign keys, WAL, and FULL
synchronous mode. All conflicting IDs roll back the entire import.

Evidence contains input, context, and output hashes, per-observation hashes,
record identity hash, cohort, and seed. Raw input and output objects are not
stored. Policy definitions remain in cleartext. Unkeyed checksums catch accidental
changes; an attacker able to rewrite the database can recompute them.

## Replay

A manifest becomes an interleaved schedule. Each invocation receives a fresh
working directory and a minimal environment. The runner fingerprints the
executable and direct file arguments, appends a digest to the cohort, and records
a campaign receipt. Transitive imports, remote services, and mutable data are
not automatically fingerprinted.

Stdin contains a single input/seed object. Nonblocking selectors drain stdout
and stderr with one combined byte limit and a monotonic wall-clock deadline.
On completion or failure, the process group is terminated. Core dumps are
disabled; CPU, file size, and file-descriptor limits are set for child processes.
These are operational bounds, not an adversarial sandbox.

The runner retains outputs in memory until every invocation succeeds, then
creates a private campaign directory. `INCOMPLETE` remains until all artifacts
are written. Consumers must reject an incomplete campaign. No successful report
is produced from a partial set of failed adapter invocations.

## Website

The public page is static. Its interactive comparison is a labeled, synthetic
demonstration; the installed Python tool is authoritative. The page can also
render a locally selected PurposeTrace report without uploading it. There are
no analytics, remote fonts, model calls, or backend services.
