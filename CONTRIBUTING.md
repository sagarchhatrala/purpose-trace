# Contributing

Keep changes focused on accurate, reviewable execution comparisons. Discuss
schema or interpretation changes before making incompatible modifications.
Use Python 3.11-compatible standard-library code for the core. Avoid runtime
dependencies and integrations that silently transmit evidence.

Install a checkout in a virtual environment. Exercise changes through actual
CLI workflows: run both example adapters, inspect reports, import evidence,
check deduplication and backup, and reproduce relevant failure paths with
synthetic data in temporary directories. Record what actually ran and any
limitations; do not describe an unexecuted scenario as verified.

The repository deliberately has no generated unit-test suite. Its CI runs the
installed package through real example campaigns and storage operations. Supply
reproduction commands and evidence for bug fixes. Preserve stable exit codes,
fail-closed validation, data minimization, and explicit statistical assumptions.

Run `python -m build` to build release artifacts. Install the resulting wheel
into a second clean environment and repeat the relevant workflows before a
release. Update schema, operations, and validation documentation alongside changes.
