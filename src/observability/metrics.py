"""
Metrics Module
Provides Prometheus-compatible metrics for monitoring the Voice Assistant.
"""

import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, Generator, List, Optional

from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    Info,
    CollectorRegistry,
    generate_latest,
    CONTENT_TYPE_LATEST
)


# ============================================================================
# Metric Definitions
# ============================================================================

# Default registry
REGISTRY = CollectorRegistry()

# Latency histograms (in seconds)
STT_LATENCY = Histogram(
    'voice_assistant_stt_latency_seconds',
    'Speech-to-text processing latency',
    ['mode', 'model'],
    buckets=[0.1, 0.25, 0.5, 0.75, 1.0, 2.0, 5.0],
    registry=REGISTRY
)

INTENT_LATENCY = Histogram(
    'voice_assistant_intent_latency_seconds',
    'Intent classification latency',
    ['intent_type'],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5],
    registry=REGISTRY
)

LLM_LATENCY = Histogram(
    'voice_assistant_llm_latency_seconds',
    'LLM response generation latency',
    ['provider', 'model'],
    buckets=[0.5, 1.0, 2.0, 3.0, 5.0, 10.0],
    registry=REGISTRY
)

TTS_LATENCY = Histogram(
    'voice_assistant_tts_latency_seconds',
    'Text-to-speech latency',
    ['provider'],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.0],
    registry=REGISTRY
)

E2E_LATENCY = Histogram(
    'voice_assistant_e2e_latency_seconds',
    'End-to-end response latency (wake word to speech output)',
    [],
    buckets=[1.0, 2.0, 3.0, 5.0, 10.0],
    registry=REGISTRY
)

PREPROCESSING_LATENCY = Histogram(
    'voice_assistant_preprocessing_latency_seconds',
    'Audio preprocessing latency',
    ['method'],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5],
    registry=REGISTRY
)

MEMORY_RETRIEVAL_LATENCY = Histogram(
    'voice_assistant_memory_retrieval_latency_seconds',
    'Semantic memory retrieval latency',
    [],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5],
    registry=REGISTRY
)

PLAN_GENERATION_LATENCY = Histogram(
    'voice_assistant_plan_generation_latency_seconds',
    'Agentic plan generation latency',
    [],
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0],
    registry=REGISTRY
)

# Counters
REQUEST_COUNT = Counter(
    'voice_assistant_requests_total',
    'Total number of requests',
    ['intent_type', 'status'],
    registry=REGISTRY
)

ERROR_COUNT = Counter(
    'voice_assistant_errors_total',
    'Total number of errors',
    ['component', 'error_type'],
    registry=REGISTRY
)

TOOL_CALLS_COUNT = Counter(
    'voice_assistant_tool_calls_total',
    'Total tool invocations',
    ['tool_name', 'status'],
    registry=REGISTRY
)

CONFIRMATION_COUNT = Counter(
    'voice_assistant_confirmations_total',
    'User confirmations for sensitive actions',
    ['action', 'confirmed'],
    registry=REGISTRY
)

# Gauges
ACTIVE_SESSIONS = Gauge(
    'voice_assistant_active_sessions',
    'Number of active conversation sessions',
    registry=REGISTRY
)

MEMORY_ENTRIES = Gauge(
    'voice_assistant_memory_entries',
    'Number of entries in semantic memory',
    registry=REGISTRY
)

STT_CONFIDENCE = Gauge(
    'voice_assistant_stt_confidence',
    'Latest STT confidence score',
    registry=REGISTRY
)

INTENT_CONFIDENCE = Gauge(
    'voice_assistant_intent_confidence',
    'Latest intent classification confidence',
    registry=REGISTRY
)

# Info
BUILD_INFO = Info(
    'voice_assistant_build',
    'Build information',
    registry=REGISTRY
)


@dataclass
class MetricSnapshot:
    """Snapshot of current metric values"""
    timestamp: datetime = field(default_factory=datetime.now)
    stt_latency_p95: float = 0.0
    llm_latency_p95: float = 0.0
    e2e_latency_p95: float = 0.0
    request_count: int = 0
    error_count: int = 0
    active_sessions: int = 0
    memory_entries: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "stt_latency_p95_ms": self.stt_latency_p95 * 1000,
            "llm_latency_p95_ms": self.llm_latency_p95 * 1000,
            "e2e_latency_p95_ms": self.e2e_latency_p95 * 1000,
            "request_count": self.request_count,
            "error_count": self.error_count,
            "active_sessions": self.active_sessions,
            "memory_entries": self.memory_entries
        }


