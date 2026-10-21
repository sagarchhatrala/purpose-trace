# Release and publication

## Build and verify

```bash
python -m pip install build
python -m build
python -m venv /tmp/purpose-release-check
/tmp/purpose-release-check/bin/pip install --no-deps dist/purpose_trace-1.0.0-py3-none-any.whl
/tmp/purpose-release-check/bin/purpose-trace run \
  --policy examples/policy.json --manifest examples/manifest.json \
  --output /tmp/purpose-release-campaign \
  -- /tmp/purpose-release-check/bin/python examples/private_router.py
```

Use a new temporary directory for each release. Exercise the deliberately leaky
adapter and expect exit 1, as well as relevant storage/failure workflows. Update
the validation record with what actually ran and preserve the exact wheel hash.
The release workflow builds artifacts on manual dispatch; it does not silently
publish a package to PyPI.

## GitHub repository

Publication requires an authenticated GitHub session and network access for Git.
Create `sagarchhatrala/purpose-trace` as a public repository, push `main` without
force, inspect the installed-package workflow, and attach the wheel, source
archive, and checksums to a versioned GitHub release after validation. Do not
claim PyPI availability unless a separate package publication actually succeeds.

## Portfolio route

The project page is the `site/` directory. Its intended URL is:

`https://sagarchhatrala.github.io/purpose-trace/`

Copy its seven public files into `purpose-trace/` in the portfolio repository.
The portfolio's build allowlist, route checker, and sitemap must include the new
route. The homepage and the two existing project pages need no changes.

For the initial publication, the companion portfolio checkout contains the
complete prepared change. Because its baseline was downloaded as an archive,
**do not push its independently initialized baseline as the website's history**.
Export the prepared change with `git diff --binary HEAD~1 HEAD` after committing
the route, then apply it to a fresh clone of the actual website repository with
`git apply --check` followed by `git apply`. Commit only that patch and push the
existing branch normally. A patch conflict requires reconciliation against the
current upstream files, not a force push.

Run the portfolio's existing `scripts/build_site.py` and `scripts/check_site.py`
before pushing. The Pages workflow deploys the built `_site` artifact. Verify
the new URI and both existing project URIs after deployment. Browser-check the
three strategy buttons, recorded report, local JSON report import, malformed
file handling, copy button, keyboard navigation, and narrow viewport layout.

## Current session status

The public repository and portfolio page were published on 2026-10-22,
Asia/Kolkata. Installed-package CI passed on Python 3.11–3.15; preview and live
Chromium checks, Pages deployment, and the release-artifact build passed. See
[the validation record](VALIDATION.md) for commits, run links, and limitations.

Publication used GitHub MCP because shell Git networking remained blocked. MCP
created new commits from the verified local file contents. The portfolio update
preserved upstream history and its complete Git tree matched the tested change.
The original local project history and independently initialized portfolio
snapshot therefore have different commit IDs from their published counterparts.
Use a fresh clone of each public repository for subsequent Git development;
retain the original delivery bundle as historical evidence.

The release workflow currently provides downloadable Actions artifacts for 30
days. A versioned GitHub release and PyPI publication have not been performed.
