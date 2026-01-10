"""
WebSocket Optimization Module
Provides connection pooling, rate limiting, and message queuing for efficient
WebSocket communication with streaming support.

Reference: https://docs.python.org/3/library/asyncio.html
"""

import asyncio
import time
import logging
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from collections import defaultdict, deque
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    """Rate limiting configuration"""
    max_requests: int = 30  # Max requests per window
    window_seconds: int = 60  # Time window in seconds
    burst_allowed: int = 5  # Allow burst up to this amount


@dataclass
class MessageQueueConfig:
    """Message queue configuration"""
    max_queue_size: int = 100  # Max messages in queue
    max_chunk_size: int = 4096  # Max bytes per chunk
    flush_interval_ms: int = 100  # Flush queue every 100ms


class RateLimiter:
    """
    Professional rate limiter using sliding window algorithm.
    Prevents DoS and abusive behavior while allowing bursts.
    """

    def __init__(self, config: RateLimitConfig):
        """
        Initialize rate limiter.

        Args:
            config: RateLimitConfig with rate limit settings
        """
        self.config = config
        self.requests: Dict[str, deque] = defaultdict(deque)
        self.blocked_until: Dict[str, float] = {}
        logger.info(
            f"RateLimiter initialized: max_requests={config.max_requests}, "
            f"window={config.window_seconds}s"
        )

    def is_allowed(self, session_id: str) -> bool:
        """
        Check if request is allowed under rate limit.

        Args:
            session_id: Client session identifier

        Returns:
            True if request is allowed, False if rate limited
        """
        now = time.time()

        # Check if session is blocked
        if session_id in self.blocked_until:
            if now < self.blocked_until[session_id]:
                logger.warning(
                    f"Session {session_id} is blocked (rate limited)",
                    extra={"blocked_until": self.blocked_until[session_id]}
                )
                return False
            else:
                # Unblock session
                del self.blocked_until[session_id]

        # Get request history for this session
        cutoff = now - self.config.window_seconds
        request_times = self.requests[session_id]

        # Remove old requests outside the window
        while request_times and request_times[0] < cutoff:
            request_times.popleft()

        # Check if limit exceeded
        if len(request_times) >= self.config.max_requests:
            # Block this session for a period
            block_duration = self.config.window_seconds // 2  # Block for half window
            self.blocked_until[session_id] = now + block_duration

            logger.warning(
                f"Rate limit exceeded for session {session_id}",
                extra={
                    "requests_in_window": len(request_times),
                    "max_allowed": self.config.max_requests,
                    "blocked_duration": block_duration
                }
            )
            return False

        # Record this request
        request_times.append(now)
        return True

    def get_stats(self, session_id: str) -> Dict[str, Any]:
        """
        Get rate limit statistics for a session.

        Args:
            session_id: Client session identifier

        Returns:
            Dictionary with rate limit stats
        """
        now = time.time()
        cutoff = now - self.config.window_seconds
        request_times = self.requests[session_id]

        # Count requests in current window
        current_requests = sum(1 for t in request_times if t >= cutoff)

        return {
            "session_id": session_id,
            "requests_in_window": current_requests,
            "max_allowed": self.config.max_requests,
            "remaining": max(0, self.config.max_requests - current_requests),
            "is_blocked": session_id in self.blocked_until,
            "window_seconds": self.config.window_seconds
        }

    def reset_session(self, session_id: str) -> None:
        """
        Reset rate limiting for a session (e.g., on disconnect).

        Args:
            session_id: Client session identifier
        """
        if session_id in self.requests:
            del self.requests[session_id]
        if session_id in self.blocked_until:
            del self.blocked_until[session_id]

        logger.debug(f"Rate limit reset for session {session_id}")


