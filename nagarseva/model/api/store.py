"""SQLite records for the local demo and consented pilots; no generated field data."""

from __future__ import annotations

from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import sqlite3
from typing import Any, Callable, Iterator


class RecordStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("CREATE TABLE IF NOT EXISTS complaints (id TEXT PRIMARY KEY, receipt_hash TEXT NOT NULL, body TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS observations (id TEXT PRIMARY KEY, pocket_id TEXT NOT NULL, body TEXT NOT NULL)")
            db.execute("CREATE INDEX IF NOT EXISTS observations_pocket ON observations(pocket_id)")
            db.execute("CREATE TABLE IF NOT EXISTS evaluations (id TEXT PRIMARY KEY, body TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS commitments (pocket_id TEXT NOT NULL, service TEXT NOT NULL, body TEXT NOT NULL, PRIMARY KEY(pocket_id, service))")
            db.execute("CREATE TABLE IF NOT EXISTS locations (id TEXT PRIMARY KEY, body TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS public_cache (key TEXT PRIMARY KEY, body TEXT NOT NULL)")

    def cached_public_data(self, key: str) -> dict | None:
        with self.connection() as db:
            row = db.execute("SELECT body FROM public_cache WHERE key = ?", (key,)).fetchone()
        return json.loads(row[0]) if row else None

    def cache_public_data(self, key: str, record: dict) -> None:
        with self.connection(write=True) as db:
            db.execute("INSERT INTO public_cache VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET body = excluded.body", (key, json.dumps(record, allow_nan=False)))

    @contextmanager
    def connection(self, write: bool = False) -> Iterator[sqlite3.Connection]:
        db = sqlite3.connect(self.path, timeout=15)
        try:
            if write:
                db.execute("BEGIN IMMEDIATE")
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def create_complaint(self, record: dict, receipt: str) -> dict:
        with self.connection(write=True) as db:
            db.execute("INSERT INTO complaints VALUES (?, ?, ?)", (record["complaint_id"], hashlib.sha256(receipt.encode()).hexdigest(), json.dumps(record)))
        return record

    def complaint(self, complaint_id: str, db: sqlite3.Connection | None = None) -> dict | None:
        if db is None:
            with self.connection() as connection:
                return self.complaint(complaint_id, connection)
        row = db.execute("SELECT body FROM complaints WHERE id = ?", (complaint_id,)).fetchone()
        return json.loads(row[0]) if row else None

    def receipt_matches(self, complaint_id: str, receipt: str) -> bool:
        import secrets
        with self.connection() as db:
            row = db.execute("SELECT receipt_hash FROM complaints WHERE id = ?", (complaint_id,)).fetchone()
        return bool(row and secrets.compare_digest(row[0], hashlib.sha256(receipt.encode()).hexdigest()))

    def complaints(self) -> list[dict]:
        with self.connection() as db:
            rows = db.execute("SELECT body FROM complaints ORDER BY rowid DESC").fetchall()
        return [json.loads(row[0]) for row in rows]

    def change_complaint(self, complaint_id: str, change: Callable[[dict, sqlite3.Connection], dict]) -> dict | None:
        with self.connection(write=True) as db:
            record = self.complaint(complaint_id, db)
            if record is None:
                return None
            record = change(record, db)
            db.execute("UPDATE complaints SET body = ? WHERE id = ?", (json.dumps(record), complaint_id))
            return record

    def save_observation(self, record: dict, db: sqlite3.Connection | None = None) -> dict:
        if db is None:
            with self.connection(write=True) as connection:
                return self.save_observation(record, connection)
        db.execute("INSERT INTO observations VALUES (?, ?, ?) ON CONFLICT(id) DO UPDATE SET body = excluded.body", (record["observation_id"], record["pocket_id"], json.dumps(record)))
        return record

    def observations(self, pocket_id: str | None = None, db: sqlite3.Connection | None = None) -> list[dict]:
        if db is None:
            with self.connection() as connection:
                return self.observations(pocket_id, connection)
        query = "SELECT body FROM observations"
        rows = db.execute(query + (" WHERE pocket_id = ?" if pocket_id else "") + " ORDER BY rowid DESC", (pocket_id,) if pocket_id else ()).fetchall()
        return [json.loads(row[0]) for row in rows]

    def save_evaluation(self, record: dict) -> dict:
        with self.connection(write=True) as db:
            db.execute("INSERT INTO evaluations VALUES (?, ?)", (record["evaluation_id"], json.dumps(record)))
        return record

    def evaluations(self) -> list[dict[str, Any]]:
        with self.connection() as db:
            rows = db.execute("SELECT body FROM evaluations ORDER BY rowid DESC").fetchall()
        return [json.loads(row[0]) for row in rows]

    def commitments(self, pocket_id: str | None = None) -> list[dict]:
        with self.connection() as db:
            rows = db.execute("SELECT body FROM commitments" + (" WHERE pocket_id = ?" if pocket_id else ""), (pocket_id,) if pocket_id else ()).fetchall()
        return [json.loads(row[0]) for row in rows]

    def save_commitment(self, record: dict) -> dict:
        with self.connection(write=True) as db:
            previous = db.execute("SELECT body FROM commitments WHERE pocket_id = ? AND service = ?", (record["pocket_id"], record["service"])).fetchone()
            record["history"] = (json.loads(previous[0])["history"] if previous else []) + [{"at": record["created_at"], "target": record["target"], "standard_source": record["standard_source"], "approved_by": record["approved_by"]}]
            db.execute("INSERT INTO commitments VALUES (?, ?, ?) ON CONFLICT(pocket_id, service) DO UPDATE SET body = excluded.body", (record["pocket_id"], record["service"], json.dumps(record)))
        return record

    def locations(self) -> list[dict]:
        with self.connection() as db:
            rows = db.execute("SELECT body FROM locations ORDER BY id").fetchall()
        return [json.loads(row[0]) for row in rows]

    def save_location(self, record: dict) -> dict:
        with self.connection(write=True) as db:
            db.execute("INSERT INTO locations VALUES (?, ?)", (record["pocket_id"], json.dumps(record)))
        return record
