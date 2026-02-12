"""
Mom Log - Structured logging with rich output
Equivalent to Pi Mono's mom/log.ts

Provides structured logging with:
- JSON output support
- Rich console output
- Log levels
- Context fields
"""
import json
import logging
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, TextIO, Union
from enum import Enum
import threading


class LogLevel(Enum):
    """Log levels"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class LogEntry:
    """A single log entry"""
    timestamp: datetime
    level: LogLevel
    message: str
    context: Dict[str, Any] = field(default_factory=dict)
    source: Optional[str] = None
    trace_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "level": self.level.value,
            "message": self.message,
            "context": self.context,
            "source": self.source,
            "trace_id": self.trace_id,
        }

    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict())


class StructuredLogger:
    """
    Structured logger with rich output.

    Supports:
    - JSON output for machine parsing
    - Rich console output with colors
    - Context fields
    - Log levels
    - File output

    Usage:
        logger = StructuredLogger("my-app")

        # Basic logging
        logger.info("Started processing")
        logger.error("Failed to connect", {"host": "localhost", "port": 8080})

        # With context
        logger.set_context({"service": "api", "version": "1.0"})
        logger.info("Request received", {"path": "/users"})

        # Rich output
        logger.set_rich_output(True)
        logger.info("Processing complete", {"items": 100, "time_ms": 150})
    """

    # Color codes for rich output
    COLORS = {
        "debug": "\033[36m",     # Cyan
        "info": "\033[32m",      # Green
        "warning": "\033[33m",   # Yellow
        "error": "\033[31m",     # Red
        "critical": "\033[35m",  # Magenta
        "reset": "\033[0m",
        "bold": "\033[1m",
        "dim": "\033[2m",
    }

    def __init__(
        self,
        name: str,
        level: LogLevel = LogLevel.INFO,
        output: Optional[Union[TextIO, Path]] = None,
        rich_output: bool = True,
        json_output: bool = False
    ):
        """
        Initialize logger.

        Args:
            name: Logger name
            level: Minimum log level
            output: Output stream or file path
            rich_output: Use colors and formatting
            json_output: Output as JSON
        """
        self.name = name
        self.level = level
        self.rich_output = rich_output and sys.stdout.isatty()
        self.json_output = json_output

        # Context
        self._context: Dict[str, Any] = {}
        self._trace_id: Optional[str] = None

        # Output
        self._output: TextIO
        self._close_output = False

        if output is None:
            self._output = sys.stdout
        elif isinstance(output, Path):
            self._output = output.open("a")
            self._close_output = True
        else:
            self._output = output

        # Thread lock for thread safety
        self._lock = threading.Lock()

    def set_level(self, level: LogLevel) -> None:
        """Set minimum log level"""
        self.level = level

    def set_context(self, context: Dict[str, Any]) -> None:
        """Set persistent context for all log entries"""
        self._context.update(context)

    def clear_context(self) -> None:
        """Clear persistent context"""
        self._context.clear()

    def set_trace_id(self, trace_id: Optional[str]) -> None:
        """Set trace ID for request tracking"""
        self._trace_id = trace_id

    def set_rich_output(self, enabled: bool) -> None:
        """Enable/disable rich output"""
        self.rich_output = enabled and sys.stdout.isatty()

    def set_json_output(self, enabled: bool) -> None:
        """Enable/disable JSON output"""
        self.json_output = enabled

    def debug(self, message: str, context: Optional[Dict[str, Any]] = None) -> None:
        """Log debug message"""
        self._log(LogLevel.DEBUG, message, context)

    def info(self, message: str, context: Optional[Dict[str, Any]] = None) -> None:
        """Log info message"""
        self._log(LogLevel.INFO, message, context)

    def warning(self, message: str, context: Optional[Dict[str, Any]] = None) -> None:
        """Log warning message"""
        self._log(LogLevel.WARNING, message, context)

    def error(self, message: str, context: Optional[Dict[str, Any]] = None) -> None:
        """Log error message"""
        self._log(LogLevel.ERROR, message, context)

    def critical(self, message: str, context: Optional[Dict[str, Any]] = None) -> None:
        """Log critical message"""
        self._log(LogLevel.CRITICAL, message, context)

    def log(self, level: LogLevel, message: str, context: Optional[Dict[str, Any]] = None) -> None:
        """Log with specific level"""
        self._log(level, message, context)

    def _log(
        self,
        level: LogLevel,
        message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Internal logging method"""
        # Check level
        if self._level_value(level) < self._level_value(self.level):
            return

        # Build entry
        entry = LogEntry(
            timestamp=datetime.now(),
            level=level,
            message=message,
            context={**self._context, **(context or {})},
            source=self.name,
            trace_id=self._trace_id,
        )

        # Format and write
        with self._lock:
            if self.json_output:
                self._output.write(entry.to_json() + "\n")
            else:
                self._output.write(self._format_rich(entry) + "\n")

            self._output.flush()

    def _level_value(self, level: LogLevel) -> int:
        """Get numeric level value"""
        values = {
            LogLevel.DEBUG: 0,
            LogLevel.INFO: 1,
            LogLevel.WARNING: 2,
            LogLevel.ERROR: 3,
            LogLevel.CRITICAL: 4,
        }
        return values.get(level, 0)

    def _format_rich(self, entry: LogEntry) -> str:
        """Format entry with rich output"""
        if not self.rich_output:
            return self._format_plain(entry)

        c = self.COLORS

        # Timestamp
        timestamp_str = entry.timestamp.strftime("%H:%M:%S.%f")[:-3]
        timestamp = f"{c['dim']}{timestamp_str}{c['reset']}"

        # Level with color
        level_str = entry.level.value.upper().ljust(8)
        level_color = c.get(entry.level.value, "")
        level = f"{level_color}{c['bold']}{level_str}{c['reset']}"

        # Source
        source = f"{c['dim']}[{entry.source}]{c['reset']}" if entry.source else ""

        # Trace ID
        trace = f"{c['dim']}<{entry.trace_id[:8]}>{c['reset']}" if entry.trace_id else ""

        # Message
        message = entry.message

        # Context
        context_str = ""
        if entry.context:
            parts = []
            for k, v in entry.context.items():
                if isinstance(v, str) and len(v) > 50:
                    v = v[:47] + "..."
                parts.append(f"{c['dim']}{k}={c['reset']}{v}")
            context_str = " ".join(parts)

        # Combine
        return f"{timestamp} {level} {source} {trace} {message} {context_str}".strip()

    def _format_plain(self, entry: LogEntry) -> str:
        """Format entry as plain text"""
        timestamp = entry.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        level = entry.level.value.upper().ljust(8)
        source = f"[{entry.source}]" if entry.source else ""
        trace = f"<{entry.trace_id[:8]}>" if entry.trace_id else ""

        context_str = ""
        if entry.context:
            context_str = " " + " ".join(f"{k}={v}" for k, v in entry.context.items())

        return f"{timestamp} {level} {source} {trace} {entry.message}{context_str}".strip()

    def close(self) -> None:
        """Close the logger"""
        if self._close_output:
            self._output.close()

    def __enter__(self) -> "StructuredLogger":
        return self

    def __exit__(self, *args) -> None:
        self.close()


