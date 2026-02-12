"""
Extension Wrapper - Wraps extension instances with unified interface
Equivalent to Pi Mono's extension-wrapper.ts

Provides:
- Unified extension interface
- Exception handling and isolation
- Method invocation with safety wrappers
- Extension state tracking
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Type
import traceback
import functools

from koda.coding.extensions.types import (
    Extension,
    ExtensionAPI,
    ExtensionConfig,
    ExtensionEvent,
    ExtensionEventType,
    ExtensionManifest,
)


@dataclass
class ExtensionInvocation:
    """Record of an extension method invocation"""
    method: str
    args: tuple
    kwargs: Dict[str, Any]
    result: Any = None
    error: Optional[str] = None
    duration_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ExtensionMetrics:
    """Metrics for an extension"""
    invocations: int = 0
    errors: int = 0
    total_duration_ms: float = 0.0
    last_invocation: Optional[datetime] = None
    last_error: Optional[str] = None
    last_error_time: Optional[datetime] = None

    @property
    def avg_duration_ms(self) -> float:
        if self.invocations == 0:
            return 0.0
        return self.total_duration_ms / self.invocations

    @property
    def error_rate(self) -> float:
        if self.invocations == 0:
            return 0.0
        return self.errors / self.invocations


class ExtensionWrapper:
    """
    Wrapper for extension instances providing:
    - Unified interface
    - Exception isolation
    - Method invocation tracking
    - Metrics collection
    """

    def __init__(
        self,
        extension: Extension,
        api: Optional[ExtensionAPI] = None,
        config: Optional[ExtensionConfig] = None,
        safe_mode: bool = True
    ):
        """
        Initialize extension wrapper.

        Args:
            extension: Extension instance to wrap
            api: Extension API instance
            config: Extension configuration
            safe_mode: If True, catch and log all exceptions
        """
        self._extension = extension
        self._api = api
        self._config = config or ExtensionConfig()
        self._safe_mode = safe_mode
        self._active = False
        self._metrics = ExtensionMetrics()
        self._invocation_history: List[ExtensionInvocation] = []
        self._max_history = 100

    @property
    def extension(self) -> Extension:
        """Get wrapped extension"""
        return self._extension

    @property
    def manifest(self) -> ExtensionManifest:
        """Get extension manifest"""
        return self._extension.manifest

    @property
    def name(self) -> str:
        """Get extension name"""
        return self._extension.manifest.name

    @property
    def active(self) -> bool:
        """Check if extension is active"""
        return self._active

    @property
    def metrics(self) -> ExtensionMetrics:
        """Get extension metrics"""
        return self._metrics

    @property
    def api(self) -> Optional[ExtensionAPI]:
        """Get extension API"""
        return self._api

    @api.setter
    def api(self, value: ExtensionAPI) -> None:
        """Set extension API"""
        self._api = value

    def activate(self) -> bool:
        """
        Activate the extension.

        Returns:
            True if activated successfully
        """
        if self._active:
            return True

        try:
            if self._api:
                self._extension.activate(self._api)
            self._active = True
            return True
        except Exception as e:
            self._record_error("activate", str(e))
            return False

    def deactivate(self) -> bool:
        """
        Deactivate the extension.

        Returns:
            True if deactivated successfully
        """
        if not self._active:
            return True

        try:
            self._extension.deactivate()
            self._active = False
            return True
        except Exception as e:
            self._record_error("deactivate", str(e))
            self._active = False  # Force deactivate on error
            return False

    def configure(self, config: ExtensionConfig) -> None:
        """
        Configure the extension.

        Args:
            config: Configuration to apply
        """
        self._config = config
        self._safe_invoke("configure", config)

    def invoke(
        self,
        method_name: str,
        *args,
        **kwargs
    ) -> Any:
        """
        Safely invoke an extension method.

        Args:
            method_name: Name of method to invoke
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Method result or None if error in safe mode

        Raises:
            AttributeError: If method doesn't exist (in non-safe mode)
            Exception: Original exception (in non-safe mode)
        """
        return self._safe_invoke(method_name, *args, **kwargs)

    def _safe_invoke(
        self,
        method_name: str,
        *args,
        **kwargs
    ) -> Any:
        """Internal safe invocation handler"""
        method = getattr(self._extension, method_name, None)

        if method is None:
            if self._safe_mode:
                self._record_error(method_name, f"Method not found: {method_name}")
                return None
            raise AttributeError(f"Extension has no method '{method_name}'")

        invocation = ExtensionInvocation(
            method=method_name,
            args=args,
            kwargs=kwargs,
        )

        start_time = datetime.now()

        try:
            result = method(*args, **kwargs)
            invocation.result = result
            return result

        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}"
            invocation.error = error_msg
            self._record_error(method_name, error_msg, traceback.format_exc())

            if not self._safe_mode:
                raise

            return None

        finally:
            end_time = datetime.now()
            invocation.duration_ms = (end_time - start_time).total_seconds() * 1000

            # Update metrics
            self._metrics.invocations += 1
            self._metrics.total_duration_ms += invocation.duration_ms
            self._metrics.last_invocation = end_time

            # Store invocation
            self._invocation_history.append(invocation)
            if len(self._invocation_history) > self._max_history:
                self._invocation_history.pop(0)

    def _record_error(
        self,
        method: str,
        error: str,
        trace: Optional[str] = None
    ) -> None:
        """Record an error occurrence"""
        self._metrics.errors += 1
        self._metrics.last_error = error
        self._metrics.last_error_time = datetime.now()

        # Log error
        print(f"[Extension:{self.name}] Error in {method}: {error}")
        if trace:
            print(f"[Extension:{self.name}] Traceback:\n{trace}")

    # Proxy common extension methods

    def on_user_message(self, content: str) -> Optional[str]:
        """Proxy for on_user_message hook"""
        return self.invoke("on_user_message", content)

    def on_assistant_message(self, content: str) -> Optional[str]:
        """Proxy for on_assistant_message hook"""
        return self.invoke("on_assistant_message", content)

    def on_tool_call(
        self,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Proxy for on_tool_call hook"""
        return self.invoke("on_tool_call", tool_name, arguments)

    def on_tool_result(
        self,
        tool_name: str,
        result: Any
    ) -> Any:
        """Proxy for on_tool_result hook"""
        return self.invoke("on_tool_result", tool_name, result)

    def on_llm_start(self, messages: List[Any]) -> Optional[List[Any]]:
        """Proxy for on_llm_start hook"""
        return self.invoke("on_llm_start", messages)

    def on_llm_complete(self, response: Any) -> Any:
        """Proxy for on_llm_complete hook"""
        return self.invoke("on_llm_complete", response)

    def on_context_compact(
        self,
        original_tokens: int,
        new_tokens: int
    ) -> None:
        """Proxy for on_context_compact hook"""
        self.invoke("on_context_compact", original_tokens, new_tokens)

    def on_session_start(self) -> None:
        """Proxy for on_session_start hook"""
        self.invoke("on_session_start")

    def on_session_end(self) -> None:
        """Proxy for on_session_end hook"""
        self.invoke("on_session_end")

    def on_error(
        self,
        error: Exception,
        context: Dict[str, Any]
    ) -> None:
        """Proxy for on_error hook"""
        self.invoke("on_error", error, context)

    def get_invocation_history(
        self,
        method: Optional[str] = None,
        limit: int = 50
    ) -> List[ExtensionInvocation]:
        """
        Get invocation history.

        Args:
            method: Filter by method name (optional)
            limit: Maximum number of records to return

        Returns:
            List of invocation records
        """
        history = self._invocation_history

        if method:
            history = [h for h in history if h.method == method]

        return history[-limit:]

    def get_recent_errors(self, limit: int = 10) -> List[ExtensionInvocation]:
        """
        Get recent error invocations.

        Args:
            limit: Maximum number of errors to return

        Returns:
            List of error invocations
        """
        errors = [h for h in self._invocation_history if h.error]
        return errors[-limit:]

    def clear_history(self) -> None:
        """Clear invocation history"""
        self._invocation_history.clear()

    def reset_metrics(self) -> None:
        """Reset metrics counters"""
        self._metrics = ExtensionMetrics()

    def to_dict(self) -> Dict[str, Any]:
        """Convert wrapper state to dictionary"""
        return {
            "name": self.name,
            "active": self._active,
            "safe_mode": self._safe_mode,
            "manifest": {
                "name": self.manifest.name,
                "version": self.manifest.version,
                "description": self.manifest.description,
                "author": self.manifest.author,
            },
            "metrics": {
                "invocations": self._metrics.invocations,
                "errors": self._metrics.errors,
                "error_rate": self._metrics.error_rate,
                "avg_duration_ms": self._metrics.avg_duration_ms,
                "total_duration_ms": self._metrics.total_duration_ms,
            },
            "config": {
                "enabled": self._config.enabled,
                "priority": self._config.priority,
            },
        }


