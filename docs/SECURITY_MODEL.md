# Security and threat model

## Objective

Detect observable dependence on protected context in a bounded set of agent
executions that should share the same authorized inputs. Supply inspectable
evidence and a dependable nonzero exit when evaluation fails or is incomplete.

## Trusted components

- The human-reviewed policy and its input/output projections.
- The collector's completeness, truthful IDs, seeds, and cohort definitions.
- The host, interpreter, PurposeTrace package, and local storage directory.
- The adapter and any service it calls, for the accuracy of collected evidence.
- Experiment controls and statistical exchangeability assumptions.

A model must not write its own policy or decide which disclosures to omit.
An attacker able to fabricate traces can fabricate a clean audit. Cryptographic
hashing does not authenticate the collector.

## Defensive behavior

The parser bounds bytes, nodes, nesting, numeric range, groups, samples, and
statistical work. Duplicate keys, missing fields, unclassified inputs and outputs,
conflicting trace identities, policy mismatch, and unrecognized schema versions
fail. Reports escape all data and contain no JavaScript or external resources.
Database statements use parameters; imports use transactions. Existing output
files are never replaced by a successful write operation.

The replay runner never uses a shell. It removes inherited credentials and
uses temporary working directories with bounded stdout/stderr, a wall deadline,
process-group cleanup, and POSIX resource limits. Raw adapter stderr is not
echoed into error messages. It executes only commands selected by the operator.

## Explicit non-goals

PurposeTrace is not a sandbox, live authorization gate, prompt-injection detector,
data-loss-prevention system, or proof that a model will behave safely in unseen
situations. Temporary directories do not prevent absolute-path access or network
calls. A hostile process can escape a process group, and there is no portable
memory or descendant-process containment guarantee. Use a real externally
enforced isolation boundary for untrusted code.

Checksums detect accidental mutation, not an adversary rewriting both data and
checksum. SQLite is neither immutable nor distributed. The tool does not detect
database rollback, authenticate a report, or establish that all real executions
were collected. Retain trusted evidence digests separately if an operational
workflow needs external verification of archived artifacts.

Reports omit raw values but contain hashes, paths, identifiers, and counts. Hashes
of low-entropy data are vulnerable to guessing. The policy itself can disclose
sensitive concepts through its paths. Raw replay traces preserve complete input
and output values. Apply normal sensitive-data handling to every artifact.

## Remaining analytical risks

A bad output abstraction can miss an actual channel or invent a false signal.
Uncontrolled environment differences can look like private-context dependence.
Too few observations can miss rare behavior. High-cardinality categories reduce
statistical power. Adaptive repeated testing invalidates the nominal p-value.
The documentation and report include these interpretation boundaries because
they affect the meaning of a successful release gate.
