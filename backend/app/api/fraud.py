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
from pydantic import BaseModel

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


@router.post(
    "/prompts/build",
    summary="Build hierarchical prompt",
    description="Build complete prompt with system/developer/user hierarchy",
)
async def build_hierarchical_prompt(transaction: dict):
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


@router.post(
    "/prompts/compress",
    summary="Compress prompt",
    description="Compress prompt while preserving critical information",
)
async def compress_prompt(prompt_text: dict):
    """Compress a prompt to fit token budget."""
    text = prompt_text.get("text", "")
    max_tokens = prompt_text.get("max_tokens", 1500)

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


@router.post(
    "/prompts/validate-output",
    summary="Validate LLM output",
    description="Validate LLM output against fraud decision schema",
)
async def validate_llm_output(output: dict):
    """Validate LLM output against schema."""
    output_json = json.dumps(output.get("output", {}))
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


@router.post(
    "/agents/tools/execute",
    summary="Execute agent tool manually",
    description="Execute a specific agent tool for testing/debugging",
)
async def execute_agent_tool(tool_name: str, parameters: dict):
    """Execute an agent tool manually."""
    from app.agents.tool_registry import get_tool_registry

    registry = get_tool_registry()

    try:
        result = await registry.execute(tool_name, parameters)

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

