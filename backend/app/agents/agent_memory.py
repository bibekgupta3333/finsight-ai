"""
Agent Memory Management.

Implements short-term, working, and long-term memory for agents.
"""

from typing import Dict, Any, List, Optional
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field


class MemoryType(str, Enum):
    """Types of memory for agents."""
    
    SHORT_TERM = "short_term"  # Current transaction context
    WORKING = "working"  # Intermediate reasoning steps
    LONG_TERM = "long_term"  # Historical fraud patterns


class MemoryEntry(BaseModel):
    """Single memory entry."""
    
    key: str
    value: Any
    memory_type: MemoryType
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AgentMemory:
    """
    Memory system for agents.
    
    Provides short-term, working, and long-term memory storage with
    read/write policies and memory cleanup.
    """
    
    def __init__(
        self,
        max_short_term: int = 10,
        max_working: int = 100,
        max_long_term: int = 1000,
    ):
        """
        Initialize agent memory.
        
        Args:
            max_short_term: Max short-term memory entries
            max_working: Max working memory entries
            max_long_term: Max long-term memory entries
        """
        self.max_short_term = max_short_term
        self.max_working = max_working
        self.max_long_term = max_long_term
        
        self._short_term: Dict[str, MemoryEntry] = {}
        self._working: Dict[str, MemoryEntry] = {}
        self._long_term: Dict[str, MemoryEntry] = {}
    
    def store(
        self,
        key: str,
        value: Any,
        memory_type: MemoryType,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Store value in memory.
        
        Args:
            key: Memory key
            value: Value to store
            memory_type: Type of memory
            metadata: Optional metadata
        """
        entry = MemoryEntry(
            key=key,
            value=value,
            memory_type=memory_type,
            metadata=metadata or {},
        )
        
        if memory_type == MemoryType.SHORT_TERM:
            self._short_term[key] = entry
            self._cleanup_memory(self._short_term, self.max_short_term)
        elif memory_type == MemoryType.WORKING:
            self._working[key] = entry
            self._cleanup_memory(self._working, self.max_working)
        else:  # LONG_TERM
            self._long_term[key] = entry
            self._cleanup_memory(self._long_term, self.max_long_term)
    
    def retrieve(
        self,
        key: str,
        memory_type: Optional[MemoryType] = None,
    ) -> Optional[Any]:
        """
        Retrieve value from memory.
        
        Args:
            key: Memory key
            memory_type: Type of memory (searches all if None)
        
        Returns:
            Retrieved value or None
        """
        if memory_type:
            store = self._get_store(memory_type)
            entry = store.get(key)
            return entry.value if entry else None
        
        # Search all memory types
        for store in [self._short_term, self._working, self._long_term]:
            entry = store.get(key)
            if entry:
                return entry.value
        
        return None
    
    def list_memories(
        self,
        memory_type: Optional[MemoryType] = None,
    ) -> List[MemoryEntry]:
        """
        List all memories of a type.
        
        Args:
            memory_type: Type to list (all if None)
        
        Returns:
            List of memory entries
        """
        if memory_type:
            store = self._get_store(memory_type)
            return list(store.values())
        
        # Return all memories
        all_memories = []
        all_memories.extend(self._short_term.values())
        all_memories.extend(self._working.values())
        all_memories.extend(self._long_term.values())
        return all_memories
    
    def clear(self, memory_type: Optional[MemoryType] = None) -> None:
        """
        Clear memory.
        
        Args:
            memory_type: Type to clear (all if None)
        """
        if memory_type:
            store = self._get_store(memory_type)
            store.clear()
        else:
            self._short_term.clear()
            self._working.clear()
            self._long_term.clear()
    
    def _get_store(self, memory_type: MemoryType) -> Dict[str, MemoryEntry]:
        """Get memory store by type."""
        if memory_type == MemoryType.SHORT_TERM:
            return self._short_term
        elif memory_type == MemoryType.WORKING:
            return self._working
        else:
            return self._long_term
    
    def _cleanup_memory(
        self,
        store: Dict[str, MemoryEntry],
        max_size: int,
    ) -> None:
        """
        Cleanup memory when exceeding max size.
        
        Removes oldest entries first (FIFO).
        """
        if len(store) > max_size:
            # Sort by timestamp and remove oldest
            sorted_entries = sorted(
                store.items(),
                key=lambda x: x[1].timestamp,
            )
            entries_to_remove = sorted_entries[: len(store) - max_size]
            for key, _ in entries_to_remove:
                del store[key]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics."""
        return {
            "short_term": {
                "count": len(self._short_term),
                "max": self.max_short_term,
                "usage": len(self._short_term) / self.max_short_term,
            },
            "working": {
                "count": len(self._working),
                "max": self.max_working,
                "usage": len(self._working) / self.max_working,
            },
            "long_term": {
                "count": len(self._long_term),
                "max": self.max_long_term,
                "usage": len(self._long_term) / self.max_long_term,
            },
        }
