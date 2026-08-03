import sqlite3
import json
from contextlib import contextmanager

from . import config


def get_conn():
    conn = sqlite3.connect(config.DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


@contextmanager
def get_db():
    conn = get_conn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def query_all(sql, params=()):
    with get_db() as db:
        rows = db.execute(sql, params).fetchall()
        return [dict(r) for r in rows]


def query_one(sql, params=()):
    with get_db() as db:
        row = db.execute(sql, params).fetchone()
        return dict(row) if row else None


def execute(sql, params=()):
    with get_db() as db:
        cur = db.execute(sql, params)
        return cur.lastrowid


def dumps(obj):
    return json.dumps(obj, ensure_ascii=False)


def loads(s, default=None):
    if s is None or s == "":
        return default
    try:
        return json.loads(s)
    except Exception:
        return default


def ensure_column(db, table, column, col_type="TEXT"):
    cols = {r["name"] for r in db.execute(f"PRAGMA table_info({table})")}
    if column not in cols:
        db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")


SQLITE_TYPE_MAP = {
    "text": "TEXT",
    "number": "REAL",
    "date": "TEXT",
    "image": "TEXT",
    "select": "TEXT",
}
