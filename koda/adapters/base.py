"""
LLM Adapter Base Class
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class BaseLLMAdapter(ABC):
    """
    LLM Adapter Base Class
    
    Provides unified interface for different LLM providers.
    """
    
    def __init__(self, **config):
        self.config = config
    
    @abstractmethod
    async def complete(self, prompt: str, **kwargs) -> str:
        """Complete text generation"""
        pass
    
    @abstractmethod
    async def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """Chat mode"""
        pass
    
    def get_name(self) -> str:
        """Get adapter name"""
        return self.__class__.__name__