class MetricsCollector:
    """
    Central metrics collector for the Voice Assistant.

    Provides:
    - Prometheus metric collection and export
    - Latency timing helpers
    - Metric snapshots for dashboards
    - Alert threshold checking
    """

    def __init__(
        self,
        version: str = "2.0.0",
        enable_prometheus: bool = True
    ):
        self.version = version
        self.enable_prometheus = enable_prometheus
        self._start_time = datetime.now()

        # Set build info
        if enable_prometheus:
            BUILD_INFO.info({
                'version': version,
                'start_time': self._start_time.isoformat()
            })

        # Internal counters for snapshot
        self._request_count = 0
        self._error_count = 0

    @contextmanager
    def time_stt(
        self,
        mode: str = "local",
        model: str = "whisper-base"
    ) -> Generator[None, None, None]:
        """Time STT processing"""
        start = time.time()
        try:
            yield
        finally:
            if self.enable_prometheus:
                STT_LATENCY.labels(mode=mode, model=model).observe(time.time() - start)

    @contextmanager
    def time_intent(
        self,
        intent_type: str = "unknown"
    ) -> Generator[None, None, None]:
        """Time intent classification"""
        start = time.time()
        try:
            yield
        finally:
            if self.enable_prometheus:
                INTENT_LATENCY.labels(intent_type=intent_type).observe(time.time() - start)

    @contextmanager
    def time_llm(
        self,
        provider: str = "gemini",
        model: str = "gemini-1.5-flash"
    ) -> Generator[None, None, None]:
        """Time LLM response generation"""
        start = time.time()
        try:
            yield
        finally:
            if self.enable_prometheus:
                LLM_LATENCY.labels(provider=provider, model=model).observe(time.time() - start)

    @contextmanager
    def time_tts(
        self,
        provider: str = "elevenlabs"
    ) -> Generator[None, None, None]:
        """Time TTS generation"""
        start = time.time()
        try:
            yield
        finally:
            if self.enable_prometheus:
                TTS_LATENCY.labels(provider=provider).observe(time.time() - start)

    @contextmanager
    def time_e2e(self) -> Generator[None, None, None]:
        """Time end-to-end request"""
        start = time.time()
        try:
            yield
        finally:
            if self.enable_prometheus:
                E2E_LATENCY.observe(time.time() - start)

    @contextmanager
    def time_preprocessing(
        self,
        method: str = "spectral_gating"
    ) -> Generator[None, None, None]:
        """Time audio preprocessing"""
        start = time.time()
        try:
            yield
        finally:
            if self.enable_prometheus:
                PREPROCESSING_LATENCY.labels(method=method).observe(time.time() - start)

    @contextmanager
    def time_memory_retrieval(self) -> Generator[None, None, None]:
        """Time semantic memory retrieval"""
        start = time.time()
        try:
            yield
        finally:
            if self.enable_prometheus:
                MEMORY_RETRIEVAL_LATENCY.observe(time.time() - start)

    @contextmanager
    def time_plan_generation(self) -> Generator[None, None, None]:
        """Time plan generation"""
        start = time.time()
        try:
            yield
        finally:
            if self.enable_prometheus:
                PLAN_GENERATION_LATENCY.observe(time.time() - start)

    def record_request(
        self,
        intent_type: str = "unknown",
        status: str = "success"
    ) -> None:
        """Record a completed request"""
        self._request_count += 1
        if self.enable_prometheus:
            REQUEST_COUNT.labels(intent_type=intent_type, status=status).inc()

    def record_error(
        self,
        component: str,
        error_type: str = "unknown"
    ) -> None:
        """Record an error"""
        self._error_count += 1
        if self.enable_prometheus:
            ERROR_COUNT.labels(component=component, error_type=error_type).inc()

    def record_tool_call(
        self,
        tool_name: str,
        success: bool = True
    ) -> None:
        """Record a tool invocation"""
        if self.enable_prometheus:
            status = "success" if success else "failure"
            TOOL_CALLS_COUNT.labels(tool_name=tool_name, status=status).inc()

    def record_confirmation(
        self,
        action: str,
        confirmed: bool
    ) -> None:
        """Record a user confirmation"""
        if self.enable_prometheus:
            CONFIRMATION_COUNT.labels(
                action=action,
                confirmed=str(confirmed).lower()
            ).inc()

    def set_active_sessions(self, count: int) -> None:
        """Update active session count"""
        if self.enable_prometheus:
            ACTIVE_SESSIONS.set(count)

    def set_memory_entries(self, count: int) -> None:
        """Update memory entry count"""
        if self.enable_prometheus:
            MEMORY_ENTRIES.set(count)

    def set_stt_confidence(self, confidence: float) -> None:
        """Update latest STT confidence"""
        if self.enable_prometheus:
            STT_CONFIDENCE.set(confidence)

    def set_intent_confidence(self, confidence: float) -> None:
        """Update latest intent confidence"""
        if self.enable_prometheus:
            INTENT_CONFIDENCE.set(confidence)

    def get_prometheus_metrics(self) -> bytes:
        """Get metrics in Prometheus format"""
        return generate_latest(REGISTRY)

    def get_content_type(self) -> str:
        """Get Prometheus content type"""
        return CONTENT_TYPE_LATEST

    def get_snapshot(self) -> MetricSnapshot:
        """Get current metric snapshot"""
        return MetricSnapshot(
            timestamp=datetime.now(),
            request_count=self._request_count,
            error_count=self._error_count
        )

    def get_uptime_seconds(self) -> float:
        """Get service uptime in seconds"""
        return (datetime.now() - self._start_time).total_seconds()


# Global metrics collector instance
_metrics_collector: Optional[MetricsCollector] = None


def create_metrics_collector(
    version: str = "2.0.0",
    enable_prometheus: bool = True
) -> MetricsCollector:
    """Create or get the global metrics collector"""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector(
            version=version,
            enable_prometheus=enable_prometheus
        )
    return _metrics_collector


def get_metrics_collector() -> Optional[MetricsCollector]:
    """Get the global metrics collector"""
    return _metrics_collector
