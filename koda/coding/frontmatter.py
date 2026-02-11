"""
Frontmatter Parser
Equivalent to Pi Mono's packages/coding-agent/src/utils/frontmatter.ts

Parses YAML frontmatter from Markdown files.
"""
import re
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass


@dataclass
class Frontmatter:
    """Parsed frontmatter result"""
    attributes: Dict[str, Any]
    body: str
    frontmatter: str  # Raw frontmatter text


class FrontmatterParser:
    """
    Parser for YAML frontmatter in Markdown files.
    
    Frontmatter is YAML metadata at the start of a file
delimited by --- lines:
    
    ```markdown
    ---
title: My Document
author: John Doe
tags:
  - python
  - markdown
---

# Content starts here
    ```
    
    Example:
        >>> parser = FrontmatterParser()
        >>> result = parser.parse("---\\ntitle: Test\\n---\\n\\nContent")
        >>> result.attributes['title']
        'Test'
    """
    
    # Pattern to match frontmatter: ---\n...\n---
    FRONTMATTER_PATTERN = re.compile(
        r'^---\s*\n(.*?)\n---\s*\n(.*)$',
        re.DOTALL
    )
    
    def __init__(self):
        self._yaml_available = self._check_yaml()
    
    def _check_yaml(self) -> bool:
        """Check if PyYAML is available"""
        try:
            import yaml
            return True
        except ImportError:
            return False
    
    def parse(self, content: str) -> Frontmatter:
        """
        Parse frontmatter from content.
        
        Args:
            content: Markdown content with optional frontmatter
            
        Returns:
            Frontmatter with attributes and body
        """
        match = self.FRONTMATTER_PATTERN.match(content)
        
        if not match:
            # No frontmatter found
            return Frontmatter(
                attributes={},
                body=content,
                frontmatter=""
            )
        
        frontmatter_text = match.group(1)
        body = match.group(2)
        
        # Parse YAML
        attributes = self._parse_yaml(frontmatter_text)
        
        return Frontmatter(
            attributes=attributes,
            body=body,
            frontmatter=frontmatter_text
        )
    
    def _parse_yaml(self, yaml_text: str) -> Dict[str, Any]:
        """Parse YAML text to dict"""
        if self._yaml_available:
            try:
                import yaml
                return yaml.safe_load(yaml_text) or {}
            except Exception:
                return {}
        else:
            # Fallback: simple key-value parsing
            return self._simple_yaml_parse(yaml_text)
    
    def _simple_yaml_parse(self, yaml_text: str) -> Dict[str, Any]:
        """Simple YAML parser for basic key-value pairs"""
        result = {}
        current_key = None
        current_list = None
        
        for line in yaml_text.split('\n'):
            stripped = line.strip()
            
            # Skip empty lines and comments
            if not stripped or stripped.startswith('#'):
                continue
            
            # Check for list item
            if stripped.startswith('- '):
                if current_list is not None and current_key:
                    value = stripped[2:].strip()
                    # Try to parse as number/boolean
                    current_list.append(self._parse_value(value))
            else:
                # Close current list
                if current_list is not None and current_key:
                    result[current_key] = current_list
                    current_list = None
                
                # Parse key-value
                if ':' in stripped:
                    key, value = stripped.split(':', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    if not value:
                        # Start of list or nested
                        current_key = key
                        current_list = []
                    else:
                        # Simple key-value
                        result[key] = self._parse_value(value)
        
        # Close any open list
        if current_list is not None and current_key:
            result[current_key] = current_list
        
        return result
    
    def _parse_value(self, value: str) -> Any:
        """Parse a YAML value"""
        # Remove quotes
        if (value.startswith('"') and value.endswith('"')) or \
           (value.startswith("'") and value.endswith("'")):
            return value[1:-1]
        
        # Boolean
        lower = value.lower()
        if lower in ('true', 'yes', 'on'):
            return True
        if lower in ('false', 'no', 'off'):
            return False
        
        # Null
        if lower in ('null', '~', ''):
            return None
        
        # Number
        try:
            if '.' in value:
                return float(value)
            return int(value)
        except ValueError:
            pass
        
        # String
        return value
    
    def stringify(self, attributes: Dict[str, Any], body: str = "") -> str:
        """
        Convert attributes and body to frontmatter format.
        
        Args:
            attributes: Frontmatter attributes
            body: Content body
            
        Returns:
            Formatted markdown with frontmatter
        """
        if not attributes:
            return body
        
        if self._yaml_available:
            import yaml
            yaml_text = yaml.dump(
                attributes,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False
            )
        else:
            yaml_text = self._simple_yaml_stringify(attributes)
        
        return f"---\n{yaml_text}---\n\n{body}"
    
    def _simple_yaml_stringify(self, attributes: Dict[str, Any]) -> str:
        """Simple YAML stringify"""
        lines = []
        for key, value in attributes.items():
            if isinstance(value, list):
                lines.append(f"{key}:")
                for item in value:
                    lines.append(f"  - {self._stringify_value(item)}")
            elif isinstance(value, dict):
                lines.append(f"{key}:")
                for k, v in value.items():
                    lines.append(f"  {k}: {self._stringify_value(v)}")
            else:
                lines.append(f"{key}: {self._stringify_value(value)}")
        return '\n'.join(lines) + '\n'
    
    def _stringify_value(self, value: Any) -> str:
        """Stringify a value for YAML"""
        if isinstance(value, bool):
            return 'true' if value else 'false'
        if isinstance(value, (int, float)):
            return str(value)
        if value is None:
            return 'null'
        if isinstance(value, str):
            # Quote if contains special chars
            if any(c in value for c in [':', '#', '{', '}', '[', ']', ',', '&', '*', '?', '|', '-', '<', '>', '=', '!', '%', '@', '`', '"', "'"]):
                return f'"{value}"'
            return value
        return str(value)


# Convenience functions
def parse(content: str) -> Frontmatter:
    """Parse frontmatter from content"""
    parser = FrontmatterParser()
    return parser.parse(content)


def stringify(attributes: Dict[str, Any], body: str = "") -> str:
    """Convert to frontmatter format"""
    parser = FrontmatterParser()
    return parser.stringify(attributes, body)


__all__ = [
    "Frontmatter",
    "FrontmatterParser",
    "parse",
    "stringify",
]
