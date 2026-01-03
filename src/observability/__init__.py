"""
Observability Module
Provides metrics, tracing, and health check capabilities for the Voice Assistant.
"""

from .metrics import (
    MetricsCollector,
    create_metrics_collector,
    STT_LATENCY,
    INTENT_LATENCY,
    LLM_LATENCY,
    TTS_LATENCY,
    E2E_LATENCY,
    REQUEST_COUNT,
    ERROR_COUNT,
    ACTIVE_SESSIONS,
    MEMORY_ENTRIES
)
from .tracing import (
    TracingContext,
    Span,
    create_trace,
    get_current_trace
)
from .health import (
    HealthCheck,
    HealthStatus,
    ComponentHealth,
    create_health_check
)

__all__ = [
    'MetricsCollector',
    'create_metrics_collector',
    'TracingContext',
    'Span',
    'create_trace',
    'get_current_trace',
    'HealthCheck',
    'HealthStatus',
    'ComponentHealth',
    'create_health_check',
    # Metrics
    'STT_LATENCY',
    'INTENT_LATENCY',
    'LLM_LATENCY',
    'TTS_LATENCY',
    'E2E_LATENCY',
    'REQUEST_COUNT',
    'ERROR_COUNT',
    'ACTIVE_SESSIONS',
    'MEMORY_ENTRIES'
]
