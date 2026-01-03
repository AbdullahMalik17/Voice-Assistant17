"""
Tracing Module
Provides distributed tracing for request tracking and debugging.
"""

import contextvars
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Generator, List, Optional

# Context variable for current trace
_current_trace: contextvars.ContextVar[Optional['TracingContext']] = contextvars.ContextVar(
    'current_trace', default=None
)


@dataclass
class Span:
    """A single span in a trace"""
    span_id: str
    name: str
    trace_id: str
    parent_span_id: Optional[str] = None
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    duration_ms: float = 0.0
    status: str = "ok"
    attributes: Dict[str, Any] = field(default_factory=dict)
    events: List[Dict[str, Any]] = field(default_factory=list)

    def finish(self, status: str = "ok") -> None:
        """Finish the span"""
        self.end_time = datetime.now()
        self.duration_ms = (self.end_time - self.start_time).total_seconds() * 1000
        self.status = status

    def add_event(self, name: str, attributes: Optional[Dict[str, Any]] = None) -> None:
        """Add an event to the span"""
        self.events.append({
            "name": name,
            "timestamp": datetime.now().isoformat(),
            "attributes": attributes or {}
        })

    def set_attribute(self, key: str, value: Any) -> None:
        """Set a span attribute"""
        self.attributes[key] = value

    def to_dict(self) -> Dict[str, Any]:
        return {
            "span_id": self.span_id,
            "name": self.name,
            "trace_id": self.trace_id,
            "parent_span_id": self.parent_span_id,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_ms": self.duration_ms,
            "status": self.status,
            "attributes": self.attributes,
            "events": self.events
        }


@dataclass
class TracingContext:
    """
    Context for a distributed trace.

    Tracks all spans for a single request/interaction.
    """
    trace_id: str
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    start_time: datetime = field(default_factory=datetime.now)
    spans: List[Span] = field(default_factory=list)
    current_span: Optional[Span] = None
    attributes: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> 'TracingContext':
        """Create a new tracing context"""
        return cls(
            trace_id=str(uuid.uuid4()),
            session_id=session_id,
            user_id=user_id
        )

    @contextmanager
    def span(
        self,
        name: str,
        attributes: Optional[Dict[str, Any]] = None
    ) -> Generator[Span, None, None]:
        """
        Create and manage a span.

        Usage:
            with trace.span("stt_processing") as span:
                span.set_attribute("model", "whisper-base")
                result = process_audio()
        """
        parent_span_id = self.current_span.span_id if self.current_span else None

        span = Span(
            span_id=str(uuid.uuid4()),
            name=name,
            trace_id=self.trace_id,
            parent_span_id=parent_span_id,
            attributes=attributes or {}
        )

        self.spans.append(span)
        previous_span = self.current_span
        self.current_span = span

        try:
            yield span
            span.finish("ok")
        except Exception as e:
            span.set_attribute("error", str(e))
            span.finish("error")
            raise
        finally:
            self.current_span = previous_span

    def add_attribute(self, key: str, value: Any) -> None:
        """Add a trace-level attribute"""
        self.attributes[key] = value

    def get_duration_ms(self) -> float:
        """Get total trace duration"""
        if not self.spans:
            return 0.0
        return (datetime.now() - self.start_time).total_seconds() * 1000

    def get_root_span(self) -> Optional[Span]:
        """Get the root span"""
        for span in self.spans:
            if span.parent_span_id is None:
                return span
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "start_time": self.start_time.isoformat(),
            "duration_ms": self.get_duration_ms(),
            "attributes": self.attributes,
            "spans": [s.to_dict() for s in self.spans]
        }

    def to_json_log(self) -> str:
        """Format trace for JSON logging"""
        import json
        return json.dumps(self.to_dict(), default=str)


class TraceExporter:
    """
    Base class for trace exporters.

    Implement subclasses for different backends (Jaeger, console, file).
    """

    def export(self, trace: TracingContext) -> None:
        """Export a completed trace"""
        raise NotImplementedError


