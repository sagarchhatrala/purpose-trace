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
passed `pip check`. Python 3.11–3.13 and Linux were not executed locally. The
subsequent hosted CI results are recorded below separately.

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

## Website build verification

The portfolio build includes exactly four HTML entry points, including the new
`/purpose-trace/` page. The existing build checker verified **84 local references**,
assets, metadata, sitemap entries, and exclusion of retired routes. Git diffs
confirmed that the homepage, its assets/metadata, and both existing project pages
were unchanged. JavaScriptCore accepted the project script's syntax.

The local execution environment refused a loopback HTTP listener and Chrome
terminated during startup. Browser verification was subsequently completed in
Chromium on GitHub Actions, as recorded below.

## GitHub publication and hosted verification

Publication completed **2026-10-22, Asia/Kolkata**, using authenticated GitHub MCP
access. Shell Git networking remained unavailable. The initial public source
commit is `e85eca62c8a5944a3764b88f830a988bfbabc5e8`; every root file and directory
Git hash matched the local implementation plus the new browser workflow.

- [Installed-package CI](https://github.com/sagarchhatrala/purpose-trace/actions/runs/39681137563)
  passed on Ubuntu with Python **3.11, 3.12, 3.13, 3.14, and 3.15**. Each job built
  and installed a wheel, checked dependencies, executed the private and leaky
  adapters, and exercised import, duplicate suppression, health, backup, and
  restored audit. This adds 120 completed synthetic adapter executions.
- [Chromium preview verification](https://github.com/sagarchhatrala/purpose-trace/actions/runs/39681137493)
  passed before the portfolio update.
- [Pages deployment](https://github.com/sagarchhatrala/sagarchhatrala.github.io/actions/runs/39681273329)
  passed for website commit `8402da32ec890f3802ad6cec547ba7b48cdcfa17`, following
  upstream commit `3d3e62d96ee39746111bdd2a9e3a0500967598a6`. Only the ten prepared
  files changed. The published Git tree matched the locally tested tree, and
  homepage/existing project file and directory hashes remained unchanged.
- [Live Chromium verification](https://github.com/sagarchhatrala/purpose-trace/actions/runs/39681673808)
  passed against <https://sagarchhatrala.github.io/purpose-trace/>. All seven public
  assets returned HTTP 200 and matched the source bytes. The homepage and both
  existing project routes also returned HTTP 200.
- [Release-artifact build](https://github.com/sagarchhatrala/purpose-trace/actions/runs/39681679155)
  built the wheel and source archive, installed that wheel in a fresh Python 3.14
  environment, and completed the 12-execution private adapter campaign. Its
  downloadable Actions artifact is retained for 30 days. This is a separate
  build from the locally hashed wheel above; no versioned GitHub release or PyPI
  publication is claimed.

Both browser runs exercised all three strategy buttons, keyboard activation and
the skip link, sample-report loading, local JSON import with no network request,
safe text rendering, malformed JSON and unsupported-schema errors, recovery
after errors, interpretation boundaries, and exact clipboard contents. Viewports
of **320, 375, 768, and 1440 pixels** passed horizontal-overflow and control-bounds
checks. Full-page screenshots and results are retained in each browser run's
Actions artifact for 30 days. No uncaught browser errors occurred. These are
automated Chromium checks; they do not establish cross-browser compatibility or
replace a human accessibility review.

Machine-readable publication evidence is in [evidence/publication.json](evidence/publication.json).
