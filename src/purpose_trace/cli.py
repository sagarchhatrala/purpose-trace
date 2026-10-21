"""PurposeTrace command-line interface and stable automation exit codes."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys

from .audit import audit, audit_prepared
from .policy import Policy
from .records import prepare, read_traces
from .replay import run
from .report import html_report
from .store import Store
from .util import InputError, canonical, load, write_new


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="purpose-trace", description="Audit whether private context changes agent disclosures.")
    root.add_argument("--version", action="version", version="purpose-trace 1.0.0")
    sub = root.add_subparsers(dest="action", required=True)
    check = sub.add_parser("validate", help="validate and fingerprint a policy")
    check.add_argument("--policy", required=True)
    check = sub.add_parser("audit", help="compare supplied executions")
    check.add_argument("--policy", required=True)
    source = check.add_mutually_exclusive_group(required=True)
    source.add_argument("--traces")
    source.add_argument("--db")
    check.add_argument("--json", dest="json_output")
    check.add_argument("--html", dest="html_output")
    ingest = sub.add_parser("ingest", help="atomically import minimized trace evidence")
    for arg in ("policy", "traces", "db"):
        ingest.add_argument("--" + arg, required=True)
    health = sub.add_parser("health", help="check store integrity and evidence checksums")
    health.add_argument("--db", required=True)
    backup = sub.add_parser("backup", help="take a consistent SQLite backup")
    backup.add_argument("--db", required=True)
    backup.add_argument("--output", required=True)
    replay = sub.add_parser("run", help="run a trusted local adapter in a temporary workspace")
    for arg in ("policy", "manifest", "output"):
        replay.add_argument("--" + arg, required=True)
    replay.add_argument("--timeout", type=float, default=10)
    replay.add_argument("--max-output", type=int, default=1024 * 1024)
    replay.add_argument("--order-seed", type=int, default=0)
    replay.add_argument("command", nargs=argparse.REMAINDER)
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        policy = Policy.from_dict(load(args.policy)) if hasattr(args, "policy") else None
        if args.action == "validate":
            result = {"status": "valid", "fingerprint": policy.fingerprint,
                      "policy": json.loads(policy.encoded)}
        elif args.action == "audit":
            if args.traces:
                result = audit(policy, read_traces(args.traces))
            else:
                with Store(args.db) as store:
                    result = audit_prepared(policy, store.read(policy))
            if args.json_output:
                write_new(args.json_output, canonical(result) + "\n")
            if args.html_output:
                write_new(args.html_output, html_report(result))
        elif args.action == "ingest":
            records = [prepare(policy, trace) for trace in read_traces(args.traces)]
            if not records:
                raise InputError("cannot ingest empty evidence")
            with Store(args.db, create=True) as store:
                result = store.ingest(policy, records)
        elif args.action == "health":
            with Store(args.db) as store:
                result = store.health()
        elif args.action == "backup":
            with Store(args.db) as store:
                store.backup(args.output)
            result = {"status": "backed_up"}
        else:
            command = args.command[1:] if args.command[:1] == ["--"] else args.command
            result = run(policy, load(args.manifest), command, args.output,
                         timeout=args.timeout, max_output=args.max_output, order_seed=args.order_seed)
        print(canonical(result))
        return result.get("exit_code", 0)
    except (InputError, OSError, sqlite3.Error, RecursionError, OverflowError) as exc:
        print(canonical({"status": "ERROR", "error": str(exc), "exit_code": 2}), file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print('{"status":"INTERRUPTED","exit_code":130}', file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
