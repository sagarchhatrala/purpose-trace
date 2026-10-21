# PurposeTrace

**Find private information leaking through an agent's choices.**

A support assistant can send a perfectly valid queue name while quietly selecting
that queue based on a confidential account note. Every output is allowed on its
own. The problem becomes visible when executions with the same authorized inputs
behave differently across private contexts.

PurposeTrace is an independent, local-first execution auditor. It runs trusted
adapters against controlled inputs or imports existing JSONL traces, compares
policy-relevant disclosures, and produces evidence suitable for a release gate.
The implementation requires Python 3.11+ and has **no runtime dependencies**.

- Explicit classification of public, authorized, and protected input fields.
- Deterministic witnesses with matching seeds and repeatability checks.
- Statistical distribution comparisons with permutation p-values and correction
  across comparison groups.
- Fail-closed input validation; incomplete or unstable evidence is inconclusive.
- Atomic SQLite imports, duplicate suppression, integrity checks, and backups.
- JSON and self-contained HTML reports that omit raw inputs and output values.
- Temporary local replay workspaces, minimal environments, process timeouts, and
  bounded output capture on macOS and Linux.

## Install

Install from a checkout or a downloaded release wheel. No PyPI publication is
assumed by these instructions.

```bash
git clone https://github.com/sagarchhatrala/purpose-trace.git
cd purpose-trace
python3 -m venv .venv
source .venv/bin/activate
python -m pip install .
purpose-trace --version
```

On Windows, activate `.venv\Scripts\activate`; file auditing and storage work
without the POSIX replay command.

## Run real workflows

The included adapters process synthetic support requests and return real JSON
outputs. They make no network requests and do not change external systems.

```bash
purpose-trace run --policy examples/policy.json \
  --manifest examples/manifest.json --output /tmp/purpose-leak \
  -- python examples/leaky_router.py
```

Expected: `VIOLATION`, exit **1**, three comparison groups identify `/queue` as
the changed observation. Open `/tmp/purpose-leak/report.html` for the evidence.
The nonzero exit is the intended detection result.

Run the implementation that selects from authorized data only:

```bash
purpose-trace run --policy examples/policy.json \
  --manifest examples/manifest.json --output /tmp/purpose-private \
  -- python examples/private_router.py
```

Expected: `CONSISTENT`, exit **0**, twelve actual adapter executions. Choose new
output directories when repeating either command; existing data is not replaced.

## Audit your own traces

Each line of a trace file is an object with `id`, `cohort`, `seed`, `input`, and
`output`. A cohort identifies a fixed agent version and environment.

```bash
purpose-trace validate --policy examples/policy.json
purpose-trace audit --policy examples/policy.json \
  --traces /tmp/purpose-leak/traces.jsonl \
  --json /tmp/purpose-audit.json --html /tmp/purpose-audit.html
```

| Exit | Result | Meaning |
| --- | --- | --- |
| 0 | `CONSISTENT` | Every supplied deterministic group passed its coverage and repeatability checks. |
| 0 | `NO_DIFFERENCE_DETECTED` | Statistical coverage was sufficient; no group crossed its corrected threshold. |
| 1 | `VIOLATION` | At least one deterministic witness or statistical signal was found. |
| 2 | `ERROR` | Invalid inputs, failed adapter, storage error, or exceeded resource bound. |
| 3 | `INCONCLUSIVE` | No violation found, but at least one group lacks usable evidence. |
| 130 | `INTERRUPTED` | The operator interrupted the command. |

A zero exit describes the supplied experiment. It is not proof of universal
privacy. An imported cohort label is a claim by the collector, not an
authentication mechanism.

## Keep an audit history

```bash
purpose-trace ingest --policy examples/policy.json \
  --traces /tmp/purpose-leak/traces.jsonl --db /tmp/purpose.sqlite
purpose-trace audit --policy examples/policy.json --db /tmp/purpose.sqlite
purpose-trace health --db /tmp/purpose.sqlite
purpose-trace backup --db /tmp/purpose.sqlite --output /tmp/purpose-backup.sqlite
```

The database stores projections as SHA-256 hashes, sample identifiers, seeds,
cohorts, and policy definitions. Raw traces from replay remain in the campaign
directory with private file permissions. Hashes reduce accidental disclosure;
they are not encryption or anonymization.

## Python API

```python
import json
from purpose_trace import Policy, audit

with open("examples/policy.json") as stream:
    policy = Policy.from_dict(json.load(stream))
with open("/tmp/purpose-leak/traces.jsonl") as stream:
    result = audit(policy, (json.loads(line) for line in stream))
print(result["status"], result["coverage"])
```

## Operational scope

Version 1.0 targets bounded offline audits and single-host CI release gates.
It does not intercept live tool calls. A trusted collector must include every
policy-relevant disclosure and control agent version, prompts, tools, memory,
time-dependent data, and other environment inputs. Local replay isolates working
files and removes inherited secrets, but it **is not an OS sandbox**: execute
only trusted adapters, with synthetic data, or use an externally isolated host.

PurposeTrace complements [Agent Circuit Breaker](https://github.com/sagarchhatrala/agent-circuit-breaker):
ACB gates actions and trajectories; PurposeTrace compares executions before a
release. Neither tool makes omitted or unmediated behavior safe.

## Documentation

- [Policy and trace schema](docs/SCHEMA.md)
- [Statistical method and interpretation](docs/METHOD.md)
- [Integrating a real agent](docs/INTEGRATION.md)
- [Architecture and data flow](docs/ARCHITECTURE.md)
- [Operations, recovery, and release gates](docs/OPERATIONS.md)
- [Security and threat model](docs/SECURITY_MODEL.md)
- [Actual local validation record](docs/VALIDATION.md)
- [Releasing and publishing](docs/RELEASING.md)

[MIT license](LICENSE) · [Security reporting](SECURITY.md) · [Contributing](CONTRIBUTING.md)
