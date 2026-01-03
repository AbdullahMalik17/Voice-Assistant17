"""
Semantic Memory Module
Provides RAG-based semantic memory using ChromaDB for embeddings storage
and sentence-transformers for embedding generation.
"""

import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

# ChromaDB for vector storage
try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False

# Sentence transformers for embeddings
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False

import numpy as np


class RetentionPolicy(str, Enum):
    """Memory retention policies"""
    SESSION = "session"        # Clear on session end
    ONE_DAY = "1d"
    SEVEN_DAYS = "7d"
    THIRTY_DAYS = "30d"
    INDEFINITE = "indefinite"

    def to_timedelta(self) -> Optional[timedelta]:
        """Convert retention policy to timedelta"""
        mapping = {
            RetentionPolicy.SESSION: timedelta(hours=1),
            RetentionPolicy.ONE_DAY: timedelta(days=1),
            RetentionPolicy.SEVEN_DAYS: timedelta(days=7),
            RetentionPolicy.THIRTY_DAYS: timedelta(days=30),
            RetentionPolicy.INDEFINITE: None
        }
        return mapping.get(self)


@dataclass
class MemoryConfig:
    """Configuration for semantic memory"""
    # Storage settings
    persist_directory: str = "data/memory"
    collection_name: str = "conversation_memory"

    # Embedding settings
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_dimension: int = 384

    # Retrieval settings
    default_top_k: int = 5
    similarity_threshold: float = 0.5

    # Retention settings
    retention_policy: RetentionPolicy = RetentionPolicy.SEVEN_DAYS
    max_entries: int = 10000

    # Performance settings
    batch_size: int = 32


@dataclass
class MemoryEntry:
    """A single memory entry with content and metadata"""
    id: str
    content: str
    embedding: Optional[List[float]] = None

    # Metadata
    session_id: str = ""
    user_id: str = "default"
    timestamp: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None

    # Context
    intent: Optional[str] = None
    entities: Dict[str, Any] = field(default_factory=dict)
    importance: float = 0.5  # 0.0 to 1.0

    # Source tracking
    source: str = "conversation"  # conversation, user_fact, system
    turn_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            "id": self.id,
            "content": self.content,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "timestamp": self.timestamp.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "intent": self.intent,
            "entities": self.entities,
            "importance": self.importance,
            "source": self.source,
            "turn_id": self.turn_id
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any], embedding: Optional[List[float]] = None) -> "MemoryEntry":
        """Create from dictionary"""
        return cls(
            id=data["id"],
            content=data.get("content", ""),
            embedding=embedding,
            session_id=data.get("session_id", ""),
            user_id=data.get("user_id", "default"),
            timestamp=datetime.fromisoformat(data["timestamp"]) if data.get("timestamp") else datetime.now(),
            expires_at=datetime.fromisoformat(data["expires_at"]) if data.get("expires_at") else None,
            intent=data.get("intent"),
            entities=data.get("entities", {}),
            importance=data.get("importance", 0.5),
            source=data.get("source", "conversation"),
            turn_id=data.get("turn_id")
        )

    def is_expired(self) -> bool:
        """Check if the memory entry has expired"""
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at


@dataclass
class RetrievedMemory:
    """A memory entry with similarity score from retrieval"""
    entry: MemoryEntry
    similarity: float
    rank: int


class EmbeddingModel:
    """
    Embedding model wrapper for generating text embeddings.
    Uses sentence-transformers or falls back to simple TF-IDF-like approach.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self.model = None
        self._dimension = 384

        if SENTENCE_TRANSFORMERS_AVAILABLE:
            try:
                self.model = SentenceTransformer(model_name)
                self._dimension = self.model.get_sentence_embedding_dimension()
            except Exception:
                self.model = None

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings for a list of texts"""
        if not texts:
            return np.array([])

        if self.model is not None:
            embeddings = self.model.encode(texts, convert_to_numpy=True)
            return embeddings
        else:
            # Fallback: simple bag-of-words embedding
            return self._simple_embed(texts)

    def embed_single(self, text: str) -> List[float]:
        """Generate embedding for a single text"""
        embeddings = self.embed([text])
        return embeddings[0].tolist()

    def _simple_embed(self, texts: List[str]) -> np.ndarray:
        """
        Simple fallback embedding using character n-grams.
        Not as good as sentence-transformers but works offline.
        """
        embeddings = []
        for text in texts:
            # Create a simple hash-based embedding
            text_lower = text.lower()
            embedding = np.zeros(self._dimension, dtype=np.float32)

            # Character trigram hashing
            for i in range(len(text_lower) - 2):
                trigram = text_lower[i:i+3]
                hash_val = hash(trigram) % self._dimension
                embedding[hash_val] += 1

            # Normalize
            norm = np.linalg.norm(embedding)
            if norm > 0:
                embedding /= norm

            embeddings.append(embedding)

        return np.array(embeddings)