class ConsoleExporter(TraceExporter):
    """Export traces to console (for debugging)"""

    def export(self, trace: TracingContext) -> None:
        print(f"\n=== Trace {trace.trace_id} ===")
        print(f"Duration: {trace.get_duration_ms():.2f}ms")
        print(f"Session: {trace.session_id}")

        for span in trace.spans:
            indent = "  " if span.parent_span_id else ""
            status_icon = "+" if span.status == "ok" else "x"
            print(f"{indent}[{status_icon}] {span.name}: {span.duration_ms:.2f}ms")

            for key, value in span.attributes.items():
                print(f"{indent}    {key}: {value}")


class FileExporter(TraceExporter):
    """Export traces to a file"""

    def __init__(self, file_path: str):
        self.file_path = file_path

    def export(self, trace: TracingContext) -> None:
        with open(self.file_path, 'a') as f:
            f.write(trace.to_json_log() + "\n")


class TracingManager:
    """
    Manages trace lifecycle and export.

    Provides:
    - Trace creation and context management
    - Multiple exporter support
    - Automatic trace export on completion
    """

    def __init__(
        self,
        exporters: Optional[List[TraceExporter]] = None,
        sample_rate: float = 1.0
    ):
        self.exporters = exporters or []
        self.sample_rate = sample_rate
        self._traces: Dict[str, TracingContext] = {}

    def add_exporter(self, exporter: TraceExporter) -> None:
        """Add a trace exporter"""
        self.exporters.append(exporter)

    @contextmanager
    def trace(
        self,
        name: str = "request",
        session_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Generator[TracingContext, None, None]:
        """
        Create and manage a trace.

        Usage:
            with tracing.trace("voice_request", session_id="abc") as trace:
                with trace.span("stt"):
                    process_audio()
        """
        import random
        if random.random() > self.sample_rate:
            # Skip tracing for this request
            yield TracingContext.create(session_id, user_id)
            return

        ctx = TracingContext.create(session_id, user_id)
        self._traces[ctx.trace_id] = ctx

        # Set as current trace
        token = _current_trace.set(ctx)

        try:
            # Create root span
            with ctx.span(name):
                yield ctx
        finally:
            # Reset current trace
            _current_trace.reset(token)

            # Export trace
            for exporter in self.exporters:
                try:
                    exporter.export(ctx)
                except Exception:
                    pass

            # Cleanup
            if ctx.trace_id in self._traces:
                del self._traces[ctx.trace_id]

    def get_trace(self, trace_id: str) -> Optional[TracingContext]:
        """Get a trace by ID"""
        return self._traces.get(trace_id)


# Global tracing manager
_tracing_manager: Optional[TracingManager] = None


def create_trace(
    name: str = "request",
    session_id: Optional[str] = None,
    user_id: Optional[str] = None
) -> TracingContext:
    """Create a new trace context"""
    ctx = TracingContext.create(session_id, user_id)
    _current_trace.set(ctx)
    return ctx


def get_current_trace() -> Optional[TracingContext]:
    """Get the current trace context"""
    return _current_trace.get()


def get_trace_id() -> Optional[str]:
    """Get the current trace ID"""
    ctx = _current_trace.get()
    return ctx.trace_id if ctx else None


def create_tracing_manager(
    enable_console: bool = False,
    file_path: Optional[str] = None,
    sample_rate: float = 1.0
) -> TracingManager:
    """Create the global tracing manager"""
    global _tracing_manager

    exporters = []
    if enable_console:
        exporters.append(ConsoleExporter())
    if file_path:
        exporters.append(FileExporter(file_path))

    _tracing_manager = TracingManager(
        exporters=exporters,
        sample_rate=sample_rate
    )
    return _tracing_manager


def get_tracing_manager() -> Optional[TracingManager]:
    """Get the global tracing manager"""
    return _tracing_manager
