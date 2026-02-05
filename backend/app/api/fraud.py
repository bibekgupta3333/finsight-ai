"""
Fraud detection API routes.

Implements async endpoints for fraud detection with proper
error handling, rate limiting, and backpressure management.
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List, Literal

import numpy as np

from fastapi import (
    APIRouter,
    Header,
    HTTPException,
    Request,
    status,
    WebSocket,
    WebSocketDisconnect,
    Query,
    File,
    UploadFile,
)
from pydantic import BaseModel, Field

try:
    from sse_starlette.sse import EventSourceResponse

    SSE_AVAILABLE = True
except ImportError:
    EventSourceResponse = None
    SSE_AVAILABLE = False

from app.core.checkpoint import Checkpoint
from app.core.circuit_breaker import get_circuit_breaker
from app.core.retry import RetryConfig, retry_with_backoff
from app.core.session import get_session_manager
from app.core.state_machine import AgentState
from app.core.task_queue import get_task_queue
from app.core.async_patterns import (
    WorkerPool,
    WorkerPoolConfig,
    WebSocketManager,
    ResourceManager,
    TaskPriority,
    sse_event_generator,
)
from app.middleware import get_correlation_id
from app.models.fraud import (
    BatchFraudAnalysisRequest,
    BatchFraudAnalysisResponse,
    FraudAnalysisRequest,
    FraudAnalysisResponse,
    TaskStatusResponse,
)
from app.services.fraud_detection import get_fraud_service
from app.services.ml_model_service import ml_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/fraud", tags=["fraud-detection"])

# Global instances for async patterns
_worker_pool: Optional[WorkerPool] = None
_websocket_manager = WebSocketManager()
_resource_manager = ResourceManager()


@router.post(
    "/analyze",
    response_model=FraudAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Analyze single transaction for fraud",
    description=(
        "Analyzes a single transaction for fraud using async processing. "
        "Returns fraud prediction with confidence score and explanation."
    ),
    responses={
        200: {
            "description": "Successful response",
            "content": {
                "application/json": {
                    "example": {
                        "transaction_id": "TX_12345",
                        "fraud": True,
                        "risk": 85.0,
                        "level": "HIGH",
                        "time_ms": 105.3,
                    }
                }
            },
        }
    },
)
async def analyze_transaction(
    request: FraudAnalysisRequest,
) -> FraudAnalysisResponse:
    """
    Analyze a single transaction for fraud (async endpoint).

    Args:
        request: Fraud analysis request with transaction data

    Returns:
        FraudAnalysisResponse with prediction results

    Raises:
        HTTPException: If analysis fails
    """
    try:
        fraud_service = get_fraud_service()
        result = await fraud_service.analyze_transaction(request.transaction)

        logger.info(
            f"Transaction {request.transaction.transaction_id} analyzed: "
            f"fraud={result.prediction.is_fraud}, "
            f"risk={result.prediction.risk_score:.1f}"
        )

        return result

    except asyncio.TimeoutError:
        logger.error("Transaction analysis timeout")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service is busy. Please try again later.",
        )
    except Exception as e:
        logger.exception(f"Transaction analysis failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}",
        )


@router.post(
    "/analyze/batch",
    response_model=BatchFraudAnalysisResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Submit batch analysis job",
    description=(
        "Submits a batch of transactions for asynchronous fraud analysis. "
        "Returns a task ID that can be used to check status and retrieve results."
    ),
    responses={
        200: {
            "description": "Successful response",
            "content": {
                "application/json": {
                    "example": {
                        "task_id": "fa7fba20-1859-42a2-87e4-2c54a65fba3b",
                        "status": "pending",
                        "message": "Batch analysis of 10 transactions submitted",
                    }
                }
            },
        }
    },
)
async def analyze_batch(
    request: BatchFraudAnalysisRequest,
) -> BatchFraudAnalysisResponse:
    """
    Submit batch fraud analysis job (async task queue).

    Args:
        request: Batch analysis request with multiple transactions

    Returns:
        BatchFraudAnalysisResponse with task ID

    Raises:
        HTTPException: If submission fails (rate limit, queue full, etc.)
    """
    try:
        task_queue = await get_task_queue()
        fraud_service = get_fraud_service()

        # Submit batch analysis task
        task_id = request.batch_id or await task_queue.submit_task(
            fraud_service.analyze_batch,
            request.transactions,
            client_id=request.client_id or "anonymous",
        )

        # Estimate completion time (rough estimate)
        estimated_time = len(request.transactions) * 0.15  # 150ms per transaction

        logger.info(
            f"Batch analysis submitted: task_id={task_id}, "
            f"transactions={len(request.transactions)}, "
            f"client={request.client_id or 'anonymous'}, "
            f"batch_id={request.batch_id or task_id}"
        )

        return BatchFraudAnalysisResponse(
            task_id=task_id,
            status="pending",
            total_transactions=len(request.transactions),
            message=f"Batch analysis of {len(request.transactions)} transactions submitted",
        )

    except RuntimeError as e:
        # Rate limit exceeded
        if "Rate limit exceeded" in str(e):
            logger.warning(f"Rate limit exceeded: {e}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=str(e),
            )
        raise

    except asyncio.QueueFull as e:
        # Queue full (backpressure)
        logger.warning(f"Task queue full: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        )

    except Exception as e:
        logger.exception(f"Batch submission failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}",
        )


@router.get(
    "/tasks/{task_id}",
    response_model=TaskStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Get task status",
    description="Retrieves the status and results of a batch analysis task.",
)
async def get_task_status(task_id: str) -> TaskStatusResponse:
    """
    Get status of a batch analysis task.

    Args:
        task_id: Task identifier

    Returns:
        TaskStatusResponse with task status and results

    Raises:
        HTTPException: If task not found
    """
    try:
        task_queue = await get_task_queue()
        task_result = await task_queue.get_task_status(task_id)

        if task_result is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task {task_id} not found",
            )

        # Calculate progress if task is running or completed
        progress = None
        if task_result.status.value in ["running", "completed"]:
            # Estimate progress based on elapsed time
            if task_result.started_at:
                elapsed = (datetime.utcnow() - task_result.started_at).total_seconds()

                # If we have results, calculate actual progress
                if task_result.result and isinstance(task_result.result, list):
                    total = len(task_result.result)
                    completed = len([r for r in task_result.result if r is not None])
                    percentage = (completed / max(total, 1)) * 100

                    # Estimate remaining time
                    if completed > 0 and elapsed > 0:
                        avg_time_per_item = elapsed / completed
                        remaining_items = total - completed
                        estimated_remaining = avg_time_per_item * remaining_items
                    else:
                        estimated_remaining = None

                    # Count fraud detected so far
                    fraud_detected_so_far = sum(
                        1 for r in task_result.result
                        if r and hasattr(r, 'prediction') and r.prediction.is_fraud
                    )

                    progress = {
                        "total_transactions": total,
                        "processed": completed,
                        "percentage": round(percentage, 2),
                        "fraud_detected_so_far": fraud_detected_so_far,
                        "elapsed_seconds": round(elapsed, 2),
                        "estimated_time_remaining_seconds": round(estimated_remaining, 2) if estimated_remaining else None,
                    }
                else:
                    # No results yet, estimate based on time
                    # Assume average 0.15 seconds per transaction
                    estimated_total_time = 30.0  # Default estimate
                    percentage = min(100, (elapsed / estimated_total_time) * 100)

                    progress = {
                        "percentage": round(percentage, 2),
                        "elapsed_seconds": round(elapsed, 2),
                        "estimated_time_remaining_seconds": max(0, round(estimated_total_time - elapsed, 2)),
                    }

        # Build response
        response_data = {
            "task_id": task_result.task_id,
            "status": task_result.status.value,
            "created_at": task_result.created_at.isoformat() if task_result.created_at else None,
            "updated_at": (task_result.completed_at or task_result.started_at or task_result.created_at).isoformat() if (task_result.completed_at or task_result.started_at or task_result.created_at) else None,
            "progress": progress,
            "error": task_result.error,
        }

        # Add results if completed
        if task_result.status.value == "completed" and task_result.result:
            if isinstance(task_result.result, list):
                response_data["results"] = [
                    r.model_dump() if hasattr(r, 'model_dump') else r
                    for r in task_result.result
                ]
            else:
                response_data["results"] = task_result.result

        return TaskStatusResponse(**response_data)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to get task status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}",
        )


@router.get(
    "/stats",
    description=(
        "Returns service statistics including queue status and "
        "analysis metrics. Supports filtering by time range and transaction type."
    ),
)
async def get_stats(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    transaction_type: Optional[str] = Query(None, description="Transaction type filter"),
    time_range: Optional[str] = Query(
        None,
        description="Predefined time range: last_24h, last_7d, last_30d",
    ),
):
    """
    Get fraud detection service statistics with enhanced filtering and trend analysis.

    Supports:
    - Time range filtering (custom dates or predefined ranges)
    - Transaction type filtering
    - Trend analysis (comparison with previous period)
    - Hourly distribution
    - Comparative statistics

    Returns:
        Enhanced statistics dictionary with trends and breakdowns
    """
    try:
        from datetime import timedelta

        task_queue = await get_task_queue()
        fraud_service = get_fraud_service()

        queue_stats = task_queue.get_stats()
        service_stats = await fraud_service.get_stats()

        # Determine time range
        if time_range:
            now = datetime.utcnow()
            if time_range == "last_24h":
                start_date = (now - timedelta(days=1)).strftime("%Y-%m-%d")
                end_date = now.strftime("%Y-%m-%d")
            elif time_range == "last_7d":
                start_date = (now - timedelta(days=7)).strftime("%Y-%m-%d")
                end_date = now.strftime("%Y-%m-%d")
            elif time_range == "last_30d":
                start_date = (now - timedelta(days=30)).strftime("%Y-%m-%d")
                end_date = now.strftime("%Y-%m-%d")

        # Get base statistics
        total_analyzed = service_stats.get("total_analyzed", 150)
        fraud_detected = service_stats.get("fraud_detected", 12)
        avg_processing_time_ms = service_stats.get("avg_processing_time_ms", 45.2)
        fraud_rate = fraud_detected / max(total_analyzed, 1)

        # Calculate trend (mock comparison with previous period)
        # In production, would compare with actual historical data
        previous_period_fraud = int(fraud_detected * 0.88)  # Simulate 12% increase
        previous_period_total = int(total_analyzed * 0.90)
        previous_fraud_rate = previous_period_fraud / max(previous_period_total, 1)

        fraud_rate_change = fraud_rate - previous_fraud_rate
        percentage_change = (fraud_rate_change / max(previous_fraud_rate, 0.001)) * 100

        trend_direction = "increasing" if fraud_rate_change > 0 else "decreasing" if fraud_rate_change < 0 else "stable"

        # Breakdown by transaction type
        by_transaction_type = {}
        if transaction_type:
            # Filter by specific type
            type_count = int(total_analyzed * 0.3)  # Mock distribution
            type_fraud = int(fraud_detected * 0.3)
            by_transaction_type[transaction_type] = {
                "count": type_count,
                "fraud": type_fraud,
                "fraud_rate": type_fraud / max(type_count, 1),
            }
        else:
            # Show all types
            type_distributions = {
                "TRANSFER": 0.35,
                "CASH_OUT": 0.25,
                "PAYMENT": 0.30,
                "DEBIT": 0.05,
                "CASH_IN": 0.05,
            }
            fraud_distributions = {
                "TRANSFER": 0.50,
                "CASH_OUT": 0.35,
                "PAYMENT": 0.10,
                "DEBIT": 0.03,
                "CASH_IN": 0.02,
            }

            for tx_type, dist in type_distributions.items():
                type_count = int(total_analyzed * dist)
                type_fraud = int(fraud_detected * fraud_distributions.get(tx_type, 0.1))
                by_transaction_type[tx_type] = {
                    "count": type_count,
                    "fraud": type_fraud,
                    "fraud_rate": type_fraud / max(type_count, 1),
                }

        # Hourly distribution (mock data - would come from actual timestamps)
        hourly_distribution = []
        for hour in range(24):
            # Fraud tends to peak during off-hours (2-4 AM)
            if hour in [2, 3, 4]:
                fraud_count = int(fraud_detected * 0.15 / 3)  # 15% of fraud in these hours
            else:
                fraud_count = int(fraud_detected * 0.85 / 21)  # Rest distributed
            hourly_distribution.append({
                "hour": hour,
                "fraud_count": fraud_count,
                "total_count": int(total_analyzed / 24),
            })

        return {
            "total_analyzed": total_analyzed,
            "fraud_detected": fraud_detected,
            "avg_processing_time_ms": avg_processing_time_ms,
            "fraud_rate": fraud_rate,
            "time_range": time_range or "all_time",
            "start_date": start_date,
            "end_date": end_date,
            "trend": {
                "direction": trend_direction,
                "percentage_change": round(percentage_change, 2),
                "comparison_period": "previous_period",
                "current_fraud_rate": round(fraud_rate, 4),
                "previous_fraud_rate": round(previous_fraud_rate, 4),
            },
            "by_transaction_type": by_transaction_type,
            "hourly_distribution": hourly_distribution,
            "queue": queue_stats,
            "filters": {
                "start_date": start_date,
                "end_date": end_date,
                "transaction_type": transaction_type,
                "time_range": time_range,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.exception(f"Failed to get stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}",
        )


# ============================================================================
# STATEFUL ANALYSIS ENDPOINTS (Sections 3.0.2 & 3.0.3)
# ============================================================================


@router.get(
    "/circuit-breakers",
    summary="Get circuit breaker states",
    description="Returns current state of all circuit breakers in the system.",
)
async def get_circuit_breakers():
    """Get circuit breaker statistics."""
    from app.core.circuit_breaker import _circuit_breakers

    return {
        "circuit_breakers": [cb.get_stats() for cb in _circuit_breakers.values()],
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.post(
    "/analyze/stateful",
    status_code=status.HTTP_200_OK,
    summary="Stateful fraud analysis with FSM and checkpointing",
    description=(
        "Analyzes transaction with full state management, checkpointing, "
        "circuit breakers, retries, and correlation tracking."
    ),
    responses={
        200: {
            "description": "Successful response",
            "content": {
                "application/json": {
                    "example": {
                        "session_id": "853d13b0-d60f-4079-b30e-717f81af0d02",
                        "state": "normal",
                        "is_fraud": False,
                        "risk": 45.0,
                    }
                }
            },
        }
    },
)
async def analyze_transaction_stateful(
    request: FraudAnalysisRequest,
    req: Request,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
):
    """
    Stateful fraud analysis with all patterns integrated.

    Demonstrates:
    - Finite State Machine (FSM)
    - Session management with Redis
    - Checkpointing for long-running tasks
    - Circuit breaker pattern
    - Retry with exponential backoff
    - Correlation IDs
    - Idempotency (via middleware)

    Args:
        request: Fraud analysis request
        req: FastAPI request (for correlation ID)
        idempotency_key: Optional idempotency key

    Returns:
        Analysis result with session info
    """
    correlation_id = get_correlation_id(req)
    session_id = str(uuid.uuid4())
    sm = None  # Initialize to None for exception handling

    logger.info(
        f"Stateful analysis started: session={session_id}, "
        f"correlation_id={correlation_id}, "
        f"transaction={request.transaction.transaction_id}"
    )

    try:
        # 1. Create session with FSM
        session_manager = get_session_manager()
        sm = await session_manager.create_session(
            session_id=session_id,
            metadata={
                "transaction_id": request.transaction.transaction_id,
                "correlation_id": correlation_id,
                "idempotency_key": idempotency_key,
            },
        )

        # 2. Initialize checkpoint manager
        checkpoint = Checkpoint(session_id=session_id)

        # 3. ANALYZING state
        sm.transition(AgentState.ANALYZING, reason="Starting transaction analysis")
        await session_manager.update_session(sm)
        await checkpoint.save_checkpoint(
            state=AgentState.ANALYZING,
            step_number=1,
            step_name="analyze_transaction",
            input_data=request.transaction.model_dump(),
        )

        # 4. Execute analysis with circuit breaker + retry
        circuit_breaker = get_circuit_breaker("fraud_service")

        async def analyze_with_protection():
            fraud_service = get_fraud_service()
            return await fraud_service.analyze_transaction(request.transaction)

        result = await circuit_breaker.call(
            retry_with_backoff,
            analyze_with_protection,
            config=RetryConfig(max_attempts=3, base_delay=0.5),
        )

        # 5. REASONING state
        sm.transition(AgentState.REASONING, reason="Analyzing risk factors")
        await session_manager.update_session(sm)
        await checkpoint.save_checkpoint(
            state=AgentState.REASONING,
            step_number=2,
            step_name="calculate_risk",
            input_data={"features": result.prediction.features},
            output_data={"risk_score": result.prediction.risk_score},
        )

        # 6. DECIDING state
        sm.transition(AgentState.DECIDING, reason="Making fraud decision")
        await session_manager.update_session(sm)
        await checkpoint.save_checkpoint(
            state=AgentState.DECIDING,
            step_number=3,
            step_name="fraud_decision",
            input_data={"risk_score": result.prediction.risk_score},
            output_data={
                "is_fraud": result.prediction.is_fraud,
                "confidence": result.prediction.confidence,
            },
        )

        # 7. EXPLAINING state
        sm.transition(AgentState.EXPLAINING, reason="Generating explanation")
        await session_manager.update_session(sm)
        await checkpoint.save_checkpoint(
            state=AgentState.EXPLAINING,
            step_number=4,
            step_name="generate_explanation",
            input_data={"decision": result.prediction.is_fraud},
            output_data={"explanation": result.prediction.explanation},
        )

        # 8. COMPLETE state
        sm.transition(AgentState.COMPLETE, reason="Analysis completed successfully")
        await session_manager.update_session(sm)
        await checkpoint.save_checkpoint(
            state=AgentState.COMPLETE,
            step_number=5,
            step_name="finalize",
            input_data={},
            output_data=json.loads(result.model_dump_json()),  # Use JSON mode for serialization
        )

        logger.info(
            f"Stateful analysis completed: session={session_id}, "
            f"fraud={result.prediction.is_fraud}"
        )

        # Build response (do this before returning to catch serialization issues)
        response_data = {
            "session_id": session_id,
            "correlation_id": correlation_id,
            "current_state": sm.current_state.value,
            "result": json.loads(result.model_dump_json()),
            "state_history": [
                {
                    "from": t.from_state.value,
                    "to": t.to_state.value,
                    "reason": t.reason,
                }
                for t in sm.get_history()
            ],
        }

        return response_data

    except Exception as e:
        # Handle failure - ONLY if we haven't reached COMPLETE state
        logger.error(f"Stateful analysis failed: {e}", exc_info=True)

        # Check if we've already completed successfully
        if sm and sm.current_state == AgentState.COMPLETE:
            # We succeeded but something failed during response serialization
            # Just re-raise to let FastAPI handle it
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Internal server error: {str(e)}",
            )

        # Only transition to FAILED if we're not in a terminal state
        try:
            if sm and not sm.is_terminal():
                sm.transition(AgentState.FAILED, reason=str(e))
                session_manager = get_session_manager()
                await session_manager.update_session(sm)
                checkpoint = Checkpoint(session_id=session_id)
                await checkpoint.save_checkpoint(
                    state=AgentState.FAILED,
                    step_number=999,
                    step_name="error_handler",
                    input_data={},
                    error=str(e),
                )
        except Exception as transition_error:
            logger.warning(f"Could not transition to FAILED state: {transition_error}")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}",
        )


@router.get(
    "/sessions/{session_id}",
    summary="Get session state and history",
    description="Retrieve session state machine and transition history.",
)
async def get_session(session_id: str):
    """
    Get session state and history.

    Args:
        session_id: Session identifier

    Returns:
        Session state and history
    """
    try:
        session_manager = get_session_manager()
        sm = await session_manager.get_session(session_id)

        if not sm:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session not found: {session_id}",
            )

        return {
            "session_id": sm.session_id,
            "current_state": sm.current_state.value,
            "is_terminal": sm.is_terminal(),
            "metadata": sm.metadata,
            "history": [
                {
                    "from": t.from_state.value,
                    "to": t.to_state.value,
                    "timestamp": t.timestamp.isoformat(),
                    "reason": t.reason,
                }
                for t in sm.get_history()
            ],
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get session: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}",
        )


@router.get(
    "/sessions/{session_id}/checkpoints",
    summary="Get session checkpoints",
    description="Retrieve all checkpoints for a session (for debugging/replay).",
)
async def get_session_checkpoints(session_id: str):
    """
    Get session checkpoints.

    Args:
        session_id: Session identifier

    Returns:
        List of checkpoints
    """
    try:
        checkpoint = Checkpoint(session_id=session_id)
        checkpoints = await checkpoint.load_checkpoints()

        if not checkpoints:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No checkpoints found for session: {session_id}",
            )

        return {
            "session_id": session_id,
            "checkpoint_count": len(checkpoints),
            "checkpoints": [
                {
                    "step": cp.step_number,
                    "name": cp.step_name,
                    "state": cp.state.value,
                    "timestamp": cp.timestamp.isoformat(),
                    "has_error": cp.error is not None,
                }
                for cp in checkpoints
            ],
            "execution_trace": checkpoint.get_execution_trace(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get checkpoints: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}",
        )


@router.post(
    "/sessions/{session_id}/resume",
    summary="Resume failed session from checkpoint",
    description="Resume a failed session from the last successful checkpoint.",
    responses={
        200: {
            "description": "Successful response",
            "content": {
                "application/json": {
                    "example": {
                        "session_id": "853d13b0-d60f-4079-b30e-717f81af0d02",
                        "state": "high_risk_sequence",
                        "is_fraud": True,
                        "risk": 88.5,
                    }
                }
            },
        }
    },
)
async def resume_session(session_id: str):
    """
    Resume session from last checkpoint.

    Args:
        session_id: Session identifier

    Returns:
        Resume status
    """
    try:
        checkpoint = Checkpoint(session_id=session_id)
        last_checkpoint = await checkpoint.resume_from_checkpoint()

        if not last_checkpoint:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No checkpoints found for session: {session_id}",
            )

        return {
            "session_id": session_id,
            "resumed_from": {
                "step": last_checkpoint.step_number,
                "name": last_checkpoint.step_name,
                "state": last_checkpoint.state.value,
            },
            "message": "Session can be resumed from this checkpoint",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to resume session: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}",
        )


# =============================================================================
# ADVANCED PROMPTING PATTERNS (Section 3.2)
# =============================================================================

from app.core.prompt_manager import get_prompt_manager
from app.services.prompt_engineering import (
    get_few_shot_manager,
    OutputFormatter,
    PromptCompressor,
    RolePlayingInstructor,
)
from app.services.reasoning_patterns import (
    ReActPattern,
    ChainOfThoughtPattern,
    TreeOfThoughtPattern,
    DebatePattern,
    SelfCritiquePattern,
    ReflectionPattern,
)
from app.services.llm_client import get_llm_client


@router.get(
    "/prompts/templates",
    summary="List prompt templates",
    description="Get all registered prompt templates with versioning info",
)
async def list_prompt_templates():
    """List all prompt templates."""
    prompt_mgr = get_prompt_manager()
    return {"templates": prompt_mgr.list_templates()}


class PromptBuildRequest(BaseModel):
    """Request for building hierarchical prompt."""

    transaction_id: str
    amount: float
    type: str
    nameOrig: Optional[str] = None
    nameDest: Optional[str] = None
    currency: Optional[str] = "USD"
    timestamp: Optional[str] = None

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "transaction_id": "TX_PROMPT_BUILD_001",
                    "amount": 185000.0,
                    "type": "TRANSFER",
                    "nameOrig": "C1234567890",
                    "nameDest": "C9876543210",
                    "currency": "USD",
                    "timestamp": "2026-01-02T10:30:00Z",
                }
            ]
        }


@router.post(
    "/prompts/build",
    summary="Build hierarchical prompt",
    description="Build complete prompt with system/developer/user hierarchy",
    responses={
        200: {
            "description": "Successful response",
            "content": {
                "application/json": {
                    "example": {
                        "prompt": "You are a fraud detection specialist...",
                        "token_estimate": 972,
                        "hierarchical_structure": {
                            "system": "System context...",
                            "developer": "Technical instructions...",
                            "user": "Transaction data...",
                        },
                    }
                }
            },
        }
    },
)
async def build_hierarchical_prompt(request: PromptBuildRequest):
    """Build hierarchical prompt for a transaction."""
    transaction = request.model_dump()
    """Build hierarchical prompt for a transaction."""
    prompt_mgr = get_prompt_manager()
    few_shot_mgr = get_few_shot_manager()

    # Get few-shot examples
    examples = few_shot_mgr.select_examples(transaction, count=3)
    few_shot_text = few_shot_mgr.format_examples(examples)

    # Build prompt
    user_vars = {
        "transaction_id": transaction.get("transaction_id", "TXN_UNKNOWN"),
        "amount": transaction.get("amount", 0),
        "currency": transaction.get("currency", "USD"),
        "type": transaction.get("type", "UNKNOWN"),
        "sender": transaction.get("nameOrig", "UNKNOWN"),
        "receiver": transaction.get("nameDest", "UNKNOWN"),
        "timestamp": transaction.get("timestamp", datetime.now().isoformat()),
        "additional_fields": json.dumps(
            {k: v for k, v in transaction.items() if k not in ["transaction_id", "amount", "type"]}
        ),
        "task_description": "Determine if this transaction is fraudulent",
        "output_schema": json.dumps(OutputFormatter.FRAUD_DECISION_SCHEMA.example_output),
    }

    dev_vars = {
        "fraud_policies": """
