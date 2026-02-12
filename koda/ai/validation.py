"""
Message Validation
Equivalent to Pi Mono's packages/ai/src/validation.ts

Message validation utilities with AJV-style type coercion support.
"""
from typing import List, Dict, Any, Optional, Union, Type
from dataclasses import dataclass
from enum import Enum

from .types import Message, AssistantMessage, UserMessage


class CoercionTarget(Enum):
    """Target types for coercion"""
    STRING = "string"
    INTEGER = "integer"
    NUMBER = "number"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"


@dataclass
class ValidationResult:
    """Validation result"""
    valid: bool
    errors: List[str]


class MessageValidator:
    """
    Validates messages for correctness.
    
    Checks for common issues in message format and content.
    
    Example:
        >>> validator = MessageValidator()
        >>> result = validator.validate_messages([{"role": "user", "content": "hi"}])
        >>> result.valid
        True
    """
    
    def __init__(self):
        self.max_content_length = 1000000  # 1MB
    
    def validate_message(self, message: Any) -> ValidationResult:
        """
        Validate a single message.
        
        Args:
            message: Message to validate
            
        Returns:
            Validation result
        """
        errors = []
        
        # Check basic structure
        if not isinstance(message, dict):
            if hasattr(message, 'role') and hasattr(message, 'content'):
                # It's a dataclass-like object, convert to dict for validation
                message = {
                    'role': message.role,
                    'content': message.content,
                }
            else:
                return ValidationResult(valid=False, errors=["Message must be a dict or message object"])
        
        # Check required fields
        if "role" not in message:
            errors.append("Message missing 'role' field")
        elif message["role"] not in ("user", "assistant", "system", "tool"):
            errors.append(f"Invalid role: {message['role']}")
        
        if "content" not in message:
            errors.append("Message missing 'content' field")
        
        # Check content length
        content = message.get("content", "")
        if isinstance(content, str) and len(content) > self.max_content_length:
            errors.append(f"Content exceeds max length: {len(content)} > {self.max_content_length}")
        
        return ValidationResult(valid=len(errors) == 0, errors=errors)
    
    def validate_messages(self, messages: List[Any]) -> ValidationResult:
        """
        Validate a list of messages.
        
        Args:
            messages: Messages to validate
            
        Returns:
            Validation result
        """
        errors = []
        
        if not messages:
            return ValidationResult(valid=False, errors=["Messages list is empty"])
        
        for i, msg in enumerate(messages):
            result = self.validate_message(msg)
            if not result.valid:
                errors.extend([f"Message {i}: {e}" for e in result.errors])
        
        return ValidationResult(valid=len(errors) == 0, errors=errors)
    
    def validate_context(self, messages: List[Any], max_messages: int = 1000) -> ValidationResult:
        """
        Validate message context.
        
        Args:
            messages: Messages to validate
            max_messages: Maximum number of messages allowed
            
        Returns:
            Validation result
        """
        errors = []
        
        if len(messages) > max_messages:
            errors.append(f"Too many messages: {len(messages)} > {max_messages}")
        
        # Check for alternating user/assistant (basic check)
        if messages:
            first = messages[0]
            first_role = first.get("role") if isinstance(first, dict) else getattr(first, "role", None)
            if first_role == "assistant":
                errors.append("First message should not be from assistant")
        
        return ValidationResult(valid=len(errors) == 0, errors=errors)


def coerce_string(value: Any) -> Optional[str]:
    """
    Coerce a value to string.

    Args:
        value: Value to coerce

    Returns:
        Coerced string value or None if coercion fails
    """
    if value is None:
        return None
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        return value
    return str(value)


def coerce_number(value: Any) -> Optional[Union[int, float]]:
    """
    Coerce a value to number (int or float).

    Args:
        value: Value to coerce

    Returns:
        Coerced number value or None if coercion fails
    """
    if value is None:
        return None
    if isinstance(value, bool):
        return 1 if value else 0
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        try:
            # Try integer first
            if "." not in value and "e" not in value.lower():
                return int(value)
            return float(value)
        except (ValueError, TypeError):
            return None
    return None


