"""
Memory Systems API Endpoints

Provides REST API for:
- Memory storage (episodic, semantic)
- Memory retrieval (hybrid search)
- Memory statistics
- Memory management (clear, archive)
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.core.hybrid_search import MemoryRetriever
from app.core.memory_systems import (
    MemoryManager,
    MemoryPriority,
    MemoryQuery,
    MemoryResponse,
    MemoryStoreRequest,
    MemoryType,
)

router = APIRouter(prefix="/api/v1/memory", tags=["memory"])

# Global memory manager instance
memory_manager: Optional[MemoryManager] = None
memory_retriever: Optional[MemoryRetriever] = None


def get_memory_manager() -> MemoryManager:
    """Get or create memory manager instance."""
    global memory_manager
    if memory_manager is None:
        # Let MemoryManager read from environment variables
        memory_manager = MemoryManager()
    return memory_manager


def get_memory_retriever() -> MemoryRetriever:
    """Get or create memory retriever instance."""
    global memory_retriever
    if memory_retriever is None:
        manager = get_memory_manager()
        memory_retriever = MemoryRetriever(manager)
    return memory_retriever


# Request/Response Models
class TaskStartRequest(BaseModel):
    """Request to start a new task."""
    transaction_id: str = Field(..., description="Transaction ID")
    transaction_data: Dict[str, Any] = Field(..., description="Transaction data")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")


class TaskCompleteRequest(BaseModel):
    """Request to complete a task."""
    outcome: Dict[str, Any] = Field(..., description="Task outcome")
    store_memory: bool = Field(default=True, description="Store to long-term memory")


class EpisodicMemoryRequest(BaseModel):
    """Request to store episodic memory."""
    episode_id: str = Field(..., description="Episode ID")
    content: Dict[str, Any] = Field(..., description="Episode content")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Metadata")
    priority: str = Field(default="medium", description="Priority level")


class SemanticMemoryRequest(BaseModel):
    """Request to store semantic memory."""
    knowledge_id: str = Field(..., description="Knowledge ID")
    content: str = Field(..., description="Knowledge content")
    category: str = Field(..., description="Knowledge category")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Metadata")


class HybridSearchRequest(BaseModel):
    """Request for hybrid search."""
    query: str = Field(..., description="Search query")
    collection: str = Field(default="episodic", description="Collection to search")
    n_results: int = Field(default=5, ge=1, le=20, description="Number of results")
    min_similarity: float = Field(default=0.7, ge=0.0, le=1.0, description="Minimum similarity")
    use_hybrid: bool = Field(default=True, description="Use hybrid search")


class ContextualSearchRequest(BaseModel):
    """Request for contextual search."""
    query: str = Field(..., description="Search query")
    context: Dict[str, Any] = Field(..., description="Search context")
    n_results: int = Field(default=5, ge=1, le=20, description="Number of results")


class ProceduralMemoryRequest(BaseModel):
    """Request to record procedural memory."""
    procedure_name: str = Field(..., description="Procedure name")
    steps: List[str] = Field(..., description="Procedure steps")
    success_rate: float = Field(..., ge=0.0, le=1.0, description="Success rate")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Metadata")


class ReasoningChainRequest(BaseModel):
    """Request to record reasoning chain."""
    chain: List[str] = Field(..., description="Reasoning steps")
    outcome: str = Field(..., description="Chain outcome")
    success: bool = Field(..., description="Whether successful")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")


# Endpoints
@router.post("/task/start", status_code=status.HTTP_200_OK)
async def start_task(request: TaskStartRequest) -> Dict[str, Any]:
    """
    Start a new task with fresh short-term memory.

    This initializes the short-term memory context for analyzing a transaction.
    """
    try:
        manager = get_memory_manager()

        task_data = {
            "transaction_id": request.transaction_id,
            **request.transaction_data,
            **(request.context or {}),
        }

        manager.start_task(task_data)

        return {
            "status": "success",
            "message": f"Task started for transaction {request.transaction_id}",
            "task_id": manager.short_term.current_task["id"],
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start task: {str(e)}",
        )


@router.post("/task/complete", status_code=status.HTTP_200_OK)
async def complete_task(request: TaskCompleteRequest) -> Dict[str, Any]:
    """
    Complete current task and optionally store to long-term memory.

    High-confidence decisions are automatically stored to episodic memory.
    """
    try:
        import asyncio

        manager = get_memory_manager()

        # Use async method to get episodic memory
        episodic = await manager.get_episodic()
        if episodic is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="ChromaDB service is not available. Cannot access episodic memory.",
            )

        manager.complete_task(
            outcome=request.outcome,
            store=request.store_memory,
        )

        # Flush episodic memory buffer
        await asyncio.to_thread(episodic.flush)

        return {
            "status": "success",
            "message": "Task completed",
            "stored": request.store_memory,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to complete task: {str(e)}",
        )


@router.post("/reasoning/step", status_code=status.HTTP_200_OK)
async def add_reasoning_step(step: Dict[str, Any]) -> Dict[str, Any]:
    """
    Add a reasoning step to current short-term memory.

    Tracks the agent's reasoning process for later review.
    """
    try:
        manager = get_memory_manager()
        manager.short_term.add_reasoning_step(step)

        return {
            "status": "success",
            "message": "Reasoning step added",
            "total_steps": len(manager.short_term.reasoning_steps),
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add reasoning step: {str(e)}",
        )


@router.post("/tool/call", status_code=status.HTTP_200_OK)
async def record_tool_call(
    tool_name: str,
    args: Dict[str, Any],
    result: Any,
) -> Dict[str, Any]:
    """
    Record a tool call in short-term memory.

    Tracks tool usage for analysis and debugging.
    """
    try:
        manager = get_memory_manager()
        manager.short_term.add_tool_call(tool_name, args, result)

        return {
            "status": "success",
            "message": "Tool call recorded",
            "total_calls": len(manager.short_term.tool_calls),
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to record tool call: {str(e)}",
        )


@router.post("/episodic/store", status_code=status.HTTP_201_CREATED)
async def store_episodic_memory(request: EpisodicMemoryRequest) -> Dict[str, Any]:
    """
    Store episode in long-term episodic memory.

    Useful for manually storing important fraud cases or decisions.
    """
    try:
        import asyncio

        manager = get_memory_manager()

        # Use async method to get episodic memory
        episodic = await manager.get_episodic()
        if episodic is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Episodic memory (ChromaDB) is not available",
            )

        priority = MemoryPriority(request.priority.lower())

        # Run ChromaDB operations in thread pool
        await asyncio.to_thread(
            episodic.store_episode,
            episode_id=request.episode_id,
            content=request.content,
            metadata=request.metadata,
            priority=priority,
        )

        # Flush immediately for manual storage
        await asyncio.to_thread(episodic.flush)

        return {
            "status": "success",
            "message": f"Episode {request.episode_id} stored",
            "priority": priority.value,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to store episode: {str(e)}",
        )


@router.post("/semantic/store", status_code=status.HTTP_201_CREATED)
async def store_semantic_memory(request: SemanticMemoryRequest) -> Dict[str, Any]:
    """
    Store knowledge in semantic memory.

    Used for fraud policies, rules, and domain knowledge.
    """
    try:
        import asyncio

        manager = get_memory_manager()

        # Use async method to get semantic memory
        semantic = await manager.get_semantic()
        if semantic is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="ChromaDB service is not available. Cannot access semantic memory.",
            )

        # Run ChromaDB operations in thread pool
        await asyncio.to_thread(
            semantic.store_knowledge,
            knowledge_id=request.knowledge_id,
            content=request.content,
            category=request.category,
            metadata=request.metadata,
        )

        return {
            "status": "success",
            "message": f"Knowledge {request.knowledge_id} stored in category {request.category}",
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to store knowledge: {str(e)}",
        )


@router.post("/retrieve", status_code=status.HTTP_200_OK)
async def retrieve_memories(query: MemoryQuery) -> MemoryResponse:
    """
    Retrieve relevant memories across systems.

    Uses vector similarity and memory decay for optimal retrieval.
    """
    try:
        manager = get_memory_manager()

        # Convert string memory types to enum
        memory_types = [MemoryType(mt) for mt in query.memory_types]

        # Update retrieval parameters
        manager.retrieval_k = query.n_results
        manager.relevance_threshold = query.min_similarity

        # Retrieve memories
        memories = manager.retrieve_relevant_memories(
            query=query.query,
            memory_types=memory_types,
        )

        # Get stats
        stats = manager.get_memory_stats()

        return MemoryResponse(memories=memories, stats=stats)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve memories: {str(e)}",
        )


@router.post("/search/hybrid", status_code=status.HTTP_200_OK)
async def hybrid_search(request: HybridSearchRequest) -> Dict[str, Any]:
    """
    Perform hybrid search (BM25 + vector similarity).

    Combines keyword matching with semantic similarity for best results.
    """
    try:
        retriever = get_memory_retriever()

        if request.use_hybrid:
            results = retriever.retrieve_with_hybrid_search(
                query=request.query,
                collection_name=request.collection,
                n_results=request.n_results,
                min_similarity=request.min_similarity,
            )
        else:
            # Fall back to vector search only
            import asyncio

            manager = get_memory_manager()
            if request.collection == "episodic":
                episodic = await manager.get_episodic()
                if episodic is None:
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail="ChromaDB service is not available. Cannot access episodic memory.",
                    )
                results = await asyncio.to_thread(
                    episodic.retrieve_similar,
                    query=request.query,
                    n_results=request.n_results,
                    min_similarity=request.min_similarity,
                )
            else:
                semantic = await manager.get_semantic()
                if semantic is None:
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail="ChromaDB service is not available. Cannot access semantic memory.",
                    )
                results = await asyncio.to_thread(
                    semantic.retrieve_knowledge,
                    query=request.query,
                    n_results=request.n_results,
                )

        return {
            "query": request.query,
            "collection": request.collection,
            "results": results,
            "count": len(results),
            "hybrid_search": request.use_hybrid,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to perform hybrid search: {str(e)}",
        )


@router.post("/search/contextual", status_code=status.HTTP_200_OK)
async def contextual_search(request: ContextualSearchRequest) -> Dict[str, Any]:
    """
    Retrieve memories with context awareness.

    Filters by transaction type, amount range, time, etc.
    """
    try:
        retriever = get_memory_retriever()

        results = retriever.retrieve_contextual(
            query=request.query,
            context=request.context,
            n_results=request.n_results,
        )

        return {
            "query": request.query,
            "context": request.context,
            "results": results,
            "episodic_count": len(results.get("episodic", [])),
            "semantic_count": len(results.get("semantic", [])),
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to perform contextual search: {str(e)}",
        )


@router.post("/procedural/record", status_code=status.HTTP_201_CREATED)
async def record_procedure(request: ProceduralMemoryRequest) -> Dict[str, Any]:
    """
    Record a procedure in procedural memory.

    Stores successful analysis procedures for reuse.
    """
    try:
        manager = get_memory_manager()

        manager.procedural.record_procedure(
            procedure_name=request.procedure_name,
            steps=request.steps,
            success_rate=request.success_rate,
            metadata=request.metadata,
        )

        return {
            "status": "success",
            "message": f"Procedure {request.procedure_name} recorded",
            "success_rate": request.success_rate,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to record procedure: {str(e)}",
        )


@router.post("/procedural/chain", status_code=status.HTTP_201_CREATED)
async def record_reasoning_chain(request: ReasoningChainRequest) -> Dict[str, Any]:
    """
    Record a successful reasoning chain.

    Stores effective reasoning patterns for future use.
    """
    try:
        manager = get_memory_manager()

        manager.procedural.record_reasoning_chain(
            chain=request.chain,
            outcome=request.outcome,
            success=request.success,
            confidence=request.confidence,
        )

        return {
            "status": "success",
            "message": "Reasoning chain recorded",
            "success": request.success,
            "confidence": request.confidence,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to record reasoning chain: {str(e)}",
        )


@router.get("/stats", status_code=status.HTTP_200_OK)
async def get_memory_stats() -> Dict[str, Any]:
    """
    Get comprehensive memory statistics.

    Returns stats for all memory systems: short-term, working, episodic, semantic, procedural.
    """
    try:
        manager = get_memory_manager()
        stats = manager.get_memory_stats()

        # Add retrieval stats
        retriever = get_memory_retriever()
        stats["retrieval"] = retriever.get_retrieval_stats()

        return {
            "status": "success",
            "stats": stats,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get memory stats: {str(e)}",
        )


@router.get("/short-term", status_code=status.HTTP_200_OK)
async def get_short_term_memory() -> Dict[str, Any]:
    """
    Get current short-term memory contents.

    Shows current task, reasoning steps, and tool calls.
    """
    try:
        manager = get_memory_manager()
        summary = manager.short_term.get_summary()

        return {
            "status": "success",
            "short_term_memory": summary,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get short-term memory: {str(e)}",
        )


@router.get("/working/stats", status_code=status.HTTP_200_OK)
async def get_working_memory_stats() -> Dict[str, Any]:
    """
    Get working memory cache statistics.

    Shows cache hit rate, size, evictions, etc.
    """
    try:
        manager = get_memory_manager()
        stats = manager.working.get_stats()

        return {
            "status": "success",
            "working_memory": stats,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get working memory stats: {str(e)}",
        )


@router.post("/working/put", status_code=status.HTTP_200_OK)
async def put_working_memory(key: str, value: Any, metadata: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Store item in working memory cache.

    Useful for caching frequently accessed data.
    """
    try:
        manager = get_memory_manager()
        manager.working.put(key, value, metadata)

        return {
            "status": "success",
            "message": f"Item {key} stored in working memory",
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to store in working memory: {str(e)}",
        )


