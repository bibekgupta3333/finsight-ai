"""
Memory Systems for FinSight AI - AGI-Inspired Memory Architecture

This module implements a comprehensive memory system with:
- Short-term memory (task context)
- Working memory (LRU cache)
- Long-term episodic memory (previous cases)
- Semantic memory (knowledge base)
- Procedural memory (successful patterns)

Key Features:
- Hybrid search (BM25 + vector similarity)
- Memory decay and summarization
- Intelligent retrieval and write policies
- ChromaDB integration for persistent storage
"""

import json
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple
from uuid import uuid4

import chromadb
from chromadb.config import Settings as ChromaSettings
from pydantic import BaseModel, Field


class MemoryType(str, Enum):
    """Types of memory in the system."""
    SHORT_TERM = "short_term"
    WORKING = "working"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"


class MemoryPriority(str, Enum):
    """Priority levels for memory storage."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Memory:
    """Base memory unit."""
    id: str
    memory_type: MemoryType
    content: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    priority: MemoryPriority = MemoryPriority.MEDIUM
    access_count: int = 0
    last_accessed: float = field(default_factory=time.time)
    relevance_score: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert memory to dictionary."""
        return {
            "id": self.id,
            "memory_type": self.memory_type.value,
            "content": self.content,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
            "priority": self.priority.value,
            "access_count": self.access_count,
            "last_accessed": self.last_accessed,
            "relevance_score": self.relevance_score,
        }

    def access(self):
        """Record memory access."""
        self.access_count += 1
        self.last_accessed = time.time()


