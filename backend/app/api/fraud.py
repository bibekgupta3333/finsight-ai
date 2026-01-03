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
from typing import Optional, Dict, Any, List

from fastapi import APIRouter, Header, HTTPException, Request, status, WebSocket, WebSocketDisconnect
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
                    "timestamp": "2026-01-02T10:30:00Z"
                }
            ]
        }


@router.post(
    "/prompts/build",
    summary="Build hierarchical prompt",
    description="Build complete prompt with system/developer/user hierarchy",
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
    summary="Analyze with ReAct pattern",
    description="Use ReAct (Reasoning + Acting) pattern for fraud analysis",
)
async def analyze_with_react(request: FraudAnalysisRequest):
    """
    Analyze transaction using ReAct pattern.

    Interleaves reasoning (thoughts) with actions (tool calls).
    """
    logger.info("Starting ReAct analysis")

    # Mock tools for ReAct
    async def calculate_risk_score(**kwargs):
        return {"risk_score": 75.0, "factors": ["high_amount", "balance_inconsistency"]}

    async def query_fraud_policy(**kwargs):
        return {"policy": "TRANSFER > 100k = high risk", "threshold_exceeded": True}

    async def check_history(**kwargs):
        return {"similar_transactions": 0, "fraud_history": False}

    tools = {
        "calculate_risk_score": calculate_risk_score,
        "query_fraud_policy": query_fraud_policy,
        "check_history": check_history,
    }

    # Execute ReAct
    react = ReActPattern(max_steps=5)
    llm_client = get_llm_client()

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
    summary="Analyze with Chain-of-Thought",
    description="Use Chain-of-Thought reasoning for fraud analysis",
)
async def analyze_with_cot(request: FraudAnalysisRequest):
    """Analyze transaction using Chain-of-Thought pattern."""
    logger.info("Starting CoT analysis")

    cot = ChainOfThoughtPattern(steps_required=5)
    llm_client = get_llm_client()

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
    summary="Analyze with Tree-of-Thought",
    description="Explore multiple reasoning paths and select the best one",
)
async def analyze_with_tot(request: FraudAnalysisRequest):
    """Analyze transaction using Tree-of-Thought pattern."""
    logger.info("Starting ToT analysis")

    tot = TreeOfThoughtPattern(branching_factor=3, max_depth=3)
    llm_client = get_llm_client()

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
    summary="Analyze with Debate pattern",
    description="Prosecutor vs Defense agents debate, judge decides",
)
async def analyze_with_debate(request: FraudAnalysisRequest):
    """Analyze transaction using Debate pattern."""
    logger.info("Starting Debate analysis")

    debate = DebatePattern(rounds=2)
    llm_client = get_llm_client()

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
    summary="Analyze with Self-Critique",
    description="Generate → Critique → Revise loop for better accuracy",
)
async def analyze_with_self_critique(request: FraudAnalysisRequest):
    """Analyze transaction using Self-Critique pattern."""
    logger.info("Starting Self-Critique analysis")

    self_critique = SelfCritiquePattern()
    llm_client = get_llm_client()

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
                        "transaction_id": "TX_REFLECTION_001",
                        "type": "TRANSFER",
                        "amount": 145000.0,
                        "oldbalanceOrg": 160000.0,
                        "newbalanceOrig": 15000.0,
                        "oldbalanceDest": 5000.0,
                        "newbalanceDest": 150000.0
                    },
                    "initial_decision": {
                        "is_fraud": True,
                        "risk_score": 88.5,
                        "confidence": 0.87,
                        "reasoning": "Large transfer draining 91% of origin balance"
                    }
                }
            ]
        }


@router.post(
    "/analyze/reflection",
    summary="Validate decision with Reflection",
    description="Reflect on decision against policies and reasoning chain",
)
async def analyze_with_reflection(
    request: ReflectionRequest,
):
    """Validate decision using Reflection pattern."""
    logger.info("Starting Reflection validation")

    llm_client = get_llm_client()

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
                    "max_tokens": 1500
                }
            ]
        }


@router.post(
    "/prompts/compress",
    summary="Compress prompt",
    description="Compress prompt while preserving critical information",
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
                            "Reviewed fraud policies: Exceeds high-risk threshold"
                        ]
                    }
                }
            ]
        }


@router.post(
    "/prompts/validate-output",
    summary="Validate LLM output",
    description="Validate LLM output against fraud decision schema",
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
                    "transaction_id": "TX_AGENT_001",
                    "amount": 165000.0,
                    "type": "TRANSFER",
                    "oldbalanceOrg": 180000.0,
                    "newbalanceOrig": 15000.0,
                    "oldbalanceDest": 5000.0,
                    "newbalanceDest": 170000.0,
                    "nameOrig": "C1231231230",
                    "nameDest": "C9879879870"
                }
            ]
        }


