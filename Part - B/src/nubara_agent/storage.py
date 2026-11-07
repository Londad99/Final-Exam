"""Durable confirmation and write claims; never store conversations or contacts."""
import json
import sqlite3
import uuid
from contextlib import contextmanager
from pathlib import Path


class Store:
    def __init__(self, path: str | Path):
        self.path = str(path)
        with self.connection() as db:
            db.execute("CREATE TABLE IF NOT EXISTS offers (token TEXT PRIMARY KEY, owner TEXT, payload TEXT)")
            db.execute("CREATE TABLE IF NOT EXISTS writes (key TEXT PRIMARY KEY, status TEXT, payload TEXT)")

    @contextmanager
    def connection(self):
        with sqlite3.connect(self.path, timeout=15) as db:
            yield db

    def offer(self, owner: str, payload: dict) -> str:
        token = uuid.uuid4().hex
        with self.connection() as db:
            db.execute("INSERT INTO offers VALUES (?, ?, ?)", (token, owner, json.dumps(payload)))
        return token

    def get_offer(self, token: str, owner: str) -> dict:
        with self.connection() as db:
            row = db.execute("SELECT payload FROM offers WHERE token=? AND owner=?", (token, owner)).fetchone()
        if not row:
            raise ValueError("Unknown confirmation token")
        return json.loads(row[0])

    def claim(self, key: str) -> tuple[bool, dict]:
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT status,payload FROM writes WHERE key=?", (key,)).fetchone()
            if row:
                return False, {"status": row[0], **json.loads(row[1])}
            db.execute("INSERT INTO writes VALUES (?, 'INDETERMINATE', '{}')", (key,))
        return True, {"status": "INDETERMINATE"}

    def finish(self, key: str, status: str, payload: dict):
        with self.connection() as db:
            db.execute("UPDATE writes SET status=?,payload=? WHERE key=?", (status, json.dumps(payload), key))

    def lookup(self, key: str) -> dict | None:
        with self.connection() as db:
            row = db.execute("SELECT status,payload FROM writes WHERE key=?", (key,)).fetchone()
        return {"status": row[0], **json.loads(row[1])} if row else None
