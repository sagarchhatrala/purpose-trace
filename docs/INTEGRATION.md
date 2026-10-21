# Integrating an agent

## Choose a decision worth protecting

Start with a narrow externally observable decision: a recipient, a support
queue, a set of recommended resources, a price bucket, or a sequence of messages.
Write down which input information is permitted to influence that decision.
Represent it as structured JSON before adding an agent framework adapter.

For example, support tier and queue availability may be authorized inputs,
while a confidential account investigation must not influence routing. Build
at least two worlds with identical tier, availability, and request, changing
only the protected field. Add other authorized configurations as separate
comparison groups.

## Implement the stdin/stdout adapter

```python
import json
import sys

request = json.load(sys.stdin)
world = request["input"]
seed = request["seed"]

# Instantiate a fresh agent with synthetic tools and fixed configuration.
# Do not let this replay send real messages or make production changes.
result = run_your_agent(world, seed=seed)

# Include the complete relevant disclosure, not just a convenient final value.
json.dump({"recipient": result.recipient,
           "queue": result.queue,
           "wording": result.message}, sys.stdout)
```

`run_your_agent` is your integration point, not an exported PurposeTrace API.
Use the supplied working routers as complete runnable adapters. Install adapter
dependencies into its own environment, then pass the absolute interpreter and
script paths. The runner starts it with a fresh working directory, so resolve
fixture paths relative to the adapter file or include fixture data in the input.

Replay does not forward inherited API tokens or proxy settings. For a hosted
agent, use a separately controlled collector with a synthetic environment and
export traces for `audit`. This keeps service credentials and production tools
outside the local replay interface. Do not add credentials to manifest inputs,
which are written to raw campaign traces.

## Control the environment

Pin model version, prompt, dependencies, tool responses, time inputs, and initial
memory. Reset mutable state for every execution. Record their version/digest
in `cohort`. The runner fingerprints the executable and direct argument files;
it cannot discover every imported dependency or remote configuration change.
Changing the cohort intentionally prevents comparisons across those changes.

In deterministic mode, repeat every context under the same seeds. Use statistical
mode when the workflow intentionally remains randomized. A server ignoring your
seed does not become deterministic merely because the record includes one.

Keep output completeness under trusted host control. A model must not choose
which events the audit sees. Capture message history, delegated outputs,
recipients, attachments, and intermediate disclosures when they affect the
policy. Use observed arrays to preserve order, or explicitly mark a selection
as unordered when the policy permits that normalization.

## Import existing executions

Map each complete execution to the five-field trace envelope described in
[SCHEMA.md](SCHEMA.md). Generate unique IDs at execution time. Keep retries with
their original ID if they represent retransmission of the same evidence;
separate actual executions need new IDs. Import all records atomically.

```bash
purpose-trace ingest --policy policy.json --traces executions.jsonl --db audit.sqlite
purpose-trace audit --policy policy.json --db audit.sqlite --html review.html
```

## Combine with an execution gate

Use an action gate inside the runtime for individual operations. Use PurposeTrace
in the deployment pipeline to compare complete executions of a candidate
workflow. The release job should proceed only on exit 0. Exit 1 requires fixing
or investigating a disclosure dependency; exit 2 requires correcting the failed
operation; exit 3 requires improving the experiment.

This composition gives each tool a clear role. PurposeTrace does not mint runtime
authorizations or intercept calls that bypass your existing gate.

## Reduce the dependency by construction

Where practical, construct final disclosures from the authorized projection
alone. Keep private context out of the component selecting the queue, recipient,
or output. Audit that architecture with counterfactual inputs after changing
models, prompts, tools, or policy. It is easier to review a small authorized
projection than to rely on instructions asking a model to forget what it read.