class WrappedExtensionRegistry:
    """
    Registry for managing wrapped extensions.

    Provides a unified interface for working with multiple extensions.
    """

    def __init__(self, safe_mode: bool = True):
        """
        Initialize registry.

        Args:
            safe_mode: Default safe mode for wrappers
        """
        self._wrappers: Dict[str, ExtensionWrapper] = {}
        self._safe_mode = safe_mode

    def register(
        self,
        extension: Extension,
        api: Optional[ExtensionAPI] = None,
        config: Optional[ExtensionConfig] = None
    ) -> ExtensionWrapper:
        """
        Register and wrap an extension.

        Args:
            extension: Extension to register
            api: Extension API
            config: Extension configuration

        Returns:
            Created wrapper
        """
        wrapper = ExtensionWrapper(
            extension,
            api=api,
            config=config,
            safe_mode=self._safe_mode
        )
        self._wrappers[wrapper.name] = wrapper
        return wrapper

    def unregister(self, name: str) -> bool:
        """
        Unregister an extension.

        Args:
            name: Extension name

        Returns:
            True if unregistered
        """
        if name in self._wrappers:
            wrapper = self._wrappers.pop(name)
            wrapper.deactivate()
            return True
        return False

    def get(self, name: str) -> Optional[ExtensionWrapper]:
        """Get wrapper by name"""
        return self._wrappers.get(name)

    def get_all(self) -> Dict[str, ExtensionWrapper]:
        """Get all wrappers"""
        return self._wrappers.copy()

    def get_active(self) -> List[ExtensionWrapper]:
        """Get all active wrappers"""
        return [w for w in self._wrappers.values() if w.active]

    def activate_all(self) -> Dict[str, bool]:
        """
        Activate all extensions.

        Returns:
            Dict mapping extension names to activation success
        """
        results = {}
        for name, wrapper in self._wrappers.items():
            results[name] = wrapper.activate()
        return results

    def deactivate_all(self) -> Dict[str, bool]:
        """
        Deactivate all extensions.

        Returns:
            Dict mapping extension names to deactivation success
        """
        results = {}
        for name, wrapper in self._wrappers.items():
            results[name] = wrapper.deactivate()
        return results

    def invoke_all(
        self,
        method_name: str,
        *args,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Invoke a method on all active extensions.

        Args:
            method_name: Method to invoke
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Dict mapping extension names to results
        """
        results = {}
        for name, wrapper in self._wrappers.items():
            if wrapper.active:
                results[name] = wrapper.invoke(method_name, *args, **kwargs)
        return results

    def collect_errors(self) -> Dict[str, List[ExtensionInvocation]]:
        """
        Collect recent errors from all extensions.

        Returns:
            Dict mapping extension names to error lists
        """
        errors = {}
        for name, wrapper in self._wrappers.items():
            ext_errors = wrapper.get_recent_errors()
            if ext_errors:
                errors[name] = ext_errors
        return errors

    def get_metrics(self) -> Dict[str, Dict[str, Any]]:
        """
        Get metrics for all extensions.

        Returns:
            Dict mapping extension names to metrics
        """
        return {name: wrapper.to_dict()["metrics"] for name, wrapper in self._wrappers.items()}

    def clear_all_history(self) -> None:
        """Clear history for all extensions"""
        for wrapper in self._wrappers.values():
            wrapper.clear_history()

    def to_dict(self) -> Dict[str, Any]:
        """Convert registry state to dictionary"""
        return {
            "extensions": {name: wrapper.to_dict() for name, wrapper in self._wrappers.items()},
            "total_extensions": len(self._wrappers),
            "active_extensions": len(self.get_active()),
        }


__all__ = [
    "ExtensionWrapper",
    "WrappedExtensionRegistry",
    "ExtensionInvocation",
    "ExtensionMetrics",
]