class ShortTermMemory:
    """
    Short-term memory for current task context.
    - Stores current transaction, reasoning steps, tool calls
    - Limited capacity (~2000 tokens)
    - Cleared after task completion
    """

    def __init__(self, max_tokens: int = 2000):
        self.max_tokens = max_tokens
        self.current_task: Optional[Dict[str, Any]] = None
        self.reasoning_steps: List[Dict[str, Any]] = []
        self.tool_calls: List[Dict[str, Any]] = []
        self.context: Dict[str, Any] = {}
        self.token_count = 0

    def start_task(self, task_data: Dict[str, Any]):
        """Initialize memory for a new task."""
        self.clear()
        self.current_task = {
            "id": str(uuid4()),
            "data": task_data,
            "started_at": time.time(),
        }
        self.token_count += len(json.dumps(task_data)) // 4  # Rough estimate

    def add_reasoning_step(self, step: Dict[str, Any]):
        """Add a reasoning step to short-term memory."""
        self.reasoning_steps.append({
            "step": len(self.reasoning_steps) + 1,
            "content": step,
            "timestamp": time.time(),
        })
        self.token_count += len(json.dumps(step)) // 4
        self._manage_capacity()

    def add_tool_call(self, tool_name: str, args: Dict[str, Any], result: Any):
        """Record a tool call."""
        self.tool_calls.append({
            "tool": tool_name,
            "args": args,
            "result": result,
            "timestamp": time.time(),
        })
        self.token_count += (len(json.dumps(args)) + len(str(result))) // 4
        self._manage_capacity()

    def update_context(self, key: str, value: Any):
        """Update task context."""
        self.context[key] = value
        self.token_count += len(json.dumps({key: value})) // 4
        self._manage_capacity()

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of short-term memory."""
        return {
            "task": self.current_task,
            "reasoning_steps": len(self.reasoning_steps),
            "tool_calls": len(self.tool_calls),
            "context": self.context,
            "token_count": self.token_count,
        }

    def clear(self):
        """Clear all short-term memory."""
        self.current_task = None
        self.reasoning_steps = []
        self.tool_calls = []
        self.context = {}
        self.token_count = 0

    def _manage_capacity(self):
        """Remove oldest entries if capacity exceeded."""
        while self.token_count > self.max_tokens:
            if self.reasoning_steps:
                removed = self.reasoning_steps.pop(0)
                self.token_count -= len(json.dumps(removed)) // 4
            elif self.tool_calls:
                removed = self.tool_calls.pop(0)
                self.token_count -= len(json.dumps(removed)) // 4
            else:
                break


class WorkingMemory:
    """
    Working memory with LRU cache eviction.
    - Stores recently used policies, calculations, tool outputs
    - Fixed capacity with automatic eviction
    """

    def __init__(self, capacity: int = 100):
        self.capacity = capacity
        self.cache: OrderedDict[str, Memory] = OrderedDict()
        self.stats = {"hits": 0, "misses": 0, "evictions": 0}

    def put(self, key: str, content: Any, metadata: Optional[Dict] = None):
        """Store item in working memory."""
        if key in self.cache:
            self.cache.move_to_end(key)
            self.cache[key].content = content
            self.cache[key].access()
        else:
            if len(self.cache) >= self.capacity:
                evicted_key, evicted_memory = self.cache.popitem(last=False)
                self.stats["evictions"] += 1

            memory = Memory(
                id=key,
                memory_type=MemoryType.WORKING,
                content={"value": content},
                metadata=metadata or {},
            )
            self.cache[key] = memory

    def get(self, key: str) -> Optional[Any]:
        """Retrieve item from working memory."""
        if key in self.cache:
            self.cache.move_to_end(key)
            self.cache[key].access()
            self.stats["hits"] += 1
            return self.cache[key].content["value"]
        else:
            self.stats["misses"] += 1
            return None

    def contains(self, key: str) -> bool:
        """Check if key exists in working memory."""
        return key in self.cache

    def clear(self):
        """Clear all working memory."""
        self.cache.clear()

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_accesses = self.stats["hits"] + self.stats["misses"]
        hit_rate = self.stats["hits"] / total_accesses if total_accesses > 0 else 0

        return {
            "size": len(self.cache),
            "capacity": self.capacity,
            "hits": self.stats["hits"],
            "misses": self.stats["misses"],
            "evictions": self.stats["evictions"],
            "hit_rate": hit_rate,
        }


class EpisodicMemory:
    """
    Long-term episodic memory for previous cases.
    - Stores fraud cases, decisions, feedback
    - Timestamped episodes with metadata
    - ChromaDB-backed for persistence
    """

    def __init__(self, chroma_client: chromadb.Client, collection_name: str = "episodic_memory"):
        self.client = chroma_client
        self.collection_name = collection_name
        self.collection = self._get_or_create_collection()
        self.write_buffer: List[Memory] = []
        self.buffer_size = 10

    def _get_or_create_collection(self):
        """Get or create ChromaDB collection."""
        try:
            return self.client.get_collection(name=self.collection_name)
        except:
            return self.client.create_collection(
                name=self.collection_name,
                metadata={"description": "Long-term episodic memory for fraud cases"}
            )

    def store_episode(
        self,
        episode_id: str,
        content: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
        priority: MemoryPriority = MemoryPriority.MEDIUM,
    ):
        """Store an episode in long-term memory."""
        memory = Memory(
            id=episode_id,
            memory_type=MemoryType.EPISODIC,
            content=content,
            metadata=metadata or {},
            priority=priority,
        )

        # Add to buffer
        self.write_buffer.append(memory)

        # Flush if buffer is full
        if len(self.write_buffer) >= self.buffer_size:
            self.flush()

    def flush(self):
        """Flush write buffer to ChromaDB."""
        if not self.write_buffer:
            return

        ids = [m.id for m in self.write_buffer]
        documents = [json.dumps(m.content) for m in self.write_buffer]
        metadatas = [
            {
                **m.metadata,
                "timestamp": m.timestamp,
                "priority": m.priority.value,
                "memory_type": m.memory_type.value,
            }
            for m in self.write_buffer
        ]

        self.collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
        )

        self.write_buffer.clear()

    def retrieve_similar(
        self,
        query: str,
        n_results: int = 5,
        min_similarity: float = 0.7,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve similar episodes using vector search."""
        where = filters if filters else None

        results = self.collection.query(
            query_texts=[query],
            n_results=n_results,
            where=where,
        )

        episodes = []
        if results["ids"] and results["ids"][0]:
            for i, (id_, doc, metadata, distance) in enumerate(
                zip(
                    results["ids"][0],
                    results["documents"][0],
                    results["metadatas"][0],
                    results["distances"][0],
                )
            ):
                similarity = 1 - distance  # Convert distance to similarity
                if similarity >= min_similarity:
                    episodes.append({
                        "id": id_,
                        "content": json.loads(doc),
                        "metadata": metadata,
                        "similarity": similarity,
                    })

        return episodes

    def get_recent_episodes(
        self,
        n: int = 10,
        hours: int = 24,
    ) -> List[Dict[str, Any]]:
        """Get recent episodes within time window."""
        cutoff_time = time.time() - (hours * 3600)

        # Query with time filter
        results = self.collection.get(
            where={"timestamp": {"$gte": cutoff_time}},
            limit=n,
        )

        episodes = []
        if results["ids"]:
            for id_, doc, metadata in zip(
                results["ids"],
                results["documents"],
                results["metadatas"],
            ):
                episodes.append({
                    "id": id_,
                    "content": json.loads(doc),
                    "metadata": metadata,
                })

        return sorted(episodes, key=lambda x: x["metadata"].get("timestamp", 0), reverse=True)

    def count(self) -> int:
        """Count total episodes."""
        return self.collection.count()