def coerce_integer(value: Any) -> Optional[int]:
    """
    Coerce a value to integer.

    Args:
        value: Value to coerce

    Returns:
        Coerced integer value or None if coercion fails
    """
    if value is None:
        return None
    if isinstance(value, bool):
        return 1 if value else 0
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            # Handle float strings by converting to float first
            return int(float(value))
        except (ValueError, TypeError):
            return None
    return None


def coerce_boolean(value: Any) -> Optional[bool]:
    """
    Coerce a value to boolean.

    Supports common string representations:
    - "true", "1", "yes", "on" -> True
    - "false", "0", "no", "off" -> False

    Args:
        value: Value to coerce

    Returns:
        Coerced boolean value or None if coercion fails
    """
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        lower = value.lower().strip()
        if lower in ("true", "1", "yes", "on"):
            return True
        if lower in ("false", "0", "no", "off"):
            return False
        return None
    return None


def coerce_array(value: Any) -> Optional[List[Any]]:
    """
    Coerce a value to array.

    Args:
        value: Value to coerce

    Returns:
        Coerced array value or None if coercion fails
    """
    if value is None:
        return None
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    # Wrap single values in array
    return [value]


def coerce_object(value: Any) -> Optional[Dict[str, Any]]:
    """
    Coerce a value to object (dict).

    Args:
        value: Value to coerce

    Returns:
        Coerced object value or None if coercion fails
    """
    if value is None:
        return None
    if isinstance(value, dict):
        return value
    # Cannot coerce other types to object
    return None


def coerce_value(value: Any, target_type: Union[CoercionTarget, str]) -> Any:
    """
    Coerce a value to the specified target type.

    Args:
        value: Value to coerce
        target_type: Target type (CoercionTarget enum or string)

    Returns:
        Coerced value or original value if coercion fails
    """
    if isinstance(target_type, str):
        target_type = CoercionTarget(target_type)

    coercers = {
        CoercionTarget.STRING: coerce_string,
        CoercionTarget.NUMBER: coerce_number,
        CoercionTarget.INTEGER: coerce_integer,
        CoercionTarget.BOOLEAN: coerce_boolean,
        CoercionTarget.ARRAY: coerce_array,
        CoercionTarget.OBJECT: coerce_object,
    }

    coercer = coercers.get(target_type)
    if coercer:
        result = coercer(value)
        return result if result is not None else value
    return value


def coerce_types(
    data: Any,
    schema: Dict[str, Any],
    coerce_strings_to_numbers: bool = True,
    coerce_strings_to_booleans: bool = True,
    coerce_numbers_to_strings: bool = True,
) -> Any:
    """
    Recursively coerce types in data according to schema (AJV-style).

    This function performs type coercion similar to AJV's coerceTypes option.
    It processes data recursively to handle nested objects and arrays.

    Args:
        data: Data to coerce
        schema: JSON Schema-like type definition
        coerce_strings_to_numbers: Enable string to number coercion
        coerce_strings_to_booleans: Enable string to boolean coercion
        coerce_numbers_to_strings: Enable number to string coercion

    Returns:
        Coerced data with types converted according to schema

    Example:
        >>> schema = {"type": "object", "properties": {"age": {"type": "integer"}}}
        >>> coerce_types({"age": "25"}, schema)
        {'age': 25}

        >>> schema = {"type": "boolean"}
        >>> coerce_types("true", schema)
        True
    """
    if data is None:
        return None

    if not isinstance(schema, dict):
        return data

    schema_type = schema.get("type")

    # Handle multiple types (union types)
    if isinstance(schema_type, list):
        # Try each type in order until one succeeds
        for t in schema_type:
            coerced = coerce_types(
                data,
                {**schema, "type": t},
                coerce_strings_to_numbers,
                coerce_strings_to_booleans,
                coerce_numbers_to_strings,
            )
            # Check if coercion was successful
            if _check_type(coerced, t):
                return coerced
        return data

    # Handle string type
    if schema_type == "string" and coerce_numbers_to_strings:
        return coerce_string(data) or data

    # Handle number/integer types
    if schema_type in ("number", "integer") and coerce_strings_to_numbers:
        if schema_type == "integer":
            return coerce_integer(data) or data
        return coerce_number(data) or data

    # Handle boolean type
    if schema_type == "boolean" and coerce_strings_to_booleans:
        return coerce_boolean(data) or data

    # Handle array type
    if schema_type == "array":
        if not isinstance(data, list):
            data = coerce_array(data)
        if isinstance(data, list):
            items_schema = schema.get("items")
            if items_schema:
                return [
                    coerce_types(
                        item,
                        items_schema,
                        coerce_strings_to_numbers,
                        coerce_strings_to_booleans,
                        coerce_numbers_to_strings,
                    )
                    for item in data
                ]
        return data

    # Handle object type
    if schema_type == "object":
        if not isinstance(data, dict):
            data = coerce_object(data)
        if isinstance(data, dict):
            properties = schema.get("properties", {})
            additional_properties = schema.get("additionalProperties", True)

            result = {}
            for key, value in data.items():
                if key in properties:
                    # Coerce according to property schema
                    result[key] = coerce_types(
                        value,
                        properties[key],
                        coerce_strings_to_numbers,
                        coerce_strings_to_booleans,
                        coerce_numbers_to_strings,
                    )
                else:
                    # Keep as-is for additional properties
                    result[key] = value

            return result
        return data

    return data


