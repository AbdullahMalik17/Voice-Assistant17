"""
Network Monitoring Utility
Monitors internet connectivity using HTTP health checks with DNS fallback
"""

import socket
from typing import Optional

import requests


class NetworkMonitor:
    """
    Network connectivity monitor
    Uses HTTP health checks with DNS fallback to detect internet connectivity
    """

    def __init__(
        self,
        health_check_url: str = "https://www.google.com",
        dns_fallback: str = "8.8.8.8",
        timeout_seconds: int = 5
    ):
        self.health_check_url = health_check_url
        self.dns_fallback = dns_fallback
        self.timeout_seconds = timeout_seconds
        self._last_status: Optional[bool] = None

    def is_connected(self) -> bool:
        """
        Check if internet is available
        Returns True if connected, False otherwise
        """
        # Try HTTP health check first
        if self._check_http():
            self._last_status = True
            return True

        # Fallback to DNS check
        if self._check_dns():
            self._last_status = True
            return True

        self._last_status = False
        return False

    def _check_http(self) -> bool:
        """Check connectivity via HTTP request"""
        try:
            response = requests.get(
                self.health_check_url,
                timeout=self.timeout_seconds,
                allow_redirects=False
            )
            # Accept any response (even errors) as proof of connectivity
            return True
        except (requests.ConnectionError, requests.Timeout, requests.RequestException):
            return False

    def _check_dns(self) -> bool:
        """Check connectivity via DNS resolution"""
        try:
            # Try to resolve DNS server
            socket.setdefaulttimeout(self.timeout_seconds)
            socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((self.dns_fallback, 53))
            return True
        except (socket.error, socket.timeout):
            return False

    def has_status_changed(self) -> bool:
        """
        Check if network status has changed since last check
        Returns True if status changed, False otherwise
        """
        current_status = self.is_connected()

        if self._last_status is None:
            # First check
            return True

        return current_status != self._last_status

    def get_last_status(self) -> Optional[bool]:
        """Get last known network status"""
        return self._last_status

    def wait_for_connection(self, max_attempts: int = 10, delay_seconds: int = 5) -> bool:
        """
        Wait for network connection to be restored
        Returns True if connection restored, False if max attempts reached
        """
        import time

        for attempt in range(max_attempts):
            if self.is_connected():
                return True

            if attempt < max_attempts - 1:
                time.sleep(delay_seconds)

        return False


# Global network monitor instance
_network_monitor: Optional[NetworkMonitor] = None


def get_network_monitor(
    health_check_url: str = "https://www.google.com",
    dns_fallback: str = "8.8.8.8",
    timeout_seconds: int = 5
) -> NetworkMonitor:
    """Get or create global network monitor instance"""
    global _network_monitor
    if _network_monitor is None:
        _network_monitor = NetworkMonitor(
            health_check_url=health_check_url,
            dns_fallback=dns_fallback,
            timeout_seconds=timeout_seconds
        )
    return _network_monitor
