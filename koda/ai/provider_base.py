"""
Koda AI Provider Base - Provider Base Class
Defines standardized Provider interface
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List, Callable, TYPE_CHECKING, Union
from dataclasses import dataclass, field
import time

from koda.ai.types import (
    ModelInfo,
    Context,
    Usage,
    AssistantMessage,
    StreamOptions,
    SimpleStreamOptions,
    ThinkingLevel,
    StopReason,
    TextContent,
    ToolCall,
)

if TYPE_CHECKING:
    from koda.ai.event_stream import AssistantMessageEventStream
    from koda.ai.http_proxy import ProxyConfig

from koda.ai.event_stream import EventType, AssistantMessageEvent


@dataclass
class ProviderConfig:
    """Provider Configuration"""
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    timeout: float = 60.0
    max_retries: int = 3
    headers: Optional[Dict[str, str]] = None

    # Proxy configuration
    proxy: Optional[Union[str, "ProxyConfig"]] = None
    """Proxy URL or ProxyConfig for HTTP requests"""

    proxy_enabled: bool = True
    """Whether to use proxy for requests (default: True if proxy is configured)"""


class BaseProvider(ABC):
    """
    Standardized Provider Base Class

    All LLM Providers must inherit from this class
    Equivalent to Pi Mono's Provider interface
    """

    def __init__(self, config: Optional[ProviderConfig] = None):
        self.config = config or ProviderConfig()
        self._rate_limit_remaining: Optional[int] = None
        self._rate_limit_reset: Optional[int] = None
        self._proxy_config: Optional["ProxyConfig"] = None
        self._session_manager = None
    
    @property
    @abstractmethod
    def api_type(self) -> str:
        """
        Return API type
        
        e.g.: 'openai-completions', 'anthropic-messages', 'google-generative-ai'
        """
        pass
    
    @property
    @abstractmethod
    def provider_id(self) -> str:
        """
        Return Provider ID
        
        e.g.: 'openai', 'anthropic', 'google'
        """
        pass
    
    @abstractmethod
    async def stream(
        self,
        model: ModelInfo,
        context: Context,
        options: Optional[StreamOptions] = None
    ) -> "AssistantMessageEventStream":
        """
        Stream generation response
        
        Must return AssistantMessageEventStream
        All events must be sent via push()
        
        Args:
            model: Model information
            context: Conversation context
            options: Stream options
        
        Returns:
            AssistantMessageEventStream event stream
        """
        pass
    
    async def complete(
        self,
        model: ModelInfo,
        context: Context,
        options: Optional[StreamOptions] = None
    ) -> AssistantMessage:
        """
        Non-streaming completion
        
        Default implementation collects all events via stream()
        Provider can override for performance optimization
        """
        from koda.ai.event_stream import AssistantMessageEventStream
        stream = await self.stream(model, context, options)
        return await stream.collect()
    
    @abstractmethod
    def calculate_cost(self, model: ModelInfo, usage: Usage) -> float:
        """
        Calculate request cost
        
        Args:
            model: Model information (contains cost configuration)
            usage: Token usage statistics
        
        Returns:
            Total cost (USD)
        """
        pass
    
    def supports_thinking_level(self, level: ThinkingLevel) -> bool:
        """
        Check if specific thinking level is supported
        
        Args:
            level: Thinking level
        
        Returns:
            Whether supported
        """
        return False
    
    def supports_cache_retention(self) -> bool:
        """Whether cache retention is supported"""
        return False
    
    def supports_vision(self) -> bool:
        """Whether vision is supported"""
        return True
    
    def supports_tools(self) -> bool:
        """Whether tool calling is supported"""
        return True
    
    def get_default_headers(self) -> Dict[str, str]:
        """Get default request headers"""
        headers = {
            "Content-Type": "application/json",
        }
        if self.config.headers:
            headers.update(self.config.headers)
        return headers
    
    def get_auth_header(self) -> Optional[Dict[str, str]]:
        """Get authentication header"""
        if self.config.api_key:
            return {"Authorization": f"Bearer {self.config.api_key}"}
        return None

    def get_proxy_config(self) -> Optional["ProxyConfig"]:
        """
        Get proxy configuration for this provider

        Returns:
            ProxyConfig if proxy is configured, None otherwise
        """
        if self._proxy_config:
            return self._proxy_config

        # Import here to avoid circular imports
        from koda.ai.http_proxy import ProxyConfig, load_proxy_from_env

        # Check if proxy is configured in provider config
        if self.config.proxy:
            if isinstance(self.config.proxy, ProxyConfig):
                self._proxy_config = self.config.proxy
            elif isinstance(self.config.proxy, str):
                self._proxy_config = ProxyConfig.from_url(self.config.proxy)
            return self._proxy_config

        # Fall back to environment variables if proxy is enabled
        if self.config.proxy_enabled:
            self._proxy_config = load_proxy_from_env()

        return self._proxy_config

    def should_use_proxy(self, url: str) -> bool:
        """
        Check if proxy should be used for a given URL

        Args:
            url: Target URL

        Returns:
            True if proxy should be used, False otherwise
        """
        if not self.config.proxy_enabled:
            return False

        proxy_config = self.get_proxy_config()
        if not proxy_config:
            return False

        return proxy_config.should_use_proxy(url)

    async def get_proxy_session_manager(self):
        """
        Get or create a ProxySessionManager for HTTP requests

        Returns:
            ProxySessionManager instance
        """
        if self._session_manager is None:
            from koda.ai.http_proxy import ProxySessionManager
            self._session_manager = ProxySessionManager(
                proxy_config=self.get_proxy_config(),
                trust_env=self.config.proxy_enabled
            )
        return self._session_manager

    async def close_proxy_session(self):
        """Close the proxy session if it exists"""
        if self._session_manager:
            await self._session_manager.close()
            self._session_manager = None

    def _apply_rate_limits(self, headers: Dict[str, str]) -> None:
        """
        Extract rate limit information from response headers
        
        Standard headers:
        - x-ratelimit-remaining
        - x-ratelimit-reset
        """
        self._rate_limit_remaining = int(headers.get("x-ratelimit-remaining", -1))
        reset_timestamp = headers.get("x-ratelimit-reset")
        if reset_timestamp:
            self._rate_limit_reset = int(reset_timestamp)
    
    def should_retry(self, error: Exception, attempt: int) -> bool:
        """
        Determine if should retry
        
        Args:
            error: Exception
            attempt: Current attempt count
        
        Returns:
            Whether to retry
        """
        if attempt >= self.config.max_retries:
            return False
        
        # Retryable error types
        retryable_errors = [
            "rate limit",
            "timeout",
            "connection",
            "503",
            "429",
            "500",
        ]
        
        error_str = str(error).lower()
        return any(err in error_str for err in retryable_errors)
    
    def get_retry_delay(self, attempt: int) -> float:
        """
        Get retry delay (exponential backoff)
        
        Args:
            attempt: Attempt count (starting from 0)
        
        Returns:
            Delay in seconds
        """
        import random
        base_delay = 2 ** attempt  # Exponential backoff: 1, 2, 4, 8...
        jitter = random.uniform(0, 1)  # Random jitter
        return min(base_delay + jitter, 60.0)  # Max 60 seconds
    
    def _create_initial_message(
        self,
        model: ModelInfo
    ) -> AssistantMessage:
        """Create initial assistant message structure"""
        return AssistantMessage(
            role="assistant",
            content=[],
            api=self.api_type,
            provider=self.provider_id,
            model=model.id,
            usage=Usage(),
            stop_reason=StopReason.STOP,
            timestamp=int(time.time() * 1000)
        )
    
    def _emit_start(
        self,
        stream: "AssistantMessageEventStream",
        message: AssistantMessage
    ) -> None:
        """Emit start event"""
        stream.push(AssistantMessageEvent(
            type=EventType.START.value,
            partial=message
        ))
    
    def _emit_text_start(
        self,
        stream: "AssistantMessageEventStream",
        message: AssistantMessage,
        index: int
    ) -> None:
        """Emit text start event"""
        stream.push(AssistantMessageEvent(
            type=EventType.TEXT_START.value,
            partial=message,
            content_index=index
        ))
    
    def _emit_text_delta(
        self,
        stream: "AssistantMessageEventStream",
        message: AssistantMessage,
        index: int,
        delta: str
    ) -> None:
        """Emit text delta event"""
        # Update message content
        if index < len(message.content):
            content = message.content[index]
            if content.type == "text":
                content.text += delta
        
        stream.push(AssistantMessageEvent(
            type=EventType.TEXT_DELTA.value,
            partial=message,
            content_index=index,
            delta=delta
        ))
    
    def _emit_text_end(
        self,
        stream: "AssistantMessageEventStream",
        message: AssistantMessage,
        index: int,
        text: str
    ) -> None:
        """Emit text end event"""
        stream.push(AssistantMessageEvent(
            type=EventType.TEXT_END.value,
            partial=message,
            content_index=index,
            delta=text
        ))
    
    def _emit_thinking_start(
        self,
        stream: "AssistantMessageEventStream",
        message: AssistantMessage,
        index: int
    ) -> None:
        """Emit thinking start event"""
        stream.push(AssistantMessageEvent(
            type=EventType.THINKING_START.value,
            partial=message,
            content_index=index
        ))
    
    def _emit_thinking_delta(
        self,
        stream: "AssistantMessageEventStream",
        message: AssistantMessage,
        index: int,
        delta: str
    ) -> None:
        """Emit thinking delta event"""
        if index < len(message.content):
            content = message.content[index]
            if content.type == "thinking":
                content.thinking += delta
        
        stream.push(AssistantMessageEvent(
            type=EventType.THINKING_DELTA.value,
            partial=message,
            content_index=index,
            delta=delta
        ))
    
    def _emit_thinking_end(
        self,
        stream: "AssistantMessageEventStream",
        message: AssistantMessage,
        index: int
    ) -> None:
        """Emit thinking end event"""
        stream.push(AssistantMessageEvent(
            type=EventType.THINKING_END.value,
            partial=message,
            content_index=index
        ))
    
    def _emit_toolcall_start(
        self,
        stream: "AssistantMessageEventStream",
        message: AssistantMessage,
        index: int,
        tool_call: ToolCall
    ) -> None:
        """Emit tool call start event"""
        # Add to message content
        message.content.append(tool_call)
        
        stream.push(AssistantMessageEvent(
            type=EventType.TOOLCALL_START.value,
            partial=message,
            content_index=index
        ))
    
    def _emit_toolcall_delta(
        self,
        stream: "AssistantMessageEventStream",
        message: AssistantMessage,
        index: int,
        delta: str
    ) -> None:
        """Emit tool call delta event"""
        stream.push(AssistantMessageEvent(
            type=EventType.TOOLCALL_DELTA.value,
            partial=message,
            content_index=index,
            delta=delta
        ))
    
    def _emit_toolcall_end(
        self,
        stream: "AssistantMessageEventStream",
        message: AssistantMessage,
        index: int,
        tool_call: ToolCall
    ) -> None:
        """Emit tool call end event"""
        # Update tool call in message
        if index < len(message.content):
            message.content[index] = tool_call
        
        stream.push(AssistantMessageEvent(
            type=EventType.TOOLCALL_END.value,
            partial=message,
            content_index=index,
            tool_call=tool_call
        ))
    
    def _emit_done(
        self,
        stream: "AssistantMessageEventStream",
        message: AssistantMessage,
        reason: StopReason
    ) -> None:
        """Emit done event"""
        message.stop_reason = reason
        stream.push(AssistantMessageEvent(
            type=EventType.DONE.value,
            partial=message,
            reason=reason
        ))
        stream.close()
    
    def _emit_error(
        self,
        stream: "AssistantMessageEventStream",
        message: AssistantMessage,
        error: Exception
    ) -> None:
        """Emit error event"""
        message.stop_reason = StopReason.ERROR
        message.error_message = str(error)
        stream.push(AssistantMessageEvent(
            type=EventType.ERROR.value,
            partial=message,
            error=error,
            reason=StopReason.ERROR
        ))
        stream.close()


class ProviderRegistry:
    """
    Provider Registry
    
    Manages all available Providers
    """
    
    def __init__(self):
        self._providers: Dict[str, type[BaseProvider]] = {}
        self._instances: Dict[str, BaseProvider] = {}
    
    def register(
        self,
        provider_id: str,
        provider_class: type[BaseProvider]
    ) -> None:
        """Register Provider class"""
        self._providers[provider_id] = provider_class
    
    def create(
        self,
        provider_id: str,
        config: Optional[ProviderConfig] = None
    ) -> BaseProvider:
        """Create Provider instance"""
        if provider_id not in self._providers:
            raise ValueError(f"Unknown provider: {provider_id}")
        
        provider_class = self._providers[provider_id]
        return provider_class(config)
    
    def get_or_create(
        self,
        provider_id: str,
        config: Optional[ProviderConfig] = None
    ) -> BaseProvider:
        """Get or create Provider instance (singleton)"""
        cache_key = f"{provider_id}:{hash(str(config))}"
        
        if cache_key not in self._instances:
            self._instances[cache_key] = self.create(provider_id, config)
        
        return self._instances[cache_key]
    
    def list_providers(self) -> List[str]:
        """List all registered Providers"""
        return list(self._providers.keys())


# Global Provider Registry
_global_provider_registry: Optional[ProviderRegistry] = None


def get_provider_registry() -> ProviderRegistry:
    """Get global Provider Registry"""
    global _global_provider_registry
    if _global_provider_registry is None:
        _global_provider_registry = ProviderRegistry()
    return _global_provider_registry