class SemanticMemory:
    """
    Semantic memory for facts and knowledge.
    - Fraud policies, rules, thresholds
    - Knowledge base (RAG)
    - ChromaDB-backed with hybrid search
    """

    def __init__(self, chroma_client: chromadb.Client, collection_name: str = "semantic_memory"):
        self.client = chroma_client
        self.collection_name = collection_name
        self.collection = self._get_or_create_collection()

    def _get_or_create_collection(self):
        """Get or create ChromaDB collection."""
        try:
            return self.client.get_collection(name=self.collection_name)
        except:
            return self.client.create_collection(
                name=self.collection_name,
                metadata={"description": "Semantic memory for facts and knowledge"}
            )

    def store_knowledge(
        self,
        knowledge_id: str,
        content: str,
        category: str,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Store knowledge in semantic memory."""
        self.collection.add(
            ids=[knowledge_id],
            documents=[content],
            metadatas=[{
                **(metadata or {}),
                "category": category,
                "stored_at": time.time(),
            }],
        )

    def retrieve_knowledge(
        self,
        query: str,
        category: Optional[str] = None,
        n_results: int = 5,
    ) -> List[Dict[str, Any]]:
        """Retrieve relevant knowledge."""
        where = {"category": category} if category else None

        results = self.collection.query(
            query_texts=[query],
            n_results=n_results,
            where=where,
        )

        knowledge_items = []
        if results["ids"] and results["ids"][0]:
            for id_, doc, metadata, distance in zip(
                results["ids"][0],
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0],
            ):
                knowledge_items.append({
                    "id": id_,
                    "content": doc,
                    "metadata": metadata,
                    "relevance": 1 - distance,
                })

        return knowledge_items

    def get_by_category(self, category: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get all knowledge items in a category."""
        results = self.collection.get(
            where={"category": category},
            limit=limit,
        )

        items = []
        if results["ids"]:
            for id_, doc, metadata in zip(
                results["ids"],
                results["documents"],
                results["metadatas"],
            ):
                items.append({
                    "id": id_,
                    "content": doc,
                    "metadata": metadata,
                })

        return items


class ProceduralMemory:
    """
    Procedural memory for successful patterns and procedures.
    - Analysis procedures
    - Tool usage patterns
    - Successful reasoning chains
    """

    def __init__(self):
        self.procedures: Dict[str, Dict[str, Any]] = {}
        self.tool_patterns: Dict[str, List[Dict[str, Any]]] = {}
        self.successful_chains: List[Dict[str, Any]] = []
        self.success_threshold = 0.8

    def record_procedure(
        self,
        procedure_name: str,
        steps: List[str],
        success_rate: float,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Record a procedure."""
        self.procedures[procedure_name] = {
            "steps": steps,
            "success_rate": success_rate,
            "metadata": metadata or {},
            "usage_count": self.procedures.get(procedure_name, {}).get("usage_count", 0) + 1,
            "last_used": time.time(),
        }

    def record_tool_pattern(
        self,
        tool_name: str,
        args_pattern: Dict[str, Any],
        success: bool,
    ):
        """Record a tool usage pattern."""
        if tool_name not in self.tool_patterns:
            self.tool_patterns[tool_name] = []

        self.tool_patterns[tool_name].append({
            "args_pattern": args_pattern,
            "success": success,
            "timestamp": time.time(),
        })

        # Keep only recent patterns
        if len(self.tool_patterns[tool_name]) > 100:
            self.tool_patterns[tool_name] = self.tool_patterns[tool_name][-100:]

    def record_reasoning_chain(
        self,
        chain: List[str],
        outcome: str,
        success: bool,
        confidence: float,
    ):
        """Record a reasoning chain."""
        if success and confidence >= self.success_threshold:
            self.successful_chains.append({
                "chain": chain,
                "outcome": outcome,
                "confidence": confidence,
                "timestamp": time.time(),
            })

            # Keep top 50 successful chains
            self.successful_chains.sort(key=lambda x: x["confidence"], reverse=True)
            self.successful_chains = self.successful_chains[:50]

    def get_best_procedure(self, task_type: str) -> Optional[Dict[str, Any]]:
        """Get best procedure for a task type."""
        matching = [
            (name, proc) for name, proc in self.procedures.items()
            if task_type in name.lower()
        ]

        if not matching:
            return None

        # Return highest success rate
        best = max(matching, key=lambda x: x[1]["success_rate"])
        return {"name": best[0], **best[1]}

    def get_tool_success_rate(self, tool_name: str) -> float:
        """Calculate tool success rate."""
        if tool_name not in self.tool_patterns:
            return 0.0

        patterns = self.tool_patterns[tool_name]
        if not patterns:
            return 0.0

        successes = sum(1 for p in patterns if p["success"])
        return successes / len(patterns)

    def get_similar_chain(self, current_steps: List[str]) -> Optional[Dict[str, Any]]:
        """Find similar successful reasoning chain."""
        if not self.successful_chains:
            return None

        # Simple similarity based on step overlap
        best_match = None
        best_similarity = 0.0

        for chain_record in self.successful_chains:
            chain = chain_record["chain"]
            overlap = len(set(current_steps) & set(chain))
            similarity = overlap / max(len(current_steps), len(chain))

            if similarity > best_similarity:
                best_similarity = similarity
                best_match = chain_record

        return best_match if best_similarity > 0.5 else None


class MemoryManager:
    """
    Central memory manager coordinating all memory systems.
    Implements retrieval and write policies.
    """

    def __init__(
        self,
        chroma_host: Optional[str] = None,
        chroma_port: Optional[int] = None,
    ):
        """
        Initialize memory manager with all memory systems.

        Args:
            chroma_host: ChromaDB server host (defaults to env CHROMA_HOST or "localhost")
            chroma_port: ChromaDB server port (defaults to env CHROMA_PORT or 8000)
        """
        import os
        import logging

        logger = logging.getLogger(__name__)

        # Store ChromaDB connection params (lazy initialization)
        # Read from environment variables for Docker Compose compatibility
        self.chroma_host = chroma_host or os.getenv("CHROMA_HOST", "localhost")
        self.chroma_port = int(chroma_port or os.getenv("CHROMA_PORT", "8000"))

        logger.info(f"MemoryManager initialized with ChromaDB at {self.chroma_host}:{self.chroma_port}")

        self._chroma_client: Optional[chromadb.Client] = None
        self._chroma_available = None  # None = unknown, True/False = known state

        # Initialize memory systems (ChromaDB-dependent ones will be lazy)
        self.short_term = ShortTermMemory()
        self.working = WorkingMemory()
        self._episodic: Optional[EpisodicMemory] = None
        self._semantic: Optional[SemanticMemory] = None
        self.procedural = ProceduralMemory()

        # Retrieval policies
        self.retrieval_k = 5
        self.relevance_threshold = 0.7
        self.decay_factor = 0.95  # Decay per day

        # Write policies
        self.high_confidence_threshold = 0.8
        self.deduplication_threshold = 0.95

    async def _init_chroma_client(self) -> Optional[chromadb.Client]:
        """Initialize ChromaDB client in a thread pool to avoid blocking."""
        import asyncio

        def _create_client():
            try:
                client = chromadb.HttpClient(
                    host=self.chroma_host,
                    port=self.chroma_port,
                    settings=ChromaSettings(anonymized_telemetry=False),
                )
                # Test connection
                client.heartbeat()
                return client
            except Exception as e:
                print(f"Warning: ChromaDB not available at {self.chroma_host}:{self.chroma_port}: {e}")
                return None

        return await asyncio.to_thread(_create_client)

    @property
    def chroma_client(self) -> Optional[chromadb.Client]:
        """Synchronous property for non-async access (returns None if not initialized)."""
        return self._chroma_client

    async def get_chroma_client(self) -> Optional[chromadb.Client]:
        """Async method to get or initialize ChromaDB client."""
        if self._chroma_client is None and self._chroma_available != False:
            self._chroma_client = await self._init_chroma_client()
            self._chroma_available = self._chroma_client is not None
        return self._chroma_client

    @property
    def episodic(self) -> Optional[EpisodicMemory]:
        """Synchronous property for non-async access (returns None if not initialized)."""
        return self._episodic

    async def get_episodic(self) -> Optional[EpisodicMemory]:
        """Async method to get or initialize episodic memory."""
        if self._episodic is None:
            client = await self.get_chroma_client()
            if client is not None:
                import asyncio
                self._episodic = await asyncio.to_thread(
                    lambda: EpisodicMemory(client, "fraud_cases")
                )
        return self._episodic

    @property
    def semantic(self) -> Optional[SemanticMemory]:
        """Synchronous property for non-async access (returns None if not initialized)."""
        return self._semantic

    async def get_semantic(self) -> Optional[SemanticMemory]:
        """Async method to get or initialize semantic memory."""
        if self._semantic is None:
            client = await self.get_chroma_client()
            if client is not None:
                import asyncio
                self._semantic = await asyncio.to_thread(
                    lambda: SemanticMemory(client, "fraud_policies")
                )
        return self._semantic

    def start_task(self, task_data: Dict[str, Any]):
        """Start a new task with fresh short-term memory."""
        self.short_term.start_task(task_data)

    def complete_task(self, outcome: Dict[str, Any], store: bool = True):
        """Complete task and optionally store to long-term memory."""
        if store and self._should_store(outcome):
            episode_id = str(uuid4())

            # Combine short-term memory into episode
            episode = {
                "task": self.short_term.current_task,
                "reasoning_steps": self.short_term.reasoning_steps,
                "tool_calls": self.short_term.tool_calls,
                "outcome": outcome,
                "completed_at": time.time(),
            }

            priority = self._determine_priority(outcome)

            # Check for duplicates
            if not self._is_duplicate(episode):
                self.episodic.store_episode(
                    episode_id=episode_id,
                    content=episode,
                    metadata={
                        "fraud_detected": outcome.get("is_fraud", False),
                        "confidence": outcome.get("confidence", 0.0),
                        "amount": outcome.get("amount", 0.0),
                    },
                    priority=priority,
                )

        # Clear short-term memory
        self.short_term.clear()

    def retrieve_relevant_memories(
        self,
        query: str,
        memory_types: Optional[List[MemoryType]] = None,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Retrieve relevant memories across systems."""
        results = {}

        memory_types = memory_types or [MemoryType.EPISODIC, MemoryType.SEMANTIC]

        if MemoryType.EPISODIC in memory_types:
            results["episodic"] = self.episodic.retrieve_similar(
                query=query,
                n_results=self.retrieval_k,
                min_similarity=self.relevance_threshold,
            )

        if MemoryType.SEMANTIC in memory_types:
            results["semantic"] = self.semantic.retrieve_knowledge(
                query=query,
                n_results=self.retrieval_k,
            )

        # Apply decay to episodic memories
        if "episodic" in results:
            results["episodic"] = self._apply_decay(results["episodic"])

        return results

    def get_memory_stats(self) -> Dict[str, Any]:
        """Get statistics for all memory systems."""
        stats = {
            "short_term": self.short_term.get_summary(),
            "working": self.working.get_stats(),
            "procedural": {
                "procedures": len(self.procedural.procedures),
                "tool_patterns": len(self.procedural.tool_patterns),
                "successful_chains": len(self.procedural.successful_chains),
            },
            "chroma_available": self._chroma_available if self._chroma_available is not None else False,
        }

        # Add episodic stats if available
        if self.episodic is not None:
            try:
                stats["episodic"] = {
                    "count": self.episodic.count(),
                    "buffer_size": len(self.episodic.write_buffer),
                }
            except Exception as e:
                stats["episodic"] = {"error": str(e)}
        else:
            stats["episodic"] = {"status": "ChromaDB not available"}

        # Add semantic stats if available
        if self.semantic is not None:
            try:
                stats["semantic"] = {
                    "count": self.semantic.collection.count(),
                }
            except Exception as e:
                stats["semantic"] = {"error": str(e)}
        else:
            stats["semantic"] = {"status": "ChromaDB not available"}

        return stats

    def _should_store(self, outcome: Dict[str, Any]) -> bool:
        """Determine if outcome should be stored."""
        confidence = outcome.get("confidence", 0.0)
        return confidence >= self.high_confidence_threshold

    def _determine_priority(self, outcome: Dict[str, Any]) -> MemoryPriority:
        """Determine storage priority."""
        if outcome.get("is_fraud") and outcome.get("confidence", 0) > 0.9:
            return MemoryPriority.CRITICAL
        elif outcome.get("confidence", 0) > 0.8:
            return MemoryPriority.HIGH
        elif outcome.get("human_feedback"):
            return MemoryPriority.HIGH
        else:
            return MemoryPriority.MEDIUM

    def _is_duplicate(self, episode: Dict[str, Any]) -> bool:
        """Check if episode is duplicate of recent memory."""
        # Simple deduplication based on outcome similarity
        recent = self.episodic.get_recent_episodes(n=10, hours=1)

        for past_episode in recent:
            # Compare outcomes
            similarity = self._calculate_similarity(
                episode.get("outcome", {}),
                past_episode["content"].get("outcome", {})
            )

            if similarity >= self.deduplication_threshold:
                return True

        return False

    def _calculate_similarity(self, obj1: Dict, obj2: Dict) -> float:
        """Calculate similarity between two objects."""
        # Simple Jaccard similarity
        keys1 = set(obj1.keys())
        keys2 = set(obj2.keys())

        if not keys1 and not keys2:
            return 1.0

        intersection = keys1 & keys2
        union = keys1 | keys2

        return len(intersection) / len(union) if union else 0.0

    def _apply_decay(self, memories: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply time-based decay to memory relevance."""
        current_time = time.time()

        for memory in memories:
            timestamp = memory.get("metadata", {}).get("timestamp", current_time)
            age_days = (current_time - timestamp) / 86400  # Convert to days

            # Apply exponential decay
            decay = self.decay_factor ** age_days
            original_similarity = memory.get("similarity", 1.0)
            memory["similarity"] = original_similarity * decay

        # Re-sort by decayed similarity
        return sorted(memories, key=lambda x: x.get("similarity", 0), reverse=True)


# Pydantic models for API
class MemoryQuery(BaseModel):
    """Memory query model."""
    query: str = Field(..., description="Query text for memory retrieval")
    memory_types: List[str] = Field(
        default=["episodic", "semantic"],
        description="Types of memory to search"
    )
    n_results: int = Field(default=5, ge=1, le=20, description="Number of results")
    min_similarity: float = Field(default=0.7, ge=0.0, le=1.0, description="Minimum similarity")


class MemoryStoreRequest(BaseModel):
    """Memory storage request."""
    content: Dict[str, Any] = Field(..., description="Content to store")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Optional metadata")
    category: Optional[str] = Field(None, description="Category for semantic memory")
    priority: str = Field(default="medium", description="Storage priority")


class MemoryResponse(BaseModel):
    """Memory response model."""
    memories: Dict[str, List[Dict[str, Any]]] = Field(..., description="Retrieved memories")
    stats: Dict[str, Any] = Field(..., description="Memory statistics")