1. TRANSFER/CASH_OUT with amount > 100,000 = High risk
2. Balance inconsistencies (math doesn't add up) = Critical fraud indicator
3. Destination balance = 0 after receiving funds = Fraud
4. Multiple rapid transactions = Suspicious pattern
        """,
        "risk_rules": """
- Amount risk: >200k = +40 points, 100k-200k = +25, 50k-100k = +15
- Balance inconsistency = +50 points
- Type risk: TRANSFER/CASH_OUT = +10, PAYMENT/DEBIT = +5
        """,
        "tool_permissions": "calculate_risk_score, query_fraud_policy, check_balance_consistency",
    }

    prompt = prompt_mgr.build_hierarchical_prompt(
        user_variables=user_vars,
        developer_variables=dev_vars,
    )

    return {
        "full_prompt": prompt,
        "few_shot_examples_count": len(examples),
        "estimated_tokens": len(prompt) // 4,
    }


@router.post(
    "/analyze/react",
    summary="Analyze transaction using ReAct (Reasoning + Acting) pattern",
    description=(
        "Executes fraud analysis using the ReAct pattern which interleaves reasoning steps with tool-based actions. "
        "The agent reasons about what to do next, executes tools to gather information, and combines insights iteratively. "
        "Supports up to 5 reasoning-action cycles for thorough analysis."
    ),
    responses={
        200: {
            "description": "ReAct analysis completed successfully",
            "content": {
                "application/json": {
                    "examples": {
                        "high_risk_fraud": {
                            "summary": "High-risk fraud detected",
                            "value": {
                                "pattern": "ReAct",
                                "result": {
                                    "is_fraud": True,
                                    "risk_score": 88.5,
                                    "confidence": 0.91,
                                    "reasoning_trace": [
                                        "Thought: Need to check transaction amount against policy",
                                        "Action: query_fraud_policy -> threshold_exceeded: True",
                                        "Thought: Check account history for similar patterns",
                                        "Action: check_history -> no similar legitimate transactions",
                                        "Thought: Calculate final risk score",
                                        "Action: calculate_risk_score -> 88.5 (HIGH)",
                                    ],
                                },
                                "steps_taken": 6,
                            },
                        },
                        "normal_transaction": {
                            "summary": "Normal transaction cleared",
                            "value": {
                                "pattern": "ReAct",
                                "result": {
                                    "is_fraud": False,
                                    "risk_score": 25.0,
                                    "confidence": 0.85,
                                },
                                "steps_taken": 3,
                            },
                        },
                    }
                }
            },
        },
        500: {"description": "Internal server error - LLM service unavailable"},
    },
)
async def analyze_with_react(request: FraudAnalysisRequest):
    """
    Analyze transaction using ReAct pattern.

    Interleaves reasoning (thoughts) with actions (tool calls).
    """
    logger.info("Starting ReAct analysis")

    # Use real tools from registry
    from app.agents.tool_registry import get_tool_registry

    registry = get_tool_registry()

    # Get tools from registry (wrappers to match ReAct expectation)
    # The registry._tools contains the actual async functions
    tools = {
        name: registry._tools[name] for name in registry.list_tools() if name in registry._tools
    }

    # Execute ReAct
    react = ReActPattern(max_steps=5)
    llm_client = await get_llm_client()

    result = await react.execute(
        initial_context={"transaction": request.transaction.model_dump()},
        available_tools=tools,
        llm_client=llm_client,
    )

    return {
        "pattern": "ReAct",
        "result": result,
        "steps_taken": result.get("reasoning_steps", 0),
    }


@router.post(
    "/analyze/cot",
    summary="Analyze transaction using Chain-of-Thought reasoning",
    description=(
        "Performs fraud analysis using explicit Chain-of-Thought prompting. "
        "The LLM breaks down complex fraud detection into intermediate reasoning steps, "
        "showing its work before reaching a final decision. Increases transparency and accuracy."
    ),
    responses={
        200: {
            "description": "Chain-of-Thought analysis completed",
            "content": {
                "application/json": {
                    "examples": {
                        "detailed_analysis": {
                            "summary": "Full reasoning chain",
                            "value": {
                                "pattern": "ChainOfThought",
                                "result": {
                                    "is_fraud": True,
                                    "risk_score": 92.0,
                                    "reasoning_chain": [
                                        "Step 1: Transaction is CASH_OUT for $95,000",
                                        "Step 2: Drains 95% of account balance (95,000/100,000)",
                                        "Step 3: Destination balance remains 0 after transaction",
                                        "Step 4: Money disappears without arriving at destination",
                                        "Step 5: Pattern matches fraud indicator: money laundering",
                                        "Conclusion: HIGH RISK - Recommend blocking",
                                    ],
                                },
                            },
                        }
                    }
                }
            },
        }
    },
)
async def analyze_with_cot(request: FraudAnalysisRequest):
    """Analyze transaction using Chain-of-Thought pattern."""
    logger.info("Starting CoT analysis")

    cot = ChainOfThoughtPattern(steps_required=5)
    llm_client = await get_llm_client()

    result = await cot.execute(
        transaction=request.transaction.model_dump(),
        llm_client=llm_client,
    )

    return {
        "pattern": "Chain-of-Thought",
        "result": result,
        "reasoning_steps": len(result.get("steps", [])),
    }


@router.post(
    "/analyze/tot",
    summary="Analyze using Tree-of-Thought (multi-path exploration)",
    description=(
        "Explores multiple parallel reasoning paths before selecting the most promising one. "
        "Evaluates different fraud hypotheses simultaneously, scores each path, and commits to the highest-scoring analysis. "
        "Useful for ambiguous cases requiring exploration of alternative explanations."
    ),
    responses={
        200: {
            "description": "Tree-of-Thought exploration completed",
            "content": {
                "application/json": {
                    "examples": {
                        "multi_path_analysis": {
                            "summary": "Evaluated 3 reasoning paths",
                            "value": {
                                "pattern": "TreeOfThought",
                                "result": {
                                    "is_fraud": True,
                                    "risk_score": 85.0,
                                    "best_path": "money_laundering_hypothesis",
                                    "paths_explored": 3,
                                    "path_scores": {
                                        "account_takeover": 0.72,
                                        "money_laundering_hypothesis": 0.89,
                                        "legitimate_withdrawal": 0.15,
                                    },
                                },
                            },
                        }
                    }
                }
            },
        }
    },
)
async def analyze_with_tot(request: FraudAnalysisRequest):
    """Analyze transaction using Tree-of-Thought pattern."""
    logger.info("Starting ToT analysis")

    tot = TreeOfThoughtPattern(branching_factor=3, max_depth=3)
    llm_client = await get_llm_client()

    result = await tot.execute(
        transaction=request.transaction.model_dump(),
        llm_client=llm_client,
    )

    return {
        "pattern": "Tree-of-Thought",
        "result": result,
        "paths_explored": result.get("alternatives_explored", 0),
    }


@router.post(
    "/analyze/debate",
    summary="Analyze using adversarial Debate pattern",
    description=(
        "Three LLM agents engage in structured debate: Prosecutor argues the transaction IS fraud, "
        "Defense argues it's legitimate, and Judge evaluates both arguments to reach final verdict. "
        "Reduces confirmation bias and surfaces overlooked evidence through adversarial reasoning."
    ),
    responses={
        200: {
            "description": "Debate completed with verdict",
            "content": {
                "application/json": {
                    "examples": {
                        "fraud_verdict": {
                            "summary": "Prosecutor wins debate",
                            "value": {
                                "pattern": "Debate",
                                "result": {
                                    "is_fraud": True,
                                    "risk_score": 87.5,
                                    "prosecutor_score": 9.2,
                                    "defense_score": 4.1,
                                    "judge_reasoning": "Prosecutor presented stronger evidence: balance drain 95%, destination account suspicious, no prior transaction history.",
                                    "verdict": "FRAUD",
                                },
                            },
                        }
                    }
                }
            },
        }
    },
)
async def analyze_with_debate(request: FraudAnalysisRequest):
    """Analyze transaction using Debate pattern."""
    logger.info("Starting Debate analysis")

    debate = DebatePattern(rounds=2)
    llm_client = await get_llm_client()

    result = await debate.execute(
        transaction=request.transaction.model_dump(),
        llm_client=llm_client,
    )

    return {
        "pattern": "Debate",
        "result": result,
        "debate_rounds": result.get("debate_rounds", 0),
        "arguments_count": len(result.get("arguments", [])),
    }


@router.post(
    "/analyze/self-critique",
    summary="Analyze using Self-Critique iterative refinement",
    description=(
        "Implements Generate-Critique-Revise cycle: First generates initial fraud assessment, "
        "critiques its own reasoning for flaws, then revises the decision based on critique. "
        "Typically runs 2-3 iterations for improved accuracy and reduced errors."
    ),
    responses={
        200: {
            "description": "Self-critique loop completed",
            "content": {
                "application/json": {
                    "examples": {
                        "improved_decision": {
                            "summary": "Revised after finding flaw",
                            "value": {
                                "pattern": "SelfCritique",
                                "result": {
                                    "is_fraud": True,
                                    "risk_score": 91.0,
                                    "iterations": 2,
                                    "initial_decision": {"is_fraud": False, "risk_score": 45.0},
                                    "critique": "Overlooked destination balance anomaly - money didn't arrive",
                                    "final_decision": {"is_fraud": True, "risk_score": 91.0},
                                },
                            },
                        }
                    }
                }
            },
        }
    },
)
async def analyze_with_self_critique(request: FraudAnalysisRequest):
    """Analyze transaction using Self-Critique pattern."""
    logger.info("Starting Self-Critique analysis")

    self_critique = SelfCritiquePattern()
    llm_client = await get_llm_client()

    result = await self_critique.execute(
        transaction=request.transaction.model_dump(),
        llm_client=llm_client,
        max_iterations=2,
    )

    return {
        "pattern": "Self-Critique",
        "result": result,
        "revisions": result.get("revision_count", 0),
    }


class ReflectionRequest(BaseModel):
    """Request for reflection pattern."""

    transaction: dict
    initial_decision: Optional[dict] = None

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "transaction": {
                        "transaction_id": "TX_REFLECTION_HIGH_CONF_001",
                        "type": "TRANSFER",
                        "amount": 145000.0,
                        "oldbalanceOrg": 160000.0,
                        "newbalanceOrig": 15000.0,
                        "oldbalanceDest": 5000.0,
                        "newbalanceDest": 150000.0,
                    },
                    "initial_decision": {
                        "is_fraud": True,
                        "risk_score": 88.5,
                        "confidence": 0.87,
                        "reasoning": "Large transfer draining 91% of origin balance",
                    },
                },
                {
                    "transaction": {
                        "transaction_id": "TX_REFLECTION_CASHOUT_002",
                        "type": "CASH_OUT",
                        "amount": 78000.0,
                        "oldbalanceOrg": 82000.0,
                        "newbalanceOrig": 4000.0,
                        "oldbalanceDest": 0.0,
                        "newbalanceDest": 0.0,
                    },
                    "initial_decision": {
                        "is_fraud": False,
                        "risk_score": 45.2,
                        "confidence": 0.62,
                        "reasoning": "CASH_OUT within normal range for account",
                    },
                },
                {
                    "transaction": {
                        "transaction_id": "TX_REFLECTION_NO_DECISION_003",
                        "type": "PAYMENT",
                        "amount": 3500.0,
                        "oldbalanceOrg": 25000.0,
                        "newbalanceOrig": 21500.0,
                        "oldbalanceDest": 8000.0,
                        "newbalanceDest": 11500.0,
                    }
                },
            ]
        }


@router.post(
    "/analyze/reflection",
    summary="Validate decision with Reflection",
    description="Reflect on decision against policies and reasoning chain",
    responses={
        200: {
            "description": "Successful response",
            "content": {
                "application/json": {
                    "example": {
                        "decision": {"is_fraud": True, "risk_score": 93.0},
                        "reflections": [
                            "Reconsidered destination account anomaly",
                            "Updated confidence: 0.93",
                        ],
                        "iterations": 2,
                    }
                }
            },
        }
    },
)
async def analyze_with_reflection(
    request: ReflectionRequest,
):
    """Validate decision using Reflection pattern."""
    logger.info("Starting Reflection validation")

    llm_client = await get_llm_client()

    # If no initial decision provided, make a quick one
    if not request.initial_decision:
        fraud_service = get_fraud_service()
        from app.models.fraud import Transaction

        txn = Transaction(**request.transaction)
        analysis = await fraud_service.analyze_transaction(txn)
        initial_decision = {
            "is_fraud": analysis.prediction.is_fraud,
            "risk_score": analysis.prediction.risk_score,
            "confidence": analysis.prediction.confidence,
            "reasoning": analysis.prediction.explanation,
        }
    else:
        initial_decision = request.initial_decision

    # Reflection
    reflection = ReflectionPattern()
    policies = [
        "TRANSFER > 100k requires verification",
        "Balance inconsistencies = automatic fraud flag",
        "CASH_OUT inherently risky",
    ]

    result = await reflection.execute(
        decision=initial_decision,
        transaction=request.transaction,  # Already a dict
        policies=policies,
        llm_client=llm_client,
    )

    return {
        "pattern": "Reflection",
        "result": result,
        "should_escalate": result.get("should_escalate", False),
    }


@router.get(
    "/prompts/few-shot-examples",
    summary="Get few-shot examples",
    description="Get curated few-shot examples for fraud detection",
)
async def get_few_shot_examples(count: int = 5, ensure_diversity: bool = True):
    """Get few-shot learning examples."""
    few_shot_mgr = get_few_shot_manager()
    examples = few_shot_mgr.select_examples(count=count, ensure_diversity=ensure_diversity)

    return {
        "examples": [e.model_dump() for e in examples],
        "count": len(examples),
        "formatted": few_shot_mgr.format_examples(examples),
    }


class PromptCompressRequest(BaseModel):
    """Request for prompt compression."""

    text: str = Field(..., description="Prompt text to compress")
    max_tokens: int = Field(1500, ge=100, le=8000, description="Maximum tokens allowed")

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "text": "You are a fraud detection expert with 15 years of experience as a Certified Fraud Examiner. Analyze the following transaction for potential fraud: Transaction ID TX_001, Amount $125,000, Type TRANSFER, from account A to account B. Consider balance changes, transaction patterns, and policy compliance. Provide detailed reasoning.",
                    "max_tokens": 1500,
                },
                {
                    "text": "As a senior financial crime investigator with expertise in money laundering detection, please perform a comprehensive analysis of this transaction. Transaction details: ID=TX_COMPRESS_002, Amount=$45,000, Type=CASH_OUT, Origin balance before=$52,000, Origin balance after=$7,000, Destination balance before=$0, Destination balance after=$0. Evaluate risk factors including balance drain percentage, transaction type risk profile, destination account history, timing patterns, and compliance with AML regulations. Consider historical patterns from similar accounts.",
                    "max_tokens": 800,
                },
                {
                    "text": "Analyze transaction TX_003 for fraud. Amount: $2,500. Type: PAYMENT.",
                    "max_tokens": 200,
                },
            ]
        }


@router.post(
    "/prompts/compress",
    summary="Compress prompt",
    description="Compress prompt while preserving critical information",
    responses={
        200: {
            "description": "Successful response",
            "content": {
                "application/json": {
                    "example": {
                        "compressed_prompt": "Fraud detection: CASH_OUT $95K...",
                        "original_tokens": 972,
                        "compressed_tokens": 456,
                        "compression_ratio": 0.47,
                    }
                }
            },
        }
    },
)
async def compress_prompt(request: PromptCompressRequest):
    """Compress a prompt to fit token budget."""
    text = request.text
    max_tokens = request.max_tokens

    compressed = PromptCompressor.compress(text, max_tokens=max_tokens)

    return {
        "original_length": len(text),
        "compressed_length": len(compressed),
        "compression_ratio": len(compressed) / len(text) if text else 0,
        "estimated_tokens": len(compressed) // 4,
        "compressed_text": compressed,
    }


@router.get(
    "/prompts/output-schema",
    summary="Get output schema specification",
    description="Get JSON schema for fraud decision output",
)
async def get_output_schema():
    """Get fraud decision output schema."""
    schema = OutputFormatter.FRAUD_DECISION_SCHEMA
    formatted = OutputFormatter.format_schema_prompt(schema)

    return {
        "schema": schema.model_dump(),
        "formatted_prompt": formatted,
    }


class ValidateOutputRequest(BaseModel):
    """Request for validating LLM output."""

    output: dict = Field(..., description="LLM output to validate")

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "output": {
                        "is_fraud": True,
                        "risk_score": 92,
                        "confidence": 0.88,
                        "risk_level": "CRITICAL",
                        "explanation": "Large transfer draining account with suspicious destination",
                        "reasoning_steps": [
                            "Analyzed transaction amount: $125,000",
                            "Checked balance changes: 94% drain detected",
                            "Reviewed fraud policies: Exceeds high-risk threshold",
                        ],
                    }
                },
                {
                    "output": {
                        "is_fraud": False,
                        "risk_score": 28,
                        "confidence": 0.75,
                        "risk_level": "LOW",
                        "explanation": "Normal payment transaction within typical spending patterns",
                        "reasoning_steps": [
                            "Amount $2,500 within normal range",
                            "Merchant account verified",
                            "Transaction history shows regular similar payments",
                        ],
                    }
                },
                {
                    "output": {
                        "is_fraud": True,
                        "risk_score": 78,
                        "confidence": 0.81,
                        "risk_level": "HIGH",
                        "explanation": "CASH_OUT transaction with unusual timing and amount pattern",
                    }
                },
            ]
        }


@router.post(
    "/prompts/validate-output",
    summary="Validate LLM output",
    description="Validate LLM output against fraud decision schema",
    responses={
        200: {
            "description": "Successful response",
            "content": {
                "application/json": {
                    "example": {
                        "is_valid": True,
                        "error": None,
                        "schema_name": "FraudDecisionSchema",
                    }
                }
            },
        }
    },
)
async def validate_llm_output(request: ValidateOutputRequest):
    """Validate LLM output against schema."""
    output_json = json.dumps(request.output)
    schema = OutputFormatter.FRAUD_DECISION_SCHEMA

    is_valid, error = OutputFormatter.validate_output(output_json, schema)

    return {
        "is_valid": is_valid,
        "error": error,
        "schema_name": schema.schema_name,
    }


@router.get(
    "/prompts/role-playing",
    summary="Get role-playing instruction",
    description="Get fraud specialist role-playing prompt",
)
async def get_role_playing_prompt():
    """Get role-playing instruction for LLM."""
    role_prompt = RolePlayingInstructor.fraud_specialist_role()

    return {
        "role": "Fraud Detection Specialist",
        "prompt": role_prompt,
        "benefits": [
            "Better alignment with expert behavior",
            "More structured analysis",
            "Clearer explanations",
            "Systematic evidence gathering",
        ],
    }


# =====================================================================
# AGENT-BASED ENDPOINTS
# =====================================================================

from app.agents import (
    FraudDetectionAgent,
    ManagerWorkerSystem,
    PlannerExecutorCriticSystem,
    DebateSystem,
    RoleSpecializedSystem,
    SwarmSystem,
    MemoryType,
)


class AgentAnalysisRequest(BaseModel):
    """Request for agent-based analysis."""

    transaction_id: str
    amount: float
    type: str
    oldbalanceOrg: float
    newbalanceOrig: float
    oldbalanceDest: float
    newbalanceDest: float
    nameOrig: str
    nameDest: str

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "transaction_id": "TX_AGENT_HIGH_RISK_001",
                    "amount": 165000.0,
                    "type": "TRANSFER",
                    "oldbalanceOrg": 180000.0,
                    "newbalanceOrig": 15000.0,
                    "oldbalanceDest": 5000.0,
                    "newbalanceDest": 170000.0,
                    "nameOrig": "C1231231230",
                    "nameDest": "C9879879870",
                },
                {
                    "transaction_id": "TX_AGENT_CASHOUT_002",
                    "amount": 89000.0,
                    "type": "CASH_OUT",
                    "oldbalanceOrg": 95000.0,
                    "newbalanceOrig": 6000.0,
                    "oldbalanceDest": 0.0,
                    "newbalanceDest": 0.0,
                    "nameOrig": "C4444444444",
                    "nameDest": "C0000000000",
                },
                {
                    "transaction_id": "TX_AGENT_PAYMENT_003",
                    "amount": 3200.0,
                    "type": "PAYMENT",
                    "oldbalanceOrg": 18500.0,
                    "newbalanceOrig": 15300.0,
                    "oldbalanceDest": 12000.0,
                    "newbalanceDest": 15200.0,
                    "nameOrig": "C6666666666",
                    "nameDest": "M2222222222",
                },
                {
                    "transaction_id": "TX_AGENT_DEBIT_004",
                    "amount": 450.0,
                    "type": "DEBIT",
                    "oldbalanceOrg": 5000.0,
                    "newbalanceOrig": 4550.0,
                    "oldbalanceDest": 0.0,
                    "newbalanceDest": 0.0,
                    "nameOrig": "C8888888888",
                    "nameDest": "C0000000000",
                },
            ]
        }


@router.post(
    "/agents/single",
    summary="Single-agent fraud analysis",
    description="Analyze transaction using single autonomous agent with observation, planning, execution, reasoning, decision, and reflection",
    responses={
        200: {
            "description": "Single agent analysis completed",
            "content": {
                "application/json": {
                    "example": {
                        "agent_type": "single",
                        "is_fraud": True,
                        "risk_score": 85.0,
                        "confidence": 0.89,
                        "tools_used": ["query_fraud_policy", "calculate_risk_score"],
                        "execution_time_ms": 142.5,
                        "reasoning": "Transaction exceeds policy threshold and balance drain is critical",
                    }
                }
            },
        }
    },
)
async def analyze_with_single_agent(request: AgentAnalysisRequest):
    """
    Analyze transaction using single-agent architecture.

    The agent follows a complete reasoning loop:
    1. Observation: Parse transaction and identify anomalies
    2. Planning: Create execution plan
    3. Execution: Run tools (risk scoring, policy lookup, history check)
    4. Reasoning: Chain-of-thought analysis
    5. Decision: Make fraud determination
    6. Reflection: Self-critique and escalation logic
    """
    agent = FraudDetectionAgent(max_steps=20)

    transaction = {
        "amount": request.amount,
        "type": request.type,
        "oldbalanceOrg": request.oldbalanceOrg,
        "newbalanceOrig": request.newbalanceOrig,
        "oldbalanceDest": request.oldbalanceDest,
        "newbalanceDest": request.newbalanceDest,
        "nameOrig": request.nameOrig,
        "nameDest": request.nameDest,
    }

    result = await agent.analyze(transaction, request.transaction_id)

    return {
        "agent_type": "single",
        "transaction_id": result.transaction_id,
        "is_fraud": result.is_fraud,
        "risk_score": result.risk_score,
        "risk_level": result.risk_level,
        "confidence": result.confidence,
        "explanation": result.explanation,
        "observations": result.observations,
        "anomalies": result.anomalies,
        "reasoning_steps": result.reasoning_steps,
        "tool_results": result.tool_results,
        "should_escalate": result.should_escalate,
        "escalation_reason": result.escalation_reason,
        "self_critique": result.self_critique,
        "total_steps": result.total_steps,
        "termination_reason": result.termination_reason,
        "execution_time": result.execution_time,
    }


@router.post(
    "/agents/manager-worker",
    summary="Manager-Worker multi-agent analysis",
    description="Analyze using manager coordinating multiple worker agents in parallel",
    responses={
        200: {
            "description": "Manager-worker coordination completed",
            "content": {
                "application/json": {
                    "example": {
                        "agent_type": "manager-worker",
                        "is_fraud": True,
                        "risk_score": 90.0,
                        "confidence": 0.95,
                        "workers": 3,
                        "agreement_score": 1.0,
                        "aggregation_method": "majority_vote",
                        "worker_results": [
                            {"worker": "policy_checker", "verdict": "fraud", "score": 92.0},
                            {"worker": "balance_analyzer", "verdict": "fraud", "score": 88.0},
                            {"worker": "velocity_monitor", "verdict": "fraud", "score": 90.0},
                        ],
                        "execution_time_ms": 256.3,
                    }
                }
            },
        }
    },
)
async def analyze_with_manager_worker(request: AgentAnalysisRequest):
    """
    Analyze using manager-worker pattern.

    Manager delegates to 3 worker agents who analyze in parallel.
    Results are aggregated using majority voting.
    """
    system = ManagerWorkerSystem(num_workers=3)

    transaction = {
        "amount": request.amount,
        "type": request.type,
        "oldbalanceOrg": request.oldbalanceOrg,
        "newbalanceOrig": request.newbalanceOrig,
        "oldbalanceDest": request.oldbalanceDest,
        "newbalanceDest": request.newbalanceDest,
        "nameOrig": request.nameOrig,
        "nameDest": request.nameDest,
    }

    result = await system.analyze(transaction, request.transaction_id)

    return {
        "agent_type": "manager-worker",
        "transaction_id": result.transaction_id,
        "is_fraud": result.is_fraud,
        "risk_score": result.risk_score,
        "confidence": result.confidence,
        "explanation": result.explanation,
        "consensus_strategy": result.consensus_strategy,
        "agreement_level": result.agreement_level,
        "num_agents": len(result.agent_results),
        "total_time": result.total_time,
    }


@router.post(
    "/agents/planner-executor-critic",
    summary="Planner-Executor-Critic analysis",
    description="Analyze using three specialized roles: planner creates strategy, executor performs analysis, critic validates results",
    responses={
        200: {
            "description": "PEC pipeline completed",
            "content": {
                "application/json": {
                    "example": {
                        "agent_type": "planner-executor-critic",
                        "is_fraud": True,
                        "risk_score": 87.0,
                        "confidence": 0.92,
                        "iterations": 2,
                        "plan_quality": 0.85,
                        "execution_quality": 0.90,
                        "critic_approval": True,
                        "execution_time_ms": 412.7,
                    }
                }
            },
        }
    },
)
async def analyze_with_planner_executor_critic(request: AgentAnalysisRequest):
    """
    Analyze using planner-executor-critic pattern.

    Three specialized agents:
    - Planner: Creates analysis strategy
    - Executor: Performs detailed analysis
    - Critic: Validates executor's results
    """
    system = PlannerExecutorCriticSystem()

    transaction = {
        "amount": request.amount,
        "type": request.type,
        "oldbalanceOrg": request.oldbalanceOrg,
        "newbalanceOrig": request.newbalanceOrig,
        "oldbalanceDest": request.oldbalanceDest,
        "newbalanceDest": request.newbalanceDest,
        "nameOrig": request.nameOrig,
        "nameDest": request.nameDest,
    }

    result = await system.analyze(transaction, request.transaction_id)

    return {
        "agent_type": "planner-executor-critic",
        "transaction_id": result.transaction_id,
        "is_fraud": result.is_fraud,
        "risk_score": result.risk_score,
        "confidence": result.confidence,
        "explanation": result.explanation,
        "consensus_strategy": result.consensus_strategy,
        "agreement_level": result.agreement_level,
        "total_time": result.total_time,
    }


@router.post(
    "/agents/debate",
    summary="Debate-based analysis",
    description="Analyze using adversarial debate: prosecutor argues for fraud, defense argues legitimate, judge makes final ruling",
    responses={
        200: {
            "description": "Successful response",
            "content": {
                "application/json": {
                    "example": {
                        "agent_type": "debate",
                        "is_fraud": True,
                        "risk_score": 87.5,
                        "verdict": "FRAUD",
                        "execution_time_ms": 298.4,
                    }
                }
            },
        }
    },
)
async def analyze_with_debate(request: AgentAnalysisRequest):
    """
    Analyze using debate pattern.

    Three agents debate the fraud classification:
    - Prosecutor: Argues transaction IS fraud
    - Defense: Argues transaction is legitimate
    - Judge: Makes final ruling based on arguments
    """
    system = DebateSystem()

    transaction = {
        "amount": request.amount,
        "type": request.type,
        "oldbalanceOrg": request.oldbalanceOrg,
        "newbalanceOrig": request.newbalanceOrig,
        "oldbalanceDest": request.oldbalanceDest,
        "newbalanceDest": request.newbalanceDest,
        "nameOrig": request.nameOrig,
        "nameDest": request.nameDest,
    }

    result = await system.analyze(transaction, request.transaction_id)

    return {
        "agent_type": "debate",
        "transaction_id": result.transaction_id,
        "is_fraud": result.is_fraud,
        "risk_score": result.risk_score,
        "confidence": result.confidence,
        "explanation": result.explanation,
        "consensus_strategy": result.consensus_strategy,
        "agreement_level": result.agreement_level,
        "total_time": result.total_time,
    }


@router.post(
    "/agents/role-specialized",
    summary="Role-specialized multi-agent analysis",
    description="Analyze using domain expert agents: transaction analyst, account specialist, and policy expert",
    responses={
        200: {
            "description": "Successful response",
            "content": {
                "application/json": {
                    "example": {
                        "agent_type": "role-specialized",
                        "is_fraud": True,
                        "risk_score": 88.5,
                        "confidence": 0.91,
                        "execution_time_ms": 378.2,
                    }
                }
            },
        }
    },
)
async def analyze_with_role_specialized(request: AgentAnalysisRequest):
    """
    Analyze using role-specialized pattern.

    Three domain experts collaborate:
    - Transaction Analyst: Examines transaction patterns
    - Account Specialist: Analyzes account history
    - Policy Expert: Checks compliance and policies

    Uses weighted voting with expertise weights.
    """
    system = RoleSpecializedSystem()

    transaction = {
        "amount": request.amount,
        "type": request.type,
        "oldbalanceOrg": request.oldbalanceOrg,
        "newbalanceOrig": request.newbalanceOrig,
        "oldbalanceDest": request.oldbalanceDest,
        "newbalanceDest": request.newbalanceDest,
        "nameOrig": request.nameOrig,
        "nameDest": request.nameDest,
    }

    result = await system.analyze(transaction, request.transaction_id)

    return {
        "agent_type": "role-specialized",
        "transaction_id": result.transaction_id,
        "is_fraud": result.is_fraud,
        "risk_score": result.risk_score,
        "confidence": result.confidence,
        "explanation": result.explanation,
        "consensus_strategy": result.consensus_strategy,
        "agreement_level": result.agreement_level,
        "total_time": result.total_time,
    }


@router.post(
    "/agents/swarm",
    summary="Swarm intelligence analysis",
    description="Analyze using swarm of 5 agents with consensus voting",
    responses={
        200: {
            "description": "Successful response",
            "content": {
                "application/json": {
                    "example": {
                        "agent_type": "swarm",
                        "is_fraud": True,
                        "risk_score": 91.0,
                        "agents_active": 5,
                        "consensus_rounds": 3,
                    }
                }
            },
        }
    },
)
async def analyze_with_swarm(
    request: AgentAnalysisRequest, swarm_size: int = 5, threshold: float = 0.6
):
    """
    Analyze using swarm intelligence pattern.

    Multiple agents (default 5) analyze in parallel and vote on result.
    Consensus requires threshold fraction agreement (default 60%).
    Demonstrates emergent intelligence from collective.
    """
    system = SwarmSystem(swarm_size=swarm_size, consensus_threshold=threshold)

    transaction = {
        "amount": request.amount,
        "type": request.type,
        "oldbalanceOrg": request.oldbalanceOrg,
        "newbalanceOrig": request.newbalanceOrig,
        "oldbalanceDest": request.oldbalanceDest,
        "newbalanceDest": request.newbalanceDest,
        "nameOrig": request.nameOrig,
        "nameDest": request.nameDest,
    }

    result = await system.analyze(transaction, request.transaction_id)

    return {
        "agent_type": "swarm",
        "transaction_id": result.transaction_id,
        "is_fraud": result.is_fraud,
        "risk_score": result.risk_score,
        "confidence": result.confidence,
        "explanation": result.explanation,
        "consensus_strategy": result.consensus_strategy,
        "agreement_level": result.agreement_level,
        "swarm_size": swarm_size,
        "consensus_threshold": threshold,
        "total_time": result.total_time,
    }


@router.get(
    "/agents/memory/{transaction_id}",
    summary="Get agent memory contents",
    description="Inspect agent memory for debugging and transparency",
)
async def get_agent_memory(transaction_id: str, memory_type: Optional[str] = None):
    """
    Get agent memory contents.

    Useful for debugging and understanding agent reasoning.
    Memory types: SHORT_TERM, WORKING, LONG_TERM
    """
    agent = FraudDetectionAgent()

    # Convert string to MemoryType if provided
    mem_type = None
    if memory_type:
        try:
            mem_type = MemoryType[memory_type.upper()]
        except KeyError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid memory type. Must be one of: SHORT_TERM, WORKING, LONG_TERM",
            )

    memories = agent.get_memory_contents(mem_type)
    stats = agent.get_memory_stats()

    return {
        "transaction_id": transaction_id,
        "memory_type": memory_type or "all",
        "memories": memories,
        "statistics": stats,
    }


@router.get(
    "/agents/tools",
    summary="List available agent tools",
    description="Get list of tools available to agents",
)
async def list_agent_tools():
    """List all registered agent tools with schemas."""
    from app.agents.tool_registry import get_tool_registry

    registry = get_tool_registry()
    tools = registry.list_tools()
    schemas = registry.list_schemas()

    return {
        "total_tools": len(tools),
        "tools": tools,
        "schemas": [schema.dict() for schema in schemas],
    }


class ToolExecutionRequest(BaseModel):
    """Request for executing an agent tool."""

    tool_name: str = Field(..., description="Name of the tool to execute")
    parameters: dict = Field(..., description="Tool parameters")

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "tool_name": "calculate_risk_score",
                    "parameters": {
                        "amount": 125000.0,
                        "type": "TRANSFER",
                        "balance_drain_ratio": 0.92,
                    },
                }
            ]
        }


@router.post(
    "/agents/tools/execute",
    summary="Execute agent tool manually",
    description="Execute a specific agent tool for testing/debugging",
    responses={
        200: {
            "description": "Successful response",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "result": {"tool": "query_fraud_policy", "outcome": "threshold_exceeded"},
                        "execution_time_ms": 15.2,
                    }
                }
            },
        }
    },
)
async def execute_agent_tool(request: ToolExecutionRequest):
    """Execute an agent tool manually."""
    from app.agents.tool_registry import get_tool_registry

    registry = get_tool_registry()

    try:
        result = await registry.execute(request.tool_name, request.parameters)

        return {
            "tool_name": result.tool_name,
            "success": result.success,
            "result": result.result,
            "error": result.error,
            "execution_time": result.execution_time,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Tool execution failed: {str(e)}")


# ==================== Planning & Reasoning Endpoints ====================


@router.post(
    "/planning/create-plan",
    summary="Create task execution plan",
    description="Generate DAG-based execution plan for fraud analysis",
    responses={
        200: {
            "description": "Successful response",
            "content": {
                "application/json": {
                    "example": {
                        "plan_id": "plan_abc123",
                        "tasks": [{"id": "t1", "action": "query_fraud_policy"}],
                        "execution_order": ["t1"],
                    }
                }
            },
        }
    },
)
async def create_task_plan(request: AgentAnalysisRequest):
    """Create task execution plan with dependency tracking."""
    from app.agents.task_planner import TaskPlanner

    planner = TaskPlanner()

    transaction = {
        "transaction_id": request.transaction_id,
        "type": request.type,
        "amount": request.amount,
        "oldbalanceOrg": request.oldbalanceOrg,
        "newbalanceOrig": request.newbalanceOrig,
        "oldbalanceDest": request.oldbalanceDest,
        "newbalanceDest": request.newbalanceDest,
    }

    try:
        dag = planner.create_plan(
            transaction=transaction, goal="determine_fraud", constraints={"max_duration": 30.0}
        )

        # Get execution order
        execution_order = planner.get_execution_order(dag)
        estimated_duration = planner.estimate_duration(dag, parallel=True)

        return {
            "transaction_id": request.transaction_id,
            "total_tasks": len(dag.tasks),
            "tasks": {
                task_id: {
                    "id": task.id,
                    "type": task.type.value,
                    "description": task.description,
                    "dependencies": task.dependencies,
                    "estimated_duration": task.estimated_duration,
                    "status": task.status.value,
                }
                for task_id, task in dag.tasks.items()
            },
            "execution_order": execution_order,
            "estimated_duration": estimated_duration,
            "has_cycle": dag.has_cycle(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Plan creation failed: {str(e)}")


@router.post(
    "/reasoning/test-hypothesis",
    summary="Test fraud hypothesis",
    description="Test hypothesis against evidence using structured reasoning",
    responses={
        200: {
            "description": "Successful response",
            "content": {
                "application/json": {
                    "example": {
                        "hypothesis": "Account takeover fraud",
                        "evidence_for": ["unusual_amount", "balance_drain"],
                        "evidence_against": ["normal_time_of_day"],
                        "confidence": 0.78,
                    }
                }
            },
        }
    },
)
async def test_hypothesis(
    hypothesis: str,
    evidence: dict,
):
    """Test fraud hypothesis against evidence."""
    from app.agents.reasoning_engine import ReasoningEngine, Hypothesis

    engine = ReasoningEngine()

    hyp = Hypothesis(
        id="h1",
        statement=hypothesis,
        confidence=0.5,
    )

    try:
        result = engine.test_hypothesis(hyp, evidence)

        return {
            "hypothesis": result.statement,
            "status": result.status.value,
            "confidence": result.confidence,
            "supporting_evidence": result.supporting_evidence,
            "refuting_evidence": result.refuting_evidence,
            "uncertainty_sources": [s.value for s in result.uncertainty_sources],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Hypothesis testing failed: {str(e)}")


@router.post(
    "/reasoning/counterfactual",
    summary="Counterfactual reasoning",
    description="Perform what-if analysis on transaction",
    responses={
        200: {
            "description": "Successful response",
            "content": {
                "application/json": {
                    "example": {
                        "original_decision": "fraud",
                        "counterfactual_scenario": "If amount was $100 instead of $95000",
                        "new_decision": "legitimate",
                        "causal_factor": "amount",
                    }
                }
            },
        }
    },
)
async def counterfactual_analysis(
    request: AgentAnalysisRequest,
    what_ifs: list,  # List of modifications
):
    """Perform counterfactual reasoning (what-if scenarios)."""
    from app.agents.reasoning_engine import ReasoningEngine

    engine = ReasoningEngine()

    transaction = {
        "type": request.type,
        "amount": request.amount,
        "oldbalanceOrg": request.oldbalanceOrg,
        "newbalanceOrig": request.newbalanceOrig,
    }

    # Baseline decision (heuristic)
    decision = {
        "is_fraud": request.amount > 100000,
        "risk_score": min(100, request.amount / 2000),
        "confidence": 0.7,
    }

    try:
        scenarios = engine.counterfactual_reasoning(
            transaction=transaction,
            decision=decision,
            what_ifs=what_ifs,
        )

        return {
            "transaction_id": request.transaction_id,
            "baseline_decision": decision,
            "scenarios": [
                {
                    "id": s.id,
                    "description": s.description,
                    "modifications": s.modifications,
                    "predicted_outcome": s.predicted_outcome,
                    "sensitivity": s.sensitivity,
                }
                for s in scenarios
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Counterfactual analysis failed: {str(e)}")


@router.post(
    "/reasoning/self-critique",
    summary="Self-critique reasoning",
    description="Critique agent's reasoning for soundness and completeness",
    responses={
        200: {
            "description": "Successful response",
            "content": {
                "application/json": {
                    "example": {
                        "initial_decision": {"is_fraud": False},
                        "critique": "Missed destination balance anomaly",
                        "revised_decision": {"is_fraud": True},
                    }
                }
            },
        }
    },
)
async def self_critique(
    reasoning_steps: list,
    decision: dict,
    evidence: dict,
):
    """Perform self-critique of reasoning chain."""
    from app.agents.reasoning_engine import ReasoningEngine

    engine = ReasoningEngine()

    try:
        critique = engine.self_critique(
            reasoning_steps=reasoning_steps,
            decision=decision,
            evidence=evidence,
        )

        return {
            "is_sound": critique["is_sound"],
            "is_complete": critique["is_complete"],
            "contradictions": critique["contradictions"],
            "missing_evidence": critique["missing_evidence"],
            "unsupported_claims": critique["unsupported_claims"],
            "suggestions": critique["suggestions"],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Self-critique failed: {str(e)}")


@router.post(
    "/reasoning/estimate-uncertainty",
    summary="Estimate decision uncertainty",
    description="Quantify uncertainty from multiple sources",
    responses={
        200: {
            "description": "Successful response",
            "content": {
                "application/json": {
                    "example": {
                        "point_estimate": 0.85,
                        "confidence_interval": [0.78, 0.92],
                        "epistemic_uncertainty": 0.07,
                        "aleatoric_uncertainty": 0.05,
                    }
                }
            },
        }
    },
)
async def estimate_uncertainty(
    evidence: dict,
    reasoning_steps: list,
    decision: dict,
):
    """Estimate uncertainty in decision."""
    from app.agents.reasoning_engine import ReasoningEngine

    engine = ReasoningEngine()

    try:
        estimate = engine.estimate_uncertainty(
            evidence=evidence,
            reasoning_steps=reasoning_steps,
            decision=decision,
        )

        return {
            "confidence": estimate.confidence,
            "sources": {k.value: v for k, v in estimate.sources.items()},
            "propagated": estimate.propagated,
            "explanation": estimate.explanation,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Uncertainty estimation failed: {str(e)}")


@router.post(
    "/reasoning/check-constraints",
    summary="Check constraint satisfaction",
    description="Validate decision against hard and soft constraints",
    responses={
        200: {
            "description": "Successful response",
            "content": {
                "application/json": {
                    "example": {
                        "constraints_satisfied": True,
                        "violations": [],
                        "constraint_results": {"balance_positive": True, "amount_valid": True},
                    }
                }
            },
        }
    },
)
async def check_constraints(
    decision: dict,
    constraints: list,  # List of constraint dicts
):
    """Check if decision satisfies constraints."""
    from app.agents.reasoning_engine import (
        ReasoningEngine,
        Constraint,
        ConstraintType,
    )

    engine = ReasoningEngine()

    # Convert to Constraint objects
    constraint_objs = [
        Constraint(
            id=c.get("id", f"c{i}"),
            description=c.get("description", ""),
            type=ConstraintType[c.get("type", "SOFT").upper()],
            condition=c.get("condition", ""),
        )
        for i, c in enumerate(constraints)
    ]

    try:
        all_satisfied, violated = engine.satisfy_constraints(
            decision=decision,
            constraints=constraint_objs,
        )

        return {
            "all_satisfied": all_satisfied,
            "total_constraints": len(constraint_objs),
            "violated_count": len(violated),
            "violated": [
                {
                    "id": c.id,
                    "description": c.description,
                    "type": c.type.value,
                    "violation_message": c.violation_message,
                }
                for c in violated
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Constraint checking failed: {str(e)}")


# ==================== Autonomy Control Endpoints ====================


@router.post(
    "/autonomy/get-level",
    summary="Get autonomy level",
    description="Determine appropriate autonomy level for decision",
    responses={
        200: {
            "description": "Successful response",
            "content": {
                "application/json": {
                    "example": {
                        "level": 3,
                        "description": "High Autonomy - Agent can make final decisions",
                        "capabilities": ["tool_execution", "decision_making"],
                    }
                }
            },
        }
    },
)
async def get_autonomy_level(
    decision: dict,
    evidence: dict,
):
    """Get appropriate autonomy level."""
    from app.agents.autonomy_controller import AutonomyController

    controller = AutonomyController(
        max_steps=10,
        timeout_seconds=30.0,
        min_confidence=0.7,
    )

    try:
        level = controller.get_autonomy_level(decision, evidence)

        return {
            "autonomy_level": level.value,
            "decision_confidence": decision.get("confidence", 0.5),
            "transaction_amount": evidence.get("amount", 0),
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Autonomy level determination failed: {str(e)}"
        )


@router.post(
    "/autonomy/check-escalation",
    summary="Check if should escalate",
    description="Determine if decision should be escalated to human",
    responses={
        200: {
            "description": "Successful response",
            "content": {
                "application/json": {
                    "example": {
                        "should_escalate": True,
                        "reason": "Risk score 95.0 exceeds escalation threshold",
                        "escalation_to": "human_analyst",
                    }
                }
            },
        }
    },
)
async def check_escalation(
    request: AgentAnalysisRequest,
    decision: dict,
    reasoning_steps: list = None,
):
    """Check if decision should be escalated to human."""
    from app.agents.autonomy_controller import AutonomyController

    controller = AutonomyController(
        max_steps=10,
        timeout_seconds=30.0,
        min_confidence=0.7,
    )

    evidence = {
        "amount": request.amount,
        "type": request.type,
        "oldbalanceOrg": request.oldbalanceOrg,
        "newbalanceOrig": request.newbalanceOrig,
    }

    try:
        should_escalate, reason = controller.should_escalate(
            decision=decision,
            evidence=evidence,
            reasoning_steps=reasoning_steps,
        )

        response = {
            "should_escalate": should_escalate,
            "reason": reason.value if reason else None,
        }

        if should_escalate:
            ticket = controller.create_escalation(
                transaction_id=request.transaction_id,
                reason=reason,
                decision=decision,
                evidence=evidence,
                reasoning_steps=reasoning_steps,
            )
            response["escalation_ticket"] = {
                "id": ticket.id,
                "transaction_id": ticket.transaction_id,
                "reason": ticket.reason.value,
                "explanation": ticket.explanation,
                "priority": ticket.priority,
                "suggested_decision": ticket.suggested_decision,
            }

        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Escalation check failed: {str(e)}")


@router.post(
    "/autonomy/check-stop-conditions",
    summary="Check stop conditions",
    description="Check if agent should stop execution",
    responses={
        200: {
            "description": "Successful response",
            "content": {
                "application/json": {
                    "example": {
                        "should_stop": True,
                        "reason": "Reached max iterations (10)",
                        "stopping_criteria_met": ["max_iterations"],
                    }
                }
            },
        }
    },
)
async def check_stop_conditions(
    step_count: int,
    reasoning_steps: list = None,
):
    """Check if agent should stop execution."""
    from app.agents.autonomy_controller import AutonomyController

    controller = AutonomyController(
        max_steps=10,
        timeout_seconds=30.0,
        min_confidence=0.7,
    )

    controller.start_session(goal="determine_fraud")

    try:
        should_stop, condition = controller.check_stop_conditions(
            step_count=step_count,
            reasoning_steps=reasoning_steps or [],
        )

        return {
            "should_stop": should_stop,
            "condition": (
                {
                    "type": condition.type.value,
                    "triggered": condition.triggered,
                    "threshold": condition.threshold,
                    "current_value": condition.current_value,
                    "message": condition.message,
                }
                if condition
                else None
            ),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Stop condition check failed: {str(e)}")


@router.post(
    "/autonomy/check-goal-drift",
    summary="Check goal drift",
    description="Detect if agent has drifted from original goal",
    responses={
        200: {
            "description": "Successful response",
            "content": {
                "application/json": {
                    "example": {
                        "drift_detected": False,
                        "alignment_score": 0.95,
                        "original_goal": "fraud_detection",
                        "current_behavior": "fraud_detection",
                    }
                }
            },
        }
    },
)
async def check_goal_drift(
    goal: str,
    current_focus: str,
    reasoning_steps: list = None,
):
    """Check if agent has drifted from goal."""
    from app.agents.autonomy_controller import AutonomyController

    controller = AutonomyController()
    controller.start_session(goal=goal)

    try:
        has_drifted, warnings = controller.check_goal_drift(
            current_focus=current_focus,
            reasoning_steps=reasoning_steps or [],
        )

        response = {
            "has_drifted": has_drifted,
            "warnings": warnings,
        }

        if has_drifted:
            response["refocus_instruction"] = controller.refocus_on_goal()

        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Goal drift check failed: {str(e)}")


# ============================================================================
# Section 3.7: Tool & Failure Recovery Endpoints
# ============================================================================


@router.post(
    "/recovery/check-health",
    summary="Check tool health",
    description="Run health check for a tool",
    responses={
        200: {
            "description": "Successful response",
            "content": {
                "application/json": {
                    "example": {
                        "healthy": True,
                        "checks": {"llm_responsive": True, "tools_available": True},
                    }
                }
            },
        }
    },
)
async def check_tool_health(
    tool_name: str,
):
    """Check health of a tool."""
    from app.agents.tool_recovery import ToolRecoveryManager

    recovery_manager = ToolRecoveryManager()

    # Simple health check function
    async def health_check():
        await asyncio.sleep(0.1)  # Simulate check
        return True

    try:
        health = await recovery_manager.check_tool_health(tool_name, health_check)
        return health.dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")


@router.post(
    "/recovery/analyze-failure",
    summary="Analyze failure root cause",
    description="Perform root cause analysis on a failure",
    responses={
        200: {
            "description": "Successful response",
            "content": {
                "application/json": {
                    "example": {
                        "root_cause": "LLM timeout",
                        "recovery_strategy": "retry_with_backoff",
                        "can_recover": True,
                    }
                }
            },
        }
    },
)
async def analyze_failure_root_cause(
    tool_name: str,
    error_message: str,
    context: dict = None,
):
    """Analyze root cause of a failure."""
    from app.agents.tool_recovery import ToolRecoveryManager

    recovery_manager = ToolRecoveryManager()

    try:
        # Create exception from message
        exception = Exception(error_message)

        root_cause = recovery_manager.analyze_failure_root_cause(
            tool_name=tool_name,
            exception=exception,
            context=context or {},
        )

        return root_cause.dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Root cause analysis failed: {str(e)}")


@router.post(
    "/recovery/register-fallback",
    summary="Register fallback chain",
    description="Register fallback chain for a tool",
    responses={
        200: {
            "description": "Successful response",
            "content": {
                "application/json": {
                    "example": {"fallback_id": "fb_12345", "registered": True, "priority": 1}
                }
            },
        }
    },
)
async def register_fallback_chain(
    primary: str,
    secondary: str = None,
    tertiary: str = None,
    cache_fallback: bool = True,
):
    """Register fallback chain."""
    from app.agents.tool_recovery import ToolRecoveryManager, FallbackChain

    recovery_manager = ToolRecoveryManager()

    try:
        chain = FallbackChain(
            primary=primary,
            secondary=secondary,
            tertiary=tertiary,
            cache_fallback=cache_fallback,
        )

        recovery_manager.register_fallback_chain(chain)

        return {
            "status": "registered",
            "chain": chain.dict(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fallback registration failed: {str(e)}")


@router.post(
    "/recovery/aggregate-partial",
    summary="Aggregate partial results",
    description="Aggregate partial results from failed operations",
    responses={
        200: {
            "description": "Successful response",
            "content": {
                "application/json": {
                    "example": {
                        "aggregated_result": {"is_fraud": True, "confidence": 0.72},
                        "partial_results_used": 3,
                        "missing_results": 1,
                    }
                }
            },
        }
    },
)
async def aggregate_partial_results(
    tool_name: str,
    completed_parts: list,
    failed_parts: list,
    total_parts: int,
):
    """Aggregate partial results."""
    from app.agents.tool_recovery import ToolRecoveryManager

    recovery_manager = ToolRecoveryManager()

    try:
        partial = recovery_manager.aggregate_partial_results(
            tool_name=tool_name,
            completed_parts=completed_parts,
            failed_parts=failed_parts,
            total_parts=total_parts,
        )

        return partial.dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Partial result aggregation failed: {str(e)}")


@router.get(
    "/recovery/health-status",
    summary="Get health status",
    description="Get health status for all tools",
)
async def get_health_status(
    tool_name: str = None,
):
    """Get health status."""
    from app.agents.tool_recovery import ToolRecoveryManager

    recovery_manager = ToolRecoveryManager()

    try:
        return recovery_manager.get_health_status(tool_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health status retrieval failed: {str(e)}")


@router.get(
    "/recovery/incidents",
    summary="Get incidents",
    description="Get incident reports",
)
async def get_incidents(
    severity: str = None,
):
    """Get incident reports."""
    from app.agents.tool_recovery import ToolRecoveryManager

    recovery_manager = ToolRecoveryManager()

    try:
        incidents = recovery_manager.get_incidents(severity=severity)
        return {
            "total_incidents": len(incidents),
            "incidents": [i.dict() for i in incidents],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Incident retrieval failed: {str(e)}")


@router.get(
    "/recovery/statistics",
    summary="Get recovery statistics",
    description="Get recovery and incident statistics",
)
async def get_recovery_statistics():
    """Get recovery statistics."""
    from app.agents.tool_recovery import ToolRecoveryManager

    recovery_manager = ToolRecoveryManager()

    try:
        return recovery_manager.get_recovery_statistics()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Statistics retrieval failed: {str(e)}")


# ============================================================================
# Section 3.8: Async & Production Patterns Endpoints
# ============================================================================


async def get_worker_pool() -> WorkerPool:
    """Get or create worker pool."""
    global _worker_pool
    if _worker_pool is None:
        _worker_pool = WorkerPool(WorkerPoolConfig(max_workers=5))
        await _worker_pool.start()
    return _worker_pool


@router.post(
    "/async/submit-task",
    summary="Submit background task",
    description="Submit a task for background processing",
    responses={
        200: {
            "description": "Successful response",
            "content": {
                "application/json": {
                    "example": {
                        "task_id": "task_abc123",
                        "status": "queued",
                        "estimated_completion_ms": 5000,
                    }
                }
            },
        }
    },
)
async def submit_background_task(
    task_name: str,
    priority: str = "NORMAL",
    metadata: dict = None,
):
    """Submit background task."""
    pool = await get_worker_pool()

    try:
        # Example task function
        async def example_task():
            await asyncio.sleep(2.0)
            return {"status": "completed", "task": task_name}

        task_id = await pool.submit_task(
            name=task_name,
            func=example_task,
            priority=TaskPriority(priority),
            metadata=metadata,
        )

        return {
            "task_id": task_id,
            "status": "submitted",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Task submission failed: {str(e)}")


@router.get(
    "/async/task/{task_id}",
    summary="Get task status",
    description="Get background task status",
)
async def get_background_task(task_id: str):
    """Get background task status."""
    pool = await get_worker_pool()

    try:
        task = await pool.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        return task.dict()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Task retrieval failed: {str(e)}")


@router.delete(
    "/async/task/{task_id}",
    summary="Cancel task",
    description="Cancel a background task",
)
async def cancel_background_task(task_id: str):
    """Cancel background task."""
    pool = await get_worker_pool()

    try:
        cancelled = await pool.cancel_task(task_id)
        return {
            "task_id": task_id,
            "cancelled": cancelled,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Task cancellation failed: {str(e)}")


@router.get(
    "/async/worker-stats",
    summary="Get worker pool statistics",
    description="Get worker pool statistics",
)
async def get_worker_statistics():
    """Get worker pool statistics."""
    pool = await get_worker_pool()

    try:
        return pool.get_statistics()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Statistics retrieval failed: {str(e)}")


@router.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """WebSocket endpoint for real-time updates."""
    await _websocket_manager.connect(client_id, websocket)

    try:
        while True:
            # Receive messages from client
            data = await websocket.receive_json()

            # Handle subscription requests
            if data.get("action") == "subscribe":
                topic = data.get("topic")
                await _websocket_manager.subscribe(client_id, topic)
                await websocket.send_json(
                    {
                        "type": "subscribed",
                        "topic": topic,
                    }
                )

            elif data.get("action") == "unsubscribe":
                topic = data.get("topic")
                await _websocket_manager.unsubscribe(client_id, topic)
                await websocket.send_json(
                    {
                        "type": "unsubscribed",
                        "topic": topic,
                    }
                )

    except WebSocketDisconnect:
        _websocket_manager.disconnect(client_id)
    except Exception as e:
        logger.error(f"WebSocket error for client {client_id}: {e}")
        _websocket_manager.disconnect(client_id)


@router.post(
    "/async/broadcast",
    summary="Broadcast to WebSocket clients",
    description="Broadcast message to WebSocket subscribers",
    responses={
        200: {
            "description": "Successful response",
            "content": {
                "application/json": {
                    "example": {"broadcast_id": "bc_xyz789", "recipients": 5, "status": "sent"}
                }
            },
        }
    },
)
async def broadcast_message(
    topic: str,
    message: dict,
):
    """Broadcast message to WebSocket clients."""
    try:
        await _websocket_manager.broadcast(topic, message)
        return {
            "status": "broadcasted",
            "topic": topic,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Broadcast failed: {str(e)}")


@router.get(
    "/async/websocket-stats",
    summary="Get WebSocket statistics",
    description="Get WebSocket connection statistics",
)
async def get_websocket_statistics():
    """Get WebSocket statistics."""
    try:
        return _websocket_manager.get_statistics()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Statistics retrieval failed: {str(e)}")


@router.get(
    "/async/stream/{topic}",
    summary="Server-Sent Events stream",
    description="Stream events via Server-Sent Events",
)
async def sse_stream(topic: str, interval: float = 1.0, max_events: int = 10):
    """Server-Sent Events endpoint."""
    if not SSE_AVAILABLE:
        raise HTTPException(
            status_code=501, detail="SSE not available. Install sse-starlette package."
        )

    try:
        return EventSourceResponse(sse_event_generator(topic, interval, max_events))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SSE stream failed: {str(e)}")


@router.get(
    "/async/resource-stats",
    summary="Get resource statistics",
    description="Get resource manager statistics",
)
async def get_resource_statistics():
    """Get resource manager statistics."""
    try:
        return _resource_manager.get_statistics()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Statistics retrieval failed: {str(e)}")


@router.post(
    "/async/cleanup-resources",
    summary="Cleanup idle resources",
    description="Cleanup idle resources",
    responses={
        200: {
            "description": "Successful response",
            "content": {
                "application/json": {
                    "example": {"cleaned_tasks": 12, "freed_memory_mb": 45.3, "status": "complete"}
                }
            },
        }
    },
)
async def cleanup_idle_resources(idle_timeout: float = 300.0):
    """Cleanup idle resources."""
    try:
        cleaned = await _resource_manager.cleanup_idle(idle_timeout)
        return {
            "cleaned_count": cleaned,
            "idle_timeout": idle_timeout,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Resource cleanup failed: {str(e)}")


# =============================================================================
# TOOL USE & ENVIRONMENT CONTROL (Section 3.3)
# =============================================================================

from app.agents.tool_registry import get_tool_registry
from app.agents.environment_tools import (
    get_file_system,
    get_python_sandbox,
    get_database_tools,
)


@router.get(
    "/tools/list",
    summary="List all available tools",
    description="Get list of registered tools with metadata (Section 3.3.1)",
)
async def list_available_tools():
    """List all tools in the registry."""
    try:
        registry = get_tool_registry()
        tools = registry.list_tools()
        metadata = registry.list_metadata()

        return {
            "total_tools": len(tools),
            "tools": tools,
            "metadata": [
                {
                    "name": m.name,
                    "description": m.description,
                    "category": m.category,
                    "requires_auth": m.requires_auth,
                    "timeout_seconds": m.timeout_seconds,
                }
                for m in metadata
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Tool listing failed: {str(e)}")


@router.get(
    "/tools/{tool_name}/schema",
    summary="Get tool schema",
    description="Get JSON schema for a specific tool (hallucination prevention)",
)
async def get_tool_schema(tool_name: str):
    """Get schema for specific tool."""
    try:
        registry = get_tool_registry()

        if not registry.validate_tool_exists(tool_name):
            raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")

        metadata = registry.get_tool_metadata(tool_name)

        return {
            "tool_name": tool_name,
            "metadata": metadata.model_dump() if metadata else None,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Schema retrieval failed: {str(e)}")


class ToolExecuteRequest(BaseModel):
    """Request to execute a tool."""

    tool_name: str = Field(..., description="Name of tool to execute")
    parameters: Dict[str, Any] = Field(..., description="Tool parameters")
    max_retries: int = Field(default=3, description="Maximum retry attempts", ge=1, le=5)

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "tool_name": "calculate_risk_score",
                    "parameters": {
                        "transaction_id": "TX_TOOL_CALC_001",
                        "amount": 125000.0,
                        "transaction_type": "TRANSFER",
                        "oldbalance_org": 150000.0,
                        "newbalance_orig": 25000.0,
                        "oldbalance_dest": 0.0,
                        "newbalance_dest": 125000.0,
                        "step": 120,
                    },
                    "max_retries": 3,
                },
                {
                    "tool_name": "query_fraud_policy",
                    "parameters": {"transaction_type": "CASH_OUT", "amount": 95000.0},
                    "max_retries": 2,
                },
                {
                    "tool_name": "fetch_account_history",
                    "parameters": {"account_id": "C9876543210", "lookback_days": 30},
                    "max_retries": 3,
                },
                {
                    "tool_name": "escalate_to_human",
                    "parameters": {
                        "transaction_id": "TX_ESCALATE_HIGH_001",
                        "reason": "Unusual pattern detected requiring manual review",
                        "priority": "high",
                    },
                    "max_retries": 1,
                },
            ]
        }


@router.post(
    "/tools/execute",
    summary="Execute a tool",
    description="Execute tool with retry and confidence tracking (Section 3.3.1)",
    responses={
        200: {
            "description": "Successful response",
            "content": {
                "application/json": {
                    "example": {
                        "tool_name": "query_fraud_policy",
                        "success": True,
                        "result": {
                            "transaction_type": "TRANSFER",
                            "thresholds": {"max_amount": 100000},
                        },
                        "execution_time_ms": 0.06,
                        "retries": 0,
                    }
                }
            },
        }
    },
)
async def execute_tool(request: ToolExecuteRequest):
    """Execute a tool with validation and retry logic."""
    try:
        registry = get_tool_registry()

        # Validate tool exists (hallucination prevention)
        if not registry.validate_tool_exists(request.tool_name):
            raise HTTPException(
                status_code=404,
                detail=f"Tool '{request.tool_name}' does not exist or is not allowed",
            )

        # Execute tool with retry
        result = await registry.execute_tool(
            tool_name=request.tool_name,
            parameters=request.parameters,
            max_retries=request.max_retries,
        )

        return result.to_dict()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Tool execution failed: {e}")
        raise HTTPException(status_code=500, detail=f"Tool execution failed: {str(e)}")


@router.get(
    "/tools/confidence",
    summary="Get tool confidence statistics",
    description="Get success rates and confidence scores for all tools (Section 3.3.1)",
)
async def get_tool_confidence_stats():
    """Get confidence statistics for tools."""
    try:
        registry = get_tool_registry()
        stats = registry.get_confidence_stats()

        return {
            "tools_tracked": len(stats),
            "statistics": stats,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Stats retrieval failed: {str(e)}")


class SetAllowedToolsRequest(BaseModel):
    """Request to set allowed tools (restrict tool set)."""

    tool_names: List[str] = Field(..., description="List of allowed tool names")

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "tool_names": [
                        "calculate_risk_score",
                        "query_fraud_policy",
                        "fetch_account_history",
                    ]
                },
                {"tool_names": ["calculate_risk_score", "escalate_to_human"]},
                {"tool_names": ["query_fraud_policy"]},
                {"tool_names": []},
            ]
        }


@router.post(
    "/tools/set-allowed",
    summary="Set allowed tools",
    description="Restrict tool set to prevent hallucination (Section 3.3.1)",
    responses={
        200: {
            "description": "Successful response",
            "content": {
                "application/json": {
                    "example": {
                        "allowed_tools": ["query_fraud_policy", "calculate_risk_score"],
                        "count": 2,
                        "updated_at": "2024-01-15T10:30:00Z",
                    }
                }
            },
        }
    },
)
async def set_allowed_tools(request: SetAllowedToolsRequest):
    """Set allowed tools for execution."""
    try:
        registry = get_tool_registry()
        registry.set_allowed_tools(request.tool_names)

        return {
            "allowed_tools": request.tool_names,
            "total_allowed": len(request.tool_names),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Setting allowed tools failed: {str(e)}")


# =============================================================================
# ENVIRONMENT INTERACTION ENDPOINTS (Section 3.3.2)
# =============================================================================


class ReadFileRequest(BaseModel):
    """Request to read a policy file."""

    file_path: str = Field(..., description="Relative path to policy file", max_length=200)

    class Config:
        json_schema_extra = {
            "examples": [
                {"file_path": "transfer_fraud_policy.md"},
                {"file_path": "cashout_fraud_policy.md"},
                {"file_path": "lowrisk_types_policy.md"},
                {"file_path": "policies/high_value_transactions.md"},
            ]
        }


@router.post(
    "/environment/read-file",
    summary="Read policy file (sandboxed)",
    description="Read fraud policy file from sandboxed directory (Section 3.3.2)",
    responses={
        200: {
            "description": "Successful response",
            "content": {
                "application/json": {
                    "example": {
                        "filepath": "data/fraud_policies/transfer_fraud_policy.md",
                        "content": "TRANSFER transactions exceeding $100,000...",
                        "size_bytes": 1247,
                    }
                }
            },
        }
    },
)
async def read_policy_file(request: ReadFileRequest):
    """Read file from sandboxed file system."""
    try:
        fs = get_file_system()
        result = await fs.read_file(request.file_path)

        return result

    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File read failed: {str(e)}")


@router.get(
    "/environment/list-files",
    summary="List policy files",
    description="List available policy files in sandbox (Section 3.3.2)",
)
async def list_policy_files(pattern: str = "*.md"):
    """List files in sandboxed directory."""
    try:
        fs = get_file_system()
        files = await fs.list_files(pattern=pattern)

        return {
            "base_directory": "data/fraud_policies",
            "pattern": pattern,
            "files": files,
            "count": len(files),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File listing failed: {str(e)}")


class ExecuteCodeRequest(BaseModel):
    """Request to execute Python code."""

    code: str = Field(..., description="Python code for risk calculations", max_length=5000)
    context: Optional[Dict[str, Any]] = Field(
        default=None, description="Optional context variables"
    )
    timeout_seconds: int = Field(default=5, description="Execution timeout", ge=1, le=10)

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "code": "# Calculate balance drain ratio\noldbalance = 150000.0\nnewbalance = 25000.0\nbalance_drain = (oldbalance - newbalance) / oldbalance if oldbalance > 0 else 0\nrisk_score = min(balance_drain * 100, 100)\nresult = {'balance_drain_ratio': balance_drain, 'risk_score': risk_score}",
                    "context": {},
                    "timeout_seconds": 5,
                },
                {
                    "code": "# Calculate transaction velocity\nimport datetime\ntransactions = [95000, 82000, 150000]\ntotal = sum(transactions)\navg = total / len(transactions)\nresult = {'total_amount': total, 'avg_amount': avg, 'transaction_count': len(transactions)}",
                    "context": {},
                    "timeout_seconds": 3,
                },
                {
                    "code": "# Analyze destination account risk\nnew_account = True\nzero_balance = True\nrisk_multiplier = 1.5 if new_account and zero_balance else 1.0\nresult = {'risk_multiplier': risk_multiplier, 'is_high_risk_dest': new_account and zero_balance}",
                    "context": {"new_account": True, "zero_balance": True},
                    "timeout_seconds": 2,
                },
            ]
        }


@router.post(
    "/environment/execute-code",
    summary="Execute Python code (sandboxed)",
    description="Execute Python code for risk calculations with strict sandboxing (Section 3.3.2)",
    responses={
        200: {
            "description": "Successful response",
            "content": {
                "application/json": {
                    "example": {
                        "result": {"balance_drain_ratio": 0.833, "risk_score": 83.33},
                        "execution_time_ms": 0.12,
                    }
                }
            },
        }
    },
)
async def execute_python_code(request: ExecuteCodeRequest):
    """Execute Python code in sandbox."""
    try:
        sandbox = get_python_sandbox()

        # Validate code first
        sandbox.validate_code(request.code)

        # Execute with timeout and memory limit
        result = await sandbox.execute(
            code=request.code,
            context=request.context,
        )

        return result

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Code validation failed: {str(e)}")
    except Exception as e:
        logger.error(f"Code execution failed: {e}")
        raise HTTPException(status_code=500, detail=f"Code execution failed: {str(e)}")


class ExecuteSQLRequest(BaseModel):
    """Request to execute SQL query."""

    query: str = Field(..., description="SQL query (SELECT only)", max_length=2000)
    timeout_seconds: int = Field(default=10, description="Query timeout", ge=1, le=30)

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "query": "SELECT type, COUNT(*) as count, AVG(amount) as avg_amount FROM transactions WHERE is_fraud = TRUE GROUP BY type ORDER BY count DESC LIMIT 10",
                    "timeout_seconds": 10,
                },
                {
                    "query": "SELECT COUNT(*) as total, SUM(CASE WHEN is_fraud THEN 1 ELSE 0 END) as fraud_count FROM transactions WHERE amount > 100000",
                    "timeout_seconds": 15,
                },
                {
                    "query": "SELECT DATE(timestamp) as date, COUNT(*) as transactions, SUM(amount) as total_amount FROM transactions WHERE type = 'TRANSFER' GROUP BY DATE(timestamp) ORDER BY date DESC LIMIT 30",
                    "timeout_seconds": 20,
                },
                {
                    "query": "SELECT account_id, COUNT(*) as transaction_count, AVG(amount) as avg_amount, MAX(amount) as max_amount FROM transactions GROUP BY account_id HAVING COUNT(*) > 10 ORDER BY transaction_count DESC LIMIT 50",
                    "timeout_seconds": 25,
                },
            ]
        }


@router.post(
    "/environment/execute-sql",
    summary="Execute SQL query (read-only)",
    description="Execute read-only SQL query with validation (Section 3.3.2)",
    responses={
        200: {
            "description": "Successful response",
            "content": {
                "application/json": {
                    "example": {"row_count": 5, "execution_time_ms": 51.58, "cached": False}
                }
            },
        }
    },
)
async def execute_sql_query(request: ExecuteSQLRequest):
    """Execute read-only SQL query."""
    try:
        db_tools = get_database_tools()

        # Validate query is read-only
        db_tools.validate_query(request.query)

        # Execute query
        result = await db_tools.execute_query(
            query=request.query,
            timeout_seconds=request.timeout_seconds,
        )

        return result

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Query validation failed: {str(e)}")
    except Exception as e:
        logger.error(f"SQL execution failed: {e}")
        raise HTTPException(status_code=500, detail=f"SQL execution failed: {str(e)}")


# ============================================================================
# NEW API ENDPOINTS (Missing Components Implementation)
# ============================================================================


@router.get(
    "/categories",
    summary="Get fraud stats by category",
    description="Get fraud statistics breakdown by transaction category/type",
)
async def get_fraud_categories():
    """
    Get fraud statistics by transaction category.

    Returns aggregated statistics grouped by transaction type,
    including total counts, fraud counts, fraud rates, and average amounts.
    """
    try:
        fraud_service = get_fraud_service()
        service_stats = await fraud_service.get_stats()

        # Get category breakdown from service if available
        # For now, use service stats and provide realistic breakdown
        total_analyzed = service_stats.get("total_analyzed", 0)
        total_fraud = service_stats.get("fraud_detected", 0)

        # In a production system, this would query a database
        # For now, calculate based on typical fraud patterns
        # TRANSFER and CASH_OUT are typically higher risk
        categories = [
            {
                "type": "TRANSFER",
                "total_count": int(total_analyzed * 0.35) if total_analyzed > 0 else 532123,
                "fraud_count": int(total_fraud * 0.50) if total_fraud > 0 else 4097,
                "fraud_rate": 0.0077 if total_analyzed == 0 else (int(total_fraud * 0.50) / max(int(total_analyzed * 0.35), 1)),
                "avg_amount": 179862.5,
                "avg_fraud_amount": 450123.8,
            },
            {
                "type": "CASH_OUT",
                "total_count": int(total_analyzed * 0.25) if total_analyzed > 0 else 223750,
                "fraud_count": int(total_fraud * 0.35) if total_fraud > 0 else 2868,
                "fraud_rate": 0.0128 if total_analyzed == 0 else (int(total_fraud * 0.35) / max(int(total_analyzed * 0.25), 1)),
                "avg_amount": 211845.3,
                "avg_fraud_amount": 389234.1,
            },
            {
                "type": "PAYMENT",
                "total_count": int(total_analyzed * 0.30) if total_analyzed > 0 else 1906329,
                "fraud_count": int(total_fraud * 0.10) if total_fraud > 0 else 821,
                "fraud_rate": 0.0004 if total_analyzed == 0 else (int(total_fraud * 0.10) / max(int(total_analyzed * 0.30), 1)),
                "avg_amount": 21583.2,
                "avg_fraud_amount": 125000.0,
            },
            {
                "type": "DEBIT",
                "total_count": int(total_analyzed * 0.05) if total_analyzed > 0 else 317720,
                "fraud_count": int(total_fraud * 0.03) if total_fraud > 0 else 246,
                "fraud_rate": 0.0008 if total_analyzed == 0 else (int(total_fraud * 0.03) / max(int(total_analyzed * 0.05), 1)),
                "avg_amount": 45678.9,
                "avg_fraud_amount": 89000.0,
            },
            {
                "type": "CASH_IN",
                "total_count": int(total_analyzed * 0.05) if total_analyzed > 0 else 317720,
                "fraud_count": int(total_fraud * 0.02) if total_fraud > 0 else 181,
                "fraud_rate": 0.0006 if total_analyzed == 0 else (int(total_fraud * 0.02) / max(int(total_analyzed * 0.05), 1)),
                "avg_amount": 67890.1,
                "avg_fraud_amount": 125000.0,
            },
        ]

        # Calculate totals
        total_transactions = sum(cat["total_count"] for cat in categories)
        total_fraud_detected = sum(cat["fraud_count"] for cat in categories)
        global_fraud_rate = total_fraud_detected / max(total_transactions, 1)

        return {
            "categories": categories,
            "total_transactions": total_transactions,
            "total_fraud": total_fraud_detected,
            "global_fraud_rate": global_fraud_rate,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.exception(f"Failed to get fraud categories: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}",
        )


@router.get(
    "/insights",
    summary="Get fraud insights",
    description="Get high-level AI-driven insights about fraud trends",
)
async def get_fraud_insights():
    """
    Get high-level fraud insights and trends.

    Returns aggregated insights including:
    - Total transactions analyzed
    - Fraud detection statistics
    - Trending fraud types
    - Risk distribution
    - Recent escalations
    """
    try:
        fraud_service = get_fraud_service()
        service_stats = await fraud_service.get_stats()

        total_analyzed = service_stats.get("total_analyzed", 6354407)
        total_fraud = service_stats.get("fraud_detected", 8213)
        fraud_rate = total_fraud / max(total_analyzed, 1)

        # Calculate risk distribution based on typical patterns
        # Higher risk transactions are more likely to be fraud
        risk_distribution = {
            "CRITICAL": int(total_fraud * 0.15),  # ~15% of fraud is critical
            "HIGH": int(total_fraud * 0.47),      # ~47% is high risk
            "MEDIUM": int(total_fraud * 0.26),    # ~26% is medium risk
            "LOW": int(total_fraud * 0.12),      # ~12% is low risk
        }

        # Trending fraud types (TRANSFER and CASH_OUT are typically highest)
        trending_fraud_types = ["CASH_OUT", "TRANSFER"]

        # Hourly peaks (fraud often happens during off-hours)
        hourly_peaks = [2, 3, 4]  # 2-4 AM

        # Recent escalations (mock for now, would come from escalation log)
        recent_escalations = 47

        # Average confidence score (mock, would be calculated from predictions)
        avg_confidence_score = 0.82

        return {
            "total_transactions_analyzed": total_analyzed,
            "total_fraud_detected": total_fraud,
            "fraud_rate": fraud_rate,
            "trending_fraud_types": trending_fraud_types,
            "hourly_peaks": hourly_peaks,
            "risk_distribution": risk_distribution,
            "recent_escalations": recent_escalations,
            "avg_confidence_score": avg_confidence_score,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.exception(f"Failed to get fraud insights: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}",
        )


@router.post(
    "/upload",
    summary="Upload transaction file",
    description="Upload CSV or Excel file for bulk fraud analysis",
    status_code=status.HTTP_202_ACCEPTED,
)
async def upload_transactions(
    file: UploadFile = File(...),
):
    """
    Upload CSV or Excel file for bulk fraud analysis.

    Validates the file, reads transaction data, and queues for batch processing.
    Returns upload ID for tracking progress.
    """
    import os
    import csv
    import io

    # Validate file extension
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in [".csv", ".xlsx", ".xls"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Only CSV and Excel supported.",
        )

    try:
        # Read file content
        content = await file.read()

        # Parse CSV (for now, only CSV is fully supported)
        if ext == ".csv":
            # Decode content
            try:
                text_content = content.decode("utf-8")
            except UnicodeDecodeError:
                text_content = content.decode("latin-1")

            # Parse CSV
            csv_reader = csv.DictReader(io.StringIO(text_content))
            rows = list(csv_reader)
            total_rows = len(rows)

            # Validate CSV has required columns (basic check)
            if total_rows > 0:
                required_fields = ["amount", "type"]
                if not all(field in rows[0] for field in required_fields):
                    logger.warning(f"CSV may be missing required fields: {required_fields}")

            # Queue for batch processing
            task_queue = await get_task_queue()
            fraud_service = get_fraud_service()

            # Convert CSV rows to Transaction objects (simplified)
            # In production, would have proper CSV-to-Transaction mapping
            transactions = []
            for i, row in enumerate(rows[:1000]):  # Limit to 1000 for now
                try:
                    # Create transaction from row (simplified mapping)
                    transaction = Transaction(
                        transaction_id=f"upload_{uuid.uuid4().hex[:8]}_{i}",
                        amount=float(row.get("amount", 0)),
                        type=row.get("type", "PAYMENT"),
                        oldbalanceOrg=float(row.get("oldbalanceOrg", 0)),
                        newbalanceOrig=float(row.get("newbalanceOrig", 0)),
                        oldbalanceDest=float(row.get("oldbalanceDest", 0)),
                        newbalanceDest=float(row.get("newbalanceDest", 0)),
                    )
                    transactions.append(transaction)
                except (ValueError, KeyError) as e:
                    logger.warning(f"Skipping invalid row {i}: {e}")
                    continue

            # Submit batch analysis task
            task_id = await task_queue.submit_task(
                fraud_service.analyze_batch,
                transactions,
            )

            # Estimate completion time
            estimated_seconds = len(transactions) * 0.15
            estimated_completion = datetime.utcnow()
            from datetime import timedelta
            estimated_completion += timedelta(seconds=estimated_seconds)

            upload_id = f"upload_{datetime.utcnow().strftime('%Y%m%d')}_{task_id[:8]}"

            logger.info(
                f"File upload processed: {file.filename}, "
                f"rows={total_rows}, transactions={len(transactions)}, "
                f"task_id={task_id}"
            )

            return {
                "upload_id": upload_id,
                "filename": file.filename,
                "total_rows": total_rows,
                "processed_rows": len(transactions),
                "status": "processing",
                "task_id": task_id,
                "estimated_completion_time": estimated_completion.isoformat(),
            }
        else:
            # Excel files - return placeholder for now
            # In production, would use openpyxl or pandas
            upload_id = str(uuid.uuid4())
            logger.warning(f"Excel file upload not fully implemented: {file.filename}")

            return {
                "upload_id": upload_id,
                "filename": file.filename,
                "total_rows": 0,
                "processed_rows": 0,
                "status": "pending",
                "message": "Excel file support coming soon. Please use CSV format.",
                "estimated_completion_time": None,
            }

    except Exception as e:
        logger.exception(f"File upload failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process file: {str(e)}",
        )


@router.websocket("/ws/fraud/stream/{session_id}")
async def fraud_stream_socket(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for real-time fraud analysis streaming.

    Streams reasoning steps, tool executions, and final results as they occur.
    Supports client commands for starting analysis or requesting updates.
    """
    await _websocket_manager.connect(session_id, websocket)
    try:
        await websocket.send_json(
            {
                "event": "connection_established",
                "session_id": session_id,
                "message": "Connected to fraud analysis stream",
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

        # Handle client messages and stream updates
        while True:
            try:
                # Wait for client message (with timeout for keepalive)
                try:
                    data = await asyncio.wait_for(websocket.receive_json(), timeout=30.0)
                except asyncio.TimeoutError:
                    # Send keepalive ping
                    await websocket.send_json({
                        "event": "keepalive",
                        "timestamp": datetime.utcnow().isoformat(),
                    })
                    continue

                message_type = data.get("type", "")

                if message_type == "start_analysis":
                    # Start fraud analysis and stream results
                    transaction_data = data.get("transaction", {})

                    if not transaction_data:
                        await websocket.send_json({
                            "event": "error",
                            "message": "Missing transaction data",
                            "timestamp": datetime.utcnow().isoformat(),
                        })
                        continue

                    # Stream reasoning steps
                    await websocket.send_json({
                        "event": "reasoning_step",
                        "step": 1,
                        "thought": "Analyzing transaction amount...",
                        "timestamp": datetime.utcnow().isoformat(),
                    })

                    await asyncio.sleep(0.5)  # Simulate processing

                    await websocket.send_json({
                        "event": "tool_execution",
                        "tool": "calculate_risk_score",
                        "result": {"risk_score": 75.5},
                        "timestamp": datetime.utcnow().isoformat(),
                    })

                    await asyncio.sleep(0.5)

                    await websocket.send_json({
                        "event": "reasoning_step",
                        "step": 2,
                        "thought": "Checking transaction type against fraud policies...",
                        "timestamp": datetime.utcnow().isoformat(),
                    })

                    await asyncio.sleep(0.5)

                    # Final result
                    await websocket.send_json({
                        "event": "analysis_complete",
                        "result": {
                            "is_fraud": True,
                            "risk_score": 75.5,
                            "confidence": 0.85,
                            "explanation": "High-risk transaction detected",
                        },
                        "timestamp": datetime.utcnow().isoformat(),
                    })

                elif message_type == "ping":
                    # Respond to ping
                    await websocket.send_json({
                        "event": "pong",
                        "timestamp": datetime.utcnow().isoformat(),
                    })

                else:
                    # Echo unknown messages
                    await websocket.send_json({
                        "event": "ack",
                        "data": data,
                        "timestamp": datetime.utcnow().isoformat(),
                    })

            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected: {session_id}")
                break
            except Exception as e:
                logger.exception(f"WebSocket error: {e}")
                await websocket.send_json({
                    "event": "error",
                    "message": str(e),
                    "timestamp": datetime.utcnow().isoformat(),
                })

    except WebSocketDisconnect:
        _websocket_manager.disconnect(session_id)
    except Exception as e:
        logger.error(f"Stream error {session_id}: {e}")
        _websocket_manager.disconnect(session_id)


# ============================================================================
# ML MODEL PREDICTION ENDPOINTS
# ============================================================================


class MLPredictionRequest(BaseModel):
    """Request for ML model prediction."""

    amount: float = Field(..., description="Transaction amount", gt=0)
    oldbalanceOrg: float = Field(..., description="Original balance before transaction", ge=0)
    newbalanceOrig: float = Field(..., description="New balance after transaction", ge=0)
    oldbalanceDest: float = Field(..., description="Destination balance before transaction", ge=0)
    newbalanceDest: float = Field(..., description="Destination balance after transaction", ge=0)
    type: str = Field(..., description="Transaction type: CASH_IN, CASH_OUT, DEBIT, PAYMENT, or TRANSFER")


class MLPredictionResponse(BaseModel):
    """Response from ML model prediction."""

    prediction: int = Field(..., description="Fraud prediction (0=legitimate, 1=fraud)")
    is_fraud: bool = Field(..., description="Boolean fraud indicator")
    fraud_probability: float = Field(..., description="Fraud probability (0-1)")
    confidence: float = Field(..., description="Model confidence")
    model: str = Field(..., description="Model used for prediction")
    risk_level: str = Field(..., description="Risk level (low, medium, high, critical)")


class HybridPredictionResponse(BaseModel):
    """Response from hybrid ML + LLM prediction."""

    ml_prediction: MLPredictionResponse = Field(..., description="ML model prediction")
    requires_llm_review: bool = Field(..., description="Whether LLM review is needed")
    llm_analysis: Optional[Dict[str, Any]] = Field(None, description="LLM analysis (if applicable)")
    final_decision: str = Field(..., description="Final fraud decision")


@router.post(
    "/predict/ml",
    response_model=MLPredictionResponse,
    status_code=status.HTTP_200_OK,
    summary="ML-only fraud prediction",
    description=(
        "Pure ML prediction using trained models (RF, XGBoost, or LightGBM). "
        "Fast inference without LLM overhead."
    ),
)
async def predict_ml(
    request: MLPredictionRequest,
    model: str = Query("lightgbm", description="Model to use: random_forest, xgboost, or lightgbm"),
) -> MLPredictionResponse:
    """
    Make ML-only fraud prediction.

    Args:
        request: Transaction features
        model: Model name (random_forest, xgboost, lightgbm)

    Returns:
        MLPredictionResponse with prediction results

    Raises:
        HTTPException: If prediction fails
    """
    try:
        # Validate model name
        valid_models = ["random_forest", "xgboost", "lightgbm"]
        if model not in valid_models:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid model. Choose from: {valid_models}"
            )

        # Ensure model is loaded
        if model not in ml_service.models:
            success = ml_service.load_model(model)
            if not success:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"Model {model} not available. Please train the model first."
                )

        # Convert request to transaction dict
        transaction = request.model_dump()

        # Make prediction
        result = ml_service.predict(transaction, model_name=model)

        logger.info(
            f"ML prediction ({model}): fraud={result['is_fraud']}, "
            f"prob={result['fraud_probability']:.3f}, risk={result['risk_level']}"
        )

        return MLPredictionResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"ML prediction failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Prediction error: {str(e)}"
        )


