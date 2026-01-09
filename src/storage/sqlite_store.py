"""
SQLite Storage Implementation
Persistent storage for conversation sessions and turns.
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import logging

logger = logging.getLogger(__name__)

class SqliteStore:
    """
    SQLite-based persistent storage for conversation sessions and turns.
    """

    def __init__(self, db_path: Union[str, Path] = "data/sessions.db"):
        self.db_path = Path(db_path)
        self._init_database()

    def _init_database(self) -> None:
        """Initialize SQLite database with schema"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        # Create sessions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                state TEXT NOT NULL,
                current_intent TEXT,
                metadata TEXT,
                created_at TIMESTAMP NOT NULL,
                last_updated TIMESTAMP NOT NULL
            )
        ''')

        # Create turns table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS turns (
                turn_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                user_input TEXT NOT NULL,
                assistant_response TEXT NOT NULL,
                intent TEXT,
                intent_confidence REAL,
                entities TEXT,
                timestamp TIMESTAMP NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions (session_id) ON DELETE CASCADE
            )
        ''')

        # Create indices
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_turns_session_id ON turns(session_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id)')

        conn.commit()
        conn.close()

    def save_session(self, session_id: str, user_id: str, state: str, 
                     current_intent: Optional[str] = None, 
                     metadata: Optional[Dict] = None) -> None:
        """Save or update session state"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        now = datetime.now().isoformat()
        metadata_json = json.dumps(metadata or {})

        cursor.execute('''
            INSERT INTO sessions (session_id, user_id, state, current_intent, metadata, created_at, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(session_id) DO UPDATE SET
                state = excluded.state,
                current_intent = excluded.current_intent,
                metadata = excluded.metadata,
                last_updated = excluded.last_updated
        ''', (session_id, user_id, state, current_intent, metadata_json, now, now))

        conn.commit()
        conn.close()

    def add_turn(self, turn_id: str, session_id: str, user_input: str, 
                 assistant_response: str, intent: Optional[str] = None,
                 intent_confidence: float = 0.0, entities: Optional[Dict] = None) -> None:
        """Add a conversation turn to a session"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        now = datetime.now().isoformat()
        entities_json = json.dumps(entities or {})

        cursor.execute('''
            INSERT INTO turns (turn_id, session_id, user_input, assistant_response, intent, intent_confidence, entities, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (turn_id, session_id, user_input, assistant_response, intent, intent_confidence, entities_json, now))

        # Also update last_updated in sessions
        cursor.execute('UPDATE sessions SET last_updated = ? WHERE session_id = ?', (now, session_id))

        conn.commit()
        conn.close()

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve session data and its turns"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM sessions WHERE session_id = ?', (session_id,))
        session_row = cursor.fetchone()

        if not session_row:
            conn.close()
            return None

        cursor.execute('SELECT * FROM turns WHERE session_id = ? ORDER BY timestamp ASC', (session_id,))
        turns = [dict(row) for row in cursor.fetchall()]
        
        # Deserialize JSON fields
        session_dict = dict(session_row)
        session_dict['metadata'] = json.loads(session_dict['metadata']) if session_dict['metadata'] else {}
        for turn in turns:
            turn['entities'] = json.loads(turn['entities']) if turn['entities'] else {}

        session_dict['turns'] = turns
        
        conn.close()
        return session_dict

    def get_user_sessions(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent sessions for a user"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM sessions 
            WHERE user_id = ? 
            ORDER BY last_updated DESC 
            LIMIT ?
        ''', (user_id, limit))
        
        sessions = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return sessions

    def delete_session(self, session_id: str) -> None:
        """Delete a session and all its turns"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute('DELETE FROM turns WHERE session_id = ?', (session_id,))
        cursor.execute('DELETE FROM sessions WHERE session_id = ?', (session_id,))
        conn.commit()
        conn.close()