class SemanticMemory:
    """
    RAG-based semantic memory system using ChromaDB for storage
    and sentence-transformers for embeddings.

    Provides:
    - Semantic search for relevant memories
    - Session and cross-session memory
    - Automatic TTL-based cleanup
    - Importance-based retrieval ranking
    """

    def __init__(self, config: Optional[MemoryConfig] = None):
        if config is None:
            config = MemoryConfig()

        self.config = config

        # Initialize embedding model
        self.embedding_model = EmbeddingModel(config.embedding_model)

        # Initialize ChromaDB
        self.client = None
        self.collection = None

        if CHROMADB_AVAILABLE:
            self._initialize_chromadb()
        else:
            # Fallback to in-memory storage
            self._memory_store: List[MemoryEntry] = []
            self._embeddings: Dict[str, np.ndarray] = {}

    def _initialize_chromadb(self) -> None:
        """Initialize ChromaDB client and collection"""
        persist_path = Path(self.config.persist_directory)
        persist_path.mkdir(parents=True, exist_ok=True)

        self.client = chromadb.Client(Settings(
            chroma_db_impl="duckdb+parquet",
            persist_directory=str(persist_path),
            anonymized_telemetry=False
        ))

        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=self.config.collection_name,
            metadata={"hnsw:space": "cosine"}
        )

    def store(
        self,
        content: str,
        session_id: str = "",
        user_id: str = "default",
        intent: Optional[str] = None,
        entities: Optional[Dict[str, Any]] = None,
        importance: float = 0.5,
        source: str = "conversation",
        turn_id: Optional[str] = None
    ) -> str:
        """
        Store a new memory entry.

        Args:
            content: The text content to store
            session_id: Current session identifier
            user_id: User identifier for multi-user support
            intent: Optional intent classification
            entities: Optional extracted entities
            importance: Importance score (0.0 to 1.0)
            source: Source of the memory (conversation, user_fact, system)
            turn_id: Optional reference to conversation turn

        Returns:
            The ID of the stored memory entry
        """
        entry_id = str(uuid.uuid4())

        # Calculate expiration time
        expires_at = None
        retention_delta = self.config.retention_policy.to_timedelta()
        if retention_delta:
            expires_at = datetime.now() + retention_delta

        # Generate embedding
        embedding = self.embedding_model.embed_single(content)

        # Create memory entry
        entry = MemoryEntry(
            id=entry_id,
            content=content,
            embedding=embedding,
            session_id=session_id,
            user_id=user_id,
            timestamp=datetime.now(),
            expires_at=expires_at,
            intent=intent,
            entities=entities or {},
            importance=importance,
            source=source,
            turn_id=turn_id
        )

        # Store in ChromaDB or fallback
        if self.collection is not None:
            self.collection.add(
                ids=[entry_id],
                embeddings=[embedding],
                documents=[content],
                metadatas=[entry.to_dict()]
            )
        else:
            self._memory_store.append(entry)
            self._embeddings[entry_id] = np.array(embedding)

        return entry_id

    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        min_similarity: Optional[float] = None,
        include_expired: bool = False
    ) -> List[RetrievedMemory]:
        """
        Retrieve memories semantically similar to the query.

        Args:
            query: The search query
            top_k: Maximum number of results to return
            session_id: Filter by session (None for all sessions)
            user_id: Filter by user
            min_similarity: Minimum similarity threshold
            include_expired: Whether to include expired entries

        Returns:
            List of RetrievedMemory objects with similarity scores
        """
        if top_k is None:
            top_k = self.config.default_top_k

        if min_similarity is None:
            min_similarity = self.config.similarity_threshold

        # Generate query embedding
        query_embedding = self.embedding_model.embed_single(query)

        # Search in ChromaDB or fallback
        if self.collection is not None:
            return self._retrieve_chromadb(
                query_embedding, top_k, session_id, user_id, min_similarity, include_expired
            )
        else:
            return self._retrieve_fallback(
                query_embedding, top_k, session_id, user_id, min_similarity, include_expired
            )

    def _retrieve_chromadb(
        self,
        query_embedding: List[float],
        top_k: int,
        session_id: Optional[str],
        user_id: Optional[str],
        min_similarity: float,
        include_expired: bool
    ) -> List[RetrievedMemory]:
        """Retrieve from ChromaDB"""
        # Build where filter
        where_filter = {}
        if user_id:
            where_filter["user_id"] = user_id

        # Query ChromaDB
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k * 2,  # Get extra to filter after
            where=where_filter if where_filter else None,
            include=["documents", "metadatas", "distances"]
        )

        retrieved = []
        for i, (doc, meta, distance) in enumerate(zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0]
        )):
            # Convert distance to similarity (cosine distance -> similarity)
            similarity = 1 - distance

            if similarity < min_similarity:
                continue

            entry = MemoryEntry.from_dict(meta)
            entry.content = doc

            # Filter by session if specified
            if session_id and entry.session_id != session_id:
                continue

            # Filter expired
            if not include_expired and entry.is_expired():
                continue

            retrieved.append(RetrievedMemory(
                entry=entry,
                similarity=similarity,
                rank=len(retrieved) + 1
            ))

            if len(retrieved) >= top_k:
                break

        return retrieved

    def _retrieve_fallback(
        self,
        query_embedding: List[float],
        top_k: int,
        session_id: Optional[str],
        user_id: Optional[str],
        min_similarity: float,
        include_expired: bool
    ) -> List[RetrievedMemory]:
        """Retrieve from in-memory fallback storage"""
        query_vec = np.array(query_embedding)
        scored_entries = []

        for entry in self._memory_store:
            # Filter by session
            if session_id and entry.session_id != session_id:
                continue

            # Filter by user
            if user_id and entry.user_id != user_id:
                continue

            # Filter expired
            if not include_expired and entry.is_expired():
                continue

            # Calculate cosine similarity
            entry_vec = self._embeddings.get(entry.id)
            if entry_vec is None:
                continue

            similarity = np.dot(query_vec, entry_vec) / (
                np.linalg.norm(query_vec) * np.linalg.norm(entry_vec) + 1e-10
            )

            if similarity >= min_similarity:
                scored_entries.append((entry, similarity))

        # Sort by similarity (descending)
        scored_entries.sort(key=lambda x: x[1], reverse=True)

        # Return top_k results
        return [
            RetrievedMemory(entry=entry, similarity=sim, rank=i+1)
            for i, (entry, sim) in enumerate(scored_entries[:top_k])
        ]

    def forget(
        self,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        before: Optional[datetime] = None
    ) -> int:
        """
        Delete memories matching the criteria.

        Args:
            session_id: Delete memories from this session
            user_id: Delete memories for this user
            before: Delete memories created before this time

        Returns:
            Number of entries deleted
        """
        if self.collection is not None:
            return self._forget_chromadb(session_id, user_id, before)
        else:
            return self._forget_fallback(session_id, user_id, before)

    def _forget_chromadb(
        self,
        session_id: Optional[str],
        user_id: Optional[str],
        before: Optional[datetime]
    ) -> int:
        """Delete from ChromaDB"""
        # Build where filter
        where_filter = {}
        if session_id:
            where_filter["session_id"] = session_id
        if user_id:
            where_filter["user_id"] = user_id

        # Get matching IDs
        if where_filter:
            results = self.collection.get(where=where_filter)
            ids_to_delete = results["ids"]
        else:
            # Get all and filter by date
            results = self.collection.get()
            ids_to_delete = []

            if before:
                for id_, meta in zip(results["ids"], results["metadatas"]):
                    timestamp = datetime.fromisoformat(meta.get("timestamp", ""))
                    if timestamp < before:
                        ids_to_delete.append(id_)
            else:
                ids_to_delete = results["ids"]

        if ids_to_delete:
            self.collection.delete(ids=ids_to_delete)

        return len(ids_to_delete)

    def _forget_fallback(
        self,
        session_id: Optional[str],
        user_id: Optional[str],
        before: Optional[datetime]
    ) -> int:
        """Delete from in-memory fallback storage"""
        original_count = len(self._memory_store)
        filtered = []

        for entry in self._memory_store:
            keep = True

            if session_id and entry.session_id == session_id:
                keep = False
            if user_id and entry.user_id == user_id:
                keep = False
            if before and entry.timestamp < before:
                keep = False

            if keep:
                filtered.append(entry)
            else:
                # Remove embedding
                self._embeddings.pop(entry.id, None)

        self._memory_store = filtered
        return original_count - len(filtered)

    def cleanup_expired(self) -> int:
        """Remove all expired memory entries"""
        if self.collection is not None:
            # Get all entries and check expiration
            results = self.collection.get()
            expired_ids = []

            for id_, meta in zip(results["ids"], results["metadatas"]):
                expires_at = meta.get("expires_at")
                if expires_at:
                    if datetime.now() > datetime.fromisoformat(expires_at):
                        expired_ids.append(id_)

            if expired_ids:
                self.collection.delete(ids=expired_ids)

            return len(expired_ids)
        else:
            # In-memory fallback
            original_count = len(self._memory_store)
            self._memory_store = [e for e in self._memory_store if not e.is_expired()]
            for entry_id in list(self._embeddings.keys()):
                if entry_id not in [e.id for e in self._memory_store]:
                    del self._embeddings[entry_id]
            return original_count - len(self._memory_store)

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the memory store"""
        if self.collection is not None:
            count = self.collection.count()
        else:
            count = len(self._memory_store)

        return {
            "total_entries": count,
            "embedding_model": self.config.embedding_model,
            "embedding_dimension": self.embedding_model.dimension,
            "retention_policy": self.config.retention_policy.value,
            "chromadb_available": CHROMADB_AVAILABLE,
            "sentence_transformers_available": SENTENCE_TRANSFORMERS_AVAILABLE
        }

    def persist(self) -> None:
        """Persist memory to disk (for ChromaDB)"""
        if self.client is not None:
            self.client.persist()


def create_semantic_memory(
    persist_directory: str = "data/memory",
    retention_policy: str = "7d"
) -> SemanticMemory:
    """Factory function to create SemanticMemory with common settings"""
    config = MemoryConfig(
        persist_directory=persist_directory,
        retention_policy=RetentionPolicy(retention_policy)
    )
    return SemanticMemory(config)