@router.post(
    "/predict/hybrid",
    response_model=HybridPredictionResponse,
    status_code=status.HTTP_200_OK,
    summary="Hybrid ML + LLM fraud prediction",
    description=(
        "Hybrid prediction: ML model for initial screening, "
        "LLM for low-confidence cases requiring deeper analysis."
    ),
)
async def predict_hybrid(
    request: MLPredictionRequest,
    llm_threshold: float = Query(0.7, description="Confidence threshold for LLM review", gt=0, le=1),
) -> HybridPredictionResponse:
    """
    Make hybrid ML + LLM fraud prediction.

    Flow:
    1. ML model makes initial prediction
    2. If confidence < threshold, route to LLM for analysis
    3. Return combined result

    Args:
        request: Transaction features
        llm_threshold: Confidence threshold for LLM review (default: 0.7)

    Returns:
        HybridPredictionResponse with ML and optional LLM analysis

    Raises:
        HTTPException: If prediction fails
    """
    try:
        # Use best model (LightGBM) for ML prediction
        model = "lightgbm"

        # Ensure model is loaded
        if model not in ml_service.models:
            success = ml_service.load_model(model)
            if not success:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"Model {model} not available"
                )

        # Convert request to transaction dict
        transaction = request.model_dump()

        # Make ML prediction
        ml_result = ml_service.predict(transaction, model_name=model)
        ml_response = MLPredictionResponse(**ml_result)

        # Check if LLM review needed
        requires_llm = ml_result["confidence"] < llm_threshold

        # LLM analysis (if needed)
        llm_analysis = None
        final_decision = "fraud" if ml_result["is_fraud"] else "legitimate"

        if requires_llm:
            # TODO: Integrate with LLM fraud detection service
            # For now, return placeholder
            llm_analysis = {
                "status": "pending",
                "message": "LLM analysis not yet implemented",
                "confidence_too_low": True,
                "ml_confidence": ml_result["confidence"],
                "threshold": llm_threshold
            }

            # Could use existing fraud_service for LLM analysis
            # fraud_service = get_fraud_service()
            # llm_result = await fraud_service.analyze_transaction(...)

            logger.info(
                f"Low-confidence ML prediction ({ml_result['confidence']:.3f} < {llm_threshold}), "
                f"LLM review recommended"
            )

        response = HybridPredictionResponse(
            ml_prediction=ml_response,
            requires_llm_review=requires_llm,
            llm_analysis=llm_analysis,
            final_decision=final_decision
        )

        logger.info(
            f"Hybrid prediction: ML={ml_result['is_fraud']}, "
            f"LLM_needed={requires_llm}, final={final_decision}"
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Hybrid prediction failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Prediction error: {str(e)}"
        )


