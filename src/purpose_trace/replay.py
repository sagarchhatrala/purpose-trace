"""Run trusted local adapters in temporary working directories with bounded I/O."""

from __future__ import annotations

import hashlib
import math
import os
import random
import selectors
import shutil
import signal
import subprocess
import tempfile
import time
import uuid
from pathlib import Path

from .audit import audit
from .policy import Policy
from .records import identifier
from .report import html_report
from .util import (InputError, MAX_FILE, MAX_RECORD, canonical, decode, digest,
                   fields, integer, validate_json, write_new)


def _kill(process: subprocess.Popen) -> None:
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass


def _invoke(command: list[str], request: dict, directory: str,
            timeout: float, max_output: int) -> dict:
    import resource

    def limits():
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        resource.setrlimit(resource.RLIMIT_FSIZE, (8 * 1024 * 1024, 8 * 1024 * 1024))
        resource.setrlimit(resource.RLIMIT_NOFILE, (128, 128))
        seconds = max(1, math.ceil(timeout))
        resource.setrlimit(resource.RLIMIT_CPU, (seconds, seconds + 1))

    # HOME and working directory both point to a new, disposable directory.
    environment = {"PATH": os.defpath, "HOME": directory, "TMPDIR": directory,
                   "LANG": "C.UTF-8", "PYTHONHASHSEED": str(request["seed"]),
                   "PURPOSETRACE_SEED": str(request["seed"])}
    payload = (canonical(request) + "\n").encode()
    with tempfile.TemporaryFile(dir=directory) as stdin:
        stdin.write(payload)
        stdin.seek(0)
        process = subprocess.Popen(command, stdin=stdin, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, cwd=directory, env=environment,
                                   start_new_session=True, preexec_fn=limits)
        output = bytearray()
        stderr_bytes = 0
        deadline = time.monotonic() + timeout
        selector = selectors.DefaultSelector()
        try:
            for stream, label in ((process.stdout, "stdout"), (process.stderr, "stderr")):
                os.set_blocking(stream.fileno(), False)
                selector.register(stream, selectors.EVENT_READ, label)
            while selector.get_map():
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise InputError("adapter timed out; process group terminated")
                for key, _ in selector.select(min(remaining, 0.1)):
                    chunk = os.read(key.fileobj.fileno(), 65536)
                    if not chunk:
                        selector.unregister(key.fileobj)
                        continue
                    if key.data == "stdout":
                        output.extend(chunk)
                    else:
                        stderr_bytes += len(chunk)
                    if len(output) + stderr_bytes > max_output:
                        raise InputError("adapter exceeded combined stdout/stderr limit")
            remaining = deadline - time.monotonic()
            try:
                code = process.wait(timeout=max(0.001, remaining))
            except subprocess.TimeoutExpired as exc:
                raise InputError("adapter timed out") from exc
            if code:
                raise InputError(f"adapter exited with code {code}; raw stderr withheld")
            value = decode(bytes(output), max_output)
            if not isinstance(value, dict):
                raise InputError("adapter stdout must contain exactly one JSON object")
            return value
        finally:
            _kill(process)
            process.wait()
            selector.close()
            process.stdout.close()
            process.stderr.close()


