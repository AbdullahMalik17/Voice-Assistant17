"""
SystemStatus Model
Current system state information accessible for informational queries
"""

from datetime import datetime, timedelta
from typing import Optional

import psutil
from pydantic import BaseModel, Field, field_validator


class SystemStatus(BaseModel):
    """
    System status entity
    Provides current system state information
    """

    timestamp: datetime = Field(default_factory=datetime.utcnow)
    cpu_percent: float = Field(..., ge=0.0, le=100.0, description="CPU usage percentage")
    cpu_temp_celsius: Optional[float] = Field(None, description="CPU temperature (if available)")
    memory_percent: float = Field(..., ge=0.0, le=100.0, description="RAM usage percentage")
    memory_available_mb: int = Field(..., ge=0, description="Available RAM in MB")
    disk_percent: float = Field(..., ge=0.0, le=100.0, description="Disk usage percentage")
    disk_available_gb: float = Field(..., ge=0.0, description="Available disk space in GB")
    running_processes: int = Field(..., ge=0, description="Number of processes")
    uptime_seconds: int = Field(..., ge=0, description="System uptime")
    network_connected: bool = Field(..., description="Internet connectivity status")

    @field_validator('timestamp')
    @classmethod
    def validate_timestamp(cls, v: datetime) -> datetime:
        if v > datetime.utcnow():
            raise ValueError("timestamp must not be in the future")
        return v

    @classmethod
    def capture(cls, network_connected: bool = True) -> "SystemStatus":
        """
        Capture current system status
        Factory method to create SystemStatus from current system state
        """
        # CPU information
        cpu_percent = psutil.cpu_percent(interval=0.1)

        # CPU temperature (may not be available on all systems)
        cpu_temp = None
        try:
            temps = psutil.sensors_temperatures()
            if 'coretemp' in temps:
                cpu_temp = temps['coretemp'][0].current
            elif 'cpu_thermal' in temps:
                cpu_temp = temps['cpu_thermal'][0].current
        except (AttributeError, KeyError, IndexError):
            pass  # Temperature not available

        # Memory information
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        memory_available_mb = memory.available // (1024 * 1024)

        # Disk information
        disk = psutil.disk_usage('/')
        disk_percent = disk.percent
        disk_available_gb = disk.free / (1024 ** 3)

        # Process count
        running_processes = len(psutil.pids())

        # System uptime
        boot_time = psutil.boot_time()
        uptime_seconds = int(datetime.utcnow().timestamp() - boot_time)

        return cls(
            cpu_percent=cpu_percent,
            cpu_temp_celsius=cpu_temp,
            memory_percent=memory_percent,
            memory_available_mb=memory_available_mb,
            disk_percent=disk_percent,
            disk_available_gb=disk_available_gb,
            running_processes=running_processes,
            uptime_seconds=uptime_seconds,
            network_connected=network_connected
        )

    def to_human_readable(self) -> str:
        """Convert status to human-readable string"""
        parts = [
            f"CPU: {self.cpu_percent:.1f}%",
            f"Memory: {self.memory_percent:.1f}% ({self.memory_available_mb} MB available)",
            f"Disk: {self.disk_percent:.1f}% ({self.disk_available_gb:.1f} GB available)",
        ]

        if self.cpu_temp_celsius is not None:
            parts.insert(1, f"CPU Temp: {self.cpu_temp_celsius:.1f}°C")

        parts.extend([
            f"Processes: {self.running_processes}",
            f"Uptime: {self._format_uptime()}",
            f"Network: {'Connected' if self.network_connected else 'Disconnected'}"
        ])

        return ", ".join(parts)

        def _format_uptime(self) -> str:
            """Format uptime as human-readable string"""     
            uptime = timedelta(seconds=self.uptime_seconds)  
            days = uptime.days
            hours = uptime.seconds // 3600
            minutes = (uptime.seconds % 3600) // 60
    
            if days > 0:
                return f"{days}d {hours}h {minutes}m"        
            elif hours > 0:
                return f"{hours}h {minutes}m"
            else:
                return f"{minutes}m"

# Cache for system status to avoid excessive polling
_status_cache: Optional[SystemStatus] = None
_cache_timestamp: Optional[datetime] = None
_cache_ttl_seconds = 5  # Cache for 5 seconds


def get_system_status(network_connected: bool = True, force_refresh: bool = False) -> SystemStatus:
    """
    Get current system status with caching
    Cached for 5 seconds to avoid excessive system calls
    """
    global _status_cache, _cache_timestamp

    now = datetime.utcnow()

    # Check if cache is valid
    if not force_refresh and _status_cache is not None and _cache_timestamp is not None:
        time_since_cache = (now - _cache_timestamp).total_seconds()
        if time_since_cache < _cache_ttl_seconds:
            return _status_cache

    # Capture new status
    _status_cache = SystemStatus.capture(network_connected=network_connected)
    _cache_timestamp = now

    return _status_cache
