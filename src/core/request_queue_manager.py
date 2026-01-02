"""
Request Queue Manager
Orchestrates request queuing during network outages with auto-retry logic
"""

import threading
import time
from typing import Any, Callable, Dict, Optional
from uuid import UUID

from ..models.request_queue import QueuedRequest, RequestQueue, RequestStatus, RequestType
from ..utils.logger import EventLogger, MetricsLogger
from ..utils.network_monitor import NetworkMonitor, get_network_monitor


class RequestQueueManager:
    """
    Manages request queue with network-aware processing and auto-retry
    Integrates NetworkMonitor for automatic request processing on restore
    """

    def __init__(
        self,
        logger: EventLogger,
        metrics_logger: MetricsLogger,
        max_queue_size: int = 10,
        check_interval_seconds: float = 5.0,
        network_monitor: Optional[NetworkMonitor] = None
    ):
        self.logger = logger
        self.metrics_logger = metrics_logger
        self.max_queue_size = max_queue_size
        self.check_interval_seconds = check_interval_seconds

        # Initialize network monitor
        self.network_monitor = network_monitor or get_network_monitor()

        # Initialize request queue
        self.queue = RequestQueue(max_size=max_queue_size)

        # Processing callbacks by request type
        self._processors: Dict[RequestType, Callable] = {}

        # Notification callback for status changes
        self._on_network_status_change: Optional[Callable[[bool], None]] = None
        self._on_queue_processing: Optional[Callable[[QueuedRequest], None]] = None

        # Background thread for monitoring
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

        # Track network status
        self._was_connected = True
        self._offline_notified = False

        self.logger.info(
            event='REQUEST_QUEUE_MANAGER_INITIALIZED',
            message='Request queue manager initialized',
            max_queue_size=max_queue_size,
            check_interval=check_interval_seconds
        )

    def register_processor(
        self,
        request_type: RequestType,
        processor: Callable[[Dict[str, Any]], Any]
    ) -> None:
        """
        Register a processor function for a request type
        Processor receives payload dict and returns result or raises exception
        """
        self._processors[request_type] = processor
        self.logger.debug(
            event='PROCESSOR_REGISTERED',
            message=f'Processor registered for {request_type.value}',
            request_type=request_type.value
        )

    def set_network_status_callback(
        self,
        callback: Callable[[bool], None]
    ) -> None:
        """
        Set callback for network status changes
        Callback receives is_connected boolean
        """
        self._on_network_status_change = callback

    def set_queue_processing_callback(
        self,
        callback: Callable[[QueuedRequest], None]
    ) -> None:
        """
        Set callback when queue processing starts
        Callback receives the request being processed
        """
        self._on_queue_processing = callback

    def is_online(self) -> bool:
        """Check current network status"""
        return self.network_monitor.is_connected()

    def enqueue(
        self,
        request_type: RequestType,
        payload: Dict[str, Any],
        priority: int = 0,
        max_retries: int = 3
    ) -> QueuedRequest:
        """
        Add request to queue
        Returns: QueuedRequest object
        """
        with self._lock:
            request = QueuedRequest(
                request_type=request_type,
                payload=payload,
                priority=priority,
                max_retries=max_retries
            )
            self.queue.add(request)

            self.logger.info(
                event='REQUEST_ENQUEUED',
                message=f'Request enqueued: {request_type.value}',
                request_id=str(request.id),
                request_type=request_type.value,
                priority=priority,
                queue_size=len(self.queue.requests)
            )

            # Record metric
            self.metrics_logger.record_metric('requests_queued', 1)

            return request

    def process_request(self, request: QueuedRequest) -> Optional[Any]:
        """
        Process a single request immediately
        Returns result or None if failed
        """
        if request.request_type not in self._processors:
            self.logger.error(
                event='NO_PROCESSOR',
                message=f'No processor for request type: {request.request_type.value}',
                request_type=request.request_type.value
            )
            request.to_failed(f"No processor for type {request.request_type.value}")
            return None

        processor = self._processors[request.request_type]

        try:
            request.to_processing()

            # Notify callback
            if self._on_queue_processing:
                self._on_queue_processing(request)

            self.logger.info(
                event='REQUEST_PROCESSING',
                message=f'Processing request: {request.request_type.value}',
                request_id=str(request.id),
                retry_count=request.retry_count
            )

            # Execute processor
            result = processor(request.payload)

            # Mark completed
            request.to_completed()

            self.logger.info(
                event='REQUEST_COMPLETED',
                message=f'Request completed: {request.request_type.value}',
                request_id=str(request.id)
            )

            # Record metric
            self.metrics_logger.record_metric('requests_completed', 1)

            return result

        except Exception as e:
            error_msg = str(e)

            if request.can_retry():
                request.to_queued()
                self.logger.warning(
                    event='REQUEST_RETRY',
                    message=f'Request will retry: {error_msg}',
                    request_id=str(request.id),
                    retry_count=request.retry_count
                )
                self.metrics_logger.record_metric('requests_retried', 1)
            else:
                request.to_failed(error_msg)
                self.logger.error(
                    event='REQUEST_FAILED',
                    message=f'Request failed: {error_msg}',
                    request_id=str(request.id),
                    retry_count=request.retry_count
                )
                self.metrics_logger.record_metric('requests_failed', 1)

            return None

    def process_queue(self) -> int:
        """
        Process all pending requests in queue
        Returns: Number of successfully processed requests
        """
        processed = 0

        while True:
            with self._lock:
                request = self.queue.get_next()
                if not request:
                    break

            # Check network before processing
            if not self.is_online():
                self.logger.info(
                    event='QUEUE_PAUSED_OFFLINE',
                    message='Queue processing paused - offline'
                )
                break

            result = self.process_request(request)
            if result is not None:
                processed += 1

        if processed > 0:
            self.logger.info(
                event='QUEUE_PROCESSED',
                message=f'Processed {processed} queued requests',
                processed_count=processed,
                remaining=self.queue.get_pending_count()
            )

        return processed

    def cancel_request(self, request_id: UUID) -> bool:
        """Cancel a pending request"""
        with self._lock:
            request = self.queue.get_by_id(request_id)
            if request and request.status in [RequestStatus.QUEUED, RequestStatus.PROCESSING]:
                request.to_cancelled()
                self.logger.info(
                    event='REQUEST_CANCELLED',
                    message=f'Request cancelled',
                    request_id=str(request_id)
                )
                self.metrics_logger.record_metric('requests_cancelled', 1)
                return True
            return False

    def cancel_all_pending(self) -> int:
        """Cancel all pending requests"""
        cancelled = 0
        with self._lock:
            for request in self.queue.requests:
                if request.status == RequestStatus.QUEUED:
                    request.to_cancelled()
                    cancelled += 1

        if cancelled > 0:
            self.logger.info(
                event='ALL_REQUESTS_CANCELLED',
                message=f'Cancelled {cancelled} pending requests',
                cancelled_count=cancelled
            )

        return cancelled

    def start_monitoring(self) -> None:
        """Start background network monitoring thread"""
        if self._monitoring:
            return

        self._monitoring = True
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True,
            name="NetworkMonitor"
        )
        self._monitor_thread.start()

        self.logger.info(
            event='MONITORING_STARTED',
            message='Network monitoring started'
        )

    def stop_monitoring(self) -> None:
        """Stop background network monitoring"""
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=2.0)
            self._monitor_thread = None

        self.logger.info(
            event='MONITORING_STOPPED',
            message='Network monitoring stopped'
        )

    def _monitor_loop(self) -> None:
        """Background monitoring loop"""
        while self._monitoring:
            try:
                is_connected = self.is_online()

                # Check for status change
                if is_connected != self._was_connected:
                    self.logger.info(
                        event='NETWORK_STATUS_CHANGED',
                        message=f'Network status: {"online" if is_connected else "offline"}',
                        is_connected=is_connected
                    )

                    # Notify callback
                    if self._on_network_status_change:
                        self._on_network_status_change(is_connected)

                    # Process queue if connection restored
                    if is_connected and not self._was_connected:
                        self._offline_notified = False
                        self.metrics_logger.record_metric('network_restored', 1)

                        # Process pending requests
                        pending = self.queue.get_pending_count()
                        if pending > 0:
                            self.logger.info(
                                event='PROCESSING_QUEUED_REQUESTS',
                                message=f'Connection restored, processing {pending} queued requests',
                                pending_count=pending
                            )
                            self.process_queue()

                    elif not is_connected and self._was_connected:
                        self.metrics_logger.record_metric('network_lost', 1)

                    self._was_connected = is_connected

                time.sleep(self.check_interval_seconds)

            except Exception as e:
                self.logger.error(
                    event='MONITOR_ERROR',
                    message=f'Monitor loop error: {str(e)}',
                    error=str(e)
                )
                time.sleep(self.check_interval_seconds)

    def get_queue_stats(self) -> Dict[str, Any]:
        """Get current queue statistics"""
        stats = self.queue.get_stats()
        stats['is_online'] = self.is_online()
        stats['monitoring'] = self._monitoring
        return stats

    def should_notify_offline(self) -> bool:
        """
        Check if offline notification should be shown
        Returns True only once per offline period
        """
        if not self.is_online() and not self._offline_notified:
            self._offline_notified = True
            return True
        return False


# Global instance
_queue_manager: Optional[RequestQueueManager] = None


def get_request_queue_manager(
    logger: EventLogger,
    metrics_logger: MetricsLogger,
    max_queue_size: int = 10,
    check_interval_seconds: float = 5.0
) -> RequestQueueManager:
    """Get or create global request queue manager"""
    global _queue_manager
    if _queue_manager is None:
        _queue_manager = RequestQueueManager(
            logger=logger,
            metrics_logger=metrics_logger,
            max_queue_size=max_queue_size,
            check_interval_seconds=check_interval_seconds
        )
    return _queue_manager


def create_request_queue_manager(
    logger: EventLogger,
    metrics_logger: MetricsLogger,
    max_queue_size: int = 10,
    check_interval_seconds: float = 5.0,
    network_monitor: Optional[NetworkMonitor] = None
) -> RequestQueueManager:
    """Factory function to create request queue manager"""
    return RequestQueueManager(
        logger=logger,
        metrics_logger=metrics_logger,
        max_queue_size=max_queue_size,
        check_interval_seconds=check_interval_seconds,
        network_monitor=network_monitor
    )