# Convenience functions
_loggers: Dict[str, StructuredLogger] = {}


def get_logger(name: str, **kwargs) -> StructuredLogger:
    """Get or create a logger by name"""
    if name not in _loggers:
        _loggers[name] = StructuredLogger(name, **kwargs)
    return _loggers[name]


def configure_logging(
    level: LogLevel = LogLevel.INFO,
    rich_output: bool = True,
    json_output: bool = False,
    output: Optional[Union[TextIO, Path]] = None
) -> None:
    """Configure default logging"""
    # Configure root logger
    root = get_logger("root", level=level, rich_output=rich_output, json_output=json_output, output=output)

    # Also configure Python's logging to use our logger
    handler = logging.Handler()
    handler.emit = lambda record: root.log(
        LogLevel(record.levelname.lower()),
        record.getMessage(),
        {"file": record.filename, "line": record.lineno}
    )

    logging.root.handlers = [handler]
    logging.root.setLevel(getattr(logging, level.value.upper()))


# Rich console utilities
def print_table(
    headers: List[str],
    rows: List[List[Any]],
    title: Optional[str] = None
) -> str:
    """Format a table for console output"""
    # Calculate column widths
    widths = [len(str(h)) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(str(cell)))

    # Build border
    border = "+" + "+".join("-" * (w + 2) for w in widths) + "+"

    # Build lines
    lines = [border]

    if title:
        lines.insert(0, f"\n  {title}\n")

    # Header
    header_cells = [str(h).center(w) for h, w in zip(headers, widths)]
    lines.append("| " + " | ".join(header_cells) + " |")
    lines.append(border.replace("-", "="))

    # Rows
    for row in rows:
        cells = [str(c).ljust(w) for c, w in zip(row, widths)]
        lines.append("| " + " | ".join(cells) + " |")

    lines.append(border)

    return "\n".join(lines)


def print_kv(data: Dict[str, Any], indent: int = 2) -> str:
    """Format key-value pairs for console output"""
    lines = []
    for k, v in data.items():
        if isinstance(v, dict):
            lines.append(f"{' ' * indent}{k}:")
            lines.append(print_kv(v, indent + 2))
        elif isinstance(v, list):
            lines.append(f"{' ' * indent}{k}:")
            for item in v:
                lines.append(f"{' ' * (indent + 2)}- {item}")
        else:
            lines.append(f"{' ' * indent}{k}: {v}")
    return "\n".join(lines)
