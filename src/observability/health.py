"""
Health Check Module
Provides health check endpoint and component status monitoring.
"""

import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class HealthStatus(str, Enum):
    """Health status levels"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class ComponentHealth:
    """Health status of a single component"""
    name: str
    status: HealthStatus
    message: str = ""
    latency_ms: float = 0.0
    last_check: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "latency_ms": self.latency_ms,
            "last_check": self.last_check.isoformat(),
            "metadata": self.metadata
        }


@dataclass
class HealthCheckResult:
    """Result of a complete health check"""
    status: HealthStatus
    version: str
    uptime_seconds: float
    components: Dict[str, ComponentHealth] = field(default_factory=dict)
    metrics: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "version": self.version,
            "uptime_seconds": round(self.uptime_seconds, 2),
            "timestamp": self.timestamp.isoformat(),
            "components": {
                name: comp.to_dict()
                for name, comp in self.components.items()
            },
            "metrics": self.metrics
        }

    def is_healthy(self) -> bool:
        """Check if overall status is healthy"""
        return self.status == HealthStatus.HEALTHY

    def is_ready(self) -> bool:
        """Check if service is ready to accept requests"""
        return self.status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED]


# Type for health check functions
HealthCheckFunc = Callable[[], ComponentHealth]


class HealthCheck:
    """
    Health check manager for the Voice Assistant.

    Provides:
    - Component health registration
    - Aggregated health status
    - Kubernetes-compatible liveness/readiness probes
    - Custom health check functions
    """

    def __init__(
        self,
        version: str = "2.0.0",
        start_time: Optional[datetime] = None
    ):
        self.version = version
        self.start_time = start_time or datetime.now()
        self._components: Dict[str, HealthCheckFunc] = {}
        self._component_cache: Dict[str, ComponentHealth] = {}
        self._cache_ttl_seconds = 10.0
        self._last_check_time: Optional[datetime] = None

    def register_component(
        self,
        name: str,
        check_func: HealthCheckFunc
    ) -> None:
        """Register a component health check function"""
        self._components[name] = check_func

    def unregister_component(self, name: str) -> None:
        """Unregister a component"""
        if name in self._components:
            del self._components[name]
        if name in self._component_cache:
            del self._component_cache[name]

    def check_component(self, name: str) -> ComponentHealth:
        """Check health of a specific component"""
        if name not in self._components:
            return ComponentHealth(
                name=name,
                status=HealthStatus.UNKNOWN,
                message="Component not registered"
            )

        try:
            start = time.time()
            health = self._components[name]()
            health.latency_ms = (time.time() - start) * 1000
            health.last_check = datetime.now()
            self._component_cache[name] = health
            return health
        except Exception as e:
            return ComponentHealth(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=f"Health check failed: {str(e)}"
            )

    def check_all(self, use_cache: bool = True) -> HealthCheckResult:
        """
        Check health of all registered components.

        Args:
            use_cache: Whether to use cached results if within TTL

        Returns:
            HealthCheckResult with aggregated status
        """
        components = {}
        now = datetime.now()

        for name in self._components:
            # Check cache
            if use_cache and name in self._component_cache:
                cached = self._component_cache[name]
                cache_age = (now - cached.last_check).total_seconds()
                if cache_age < self._cache_ttl_seconds:
                    components[name] = cached
                    continue

            components[name] = self.check_component(name)

        # Determine overall status
        overall_status = self._aggregate_status(list(components.values()))

        # Get uptime
        uptime = (now - self.start_time).total_seconds()

        return HealthCheckResult(
            status=overall_status,
            version=self.version,
            uptime_seconds=uptime,
            components=components,
            timestamp=now
        )

    def _aggregate_status(self, components: List[ComponentHealth]) -> HealthStatus:
        """Aggregate component statuses into overall status"""
        if not components:
            return HealthStatus.HEALTHY

        statuses = [c.status for c in components]

        if all(s == HealthStatus.HEALTHY for s in statuses):
            return HealthStatus.HEALTHY
        elif any(s == HealthStatus.UNHEALTHY for s in statuses):
            return HealthStatus.UNHEALTHY
        elif any(s == HealthStatus.DEGRADED for s in statuses):
            return HealthStatus.DEGRADED
        else:
            return HealthStatus.UNKNOWN

    def liveness(self) -> bool:
        """Kubernetes liveness probe - is the service alive?"""
        # Simple check - if we can run this code, we're alive
        return True

    def readiness(self) -> bool:
        """Kubernetes readiness probe - is the service ready for traffic?"""
        result = self.check_all(use_cache=True)
        return result.is_ready()

    def get_uptime_seconds(self) -> float:
        """Get service uptime"""
        return (datetime.now() - self.start_time).total_seconds()


# ============================================================================
# Default Health Checks
# ============================================================================

def create_stt_health_check(stt_service) -> HealthCheckFunc:
    """Create health check for STT service"""
    def check() -> ComponentHealth:
        try:
            # Check if model is loaded
            if hasattr(stt_service, 'whisper_model') and stt_service.whisper_model is None:
                if stt_service.mode == "local":
                    return ComponentHealth(
                        name="stt",
                        status=HealthStatus.UNHEALTHY,
                        message="Whisper model not loaded"
                    )

            return ComponentHealth(
                name="stt",
                status=HealthStatus.HEALTHY,
                message="STT service operational",
                metadata={"mode": stt_service.mode}
            )
        except Exception as e:
            return ComponentHealth(
                name="stt",
                status=HealthStatus.UNHEALTHY,
                message=str(e)
            )
    return check


def create_llm_health_check(llm_service) -> HealthCheckFunc:
    """Create health check for LLM service"""
    def check() -> ComponentHealth:
        try:
            # Check API connectivity (could do a lightweight ping)
            if hasattr(llm_service, 'client') and llm_service.client is None:
                return ComponentHealth(
                    name="llm",
                    status=HealthStatus.DEGRADED,
                    message="LLM API client not initialized"
                )

            return ComponentHealth(
                name="llm",
                status=HealthStatus.HEALTHY,
                message="LLM service operational",
                metadata={
                    "provider": getattr(llm_service, 'provider', 'unknown'),
                    "model": getattr(llm_service, 'model', 'unknown')
                }
            )
        except Exception as e:
            return ComponentHealth(
                name="llm",
                status=HealthStatus.UNHEALTHY,
                message=str(e)
            )
    return check


def create_memory_health_check(memory_service) -> HealthCheckFunc:
    """Create health check for semantic memory"""
    def check() -> ComponentHealth:
        try:
            stats = memory_service.get_stats()
            return ComponentHealth(
                name="memory",
                status=HealthStatus.HEALTHY,
                message="Semantic memory operational",
                metadata=stats
            )
        except Exception as e:
            return ComponentHealth(
                name="memory",
                status=HealthStatus.UNHEALTHY,
                message=str(e)
            )
    return check


def create_network_health_check(check_url: str = "https://www.google.com") -> HealthCheckFunc:
    """Create health check for network connectivity"""
    def check() -> ComponentHealth:
        import requests
        try:
            start = time.time()
            response = requests.get(check_url, timeout=5)
            latency = (time.time() - start) * 1000

            if response.status_code == 200:
                return ComponentHealth(
                    name="network",
                    status=HealthStatus.HEALTHY,
                    message="Network connected",
                    latency_ms=latency
                )
            else:
                return ComponentHealth(
                    name="network",
                    status=HealthStatus.DEGRADED,
                    message=f"Network returned {response.status_code}",
                    latency_ms=latency
                )
        except requests.exceptions.Timeout:
            return ComponentHealth(
                name="network",
                status=HealthStatus.DEGRADED,
                message="Network timeout"
            )
        except Exception as e:
            return ComponentHealth(
                name="network",
                status=HealthStatus.UNHEALTHY,
                message=f"Network error: {str(e)}"
            )
    return check


# Global health check instance
_health_check: Optional[HealthCheck] = None


def create_health_check(
    version: str = "2.0.0"
) -> HealthCheck:
    """Create the global health check instance"""
    global _health_check
    _health_check = HealthCheck(version=version)
    return _health_check


def get_health_check() -> Optional[HealthCheck]:
    """Get the global health check instance"""
    return _health_check
