"""
Event Logging Infrastructure for Voice Assistant
Provides structured JSON logging with rotation and metrics export
"""

import json
import logging
import logging.handlers
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from pythonjsonlogger import jsonlogger


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter with timestamp and structured fields"""

    def add_fields(self, log_record: Dict[str, Any], record: logging.LogRecord, message_dict: Dict[str, Any]) -> None:
        super().add_fields(log_record, record, message_dict)

        # Add timestamp in ISO format
        log_record['timestamp'] = datetime.utcnow().isoformat() + 'Z'

        # Add standard fields
        log_record['level'] = record.levelname
        log_record['module'] = record.module
        log_record['function'] = record.funcName
        log_record['line'] = record.lineno

        # Move message to standard field
        if 'message' in log_record:
            log_record['msg'] = log_record.pop('message')


class EventLogger:
    """
    Structured event logger for voice assistant
    Supports JSON and text formats with log rotation
    """

    def __init__(
        self,
        name: str,
        log_dir: Path,
        level: str = "INFO",
        format_type: str = "json",
        max_size_mb: int = 10,
        backup_count: int = 5,
        console_output: bool = True
    ):
        self.name = name
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Create logger
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, level.upper()))
        self.logger.propagate = False  # Don't propagate to root logger

        # Clear existing handlers
        self.logger.handlers.clear()

        # Add file handler with rotation
        log_file = self.log_dir / f"{name}.log"
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_size_mb * 1024 * 1024,
            backupCount=backup_count,
            encoding='utf-8'
        )

        # Set formatter
        if format_type == "json":
            formatter = CustomJsonFormatter(
                '%(timestamp)s %(level)s %(name)s %(message)s'
            )
        else:
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(funcName)s:%(lineno)d - %(message)s'
            )

        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

        # Add console handler if requested
        if console_output:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)

    def _log_with_extra(self, level: str, event: str, message: str, **kwargs) -> None:
        """Log with structured extra fields"""
        extra = {
            'event': event,
            **kwargs
        }

        log_method = getattr(self.logger, level.lower())
        log_method(message, extra=extra)

    def debug(self, event: str, message: str, **kwargs) -> None:
        """Log debug event"""
        self._log_with_extra('DEBUG', event, message, **kwargs)

    def info(self, event: str, message: str, **kwargs) -> None:
        """Log info event"""
        self._log_with_extra('INFO', event, message, **kwargs)

    def warning(self, event: str, message: str, **kwargs) -> None:
        """Log warning event"""
        self._log_with_extra('WARNING', event, message, **kwargs)

    def error(self, event: str, message: str, **kwargs) -> None:
        """Log error event"""
        self._log_with_extra('ERROR', event, message, **kwargs)

    def critical(self, event: str, message: str, **kwargs) -> None:
        """Log critical event"""
        self._log_with_extra('CRITICAL', event, message, **kwargs)

    # Convenience methods for common events
    def wake_word_detected(self, confidence: float, duration_ms: int) -> None:
        """Log wake word detection event"""
        self.info(
            event='WAKE_WORD_DETECTED',
            message='Wake word detected',
            confidence=confidence,
            audio_duration_ms=duration_ms
        )

    def stt_completed(self, text: str, confidence: float, duration_ms: int, mode: str) -> None:
        """Log STT completion event"""
        self.info(
            event='STT_COMPLETED',
            message='Speech-to-text completed',
            transcribed_text=text,
            confidence=confidence,
            processing_time_ms=duration_ms,
            mode=mode
        )

    def intent_classified(self, intent_type: str, confidence: float, entities: Dict[str, Any]) -> None:
        """Log intent classification event"""
        self.info(
            event='INTENT_CLASSIFIED',
            message='Intent classified',
            intent_type=intent_type,
            confidence=confidence,
            entities=entities
        )

    def llm_response_generated(self, response_length: int, duration_ms: int, mode: str) -> None:
        """Log LLM response generation event"""
        self.info(
            event='LLM_RESPONSE_GENERATED',
            message='LLM response generated',
            response_length=response_length,
            processing_time_ms=duration_ms,
            mode=mode
        )

    def tts_completed(self, text_length: int, audio_duration_ms: int, mode: str) -> None:
        """Log TTS completion event"""
        self.info(
            event='TTS_COMPLETED',
            message='Text-to-speech completed',
            text_length=text_length,
            audio_duration_ms=audio_duration_ms,
            mode=mode
        )

    def action_executed(self, action_type: str, success: bool, duration_ms: int) -> None:
        """Log action execution event"""
        self.info(
            event='ACTION_EXECUTED',
            message='Action executed',
            action_type=action_type,
            success=success,
            execution_time_ms=duration_ms
        )

    def context_updated(self, exchanges_count: int, timeout_seconds: int) -> None:
        """Log context update event"""
        self.info(
            event='CONTEXT_UPDATED',
            message='Conversation context updated',
            exchanges_count=exchanges_count,
            timeout_seconds=timeout_seconds
        )

    def network_status_changed(self, is_online: bool) -> None:
        """Log network status change event"""
        self.warning(
            event='NETWORK_STATUS_CHANGED',
            message=f'Network status changed to {"online" if is_online else "offline"}',
            is_online=is_online
        )

    def request_queued(self, request_type: str, queue_size: int) -> None:
        """Log request queuing event"""
        self.warning(
            event='REQUEST_QUEUED',
            message='Request queued due to network outage',
            request_type=request_type,
            queue_size=queue_size
        )

    def error_occurred(self, error_type: str, error_message: str, component: str) -> None:
        """Log error event"""
        self.error(
            event='ERROR_OCCURRED',
            message=error_message,
            error_type=error_type,
            component=component
        )


class MetricsLogger:
    """
    Metrics logger for performance tracking
    Exports metrics in Prometheus-compatible format
    """

    def __init__(self, log_dir: Path, export_interval_seconds: int = 60):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.export_interval_seconds = export_interval_seconds

        # Metrics storage
        self.metrics: Dict[str, list] = {
            'wake_word_latency_ms': [],
            'stt_latency_ms': [],
            'llm_latency_ms': [],
            'tts_latency_ms': [],
            'end_to_end_latency_ms': [],
            'intent_confidence': [],
            'stt_confidence': [],
        }

        # Create metrics file
        self.metrics_file = self.log_dir / "metrics.jsonl"

    def record_metric(self, metric_name: str, value: float) -> None:
        """Record a metric value"""
        if metric_name in self.metrics:
            self.metrics[metric_name].append({
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'value': value
            })

    def export_metrics(self) -> None:
        """Export metrics to file"""
        if not any(self.metrics.values()):
            return

        with open(self.metrics_file, 'a') as f:
            for metric_name, values in self.metrics.items():
                if values:
                    # Calculate statistics
                    values_only = [v['value'] for v in values]
                    stats = {
                        'metric': metric_name,
                        'timestamp': datetime.utcnow().isoformat() + 'Z',
                        'count': len(values_only),
                        'min': min(values_only),
                        'max': max(values_only),
                        'avg': sum(values_only) / len(values_only),
                        'p50': self._percentile(values_only, 50),
                        'p95': self._percentile(values_only, 95),
                        'p99': self._percentile(values_only, 99),
                    }
                    f.write(json.dumps(stats) + '\n')

        # Clear metrics after export
        for key in self.metrics:
            self.metrics[key].clear()

    def _percentile(self, values: list, percentile: int) -> float:
        """Calculate percentile of values"""
        if not values:
            return 0.0
        sorted_values = sorted(values)
        index = int(len(sorted_values) * percentile / 100)
        return sorted_values[min(index, len(sorted_values) - 1)]


# Global logger instances
_event_logger: Optional[EventLogger] = None
_metrics_logger: Optional[MetricsLogger] = None


def get_event_logger(
    name: str = "voice_assistant",
    log_dir: Path = Path("logs"),
    level: str = "INFO",
    format_type: str = "json",
    max_size_mb: int = 10,
    backup_count: int = 5,
    console_output: bool = True
) -> EventLogger:
    """Get or create global event logger instance"""
    global _event_logger
    if _event_logger is None:
        _event_logger = EventLogger(
            name=name,
            log_dir=log_dir,
            level=level,
            format_type=format_type,
            max_size_mb=max_size_mb,
            backup_count=backup_count,
            console_output=console_output
        )
    return _event_logger


def get_metrics_logger(
    log_dir: Path = Path("logs"),
    export_interval_seconds: int = 60
) -> MetricsLogger:
    """Get or create global metrics logger instance"""
    global _metrics_logger
    if _metrics_logger is None:
        _metrics_logger = MetricsLogger(
            log_dir=log_dir,
            export_interval_seconds=export_interval_seconds
        )
    return _metrics_logger
