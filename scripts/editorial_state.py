"""Durable state for zero-price editorial requests; stores no credentials."""
from contextlib import contextmanager
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
import uuid


class EditorialState:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS checkpoints (
                    name TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS cloudflare_usage (
                    id TEXT PRIMARY KEY,
                    day TEXT NOT NULL,
                    brand TEXT NOT NULL,
                    model TEXT NOT NULL,
                    reserved INTEGER NOT NULL,
                    measured INTEGER
                );
                CREATE INDEX IF NOT EXISTS cloudflare_usage_day ON cloudflare_usage(day);
                CREATE TABLE IF NOT EXISTS queued_reviews (
                    id TEXT PRIMARY KEY,
                    brand TEXT NOT NULL,
                    role TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    updated TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS request_days (
                    day TEXT PRIMARY KEY,
                    requests INTEGER NOT NULL
                );
            """)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path)
        try:
            with db:
                yield db
        finally:
            db.close()

    def read(self, name):
        with self.connect() as db:
            row = db.execute("SELECT value FROM checkpoints WHERE name=?", (name,)).fetchone()
        return json.loads(row[0]) if row else None

    def save(self, name, value):
        with self.connect() as db:
            db.execute("INSERT OR IGNORE INTO checkpoints VALUES (?, ?)",
                       (name, json.dumps(value, ensure_ascii=False)))

    def reserve(self, daily_limit):
        # Count attempts before sending them, even if they time out or are rejected.
        day = datetime.now(timezone.utc).date().isoformat()
        with self.connect() as db:
            row = db.execute("""
                INSERT INTO request_days VALUES (?, 1)
                ON CONFLICT(day) DO UPDATE SET requests=requests+1
                WHERE requests < ?
                RETURNING requests
            """, (day, daily_limit)).fetchone()
        return row[0] if row else None


    def reserve_cloudflare(self, brand, model, neurons, daily_limit, *, now=None):
        day = (now or datetime.now(timezone.utc)).astimezone(timezone.utc).date().isoformat()
        uid = uuid.uuid4().hex
        with self.connect() as db:
            row = db.execute("""
                INSERT INTO cloudflare_usage (id, day, brand, model, reserved)
                SELECT ?, ?, ?, ?, ?
                WHERE (SELECT coalesce(sum(max(reserved, coalesce(measured, 0))), 0)
                       FROM cloudflare_usage WHERE day=?) + ? <= ?
                RETURNING id
            """, (uid, day, brand, model, neurons, day, neurons, daily_limit)).fetchone()
        return row[0] if row else None

    def finish_cloudflare(self, uid, measured):
        if measured is not None:
            with self.connect() as db:
                db.execute("UPDATE cloudflare_usage SET measured=? WHERE id=?", (measured, uid))

    def cloudflare_report(self):
        with self.connect() as db:
            rows = db.execute("""
                SELECT day, brand, model, count(*), sum(reserved), sum(measured), count(measured)
                FROM cloudflare_usage GROUP BY day, brand, model ORDER BY day, brand, model
            """).fetchall()
        fields = ("day", "brand", "model", "attempts", "reserved_neurons", "estimated_used_neurons", "metered_attempts")
        return [dict(zip(fields, row), usd=0) for row in rows]

    def queue_review(self, uid, brand, role, reason):
        with self.connect() as db:
            db.execute("""
                INSERT INTO queued_reviews VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET reason=excluded.reason, updated=excluded.updated
            """, (uid, brand, role, reason, datetime.now(timezone.utc).isoformat()))

    def clear_review(self, uid):
        with self.connect() as db:
            db.execute("DELETE FROM queued_reviews WHERE id=?", (uid,))
