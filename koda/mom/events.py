"""
Mom Events - Event scheduling system
Equivalent to Pi Mono's mom/events.ts

Provides:
- Cron-based scheduling
- File system watching
- Event callbacks
"""
import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union
import logging
import os
import re

logger = logging.getLogger(__name__)


@dataclass
class ScheduledEvent:
    """A scheduled event"""
    id: str
    callback: Callable
    trigger_time: Optional[datetime] = None
    cron_expression: Optional[str] = None
    repeat: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    enabled: bool = True


class CronParser:
    """Simple cron expression parser"""

    @staticmethod
    def parse(expression: str) -> Dict[str, Any]:
        """
        Parse cron expression.

        Format: minute hour day_of_month month day_of_week

        Supports:
        - * (any value)
        - */n (every n)
        - n (specific value)
        - n-m (range)
        - n,m (list)
        """
        parts = expression.split()
        if len(parts) != 5:
            raise ValueError(f"Invalid cron expression: {expression}")

        return {
            "minute": CronParser._parse_field(parts[0], 0, 59),
            "hour": CronParser._parse_field(parts[1], 0, 23),
            "day_of_month": CronParser._parse_field(parts[2], 1, 31),
            "month": CronParser._parse_field(parts[3], 1, 12),
            "day_of_week": CronParser._parse_field(parts[4], 0, 6),
        }

    @staticmethod
    def _parse_field(field: str, min_val: int, max_val: int) -> List[int]:
        """Parse a single cron field"""
        if field == "*":
            return list(range(min_val, max_val + 1))

        if field.startswith("*/"):
            step = int(field[2:])
            return list(range(min_val, max_val + 1, step))

        if "," in field:
            values = []
            for part in field.split(","):
                values.extend(CronParser._parse_field(part, min_val, max_val))
            return sorted(set(values))

        if "-" in field:
            start, end = field.split("-")
            return list(range(int(start), int(end) + 1))

        return [int(field)]

    @staticmethod
    def get_next_run(parsed: Dict[str, Any], after: datetime) -> datetime:
        """Get next run time after given datetime"""
        next_time = after.replace(second=0, microsecond=0) + timedelta(minutes=1)

        # Search for next matching time (max 1 year ahead)
        max_iterations = 365 * 24 * 60  # minutes in a year
        for _ in range(max_iterations):
            if CronParser._matches(parsed, next_time):
                return next_time
            next_time += timedelta(minutes=1)

        raise ValueError("Could not find next run time within 1 year")

    @staticmethod
    def _matches(parsed: Dict[str, Any], dt: datetime) -> bool:
        """Check if datetime matches cron expression"""
        return (
            dt.minute in parsed["minute"] and
            dt.hour in parsed["hour"] and
            dt.day in parsed["day_of_month"] and
            dt.month in parsed["month"] and
            dt.weekday() in parsed["day_of_week"]
        )