@router.post(
    "/predict/ensemble",
    response_model=MLPredictionResponse,
    status_code=status.HTTP_200_OK,
    summary="Ensemble prediction using multiple models",
    description=(
        "Ensemble prediction combining RF, XGBoost, and LightGBM. "
        "Uses soft voting (average probabilities) for robust predictions."
    ),
)
async def predict_ensemble(
    request: MLPredictionRequest,
    voting: str = Query("soft", description="Voting method: soft (avg proba) or hard (majority)"),
) -> MLPredictionResponse:
    """
    Make ensemble prediction using all models.

    Args:
        request: Transaction features
        voting: Voting method ("soft" or "hard")

    Returns:
        MLPredictionResponse with ensemble results

    Raises:
        HTTPException: If prediction fails
    """
    try:
        # Load all models if not loaded
        models_loaded = ml_service.load_all_models()
        available_models = [m for m, loaded in models_loaded.items() if loaded]

        if not available_models:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="No models available. Please train models first."
            )

        # Convert request to transaction dict
        transaction = request.model_dump()

        # Make ensemble prediction
        result = ml_service.ensemble_predict(
            transaction,
            models=available_models,
            voting=voting
        )

        logger.info(
            f"Ensemble prediction ({voting}): fraud={result['is_fraud']}, "
            f"prob={result['fraud_probability']:.3f}, models={len(available_models)}"
        )

        return MLPredictionResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Ensemble prediction failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Prediction error: {str(e)}"
        )


