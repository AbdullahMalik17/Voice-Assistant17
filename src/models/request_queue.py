"""
RequestQueue Model
Manages request queuing during network outages with auto-retry logic
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


class RequestStatus(str, Enum):
    """Request lifecycle states"""
    QUEUED = "QUEUED"  # Waiting for network
    PROCESSING = "PROCESSING"  # Currently being processed
    COMPLETED = "COMPLETED"  # Successfully processed
    FAILED = "FAILED"  # Failed after retries
    CANCELLED = "CANCELLED"  # User cancelled


class RequestType(str, Enum):
    """Types of requests that can be queued"""
    STT_API = "STT_API"  # Speech-to-text API request
    LLM_QUERY = "LLM_QUERY"  # LLM query request
    TTS_API = "TTS_API"  # Text-to-speech API request


class QueuedRequest(BaseModel):
    """
    Queued request entity
    Represents a request waiting for network restoration
    """

    id: UUID = Field(default_factory=uuid4)
    request_type: RequestType = Field(..., description="Type of request")
    payload: Dict[str, Any] = Field(..., description="Request payload data")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    retry_count: int = Field(0, ge=0, description="Number of retry attempts")
    max_retries: int = Field(3, ge=1, le=10, description="Maximum retry attempts")
    status: RequestStatus = Field(default=RequestStatus.QUEUED)
    priority: int = Field(0, ge=0, le=10, description="Request priority (higher = more important)")
    error_message: Optional[str] = Field(None, description="Last error message if failed")
    completed_at: Optional[datetime] = Field(None, description="When request completed")

    @field_validator('created_at')
    @classmethod
    def validate_created_at(cls, v: datetime) -> datetime:
        if v > datetime.utcnow():
            raise ValueError("created_at must not be in the future")
        return v

    def to_processing(self) -> None:
        """Transition to PROCESSING state"""
        if self.status != RequestStatus.QUEUED:
            raise ValueError(f"Cannot transition to PROCESSING from {self.status}")
        self.status = RequestStatus.PROCESSING

    def to_completed(self) -> None:
        """Transition to COMPLETED state"""
        if self.status != RequestStatus.PROCESSING:
            raise ValueError(f"Cannot transition to COMPLETED from {self.status}")
        self.status = RequestStatus.COMPLETED
        self.completed_at = datetime.utcnow()

    def to_failed(self, error_message: str) -> None:
        """Transition to FAILED state"""
        self.status = RequestStatus.FAILED
        self.error_message = error_message
        self.completed_at = datetime.utcnow()

    def to_queued(self) -> None:
        """Transition back to QUEUED state (for retry)"""
        if self.status not in [RequestStatus.PROCESSING, RequestStatus.FAILED]:
            raise ValueError(f"Cannot transition to QUEUED from {self.status}")
        self.status = RequestStatus.QUEUED
        self.retry_count += 1

    def to_cancelled(self) -> None:
        """Transition to CANCELLED state"""
        if self.status == RequestStatus.COMPLETED:
            raise ValueError("Cannot cancel a completed request")
        self.status = RequestStatus.CANCELLED
        self.completed_at = datetime.utcnow()

    def can_retry(self) -> bool:
        """Check if request can be retried"""
        return (
            self.status in [RequestStatus.QUEUED, RequestStatus.FAILED]
            and self.retry_count < self.max_retries
        )

    def should_retry(self) -> bool:
        """Check if request should be retried now"""
        return (
            self.status == RequestStatus.FAILED
            and self.retry_count < self.max_retries
        )

    def get_age_seconds(self) -> float:
        """Get request age in seconds"""
        return (datetime.utcnow() - self.created_at).total_seconds()

    class Config:
        json_encoders = {
            UUID: str,
            datetime: lambda v: v.isoformat()
        }


class RequestQueue(BaseModel):
    """
    Request queue manager
    Manages collection of queued requests
    """

    id: UUID = Field(default_factory=uuid4)
    requests: list[QueuedRequest] = Field(default_factory=list)
    max_size: int = Field(10, ge=1, le=100, description="Maximum queue size")

    def add(self, request: QueuedRequest) -> None:
        """Add request to queue"""
        if len(self.requests) >= self.max_size:
            # Remove oldest completed or failed requests
            self.requests = [
                r for r in self.requests
                if r.status in [RequestStatus.QUEUED, RequestStatus.PROCESSING]
            ]

            # If still full, remove oldest queued request
            if len(self.requests) >= self.max_size:
                queued = [r for r in self.requests if r.status == RequestStatus.QUEUED]
                if queued:
                    queued.sort(key=lambda r: r.created_at)
                    self.requests.remove(queued[0])

        self.requests.append(request)

    def get_next(self) -> Optional[QueuedRequest]:
        """Get next request to process (highest priority, oldest first)"""
        queued = [r for r in self.requests if r.status == RequestStatus.QUEUED and r.can_retry()]

        if not queued:
            return None

        # Sort by priority (descending) then by created_at (ascending)
        queued.sort(key=lambda r: (-r.priority, r.created_at))
        return queued[0]

    def get_by_id(self, request_id: UUID) -> Optional[QueuedRequest]:
        """Get request by ID"""
        for request in self.requests:
            if request.id == request_id:
                return request
        return None

    def remove(self, request_id: UUID) -> bool:
        """Remove request from queue"""
        for i, request in enumerate(self.requests):
            if request.id == request_id:
                self.requests.pop(i)
                return True
        return False

    def get_pending_count(self) -> int:
        """Get count of pending requests"""
        return len([r for r in self.requests if r.status == RequestStatus.QUEUED])

    def get_processing_count(self) -> int:
        """Get count of processing requests"""
        return len([r for r in self.requests if r.status == RequestStatus.PROCESSING])

    def clear_completed(self) -> None:
        """Remove all completed and failed requests"""
        self.requests = [
            r for r in self.requests
            if r.status in [RequestStatus.QUEUED, RequestStatus.PROCESSING]
        ]

    def get_stats(self) -> Dict[str, int]:
        """Get queue statistics"""
        return {
            "total": len(self.requests),
            "queued": self.get_pending_count(),
            "processing": self.get_processing_count(),
            "completed": len([r for r in self.requests if r.status == RequestStatus.COMPLETED]),
            "failed": len([r for r in self.requests if r.status == RequestStatus.FAILED]),
            "cancelled": len([r for r in self.requests if r.status == RequestStatus.CANCELLED]),
        }

    class Config:
        json_encoders = {
            UUID: str
        }
