"""
Edit Operations
Equivalent to Pi Mono's packages/ai/src/edits.ts

Pluggable edit operations for file modifications.
"""
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass
from enum import Enum


class EditType(Enum):
    """Types of edit operations"""
    INSERT = "insert"
    DELETE = "delete"
    REPLACE = "replace"
    CREATE = "create"


@dataclass
class EditOperation:
    """A single edit operation"""
    type: EditType
    path: str
    content: Optional[str] = None
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    old_content: Optional[str] = None
    new_content: Optional[str] = None


@dataclass
class EditResult:
    """Result of an edit operation"""
    success: bool
    operation: EditOperation
    error: Optional[str] = None
    affected_lines: int = 0


class EditProcessor:
    """
    Processes edit operations on files.
    
    Supports pluggable edit operations for modifying file content.
    
    Example:
        >>> processor = EditProcessor()
        >>> op = EditOperation(
        ...     type=EditType.REPLACE,
        ...     path="/tmp/test.txt",
        ...     old_content="old",
        ...     new_content="new"
        ... )
        >>> result = processor.apply(op)
    """
    
    def __init__(self):
        self._handlers: Dict[EditType, Callable[[EditOperation], EditResult]] = {}
        self._register_default_handlers()
    
    def _register_default_handlers(self):
        """Register default edit handlers"""
        self._handlers[EditType.CREATE] = self._handle_create
        self._handlers[EditType.INSERT] = self._handle_insert
        self._handlers[EditType.DELETE] = self._handle_delete
        self._handlers[EditType.REPLACE] = self._handle_replace
    
    def register_handler(
        self,
        edit_type: EditType,
        handler: Callable[[EditOperation], EditResult]
    ):
        """
        Register a custom handler for an edit type.
        
        Args:
            edit_type: Type of edit
            handler: Handler function
        """
        self._handlers[edit_type] = handler
    
    def apply(self, operation: EditOperation) -> EditResult:
        """
        Apply an edit operation.
        
        Args:
            operation: Edit operation to apply
            
        Returns:
            Result of the operation
        """
        handler = self._handlers.get(operation.type)
        if not handler:
            return EditResult(
                success=False,
                operation=operation,
                error=f"No handler for edit type: {operation.type}"
            )
        
        return handler(operation)
    
    def apply_many(self, operations: List[EditOperation]) -> List[EditResult]:
        """
        Apply multiple edit operations.
        
        Args:
            operations: List of operations
            
        Returns:
            List of results
        """
        return [self.apply(op) for op in operations]
    
    def _handle_create(self, op: EditOperation) -> EditResult:
        """Handle CREATE operation"""
        try:
            from pathlib import Path
            path = Path(op.path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(op.content or "", encoding="utf-8")
            return EditResult(success=True, operation=op, affected_lines=1)
        except Exception as e:
            return EditResult(success=False, operation=op, error=str(e))
    
    def _handle_insert(self, op: EditOperation) -> EditResult:
        """Handle INSERT operation"""
        try:
            from pathlib import Path
            path = Path(op.path)
            
            if not path.exists():
                return EditResult(success=False, operation=op, error="File not found")
            
            lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
            insert_line = op.start_line or len(lines)
            
            content_lines = (op.content or "").splitlines(keepends=True)
            if content_lines and not content_lines[-1].endswith('\n'):
                content_lines[-1] += '\n'
            
            lines = lines[:insert_line] + content_lines + lines[insert_line:]
            path.write_text("".join(lines), encoding="utf-8")
            
            return EditResult(success=True, operation=op, affected_lines=len(content_lines))
        except Exception as e:
            return EditResult(success=False, operation=op, error=str(e))
    
    def _handle_delete(self, op: EditOperation) -> EditResult:
        """Handle DELETE operation"""
        try:
            from pathlib import Path
            path = Path(op.path)
            
            if not path.exists():
                return EditResult(success=False, operation=op, error="File not found")
            
            lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
            start = op.start_line or 0
            end = op.end_line or len(lines)
            
            affected = end - start
            lines = lines[:start] + lines[end:]
            path.write_text("".join(lines), encoding="utf-8")
            
            return EditResult(success=True, operation=op, affected_lines=affected)
        except Exception as e:
            return EditResult(success=False, operation=op, error=str(e))
    
    def _handle_replace(self, op: EditOperation) -> EditResult:
        """Handle REPLACE operation"""
        try:
            from pathlib import Path
            path = Path(op.path)
            
            if not path.exists():
                return EditResult(success=False, operation=op, error="File not found")
            
            content = path.read_text(encoding="utf-8")
            
            if op.old_content and op.new_content is not None:
                # Content-based replacement
                if op.old_content not in content:
                    return EditResult(
                        success=False,
                        operation=op,
                        error="Old content not found in file"
                    )
                new_content = content.replace(op.old_content, op.new_content, 1)
                affected = len(op.new_content.splitlines()) if op.new_content else 0
            elif op.content is not None:
                # Full content replacement
                new_content = op.content
                affected = len(new_content.splitlines())
            else:
                return EditResult(
                    success=False,
                    operation=op,
                    error="No replacement content provided"
                )
            
            path.write_text(new_content, encoding="utf-8")
            return EditResult(success=True, operation=op, affected_lines=affected)
        except Exception as e:
            return EditResult(success=False, operation=op, error=str(e))


__all__ = [
    "EditOperation",
    "EditProcessor",
    "EditResult",
    "EditType",
]
