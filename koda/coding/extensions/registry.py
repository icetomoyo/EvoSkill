"""
Extension Registry
Manages loaded extensions.
"""
from typing import List, Type, Optional
from .extension import Extension, ExtensionAPI


class ExtensionRegistry:
    """Registry for extensions"""
    
    def __init__(self):
        self._extensions: List[Extension] = []
        self._extension_classes: List[Type[Extension]] = []
        self._active = False
    
    def register(self, extension_class: Type[Extension]):
        """
        Register an extension class.
        
        Args:
            extension_class: Extension class to register
        """
        self._extension_classes.append(extension_class)
    
    def load(self, extension_class: Type[Extension]):
        """
        Load and activate an extension.
        
        Args:
            extension_class: Extension class to load
        """
        instance = extension_class()
        api = ExtensionAPI(self)
        instance.activate(api)
        self._extensions.append(instance)
    
    def load_all(self):
        """Load all registered extensions"""
        for ext_class in self._extension_classes:
            self.load(ext_class)
        self._active = True
    
    def unload_all(self):
        """Unload all extensions"""
        for ext in self._extensions:
            ext.deactivate()
        self._extensions.clear()
        self._active = False
    
    def get_extensions(self) -> List[Extension]:
        """Get loaded extensions"""
        return self._extensions.copy()
    
    def find_extension(self, name: str) -> Optional[Extension]:
        """Find extension by name"""
        for ext in self._extensions:
            if ext.metadata.name == name:
                return ext
        return None


# Global registry
_registry: Optional[ExtensionRegistry] = None


def get_extension_registry() -> ExtensionRegistry:
    """Get global extension registry"""
    global _registry
    if _registry is None:
        _registry = ExtensionRegistry()
    return _registry
