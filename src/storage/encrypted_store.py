"""
Encrypted Storage Implementation
Optional persistent storage for conversation context with encryption
"""

import base64
import hashlib
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from uuid import UUID

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2

from ..models.conversation_context import ConversationContext


class EncryptedStore:
    """
    Encrypted persistent storage for conversation contexts
    Uses SQLite with AES-256 (Fernet) encryption and PBKDF2 key derivation
    """

    def __init__(
        self,
        db_path: Path,
        encryption_key: str,
        retention_days: int = 7
    ):
        self.db_path = Path(db_path)
        self.retention_days = retention_days

        # Derive encryption key from password
        self.cipher = self._derive_cipher(encryption_key)

        # Initialize database
        self._init_database()

    def _derive_cipher(self, password: str) -> Fernet:
        """Derive encryption key from password using PBKDF2"""
        # Use a fixed salt for key derivation
        # In production, this should be stored separately and unique per installation
        salt = b'voice_assistant_salt_v1'  # 23 bytes

        # Derive key using PBKDF2
        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=480000,  # OWASP recommendation for 2023+
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))

        return Fernet(key)

    def _init_database(self) -> None:
        """Initialize SQLite database with schema"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        # Create contexts table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversation_contexts (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                encrypted_data TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL,
                last_activity TIMESTAMP NOT NULL,
                is_active INTEGER NOT NULL,
                exchange_count INTEGER NOT NULL
            )
        ''')

        # Create index on session_id for faster lookups
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_session_id
            ON conversation_contexts(session_id)
        ''')

        # Create index on last_activity for cleanup
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_last_activity
            ON conversation_contexts(last_activity)
        ''')

        conn.commit()
        conn.close()

    def _encrypt(self, data: str) -> str:
        """Encrypt data using Fernet"""
        encrypted = self.cipher.encrypt(data.encode())
        return base64.urlsafe_b64encode(encrypted).decode()

    def _decrypt(self, encrypted_data: str) -> str:
        """Decrypt data using Fernet"""
        encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode())
        decrypted = self.cipher.decrypt(encrypted_bytes)
        return decrypted.decode()

    def save_context(self, context: ConversationContext) -> None:
        """Save encrypted conversation context"""
        # Serialize context to JSON
        context_dict = context.model_dump(mode='json')
        context_json = json.dumps(context_dict)

        # Encrypt
        encrypted_data = self._encrypt(context_json)

        # Store in database
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute('''
            INSERT OR REPLACE INTO conversation_contexts
            (id, session_id, encrypted_data, created_at, last_activity, is_active, exchange_count)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            str(context.id),
            str(context.session_id),
            encrypted_data,
            context.last_activity.isoformat(),  # Use last_activity as created_at proxy
            context.last_activity.isoformat(),
            1 if context.is_active else 0,
            len(context.exchanges)
        ))

        conn.commit()
        conn.close()

    def get_context(self, context_id: UUID) -> Optional[ConversationContext]:
        """Get conversation context by ID"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute('''
            SELECT encrypted_data FROM conversation_contexts
            WHERE id = ?
        ''', (str(context_id),))

        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        # Decrypt and deserialize
        decrypted_json = self._decrypt(row[0])
        context_dict = json.loads(decrypted_json)

        return ConversationContext(**context_dict)

    def get_context_by_session(self, session_id: UUID) -> Optional[ConversationContext]:
        """Get conversation context by session ID"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute('''
            SELECT encrypted_data FROM conversation_contexts
            WHERE session_id = ?
            ORDER BY last_activity DESC
            LIMIT 1
        ''', (str(session_id),))

        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        # Decrypt and deserialize
        decrypted_json = self._decrypt(row[0])
        context_dict = json.loads(decrypted_json)

        return ConversationContext(**context_dict)

    def get_all_contexts(self, active_only: bool = False) -> List[ConversationContext]:
        """Get all conversation contexts"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        if active_only:
            cursor.execute('''
                SELECT encrypted_data FROM conversation_contexts
                WHERE is_active = 1
                ORDER BY last_activity DESC
            ''')
        else:
            cursor.execute('''
                SELECT encrypted_data FROM conversation_contexts
                ORDER BY last_activity DESC
            ''')

        rows = cursor.fetchall()
        conn.close()

        contexts = []
        for row in rows:
            decrypted_json = self._decrypt(row[0])
            context_dict = json.loads(decrypted_json)
            contexts.append(ConversationContext(**context_dict))

        return contexts

    def delete_context(self, context_id: UUID) -> bool:
        """Delete conversation context"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute('''
            DELETE FROM conversation_contexts
            WHERE id = ?
        ''', (str(context_id),))

        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()

        return deleted

    def cleanup_old_contexts(self) -> int:
        """Remove contexts older than retention period"""
        retention_date = datetime.utcnow().timestamp() - (self.retention_days * 24 * 3600)
        retention_iso = datetime.fromtimestamp(retention_date).isoformat()

        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute('''
            DELETE FROM conversation_contexts
            WHERE last_activity < ?
        ''', (retention_iso,))

        deleted = cursor.rowcount
        conn.commit()
        conn.close()

        return deleted

    def get_context_count(self) -> int:
        """Get total number of stored contexts"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute('SELECT COUNT(*) FROM conversation_contexts')
        count = cursor.fetchone()[0]

        conn.close()
        return count

    def clear_all(self) -> None:
        """Delete all stored contexts"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute('DELETE FROM conversation_contexts')

        conn.commit()
        conn.close()

    def get_storage_stats(self) -> dict:
        """Get storage statistics"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        # Total contexts
        cursor.execute('SELECT COUNT(*) FROM conversation_contexts')
        total = cursor.fetchone()[0]

        # Active contexts
        cursor.execute('SELECT COUNT(*) FROM conversation_contexts WHERE is_active = 1')
        active = cursor.fetchone()[0]

        # Database size
        db_size_bytes = self.db_path.stat().st_size if self.db_path.exists() else 0

        conn.close()

        return {
            "total_contexts": total,
            "active_contexts": active,
            "db_size_bytes": db_size_bytes,
            "db_size_mb": db_size_bytes / (1024 * 1024),
            "retention_days": self.retention_days
        }


# Global encrypted store instance
_encrypted_store: Optional[EncryptedStore] = None


def get_encrypted_store(
    db_path: Path = Path("data/conversations.db"),
    encryption_key: Optional[str] = None,
    retention_days: int = 7
) -> EncryptedStore:
    """
    Get or create global encrypted store instance
    Raises ValueError if encryption_key is not provided on first call
    """
    global _encrypted_store

    if _encrypted_store is None:
        if encryption_key is None:
            raise ValueError("encryption_key required to initialize encrypted store")

        _encrypted_store = EncryptedStore(
            db_path=db_path,
            encryption_key=encryption_key,
            retention_days=retention_days
        )

    return _encrypted_store
