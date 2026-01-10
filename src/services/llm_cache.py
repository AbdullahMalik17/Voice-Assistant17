"""
LLM Response Caching Service
Provides intelligent caching of LLM responses to reduce latency and API costs.
Implements TTL (time-to-live) based cache expiration with optional Redis backend.

Reference: https://docs.python.org/3/library/hashlib.html
"""

import hashlib
import time
import logging
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Represents a cached LLM response entry"""
    response: str
    timestamp: float
    query_hash: str
    context_hash: Optional[str] = None
    intent: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def is_expired(self, ttl_seconds: int) -> bool:
        """Check if cache entry has expired based on TTL"""
        return time.time() - self.timestamp > ttl_seconds

    def to_dict(self) -> Dict[str, Any]:
        """Convert cache entry to dictionary"""
        return {
            "response": self.response,
            "timestamp": datetime.fromtimestamp(self.timestamp).isoformat(),
            "query_hash": self.query_hash,
            "context_hash": self.context_hash,
            "intent": self.intent,
            "metadata": self.metadata
        }


class LLMCache:
    """
    Cache system for LLM responses with professional features.
    Supports in-memory caching with optional Redis backend for distributed deployments.
    """

    def __init__(self, ttl_seconds: int = 3600, max_entries: int = 1000, use_redis: bool = False):
        """
        Initialize LLM cache.

        Args:
            ttl_seconds: Time-to-live for cache entries in seconds (default: 1 hour)
            max_entries: Maximum entries to keep in-memory cache (default: 1000)
            use_redis: Whether to use Redis for distributed caching (default: False)
        """
        self.ttl = ttl_seconds
        self.max_entries = max_entries
        self.use_redis = use_redis
        self._in_memory_cache: Dict[str, CacheEntry] = {}
        self._access_count: Dict[str, int] = {}
        self._stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "total_requests": 0
        }

        if use_redis:
            try:
                import redis
                self.redis_client = redis.Redis(
                    host='localhost',
                    port=6379,
                    db=0,
                    decode_responses=True
                )
                # Test connection
                self.redis_client.ping()
                logger.info("Redis cache backend initialized successfully")
            except ImportError:
                logger.warning("redis package not installed, falling back to in-memory cache")
                self.use_redis = False
            except Exception as e:
                logger.warning(f"Could not connect to Redis: {e}, falling back to in-memory cache")
                self.use_redis = False
        else:
            self.redis_client = None

        logger.info(f"LLMCache initialized (ttl={ttl_seconds}s, max_entries={max_entries}, redis={self.use_redis})")

    def _generate_hash(self, text: str) -> str:
        """
        Generate SHA-256 hash for query or context.

        Args:
            text: Text to hash

        Returns:
            Hex-encoded SHA-256 hash
        """
        return hashlib.sha256(text.encode('utf-8')).hexdigest()

    def _generate_cache_key(
        self,
        query: str,
        context: Optional[str] = None,
        intent: Optional[str] = None
    ) -> str:
        """
        Generate cache key from query, context, and intent.

        Args:
            query: User query
            context: Optional conversation context
            intent: Optional detected intent

        Returns:
            Cache key string
        """
        # Build cache key components
        key_parts = [
            self._generate_hash(query),
            self._generate_hash(context) if context else "no_context",
            intent or "no_intent"
        ]

        # Combine into cache key
        cache_key = "|".join(key_parts)
        return cache_key

    def get(
        self,
        query: str,
        context: Optional[str] = None,
        intent: Optional[str] = None
    ) -> Optional[str]:
        """
        Retrieve cached response if available and not expired.

        Args:
            query: User query
            context: Optional conversation context
            intent: Optional detected intent

        Returns:
            Cached response text or None if not found/expired
        """
        self._stats["total_requests"] += 1
        cache_key = self._generate_cache_key(query, context, intent)

        try:
            if self.use_redis and self.redis_client:
                # Try Redis first
                cached_data = self.redis_client.get(cache_key)
                if cached_data:
                    self._stats["hits"] += 1
                    logger.debug(f"Cache HIT (Redis): {cache_key[:20]}...")
                    return cached_data
            else:
                # Check in-memory cache
                if cache_key in self._in_memory_cache:
                    entry = self._in_memory_cache[cache_key]

                    # Check if expired
                    if entry.is_expired(self.ttl):
                        # Remove expired entry
                        del self._in_memory_cache[cache_key]
                        self._stats["misses"] += 1
                        logger.debug(f"Cache MISS (expired): {cache_key[:20]}...")
                        return None

                    # Update access count for LRU
                    self._access_count[cache_key] = self._access_count.get(cache_key, 0) + 1

                    self._stats["hits"] += 1
                    logger.debug(f"Cache HIT (in-memory): {cache_key[:20]}..., age={time.time() - entry.timestamp:.1f}s")
                    return entry.response

            self._stats["misses"] += 1
            logger.debug(f"Cache MISS: {cache_key[:20]}...")
            return None

        except Exception as e:
            logger.error(f"Cache retrieval error: {e}")
            return None

    def set(
        self,
        query: str,
        response: str,
        context: Optional[str] = None,
        intent: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Store response in cache.

        Args:
            query: User query
            response: LLM response to cache
            context: Optional conversation context
            intent: Optional detected intent
            metadata: Optional metadata to store with response

        Returns:
            True if cached successfully, False otherwise
        """
        try:
            cache_key = self._generate_cache_key(query, context, intent)

            if self.use_redis and self.redis_client:
                # Store in Redis with TTL
                self.redis_client.setex(
                    cache_key,
                    self.ttl,
                    response
                )
                logger.debug(f"Response cached (Redis): {cache_key[:20]}...")
                return True
            else:
                # Store in in-memory cache
                # Check if we need to evict oldest entry
                if len(self._in_memory_cache) >= self.max_entries:
                    # Find least recently used entry
                    lru_key = min(
                        self._in_memory_cache.keys(),
                        key=lambda k: self._access_count.get(k, 0)
                    )
                    del self._in_memory_cache[lru_key]
                    if lru_key in self._access_count:
                        del self._access_count[lru_key]
                    self._stats["evictions"] += 1
                    logger.debug(f"Cache entry evicted (LRU): {lru_key[:20]}...")

                # Store new entry
                entry = CacheEntry(
                    response=response,
                    timestamp=time.time(),
                    query_hash=self._generate_hash(query),
                    context_hash=self._generate_hash(context) if context else None,
                    intent=intent,
                    metadata=metadata
                )
                self._in_memory_cache[cache_key] = entry
                self._access_count[cache_key] = 1

                logger.debug(f"Response cached (in-memory): {cache_key[:20]}..., size={len(self._in_memory_cache)}")
                return True

        except Exception as e:
            logger.error(f"Cache storage error: {e}")
            return False

    def clear(self) -> None:
        """Clear all cached responses"""
        try:
            if self.use_redis and self.redis_client:
                # Get all keys with our pattern and delete them
                # (This is a simple approach; production systems might use better patterns)
                logger.info("Clearing Redis cache...")
                self.redis_client.flushdb()
            else:
                self._in_memory_cache.clear()
                self._access_count.clear()

            logger.info("LLM cache cleared")
        except Exception as e:
            logger.error(f"Cache clear error: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache hit/miss statistics
        """
        total = self._stats["total_requests"]
        hit_rate = (self._stats["hits"] / total * 100) if total > 0 else 0

        return {
            "total_requests": total,
            "cache_hits": self._stats["hits"],
            "cache_misses": self._stats["misses"],
            "hit_rate_percent": round(hit_rate, 2),
            "evictions": self._stats["evictions"],
            "in_memory_entries": len(self._in_memory_cache),
            "ttl_seconds": self.ttl,
            "using_redis": self.use_redis
        }

    def get_cache_entries(self) -> Dict[str, Any]:
        """
        Get information about cached entries (in-memory only).

        Returns:
            Dictionary with cache entry details
        """
        entries = []
        for key, entry in self._in_memory_cache.items():
            entries.append({
                "key": key[:40] + "..." if len(key) > 40 else key,
                "age_seconds": round(time.time() - entry.timestamp, 1),
                "intent": entry.intent,
                "response_length": len(entry.response)
            })

        return {
            "total_entries": len(entries),
            "entries": sorted(entries, key=lambda x: x["age_seconds"])
        }


# Global cache instance
_llm_cache: Optional[LLMCache] = None


def get_llm_cache(
    ttl_seconds: int = 3600,
    max_entries: int = 1000,
    use_redis: bool = False
) -> LLMCache:
    """
    Get or create global LLM cache instance.

    Args:
        ttl_seconds: Cache TTL in seconds
        max_entries: Maximum in-memory cache entries
        use_redis: Whether to use Redis backend

    Returns:
        LLMCache instance
    """
    global _llm_cache

    if _llm_cache is None:
        _llm_cache = LLMCache(
            ttl_seconds=ttl_seconds,
            max_entries=max_entries,
            use_redis=use_redis
        )

    return _llm_cache
