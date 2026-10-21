# Actual local validation

Validation date: **2026-10-22, Asia/Kolkata**. These results came from installed
wheel executions on the local macOS ARM64 machine, using synthetic data and
temporary directories. No generated unit-test suite or live customer system was
used. Detailed machine-readable records are in [evidence/](evidence/).

## Release wheel

`purpose_trace-1.0.0-py3-none-any.whl`

SHA-256:
`942c4373915f0939c36c11278ae9cf1c3356c32b8d51ad19611a8eeaee5b13d1`

The wheel was installed into Python 3.14 and Python 3.15 virtual environments.
The clean 3.14 environment contained only pip and PurposeTrace. Both environments
passed `pip check`. Python 3.11–3.13 and Linux are configured in CI but were not
executed locally; their successful execution must not be inferred from the
workflow file.

## Actual adapter campaigns

Each interpreter ran all four campaigns below: **368 completed adapter
executions** on the final wheel in total.

| Workflow | Executions per interpreter | Observed result |
| --- | --- | --- |
| Private context selects support queue | 12 | `VIOLATION`, exit 1, all 3 seed groups, changed `/queue` |
| Queue selected from authorized inputs | 12 | `CONSISTENT`, exit 0, all 3 groups |
| Private context biases random routing | 80 | `VIOLATION`, exit 1, TV 0.95, p 0.0005 |
| Random routing independent of private context | 80 | `NO_DIFFERENCE_DETECTED`, exit 0, TV 0.075 |

For the independent randomized campaign, p-values were 0.64 on Python 3.14 and
0.634 on Python 3.15. Cohort fingerprints differ across interpreter environments,
so the permutation randomization differs. Both are well above alpha 0.01. These
are observations on synthetic adapters, not measured results for hosted models
or a benchmark of detection coverage.

Earlier development campaigns exercised another 184 adapter executions before
the interpreter-path fix. They are excluded from the final-wheel count above.

## Actual operational workflows

Twenty-nine command-driven operations ran successfully against the installed
wheel, with their intended outcomes. The evidence record includes actual exit
codes and durations.

- SQLite import, duplicate suppression, persisted audit, backup, and restored
  audit; report evidence digests matched before and after storage.
- Conflicting import after a new record: the entire transaction rolled back;
  the database retained exactly 12 records.
- Four concurrent CLI processes imported into a new database; all completed
  and only 12 unique records remained.
- An intentionally corrupted backup failed `health` with exit 2.
- Undeclared fields, missing observations, duplicate JSON keys, NaN, oversized
  numbers, 5000-digit numeric text, and overlapping policy paths failed closed.
- Unstable repeats, insufficient repeats, duplicated evidence, mismatched
  authorized inputs, and correlated statistical seeds returned inconclusive.
- Explicit unordered-array observations tolerated order changes.
- A real adapter importing PurposeTrace from its private virtual environment
  succeeded after the interpreter-path correction.
- Sleeping, output-flooding, malformed-output, and nonzero-exit adapters failed
  with exit 2 and did not publish a partial campaign.
- A synthetic inherited environment secret was absent inside the adapter;
  temporary files and working directories were cleaned up.
- Existing campaign output was refused. New campaign directories were mode 0700;
  raw trace files and database files were mode 0600.

## Fixes made during validation and review

The runner originally resolved an interpreter symlink to its base installation,
which lost a virtual environment's installed packages. A real dependency-using
adapter reproduced the failure. Preserving the absolute invocation path fixed
it; the same adapter then completed all 12 executions.

Store initialization was made transactional and tolerant of concurrent initial
file creation. A four-process import confirmed the resulting behavior. JSON
numeric handling was hardened so oversized numeric text produces a structured
error rather than a traceback. The corresponding actual CLI inputs were rejected.

## Website verification and remaining limits

The portfolio build includes exactly four HTML entry points, including the new
`/purpose-trace/` page. The existing build checker verified **84 local references**,
assets, metadata, sitemap entries, and exclusion of retired routes. Git diffs
confirmed that the homepage, its assets/metadata, and both existing project pages
were unchanged. JavaScriptCore accepted the project script's syntax.

The current execution environment refused a loopback HTTP listener and Chrome
terminated during startup. Consequently **browser rendering, interactive report
upload, clipboard behavior, and responsive layout were not exercised in a live
browser**. Syntax/link checks do not substitute for that work. Complete those
checks in an environment with browser access before treating the public page as
fully browser-validated.

Git networking and GitHub authentication were unavailable in this session.
Local commits, artifacts, and the website patch can be prepared, but successful
GitHub publication, hosted CI, Pages deployment, and live-URL verification require
an authenticated environment. This document does not claim they occurred.