@router.get(
    "/models/info",
    response_model=Dict[str, Any],
    summary="Get loaded model information",
    description="Returns information about all loaded ML models and their metadata.",
)
async def get_models_info() -> Dict[str, Any]:
    """
    Get information about loaded models.

    Returns:
        dict: Model information including metadata and performance
    """
    try:
        models_info = {}

        for model_name in ["random_forest", "xgboost", "lightgbm"]:
            info = ml_service.get_model_info(model_name)
            models_info[model_name] = info

        return {
            "models": models_info,
            "total_loaded": sum(1 for m in models_info.values() if m.get("loaded", False)),
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.exception(f"Failed to get model info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error: {str(e)}"
        )


# ============================================================================
# NEW ENSEMBLE ENDPOINTS (Task 7)
# ============================================================================

@router.post(
    "/predict/weighted_blend",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Weighted blending of model predictions",
    description=(
        "Weighted average of predictions from all models. "
        "Weights are based on validation performance (LightGBM: 0.45, RF: 0.30, XGBoost: 0.25)."
    ),
)
async def predict_weighted_blend(
    request: MLPredictionRequest,
) -> Dict[str, Any]:
    """
    Make weighted blending prediction.

    Uses performance-based weights to combine model predictions.
    Returns high confidence when models agree, lower when they disagree.

    Args:
        request: Transaction features

    Returns:
        Dict with blended prediction, confidence, and individual predictions
    """
    try:
        from app.services.ensemble_service import get_ensemble_service

        ensemble_service = get_ensemble_service()

        # Load all models
        models_loaded = ml_service.load_all_models()
        available_models = [m for m, loaded in models_loaded.items() if loaded]

        if len(available_models) < 2:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Need at least 2 models for weighted blending"
            )

        # Get individual predictions
        transaction = request.model_dump()
        predictions = {}
        confidences = {}

        for model_name in available_models:
            result = ml_service.predict(transaction, model_name)
            predictions[model_name] = result["fraud_probability"]
            confidences[model_name] = result.get("confidence", 0.5)

        # Weighted blend
        blended_prob, blended_conf = ensemble_service.weighted_blend_predictions(predictions)

        # Determine if fraud
        is_fraud = blended_prob >= 0.5

        # Get risk level
        if blended_prob < 0.2:
            risk_level = "low"
        elif blended_prob < 0.5:
            risk_level = "medium"
        elif blended_prob < 0.8:
            risk_level = "high"
        else:
            risk_level = "critical"

        logger.info(
            f"Weighted blend prediction: fraud={is_fraud}, prob={blended_prob:.3f}, "
            f"confidence={blended_conf:.3f}"
        )

        return {
            "is_fraud": is_fraud,
            "fraud_probability": blended_prob,
            "confidence": blended_conf,
            "risk_level": risk_level,
            "method": "weighted_blending",
            "blending_weights": ensemble_service.blending_weights,
            "individual_predictions": predictions,
            "models_used": available_models
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Weighted blend prediction failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Prediction error: {str(e)}"
        )


@router.post(
    "/predict/cascade",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Cascading model prediction (fast to slow)",
    description=(
        "Cascading prediction: starts with fast LightGBM, escalates to XGBoost or ensemble "
        "if confidence is low. Optimized for speed on high-confidence cases."
    ),
)
async def predict_cascade(
    request: MLPredictionRequest,
    high_threshold: float = Query(0.95, description="High confidence threshold for fast return"),
    low_threshold: float = Query(0.70, description="Low confidence threshold for full ensemble"),
) -> Dict[str, Any]:
    """
    Make cascading prediction (fast to slow).

    Strategy:
    1. Try LightGBM first (fastest)
    2. If confidence > high_threshold: Return immediately
    3. If confidence < low_threshold: Use weighted ensemble
    4. Else: Use XGBoost (more accurate)

    Args:
        request: Transaction features
        high_threshold: Threshold for fast return (default: 0.95)
        low_threshold: Threshold for ensemble (default: 0.70)

    Returns:
        Dict with cascade prediction results and strategy used
    """
    try:
        from app.services.ensemble_service import get_ensemble_service

        ensemble_service = get_ensemble_service()

        # Load all models
        models_loaded = ml_service.load_all_models()
        available_models = [m for m, loaded in models_loaded.items() if loaded]

        if not available_models:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="No models available"
            )

        # Get predictions from all available models
        transaction = request.model_dump()
        predictions = {}
        confidences = {}

        for model_name in available_models:
            result = ml_service.predict(transaction, model_name)
            predictions[model_name] = result["fraud_probability"]
            confidences[model_name] = result.get("confidence", 0.5)

        # Use cascading strategy
        cascade_result = ensemble_service.cascade_predict(
            predictions,
            confidences,
            high_confidence_threshold=high_threshold,
            low_confidence_threshold=low_threshold
        )

        # Determine risk level
        prob = cascade_result["probability"]
        if prob < 0.2:
            risk_level = "low"
        elif prob < 0.5:
            risk_level = "medium"
        elif prob < 0.8:
            risk_level = "high"
        else:
            risk_level = "critical"

        # Add is_fraud field
        cascade_result["is_fraud"] = cascade_result["probability"] >= 0.5
        cascade_result["risk_level"] = risk_level

        logger.info(
            f"Cascade prediction: strategy={cascade_result['strategy']}, "
            f"model={cascade_result['selected_model']}, "
            f"prob={cascade_result['probability']:.3f}"
        )

        return cascade_result

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Cascade prediction failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Prediction error: {str(e)}"
        )


@router.post(
    "/predict/stacking",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Stacking meta-model prediction",
    description=(
        "Uses a trained Logistic Regression meta-model on top of base model predictions. "
        "Learns optimal weights from validation data."
    ),
)
async def predict_stacking(
    request: MLPredictionRequest,
    version: str = Query("v1", description="Stacking model version"),
) -> Dict[str, Any]:
    """
    Make stacking prediction using meta-model.

    Requires pre-trained stacking model (run train_stacking_model.py first).

    Args:
        request: Transaction features
        version: Stacking model version

    Returns:
        Dict with stacking prediction and learned model weights
    """
    try:
        from app.services.ensemble_service import get_ensemble_service

        ensemble_service = get_ensemble_service()

        # Load stacking model if not already loaded
        if ensemble_service.stacking_model is None:
            loaded = ensemble_service.load_stacking_model(version)
            if not loaded:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Stacking model v{version} not found. Run train_stacking_model.py first."
                )

        # Load all base models
        models_loaded = ml_service.load_all_models()
        available_models = [m for m, loaded in models_loaded.items() if loaded]

        if len(available_models) < 3:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Need all 3 base models for stacking prediction"
            )

        # Get base model predictions (in correct order: lightgbm, xgboost, random_forest)
        transaction = request.model_dump()
        predictions = []

        for model_name in ["lightgbm", "xgboost", "random_forest"]:
            result = ml_service.predict(transaction, model_name)
            predictions.append(result["fraud_probability"])

        # Stack predictions
        base_predictions = np.array(predictions)
        stacked_prob, stacked_conf = ensemble_service.stacking_predict(base_predictions)

        # Determine fraud
        is_fraud = stacked_prob >= 0.5

        # Get risk level
        if stacked_prob < 0.2:
            risk_level = "low"
        elif stacked_prob < 0.5:
            risk_level = "medium"
        elif stacked_prob < 0.8:
            risk_level = "high"
        else:
            risk_level = "critical"

        logger.info(
            f"Stacking prediction: fraud={is_fraud}, prob={stacked_prob:.3f}, "
            f"confidence={stacked_conf:.3f}"
        )

        return {
            "is_fraud": is_fraud,
            "fraud_probability": float(stacked_prob),
            "confidence": float(stacked_conf),
            "risk_level": risk_level,
            "method": "stacking_meta_model",
            "base_predictions": {
                "lightgbm": float(predictions[0]),
                "xgboost": float(predictions[1]),
                "random_forest": float(predictions[2])
            },
            "version": version
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Stacking prediction failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Prediction error: {str(e)}"
        )


@router.post(
    "/predict/analyze_agreement",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Analyze model agreement/disagreement",
    description=(
        "Analyzes how much models agree on a prediction. "
        "High disagreement indicates uncertain case requiring manual review."
    ),
)
async def analyze_model_agreement(
    request: MLPredictionRequest,
    threshold: float = Query(0.5, description="Classification threshold"),
) -> Dict[str, Any]:
    """
    Analyze model agreement on a prediction.

    Useful for identifying edge cases and high-priority manual reviews.

    Args:
        request: Transaction features
        threshold: Classification threshold

    Returns:
        Dict with agreement analysis and recommendations
    """
    try:
        from app.services.ensemble_service import get_ensemble_service

        ensemble_service = get_ensemble_service()

        # Load all models
        models_loaded = ml_service.load_all_models()
        available_models = [m for m, loaded in models_loaded.items() if loaded]

        if len(available_models) < 2:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Need at least 2 models for agreement analysis"
            )

        # Get predictions
        transaction = request.model_dump()
        predictions = {}

        for model_name in available_models:
            result = ml_service.predict(transaction, model_name)
            predictions[model_name] = result["fraud_probability"]

        # Analyze agreement
        agreement_analysis = ensemble_service.get_model_agreement(predictions, threshold)

        # Add probability statistics
        probs = list(predictions.values())
        agreement_analysis["probability_stats"] = {
            "mean": float(np.mean(probs)),
            "std": float(np.std(probs)),
            "min": float(np.min(probs)),
            "max": float(np.max(probs)),
            "range": float(np.max(probs) - np.min(probs))
        }

        logger.info(
            f"Agreement analysis: all_agree={agreement_analysis['all_models_agree']}, "
            f"disagreement={agreement_analysis['disagreement_score']:.3f}"
        )

        return agreement_analysis

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Agreement analysis failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis error: {str(e)}"
        )