@router.post(
    "/agents/single",
    summary="Single-agent fraud analysis",
    description="Analyze transaction using single autonomous agent with observation, planning, execution, reasoning, decision, and reflection",
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
)
async def analyze_with_swarm(request: AgentAnalysisRequest, swarm_size: int = 5, threshold: float = 0.6):
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
                detail=f"Invalid memory type. Must be one of: SHORT_TERM, WORKING, LONG_TERM"
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
                        "balance_drain_ratio": 0.92
                    }
                }
            ]
        }


@router.post(
    "/agents/tools/execute",
    summary="Execute agent tool manually",
    description="Execute a specific agent tool for testing/debugging",
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
        raise HTTPException(
            status_code=500,
            detail=f"Tool execution failed: {str(e)}"
        )


# ==================== Planning & Reasoning Endpoints ====================


@router.post(
    "/planning/create-plan",
    summary="Create task execution plan",
    description="Generate DAG-based execution plan for fraud analysis",
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
            transaction=transaction,
            goal="determine_fraud",
            constraints={"max_duration": 30.0}
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
        raise HTTPException(
            status_code=500,
            detail=f"Plan creation failed: {str(e)}"
        )


@router.post(
    "/reasoning/test-hypothesis",
    summary="Test fraud hypothesis",
    description="Test hypothesis against evidence using structured reasoning",
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
        raise HTTPException(
            status_code=500,
            detail=f"Hypothesis testing failed: {str(e)}"
        )


@router.post(
    "/reasoning/counterfactual",
    summary="Counterfactual reasoning",
    description="Perform what-if analysis on transaction",
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
        raise HTTPException(
            status_code=500,
            detail=f"Counterfactual analysis failed: {str(e)}"
        )


@router.post(
    "/reasoning/self-critique",
    summary="Self-critique reasoning",
    description="Critique agent's reasoning for soundness and completeness",
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
        raise HTTPException(
            status_code=500,
            detail=f"Self-critique failed: {str(e)}"
        )


@router.post(
    "/reasoning/estimate-uncertainty",
    summary="Estimate decision uncertainty",
    description="Quantify uncertainty from multiple sources",
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
        raise HTTPException(
            status_code=500,
            detail=f"Uncertainty estimation failed: {str(e)}"
        )


@router.post(
    "/reasoning/check-constraints",
    summary="Check constraint satisfaction",
    description="Validate decision against hard and soft constraints",
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
        raise HTTPException(
            status_code=500,
            detail=f"Constraint checking failed: {str(e)}"
        )


# ==================== Autonomy Control Endpoints ====================


@router.post(
    "/autonomy/get-level",
    summary="Get autonomy level",
    description="Determine appropriate autonomy level for decision",
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
            status_code=500,
            detail=f"Autonomy level determination failed: {str(e)}"
        )


@router.post(
    "/autonomy/check-escalation",
    summary="Check if should escalate",
    description="Determine if decision should be escalated to human",
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
        raise HTTPException(
            status_code=500,
            detail=f"Escalation check failed: {str(e)}"
        )


@router.post(
    "/autonomy/check-stop-conditions",
    summary="Check stop conditions",
    description="Check if agent should stop execution",
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
            "condition": {
                "type": condition.type.value,
                "triggered": condition.triggered,
                "threshold": condition.threshold,
                "current_value": condition.current_value,
                "message": condition.message,
            } if condition else None,
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Stop condition check failed: {str(e)}"
        )


@router.post(
    "/autonomy/check-goal-drift",
    summary="Check goal drift",
    description="Detect if agent has drifted from original goal",
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
        raise HTTPException(
            status_code=500,
            detail=f"Goal drift check failed: {str(e)}"
        )


# ============================================================================
# Section 3.7: Tool & Failure Recovery Endpoints
# ============================================================================

@router.post(
    "/recovery/check-health",
    summary="Check tool health",
    description="Run health check for a tool",
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
        raise HTTPException(
            status_code=500,
            detail=f"Health check failed: {str(e)}"
        )


@router.post(
    "/recovery/analyze-failure",
    summary="Analyze failure root cause",
    description="Perform root cause analysis on a failure",
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
        raise HTTPException(
            status_code=500,
            detail=f"Root cause analysis failed: {str(e)}"
        )


@router.post(
    "/recovery/register-fallback",
    summary="Register fallback chain",
    description="Register fallback chain for a tool",
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
        raise HTTPException(
            status_code=500,
            detail=f"Fallback registration failed: {str(e)}"
        )


@router.post(
    "/recovery/aggregate-partial",
    summary="Aggregate partial results",
    description="Aggregate partial results from failed operations",
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
        raise HTTPException(
            status_code=500,
            detail=f"Partial result aggregation failed: {str(e)}"
        )


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
        raise HTTPException(
            status_code=500,
            detail=f"Health status retrieval failed: {str(e)}"
        )


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
        raise HTTPException(
            status_code=500,
            detail=f"Incident retrieval failed: {str(e)}"
        )


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
        raise HTTPException(
            status_code=500,
            detail=f"Statistics retrieval failed: {str(e)}"
        )


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
        raise HTTPException(
            status_code=500,
            detail=f"Task submission failed: {str(e)}"
        )


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
        raise HTTPException(
            status_code=500,
            detail=f"Task retrieval failed: {str(e)}"
        )


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
        raise HTTPException(
            status_code=500,
            detail=f"Task cancellation failed: {str(e)}"
        )


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
        raise HTTPException(
            status_code=500,
            detail=f"Statistics retrieval failed: {str(e)}"
        )


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
                await websocket.send_json({
                    "type": "subscribed",
                    "topic": topic,
                })

            elif data.get("action") == "unsubscribe":
                topic = data.get("topic")
                await _websocket_manager.unsubscribe(client_id, topic)
                await websocket.send_json({
                    "type": "unsubscribed",
                    "topic": topic,
                })

    except WebSocketDisconnect:
        _websocket_manager.disconnect(client_id)
    except Exception as e:
        logger.error(f"WebSocket error for client {client_id}: {e}")
        _websocket_manager.disconnect(client_id)


@router.post(
    "/async/broadcast",
    summary="Broadcast to WebSocket clients",
    description="Broadcast message to WebSocket subscribers",
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
        raise HTTPException(
            status_code=500,
            detail=f"Broadcast failed: {str(e)}"
        )


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
        raise HTTPException(
            status_code=500,
            detail=f"Statistics retrieval failed: {str(e)}"
        )


@router.get(
    "/async/stream/{topic}",
    summary="Server-Sent Events stream",
    description="Stream events via Server-Sent Events",
)
async def sse_stream(topic: str, interval: float = 1.0, max_events: int = 10):
    """Server-Sent Events endpoint."""
    if not SSE_AVAILABLE:
        raise HTTPException(
            status_code=501,
            detail="SSE not available. Install sse-starlette package."
        )

    try:
        return EventSourceResponse(
            sse_event_generator(topic, interval, max_events)
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"SSE stream failed: {str(e)}"
        )


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
        raise HTTPException(
            status_code=500,
            detail=f"Statistics retrieval failed: {str(e)}"
        )


@router.post(
    "/async/cleanup-resources",
    summary="Cleanup idle resources",
    description="Cleanup idle resources",
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
        raise HTTPException(
            status_code=500,
            detail=f"Resource cleanup failed: {str(e)}"
        )


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
                        "transaction_id": "TX_TOOL_TEST_001",
                        "amount": 125000.0,
                        "transaction_type": "TRANSFER",
                        "oldbalance_org": 150000.0,
                        "newbalance_orig": 25000.0,
                        "oldbalance_dest": 0.0,
                        "newbalance_dest": 125000.0,
                        "step": 120,
                    },
                    "max_retries": 3,
                }
            ]
        }


@router.post(
    "/tools/execute",
    summary="Execute a tool",
    description="Execute tool with retry and confidence tracking (Section 3.3.1)",
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
                }
            ]
        }


@router.post(
    "/tools/set-allowed",
    summary="Set allowed tools",
    description="Restrict tool set to prevent hallucination (Section 3.3.1)",
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
            "examples": [{"file_path": "transfer_fraud_policy.md"}]
        }


@router.post(
    "/environment/read-file",
    summary="Read policy file (sandboxed)",
    description="Read fraud policy file from sandboxed directory (Section 3.3.2)",
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
    context: Optional[Dict[str, Any]] = Field(default=None, description="Optional context variables")
    timeout_seconds: int = Field(default=5, description="Execution timeout", ge=1, le=10)

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "code": "# Calculate balance drain ratio\noldbalance = 150000.0\nnewbalance = 25000.0\nbalance_drain = (oldbalance - newbalance) / oldbalance if oldbalance > 0 else 0\nrisk_score = min(balance_drain * 100, 100)\nresult = {'balance_drain_ratio': balance_drain, 'risk_score': risk_score}",
                    "context": {},
                    "timeout_seconds": 5,
                }
            ]
        }


@router.post(
    "/environment/execute-code",
    summary="Execute Python code (sandboxed)",
    description="Execute Python code for risk calculations with strict sandboxing (Section 3.3.2)",
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
                }
            ]
        }


@router.post(
    "/environment/execute-sql",
    summary="Execute SQL query (read-only)",
    description="Execute read-only SQL query with validation (Section 3.3.2)",
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