class MessageQueue:
    """
    Async message queue for WebSocket streaming.
    Handles batching, backpressure, and efficient message delivery.
    """

    def __init__(self, config: MessageQueueConfig, session_id: str):
        """
        Initialize message queue for a session.

        Args:
            config: MessageQueueConfig settings
            session_id: Session identifier
        """
        self.config = config
        self.session_id = session_id
        self.queue: asyncio.Queue = asyncio.Queue(maxsize=config.max_queue_size)
        self.pending_batch: List[str] = []
        self.batch_size = 0
        self.worker_task: Optional[asyncio.Task] = None
        self.last_flush = time.time()

    async def enqueue(self, message: str) -> bool:
        """
        Add message to queue.

        Args:
            message: Message to queue

        Returns:
            True if enqueued, False if queue full
        """
        try:
            # Check if batch should be flushed
            batch_full = (
                self.batch_size + len(message) >= self.config.max_chunk_size
            )
            time_to_flush = (
                (time.time() - self.last_flush) * 1000 >= self.config.flush_interval_ms
            )

            if batch_full or (time_to_flush and self.pending_batch):
                await self._flush_batch()

            # Add to pending batch
            self.pending_batch.append(message)
            self.batch_size += len(message)

            return True

        except asyncio.QueueFull:
            logger.warning(
                f"Message queue full for session {self.session_id}",
                extra={"queue_size": self.queue.qsize()}
            )
            return False

    async def _flush_batch(self) -> None:
        """Flush pending batch to queue."""
        if not self.pending_batch:
            return

        batched_message = "".join(self.pending_batch)
        try:
            await asyncio.wait_for(
                self.queue.put(batched_message),
                timeout=1.0
            )
            logger.debug(
                f"Flushed batch for {self.session_id}",
                extra={"batch_size": len(batched_message)}
            )
        except asyncio.TimeoutError:
            logger.error(
                f"Queue flush timeout for {self.session_id}",
                extra={"batch_size": len(batched_message)}
            )

        self.pending_batch.clear()
        self.batch_size = 0
        self.last_flush = time.time()

    async def get_batch(self, timeout: float = 1.0) -> Optional[str]:
        """
        Get next message batch from queue.

        Args:
            timeout: Wait timeout in seconds

        Returns:
            Message batch or None if timeout
        """
        try:
            message = await asyncio.wait_for(
                self.queue.get(),
                timeout=timeout
            )
            return message
        except asyncio.TimeoutError:
            return None

    def get_stats(self) -> Dict[str, Any]:
        """Get queue statistics."""
        return {
            "session_id": self.session_id,
            "queue_size": self.queue.qsize(),
            "max_queue_size": self.config.max_queue_size,
            "pending_batch_size": self.batch_size,
            "pending_messages": len(self.pending_batch)
        }

    async def close(self) -> None:
        """Close and cleanup queue."""
        # Flush any pending messages
        await self._flush_batch()

        # Clear queue
        while not self.queue.empty():
            try:
                self.queue.get_nowait()
            except asyncio.QueueEmpty:
                break

        logger.debug(f"Message queue closed for {self.session_id}")


