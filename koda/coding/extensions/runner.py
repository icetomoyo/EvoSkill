"""
Extension Runner - Extension lifecycle management and execution
Equivalent to Pi Mono's extension-runner.ts

Provides:
- Extension lifecycle management
- Hook execution with error isolation
- Timeout control
- Event dispatching
"""
import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Set
import traceback

from koda.coding.extensions.types import (
    Extension,
    ExtensionAPI,
    ExtensionConfig,
    ExtensionEvent,
    ExtensionEventType,
    ExtensionManifest,
    HookPriority,
    HookRegistration,
    EventSubscription,
)
from koda.coding.extensions.loader import ExtensionLoader, get_extension_loader


@dataclass
class RunnerStats:
    """Extension runner statistics"""
    extensions_loaded: int = 0
    extensions_active: int = 0
    hooks_registered: int = 0
    events_emitted: int = 0
    hooks_executed: int = 0
    errors_caught: int = 0


@dataclass
class ExtensionState:
    """Runtime state for an extension"""
    extension: Extension
    api: ExtensionAPI
    config: ExtensionConfig
    active: bool = False
    error_count: int = 0
    last_error: Optional[str] = None


class ExtensionRunner:
    """
    Extension runner for managing extension lifecycle and execution.

    Features:
    - Load and activate extensions
    - Execute hooks with error isolation
    - Timeout control for hooks
    - Event dispatching to subscribers
    - Extension dependency management
    """

    def __init__(
        self,
        loader: Optional[ExtensionLoader] = None,
        default_timeout: float = 30.0,
        max_errors_before_disable: int = 5
    ):
        """
        Initialize extension runner.

        Args:
            loader: Extension loader to use
            default_timeout: Default timeout for hook execution
            max_errors_before_disable: Max errors before auto-disabling extension
        """
        self.loader = loader or get_extension_loader()
        self.default_timeout = default_timeout
        self.max_errors_before_disable = max_errors_before_disable

        # Extension states
        self._extensions: Dict[str, ExtensionState] = {}

        # Hook registrations by event type
        self._hooks: Dict[ExtensionEventType, List[HookRegistration]] = {}

        # Event subscriptions
        self._subscriptions: List[EventSubscription] = []

        # Stats
        self._stats = RunnerStats()

        # Running flag
        self._running = False

    @property
    def stats(self) -> RunnerStats:
        """Get runner statistics"""
        return self._stats

    @property
    def is_running(self) -> bool:
        """Check if runner is active"""
        return self._running

    def discover_and_load(self) -> Dict[str, Extension]:
        """
        Discover and load all extensions.

        Returns:
            Dictionary of loaded extensions
        """
        # Discover extensions
        self.loader.discover()

        # Load in dependency order
        loaded = self.loader.load_all()

        for name, extension in loaded.items():
            self._register_extension(name, extension)

        return loaded

    def load_extension(
        self,
        name: str,
        config: Optional[ExtensionConfig] = None
    ) -> Optional[Extension]:
        """
        Load and register a specific extension.

        Args:
            name: Extension name
            config: Extension configuration

        Returns:
            Loaded extension or None
        """
        extension = self.loader.load(name, config)
        if extension:
            self._register_extension(name, extension, config)
        return extension

    def _register_extension(
        self,
        name: str,
        extension: Extension,
        config: Optional[ExtensionConfig] = None
    ) -> None:
        """Register a loaded extension"""
        api = ExtensionAPI(registry=self)
        state = ExtensionState(
            extension=extension,
            api=api,
            config=config or ExtensionConfig(),
        )

        self._extensions[name] = state
        self._stats.extensions_loaded += 1

    def activate_all(self) -> None:
        """Activate all loaded extensions"""
        self._running = True

        for name, state in self._extensions.items():
            try:
                state.extension.activate(state.api)
                state.active = True
                self._stats.extensions_active += 1

                # Register default hooks from extension
                self._register_extension_hooks(state.extension, name)

            except Exception as e:
                state.last_error = str(e)
                state.error_count += 1
                self._stats.errors_caught += 1
                self._emit_error_event(name, "activate", str(e))

    def activate_extension(self, name: str) -> bool:
        """
        Activate a specific extension.

        Args:
            name: Extension name

        Returns:
            True if activated successfully
        """
        state = self._extensions.get(name)
        if not state:
            return False

        try:
            state.extension.activate(state.api)
            state.active = True
            self._stats.extensions_active += 1
            self._register_extension_hooks(state.extension, name)
            return True

        except Exception as e:
            state.last_error = str(e)
            state.error_count += 1
            self._stats.errors_caught += 1
            self._emit_error_event(name, "activate", str(e))
            return False

    def _register_extension_hooks(self, extension: Extension, name: str) -> None:
        """Register default hooks from extension methods"""
        # Check for hook method overrides and register them
        hooks_to_register = [
            (ExtensionEventType.USER_MESSAGE, "on_user_message"),
            (ExtensionEventType.ASSISTANT_MESSAGE, "on_assistant_message"),
            (ExtensionEventType.TOOL_CALL_START, "on_tool_call"),
            (ExtensionEventType.TOOL_CALL_END, "on_tool_result"),
            (ExtensionEventType.LLM_START, "on_llm_start"),
            (ExtensionEventType.LLM_COMPLETE, "on_llm_complete"),
            (ExtensionEventType.CONTEXT_COMPACT_END, "on_context_compact"),
            (ExtensionEventType.SESSION_START, "on_session_start"),
            (ExtensionEventType.SESSION_END, "on_session_end"),
            (ExtensionEventType.EXTENSION_ERROR, "on_error"),
        ]

        base_class_methods = dir(Extension)

        for event_type, method_name in hooks_to_register:
            method = getattr(extension, method_name, None)
            if method and method_name not in base_class_methods:
                # Method is overridden, register it
                self.register_hook(
                    event_type,
                    method,
                    priority=extension._config.priority if hasattr(extension, '_config') else HookPriority.NORMAL.value,
                    extension_name=name
                )

    def deactivate_all(self) -> None:
        """Deactivate all extensions"""
        for name, state in list(self._extensions.items()):
            self.deactivate_extension(name)

        self._running = False

    def deactivate_extension(self, name: str) -> bool:
        """
        Deactivate a specific extension.

        Args:
            name: Extension name

        Returns:
            True if deactivated successfully
        """
        state = self._extensions.get(name)
        if not state:
            return False

        try:
            state.extension.deactivate()
            state.active = False
            self._stats.extensions_active -= 1

            # Unregister hooks
            self._unregister_extension_hooks(name)
            return True

        except Exception as e:
            state.last_error = str(e)
            self._emit_error_event(name, "deactivate", str(e))
            return False

    def _unregister_extension_hooks(self, extension_name: str) -> None:
        """Unregister all hooks from an extension"""
        for event_type in self._hooks:
            self._hooks[event_type] = [
                h for h in self._hooks[event_type]
                if h.extension_name != extension_name
            ]

    def register_hook(
        self,
        event_type: ExtensionEventType,
        callback: Callable,
        priority: int = HookPriority.NORMAL.value,
        extension_name: Optional[str] = None
    ) -> None:
        """
        Register a hook for an event type.

        Args:
            event_type: Type of event to hook
            callback: Function to call
            priority: Hook priority (lower = higher priority)
            extension_name: Name of registering extension
        """
        registration = HookRegistration(
            event_type=event_type,
            callback=callback,
            priority=priority,
            extension_name=extension_name,
        )

        if event_type not in self._hooks:
            self._hooks[event_type] = []

        self._hooks[event_type].append(registration)
        self._hooks[event_type].sort(key=lambda h: h.priority)
        self._stats.hooks_registered += 1

    def unregister_hook(
        self,
        event_type: ExtensionEventType,
        callback: Callable
    ) -> None:
        """Unregister a hook"""
        if event_type in self._hooks:
            self._hooks[event_type] = [
                h for h in self._hooks[event_type]
                if h.callback != callback
            ]

    def subscribe(
        self,
        event_types: List[ExtensionEventType],
        callback: Callable[[ExtensionEvent], None],
        filter: Optional[Callable[[ExtensionEvent], bool]] = None
    ) -> EventSubscription:
        """
        Subscribe to extension events.

        Args:
            event_types: Types of events to subscribe to
            callback: Function to call when event occurs
            filter: Optional filter function

        Returns:
            Subscription object
        """
        subscription = EventSubscription(
            event_types=event_types,
            callback=callback,
            filter=filter,
        )

        self._subscriptions.append(subscription)
        return subscription

    def unsubscribe(self, subscription: EventSubscription) -> None:
        """Unsubscribe from events"""
        if subscription in self._subscriptions:
            self._subscriptions.remove(subscription)

    async def execute_hooks(
        self,
        event_type: ExtensionEventType,
        data: Any,
        timeout: Optional[float] = None
    ) -> Any:
        """
        Execute all hooks for an event type.

        Hooks are executed in priority order.
        Each hook can modify data.
        If a hook returns None, the event is cancelled.

        Args:
            event_type: Type of event
            data: Event data
            timeout: Timeout for hook execution

        Returns:
            Modified data or None if cancelled
        """
        hooks = self._hooks.get(event_type, [])
        if not hooks:
            return data

        timeout = timeout or self.default_timeout
        current_data = data

        for registration in hooks:
            # Check if extension is still active
            if registration.extension_name:
                state = self._extensions.get(registration.extension_name)
                if not state or not state.active:
                    continue

            try:
                # Execute hook with timeout
                result = await self._execute_with_timeout(
                    registration.callback,
                    current_data,
                    timeout
                )

                if result is None:
                    # Event cancelled
                    return None

                current_data = result
                self._stats.hooks_executed += 1

            except asyncio.TimeoutError:
                self._handle_hook_error(
                    registration.extension_name,
                    f"Hook timeout after {timeout}s"
                )

            except Exception as e:
                self._handle_hook_error(
                    registration.extension_name,
                    str(e)
                )

        return current_data

    async def _execute_with_timeout(
        self,
        callback: Callable,
        data: Any,
        timeout: float
    ) -> Any:
        """Execute callback with timeout"""
        if asyncio.iscoroutinefunction(callback):
            return await asyncio.wait_for(callback(data), timeout=timeout)
        else:
            # Run sync in executor
            loop = asyncio.get_event_loop()
            return await asyncio.wait_for(
                loop.run_in_executor(None, callback, data),
                timeout=timeout
            )

    def _handle_hook_error(self, extension_name: Optional[str], error: str) -> None:
        """Handle hook execution error"""
        self._stats.errors_caught += 1

        if extension_name:
            state = self._extensions.get(extension_name)
            if state:
                state.error_count += 1
                state.last_error = error

                # Auto-disable if too many errors
                if state.error_count >= self.max_errors_before_disable:
                    self.deactivate_extension(extension_name)

        self._emit_error_event(extension_name, "hook", error)

    def emit_event(self, event: ExtensionEvent) -> None:
        """
        Emit an event to all subscribers.

        Args:
            event: Event to emit
        """
        self._stats.events_emitted += 1

        # Dispatch to subscribers
        for subscription in self._subscriptions:
            if subscription.matches(event):
                try:
                    subscription.callback(event)
                except Exception as e:
                    print(f"Event subscriber error: {e}")

    def _emit_error_event(
        self,
        extension_name: Optional[str],
        context: str,
        error: str
    ) -> None:
        """Emit an error event"""
        event = ExtensionEvent(
            type=ExtensionEventType.EXTENSION_ERROR,
            data={
                "extension": extension_name,
                "context": context,
                "error": error,
            },
            source=extension_name,
        )
        self.emit_event(event)

    # Convenience methods for common event types

    async def on_user_message(self, content: str) -> Optional[str]:
        """Execute hooks for user message"""
        return await self.execute_hooks(
            ExtensionEventType.USER_MESSAGE,
            content
        )

    async def on_assistant_message(self, content: str) -> Optional[str]:
        """Execute hooks for assistant message"""
        return await self.execute_hooks(
            ExtensionEventType.ASSISTANT_MESSAGE,
            content
        )

    async def on_tool_call(
        self,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Execute hooks for tool call"""
        return await self.execute_hooks(
            ExtensionEventType.TOOL_CALL_START,
            {"tool": tool_name, "arguments": arguments}
        )

    async def on_tool_result(
        self,
        tool_name: str,
        result: Any
    ) -> Any:
        """Execute hooks for tool result"""
        return await self.execute_hooks(
            ExtensionEventType.TOOL_CALL_END,
            {"tool": tool_name, "result": result}
        )

    def get_extensions(self) -> Dict[str, ExtensionState]:
        """Get all extension states"""
        return self._extensions.copy()

    def get_extension(self, name: str) -> Optional[Extension]:
        """Get extension by name"""
        state = self._extensions.get(name)
        return state.extension if state else None

    def is_extension_active(self, name: str) -> bool:
        """Check if extension is active"""
        state = self._extensions.get(name)
        return state.active if state else False

    async def execute_concurrent(
        self,
        event_type: ExtensionEventType,
        data: Any,
        timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Execute hooks concurrently and collect results from all extensions.

        Unlike execute_hooks which chains results, this runs all hooks
        in parallel with the same input data.

        Args:
            event_type: Type of event
            data: Event data
            timeout: Timeout for each hook

        Returns:
            Dict mapping extension names to their results
        """
        hooks = self._hooks.get(event_type, [])
        if not hooks:
            return {}

        timeout = timeout or self.default_timeout
        results: Dict[str, Any] = {}

        # Create tasks for all hooks
        tasks = []
        for registration in hooks:
            if registration.extension_name:
                state = self._extensions.get(registration.extension_name)
                if not state or not state.active:
                    continue

            tasks.append((
                registration.extension_name or "anonymous",
                self._execute_with_timeout(registration.callback, data, timeout)
            ))

        # Run all tasks concurrently
        for name, task in tasks:
            try:
                result = await task
                results[name] = result
                self._stats.hooks_executed += 1
            except asyncio.TimeoutError:
                self._handle_hook_error(name, f"Hook timeout after {timeout}s")
                results[name] = None
            except Exception as e:
                self._handle_hook_error(name, str(e))
                results[name] = None

        return results

    async def execute_with_fallback(
        self,
        event_type: ExtensionEventType,
        data: Any,
        fallback: Any = None,
        timeout: Optional[float] = None
    ) -> Any:
        """
        Execute hooks with fallback behavior.

        If all hooks fail or return None, returns the fallback value.

        Args:
            event_type: Type of event
            data: Event data
            fallback: Fallback value if all hooks fail
            timeout: Timeout for hook execution

        Returns:
            Modified data or fallback
        """
        result = await self.execute_hooks(event_type, data, timeout)
        if result is None:
            return fallback
        return result

    def register_tool_provider(
        self,
        provider_name: str,
        handler: Callable
    ) -> None:
        """
        Register a tool provider extension.

        Args:
            provider_name: Name of the tool provider
            handler: Function that provides tools
        """
        # Tools are registered via ExtensionAPI
        pass

    def get_tools_from_extensions(self) -> Dict[str, Any]:
        """
        Collect all tools registered by extensions.

        Returns:
            Dict mapping tool names to tool definitions
        """
        tools: Dict[str, Any] = {}

        for name, state in self._extensions.items():
            if not state.active or not state.api:
                continue

            for tool_name, tool_def in state.api._tools.items():
                tools[tool_name] = {
                    **tool_def,
                    "provider": name
                }

        return tools

    def get_hooks_summary(self) -> Dict[str, List[str]]:
        """
        Get summary of registered hooks by event type.

        Returns:
            Dict mapping event types to list of extension names
        """
        summary: Dict[str, List[str]] = {}

        for event_type, registrations in self._hooks.items():
            extensions = []
            for reg in registrations:
                if reg.extension_name:
                    extensions.append(reg.extension_name)
                else:
                    extensions.append("anonymous")
            summary[event_type.value] = extensions

        return summary

    def get_extension_errors(self) -> Dict[str, List[str]]:
        """
        Get all errors from extensions.

        Returns:
            Dict mapping extension names to list of errors
        """
        errors: Dict[str, List[str]] = {}

        for name, state in self._extensions.items():
            if state.last_error:
                errors[name] = [state.last_error]

        return errors

    def reset_error_counts(self) -> None:
        """Reset error counts for all extensions"""
        for state in self._extensions.values():
            state.error_count = 0
            state.last_error = None

    def enable_extension(self, name: str) -> bool:
        """
        Enable a disabled extension.

        Args:
            name: Extension name

        Returns:
            True if enabled successfully
        """
        state = self._extensions.get(name)
        if not state:
            return False

        if state.active:
            return True

        return self.activate_extension(name)

    def disable_extension(self, name: str) -> bool:
        """
        Disable an active extension.

        Args:
            name: Extension name

        Returns:
            True if disabled successfully
        """
        return self.deactivate_extension(name)

    def get_runner_status(self) -> Dict[str, Any]:
        """
        Get comprehensive runner status.

        Returns:
            Dict with runner status information
        """
        return {
            "running": self._running,
            "extensions": {
                "total": len(self._extensions),
                "active": sum(1 for s in self._extensions.values() if s.active),
                "with_errors": sum(1 for s in self._extensions.values() if s.error_count > 0),
            },
            "hooks": {
                "total": self._stats.hooks_registered,
                "by_type": self.get_hooks_summary(),
            },
            "subscriptions": len(self._subscriptions),
            "stats": {
                "extensions_loaded": self._stats.extensions_loaded,
                "extensions_active": self._stats.extensions_active,
                "hooks_registered": self._stats.hooks_registered,
                "hooks_executed": self._stats.hooks_executed,
                "events_emitted": self._stats.events_emitted,
                "errors_caught": self._stats.errors_caught,
            },
        }

    # Additional lifecycle hooks

    async def on_session_start(self, session_id: str) -> None:
        """Execute hooks for session start"""
        await self.execute_hooks(
            ExtensionEventType.SESSION_START,
            {"session_id": session_id}
        )

    async def on_session_end(self, session_id: str) -> None:
        """Execute hooks for session end"""
        await self.execute_hooks(
            ExtensionEventType.SESSION_END,
            {"session_id": session_id}
        )

    async def on_llm_start(self, messages: List[Any]) -> Optional[List[Any]]:
        """Execute hooks before LLM call"""
        return await self.execute_hooks(
            ExtensionEventType.LLM_START,
            messages
        )

    async def on_llm_complete(self, response: Any) -> Any:
        """Execute hooks after LLM response"""
        return await self.execute_hooks(
            ExtensionEventType.LLM_COMPLETE,
            response
        )

    async def on_context_compact(
        self,
        original_tokens: int,
        new_tokens: int
    ) -> None:
        """Execute hooks for context compaction"""
        await self.execute_hooks(
            ExtensionEventType.CONTEXT_COMPACT_END,
            {
                "original_tokens": original_tokens,
                "new_tokens": new_tokens,
                "saved_tokens": original_tokens - new_tokens,
            }
        )

    async def on_error(
        self,
        error: Exception,
        context: Dict[str, Any]
    ) -> None:
        """Execute hooks for errors"""
        await self.execute_hooks(
            ExtensionEventType.EXTENSION_ERROR,
            {
                "error": str(error),
                "error_type": type(error).__name__,
                "context": context,
            }
        )


# Global runner instance
_runner: Optional[ExtensionRunner] = None


def get_extension_runner() -> ExtensionRunner:
    """Get global extension runner"""
    global _runner
    if _runner is None:
        _runner = ExtensionRunner()
    return _runner


def reset_extension_runner() -> None:
    """Reset global runner (for testing)"""
    global _runner
    if _runner:
        _runner.deactivate_all()
    _runner = None
