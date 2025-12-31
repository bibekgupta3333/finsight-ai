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
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Request, status

from app.core.checkpoint import Checkpoint
from app.core.circuit_breaker import get_circuit_breaker
from app.core.retry import RetryConfig, retry_with_backoff
from app.core.session import get_session_manager
from app.core.state_machine import AgentState
from app.core.task_queue import get_task_queue
from app.middleware import get_correlation_id
from app.models.fraud import (
    BatchFraudAnalysisRequest,
    BatchFraudAnalysisResponse,
    FraudAnalysisRequest,
    FraudAnalysisResponse,
    TaskStatusResponse,
)
from app.services.fraud_detection import get_fraud_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/fraud", tags=["fraud-detection"])


@router.post(
    "/analyze",
    response_model=FraudAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Analyze single transaction for fraud",
    description=(
        "Analyzes a single transaction for fraud using async processing. "
        "Returns fraud prediction with confidence score and explanation."
    ),
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
        task_id = await task_queue.submit_task(
            fraud_service.analyze_batch,
            request.transactions,
            client_id=request.client_id,
        )

        # Estimate completion time (rough estimate)
        estimated_time = len(request.transactions) * 0.15  # 150ms per transaction

        logger.info(
            f"Batch analysis submitted: task_id={task_id}, "
            f"transactions={len(request.transactions)}, "
            f"client={request.client_id}"
        )

        return BatchFraudAnalysisResponse(
            task_id=task_id,
            status="pending",
            message=f"Batch analysis of {len(request.transactions)} transactions submitted",
            estimated_completion_seconds=estimated_time,
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

        return TaskStatusResponse(
            task_id=task_result.task_id,
            status=task_result.status.value,
            created_at=task_result.created_at,
            started_at=task_result.started_at,
            completed_at=task_result.completed_at,
            result=task_result.result if task_result.status.value == "completed" else None,
            error=task_result.error,
        )

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
    summary="Get fraud detection statistics",
    description="Returns service statistics including queue status and analysis metrics.",
)
async def get_stats():
    """
    Get fraud detection service statistics.

    Returns:
        Statistics dictionary
    """
    try:
        task_queue = await get_task_queue()
        fraud_service = get_fraud_service()

        queue_stats = task_queue.get_stats()
        service_stats = await fraud_service.get_stats()

        return {
            "queue": queue_stats,
            "service": service_stats,
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