class ConnectionPool:
    """
    Manages WebSocket connections with pooling and lifecycle management.
    Tracks active sessions and provides efficient access.
    """

    def __init__(self, max_connections: int = 1000):
        """
        Initialize connection pool.

        Args:
            max_connections: Maximum allowed simultaneous connections
        """
        self.max_connections = max_connections
        self.connections: Dict[str, Dict[str, Any]] = {}
        self.session_to_user: Dict[str, Optional[str]] = {}  # session_id -> user_id
        self.user_to_sessions: Dict[str, List[str]] = defaultdict(list)  # user_id -> session_ids

    def register_connection(
        self,
        session_id: str,
        user_id: Optional[str] = None
    ) -> bool:
        """
        Register a new WebSocket connection.

        Args:
            session_id: Unique session identifier
            user_id: Optional user identifier for session

        Returns:
            True if registered, False if pool full
        """
        if len(self.connections) >= self.max_connections:
            logger.warning(
                f"Connection pool full ({self.max_connections} max)",
                extra={"new_session": session_id}
            )
            return False

        self.connections[session_id] = {
            "user_id": user_id,
            "connected_at": datetime.utcnow().isoformat(),
            "last_activity": time.time(),
            "request_count": 0,
            "bytes_sent": 0,
            "bytes_received": 0
        }

        self.session_to_user[session_id] = user_id
        if user_id:
            self.user_to_sessions[user_id].append(session_id)

        logger.info(
            f"Connection registered: {session_id}",
            extra={
                "user_id": user_id,
                "total_connections": len(self.connections)
            }
        )

        return True

    def unregister_connection(self, session_id: str) -> None:
        """
        Unregister a WebSocket connection.

        Args:
            session_id: Session identifier to unregister
        """
        if session_id not in self.connections:
            return

        connection = self.connections[session_id]
        user_id = connection.get("user_id")

        # Update user sessions
        if user_id and user_id in self.user_to_sessions:
            self.user_to_sessions[user_id].remove(session_id)
            if not self.user_to_sessions[user_id]:
                del self.user_to_sessions[user_id]

        del self.connections[session_id]
        if session_id in self.session_to_user:
            del self.session_to_user[session_id]

        logger.info(
            f"Connection unregistered: {session_id}",
            extra={"total_connections": len(self.connections)}
        )

    def update_activity(self, session_id: str, bytes_sent: int = 0, bytes_received: int = 0) -> None:
        """
        Update connection activity statistics.

        Args:
            session_id: Session identifier
            bytes_sent: Bytes sent in this operation
            bytes_received: Bytes received in this operation
        """
        if session_id in self.connections:
            conn = self.connections[session_id]
            conn["last_activity"] = time.time()
            conn["request_count"] += 1
            conn["bytes_sent"] += bytes_sent
            conn["bytes_received"] += bytes_received

    def get_connection_stats(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get statistics for a specific connection.

        Args:
            session_id: Session identifier

        Returns:
            Connection stats or None if not found
        """
        if session_id not in self.connections:
            return None

        return self.connections[session_id].copy()

    def get_pool_stats(self) -> Dict[str, Any]:
        """
        Get overall connection pool statistics.

        Returns:
            Pool statistics
        """
        total_bytes_sent = sum(c["bytes_sent"] for c in self.connections.values())
        total_bytes_received = sum(c["bytes_received"] for c in self.connections.values())

        return {
            "total_connections": len(self.connections),
            "max_connections": self.max_connections,
            "capacity_used_percent": (len(self.connections) / self.max_connections * 100),
            "unique_users": len(self.user_to_sessions),
            "total_bytes_sent": total_bytes_sent,
            "total_bytes_received": total_bytes_received,
            "avg_bytes_per_connection": (
                (total_bytes_sent + total_bytes_received) / len(self.connections)
                if self.connections else 0
            )
        }

    def get_idle_sessions(self, timeout_seconds: int = 300) -> List[str]:
        """
        Get sessions that have been idle for longer than timeout.

        Args:
            timeout_seconds: Idle timeout in seconds

        Returns:
            List of idle session IDs
        """
        now = time.time()
        idle_sessions = []

        for session_id, conn in self.connections.items():
            idle_time = now - conn["last_activity"]
            if idle_time > timeout_seconds:
                idle_sessions.append(session_id)

        return idle_sessions


class WebSocketOptimizationManager:
    """
    Central manager for WebSocket optimizations.
    Combines rate limiting, message queuing, and connection pooling.
    """

    def __init__(
        self,
        rate_limit_config: Optional[RateLimitConfig] = None,
        message_queue_config: Optional[MessageQueueConfig] = None,
        max_connections: int = 1000
    ):
        """
        Initialize optimization manager.

        Args:
            rate_limit_config: Rate limiting configuration
            message_queue_config: Message queue configuration
            max_connections: Max concurrent connections
        """
        self.rate_limiter = RateLimiter(
            rate_limit_config or RateLimitConfig()
        )
        self.message_queue_config = (
            message_queue_config or MessageQueueConfig()
        )
        self.connection_pool = ConnectionPool(max_connections)
        self.message_queues: Dict[str, MessageQueue] = {}

        logger.info(
            "WebSocketOptimizationManager initialized",
            extra={
                "max_connections": max_connections,
                "rate_limit_window": self.rate_limiter.config.window_seconds,
                "max_requests": self.rate_limiter.config.max_requests
            }
        )

    def register_session(
        self,
        session_id: str,
        user_id: Optional[str] = None
    ) -> bool:
        """
        Register new WebSocket session.

        Args:
            session_id: Session identifier
            user_id: Optional user ID

        Returns:
            True if registered successfully
        """
        # Register in connection pool
        if not self.connection_pool.register_connection(session_id, user_id):
            return False

        # Create message queue for this session
        self.message_queues[session_id] = MessageQueue(
            self.message_queue_config,
            session_id
        )

        return True

    def unregister_session(self, session_id: str) -> None:
        """
        Unregister WebSocket session.

        Args:
            session_id: Session identifier
        """
        self.connection_pool.unregister_connection(session_id)

        if session_id in self.message_queues:
            # Note: In async context, should await close()
            del self.message_queues[session_id]

        self.rate_limiter.reset_session(session_id)

    def check_rate_limit(self, session_id: str) -> bool:
        """
        Check if session is within rate limits.

        Args:
            session_id: Session identifier

        Returns:
            True if allowed, False if rate limited
        """
        return self.rate_limiter.is_allowed(session_id)

    def get_message_queue(self, session_id: str) -> Optional[MessageQueue]:
        """
        Get message queue for a session.

        Args:
            session_id: Session identifier

        Returns:
            MessageQueue or None if not found
        """
        return self.message_queues.get(session_id)

    def get_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive statistics across all optimizations.

        Returns:
            Statistics dictionary
        """
        return {
            "connection_pool": self.connection_pool.get_pool_stats(),
            "message_queues": {
                sid: queue.get_stats()
                for sid, queue in self.message_queues.items()
            },
            "rate_limiter": {
                "sessions_blocked": len(self.rate_limiter.blocked_until),
                "total_tracked_sessions": len(self.rate_limiter.requests)
            }
        }
