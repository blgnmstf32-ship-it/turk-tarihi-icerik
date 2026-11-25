"""Durable state for zero-price editorial requests; stores no credentials."""
from contextlib import contextmanager
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3


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