def run(policy: Policy, manifest: dict, command: list[str], output: str | Path,
        *, timeout: float = 10, max_output: int = MAX_RECORD, order_seed: int = 0) -> dict:
    if os.name != "posix":
        raise InputError("local replay requires macOS or Linux; file audits work on all platforms")
    validate_json(manifest)
    manifest = decode(canonical(manifest))
    fields(manifest, {"version", "cohort", "cases", "seeds", "repeats"})
    if type(manifest["version"]) is not int or manifest["version"] != 1:
        raise InputError("unsupported manifest version")
    identifier(manifest["cohort"], "cohort")
    if len(manifest["cohort"]) > 120:
        raise InputError("manifest cohort must be at most 120 characters")
    if not isinstance(manifest["cases"], list) or not 2 <= len(manifest["cases"]) <= 64:
        raise InputError("manifest requires 2 to 64 cases")
    names = set()
    for case in manifest["cases"]:
        fields(case, {"name", "input"})
        identifier(case["name"], "case name")
        if not isinstance(case["input"], dict):
            raise InputError("case input must be an object")
        if case["name"] in names:
            raise InputError("duplicate case names")
        names.add(case["name"])
        policy.project_input(case["input"])
    seeds = manifest["seeds"]
    if not isinstance(seeds, list) or not 1 <= len(seeds) <= 1000:
        raise InputError("manifest seeds must contain 1 to 1000 unique integers")
    for seed in seeds:
        integer(seed, "seed", 0, 2**32 - 1)
    if len(set(seeds)) != len(seeds):
        raise InputError("duplicate manifest seeds")
    repeats = integer(manifest["repeats"], "repeats", 1, 100)
    if policy.mode == "deterministic" and repeats < policy.min_repeats:
        raise InputError("manifest repeats are below policy minimum")
    if policy.mode == "statistical" and repeats != 1:
        raise InputError("statistical replay requires repeats=1 and independent samples")
    if len(seeds) * repeats * len(names) > 2000:
        raise InputError("manifest exceeds 2000 adapter executions")
    if not math.isfinite(timeout) or not 0.1 <= timeout <= 600:
        raise InputError("timeout must be between 0.1 and 600 seconds")
    integer(max_output, "max_output", 1024, MAX_RECORD)
    integer(order_seed, "order_seed", 0, 2**32 - 1)
    destination = Path(output)
    if destination.exists() or destination.is_symlink():
        raise InputError("output directory already exists; choose a new directory")
    if not destination.parent.is_dir():
        raise InputError("output parent directory does not exist")
    if not command:
        raise InputError("provide an adapter command after --")
    executable = shutil.which(command[0])
    if not executable:
        raise InputError("adapter executable not found")
    # Preserve interpreter symlinks: resolving a venv's python loses its site-packages.
    command = [str(Path(executable).absolute()), *command[1:]]
    artifacts = {}
    for i, arg in enumerate(command):
        path = Path(arg)
        if path.is_file():
            command[i] = str(path.absolute())
            if path.stat().st_size > 128 * 1024 * 1024:
                raise InputError("adapter command file exceeds fingerprint limit")
            with path.open("rb") as stream:
                artifacts[str(i)] = hashlib.file_digest(stream, "sha256").hexdigest()
    command_hash = digest({"command": command, "files": artifacts})
    cohort = manifest["cohort"] + ":" + command_hash[:24]
    campaign_id = uuid.uuid4().hex
    jobs = [(case, seed, repeat) for case in manifest["cases"]
            for seed in seeds for repeat in range(repeats)]
    rng = random.Random(order_seed)
    if policy.mode == "statistical":
        # Seed values are independent across contexts; seed count selects sample count.
        independent = rng.sample(range(2**32), len(jobs))
        jobs = [(case, independent[i], repeat) for i, (case, _, repeat) in enumerate(jobs)]
    rng.shuffle(jobs)
    traces = []
    encoded = []
    size = 0
    started = time.monotonic()
    for index, (case, seed, _) in enumerate(jobs):
        trace_id = f"{campaign_id}:{index}"
        with tempfile.TemporaryDirectory(prefix="purposetrace-run-") as directory:
            result = _invoke(command, {"input": case["input"], "seed": seed},
                             directory, timeout, max_output)
        trace = {"id": trace_id, "cohort": cohort, "seed": seed,
                 "input": case["input"], "output": result}
        policy.project_output(result)
        line = canonical(trace) + "\n"
        size += len(line.encode())
        if size > MAX_FILE:
            raise InputError("campaign trace output exceeds byte limit")
        traces.append(trace)
        encoded.append(line)
    report = audit(policy, traces)
    receipt = {"schema_version": 1, "campaign_id": campaign_id, "cohort": cohort,
               "command_hash": command_hash, "command_file_hashes": artifacts,
               "manifest_hash": digest(manifest), "policy_hash": policy.fingerprint,
               "executions": len(traces), "order_seed": order_seed,
               "elapsed_seconds": round(time.monotonic() - started, 4),
               "timeout_seconds": timeout, "max_output_bytes": max_output,
               "isolation": "temporary cwd, minimal environment, process group and resource limits; not an OS sandbox"}
    destination.mkdir(mode=0o700)
    write_new(destination / "INCOMPLETE", "Do not consume this campaign until completion.\n")
    write_new(destination / "traces.jsonl", "".join(encoded))
    write_new(destination / "policy.json", policy.encoded + "\n")
    write_new(destination / "receipt.json", canonical(receipt) + "\n")
    write_new(destination / "report.json", canonical(report) + "\n")
    write_new(destination / "report.html", html_report(report))
    (destination / "INCOMPLETE").unlink()
    return report
