"""Single-host SQLite storage for minimized, policy-bound evidence."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from .policy import Policy
from .records import unique, validate_prepared
from .util import InputError, MAX_RECORDS, canonical, decode, digest

SCHEMA = """
CREATE TABLE IF NOT EXISTS policies (
    fingerprint TEXT PRIMARY KEY, body TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS records (
    policy TEXT NOT NULL REFERENCES policies(fingerprint),
    id TEXT NOT NULL, body TEXT NOT NULL, checksum TEXT NOT NULL,
    PRIMARY KEY(policy, id)
);
"""


class Store:
    def __init__(self, path: str | Path, *, create: bool = False):
        self.path = Path(path)
        if self.path.is_symlink():
            raise InputError("store path must not be a symlink")
        if create and not self.path.exists():
            try:
                fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
                os.close(fd)
            except FileExistsError:
                if self.path.is_symlink():
                    raise InputError("store path must not be a symlink")
        if not self.path.is_file():
            raise InputError("store does not exist; use ingest to create it")
        self.connection = sqlite3.connect(self.path, timeout=10)
        try:
            self.connection.execute("PRAGMA foreign_keys=ON")
            self.connection.execute("PRAGMA trusted_schema=OFF")
            with self.connection:
                self.connection.execute("BEGIN IMMEDIATE")
                version = self.connection.execute("PRAGMA user_version").fetchone()[0]
                if version == 0 and create:
                    if self.connection.execute("SELECT name FROM sqlite_master").fetchone():
                        raise InputError("refusing to initialize an unrelated database")
                    for statement in SCHEMA.split(";"):
                        if statement.strip():
                            self.connection.execute(statement)
                    self.connection.execute("PRAGMA user_version=1")
                elif version != 1:
                    raise InputError("unsupported or uninitialized store schema")
            self.connection.execute("PRAGMA journal_mode=WAL")
            self.connection.execute("PRAGMA synchronous=FULL")
        except BaseException:
            self.connection.close()
            raise

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.connection.close()

    def ingest(self, policy: Policy, records: list[dict]) -> dict:
        records = unique(records)
        inserted = 0
        with self.connection:
            self.connection.execute("BEGIN IMMEDIATE")
            self.connection.execute("INSERT OR IGNORE INTO policies VALUES (?, ?)",
                                    (policy.fingerprint, policy.encoded))
            for record in records:
                validate_prepared(policy, record)
                old = self.connection.execute("SELECT body FROM records WHERE policy=? AND id=?",
                                              (policy.fingerprint, record["id"])).fetchone()
                body = canonical(record)
                if old and old[0] != body:
                    raise InputError("trace id conflict; entire import rolled back")
                if not old:
                    self.connection.execute("INSERT INTO records VALUES (?, ?, ?, ?)",
                                            (policy.fingerprint, record["id"], body, digest(record)))
                    inserted += 1
            count = self.connection.execute("SELECT COUNT(*) FROM records WHERE policy=?",
                                            (policy.fingerprint,)).fetchone()[0]
            if count > MAX_RECORDS:
                raise InputError("store exceeds per-policy record limit; import rolled back")
        return {"inserted": inserted, "duplicates": len(records) - inserted, "policy_records": count}

    def read(self, policy: Policy) -> list[dict]:
        stored = self.connection.execute("SELECT body FROM policies WHERE fingerprint=?",
                                         (policy.fingerprint,)).fetchone()
        if not stored or stored[0] != policy.encoded:
            raise InputError("policy absent from store or policy integrity failure")
        rows = self.connection.execute("SELECT id, body, checksum FROM records WHERE policy=? ORDER BY id LIMIT ?",
                                       (policy.fingerprint, MAX_RECORDS + 1)).fetchall()
        if len(rows) > MAX_RECORDS:
            raise InputError("stored evidence exceeds record limit")
        result = []
        for trace_id, body, checksum in rows:
            record = decode(body)
            validate_prepared(policy, record)
            if digest(record) != checksum or record.get("id") != trace_id or record.get("policy") != policy.fingerprint:
                raise InputError("stored evidence checksum or identity mismatch")
            result.append(record)
        return result

    def health(self) -> dict:
        integrity = self.connection.execute("PRAGMA integrity_check").fetchall()
        foreign = self.connection.execute("PRAGMA foreign_key_check").fetchall()
        if integrity != [("ok",)] or foreign:
            raise InputError("SQLite integrity check failed")
        total = 0
        for fingerprint, body in self.connection.execute("SELECT fingerprint, body FROM policies"):
            policy = Policy.from_dict(decode(body))
            if policy.fingerprint != fingerprint:
                raise InputError("stored policy checksum mismatch")
            total += len(self.read(policy))
        return {"status": "ok", "schema_version": 1, "records": total,
                "integrity": "SQLite and unkeyed content checksums verified"}

    def backup(self, target: str | Path) -> None:
        self.health()
        fd = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(fd)
        destination = sqlite3.connect(target)
        try:
            self.connection.backup(destination)
        except BaseException:
            destination.close()
            Path(target).unlink(missing_ok=True)
            raise
        finally:
            destination.close()
