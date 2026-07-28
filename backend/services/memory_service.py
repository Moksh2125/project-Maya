import sqlite3
from pathlib import Path
from services.fallback_service import handle_hallucination

DB_PATH = Path(__file__).parent.parent / "maya_memory.db"

def _init_db():
    """Ensures the SQLite table exists on startup."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fact TEXT UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

# Initialize DB when module loads
_init_db()

def handle_memory(action: str, fact: str = "") -> str:
    """Saves, recalls, or clears facts stored in local SQLite storage."""
    action = (action or "").lower().strip()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        if action == "save" and fact:
            cursor.execute("INSERT OR REPLACE INTO memories (fact) VALUES (?)", (fact,))
            conn.commit()
            return f"Saved to memory: {fact}"

        elif action in ["recall", "read", "get"]:
            cursor.execute("SELECT fact FROM memories ORDER BY created_at DESC LIMIT 5")
            rows = cursor.fetchall()
            if not rows:
                return "I don't have any saved memories yet."
            facts = [r[0] for r in rows]
            return f"Here is what I remember: {', '.join(facts)}"

        elif action in ["clear", "delete", "erase"]:
            cursor.execute("DELETE FROM memories")
            conn.commit()
            return "Cleared all stored memories."

        else:
            # <-- Catch hallucinated memory actions
            return handle_hallucination("Memory Service", f"Invalid action: {action}")
            
    except Exception as e:
        return handle_hallucination("Memory Service (Crash)", str(e))
    finally:
        conn.close()