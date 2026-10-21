# Comparison method

## What is held constant

An input projection combines public fields and context the task authorizes.
Executions are grouped by its canonical hash and the trusted cohort label.
Deterministic mode additionally matches the random seed. Private input fields
identify the alternative protected contexts within a group.

The output projection keeps only explicitly observed fields, after declared
array-order normalization. A useful projection includes all channels the
recipient can interpret: recipient, destinations, selection, order where
meaningful, labels, and disclosure granularity. Excluding a channel excludes it
from the claim. Empty and undeclared fields are checked rather than silently
discarded.

## Deterministic comparison

Every group needs at least two protected contexts and `min_repeats` distinct
executions per context. If one context produces multiple observations at the
same seed, the entire group is `INCONCLUSIVE` (`unstable_within_context`). A
repeatable difference between contexts yields a two-execution witness. If all
observations agree, the group is `CONSISTENT`.

This is an observed violation of the deterministic contract. Causal attribution
to the changed private context depends on the experiment controlling everything
else. Two repeats can expose instability; they cannot prove determinism. Frozen
inputs, fresh memory, stable tools, deterministic adapters, and versioned
dependencies remain the operator's responsibility.

## Statistical comparison

Randomized systems may legitimately emit different outputs with identical
inputs. Statistical mode compares **distributions**, without treating every
different output as a violation.

For context distributions P and Q over canonical observations, empirical total
variation is `0.5 * sum(abs(P[y] - Q[y]))`. The group statistic is the maximum
pairwise total variation across all protected contexts. It lies in [0, 1].

The engine pools observations and randomly reassigns them to context labels,
preserving each sample count. For B permutations, the Monte Carlo p-value is
`(1 + count(permuted_statistic >= observed_statistic)) / (B + 1)`. Including the
observed configuration prevents a false zero p-value. A reproducible PRNG seed
is derived from the policy and group; stable trace IDs fix observation order.

Each group is judged at `alpha / total_group_count` (Bonferroni correction).
The maximum-pair statistic handles the multiple context comparisons within a
group. Groups that lack evidence still count in the across-group correction.
If `1 / (B + 1)` exceeds the corrected threshold, the group is inconclusive:
the chosen permutation count could not detect even the strongest result.

Every context must meet `min_samples`. Seeds must be unique across a statistical
group to avoid treating repeated seeded executions as independent samples.
Distinct seeds are a basic collection check, not proof of independence. Samples
must be exchangeable under the null: no context-dependent model versions,
time drift, shared mutable memory, different prompts, or interdependent workers.
Randomized interleaving reduces ordering confounds but does not eliminate them.

`VIOLATION` means statistically significant association under those assumptions.
It is evidence to investigate, not a proof of causal leakage. The reported TV is
an empirical effect size, not an unbiased population estimate. The tool does
not estimate power or confidence bounds, and does not implement sequential
testing. Predetermine the sample size and policy; repeatedly peeking at results
or selecting projections after seeing them invalidates the stated threshold.

High-cardinality free text can produce unique categories for every run. A large
TV may then be typical under permutation and produce no significant result.
Prefer reviewed structured observations. Do not convert arbitrary wording into
a security claim without checking it against the actual disclosure policy.

## Aggregation and bounds

Any violation makes the audit fail with exit 1, even if other groups are
inconclusive. Otherwise any inconclusive group produces exit 3. A zero exit
requires every supplied group to have usable evidence.

The engine accepts at most 1024 groups and 16 contexts per group. Statistical
work is bounded to 50 million sample permutations (`records * permutations`).
These are hard rejection limits, not silent truncation. Scope an experiment to
a coherent, preregistered family of comparisons; splitting one family merely to
avoid its correction creates misleading significance claims.

## Limits of observation

Finite clean observations never establish universal privacy. Unknown contexts,
unobserved channels, rare behavior, missing traces, policy mistakes, and changed
deployments remain outside the result. The engine performs no semantic judgment,
prompt classification, model call, automatic declassification, or live blocking.
