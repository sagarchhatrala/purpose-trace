# Operations and recovery

## Supported deployment

Run bounded offline audits on one trusted host or in CI. The core has no network
listener, authentication service, background worker, telemetry, or runtime
dependencies. File auditing uses Python 3.11+. Local replay requires POSIX
process controls on macOS or Linux. See [VALIDATION.md](VALIDATION.md) for the
environments actually exercised for this release.

Keep the policy, collector, executable, cohort definitions, and release-gate exit
code under trusted control. Use a fresh virtual environment and a built wheel
for deployment. Run adapters as an unprivileged user in a disposable machine or
container when they need stronger filesystem/network separation.

## Commands

`validate --policy FILE` checks and fingerprints the complete policy.

`run --policy FILE --manifest FILE --output NEW_DIRECTORY -- PROGRAM ARG...`
runs a campaign and returns its audit exit code. Optional bounds are `--timeout`
(0.1–600 seconds per invocation, default 10), `--max-output` (1024–1048576 combined
stdout/stderr bytes, default 1048576), and `--order-seed` (32-bit integer, default
0). A run can involve up to 2000 invocations; set a separate job-level deadline.

`audit --policy FILE (--traces FILE | --db FILE)` returns JSON on stdout.
`--json NEW_FILE` and `--html NEW_FILE` additionally write complete reports.
Output paths are exclusive: existing files or symlinks are not overwritten.
If one report file is written and another path fails, the command exits 2;
remove or relocate only your intended output files before retrying.

`ingest --policy FILE --traces FILE --db FILE` creates a private database when
necessary and imports all records in one transaction. Same-ID identical records
are no-ops; conflicting evidence rolls back the batch. A policy namespace has
a maximum of 20,000 records. Retain separate databases for separate campaigns
when that limit is reached rather than removing evidence in place.

`health --db FILE` checks SQLite structure, foreign keys, policy fingerprints,
and evidence checksums. This detects accidental corruption, not malicious
rewriting or rollback.

`backup --db FILE --output NEW_FILE` creates a consistent SQLite backup through
the backup API, including committed WAL data. Do not copy only the main database
while writers are active. Audit the backup before archiving it.

## Release gate

```bash
purpose-trace run --policy policy.json --manifest campaign.json \
  --output "$RUNNER_TEMP/purpose-campaign" -- python adapter.py
# The shell/CI job must stop on any nonzero result before deployment.
```

In a shell script, enable `set -e` or explicitly inspect the command status.
Do not pipe into another command unless you preserve the original exit code.
Collect reports as CI artifacts even for exit 1 or 3, with retention and access
appropriate to their metadata. A failed adapter returns exit 2, not an audit
of the successful subset.

## Files and privacy

New database files and output files are mode 0600. Campaign directories are mode
0700. Existing databases retain their permissions: operators must verify their
directory and file ownership. SQLite sidecars should remain beside the database
in a trusted directory. Windows permissions are controlled by the directory ACL.

Raw `traces.jsonl` contains private context. Reports and SQLite evidence contain
hashes and metadata. Low-entropy values can be guessed from unkeyed hashes.
Encrypt and access-control backups as appropriate; do not treat minimized
evidence as anonymous data. Policy paths and user-supplied IDs should not contain
secrets. No record automatically leaves the machine.

## Failure recovery

| Symptom | Action |
| --- | --- |
| `INCOMPLETE` in campaign directory | Discard the incomplete campaign from analysis; fix disk/permission failure and rerun into a new directory. |
| Adapter timeout/output limit | Inspect the adapter independently with synthetic inputs; fix the loop/log volume or choose a justified bound. |
| `unstable_within_context` | Freeze hidden environment state or use a properly designed statistical experiment. |
| `only_one_protected_context` | Supply matched authorized inputs across at least two private contexts. |
| `samples_reuse_random_seeds` | Collect genuinely independent samples with distinct seed identifiers. |
| `insufficient_permutation_resolution` | Increase permutations within the documented limit; otherwise redesign the preregistered campaign. |
| SQLite busy beyond 10 seconds | Wait for the writer or investigate a stuck process; do not delete a live WAL. |
| Integrity failure | Preserve the affected files, recover from a verified backup, and reimport trusted source traces. |
| ID conflict | Correct the collector's identity reuse; do not invent duplicates to inflate coverage. |

## Upgrade and retention

Schema version 1 is checked on open. Unknown schemas are rejected; no destructive
automatic migrations run. Back up before upgrading. Keep the exact policy,
wheel digest, collector version, receipt, and raw-source provenance needed to
interpret historical results. Establish a retention period outside the tool.

No garbage collector, distributed database coordination, secret manager, remote
attestation, or storage encryption is included.
