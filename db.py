import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DB_FILE = Path(os.getenv("PORTRAIT_DB_FILE", BASE_DIR / "portrait.db")).expanduser()
if not DB_FILE.is_absolute():
    DB_FILE = BASE_DIR / DB_FILE


def get_conn():
    DB_FILE.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_message TEXT,
            assistant_response TEXT,
            created_at TEXT
        );

        CREATE TABLE IF NOT EXISTS analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER,
            tier TEXT,
            payload TEXT,
            created_at TEXT
        );

        CREATE TABLE IF NOT EXISTS portrait (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            version INTEGER DEFAULT 0,
            payload TEXT,
            updated_at TEXT
        );
    """)
    conn.commit()


def save_conversation(conn, user_message, assistant_response):
    cur = conn.execute(
        "INSERT INTO conversations (user_message, assistant_response, created_at) VALUES (?, ?, ?)",
        (user_message, assistant_response, _now()),
    )
    conn.commit()
    return cur.lastrowid


def get_conversation_count(conn):
    return conn.execute("SELECT COUNT(*) FROM conversations").fetchone()[0]


def save_analysis(conn, conversation_id, tier, payload: dict):
    conn.execute(
        "INSERT INTO analyses (conversation_id, tier, payload, created_at) VALUES (?, ?, ?, ?)",
        (conversation_id, tier, json.dumps(payload), _now()),
    )
    conn.commit()


def get_analyses_by_tier(conn, tier, limit=None):
    q = "SELECT payload FROM analyses WHERE tier = ? ORDER BY id DESC"
    if limit:
        q += f" LIMIT {limit}"
    rows = conn.execute(q, (tier,)).fetchall()
    return [json.loads(r["payload"]) for r in reversed(rows)]


def get_last_n_t1_atoms(conn, n):
    rows = conn.execute(
        "SELECT payload FROM analyses WHERE tier = 't1' ORDER BY id DESC LIMIT ?", (n,)
    ).fetchall()
    return [json.loads(r["payload"]) for r in reversed(rows)]


def get_portrait(conn):
    row = conn.execute("SELECT payload FROM portrait WHERE id = 1").fetchone()
    return json.loads(row["payload"]) if row else None


def save_portrait(conn, payload: dict, version: int):
    conn.execute(
        """INSERT INTO portrait (id, version, payload, updated_at) VALUES (1, ?, ?, ?)
           ON CONFLICT(id) DO UPDATE SET version=excluded.version, payload=excluded.payload, updated_at=excluded.updated_at""",
        (version, json.dumps(payload), _now()),
    )
    conn.commit()


def get_portrait_version(conn):
    row = conn.execute("SELECT version FROM portrait WHERE id = 1").fetchone()
    return row["version"] if row else 0


def get_recent_conversations(conn, n):
    rows = conn.execute(
        "SELECT user_message, assistant_response FROM conversations ORDER BY id DESC LIMIT ?", (n,)
    ).fetchall()
    return [dict(r) for r in reversed(rows)]


def _now():
    return datetime.now(timezone.utc).isoformat()
