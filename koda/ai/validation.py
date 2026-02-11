"""
Message Validation
Equivalent to Pi Mono's packages/ai/src/validation.ts

Message validation utilities.
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from .types import Message, AssistantMessage, UserMessage


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


__all__ = [
    "MessageValidator",
    "ValidationResult",
]
