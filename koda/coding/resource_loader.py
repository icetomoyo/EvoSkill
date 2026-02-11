"""
Resource Loader
Equivalent to Pi Mono's packages/coding-agent/src/core/resource-loader.ts

Loads external resources referenced via @url or @file syntax.
"""
import re
import os
from pathlib import Path
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass
from urllib.parse import urlparse


@dataclass
class Resource:
    """Loaded resource"""
    content: str
    source: str  # Original @ reference
    path: Optional[str] = None  # Resolved path/URL
    mime_type: Optional[str] = None


@dataclass
class LoadOptions:
    """Resource loading options"""
    max_size: int = 10 * 1024 * 1024  # 10MB default
    allowed_schemes: list = None
    base_path: Optional[str] = None

    def __post_init__(self):
        if self.allowed_schemes is None:
            self.allowed_schemes = ["http", "https", "file"]


class ResourceLoader:
    """
    Loads resources referenced in prompts.
    
    Supports:
    - @https://example.com/file.md - Load from URL
    - @file://./local/path.txt - Load from file
    - @./relative/path.py - Relative file path
    
    Example:
        >>> loader = ResourceLoader()
        >>> resource = loader.load("@https://example.com/doc.md")
        >>> print(resource.content)
    """
    
    # Pattern to match @url or @file references
    RESOURCE_PATTERN = re.compile(
        r'@((?:https?://|file://)?[^\s\n]+)',
        re.MULTILINE
    )
    
    def __init__(self, options: Optional[LoadOptions] = None):
        self.options = options or LoadOptions()
        self._handlers: Dict[str, Callable[[str], Resource]] = {
            "http": self._load_http,
            "https": self._load_http,
            "file": self._load_file,
        }
    
    def find_references(self, text: str) -> list:
        """
        Find all resource references in text.
        
        Args:
            text: Text to search
            
        Returns:
            List of @ references (without the @)
        """
        return self.RESOURCE_PATTERN.findall(text)
    
    def load(self, reference: str) -> Resource:
        """
        Load a single resource.
        
        Args:
            reference: Resource reference (with or without @)
            
        Returns:
            Loaded resource
            
        Raises:
            ValueError: If reference is invalid or cannot be loaded
        """
        # Remove @ prefix if present
        ref = reference[1:] if reference.startswith('@') else reference
        
        # Parse URL
        parsed = urlparse(ref)
        scheme = parsed.scheme or "file"
        
        if scheme not in self.options.allowed_schemes:
            raise ValueError(f"Scheme not allowed: {scheme}")
        
        # Get handler
        handler = self._handlers.get(scheme)
        if not handler:
            raise ValueError(f"No handler for scheme: {scheme}")
        
        return handler(ref)
    
    def load_all(self, text: str) -> Dict[str, Resource]:
        """
        Load all resources referenced in text.
        
        Args:
            text: Text containing @ references
            
        Returns:
            Dict mapping references to loaded resources
        """
        references = self.find_references(text)
        results = {}
        
        for ref in references:
            try:
                results[ref] = self.load(ref)
            except Exception as e:
                # Store error as resource with error message
                results[ref] = Resource(
                    content=f"# Error loading resource\n\n{str(e)}",
                    source=f"@{ref}",
                    path=None
                )
        
        return results
    
    def replace_in_text(self, text: str) -> str:
        """
        Replace all @references in text with loaded content.
        
        Args:
            text: Text containing @ references
            
        Returns:
            Text with references replaced by content
        """
        resources = self.load_all(text)
        
        def replace_match(match):
            ref = match.group(1)
            resource = resources.get(ref)
            if resource:
                return f"\n```\n{resource.content}\n```\n"
            return match.group(0)
        
        return self.RESOURCE_PATTERN.sub(replace_match, text)
    
    def _load_http(self, url: str) -> Resource:
        """Load from HTTP/HTTPS URL"""
        try:
            import urllib.request
            
            req = urllib.request.Request(
                url,
                headers={
                    'User-Agent': 'Mozilla/5.0 (compatible; Koda/1.0)'
                }
            )
            
            with urllib.request.urlopen(req, timeout=30) as response:
                content = response.read(self.options.max_size)
                
                # Check if content was truncated
                if len(response.read(1)) > 0:
                    raise ValueError(f"Resource exceeds max size: {self.options.max_size}")
                
                content_type = response.headers.get('Content-Type', '')
                
                # Try to decode as text
                try:
                    text_content = content.decode('utf-8')
                except UnicodeDecodeError:
                    # Binary content
                    text_content = f"[Binary content: {len(content)} bytes]"
                
                return Resource(
                    content=text_content,
                    source=f"@{url}",
                    path=url,
                    mime_type=content_type.split(';')[0] if content_type else None
                )
                
        except Exception as e:
            raise ValueError(f"Failed to load URL: {url} - {str(e)}")
    
    def _load_file(self, path: str) -> Resource:
        """Load from file path"""
        # Remove file:// prefix if present
        if path.startswith('file://'):
            path = path[7:]
        
        # Handle relative paths
        if not os.path.isabs(path) and self.options.base_path:
            path = os.path.join(self.options.base_path, path)
        
        file_path = Path(path)
        
        if not file_path.exists():
            raise ValueError(f"File not found: {path}")
        
        if file_path.stat().st_size > self.options.max_size:
            raise ValueError(f"File exceeds max size: {self.options.max_size}")
        
        try:
            content = file_path.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            # Try binary and show size
            content = f"[Binary file: {file_path.stat().st_size} bytes]"
        
        return Resource(
            content=content,
            source=f"@{path}",
            path=str(file_path.absolute()),
            mime_type=self._guess_mime_type(file_path.suffix)
        )
    
    def _guess_mime_type(self, extension: str) -> Optional[str]:
        """Guess MIME type from file extension"""
        mime_types = {
            '.md': 'text/markdown',
            '.txt': 'text/plain',
            '.py': 'text/x-python',
            '.js': 'application/javascript',
            '.ts': 'application/typescript',
            '.json': 'application/json',
            '.yaml': 'application/yaml',
            '.yml': 'application/yaml',
            '.html': 'text/html',
            '.css': 'text/css',
            '.xml': 'application/xml',
        }
        return mime_types.get(extension.lower())
    
    def register_handler(self, scheme: str, handler: Callable[[str], Resource]):
        """
        Register a custom handler for a scheme.
        
        Args:
            scheme: URL scheme (e.g., 's3', 'ftp')
            handler: Function that takes URL and returns Resource
        """
        self._handlers[scheme] = handler


# Convenience functions
def load_resource(reference: str, base_path: Optional[str] = None) -> Resource:
    """
    Load a single resource.
    
    Args:
        reference: @ reference (e.g., "@https://example.com/doc.md")
        base_path: Base path for relative file references
        
    Returns:
        Loaded resource
    """
    loader = ResourceLoader(LoadOptions(base_path=base_path))
    return loader.load(reference)


def load_resources(text: str, base_path: Optional[str] = None) -> Dict[str, Resource]:
    """
    Load all resources referenced in text.
    
    Args:
        text: Text containing @ references
        base_path: Base path for relative file references
        
    Returns:
        Dict of reference -> resource
    """
    loader = ResourceLoader(LoadOptions(base_path=base_path))
    return loader.load_all(text)


__all__ = [
    "Resource",
    "ResourceLoader",
    "LoadOptions",
    "load_resource",
    "load_resources",
]