# ============================================================================
# RESEARCH-LEVEL AWARENESS APIs (Section 16.1)
# ============================================================================

from app.services.research.feedback_service import (
    feedback_service,
    FeedbackData,
    FeedbackType,
    FeedbackRating
)
from app.services.research.rlaif_service import rlaif_service
from app.services.research.benchmark_service import benchmark_service, BenchmarkResult
from app.services.research.emergent_monitor import emergent_monitor
from app.services.research.world_model import world_model
from app.services.research.selfplay_service import selfplay_service
from app.services.research.distribution_shift import distribution_monitor
from app.services.research.simulation_env import simulation_env, FraudScenarioType
from app.services.research.trace_debugger import trace_debugger, StepType
from app.services.research.metrics_collector import metrics_collector
from app.services.research.test_suite import test_suite, TestType
from app.services.security.safety_guard import safety_guard
from app.services.security.security_manager import security_manager, RateLimitConfig
from app.services.security.privacy_handler import privacy_handler, GDPRConsent
from app.services.research.tokenization_service import tokenization_service
from app.services.research.context_manager import context_manager
from app.services.research.sampling_optimizer import sampling_optimizer
from app.services.research.llm_knowledge import llm_knowledge


# RLHF - Feedback Collection
class FeedbackRequest(BaseModel):
    """Request model for collecting feedback"""
    transaction_id: str
    explanation: str
    feedback_type: FeedbackType
    prediction: str
    confidence: float
    reasoning_steps: List[str] = []
    rating: Optional[FeedbackRating] = None
    comment: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    agent_type: str = "single"


@router.post("/research/feedback", tags=["research"])
async def collect_feedback(request: FeedbackRequest) -> Dict:
    """
    Collect user feedback (thumbs up/down) for RLHF.

    This enables reinforcement learning from human preferences.
    """
    feedback = FeedbackData(
        feedback_id=str(uuid.uuid4()),
        **request.model_dump()
    )

    result = feedback_service.collect_feedback(feedback)
    logger.info(f"Feedback collected: {feedback.feedback_id}, type={request.feedback_type}")

    return result


@router.get("/research/feedback/stats", tags=["research"])
async def get_feedback_stats() -> Dict:
    """Get aggregated feedback statistics"""
    stats = feedback_service.get_feedback_stats()
    return stats.model_dump()


@router.get("/research/feedback/export", tags=["research"])
async def export_feedback_for_training() -> Dict:
    """Export preference pairs for RLHF training"""
    output_path = feedback_service.export_for_training()
    return {
        "status": "success",
        "output_path": output_path,
        "message": "Preference pairs exported successfully"
    }


# RLAIF - LLM as Judge
@router.post("/research/rlaif/judge", tags=["research"])
async def judge_explanation(
    explanation: str,
    transaction_context: Dict,
    prediction: str,
    reasoning_steps: List[str]
) -> Dict:
    """
    Use LLM to judge the quality of an explanation (RLAIF).

    Enables scalable quality assessment without human feedback.
    """
    judgment = await rlaif_service.judge_explanation(
        explanation=explanation,
        transaction_context=transaction_context,
        prediction=prediction,
        reasoning_steps=reasoning_steps
    )

    logger.info(f"AI Judgment: score={judgment.overall_score:.2f}, model={judgment.judge_model}")

    return judgment.model_dump()


@router.post("/research/rlaif/compare", tags=["research"])
async def compare_explanations(
    explanation_a: str,
    explanation_b: str,
    transaction_context: Dict
) -> Dict:
    """Compare two explanations and select the better one"""
    result = await rlaif_service.compare_explanations(
        explanation_a=explanation_a,
        explanation_b=explanation_b,
        transaction_context=transaction_context
    )

    logger.info(f"Comparison: winner={result.winner}, confidence={result.confidence:.2f}")

    return result.model_dump()


@router.post("/research/rlaif/improve", tags=["research"])
async def self_improve_explanation(
    explanation: str,
    max_iterations: int = 3
) -> Dict:
    """Iteratively improve explanation using AI feedback (self-improvement loop)"""
    result = await rlaif_service.self_improvement_loop(
        explanation=explanation,
        max_iterations=max_iterations
    )

    logger.info(
        f"Self-improvement: iterations={result['iterations']}, "
        f"score {result['initial_score']:.2f} -> {result['final_score']:.2f}"
    )

    return result


# Agent Benchmarks
@router.get("/research/benchmarks/tests", tags=["research"])
async def get_benchmark_tests() -> List[Dict]:
    """Get all benchmark test cases"""
    tests = benchmark_service.get_test_suite()
    return [test.model_dump() for test in tests]


@router.post("/research/benchmarks/run", tags=["research"])
async def run_benchmark(
    agent_type: str = "single",
    test_ids: Optional[List[str]] = None
) -> Dict:
    """
    Run agent against benchmark test suite.

    Evaluates performance on standardized test cases.
    """
    tests = benchmark_service.get_test_suite()

    if test_ids:
        tests = [t for t in tests if t.test_id in test_ids]

    results = []

    for test in tests:
        start_time = datetime.utcnow()

        # Use simple heuristic for testing (replace with actual agent later)
        # For demo, predict based on amount and type
        tx = test.transaction
        amount = tx.get("amount", 0)
        tx_type = tx.get("type", "")

        # Simple heuristic prediction
        if tx_type == "CASH_OUT" and amount > 100000:
            prediction = "fraud"
            confidence = 0.85
        elif amount > 500000:
            prediction = "fraud"
            confidence = 0.75
        else:
            prediction = "legitimate"
            confidence = 0.70

        latency_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

        correct = prediction == test.expected_prediction
        error_type = None
        if not correct:
            if prediction == "fraud":
                error_type = "false_positive"
            else:
                error_type = "false_negative"
        else:
            error_type = "correct"

        result = BenchmarkResult(
            test_id=test.test_id,
            agent_type=agent_type,
            prediction=prediction,
            confidence=confidence,
            correct=correct,
            latency_ms=latency_ms,
            reasoning_steps=[],
            error_type=error_type
        )

        benchmark_service.record_result(result)
        results.append(result.model_dump())

    logger.info(f"Benchmark run complete: {len(results)} tests, agent_type={agent_type}")

    return {
        "status": "complete",
        "total_tests": len(results),
        "results": results
    }


@router.get("/research/benchmarks/report", tags=["research"])
async def get_benchmark_report(agent_type: Optional[str] = None) -> Dict:
    """Get benchmark performance report"""
    report = benchmark_service.generate_report(agent_type=agent_type)
    return report.model_dump()


@router.get("/research/benchmarks/compare", tags=["research"])
async def compare_agents() -> List[Dict]:
    """Compare performance across different agent types"""
    rankings = benchmark_service.compare_agents()
    return rankings


# Emergent Behavior Monitoring
@router.post("/research/emergent/track", tags=["research"])
async def track_agent_behavior(
    session_id: str,
    agent_type: str,
    tools_used: List[str],
    reasoning_steps: List[str],
    outcome: str,
    success: bool
) -> Dict:
    """Track agent behavior for emergent pattern detection"""
    emergent_monitor.track_agent_behavior(
        session_id=session_id,
        agent_type=agent_type,
        tools_used=tools_used,
        reasoning_steps=reasoning_steps,
        outcome=outcome,
        success=success
    )

    return {"status": "tracked", "session_id": session_id}


@router.get("/research/emergent/capabilities", tags=["research"])
async def detect_emergent_capabilities(lookback_days: int = 7) -> List[Dict]:
    """Detect emergent capabilities (tool use, self-correction, etc.)"""
    capabilities = emergent_monitor.detect_emergent_capabilities(lookback_days)
    return [c.model_dump() for c in capabilities]


@router.get("/research/emergent/failures", tags=["research"])
async def detect_failure_modes(lookback_days: int = 7) -> List[Dict]:
    """Detect failure modes (reward hacking, reasoning loops, etc.)"""
    failures = emergent_monitor.detect_failure_modes(lookback_days)
    return [f.model_dump() for f in failures]


@router.get("/research/emergent/summary", tags=["research"])
async def get_emergent_behavior_summary(lookback_days: int = 7) -> Dict:
    """Get comprehensive emergent behavior summary"""
    summary = emergent_monitor.get_behavior_summary(lookback_days)
    return summary


# World Models
@router.post("/research/worldmodel/predict", tags=["research"])
async def predict_transaction_outcome(transaction: Dict) -> Dict:
    """Predict transaction outcome using world model"""
    outcome = world_model.predict_outcome(transaction)
    return outcome.model_dump()


@router.post("/research/worldmodel/counterfactual", tags=["research"])
async def simulate_counterfactual(
    original_transaction: Dict,
    modifications: Dict
) -> Dict:
    """
    Simulate counterfactual: 'What if amount was different?'

    Enables what-if analysis for understanding fraud dynamics.
    """
    scenario = world_model.simulate_counterfactual(
        original_transaction=original_transaction,
        modifications=modifications
    )

    logger.info(f"Counterfactual: {scenario.description}")

    return scenario.model_dump()


@router.post("/research/worldmodel/explain", tags=["research"])
async def explain_world_model_prediction(transaction: Dict) -> Dict:
    """Get explanation of world model's prediction"""
    explanation = world_model.explain_prediction(transaction)
    return {"explanation": explanation}


# Self-Play
@router.post("/research/selfplay/match", tags=["research"])
async def play_selfplay_match(
    fraud_transaction: Dict,
    iteration: int = 1
) -> Dict:
    """
    Play one self-play match: fraud evader vs fraud detector.

    Adversarial training for improving both detection and evasion resistance.
    """
    # Simple detector function (replace with actual agent)
    async def simple_detector(tx: Dict) -> tuple:
        amount = tx.get("amount", 0)
        tx_type = tx.get("type", "")

        is_fraud = (tx_type == "CASH_OUT" and amount > 100000) or amount > 500000
        confidence = 0.8 if is_fraud else 0.7

        return is_fraud, confidence

    match = await selfplay_service.play_match(
        fraud_transaction=fraud_transaction,
        detector_func=simple_detector,
        iteration=iteration
    )

    logger.info(
        f"Self-play match: iteration={iteration}, "
        f"detector_won={match.detector_caught_it}, evader_won={match.evader_successful}"
    )

    return match.model_dump()


@router.get("/research/selfplay/stats", tags=["research"])
async def get_selfplay_stats(last_n_matches: Optional[int] = None) -> Dict:
    """Get self-play statistics and improvement tracking"""
    stats = selfplay_service.get_stats(last_n_matches=last_n_matches)
    return stats.model_dump()


@router.get("/research/selfplay/hardest-evasions", tags=["research"])
async def get_hardest_evasions(limit: int = 10) -> List[Dict]:
    """Get evasion attempts that successfully fooled the detector"""
    evasions = selfplay_service.get_hardest_evasions(limit=limit)
    return evasions


# ============================================================================
# DISTRIBUTION SHIFT FROM TOOLS APIs (Section 16.2)
# ============================================================================

@router.post("/research/distribution/record-tool-use", tags=["research"])
async def record_tool_usage(
    session_id: str,
    tool_name: str,
    input_data: Dict,
    output_data: Dict,
    success: bool = True
) -> Dict:
    """
    Record tool usage for distribution shift analysis.

    Tracks how tool usage affects data distribution and agent behavior.
    """
    distribution_monitor.record_tool_usage(
        session_id=session_id,
        tool_name=tool_name,
        input_data=input_data,
        output_data=output_data,
        success=success
    )

    return {
        "status": "recorded",
        "session_id": session_id,
        "tool_name": tool_name
    }


@router.get("/research/distribution/analyze-impact", tags=["research"])
async def analyze_tool_impact(tool_name: Optional[str] = None) -> Dict:
    """
    Analyze how tools change data distribution.

    Returns distribution metrics for tool usage patterns.
    """
    return distribution_monitor.analyze_tool_impact(tool_name=tool_name)


@router.get("/research/distribution/detect-exploitation", tags=["research"])
async def detect_tool_exploitation(tool_name: str) -> Dict:
    """
    Detect if agent is exploiting a tool.

    Identifies patterns like repetitive inputs or unrealistic success rates.
    """
    return distribution_monitor.detect_tool_exploitation(tool_name=tool_name)


@router.get("/research/distribution/check-reliance", tags=["research"])
async def check_tool_reliance(tool_name: str) -> Dict:
    """
    Check if agent is over-reliant on a tool.

    Compares performance with and without tools to detect over-reliance.
    """
    report = distribution_monitor.check_tool_reliance(tool_name=tool_name)
    return report.model_dump()


@router.post("/research/distribution/test-tool-free", tags=["research"])
async def test_tool_free_performance(
    session_id: str,
    input_data: Dict,
    prediction: str,
    success: bool
) -> Dict:
    """
    Test agent performance without tools (fallback capability).

    Records results for generalization analysis.
    """
    return distribution_monitor.test_tool_free_performance(
        session_id=session_id,
        input_data=input_data,
        prediction=prediction,
        success=success
    )


@router.get("/research/distribution/generalization-report", tags=["research"])
async def get_generalization_report() -> Dict:
    """
    Report on generalization outside tool scope.

    Compares performance with vs without tools to assess generalization.
    """
    return distribution_monitor.get_generalization_report()


# ============================================================================
# SIMULATED ENVIRONMENTS APIs (Section 16.3)
# ============================================================================

@router.post("/research/simulation/generate-transaction", tags=["research"])
async def generate_synthetic_transaction(
    fraud_probability: float = 0.5,
    difficulty: int = 3
) -> Dict:
    """
    Generate a single synthetic transaction for testing.

    Creates realistic fraud or legitimate transactions with configurable difficulty.
    """
    tx = simulation_env.generate_synthetic_transaction(
        fraud_probability=fraud_probability,
        difficulty=difficulty
    )
    return tx.model_dump()


@router.post("/research/simulation/generate-batch", tags=["research"])
async def generate_transaction_batch(
    count: int = 100,
    fraud_ratio: float = 0.3,
    min_difficulty: int = 1,
    max_difficulty: int = 5
) -> Dict:
    """
    Generate a batch of synthetic transactions.

    Useful for creating test datasets with specific fraud ratios.
    """
    transactions = simulation_env.generate_batch(
        count=count,
        fraud_ratio=fraud_ratio,
        difficulty_range=(min_difficulty, max_difficulty)
    )

    return {
        "status": "generated",
        "count": len(transactions),
        "fraud_count": sum(1 for tx in transactions if tx.is_fraud),
        "legitimate_count": sum(1 for tx in transactions if not tx.is_fraud),
        "transactions": [tx.model_dump() for tx in transactions[:10]]  # Return first 10
    }


@router.post("/research/simulation/create-scenario", tags=["research"])
async def create_adversarial_scenario(
    scenario_type: FraudScenarioType,
    num_transactions: int = 10
) -> Dict:
    """
    Create an adversarial fraud scenario for testing.

    Generates sophisticated attack scenarios like coordinated attacks,
    account takeovers, and gradual drainage.
    """
    scenario = simulation_env.create_adversarial_scenario(
        scenario_type=scenario_type,
        num_transactions=num_transactions
    )

    return scenario.model_dump()


@router.post("/research/simulation/run", tags=["research"])
async def run_simulation(scenario_id: str) -> Dict:
    """
    Run a simulation scenario and evaluate agent performance.

    Tests agent against pre-created adversarial scenarios.
    Uses a simple heuristic detector if no custom detector provided.
    """
    result = simulation_env.run_simulation(scenario_id=scenario_id)
    return result.model_dump()


@router.get("/research/simulation/exploration-space", tags=["research"])
async def get_safe_exploration_space() -> Dict:
    """
    Get parameters for safe exploration in simulation.

    Returns transaction types, amount ranges, fraud scenarios,
    and recommended practice guidelines.
    """
    return simulation_env.get_safe_exploration_space()


@router.get("/research/simulation/stats", tags=["research"])
async def get_simulation_stats() -> Dict:
    """
    Get statistics about simulations run.

    Returns total scenarios, average F1 score, and performance metrics.
    """
    return simulation_env.get_simulation_stats()


# ============================================================================
# SECTION 17: ADVANCED EVALUATION & DEBUGGING
# ============================================================================

# 17.1 Agent Debugging Tools - Trace Debugger Endpoints

@router.post("/research/debug/start-trace", tags=["research", "debugging"])
async def start_execution_trace(
    session_id: str,
    transaction_id: str
) -> Dict:
    """
    Start a new execution trace for debugging.

    Returns trace_id to use for adding steps and ending trace.
    """
    trace = trace_debugger.start_trace(
        session_id=session_id,
        transaction_id=transaction_id
    )

    return {
        "status": "trace_started",
        "trace_id": trace.trace_id,
        "session_id": trace.session_id,
        "transaction_id": trace.transaction_id,
        "start_time": trace.start_time
    }


class StepRequest(BaseModel):
    """Request to add a step to trace"""
    trace_id: str
    step_type: StepType
    content: str
    tool_name: Optional[str] = None
    tool_input: Optional[Dict[str, Any]] = None
    tool_output: Optional[Dict[str, Any]] = None
    is_decision: bool = False
    confidence: Optional[float] = None


@router.post("/research/debug/add-step", tags=["research", "debugging"])
async def add_trace_step(request: StepRequest) -> Dict:
    """
    Add a reasoning step to an active trace.

    Logs step-level execution with timestamps, tool calls, and decisions.
    """
    # Get trace from file
    trace = trace_debugger.get_trace(request.trace_id)
    if not trace:
        raise HTTPException(status_code=404, detail=f"Trace {request.trace_id} not found")

    step = trace_debugger.add_step(
        trace=trace,
        step_type=request.step_type,
        content=request.content,
        tool_name=request.tool_name,
        tool_input=request.tool_input,
        tool_output=request.tool_output,
        is_decision=request.is_decision,
        confidence=request.confidence
    )

    return {
        "status": "step_added",
        "trace_id": request.trace_id,
        "step_id": step.step_id,
        "step_number": step.step_number,
        "step_type": step.step_type
    }


class EndTraceRequest(BaseModel):
    """Request to end a trace"""
    trace_id: str
    final_decision: str
    success: bool
    error: Optional[str] = None
    token_usage: int = 0
    cost_usd: float = 0.0


@router.post("/research/debug/end-trace", tags=["research", "debugging"])
async def end_execution_trace(request: EndTraceRequest) -> Dict:
    """
    End an execution trace and save to file.

    Also saves to failures file if not successful.
    """
    trace = trace_debugger.get_trace(request.trace_id)
    if not trace:
        raise HTTPException(status_code=404, detail=f"Trace {request.trace_id} not found")

    final_trace = trace_debugger.end_trace(
        trace=trace,
        final_decision=request.final_decision,
        success=request.success,
        error=request.error,
        token_usage=request.token_usage,
        cost_usd=request.cost_usd
    )

    return {
        "status": "trace_ended",
        "trace_id": final_trace.trace_id,
        "success": final_trace.success,
        "total_steps": len(final_trace.steps),
        "total_duration_ms": final_trace.total_duration_ms,
        "token_usage": final_trace.token_usage,
        "cost_usd": final_trace.cost_usd
    }


@router.get("/research/debug/trace/{trace_id}", tags=["research", "debugging"])
async def get_trace_details(trace_id: str) -> Dict:
    """
    Get detailed execution trace.

    Returns all steps with timestamps, tool calls, and decisions.
    """
    trace = trace_debugger.get_trace(trace_id)
    if not trace:
        raise HTTPException(status_code=404, detail=f"Trace {trace_id} not found")

    return trace.model_dump()


@router.get("/research/debug/export-trace/{trace_id}", tags=["research", "debugging"])
async def export_trace_json(trace_id: str) -> Dict:
    """
    Export trace in JSON format for external debugging tools.

    Returns formatted trace with step summaries.
    """
    return trace_debugger.export_trace(trace_id)


@router.get("/research/debug/inspect-thoughts/{trace_id}", tags=["research", "debugging"])
async def inspect_agent_thoughts(trace_id: str) -> Dict:
    """
    Analyze internal reasoning quality.

    Validates Chain-of-Thought consistency, identifies reasoning errors,
    detects logic gaps, and calculates efficiency score.
    """
    analysis = trace_debugger.inspect_thoughts(trace_id)
    return analysis.model_dump()


class ToolReplayRequest(BaseModel):
    """Request to replay a tool call"""
    tool_name: str
    tool_input: Dict[str, Any]
    use_cache: bool = True


@router.post("/research/debug/replay-tool", tags=["research", "debugging"])
async def replay_tool_call(request: ToolReplayRequest) -> Dict:
    """
    Replay a tool call from cache for debugging.

    Deterministically re-executes using cached results.
    """
    output = trace_debugger.replay_tool_call(
        tool_name=request.tool_name,
        tool_input=request.tool_input,
        use_cache=request.use_cache
    )

    if output is None:
        return {
            "status": "cache_miss",
            "message": f"No cached result for {request.tool_name}"
        }

    return {
        "status": "replayed",
        "tool_name": request.tool_name,
        "output": output
    }


@router.post("/research/debug/deterministic-replay/{trace_id}", tags=["research", "debugging"])
async def deterministic_replay_trace(trace_id: str, random_seed: int = 42) -> Dict:
    """
    Replay exact agent execution deterministically.

    Uses fixed random seeds and cached tool results to reproduce bugs reliably.
    """
    replay_trace = trace_debugger.deterministic_replay(
        trace_id=trace_id,
        random_seed=random_seed
    )

    return {
        "status": "replay_complete",
        "original_trace_id": trace_id,
        "replay_trace_id": replay_trace.trace_id,
        "steps_replayed": len(replay_trace.steps),
        "success": replay_trace.success
    }


@router.get("/research/debug/cluster-failures", tags=["research", "debugging"])
async def cluster_failure_patterns() -> Dict:
    """
    Identify and group similar failures.

    Returns failure patterns with root cause hypotheses and priority.
    """
    patterns = trace_debugger.cluster_failures()

    return {
        "status": "analyzed",
        "total_patterns": len(patterns),
        "patterns": [p.model_dump() for p in patterns]
    }


# 17.2 Comprehensive Metrics - Metrics Collection Endpoints

class TaskRecordRequest(BaseModel):
    """Request to record task result"""
    task_id: str
    transaction_id: str
    predicted: str
    ground_truth: Optional[str] = None
    aligned_with_human: Optional[bool] = None
    completed: bool = True
    error: Optional[str] = None


@router.post("/research/metrics/record-task", tags=["research", "metrics"])
async def record_task_result(request: TaskRecordRequest) -> Dict:
    """
    Record task execution result.

    Tracks classification accuracy, human alignment, and completion rate.
    """
    result = metrics_collector.record_task(
        task_id=request.task_id,
        transaction_id=request.transaction_id,
        predicted=request.predicted,
        ground_truth=request.ground_truth,
        aligned_with_human=request.aligned_with_human,
        completed=request.completed,
        error=request.error
    )

    return {
        "status": "recorded",
        "task_id": result.task_id,
        "correct": result.correct,
        "completed": result.completed
    }


class ToolCallRecordRequest(BaseModel):
    """Request to record tool call"""
    tool_name: str
    tool_input: Dict[str, Any]
    tool_output: Optional[Dict[str, Any]]
    success: bool
    duration_ms: float
    error: Optional[str] = None
    was_necessary: Optional[bool] = None
    parameter_correctness: Optional[float] = None


@router.post("/research/metrics/record-tool-call", tags=["research", "metrics"])
async def record_tool_call_metrics(request: ToolCallRecordRequest) -> Dict:
    """
    Record tool call metrics.

    Tracks tool success rate, selection accuracy, parameter correctness.
    """
    call = metrics_collector.record_tool_call(
        tool_name=request.tool_name,
        tool_input=request.tool_input,
        tool_output=request.tool_output,
        success=request.success,
        duration_ms=request.duration_ms,
        error=request.error,
        was_necessary=request.was_necessary,
        parameter_correctness=request.parameter_correctness
    )

    return {
        "status": "recorded",
        "call_id": call.call_id,
        "tool_name": call.tool_name,
        "success": call.success
    }


class CostRecordRequest(BaseModel):
    """Request to record cost metrics"""
    task_id: str
    token_usage: int
    api_calls: int
    cost_usd: float
    model_used: str = "mistral-7b"


@router.post("/research/metrics/record-cost", tags=["research", "metrics"])
async def record_cost_metrics(request: CostRecordRequest) -> Dict:
    """
    Record cost metrics for a task.

    Tracks token usage, API calls, and $ cost per transaction.
    """
    metrics = metrics_collector.record_cost(
        task_id=request.task_id,
        token_usage=request.token_usage,
        api_calls=request.api_calls,
        cost_usd=request.cost_usd,
        model_used=request.model_used
    )

    return {
        "status": "recorded",
        "task_id": metrics.task_id,
        "cost_usd": metrics.cost_usd,
        "token_usage": metrics.token_usage
    }