def _check_type(value: Any, expected_type: str) -> bool:
    """Check if value matches expected type."""
    type_checkers = {
        "string": lambda v: isinstance(v, str),
        "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
        "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
        "boolean": lambda v: isinstance(v, bool),
        "array": lambda v: isinstance(v, list),
        "object": lambda v: isinstance(v, dict),
        "null": lambda v: v is None,
    }
    checker = type_checkers.get(expected_type)
    return checker(value) if checker else False


class SchemaValidator:
    """
    JSON Schema-like validator with type coercion support.

    Provides AJV-style validation with automatic type coercion.

    Example:
        >>> validator = SchemaValidator({"type": "integer"})
        >>> result = validator.validate("123", coerce=True)
        >>> result.valid
        True
        >>> result.coerced_value
        123
    """

    def __init__(self, schema: Dict[str, Any]):
        """
        Initialize validator with schema.

        Args:
            schema: JSON Schema-like definition
        """
        self.schema = schema

    def validate(
        self,
        data: Any,
        coerce: bool = True,
        coerce_strings_to_numbers: bool = True,
        coerce_strings_to_booleans: bool = True,
        coerce_numbers_to_strings: bool = True,
    ) -> "ValidationResult":
        """
        Validate data against schema with optional type coercion.

        Args:
            data: Data to validate
            coerce: Enable type coercion
            coerce_strings_to_numbers: Enable string to number coercion
            coerce_strings_to_booleans: Enable string to boolean coercion
            coerce_numbers_to_strings: Enable number to string coercion

        Returns:
            ValidationResult with coerced_value if coercion was applied
        """
        errors = []
        coerced_value = data

        # Apply coercion if enabled
        if coerce:
            coerced_value = coerce_types(
                data,
                self.schema,
                coerce_strings_to_numbers,
                coerce_strings_to_booleans,
                coerce_numbers_to_strings,
            )

        # Validate coerced value
        errors = self._validate_against_schema(coerced_value, self.schema)

        result = ValidationResult(
            valid=len(errors) == 0,
            errors=errors
        )
        result.coerced_value = coerced_value
        return result

    def _validate_against_schema(
        self,
        data: Any,
        schema: Dict[str, Any],
        path: str = ""
    ) -> List[str]:
        """
        Validate data against schema.

        Args:
            data: Data to validate
            schema: Schema to validate against
            path: Current path for error messages

        Returns:
            List of validation errors
        """
        errors = []

        if not isinstance(schema, dict):
            return errors

        schema_type = schema.get("type")

        # Type validation
        if schema_type:
            if isinstance(schema_type, list):
                if not any(_check_type(data, t) for t in schema_type):
                    errors.append(f"{path}: Expected one of types {schema_type}, got {type(data).__name__}")
            elif not _check_type(data, schema_type):
                errors.append(f"{path}: Expected type {schema_type}, got {type(data).__name__}")

        # Enum validation
        enum_values = schema.get("enum")
        if enum_values and data not in enum_values:
            errors.append(f"{path}: Value must be one of {enum_values}")

        # String validations
        if isinstance(data, str):
            min_length = schema.get("minLength")
            if min_length is not None and len(data) < min_length:
                errors.append(f"{path}: String length {len(data)} is less than minimum {min_length}")

            max_length = schema.get("maxLength")
            if max_length is not None and len(data) > max_length:
                errors.append(f"{path}: String length {len(data)} exceeds maximum {max_length}")

            pattern = schema.get("pattern")
            if pattern:
                import re
                if not re.search(pattern, data):
                    errors.append(f"{path}: String does not match pattern {pattern}")

        # Number validations
        if isinstance(data, (int, float)) and not isinstance(data, bool):
            minimum = schema.get("minimum")
            if minimum is not None and data < minimum:
                errors.append(f"{path}: Value {data} is less than minimum {minimum}")

            maximum = schema.get("maximum")
            if maximum is not None and data > maximum:
                errors.append(f"{path}: Value {data} exceeds maximum {maximum}")

            exclusive_minimum = schema.get("exclusiveMinimum")
            if exclusive_minimum is not None and data <= exclusive_minimum:
                errors.append(f"{path}: Value {data} must be greater than {exclusive_minimum}")

            exclusive_maximum = schema.get("exclusiveMaximum")
            if exclusive_maximum is not None and data >= exclusive_maximum:
                errors.append(f"{path}: Value {data} must be less than {exclusive_maximum}")

        # Array validations
        if isinstance(data, list):
            min_items = schema.get("minItems")
            if min_items is not None and len(data) < min_items:
                errors.append(f"{path}: Array length {len(data)} is less than minimum {min_items}")

            max_items = schema.get("maxItems")
            if max_items is not None and len(data) > max_items:
                errors.append(f"{path}: Array length {len(data)} exceeds maximum {max_items}")

            items_schema = schema.get("items")
            if items_schema:
                for i, item in enumerate(data):
                    item_path = f"{path}[{i}]" if path else f"[{i}]"
                    errors.extend(self._validate_against_schema(item, items_schema, item_path))

        # Object validations
        if isinstance(data, dict):
            required = schema.get("required", [])
            for field in required:
                if field not in data:
                    errors.append(f"{path}: Missing required field '{field}'")

            properties = schema.get("properties", {})
            for key, value in data.items():
                if key in properties:
                    prop_path = f"{path}.{key}" if path else key
                    errors.extend(self._validate_against_schema(value, properties[key], prop_path))

        return errors