class EventsWatcher:
    """
    Event scheduling and file watching system.

    Supports:
    - Immediate callback execution
    - One-shot scheduled callbacks
    - Periodic (cron-based) callbacks
    - File system watching

    Usage:
        watcher = EventsWatcher()

        # Schedule immediate
        watcher.schedule_immediate(my_callback)

        # Schedule one-shot
        watcher.schedule_one_shot(datetime(2024, 12, 25, 12, 0), my_callback)

        # Schedule periodic (every hour)
        watcher.schedule_periodic("0 * * * *", my_callback)

        # Watch file
        watcher.watch_file("/path/to/file", on_change_callback)

        # Start watching
        await watcher.start()
    """

    def __init__(self):
        self._events: Dict[str, ScheduledEvent] = {}
        self._file_watchers: Dict[str, Dict[str, Any]] = {}
        self._running = False
        self._event_task: Optional[asyncio.Task] = None
        self._file_task: Optional[asyncio.Task] = None
        self._event_id_counter = 0

    async def start(self) -> None:
        """Start the event watcher"""
        self._running = True
        self._event_task = asyncio.create_task(self._event_loop())
        self._file_task = asyncio.create_task(self._file_watch_loop())

    async def stop(self) -> None:
        """Stop the event watcher"""
        self._running = False

        if self._event_task:
            self._event_task.cancel()
        if self._file_task:
            self._file_task.cancel()

    def schedule_immediate(
        self,
        callback: Callable,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Schedule a callback to run immediately.

        Args:
            callback: Async or sync function to call
            metadata: Optional metadata

        Returns:
            Event ID
        """
        event_id = self._generate_id()
        event = ScheduledEvent(
            id=event_id,
            callback=callback,
            trigger_time=datetime.now(),
            repeat=False,
            metadata=metadata or {},
        )

        self._events[event_id] = event
        return event_id

    def schedule_one_shot(
        self,
        trigger_time: datetime,
        callback: Callable,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Schedule a callback to run once at a specific time.

        Args:
            trigger_time: When to run
            callback: Async or sync function to call
            metadata: Optional metadata

        Returns:
            Event ID
        """
        event_id = self._generate_id()
        event = ScheduledEvent(
            id=event_id,
            callback=callback,
            trigger_time=trigger_time,
            repeat=False,
            next_run=trigger_time,
            metadata=metadata or {},
        )

        self._events[event_id] = event
        return event_id

    def schedule_periodic(
        self,
        cron_expression: str,
        callback: Callable,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Schedule a periodic callback using cron expression.

        Args:
            cron_expression: Cron expression (e.g., "0 * * * *" for hourly)
            callback: Async or sync function to call
            metadata: Optional metadata

        Returns:
            Event ID
        """
        parsed = CronParser.parse(cron_expression)
        next_run = CronParser.get_next_run(parsed, datetime.now())

        event_id = self._generate_id()
        event = ScheduledEvent(
            id=event_id,
            callback=callback,
            cron_expression=cron_expression,
            repeat=True,
            next_run=next_run,
            metadata={**(metadata or {}), "cron_parsed": parsed},
        )

        self._events[event_id] = event
        return event_id

    def watch_file(
        self,
        path: Union[str, Path],
        callback: Callable[[str], None],
        debounce: float = 1.0
    ) -> str:
        """
        Watch a file for changes.

        Args:
            path: File path to watch
            callback: Function to call on change (receives file path)
            debounce: Debounce time in seconds

        Returns:
            Watcher ID
        """
        path = str(Path(path).resolve())
        watch_id = self._generate_id()

        self._file_watchers[watch_id] = {
            "path": path,
            "callback": callback,
            "debounce": debounce,
            "last_modified": 0,
            "last_triggered": datetime.min,
        }

        # Track initial modification time
        try:
            self._file_watchers[watch_id]["last_modified"] = os.path.getmtime(path)
        except OSError:
            pass

        return watch_id

    def watch_directory(
        self,
        path: Union[str, Path],
        callback: Callable[[str, str], None],  # path, event_type
        recursive: bool = True
    ) -> str:
        """
        Watch a directory for changes.

        Args:
            path: Directory path to watch
            callback: Function to call on change (receives path and event type)
            recursive: Watch subdirectories

        Returns:
            Watcher ID
        """
        path = str(Path(path).resolve())
        watch_id = self._generate_id()

        self._file_watchers[watch_id] = {
            "path": path,
            "callback": callback,
            "is_directory": True,
            "recursive": recursive,
            "last_triggered": datetime.min,
            "file_mtimes": {},
        }

        # Track initial mtimes
        try:
            for root, dirs, files in os.walk(path):
                for f in files:
                    fpath = os.path.join(root, f)
                    try:
                        self._file_watchers[watch_id]["file_mtimes"][fpath] = os.path.getmtime(fpath)
                    except OSError:
                        pass
                if not recursive:
                    break
        except OSError:
            pass

        return watch_id

    def cancel(self, event_id: str) -> bool:
        """
        Cancel a scheduled event or watcher.

        Args:
            event_id: Event or watcher ID

        Returns:
            True if cancelled, False if not found
        """
        if event_id in self._events:
            del self._events[event_id]
            return True

        if event_id in self._file_watchers:
            del self._file_watchers[event_id]
            return True

        return False

    def list_scheduled(self) -> List[Dict[str, Any]]:
        """List all scheduled events"""
        result = []
        for event_id, event in self._events.items():
            result.append({
                "id": event_id,
                "type": "periodic" if event.repeat else "one-shot",
                "next_run": event.next_run.isoformat() if event.next_run else None,
                "enabled": event.enabled,
            })
        return result

    def _generate_id(self) -> str:
        """Generate unique event ID"""
        self._event_id_counter += 1
        return f"event_{self._event_id_counter}_{datetime.now().timestamp()}"

    async def _event_loop(self) -> None:
        """Main event loop"""
        while self._running:
            try:
                now = datetime.now()
                events_to_run = []

                # Find events to run
                for event_id, event in list(self._events.items()):
                    if not event.enabled or not event.next_run:
                        continue

                    if event.next_run <= now:
                        events_to_run.append(event)

                # Run events
                for event in events_to_run:
                    await self._run_event(event)

                # Sleep until next event or 1 second
                next_event = self._get_next_event_time()
                if next_event:
                    sleep_time = min(1.0, (next_event - datetime.now()).total_seconds())
                    sleep_time = max(0.1, sleep_time)
                else:
                    sleep_time = 1.0

                await asyncio.sleep(sleep_time)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Event loop error: {e}")
                await asyncio.sleep(1.0)

    async def _run_event(self, event: ScheduledEvent) -> None:
        """Run a scheduled event"""
        try:
            callback = event.callback

            if asyncio.iscoroutinefunction(callback):
                await callback(event.metadata)
            else:
                callback(event.metadata)

            event.last_run = datetime.now()

            # Update next run for periodic events
            if event.repeat and event.cron_expression:
                parsed = event.metadata.get("cron_parsed")
                if parsed:
                    event.next_run = CronParser.get_next_run(parsed, datetime.now())

            # Remove one-shot events
            elif not event.repeat:
                del self._events[event.id]

        except Exception as e:
            logger.error(f"Event callback error ({event.id}): {e}")

    def _get_next_event_time(self) -> Optional[datetime]:
        """Get the next event trigger time"""
        next_time = None
        for event in self._events.values():
            if event.enabled and event.next_run:
                if next_time is None or event.next_run < next_time:
                    next_time = event.next_run
        return next_time

    async def _file_watch_loop(self) -> None:
        """File watching loop"""
        while self._running:
            try:
                for watch_id, watcher in list(self._file_watchers.items()):
                    if watcher.get("is_directory"):
                        await self._check_directory(watch_id, watcher)
                    else:
                        await self._check_file(watch_id, watcher)

                await asyncio.sleep(0.5)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"File watch error: {e}")
                await asyncio.sleep(1.0)

    async def _check_file(self, watch_id: str, watcher: Dict[str, Any]) -> None:
        """Check a single file for changes"""
        path = watcher["path"]
        try:
            current_mtime = os.path.getmtime(path)

            if current_mtime != watcher["last_modified"]:
                watcher["last_modified"] = current_mtime

                # Debounce
                now = datetime.now()
                if (now - watcher["last_triggered"]).total_seconds() >= watcher["debounce"]:
                    watcher["last_triggered"] = now

                    callback = watcher["callback"]
                    if asyncio.iscoroutinefunction(callback):
                        await callback(path)
                    else:
                        callback(path)

        except OSError:
            pass  # File might not exist

    async def _check_directory(self, watch_id: str, watcher: Dict[str, Any]) -> None:
        """Check a directory for changes"""
        path = watcher["path"]
        try:
            current_files = {}

            for root, dirs, files in os.walk(path):
                for f in files:
                    fpath = os.path.join(root, f)
                    try:
                        current_files[fpath] = os.path.getmtime(fpath)
                    except OSError:
                        pass

                if not watcher.get("recursive"):
                    break

            old_files = watcher["file_mtimes"]

            # Check for new or modified files
            for fpath, mtime in current_files.items():
                if fpath not in old_files:
                    # New file
                    await self._trigger_directory_callback(watcher, fpath, "created")
                elif mtime != old_files[fpath]:
                    # Modified file
                    await self._trigger_directory_callback(watcher, fpath, "modified")

            # Check for deleted files
            for fpath in old_files:
                if fpath not in current_files:
                    await self._trigger_directory_callback(watcher, fpath, "deleted")

            watcher["file_mtimes"] = current_files

        except OSError:
            pass

    async def _trigger_directory_callback(
        self,
        watcher: Dict[str, Any],
        path: str,
        event_type: str
    ) -> None:
        """Trigger directory callback with debouncing"""
        now = datetime.now()
        if (now - watcher["last_triggered"]).total_seconds() < 0.1:
            return

        watcher["last_triggered"] = now
        callback = watcher["callback"]

        if asyncio.iscoroutinefunction(callback):
            await callback(path, event_type)
        else:
            callback(path, event_type)