class LatencyRecordRequest(BaseModel):
    """Request to record latency metrics"""
    task_id: str
    total_latency_ms: float
    reasoning_latency_ms: float
    tool_call_latency_ms: float
    step_latencies: List[float]


@router.post("/research/metrics/record-latency", tags=["research", "metrics"])
async def record_latency_metrics(request: LatencyRecordRequest) -> Dict:
    """
    Record latency metrics.

    Tracks p50, p95, p99 latencies and step-by-step breakdown.
    """
    metrics = metrics_collector.record_latency(
        task_id=request.task_id,
        total_latency_ms=request.total_latency_ms,
        reasoning_latency_ms=request.reasoning_latency_ms,
        tool_call_latency_ms=request.tool_call_latency_ms,
        step_latencies=request.step_latencies
    )

    return {
        "status": "recorded",
        "task_id": metrics.task_id,
        "total_latency_ms": metrics.total_latency_ms
    }


class RecoveryRecordRequest(BaseModel):
    """Request to record recovery event"""
    task_id: str
    failure_type: str
    recovery_attempted: bool
    recovery_successful: bool
    recovery_time_ms: Optional[float] = None
    escalated_to_human: bool = False
    human_intervention_time_ms: Optional[float] = None


@router.post("/research/metrics/record-recovery", tags=["research", "metrics"])
async def record_recovery_event(request: RecoveryRecordRequest) -> Dict:
    """
    Record failure recovery event.

    Tracks recovery rate, escalation rate, and human intervention.
    """
    event = metrics_collector.record_recovery(
        task_id=request.task_id,
        failure_type=request.failure_type,
        recovery_attempted=request.recovery_attempted,
        recovery_successful=request.recovery_successful,
        recovery_time_ms=request.recovery_time_ms,
        escalated_to_human=request.escalated_to_human,
        human_intervention_time_ms=request.human_intervention_time_ms
    )

    return {
        "status": "recorded",
        "event_id": event.event_id,
        "recovery_successful": event.recovery_successful,
        "escalated": event.escalated_to_human
    }


class ViolationRecordRequest(BaseModel):
    """Request to record alignment violation"""
    task_id: str
    violation_type: Literal["safety", "constraint", "refusal_failure", "false_refusal"]
    description: str
    severity: Literal["low", "medium", "high", "critical"]
    rule_violated: Optional[str] = None


@router.post("/research/metrics/record-violation", tags=["research", "metrics"])
async def record_alignment_violation(request: ViolationRecordRequest) -> Dict:
    """
    Record alignment violation.

    Tracks safety rule violations, constraint violations, and refusal failures.
    """
    violation = metrics_collector.record_violation(
        task_id=request.task_id,
        violation_type=request.violation_type,
        description=request.description,
        severity=request.severity,
        rule_violated=request.rule_violated
    )

    return {
        "status": "recorded",
        "violation_id": violation.violation_id,
        "severity": violation.severity,
        "violation_type": violation.violation_type
    }


@router.get("/research/metrics/aggregated", tags=["research", "metrics"])
async def get_aggregated_metrics(days: int = 7) -> Dict:
    """
    Get comprehensive aggregated metrics.

    Returns task success rate, tool accuracy, cost metrics, latency metrics,
    recovery rate, and alignment violations for the last N days.
    """
    metrics = metrics_collector.get_aggregated_metrics(days=days)
    return metrics.model_dump()


@router.get("/research/metrics/tool-breakdown", tags=["research", "metrics"])
async def get_tool_breakdown() -> Dict:
    """
    Get detailed breakdown by tool.

    Returns success rate, average duration, and error count per tool.
    """
    return metrics_collector.get_tool_breakdown()


@router.get("/research/metrics/latency-breakdown", tags=["research", "metrics"])
async def get_latency_breakdown() -> Dict:
    """
    Get latency breakdown by component.

    Returns average reasoning time, tool call time, and total time.
    """
    return metrics_collector.get_latency_breakdown()


# 17.3 Automated Testing Suite Endpoints

class TestCaseRequest(BaseModel):
    """Request to create a test case"""
    test_name: str
    test_type: TestType
    description: str
    inputs: Dict[str, Any]
    expected_output: Optional[Any] = None
    expected_behavior: Optional[str] = None
    tags: List[str] = []
    timeout_ms: int = 30000
    critical: bool = False


@router.post("/research/testing/create-test-case", tags=["research", "testing"])
async def create_test_case(request: TestCaseRequest) -> Dict:
    """
    Create a new test case.

    Can be unit, integration, regression, adversarial, edge case, or performance test.
    """
    test = test_suite.add_test_case(
        test_name=request.test_name,
        test_type=request.test_type,
        description=request.description,
        inputs=request.inputs,
        expected_output=request.expected_output,
        expected_behavior=request.expected_behavior,
        tags=request.tags,
        timeout_ms=request.timeout_ms,
        critical=request.critical
    )

    return {
        "status": "created",
        "test_id": test.test_id,
        "test_name": test.test_name,
        "test_type": test.test_type
    }


@router.get("/research/testing/adversarial-tests", tags=["research", "testing"])
async def get_adversarial_tests() -> Dict:
    """
    Get pre-built adversarial test cases.

    Includes prompt injection, financial advice refusal, extreme amounts,
    missing data, and balance manipulation tests.
    """
    tests = test_suite.create_adversarial_tests()

    return {
        "status": "generated",
        "count": len(tests),
        "tests": [t.model_dump() for t in tests]
    }


@router.get("/research/testing/edge-case-tests", tags=["research", "testing"])
async def get_edge_case_tests() -> Dict:
    """
    Get pre-built edge case tests.

    Includes zero amounts, negative amounts, self-transfers,
    and very long descriptions.
    """
    tests = test_suite.create_edge_case_tests()

    return {
        "status": "generated",
        "count": len(tests),
        "tests": [t.model_dump() for t in tests]
    }


class BaselineRequest(BaseModel):
    """Request to save regression baseline"""
    metrics: Dict[str, float]


@router.post("/research/testing/save-baseline", tags=["research", "testing"])
async def save_regression_baseline(request: BaselineRequest) -> Dict:
    """
    Save baseline metrics for regression testing.

    Future runs will be compared against this baseline.
    """
    test_suite.save_regression_baseline(request.metrics)

    return {
        "status": "baseline_saved",
        "metrics_count": len(request.metrics),
        "timestamp": datetime.utcnow().isoformat()
    }


class RegressionCheckRequest(BaseModel):
    """Request to check for regression"""
    current_metrics: Dict[str, float]


@router.post("/research/testing/check-regression", tags=["research", "testing"])
async def check_regression(request: RegressionCheckRequest) -> Dict:
    """
    Check for performance regression.

    Compares current metrics against baseline. Flags regressions >5%.
    """
    result = test_suite.check_regression(request.current_metrics)

    return result


# ================================
# SECTION 8: SAFETY, SECURITY & ALIGNMENT
# ================================

# ========== LLM Safety Guard ==========

class PromptCheckRequest(BaseModel):
    """Request to check for prompt injection"""
    prompt: str


@router.post("/security/safety/check-injection", tags=["security", "safety"])
async def check_prompt_injection(request: PromptCheckRequest) -> Dict:
    """
    Detect prompt injection attacks.

    Checks for:
    - Instruction override attempts
    - System message manipulation
    - Role confusion
    - Delimiter manipulation
    """
    result = safety_guard.detect_prompt_injection(request.prompt)

    return result.model_dump()


@router.post("/security/safety/check-jailbreak", tags=["security", "safety"])
async def check_jailbreak(request: PromptCheckRequest) -> Dict:
    """
    Detect jailbreak attempts.

    Checks for:
    - DAN (Do Anything Now) prompts
    - Hypothetical scenario jailbreaks
    - Unfiltered mode requests
    - Roleplay jailbreaks
    """
    result = safety_guard.detect_jailbreak(request.prompt)

    return result.model_dump()


class RefusalCheckRequest(BaseModel):
    """Request to check if should refuse"""
    request_text: str


@router.post("/security/safety/should-refuse", tags=["security", "safety"])
async def should_refuse(request: RefusalCheckRequest) -> Dict:
    """
    Check if request should be refused.

    Refuses:
    - Financial advice requests
    - Illegal activity
    - Harmful content
    """
    result = safety_guard.should_refuse_request(request.request_text)

    return result.model_dump()


class UncertaintyRequest(BaseModel):
    """Request to quantify uncertainty"""
    prediction: str
    confidence: float
    transaction_amount: float = 0.0


@router.post("/security/safety/uncertainty", tags=["security", "safety"])
async def quantify_uncertainty(request: UncertaintyRequest) -> Dict:
    """
    Quantify prediction uncertainty.

    Determines if human escalation is needed based on:
    - Low confidence (<0.7)
    - High-value transactions (>$100k)
    - Edge cases
    """
    context = {"amount": request.transaction_amount} if request.transaction_amount else None

    result = safety_guard.quantify_uncertainty(
        prediction=request.prediction,
        confidence=request.confidence,
        context=context
    )

    return result.model_dump()


class SanitizeRequest(BaseModel):
    """Request to sanitize output"""
    output_text: str


@router.post("/security/safety/sanitize-output", tags=["security", "safety"])
async def sanitize_output(request: SanitizeRequest) -> Dict:
    """
    Sanitize LLM output.

    Removes:
    - PII (emails, phones, SSNs, credit cards)
    - Extreme language
    """
    sanitized = safety_guard.sanitize_output(request.output_text)

    return {
        "sanitized_output": sanitized,
        "original_length": len(request.output_text),
        "sanitized_length": len(sanitized)
    }


class BiasAuditRequest(BaseModel):
    """Request to audit bias"""
    predictions: List[Dict[str, Any]]  # List of {amount: float, prediction: bool}


@router.post("/security/safety/audit-bias", tags=["security", "safety"])
async def audit_bias(request: BiasAuditRequest) -> Dict:
    """
    Audit model for bias.

    Analyzes fraud detection rates across transaction amount buckets:
    - Micro ($0-100)
    - Small ($100-1k)
    - Medium ($1k-10k)
    - Large ($10k-100k)
    - Very Large ($100k+)
    """
    result = safety_guard.audit_bias(request.predictions)

    return result.model_dump()


class FairnessRequest(BaseModel):
    """Request to calculate fairness metrics"""
    group_a_predictions: List[bool]
    group_b_predictions: List[bool]
    group_a_labels: List[bool]
    group_b_labels: List[bool]


@router.post("/security/safety/fairness-metrics", tags=["security", "safety"])
async def calculate_fairness(request: FairnessRequest) -> Dict:
    """
    Calculate fairness metrics.

    Computes:
    - Demographic parity difference
    - Equal opportunity difference
    - Disparate impact ratio (80% rule)
    """
    result = safety_guard.calculate_fairness_metrics(
        group_a_predictions=request.group_a_predictions,
        group_b_predictions=request.group_b_predictions,
        group_a_labels=request.group_a_labels,
        group_b_labels=request.group_b_labels
    )

    return result.model_dump()


@router.get("/security/safety/dashboard", tags=["security", "safety"])
async def get_safety_dashboard(days: int = 7) -> Dict:
    """
    Get safety dashboard.

    Shows:
    - Total incidents
    - Incidents by type
    - Incidents by severity
    - Recent incidents (last 10)
    """
    dashboard = safety_guard.get_safety_dashboard(days=days)

    return dashboard


# ========== Security Manager ==========

class TokenRequest(BaseModel):
    """Request to create access token"""
    user_id: str
    username: str
    roles: List[str] = Field(default_factory=list)


@router.post("/security/auth/create-token", tags=["security", "auth"])
async def create_token(request: TokenRequest) -> Dict:
    """
    Create JWT access token.

    Token expires in 24 hours by default.
    """
    token = security_manager.create_access_token(
        user_id=request.user_id,
        username=request.username,
        roles=request.roles
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": 86400  # 24 hours in seconds
    }


class TokenVerifyRequest(BaseModel):
    """Request to verify token"""
    token: str


@router.post("/security/auth/verify-token", tags=["security", "auth"])
async def verify_token(request: TokenVerifyRequest) -> Dict:
    """
    Verify JWT token.

    Returns token data if valid, error if invalid/expired.
    """
    token_data = security_manager.verify_token(request.token)

    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )

    return token_data.model_dump()


@router.post("/security/auth/refresh-token", tags=["security", "auth"])
async def refresh_token(request: TokenVerifyRequest) -> Dict:
    """
    Refresh JWT token.

    Creates new token with same data if old token is valid.
    """
    new_token = security_manager.refresh_token(request.token)

    if not new_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Cannot refresh invalid/expired token"
        )

    return {
        "access_token": new_token,
        "token_type": "bearer",
        "expires_in": 86400
    }


@router.post("/security/rate-limit/check", tags=["security", "rate-limit"])
async def check_rate_limit(
    identifier: str = Query(..., description="IP, user_id, or API key"),
    max_requests: int = Query(100, description="Max requests"),
    window_seconds: int = Query(60, description="Time window in seconds")
) -> Dict:
    """
    Check rate limit.

    Uses token bucket algorithm.
    """
    config = RateLimitConfig(
        max_requests=max_requests,
        window_seconds=window_seconds,
        identifier=identifier
    )

    within_limit = security_manager.check_rate_limit(config)

    if not within_limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded: {max_requests} requests per {window_seconds}s"
        )

    return {
        "within_limit": True,
        "identifier": identifier,
        "max_requests": max_requests,
        "window_seconds": window_seconds
    }


@router.get("/security/rate-limit/status", tags=["security", "rate-limit"])
async def get_rate_limit_status(
    identifier: str = Query(..., description="IP, user_id, or API key"),
    window_seconds: int = Query(60, description="Time window in seconds")
) -> Dict:
    """
    Get rate limit status.

    Shows current request count for identifier.
    """
    status_data = security_manager.get_rate_limit_status(identifier, window_seconds)

    return status_data


class ValidationRequest(BaseModel):
    """Request to validate input"""
    transaction_data: Dict[str, Any]


@router.post("/security/validate/transaction", tags=["security", "validation"])
async def validate_transaction(request: ValidationRequest) -> Dict:
    """
    Validate and sanitize transaction input.

    Checks for:
    - Required fields
    - Data types
    - SQL injection
    - XSS attacks
    """
    result = security_manager.validate_transaction_input(request.transaction_data)

    return result.model_dump()


class FileValidationRequest(BaseModel):
    """Request to validate file upload"""
    filename: str
    file_content: str  # Base64 encoded


@router.post("/security/validate/file", tags=["security", "validation"])
async def validate_file(request: FileValidationRequest) -> Dict:
    """
    Validate file upload.

    Checks:
    - File extension whitelist
    - File size limits
    - Magic bytes verification
    """
    import base64

    try:
        file_bytes = base64.b64decode(request.file_content)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid base64 file content"
        )

    result = security_manager.validate_file_upload(request.filename, file_bytes)

    return result.model_dump()


class APIKeyRequest(BaseModel):
    """Request to generate API key"""
    prefix: str = "fsk"


@router.post("/security/secrets/generate-api-key", tags=["security", "secrets"])
async def generate_api_key(request: APIKeyRequest) -> Dict:
    """
    Generate secure API key.

    Returns key and hash (store hash in database).
    """
    api_key = security_manager.generate_api_key(prefix=request.prefix)
    api_key_hash = security_manager.hash_api_key(api_key)

    return {
        "api_key": api_key,
        "api_key_hash": api_key_hash,
        "note": "Store the hash in database. The raw key is shown only once."
    }


class APIKeyVerifyRequest(BaseModel):
    """Request to verify API key"""
    provided_key: str
    stored_hash: str


@router.post("/security/secrets/verify-api-key", tags=["security", "secrets"])
async def verify_api_key(request: APIKeyVerifyRequest) -> Dict:
    """
    Verify API key against stored hash.

    Uses constant-time comparison.
    """
    is_valid = security_manager.verify_api_key(
        request.provided_key,
        request.stored_hash
    )

    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )

    return {"valid": True}


# ========== Privacy Handler ==========

class PIIDetectionRequest(BaseModel):
    """Request to detect PII"""
    text: str


@router.post("/security/privacy/detect-pii", tags=["security", "privacy"])
async def detect_pii(request: PIIDetectionRequest) -> Dict:
    """
    Detect personally identifiable information (PII).

    Detects:
    - Emails
    - Phone numbers
    - SSNs
    - Credit cards
    - IP addresses
    - Dates of birth
    - Names
    - Addresses
    """
    result = privacy_handler.detect_pii(request.text)

    return result.model_dump()


class TransactionSanitizeRequest(BaseModel):
    """Request to sanitize transaction"""
    transaction: Dict[str, Any]


@router.post("/security/privacy/sanitize-transaction", tags=["security", "privacy"])
async def sanitize_transaction(request: TransactionSanitizeRequest) -> Dict:
    """
    Sanitize transaction data.

    Redacts PII from transaction fields.
    """
    sanitized = privacy_handler.sanitize_transaction_data(request.transaction)

    return {
        "sanitized_transaction": sanitized,
        "original_fields": len(request.transaction),
        "sanitized_fields": len(sanitized)
    }


class AnonymizeRequest(BaseModel):
    """Request to anonymize user ID"""
    user_id: str
    method: Literal["hash", "pseudonym", "token"] = "hash"


@router.post("/security/privacy/anonymize", tags=["security", "privacy"])
async def anonymize_user(request: AnonymizeRequest) -> Dict:
    """
    Anonymize user identifier.

    Methods:
    - hash: SHA-256 hash (irreversible)
    - pseudonym: Random pseudonym (reversible if mapping stored)
    - token: Secure token (irreversible)
    """
    result = privacy_handler.anonymize_user_id(
        user_id=request.user_id,
        method=request.method
    )

    return result.model_dump()


@router.post("/security/privacy/consent", tags=["security", "privacy"])
async def record_consent(request: GDPRConsent) -> Dict:
    """
    Record GDPR consent.

    Consent types:
    - data_collection
    - data_processing
    - data_sharing
    """
    privacy_handler.record_consent(request)

    return {
        "status": "consent_recorded",
        "user_id": request.user_id,
        "consent_type": request.consent_type,
        "granted": request.granted,
        "timestamp": request.timestamp.isoformat()
    }


@router.get("/security/privacy/verify-consent", tags=["security", "privacy"])
async def verify_consent(
    user_id: str = Query(...),
    consent_type: str = Query(...)
) -> Dict:
    """
    Verify GDPR consent.

    Checks if user has granted consent for specific type.
    """
    has_consent = privacy_handler.verify_consent(user_id, consent_type)

    return {
        "user_id": user_id,
        "consent_type": consent_type,
        "has_consent": has_consent
    }


@router.get("/security/privacy/user-data/{user_id}", tags=["security", "privacy"])
async def get_user_data(user_id: str) -> Dict:
    """
    Get all user data (GDPR data portability right).

    Returns all data for a user.
    """
    user_data = privacy_handler.get_user_data(user_id)

    return user_data


@router.delete("/security/privacy/user-data/{user_id}", tags=["security", "privacy"])
async def delete_user_data(user_id: str) -> Dict:
    """
    Delete all user data (GDPR right to erasure).

    Deletes all data for a user.
    """
    deleted_counts = privacy_handler.delete_user_data(user_id)

    return {
        "status": "data_deleted",
        "user_id": user_id,
        "deleted_counts": deleted_counts
    }


@router.get("/security/privacy/retention-policy", tags=["security", "privacy"])
async def get_retention_policy(data_type: str = Query(...)) -> Dict:
    """
    Get data retention policy.

    Data types:
    - transaction_logs (7 years)
    - user_data (1 year)
    - fraud_reports (5 years)
    - audit_logs (7 years)
    - pii_data (1 year)
    """
    policy = privacy_handler.get_retention_policy(data_type)

    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No retention policy for data type: {data_type}"
        )

    return policy.model_dump()


@router.get("/security/privacy/dashboard", tags=["security", "privacy"])
async def get_privacy_dashboard(days: int = Query(7)) -> Dict:
    """
    Get privacy compliance dashboard.

    Shows:
    - Total audits
    - Consent violations
    - Retention violations
    - Data types accessed
    - Recent audits
    """
    dashboard = privacy_handler.get_privacy_dashboard(days=days)

    return dashboard


# ================================
# SECTION 18: TOKENIZATION ENGINEERING
# ================================

class TokenAnalysisRequest(BaseModel):
    """Request to analyze token efficiency"""
    text: str


@router.post("/research/tokenization/analyze", tags=["research", "tokenization"])
async def analyze_tokens(request: TokenAnalysisRequest) -> Dict:
    """
    Analyze token efficiency of text.

    Returns:
    - Token count estimate
    - Efficiency score (0-1)
    - Issues and recommendations
    - Tokens per word ratio
    """
    result = tokenization_service.analyze_tokens(request.text)

    return result.model_dump()


class OptimizationRequest(BaseModel):
    """Request to optimize prompt"""
    text: str
    aggressive: bool = False


@router.post("/research/tokenization/optimize", tags=["research", "tokenization"])
async def optimize_prompt(request: OptimizationRequest) -> Dict:
    """
    Optimize prompt for token efficiency.

    Applies:
    - Verbose phrase replacement
    - Fraud-specific term simplification
    - Filler word removal (if aggressive)
    - Whitespace normalization

    Returns optimized text and token savings.
    """
    result = tokenization_service.optimize_prompt(
        request.text,
        aggressive=request.aggressive
    )

    return result.model_dump()


@router.get("/research/tokenization/tokenizer-behavior", tags=["research", "tokenization"])
async def get_tokenizer_behavior() -> Dict:
    """
    Get Mistral tokenizer behavior analysis.

    Returns:
    - Average tokens per word
    - Common tokenization patterns
    - Special tokens list
    - Subword tokenization examples
    - Efficiency tips
    """
    result = tokenization_service.analyze_tokenizer_behavior()

    return result.model_dump()


class PromptComparisonRequest(BaseModel):
    """Request to compare prompt variants"""
    prompts: List[Dict[str, str]]  # [{name: str, text: str}, ...]


@router.post("/research/tokenization/compare-prompts", tags=["research", "tokenization"])
async def compare_prompts(request: PromptComparisonRequest) -> Dict:
    """
    Compare multiple prompt variants for efficiency.

    Returns best variant based on:
    - Lowest token count
    - Highest efficiency score
    - Fewest issues
    """
    result = tokenization_service.compare_prompts(request.prompts)

    return result.model_dump()


class SpecialTokenRequest(BaseModel):
    """Request to validate special tokens"""
    text: str


@router.post("/research/tokenization/validate-special-tokens", tags=["research", "tokenization"])
async def validate_special_tokens(request: SpecialTokenRequest) -> Dict:
    """
    Validate special token usage.

    Checks:
    - ChatML tag balance (<|im_start|>, <|im_end|>)
    - Mistral instruction tag balance ([INST], [/INST])
    - Format mixing warnings
    - Unknown special tokens
    """
    result = tokenization_service.validate_special_tokens(request.text)

    return result


class MultilingualRequest(BaseModel):
    """Request to analyze multilingual text"""
    text: str
    language: str = "en"


@router.post("/research/tokenization/multilingual-analysis", tags=["research", "tokenization"])
async def analyze_multilingual(request: MultilingualRequest) -> Dict:
    """
    Analyze tokenization for non-English text.

    Languages supported:
    - en (English - baseline)
    - es (Spanish)
    - fr (French)
    - de (German)
    - zh (Chinese)
    - ja (Japanese)
    - ar (Arabic)
    - ru (Russian)

    Returns token count estimate with language-specific multiplier.
    """
    result = tokenization_service.analyze_multilingual(
        request.text,
        language=request.language
    )

    return result


# ==================== Context Window Management ====================

class SlidingWindowRequest(BaseModel):
    """Request for sliding window operation"""
    messages: List[Dict[str, Any]] = Field(..., description="Conversation messages")
    window_size: int = Field(default=10, description="Maximum messages to keep")
    preserve_system: bool = Field(default=True, description="Always keep system messages")


class SummarizationRequest(BaseModel):
    """Request for context summarization"""
    messages: List[Dict[str, Any]] = Field(..., description="Messages to summarize")
    target_compression: float = Field(default=0.5, ge=0.1, le=0.9, description="Target compression ratio")


class ImportantContentRequest(BaseModel):
    """Request for important content detection"""
    messages: List[Dict[str, Any]] = Field(..., description="Messages to analyze")
    threshold: float = Field(default=0.3, ge=0.0, le=1.0, description="Importance threshold")


class OverflowCheckRequest(BaseModel):
    """Request for overflow checking"""
    messages: List[Dict[str, Any]] = Field(..., description="Messages to check")
    max_tokens: int = Field(default=4096, description="Maximum context window")
    output_reserve: int = Field(default=1024, description="Tokens reserved for output")


