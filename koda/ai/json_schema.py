"""
JSON Schema Validator
Equivalent to Pi Mono's packages/ai/src/json-schema.ts

JSON Schema validation utilities.
"""
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass


try:
    import jsonschema
    from jsonschema import validate, ValidationError as JsonSchemaValidationError
    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False
    JsonSchemaValidationError = Exception


@dataclass
class ValidationResult:
    """JSON schema validation result"""
    valid: bool
    errors: List[str]


class JSONSchemaValidator:
    """
    JSON Schema validator.
    
    Validates data against JSON Schema.
    
    Example:
        >>> validator = JSONSchemaValidator()
        >>> schema = {"type": "object", "properties": {"name": {"type": "string"}}}
        >>> result = validator.validate({"name": "test"}, schema)
        >>> result.valid
        True
    """
    
    def __init__(self):
        self._cache: Dict[str, Any] = {}
    
    def validate(self, data: Any, schema: Dict[str, Any]) -> ValidationResult:
        """
        Validate data against schema.
        
        Args:
            data: Data to validate
            schema: JSON Schema
            
        Returns:
            Validation result
        """
        if not HAS_JSONSCHEMA:
            # Fallback: basic type checking
            return self._basic_validate(data, schema)
        
        try:
            validate(instance=data, schema=schema)
            return ValidationResult(valid=True, errors=[])
        except JsonSchemaValidationError as e:
            return ValidationResult(valid=False, errors=[str(e)])
    
    def _basic_validate(self, data: Any, schema: Dict[str, Any]) -> ValidationResult:
        """Basic validation without jsonschema library"""
        errors = []
        
        schema_type = schema.get("type")
        if schema_type:
            if schema_type == "object" and not isinstance(data, dict):
                errors.append(f"Expected object, got {type(data).__name__}")
            elif schema_type == "array" and not isinstance(data, list):
                errors.append(f"Expected array, got {type(data).__name__}")
            elif schema_type == "string" and not isinstance(data, str):
                errors.append(f"Expected string, got {type(data).__name__}")
            elif schema_type == "number" and not isinstance(data, (int, float)):
                errors.append(f"Expected number, got {type(data).__name__}")
            elif schema_type == "integer" and not isinstance(data, int):
                errors.append(f"Expected integer, got {type(data).__name__}")
            elif schema_type == "boolean" and not isinstance(data, bool):
                errors.append(f"Expected boolean, got {type(data).__name__}")
        
        # Check required properties
        if "required" in schema and isinstance(data, dict):
            for prop in schema["required"]:
                if prop not in data:
                    errors.append(f"Missing required property: {prop}")
        
        return ValidationResult(valid=len(errors) == 0, errors=errors)
    
    def is_valid(self, data: Any, schema: Dict[str, Any]) -> bool:
        """
        Check if data is valid against schema.
        
        Args:
            data: Data to validate
            schema: JSON Schema
            
        Returns:
            True if valid
        """
        return self.validate(data, schema).valid


def validate_json_schema(data: Any, schema: Dict[str, Any]) -> ValidationResult:
    """
    Validate data against JSON Schema.
    
    Args:
        data: Data to validate
        schema: JSON Schema
        
    Returns:
        Validation result
    """
    validator = JSONSchemaValidator()
    return validator.validate(data, schema)


__all__ = [
    "JSONSchemaValidator",
    "ValidationResult",
    "validate_json_schema",
]
