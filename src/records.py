import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DATABASE = Path(__file__).resolve().parents[1] / "data/private/cyberassist.db"

def connect():
    connection = sqlite3.connect(DATABASE, timeout=10)
    connection.execute("PRAGMA foreign_keys = ON")
    return connection

def initialise():
    with connect() as connection:
        connection.executescript("""
            CREATE TABLE IF NOT EXISTS analyses (
                id TEXT PRIMARY KEY,
                username TEXT NOT NULL REFERENCES users(username),
                created_utc TEXT NOT NULL,
                result_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                analysis_id TEXT NOT NULL REFERENCES analyses(id),
                username TEXT NOT NULL REFERENCES users(username),
                decision TEXT NOT NULL,
                final_label TEXT NOT NULL,
                notes TEXT NOT NULL,
                created_utc TEXT NOT NULL
            );
        """)

def save_analysis(username, result):
    with connect() as connection:
        connection.execute(
            "INSERT INTO analyses VALUES (?, ?, ?, ?)",
            (
                result["id"], username, result["created_utc"],
                json.dumps(result),
            ),
        )

def get_analysis(username, analysis_id):
    with connect() as connection:
        row = connection.execute(
            "SELECT result_json FROM analyses WHERE id = ? AND username = ?",
            (analysis_id, username),
        ).fetchone()
    return json.loads(row[0]) if row else None

def save_review(username, analysis_id, decision, final_label, notes):
    created = datetime.now(timezone.utc).isoformat()
    with connect() as connection:
        owned = connection.execute(
            "SELECT 1 FROM analyses WHERE id = ? AND username = ?",
            (analysis_id, username),
        ).fetchone()
        if not owned:
            return None

        cursor = connection.execute(
            """INSERT INTO reviews
               (analysis_id, username, decision, final_label, notes, created_utc)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (analysis_id, username, decision, final_label, notes, created),
        )
        return {
            "review_id": cursor.lastrowid,
            "analysis_id": analysis_id,
            "analyst": username,
            "decision": decision,
            "final_label": final_label,
            "notes": notes,
            "created_utc": created,
        }
