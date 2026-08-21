"""Persistent SQLite Session and Wedding Profile Store for Multi-Turn Agent Memory."""

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from wedding_planner.observability.pii_scrubber import redact_pii


class PersistentSessionStore:
    """Persistent SQLite database manager for wedding profile state and conversation turns."""

    def __init__(self, db_path: str = "wedding_planner_sessions.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        """Initializes database schema if tables do not exist."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # Session State table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    wedding_profile TEXT,
                    created_at TEXT,
                    updated_at TEXT
                )
            """)
            # Message history table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversation_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    role TEXT,
                    content TEXT,
                    timestamp TEXT,
                    FOREIGN KEY(session_id) REFERENCES sessions(session_id)
                )
            """)
            # Shortlisted vendors/venues table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS shortlisted_vendors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    vendor_name TEXT,
                    vendor_type TEXT,
                    details TEXT,
                    saved_at TEXT,
                    FOREIGN KEY(session_id) REFERENCES sessions(session_id)
                )
            """)
            conn.commit()

    def get_or_create_profile(self, session_id: str) -> Dict[str, Any]:
        """Retrieves active wedding profile or initializes a default template."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT wedding_profile FROM sessions WHERE session_id = ?", (session_id,))
            row = cursor.fetchone()
            if row:
                return json.loads(row[0])

            default_profile = {
                "city": None,
                "total_budget_usd": None,
                "guest_count": None,
                "style_preference": None,
                "wedding_date": None,
                "priorities": [],
                "confirmed_decisions": {},
            }
            now = datetime.now(timezone.utc).isoformat()
            cursor.execute(
                "INSERT INTO sessions (session_id, wedding_profile, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (session_id, json.dumps(default_profile), now, now),
            )
            conn.commit()
            return default_profile

    def update_profile(self, session_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Updates specific fields in the persistent wedding profile."""
        current = self.get_or_create_profile(session_id)
        current.update(updates)
        now = datetime.now(timezone.utc).isoformat()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE sessions SET wedding_profile = ?, updated_at = ? WHERE session_id = ?",
                (json.dumps(current), now, session_id),
            )
            conn.commit()
        return current

    def record_message(self, session_id: str, role: str, content: str) -> None:
        """Stores a sanitized turn in the conversation history table."""
        # Ensure session exists
        self.get_or_create_profile(session_id)
        # Apply PII redaction before persistence
        clean_content = redact_pii(content) if isinstance(content, str) else str(content)
        now = datetime.now(timezone.utc).isoformat()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO conversation_history (session_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
                (session_id, role, clean_content, now),
            )
            conn.commit()

    def get_history(self, session_id: str, limit: int = 50) -> List[Dict[str, str]]:
        """Retrieves conversational history for a session."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT role, content FROM conversation_history WHERE session_id = ? ORDER BY id ASC LIMIT ?",
                (session_id, limit),
            )
            rows = cursor.fetchall()
            return [{"role": r[0], "content": r[1]} for r in rows]

    def save_shortlisted_vendor(self, session_id: str, vendor_name: str, vendor_type: str, details: Dict[str, Any]) -> None:
        """Saves a venue or vendor to the couple's persistent shortlist."""
        self.get_or_create_profile(session_id)
        now = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO shortlisted_vendors (session_id, vendor_name, vendor_type, details, saved_at) VALUES (?, ?, ?, ?, ?)",
                (session_id, vendor_name, vendor_type, json.dumps(details), now),
            )
            conn.commit()
