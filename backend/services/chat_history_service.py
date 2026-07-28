import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

# Reuses the same local SQLite file as memory_service.py, just a different table.
DB_PATH = Path(__file__).parent.parent / "maya_memory.db"


def _init_db():
    """Ensures the chat_sessions table exists on startup."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            started_at TIMESTAMP,
            ended_at TIMESTAMP,
            messages TEXT
        )
    """)
    conn.commit()
    conn.close()


_init_db()


def save_session(messages: List[Dict], started_at: Optional[datetime] = None,
                  ended_at: Optional[datetime] = None) -> Optional[int]:
    """
    Persists one full conversation session as a JSON blob.

    `messages` is a list of {"sender": "user"|"maya", "content": str, "timestamp": str}
    in chronological order. Called once, right when the "stop" command fires,
    so the whole live session gets written in a single row.
    """
    if not messages:
        return None

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO chat_sessions (started_at, ended_at, messages) VALUES (?, ?, ?)",
        (
            (started_at or datetime.now()).isoformat(),
            (ended_at or datetime.now()).isoformat(),
            json.dumps(messages),
        ),
    )
    conn.commit()
    session_id = cursor.lastrowid
    conn.close()
    return session_id


def get_all_sessions() -> List[Dict]:
    """Returns every saved session, most recent first, with messages parsed."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, started_at, ended_at, messages FROM chat_sessions ORDER BY id DESC"
    )
    rows = cursor.fetchall()
    conn.close()

    sessions = []
    for row in rows:
        sessions.append({
            "id": row[0],
            "started_at": row[1],
            "ended_at": row[2],
            "messages": json.loads(row[3]),
        })
    return sessions


def get_session(session_id: int) -> Optional[Dict]:
    """Returns a single session by id, or None if it doesn't exist."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, started_at, ended_at, messages FROM chat_sessions WHERE id = ?",
        (session_id,),
    )
    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    return {
        "id": row[0],
        "started_at": row[1],
        "ended_at": row[2],
        "messages": json.loads(row[3]),
    }


def delete_session(session_id: int) -> bool:
    """Deletes a single saved session. Returns True if a row was removed."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM chat_sessions WHERE id = ?", (session_id,))
    conn.commit()
    deleted = cursor.rowcount > 0
    conn.close()
    return deleted