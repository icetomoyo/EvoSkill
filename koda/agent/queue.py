"""
Message Queue

Queue system for message delivery modes.
Similar to Pi's message queue with steering and follow-up modes.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
from datetime import datetime


class DeliveryMode(Enum):
    """Message delivery mode"""
    STEERING = "steering"      # Interrupts current work
    FOLLOW_UP = "follow_up"    # Waits for completion


@dataclass
class QueuedMessage:
    """Queued message"""
    content: str
    mode: DeliveryMode
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)


class MessageQueue:
    """
    Message queue for agent communication
    
    Supports Pi-style message queuing:
    - Steering messages (interrupt current work)
    - Follow-up messages (wait for completion)
    - One-at-a-time or all-at-once delivery
    """
    
    def __init__(
        self,
        steering_mode: str = "one-at-a-time",
        follow_up_mode: str = "one-at-a-time"
    ):
        """
        Args:
            steering_mode: "one-at-a-time" or "all"
            follow_up_mode: "one-at-a-time" or "all"
        """
        self.steering_mode = steering_mode
        self.follow_up_mode = follow_up_mode
        self._queue: List[QueuedMessage] = []
        self._current: Optional[QueuedMessage] = None
    
    def queue(
        self,
        content: str,
        mode: DeliveryMode = DeliveryMode.STEERING,
        metadata: Optional[Dict[str, Any]] = None
    ) -> QueuedMessage:
        """
        Add message to queue
        
        Args:
            content: Message content
            mode: Delivery mode
            metadata: Additional metadata
            
        Returns:
            Queued message
        """
        msg = QueuedMessage(
            content=content,
            mode=mode,
            metadata=metadata or {}
        )
        self._queue.append(msg)
        return msg
    
    def queue_steering(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> QueuedMessage:
        """Queue steering message (interrupts current work)"""
        return self.queue(content, DeliveryMode.STEERING, metadata)
    
    def queue_follow_up(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> QueuedMessage:
        """Queue follow-up message (waits for completion)"""
        return self.queue(content, DeliveryMode.FOLLOW_UP, metadata)
    
    def get_next(self) -> Optional[QueuedMessage]:
        """
        Get next message to deliver
        
        Returns:
            Next message or None
        """
        if not self._queue:
            return None
        
        # Check for steering messages first
        steering_msgs = [m for m in self._queue if m.mode == DeliveryMode.STEERING]
        
        if steering_msgs:
            # Deliver steering messages based on mode
            if self.steering_mode == "all":
                # Combine all steering messages
                combined = "\n\n".join(m.content for m in steering_msgs)
                self._queue = [m for m in self._queue if m.mode != DeliveryMode.STEERING]
                return QueuedMessage(
                    content=combined,
                    mode=DeliveryMode.STEERING
                )
            else:
                # One at a time
                msg = steering_msgs[0]
                self._queue.remove(msg)
                return msg
        
        # Then follow-up messages
        follow_up_msgs = [m for m in self._queue if m.mode == DeliveryMode.FOLLOW_UP]
        
        if follow_up_msgs:
            if self.follow_up_mode == "all":
                combined = "\n\n".join(m.content for m in follow_up_msgs)
                self._queue = []
                return QueuedMessage(
                    content=combined,
                    mode=DeliveryMode.FOLLOW_UP
                )
            else:
                msg = follow_up_msgs[0]
                self._queue.remove(msg)
                return msg
        
        return None
    
    def peek(self) -> Optional[QueuedMessage]:
        """Peek at next message without removing"""
        if not self._queue:
            return None
        return self._queue[0]
    
    def has_pending(self) -> bool:
        """Check if queue has pending messages"""
        return len(self._queue) > 0
    
    def get_pending_count(self) -> int:
        """Get number of pending messages"""
        return len(self._queue)
    
    def get_pending_steering(self) -> int:
        """Get number of pending steering messages"""
        return sum(1 for m in self._queue if m.mode == DeliveryMode.STEERING)
    
    def clear(self) -> List[QueuedMessage]:
        """
        Clear all messages
        
        Returns:
            Cleared messages
        """
        cleared = list(self._queue)
        self._queue = []
        return cleared
    
    def cancel(self) -> List[QueuedMessage]:
        """
        Cancel and return all queued messages
        Same as clear but semantically different
        """
        return self.clear()
