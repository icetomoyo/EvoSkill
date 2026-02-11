"""
Prompt Templates
Equivalent to Pi Mono's packages/coding-agent/src/core/prompt-templates.ts

Template system for prompts with variable substitution.
"""
import re
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Template:
    """Prompt template"""
    name: str
    template: str
    description: str = ""
    variables: List[str] = None
    
    def __post_init__(self):
        if self.variables is None:
            self.variables = self._extract_variables()
    
    def _extract_variables(self) -> List[str]:
        """Extract variable names from template"""
        pattern = r'\{\{(\w+)\}\}'
        return list(set(re.findall(pattern, self.template)))
    
    def render(self, **kwargs) -> str:
        """Render template with variables"""
        result = self.template
        for key, value in kwargs.items():
            result = result.replace(f"{{{{{key}}}}}", str(value))
        return result


class PromptTemplateRegistry:
    """
    Registry for prompt templates.
    
    Manages named templates with variable substitution.
    
    Example:
        >>> registry = PromptTemplateRegistry()
        >>> registry.register("code_review", "Review: {{language}}\\n\\n{{code}}")
        >>> prompt = registry.render("code_review", language="python", code="def foo():...")
    """
    
    def __init__(self):
        self._templates: Dict[str, Template] = {}
        self._load_defaults()
    
    def _load_defaults(self):
        """Load default templates"""
        defaults = {
            "code_review": Template(
                name="code_review",
                template="""Please review the following {{language}} code:

```{{language}}
{{code}}
```

Focus on:
1. Code quality and readability
2. Potential bugs or issues
3. Performance considerations
4. Best practices

Provide specific suggestions for improvement.""",
                description="Code review template"
            ),
            "explain_code": Template(
                name="explain_code",
                template="""Explain what the following {{language}} code does:

```{{language}}
{{code}}
```

Please be concise and focus on:
- What the code accomplishes
- Key logic or algorithms
- Any important edge cases""",
                description="Code explanation template"
            ),
            "generate_tests": Template(
                name="generate_tests",
                template="""Generate unit tests for the following {{language}} code:

```{{language}}
{{code}}
```

Requirements:
- Use {{framework}} testing framework
- Cover main functionality
- Include edge cases
- Tests should be self-contained

Provide the complete test file.""",
                description="Test generation template"
            ),
            "refactor": Template(
                name="refactor",
                template="""Refactor the following {{language}} code to improve {{goal}}:

```{{language}}
{{code}}
```

Please provide:
1. The refactored code
2. Explanation of changes made
3. Why these changes improve the code""",
                description="Code refactoring template"
            ),
            "commit_message": Template(
                name="commit_message",
                template="""Generate a concise commit message for the following changes:

```diff
{{diff}}
```

Requirements:
- Use conventional commit format (type: description)
- Maximum 50 characters for the subject
- Optional detailed body if needed
- Be specific but concise""",
                description="Commit message generation"
            ),
            "documentation": Template(
                name="documentation",
                template="""Generate {{style}} documentation for the following {{language}} code:

```{{language}}
{{code}}
```

Include:
- Function/class description
- Parameter descriptions
- Return value description
- Usage examples
- Any important notes""",
                description="Documentation generation"
            ),
        }
        
        for name, template in defaults.items():
            self._templates[name] = template
    
    def register(
        self,
        name: str,
        template: str,
        description: str = "",
        variables: Optional[List[str]] = None
    ):
        """
        Register a template.
        
        Args:
            name: Template name
            template: Template string with {{variable}} placeholders
            description: Template description
            variables: Explicit variable list (auto-detected if None)
        """
        self._templates[name] = Template(
            name=name,
            template=template,
            description=description,
            variables=variables
        )
    
    def get(self, name: str) -> Optional[Template]:
        """Get a template by name"""
        return self._templates.get(name)
    
    def render(self, name: str, **kwargs) -> str:
        """
        Render a template.
        
        Args:
            name: Template name
            **kwargs: Variable values
            
        Returns:
            Rendered template
            
        Raises:
            KeyError: If template not found
        """
        template = self._templates.get(name)
        if not template:
            raise KeyError(f"Template not found: {name}")
        
        return template.render(**kwargs)
    
    def list_templates(self) -> List[str]:
        """List all template names"""
        return list(self._templates.keys())
    
    def get_info(self, name: str) -> Optional[Dict[str, Any]]:
        """Get template info"""
        template = self._templates.get(name)
        if not template:
            return None
        
        return {
            "name": template.name,
            "description": template.description,
            "variables": template.variables,
        }
    
    def load_from_file(self, path: Path):
        """
        Load templates from JSON/YAML file.
        
        Args:
            path: Path to template file
        """
        if path.suffix == '.json':
            import json
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        elif path.suffix in ('.yaml', '.yml'):
            try:
                import yaml
                with open(path, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
            except ImportError:
                raise ImportError("PyYAML required for YAML template files")
        else:
            raise ValueError(f"Unsupported file format: {path.suffix}")
        
        for name, template_data in data.items():
            self.register(
                name=name,
                template=template_data.get('template', ''),
                description=template_data.get('description', ''),
                variables=template_data.get('variables')
            )
    
    def save_to_file(self, path: Path):
        """
        Save templates to file.
        
        Args:
            path: Output path
        """
        data = {}
        for name, template in self._templates.items():
            data[name] = {
                'template': template.template,
                'description': template.description,
                'variables': template.variables
            }
        
        if path.suffix == '.json':
            import json
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        elif path.suffix in ('.yaml', '.yml'):
            try:
                import yaml
                with open(path, 'w', encoding='utf-8') as f:
                    yaml.dump(data, f, default_flow_style=False)
            except ImportError:
                raise ImportError("PyYAML required for YAML output")
        else:
            raise ValueError(f"Unsupported file format: {path.suffix}")


# Global registry
_default_registry: Optional[PromptTemplateRegistry] = None


def get_default_registry() -> PromptTemplateRegistry:
    """Get default template registry"""
    global _default_registry
    if _default_registry is None:
        _default_registry = PromptTemplateRegistry()
    return _default_registry


def render_template(name: str, **kwargs) -> str:
    """Render template using default registry"""
    registry = get_default_registry()
    return registry.render(name, **kwargs)


__all__ = [
    "PromptTemplateRegistry",
    "Template",
    "get_default_registry",
    "render_template",
]