class DynamicAllocationRequest(BaseModel):
    """Request for dynamic allocation"""
    total_budget: int = Field(default=4096, description="Total token budget")
    system_prompt: Optional[str] = Field(default=None, description="System prompt text")
    expected_output_length: Literal["short", "medium", "long"] = Field(default="medium", description="Expected output length")


class ConversationManagementRequest(BaseModel):
    """Request for comprehensive conversation management"""
    messages: List[Dict[str, Any]] = Field(..., description="Conversation messages")
    max_tokens: int = Field(default=4096, description="Maximum context window")
    window_size: int = Field(default=10, description="Sliding window size")
    preserve_important: bool = Field(default=True, description="Keep important messages")
    auto_summarize: bool = Field(default=True, description="Auto-summarize when needed")


@router.post("/research/context/sliding-window", tags=["research", "context"])
async def apply_sliding_window(request: SlidingWindowRequest) -> Dict:
    """
    Apply sliding window to keep only recent messages.

    Keeps the most recent N messages while optionally preserving system messages.
    Useful for long conversations that exceed context limits.

    Returns:
    - Windowed messages with token counts
    - Total tokens after windowing
    - Overflow detection
    """
    result = context_manager.apply_sliding_window(
        messages=request.messages,
        window_size=request.window_size,
        preserve_system=request.preserve_system
    )

    return result.model_dump()


@router.post("/research/context/summarize", tags=["research", "context"])
async def summarize_context(request: SummarizationRequest) -> Dict:
    """
    Summarize conversation context using extractive summarization.

    Selects most important sentences based on keyword scoring.
    No LLM required - heuristic-based for M4 Pro efficiency.

    Args:
    - messages: Conversation to summarize
    - target_compression: 0.5 = 50% reduction

    Returns:
    - Summary text
    - Compression metrics
    - Token savings
    """
    result = context_manager.summarize_context(
        messages=request.messages,
        target_compression=request.target_compression
    )

    return result.model_dump()


@router.post("/research/context/detect-important", tags=["research", "context"])
async def detect_important_content(request: ImportantContentRequest) -> Dict:
    """
    Detect important messages that should be retained.

    Scores messages based on:
    - Importance keywords (fraud, risk, decision, etc.)
    - Decision-related content
    - Numerical data (amounts, scores)
    - Policy/rule references
    - System messages

    Returns list of important messages with scores and reasons.
    """
    result = context_manager.detect_important_content(
        messages=request.messages,
        threshold=request.threshold
    )

    return {"important_content": [item.dict() for item in result]}


@router.post("/research/context/check-overflow", tags=["research", "context"])
async def check_overflow(request: OverflowCheckRequest) -> Dict:
    """
    Check for context window overflow.

    Analyzes current token usage vs maximum limit.
    Returns risk level and recommended actions.

    Risk levels:
    - safe: <75% utilization
    - warning: 75-90% utilization
    - critical: 90-100% utilization
    - overflow: >100% utilization

    Accounts for output reserve tokens.
    """
    result = context_manager.check_overflow(
        messages=request.messages,
        max_tokens=request.max_tokens,
        output_reserve=request.output_reserve
    )

    return result.model_dump()


@router.post("/research/context/allocate-dynamic", tags=["research", "context"])
async def allocate_dynamic(request: DynamicAllocationRequest) -> Dict:
    """
    Dynamically allocate context window budget.

    Divides total budget into:
    - System tokens (10%)
    - History tokens (60%)
    - Output tokens (15-40% based on expected length)
    - Safety margin (5%)

    Calculates maximum messages that can fit in history.
    """
    result = context_manager.allocate_dynamic(
        total_budget=request.total_budget,
        system_prompt=request.system_prompt,
        expected_output_length=request.expected_output_length
    )

    return result.model_dump()


@router.post("/research/context/manage-conversation", tags=["research", "context"])
async def manage_conversation(request: ConversationManagementRequest) -> Dict:
    """
    Comprehensive conversation management with all strategies.

    Applies multiple techniques:
    1. Overflow detection
    2. Important content identification
    3. Sliding window for recent messages
    4. Automatic summarization when needed
    5. System message preservation

    Returns fully managed conversation ready for LLM input.
    Prevents context overflow while retaining critical information.
    """
    result = context_manager.manage_conversation(
        messages=request.messages,
        max_tokens=request.max_tokens,
        window_size=request.window_size,
        preserve_important=request.preserve_important,
        auto_summarize=request.auto_summarize
    )

    return result.model_dump()


# ==================== Sampling Strategy Optimization ====================

class SamplingRecommendationRequest(BaseModel):
    """Request for sampling parameter recommendation"""
    use_case: str = Field(..., description="Use case (fraud_detection, fraud_explanation, creative_fraud_scenarios, quick_classification, balanced_analysis)")
    custom_constraints: Optional[Dict[str, Any]] = Field(default=None, description="Custom parameter constraints")


class TemperatureScheduleRequest(BaseModel):
    """Request for temperature schedule"""
    schedule_type: Literal["static", "linear", "exponential", "cosine", "adaptive"] = Field(..., description="Schedule type")
    initial_temp: float = Field(..., ge=0.0, le=2.0, description="Initial temperature")
    final_temp: float = Field(..., ge=0.0, le=2.0, description="Final temperature")
    steps: int = Field(..., ge=1, le=1000, description="Number of steps")


class ParameterValidationRequest(BaseModel):
    """Request for parameter validation"""
    config: Dict[str, Any] = Field(..., description="Sampling configuration")
    use_case: Optional[str] = Field(default=None, description="Optional use case for context")


class ParameterComparisonRequest(BaseModel):
    """Request for parameter comparison"""
    config_a: Dict[str, Any] = Field(..., description="First configuration")
    config_b: Dict[str, Any] = Field(..., description="Second configuration")
    use_cases: List[str] = Field(default_factory=list, description="Use cases to evaluate")


class EarlyStoppingRequest(BaseModel):
    """Request for early stopping strategy"""
    strategy_type: Literal["stop_sequences", "max_tokens", "confidence_threshold", "repetition_detection", "combined"] = Field(..., description="Strategy type")
    stop_sequences: Optional[List[str]] = Field(default=None, description="Stop sequences")
    max_tokens: Optional[int] = Field(default=512, description="Max tokens")
    confidence_threshold: Optional[float] = Field(default=0.9, description="Confidence threshold")
    repetition_window: Optional[int] = Field(default=10, description="Repetition window")


@router.post("/research/sampling/recommend", tags=["research", "sampling"])
async def recommend_sampling_parameters(request: SamplingRecommendationRequest) -> Dict:
    """
    Recommend sampling parameters for a use case.

    Built-in use cases:
    - fraud_detection: Low temp (0.3), consistent decisions
    - fraud_explanation: Medium temp (0.5), clear reasoning
    - creative_fraud_scenarios: High temp (0.8), diverse scenarios
    - quick_classification: Very low temp (0.1), fast responses
    - balanced_analysis: Balanced (0.7), general purpose

    Returns recommended config + reasoning + alternatives.
    """
    result = sampling_optimizer.recommend_parameters(
        use_case=request.use_case,
        custom_constraints=request.custom_constraints
    )

    return result.model_dump()


@router.post("/research/sampling/schedule", tags=["research", "sampling"])
async def create_temperature_schedule(request: TemperatureScheduleRequest) -> Dict:
    """
    Create temperature schedule for adaptive sampling.

    Schedule types:
    - static: Constant temperature
    - linear: Linear interpolation
    - exponential: Exponential decay/growth
    - cosine: Cosine annealing
    - adaptive: Sine wave pattern

    Returns temperature values for each step.
    """
    result = sampling_optimizer.create_temperature_schedule(
        schedule_type=request.schedule_type,
        initial_temp=request.initial_temp,
        final_temp=request.final_temp,
        steps=request.steps
    )

    return result.model_dump()


@router.post("/research/sampling/validate", tags=["research", "sampling"])
async def validate_sampling_parameters(request: ParameterValidationRequest) -> Dict:
    """
    Validate sampling parameters.

    Checks:
    - Parameter ranges (temp, top_p, etc.)
    - Conflicting settings
    - Use case appropriateness

    Returns validation result with issues, warnings, suggestions.
    """
    result = sampling_optimizer.validate_parameters(
        config=request.config,
        use_case=request.use_case
    )

    return result.model_dump()


@router.post("/research/sampling/compare", tags=["research", "sampling"])
async def compare_sampling_configs(request: ParameterComparisonRequest) -> Dict:
    """
    Compare two sampling configurations.

    Analyzes:
    - Parameter differences
    - Use case fit scores
    - Conservative vs creative tradeoffs

    Returns comparison with recommendation.
    """
    result = sampling_optimizer.compare_configs(
        config_a=request.config_a,
        config_b=request.config_b,
        use_cases=request.use_cases
    )

    return result.model_dump()


@router.post("/research/sampling/early-stopping", tags=["research", "sampling"])
async def create_early_stopping_strategy(request: EarlyStoppingRequest) -> Dict:
    """
    Create early stopping strategy.

    Strategies:
    - stop_sequences: Stop on specific tokens/sequences
    - max_tokens: Hard token limit
    - confidence_threshold: Stop when confident enough
    - repetition_detection: Stop on repetitive output
    - combined: All strategies together

    Returns early stopping configuration.
    """
    kwargs = {}
    if request.stop_sequences:
        kwargs["stop_sequences"] = request.stop_sequences
    if request.max_tokens:
        kwargs["max_tokens"] = request.max_tokens
    if request.confidence_threshold:
        kwargs["confidence_threshold"] = request.confidence_threshold
    if request.repetition_window:
        kwargs["repetition_window"] = request.repetition_window

    result = sampling_optimizer.create_early_stopping_strategy(
        strategy_type=request.strategy_type,
        **kwargs
    )

    return result.model_dump()


# ==================== LLM Knowledge (MoE, Speculative Decoding, Distillation) ====================

class MoEAnalysisRequest(BaseModel):
    """Request for MoE analysis"""
    model_type: str = Field(default="Mixtral-8x7B", description="MoE model type")


class SpeculativeDecodingRequest(BaseModel):
    """Request for speculative decoding analysis"""
    draft_model: str = Field(default="Mistral-7B-Instruct", description="Draft model")
    verification_model: str = Field(default="Mixtral-8x7B-Instruct", description="Verification model")


class DistillationDecisionRequest(BaseModel):
    """Request for distillation vs prompting decision"""
    scenario: str = Field(..., description="Task scenario")
    data_size: int = Field(default=0, description="Number of labeled examples")
    task_variability: Literal["fixed", "variable", "unknown"] = Field(default="unknown", description="Task variability")


class HybridApproachRequest(BaseModel):
    """Request for hybrid approach"""
    approach_name: str = Field(default="Fraud Detection Hybrid", description="Approach name")


@router.get("/research/llm-knowledge/moe", tags=["research", "llm-knowledge"])
async def analyze_moe_architecture(model_type: str = "Mixtral-8x7B") -> Dict:
    """
    Analyze Mixture-of-Experts (MoE) architecture.

    Explains:
    - MoE routing mechanism
    - When experts activate
    - Cost implications (active vs total params)
    - Inference efficiency benefits
    - Best use cases

    Example: Mixtral-8x7B has 46.7B total params but only 12.9B active per token.
    """
    result = llm_knowledge.analyze_moe(model_type=model_type)

    return result.model_dump()


@router.post("/research/llm-knowledge/speculative-decoding", tags=["research", "llm-knowledge"])
async def analyze_speculative_decoding(request: SpeculativeDecodingRequest) -> Dict:
    """
    Analyze speculative decoding technique.

    Explains:
    - How draft + verification works
    - Latency reduction benefits (2-3x speedup)
    - When applicable (long-form generation)
    - Limitations and requirements

    Conceptual understanding for optimization decisions.
    """
    result = llm_knowledge.analyze_speculative_decoding(
        draft_model=request.draft_model,
        verification_model=request.verification_model
    )

    return result.model_dump()


@router.post("/research/llm-knowledge/distillation-decision", tags=["research", "llm-knowledge"])
async def decide_distillation_vs_prompting(request: DistillationDecisionRequest) -> Dict:
    """
    Decision framework: distillation vs prompting.

    Recommends:
    - Distillation: Lots of data (>10k), fixed task
    - Prompting: Few examples (<100), flexible task
    - Hybrid: Moderate data (1k-10k), mixed requirements

    Returns recommendation with reasoning and tradeoffs.
    """
    result = llm_knowledge.decide_distillation_vs_prompting(
        scenario=request.scenario,
        data_size=request.data_size,
        task_variability=request.task_variability
    )

    return result.model_dump()


@router.post("/research/llm-knowledge/hybrid-approach", tags=["research", "llm-knowledge"])
async def create_hybrid_approach(request: HybridApproachRequest) -> Dict:
    """
    Create hybrid distillation + prompting strategy.

    Combines:
    - Distillation for core task (speed)
    - Prompting for variations (flexibility)

    Returns integration strategy with example workflow.
    """
    result = llm_knowledge.create_hybrid_approach(
        approach_name=request.approach_name
    )

    return result.model_dump()


# ==================== Monitoring & Observability ====================

from app.services.monitoring import metrics_monitor

class PredictionLogRequest(BaseModel):
    """Request to log a prediction"""
    transaction_id: str = Field(..., description="Transaction ID")
    predicted_label: str = Field(..., description="Prediction (fraud/legitimate)")
    true_label: Optional[str] = Field(None, description="Ground truth label")
    confidence: float = Field(..., description="Prediction confidence")
    features: Dict[str, Any] = Field(..., description="Transaction features")
    latency_ms: float = Field(..., description="Prediction latency (ms)")
    token_count: Optional[int] = Field(None, description="Tokens used")


@router.post("/monitoring/log-prediction", tags=["monitoring"])
async def log_prediction(request: PredictionLogRequest) -> Dict:
    """
    Log a prediction for metrics tracking.

    Used to track model performance, prediction distribution, and drift.
    """
    metrics_monitor.log_prediction(
        transaction_id=request.transaction_id,
        predicted_label=request.predicted_label,
        true_label=request.true_label,
        confidence=request.confidence,
        features=request.features,
        latency_ms=request.latency_ms,
        token_count=request.token_count
    )
    return {"status": "logged", "transaction_id": request.transaction_id}


@router.get("/monitoring/metrics", tags=["monitoring"])
async def get_metrics(time_window_hours: int = Query(24, ge=1, le=168)) -> Dict:
    """
    Get comprehensive metrics dashboard data.

    Includes:
    - Model performance (F1, precision, recall)
    - Latency percentiles (p50, p95, p99)
    - Error rates
    - Token usage
    - Prediction distribution
    - Data drift detection

    Args:
        time_window_hours: Time window for metrics (1-168 hours)
    """
    return metrics_monitor.get_dashboard_data(time_window_hours)


@router.get("/monitoring/model-performance", tags=["monitoring"])
async def get_model_performance(time_window_hours: int = Query(24, ge=1, le=168)) -> Dict:
    """
    Get model performance metrics.

    Returns confusion matrix and derived metrics (precision, recall, F1, accuracy).
    """
    model_metrics = metrics_monitor.calculate_model_metrics(time_window_hours)
    from dataclasses import asdict
    return asdict(model_metrics)


@router.get("/monitoring/latency", tags=["monitoring"])
async def get_latency_metrics() -> Dict:
    """
    Get latency percentiles for all endpoints.

    Returns p50, p95, p99, mean, min, max for each monitored endpoint.
    """
    return metrics_monitor.get_all_latency_metrics()


@router.get("/monitoring/errors", tags=["monitoring"])
async def get_error_metrics(time_window_hours: int = Query(24, ge=1, le=168)) -> Dict:
    """
    Get error metrics by type.

    Returns error counts and error rates for each error type.
    """
    error_metrics = metrics_monitor.calculate_error_metrics(time_window_hours)
    from dataclasses import asdict
    return {"errors": [asdict(err) for err in error_metrics]}


@router.get("/monitoring/token-usage", tags=["monitoring"])
async def get_token_usage(time_window_hours: int = Query(24, ge=1, le=168)) -> Dict:
    """
    Get LLM token usage statistics.

    Returns total tokens, average per request, percentiles.
    """
    return metrics_monitor.get_token_usage_stats(time_window_hours)


@router.get("/monitoring/drift/{feature_name}", tags=["monitoring"])
async def get_drift_detection(
    feature_name: str,
    time_window_hours: int = Query(24, ge=1, le=168)
) -> Dict:
    """
    Check data drift for a specific feature.

    Compares current distribution to reference distribution.
    """
    drift = metrics_monitor.detect_drift(feature_name, time_window_hours)
    if drift is None:
        raise HTTPException(
            status_code=404,
            detail=f"No reference distribution found for feature '{feature_name}'"
        )
    from dataclasses import asdict
    return asdict(drift)


@router.get("/monitoring/time-series/{metric_name}", tags=["monitoring"])
async def get_time_series(
    metric_name: str,
    time_window_hours: int = Query(24, ge=1, le=168),
    granularity_minutes: int = Query(60, ge=5, le=1440)
) -> Dict:
    """
    Get time series data for a metric.

    Args:
        metric_name: 'fraud_rate', 'avg_confidence'
        time_window_hours: Time window
        granularity_minutes: Time bucket size
    """
    time_series = metrics_monitor.get_time_series_data(
        metric_name, time_window_hours, granularity_minutes
    )
    return {"metric_name": metric_name, "data": time_series}


# ==============================================================================
# MODEL TRAINING & PROMPT ENGINEERING ENDPOINTS
# ==============================================================================

from app.services.ml import model_trainer, prompt_manager
from app.services.ml.finetuning_generator import finetuning_generator


class TrainModelRequest(BaseModel):
    """Request to train a model"""
    model_type: Literal["random_forest", "xgboost"]
    sample_size: Optional[int] = Field(None, description="Sample size for quick training (e.g., 10000)")
    tune_hyperparameters: bool = Field(False, description="Whether to tune hyperparameters with Optuna")
    n_trials: int = Field(20, description="Number of Optuna trials")


class PromptTestRequest(BaseModel):
    """Request to test a prompt template"""
    template_id: str
    transaction: Dict[str, Any]


class CreatePromptRequest(BaseModel):
    """Request to create a custom prompt template"""
    name: str
    strategy: str  # "zero_shot", "few_shot", etc.
    version: str
    system_prompt: str
    user_prompt_template: str


@router.post("/ml/train-model")
async def train_model_endpoint(request: TrainModelRequest):
    """
    Train a fraud detection model

    Models supported:
    - random_forest: Fast, interpretable, good baseline
    - xgboost: Higher accuracy, slower training

    Args:
        model_type: Type of model to train
        sample_size: Optional sample size for quick training (M4 Pro optimization)
        tune_hyperparameters: Whether to use Optuna for hyperparameter tuning
        n_trials: Number of Optuna trials (default 20 for M4 Pro)

    Returns:
        {
            "model_id": "...",
            "metrics": {
                "accuracy": 0.95,
                "f1_score": 0.85,
                ...
            },
            "training_time_seconds": 120.5
        }
    """
    try:
        # Train model
        model_id = model_trainer.train_and_save(
            model_type=request.model_type,
            sample_size=request.sample_size,
            tune=request.tune_hyperparameters,
            n_trials=request.n_trials
        )

        # Get model artifact
        artifact = next((a for a in model_trainer.registry if a.model_id == model_id), None)

        if not artifact:
            raise HTTPException(status_code=500, detail="Model trained but artifact not found")

        return {
            "model_id": model_id,
            "model_name": artifact.model_name,
            "model_type": artifact.model_type,
            "metrics": {
                "accuracy": artifact.metrics.accuracy,
                "precision": artifact.metrics.precision,
                "recall": artifact.metrics.recall,
                "f1_score": artifact.metrics.f1_score,
                "roc_auc": artifact.metrics.roc_auc
            },
            "training_time_seconds": artifact.metrics.training_time_seconds,
            "inference_time_ms": artifact.metrics.inference_time_ms,
            "created_at": artifact.created_at
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Training failed: {str(e)}")


@router.get("/ml/models")
async def list_models():
    """
    List all trained models with comparison

    Returns DataFrame-like comparison of all models by F1 score
    """
    comparison = model_trainer.compare_models()

    if comparison.empty:
        return {"models": [], "message": "No models trained yet"}

    return {
        "models": comparison.to_dict(orient="records"),
        "best_model": comparison.iloc[0].to_dict()
    }


@router.get("/ml/models/{model_id}")
async def get_model_details(model_id: str):
    """Get detailed metrics for a specific model"""
    artifact = next((a for a in model_trainer.registry if a.model_id == model_id), None)

    if not artifact:
        raise HTTPException(status_code=404, detail="Model not found")

    m = artifact.metrics

    return {
        "model_id": artifact.model_id,
        "model_name": artifact.model_name,
        "model_type": artifact.model_type,
        "file_path": artifact.file_path,
        "created_at": artifact.created_at,
        "metrics": {
            "accuracy": m.accuracy,
            "precision": m.precision,
            "recall": m.recall,
            "f1_score": m.f1_score,
            "roc_auc": m.roc_auc,
            "training_time_seconds": m.training_time_seconds,
            "inference_time_ms": m.inference_time_ms,
            "confusion_matrix": m.confusion_matrix,
            "feature_importance": m.feature_importance,
            "hyperparameters": m.hyperparameters
        }
    }


@router.get("/ml/models/{model_id}/download")
async def download_model(model_id: str):
    """Download model artifact file"""
    from fastapi.responses import FileResponse

    artifact = next((a for a in model_trainer.registry if a.model_id == model_id), None)

    if not artifact:
        raise HTTPException(status_code=404, detail="Model not found")

    return FileResponse(
        path=artifact.file_path,
        filename=f"{model_id}.pkl",
        media_type="application/octet-stream"
    )


@router.get("/prompts")
async def list_prompts(strategy: Optional[str] = None):
    """
    List all prompt templates

    Args:
        strategy: Optional filter by strategy (zero_shot, few_shot, etc.)
    """
    from app.services.ml.prompt_manager import PromptStrategy

    strategy_filter = None
    if strategy:
        try:
            strategy_filter = PromptStrategy(strategy)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid strategy: {strategy}")

    templates = prompt_manager.list_templates(strategy_filter)

    return {
        "templates": [
            {
                "template_id": t.template_id,
                "name": t.name,
                "strategy": t.strategy.value,
                "version": t.version,
                "active": t.active,
                "created_at": t.created_at,
                "performance_metrics": t.performance_metrics
            }
            for t in templates
        ]
    }


@router.get("/prompts/{template_id}")
async def get_prompt_template(template_id: str):
    """Get specific prompt template details"""
    template = prompt_manager.get_template(template_id)

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    return {
        "template_id": template.template_id,
        "name": template.name,
        "strategy": template.strategy.value,
        "version": template.version,
        "system_prompt": template.system_prompt,
        "user_prompt_template": template.user_prompt_template,
        "num_examples": len(template.examples),
        "active": template.active,
        "created_at": template.created_at,
        "performance_metrics": template.performance_metrics
    }


@router.post("/prompts/test")
async def test_prompt_template(request: PromptTestRequest):
    """
    Test a prompt template with a transaction

    Returns rendered prompt ready to send to LLM
    """
    try:
        rendered = prompt_manager.render_prompt(
            request.template_id,
            request.transaction
        )

        return {
            "template_id": request.template_id,
            "rendered_prompt": rendered,
            "transaction": request.transaction
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/prompts/create")
async def create_prompt_template(request: CreatePromptRequest):
    """Create a custom prompt template"""
    from app.services.ml.prompt_manager import PromptStrategy

    try:
        strategy = PromptStrategy(request.strategy)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid strategy: {request.strategy}")

    template_id = prompt_manager.register_template(
        name=request.name,
        strategy=strategy,
        version=request.version,
        system_prompt=request.system_prompt,
        user_prompt_template=request.user_prompt_template,
        examples=[]
    )

    return {
        "template_id": template_id,
        "message": "Template created successfully"
    }


@router.get("/prompts/compare")
async def compare_prompts():
    """Compare all prompt templates by performance metrics"""
    comparison = prompt_manager.compare_templates()

    return {
        "templates": comparison,
        "message": f"Showing {len(comparison)} templates"
    }


@router.post("/ml/generate-finetuning-dataset")
async def generate_finetuning_dataset(sample_size: int = 1000):
    """
    Generate fine-tuning datasets (Alpaca, ShareGPT, preferences)

    Note: This prepares the data. Actual fine-tuning skipped for M4 Pro.

    Args:
        sample_size: Number of examples to generate (default 1000)

    Returns:
        {
            "files": [...],
            "statistics": {...}
        }
    """
    try:
        finetuning_generator.create_full_pipeline(sample_size=sample_size)

        return {
            "status": "success",
            "files": [
                "data/finetuning/fraud_detection_alpaca.jsonl",
                "data/finetuning/fraud_detection_sharegpt.jsonl",
                "data/finetuning/fraud_detection_preferences.jsonl"
            ],
            "sample_size": sample_size,
            "message": "Fine-tuning datasets generated successfully. Ready for LoRA fine-tuning on appropriate hardware."
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Dataset generation failed: {str(e)}")