@router.get("/working/get/{key}", status_code=status.HTTP_200_OK)
async def get_working_memory(key: str) -> Dict[str, Any]:
    """
    Retrieve item from working memory cache.
    """
    try:
        manager = get_memory_manager()
        value = manager.working.get(key)

        if value is None:
            return {
                "status": "miss",
                "message": f"Key {key} not found in working memory",
                "value": None,
            }

        return {
            "status": "hit",
            "key": key,
            "value": value,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get from working memory: {str(e)}",
        )


@router.delete("/clear", status_code=status.HTTP_200_OK)
async def clear_short_term_memory() -> Dict[str, Any]:
    """
    Clear short-term memory.

    Use when starting fresh or after error.
    """
    try:
        manager = get_memory_manager()
        manager.short_term.clear()

        return {
            "status": "success",
            "message": "Short-term memory cleared",
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear short-term memory: {str(e)}",
        )


@router.delete("/working/clear", status_code=status.HTTP_200_OK)
async def clear_working_memory() -> Dict[str, Any]:
    """
    Clear working memory cache.
    """
    try:
        manager = get_memory_manager()
        manager.working.clear()

        return {
            "status": "success",
            "message": "Working memory cleared",
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear working memory: {str(e)}",
        )


@router.post("/index/build", status_code=status.HTTP_200_OK)
async def build_search_index(collection: str) -> Dict[str, Any]:
    """
    Build BM25 search index for a collection.

    Required before using hybrid search on a collection.
    """
    try:
        retriever = get_memory_retriever()
        retriever.build_index(collection)

        return {
            "status": "success",
            "message": f"Search index built for {collection}",
            "collection": collection,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to build index: {str(e)}",
        )
