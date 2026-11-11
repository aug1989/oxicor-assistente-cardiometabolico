"""Opt-in cleanup for expired local chat and observability records."""
import json
import os
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path


def configured_retention_days():
    raw = os.getenv("OXICOR_RETENTION_DAYS", "").strip()
    if not raw:
        return None
    try:
        days = int(raw)
    except ValueError as exc:
        raise ValueError("OXICOR_RETENTION_DAYS deve ser um inteiro positivo.") from exc
    if days <= 0:
        raise ValueError("OXICOR_RETENTION_DAYS deve ser um inteiro positivo.")
    return days


def _utc_datetime(value):
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def cleanup_expired_records(chat_path, trace_path, days, now=None):
    """Delete expired rows only when explicitly configured by the operator."""
    if days is None:
        return {"chats": 0, "traces": 0}
    if type(days) is not int or days <= 0:
        raise ValueError("days deve ser um inteiro positivo.")
    current = now or datetime.now(timezone.utc)
    cutoff = current.astimezone(timezone.utc) - timedelta(days=days)
    removed = {"chats": 0, "traces": 0}

    chat_path = Path(chat_path)
    if chat_path.exists():
        with closing(sqlite3.connect(chat_path, timeout=15)) as db, db:
            tables = {row[0] for row in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )}
            if "chats" in tables:
                expired = []
                for chat_id, created_at, raw_messages in db.execute(
                    "SELECT id, created_at, messages FROM chats"
                ):
                    timestamps = [_utc_datetime(created_at)]
                    for message in json.loads(raw_messages):
                        if message.get("created_at"):
                            timestamps.append(_utc_datetime(message["created_at"]))
                    if max(timestamps) < cutoff:
                        expired.append((chat_id,))
                db.executemany("DELETE FROM chats WHERE id=?", expired)
                removed["chats"] = len(expired)

    trace_path = Path(trace_path)
    if trace_path.exists():
        with closing(sqlite3.connect(trace_path, timeout=15)) as db, db:
            tables = {row[0] for row in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )}
            if "traces" in tables:
                expired = [
                    row[0] for row in db.execute(
                        "SELECT id FROM traces WHERE started_at < ?",
                        (cutoff.isoformat(),),
                    )
                ]
                db.executemany("DELETE FROM traces WHERE id=?", ((item,) for item in expired))
                if "langfuse_exports" in tables:
                    db.executemany(
                        "DELETE FROM langfuse_exports WHERE trace_id=?",
                        ((item,) for item in expired),
                    )
                removed["traces"] = len(expired)
    return removed
