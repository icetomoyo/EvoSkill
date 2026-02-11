"""
Timings
Equivalent to Pi Mono's packages/coding-agent/src/core/timings.ts

Performance timing and measurement.
"""
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from contextlib import contextmanager


@dataclass
class Timing:
    """Single timing measurement"""
    name: str
    start: float
    end: Optional[float] = None
    duration: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def stop(self):
        """Stop timing"""
        self.end = time.perf_counter()
        self.duration = self.end - self.start


@dataclass
class TimingReport:
    """Timing report"""
    name: str
    total_duration: float
    timings: List[Timing]
    metadata: Dict[str, Any] = field(default_factory=dict)


class Timings:
    """
    Performance timing collector.
    
    Measures and collects timing data for operations.
    
    Example:
        >>> timings = Timings("request")
        >>> with timings.measure("llm_call"):
        ...     # LLM API call
        ...     pass
        >>> with timings.measure("parsing"):
        ...     # Parse response
        ...     pass
        >>> report = timings.finish()
        >>> print(report.total_duration)
    """
    
    def __init__(self, name: str = "operation"):
        """
        Initialize timings.
        
        Args:
            name: Name of the overall operation
        """
        self.name = name
        self._start = time.perf_counter()
        self._timings: List[Timing] = []
        self._current: Optional[Timing] = None
        self._metadata: Dict[str, Any] = {}
    
    @contextmanager
    def measure(self, name: str, **metadata):
        """
        Measure a section of code.
        
        Args:
            name: Section name
            **metadata: Additional metadata
            
        Yields:
            Timing object
            
        Example:
            >>> with timings.measure("database", query="SELECT *"):
            ...     result = db.query("SELECT *")
        """
        timing = Timing(name=name, start=time.perf_counter(), metadata=metadata)
        self._current = timing
        
        try:
            yield timing
        finally:
            timing.stop()
            self._timings.append(timing)
            self._current = None
    
    def start(self, name: str, **metadata) -> Timing:
        """
        Start a timing manually.
        
        Args:
            name: Section name
            **metadata: Additional metadata
            
        Returns:
            Timing object (call .stop() when done)
        """
        timing = Timing(name=name, start=time.perf_counter(), metadata=metadata)
        self._current = timing
        return timing
    
    def stop_current(self):
        """Stop current timing"""
        if self._current:
            self._current.stop()
            self._timings.append(self._current)
            self._current = None
    
    def add_metadata(self, key: str, value: Any):
        """Add metadata to the report"""
        self._metadata[key] = value
    
    def finish(self) -> TimingReport:
        """
        Finish timing and generate report.
        
        Returns:
            TimingReport with all measurements
        """
        # Stop any running timing
        self.stop_current()
        
        total_duration = time.perf_counter() - self._start
        
        return TimingReport(
            name=self.name,
            total_duration=total_duration,
            timings=list(self._timings),
            metadata=dict(self._metadata)
        )
    
    def get_summary(self) -> str:
        """
        Get human-readable summary.
        
        Returns:
            Formatted timing summary
        """
        report = self.finish()
        
        lines = [f"Timing: {report.name}", "=" * 40]
        lines.append(f"Total: {self._format_duration(report.total_duration)}")
        lines.append("")
        
        for timing in report.timings:
            if timing.duration:
                pct = (timing.duration / report.total_duration) * 100 if report.total_duration > 0 else 0
                lines.append(
                    f"  {timing.name}: {self._format_duration(timing.duration)} ({pct:.1f}%)"
                )
                
                # Show metadata if present
                if timing.metadata:
                    for key, value in timing.metadata.items():
                        lines.append(f"    {key}: {value}")
        
        return "\n".join(lines)
    
    def _format_duration(self, seconds: float) -> str:
        """Format duration in human-readable form"""
        if seconds < 0.001:
            return f"{seconds * 1000000:.1f}µs"
        elif seconds < 1:
            return f"{seconds * 1000:.1f}ms"
        else:
            return f"{seconds:.2f}s"
    
    def reset(self):
        """Reset timings"""
        self._start = time.perf_counter()
        self._timings = []
        self._current = None
        self._metadata = {}


# Global timings storage
_global_timings: Dict[str, Timings] = {}


def start_timings(name: str = "operation") -> Timings:
    """Start new timings collection"""
    timings = Timings(name)
    _global_timings[name] = timings
    return timings


def get_timings(name: str = "operation") -> Optional[Timings]:
    """Get existing timings"""
    return _global_timings.get(name)


@contextmanager
def timed(name: str = "operation", section: Optional[str] = None):
    """
    Context manager for simple timing.
    
    Example:
        >>> with timed("my_op", "database"):
        ...     db.query()
    """
    timings = start_timings(name)
    if section:
        with timings.measure(section):
            yield timings
    else:
        yield timings
    
    report = timings.finish()
    print(f"{name}: {report.total_duration:.3f}s")


__all__ = [
    "Timings",
    "Timing",
    "TimingReport",
    "start_timings",
    "get_timings",
    "timed",
]
