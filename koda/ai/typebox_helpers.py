"""
TypeBox Helpers
Equivalent to Pi Mono's packages/ai/src/typebox-helpers.ts

JSON Schema validation helpers using Pydantic (TypeScript's TypeBox equivalent).
"""
from typing import Any, Dict, List, Optional, Type, TypeVar, Callable, Union
from dataclasses import dataclass
import json

# Try to import Pydantic, fall back to basic validation
try:
    from pydantic import BaseModel, ValidationError, create_model, Field
    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False


T = TypeVar('T')


@dataclass
class ValidationResult:
    """Result of JSON Schema validation"""
    success: bool
    data: Optional[Any] = None
    errors: Optional[List[str]] = None


class SchemaBuilder:
    """
    Build JSON Schemas dynamically.
    
    Equivalent to TypeBox's schema builder in TypeScript.
    
    Example:
        >>> builder = SchemaBuilder()
        >>> schema = builder.object({
        ...     "name": builder.string(),
        ...     "age": builder.number()
        ... })
    """
    
    def string(self, min_length: Optional[int] = None, 
               max_length: Optional[int] = None,
               pattern: Optional[str] = None) -> Dict[str, Any]:
        """Create string schema"""
        schema = {"type": "string"}
        if min_length is not None:
            schema["minLength"] = min_length
        if max_length is not None:
            schema["maxLength"] = max_length
        if pattern is not None:
            schema["pattern"] = pattern
        return schema
    
    def number(self, minimum: Optional[float] = None,
               maximum: Optional[float] = None,
               exclusive_minimum: Optional[float] = None,
               exclusive_maximum: Optional[float] = None) -> Dict[str, Any]:
        """Create number schema"""
        schema = {"type": "number"}
        if minimum is not None:
            schema["minimum"] = minimum
        if maximum is not None:
            schema["maximum"] = maximum
        if exclusive_minimum is not None:
            schema["exclusiveMinimum"] = exclusive_minimum
        if exclusive_maximum is not None:
            schema["exclusiveMaximum"] = exclusive_maximum
        return schema
    
    def integer(self, minimum: Optional[int] = None,
                maximum: Optional[int] = None) -> Dict[str, Any]:
        """Create integer schema"""
        schema = {"type": "integer"}
        if minimum is not None:
            schema["minimum"] = minimum
        if maximum is not None:
            schema["maximum"] = maximum
        return schema
    
    def boolean(self) -> Dict[str, Any]:
        """Create boolean schema"""
        return {"type": "boolean"}
    
    def array(self, items: Optional[Dict[str, Any]] = None,
              min_items: Optional[int] = None,
              max_items: Optional[int] = None,
              unique_items: bool = False) -> Dict[str, Any]:
        """Create array schema"""
        schema = {"type": "array"}
        if items is not None:
            schema["items"] = items
        if min_items is not None:
            schema["minItems"] = min_items
        if max_items is not None:
            schema["maxItems"] = max_items
        if unique_items:
            schema["uniqueItems"] = True
        return schema
    
    def object(self, properties: Dict[str, Dict[str, Any]],
               required: Optional[List[str]] = None,
               additional_properties: Union[bool, Dict[str, Any]] = False,
               min_properties: Optional[int] = None,
               max_properties: Optional[int] = None) -> Dict[str, Any]:
        """Create object schema"""
        schema = {"type": "object", "properties": properties}
        if required is not None:
            schema["required"] = required
        if additional_properties is not True:
            schema["additionalProperties"] = additional_properties
        if min_properties is not None:
            schema["minProperties"] = min_properties
        if max_properties is not None:
            schema["maxProperties"] = max_properties
        return schema
    
    def null(self) -> Dict[str, Any]:
        """Create null schema"""
        return {"type": "null"}
    
    def any_of(self, schemas: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create anyOf schema (union)"""
        return {"anyOf": schemas}
    
    def all_of(self, schemas: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create allOf schema (intersection)"""
        return {"allOf": schemas}
    
    def one_of(self, schemas: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create oneOf schema (exactly one)"""
        return {"oneOf": schemas}
    
    def enum(self, values: List[str]) -> Dict[str, Any]:
        """Create enum schema"""
        return {"enum": values}
    
    def const(self, value: Any) -> Dict[str, Any]:
        """Create const schema"""
        return {"const": value}
    
    def ref(self, ref: str) -> Dict[str, Any]:
        """Create $ref schema"""
        return {"$ref": ref}
    
    def optional(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Make schema optional (nullable)"""
        if "anyOf" in schema:
            return {"anyOf": schema["anyOf"] + [{"type": "null"}]}
        return {"anyOf": [schema, {"type": "null"}]}
    
    def default(self, schema: Dict[str, Any], default: Any) -> Dict[str, Any]:
        """Add default value to schema"""
        schema_copy = schema.copy()
        schema_copy["default"] = default
        return schema_copy


class Validator:
    """
    JSON Schema validator.
    
    Validates data against JSON Schema definitions.
    """
    
    def __init__(self, schema: Optional[Dict[str, Any]] = None):
        self.schema = schema or {}
    
    def validate(self, data: Any) -> ValidationResult:
        """
        Validate data against schema.
        
        Args:
            data: Data to validate
            
        Returns:
            Validation result
        """
        if not self.schema:
            return ValidationResult(success=True, data=data)
        
        errors = self._validate_value(data, self.schema, "")
        
        if errors:
            return ValidationResult(success=False, errors=errors)
        
        return ValidationResult(success=True, data=data)
    
    def _validate_value(self, value: Any, schema: Dict[str, Any], 
                        path: str) -> List[str]:
        """Validate a value against schema (internal)"""
        errors = []
        
        # Handle anyOf
        if "anyOf" in schema:
            any_errors = []
            for subschema in schema["anyOf"]:
                sub_errors = self._validate_value(value, subschema, path)
                if not sub_errors:
                    return []  # Valid against at least one
                any_errors.extend(sub_errors)
            errors.append(f"{path}: Value does not match anyOf schema")
            return errors
        
        # Handle const
        if "const" in schema:
            if value != schema["const"]:
                errors.append(f"{path}: Expected {schema['const']}, got {value}")
            return errors
        
        # Handle enum
        if "enum" in schema:
            if value not in schema["enum"]:
                errors.append(f"{path}: Value must be one of {schema['enum']}")
            return errors
        
        # Type validation
        if "type" in schema:
            type_errors = self._validate_type(value, schema["type"], path, schema)
            errors.extend(type_errors)
        
        return errors
    
    def _validate_type(self, value: Any, type_name: str, 
                       path: str, schema: Dict[str, Any]) -> List[str]:
        """Validate type-specific constraints"""
        errors = []
        
        if type_name == "string":
            if not isinstance(value, str):
                errors.append(f"{path}: Expected string, got {type(value).__name__}")
                return errors
            
            # String constraints
            if "minLength" in schema and len(value) < schema["minLength"]:
                errors.append(f"{path}: String too short (min {schema['minLength']})")
            if "maxLength" in schema and len(value) > schema["maxLength"]:
                errors.append(f"{path}: String too long (max {schema['maxLength']})")
        
        elif type_name == "number":
            if not isinstance(value, (int, float)):
                errors.append(f"{path}: Expected number, got {type(value).__name__}")
                return errors
            
            # Number constraints
            if "minimum" in schema and value < schema["minimum"]:
                errors.append(f"{path}: Number below minimum {schema['minimum']}")
            if "maximum" in schema and value > schema["maximum"]:
                errors.append(f"{path}: Number above maximum {schema['maximum']}")
        
        elif type_name == "integer":
            if not isinstance(value, int) or isinstance(value, bool):
                errors.append(f"{path}: Expected integer, got {type(value).__name__}")
                return errors
            
            if "minimum" in schema and value < schema["minimum"]:
                errors.append(f"{path}: Integer below minimum {schema['minimum']}")
            if "maximum" in schema and value > schema["maximum"]:
                errors.append(f"{path}: Integer above maximum {schema['maximum']}")
        
        elif type_name == "boolean":
            if not isinstance(value, bool):
                errors.append(f"{path}: Expected boolean, got {type(value).__name__}")
        
        elif type_name == "array":
            if not isinstance(value, list):
                errors.append(f"{path}: Expected array, got {type(value).__name__}")
                return errors
            
            # Array constraints
            if "minItems" in schema and len(value) < schema["minItems"]:
                errors.append(f"{path}: Array too short (min {schema['minItems']})")
            if "maxItems" in schema and len(value) > schema["maxItems"]:
                errors.append(f"{path}: Array too long (max {schema['maxItems']})")
            
            # Validate items
            if "items" in schema:
                for i, item in enumerate(value):
                    item_errors = self._validate_value(item, schema["items"], f"{path}[{i}]")
                    errors.extend(item_errors)
        
        elif type_name == "object":
            if not isinstance(value, dict):
                errors.append(f"{path}: Expected object, got {type(value).__name__}")
                return errors
            
            # Check required properties
            if "required" in schema:
                for prop in schema["required"]:
                    if prop not in value:
                        errors.append(f"{path}: Missing required property '{prop}'")
            
            # Validate properties
            if "properties" in schema:
                for prop, prop_schema in schema["properties"].items():
                    if prop in value:
                        prop_errors = self._validate_value(
                            value[prop], prop_schema, f"{path}.{prop}" if path else prop
                        )
                        errors.extend(prop_errors)
        
        elif type_name == "null":
            if value is not None:
                errors.append(f"{path}: Expected null, got {type(value).__name__}")
        
        return errors


class PydanticValidator:
    """
    Pydantic-based validator (preferred when available).
    
    Provides more robust validation with automatic type coercion.
    """
    
    def __init__(self, model_class: Optional[Any] = None):
        self.model_class = model_class
    
    def validate(self, data: Any) -> ValidationResult:
        """Validate using Pydantic model"""
        if not PYDANTIC_AVAILABLE or self.model_class is None:
            return ValidationResult(success=True, data=data)
        
        try:
            if isinstance(data, dict):
                validated = self.model_class(**data)
            else:
                validated = self.model_class.model_validate(data)
            
            # Convert back to dict for consistency
            return ValidationResult(
                success=True,
                data=validated.model_dump() if hasattr(validated, 'model_dump') 
                     else validated.dict()
            )
        except ValidationError as e:
            errors = []
            for err in e.errors():
                loc = ".".join(str(x) for x in err.get("loc", []))
                errors.append(f"{loc}: {err.get('msg', 'Validation error')}")
            return ValidationResult(success=False, errors=errors)


def create_validator(schema: Dict[str, Any]) -> Validator:
    """
    Create a validator for a schema.
    
    Args:
        schema: JSON Schema
        
    Returns:
        Validator instance
    """
    return Validator(schema)


def validate_json(data: Union[str, Dict], schema: Dict[str, Any]) -> ValidationResult:
    """
    Validate JSON data against schema.
    
    Args:
        data: JSON string or dict
        schema: JSON Schema
        
    Returns:
        Validation result
    """
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except json.JSONDecodeError as e:
            return ValidationResult(
                success=False,
                errors=[f"Invalid JSON: {e}"]
            )
    
    validator = Validator(schema)
    return validator.validate(data)


__all__ = [
    "SchemaBuilder",
    "Validator",
    "ValidationResult",
    "PydanticValidator",
    "create_validator",
    "validate_json",
]