def validate_with_coercion(
    data: Any,
    schema: Dict[str, Any],
    coerce_strings_to_numbers: bool = True,
    coerce_strings_to_booleans: bool = True,
    coerce_numbers_to_strings: bool = True,
) -> ValidationResult:
    """
    Validate data with AJV-style type coercion.

    This is a convenience function that creates a SchemaValidator
    and validates with coercion enabled.

    Args:
        data: Data to validate
        schema: JSON Schema-like type definition
        coerce_strings_to_numbers: Enable string to number coercion
        coerce_strings_to_booleans: Enable string to boolean coercion
        coerce_numbers_to_strings: Enable number to string coercion

    Returns:
        ValidationResult with coerced_value attribute containing the coerced data

    Example:
        >>> schema = {"type": "object", "properties": {"count": {"type": "integer"}}}
        >>> result = validate_with_coercion({"count": "42"}, schema)
        >>> result.valid
        True
        >>> result.coerced_value
        {'count': 42}
    """
    validator = SchemaValidator(schema)
    return validator.validate(
        data,
        coerce=True,
        coerce_strings_to_numbers=coerce_strings_to_numbers,
        coerce_strings_to_booleans=coerce_strings_to_booleans,
        coerce_numbers_to_strings=coerce_numbers_to_strings,
    )


__all__ = [
    "MessageValidator",
    "ValidationResult",
    "CoercionTarget",
    "coerce_string",
    "coerce_number",
    "coerce_integer",
    "coerce_boolean",
    "coerce_array",
    "coerce_object",
    "coerce_value",
    "coerce_types",
    "SchemaValidator",
    "validate_with_coercion",
]
