"""SQLite persistence: analysis history + cache."""
import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

from app.config import settings


@contextmanager
def conn():
    os.makedirs(os.path.dirname(settings.db_path) or ".", exist_ok=True)
    c = sqlite3.connect(settings.db_path)
    c.row_factory = sqlite3.Row
    try:
        yield c
        c.commit()
    finally:
        c.close()


def init():
    with conn() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS analyses(
            id INTEGER PRIMARY KEY AUTOINCREMENT, url TEXT, content_hash TEXT, brand TEXT,
            category TEXT, created_at TEXT, result TEXT)""")
        c.execute("CREATE INDEX IF NOT EXISTS idx_url ON analyses(url, content_hash)")


def save(url: str, content_hash: str, result: dict) -> int:
    with conn() as c:
        cur = c.execute(
            "INSERT INTO analyses(url, content_hash, brand, category, created_at, result) VALUES (?,?,?,?,?,?)",
            (url, content_hash, result["brand"].get("name", ""), result["brand"].get("category", ""),
             datetime.now(timezone.utc).isoformat(), json.dumps(result)))
        return cur.lastrowid


def find_cached(url: str, content_hash: str, ttl_hours: int):
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=ttl_hours)).isoformat()
    with conn() as c:
        row = c.execute("SELECT id, result FROM analyses WHERE url=? AND content_hash=? AND created_at>? "
                        "ORDER BY id DESC LIMIT 1", (url, content_hash, cutoff)).fetchone()
    return {**json.loads(row["result"]), "id": row["id"]} if row else None


def history(limit: int = 50):
    with conn() as c:
        rows = c.execute("SELECT id, url, brand, category, created_at FROM analyses ORDER BY id DESC LIMIT ?",
                         (limit,)).fetchall()
    return [dict(r) for r in rows]


def get(rid: int):
    with conn() as c:
        row = c.execute("SELECT id, result FROM analyses WHERE id=?", (rid,)).fetchone()
    return {**json.loads(row["result"]), "id": row["id"], "cached": True} if row else None


def delete(rid: int) -> bool:
    with conn() as c:
        return c.execute("DELETE FROM analyses WHERE id=?", (rid,)).rowcount > 0
