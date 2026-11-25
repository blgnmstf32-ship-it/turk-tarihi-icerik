"""Shared conservative budgets. Paid reservations count before an API request is sent."""
from __future__ import annotations

from calendar import monthrange
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import sqlite3
from zoneinfo import ZoneInfo

USD_MICROS = 1_000_000
MONTHLY_CAP = 18 * USD_MICROS
DAILY_CAP = 625_000
PACIFIC = ZoneInfo("America/Los_Angeles")
IMAGE_PRICE = {"batch": (0.125, 0.75, 15), "standard": (0.25, 1.50, 30)}


def image_quote(mode, count, input_tokens=768, output_text_tokens=768, image_tokens=1120):
    from math import ceil

    if count < 1:
        raise ValueError("Image count must be positive.")
    prompt, text, image = IMAGE_PRICE[mode]
    return count * ceil(prompt * input_tokens + text * output_text_tokens + image * image_tokens)


def batch_plan(first_day, available_usd_micros, desired_per_day=35):
    """Spread the remaining whole-image budget evenly across the remaining UTC dates."""
    remaining_days = monthrange(first_day.year, first_day.month)[1] - first_day.day + 1
    total = min(desired_per_day * remaining_days, max(0, available_usd_micros) // image_quote("batch", 1))
    return [{"date": (first_day + timedelta(days=i)).isoformat(),
             "image_count": (i + 1) * total // remaining_days - i * total // remaining_days}
            for i in range(remaining_days)]


class Budget:
    def __init__(self, filename):
        path = Path(filename)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path, isolation_level=None, timeout=20)
        self.db.execute("""CREATE TABLE IF NOT EXISTS usage (
            id TEXT PRIMARY KEY, brand TEXT NOT NULL, project TEXT NOT NULL,
            model TEXT NOT NULL, mode TEXT NOT NULL, date TEXT NOT NULL, time REAL NOT NULL,
            in_tokens INTEGER NOT NULL, out_tokens INTEGER NOT NULL, amount INTEGER NOT NULL,
            status TEXT NOT NULL, operation TEXT)""")

    def _reserve(self, values, allowed):
        self.db.execute("BEGIN IMMEDIATE")
        try:
            if self.db.execute("SELECT 1 FROM usage WHERE id=?", (values[0],)).fetchone() or not allowed():
                self.db.execute("ROLLBACK")
                return False
            self.db.execute("INSERT INTO usage VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", values)
            self.db.execute("COMMIT")
            return True
        except Exception:
            self.db.execute("ROLLBACK")
            raise

    def committed_image_cost(self, day):
        return self.db.execute("""
            SELECT coalesce(sum(CASE WHEN substr(date,1,7)=? OR status IN ('pending','submitted','unknown')
                                     THEN amount ELSE 0 END),0),
                   coalesce(sum(CASE WHEN date=? THEN amount ELSE 0 END),0)
            FROM usage WHERE project='gemini-image'""", (day[:7], day)).fetchone()

    def image_schedule(self, first_day=None):
        first_day = first_day or datetime.now(timezone.utc).date()
        month_spent, _ = self.committed_image_cost(first_day.isoformat())
        return batch_plan(first_day, MONTHLY_CAP - month_spent)

    def reserve_image(self, request_id, brand, model, mode, count, now=None):
        now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
        day = now.date().isoformat()
        amount = image_quote(mode, count)
        def allowed():
            month_total, day_total = self.committed_image_cost(day)
            return month_total + amount <= MONTHLY_CAP and day_total + amount <= DAILY_CAP
        return self._reserve((request_id, brand, "gemini-image", model, mode, day, now.timestamp(),
                              768 * count, (768 + 1120) * count, amount, "pending", None), allowed)

    def reserve_free(self, request_id, brand, model, tokens, limits, now=None):
        now = now or datetime.now(timezone.utc)
        day = now.astimezone(PACIFIC).date().isoformat()
        rpm, tpm, rpd = limits
        def allowed():
            minute, used, daily = self.db.execute("""
                SELECT coalesce(sum(time>?),0),
                       coalesce(sum(CASE WHEN time>? THEN in_tokens ELSE 0 END),0),
                       coalesce(sum(date=?),0) FROM usage WHERE project='gemini-free' AND model=?""",
                 (now.timestamp() - 60, now.timestamp() - 60, day, model)).fetchone()
            return minute < rpm and used + tokens <= tpm and daily < rpd
        return self._reserve((request_id, brand, "gemini-free", model, "standard", day, now.timestamp(),
                              tokens, 0, 0, "pending", None), allowed)

    def free_slot_delay(self, model, tokens, limits, now=None):
        """Seconds until the next model minute slot, or None when today's budget is spent."""
        now = now or datetime.now(timezone.utc)
        day, end = now.astimezone(PACIFIC).date().isoformat(), now.timestamp()
        rpm, tpm, rpd = limits
        daily = self.db.execute("SELECT count(*) FROM usage WHERE project='gemini-free' AND model=? AND date=?",
                                (model, day)).fetchone()[0]
        if daily >= rpd or tokens > tpm:
            return None
        pending = self.db.execute("""
            SELECT time, in_tokens FROM usage WHERE project='gemini-free' AND model=? AND time>?
            ORDER BY time""", (model, end-60)).fetchall()
        used = sum(amount for _, amount in pending)
        delay, count = 0, len(pending)
        for started, amount in pending:
            if count < rpm and used + tokens <= tpm:
                break
            delay = max(delay, started + 60.1 - end)
            count -= 1
            used -= amount
        return delay

    def entry(self, request_id):
        row = self.db.execute("SELECT status, operation, amount, mode FROM usage WHERE id=?", (request_id,)).fetchone()
        return dict(zip(("status", "operation", "reserved_usd_micros", "mode"), row)) if row else None

    def finish(self, request_id, status, *, operation=None, tokens=None, measured_cost=None):
        if status not in {"complete", "submitted", "unknown", "failed"}:
            raise ValueError("Invalid budget status.")
        in_tokens, out_tokens = tokens or (None, None)
        result = self.db.execute("""UPDATE usage SET status=?, operation=coalesce(?,operation),
            in_tokens=coalesce(?,in_tokens), out_tokens=coalesce(?,out_tokens),
            amount=coalesce(?,amount) WHERE id=?""",
            (status, operation, in_tokens, out_tokens, measured_cost, request_id))
        if result.rowcount != 1:
            raise ValueError("No reservation with this identity.")

    def report(self):
        fields = ("date", "brand", "project", "model", "mode", "status", "requests",
                  "input_tokens", "output_tokens", "usd_micros")
        return [dict(zip(fields, row)) for row in self.db.execute("""
            SELECT date, brand, project, model, mode, status, count(*), sum(in_tokens), sum(out_tokens), sum(amount)
            FROM usage GROUP BY date, brand, project, model, mode, status ORDER BY date,brand,project,model""")]
