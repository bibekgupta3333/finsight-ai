"""
LLM Engineering API routes.

Implements endpoints for LLM Fundamentals testing:
- Token analysis and context management
- Sampling configuration testing
- Model routing decisions
- Safety checks (hallucination, prompt injection)
- Self-consistency testing
"""

import logging
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.services.llm_client import get_llm_client
from app.services.llm_safety import get_llm_safety
from app.services.model_router import get_model_router
from app.services.sampling_config import (
    MultiSampleGenerator,
    SamplingMode,
    explain_sampling_tradeoffs,
    get_sampling_for_mode,
    get_sampling_for_task,
)
from app.services.token_analyzer import get_token_analyzer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/llm", tags=["llm-engineering"])


# ============================================================================
#  REQUEST/RESPONSE MODELS (defined inline to avoid gitignore issues)
# ============================================================================


class TokenAnalysisResponse(BaseModel):
    """Token analysis response."""

    token_count: int
    max_tokens: int
    context_usage_percent: float
    is_within_limit: bool
    optimization_suggestions: List[str]
    complexity: str

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "token_count": 23,
                    "max_tokens": 32768,
                    "context_usage_percent": 0.07,
                    "is_within_limit": True,
                    "optimization_suggestions": [
                        "Prompt is concise and within limits",
                        "Consider caching for repeated queries"
                    ],
                    "complexity": "low"
                }
            ]
        }


class SamplingConfigRequest(BaseModel):
    """Sampling configuration request."""

    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    top_p: Optional[float] = Field(None, ge=0.0, le=1.0)
    top_k: Optional[int] = Field(None, ge=0)
    seed: Optional[int] = None
    mode: Optional[str] = None

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "temperature": 0.0,
                    "top_p": 1.0,
                    "top_k": 50,
                    "seed": 42,
                    "mode": "deterministic",
                }
            ]
        }


class TransactionRequest(BaseModel):
    """Transaction request for LLM analysis."""

    transaction_id: str
    type: str
    amount: float
    oldbalanceOrg: Optional[float] = None
    newbalanceOrig: Optional[float] = None
    oldbalanceDest: Optional[float] = None
    newbalanceDest: Optional[float] = None

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "transaction_id": "TX_LLM_TEST_001",
                    "type": "CASH_OUT",
                    "amount": 175000.0,
                    "oldbalanceOrg": 190000.0,
                    "newbalanceOrig": 15000.0,
                    "oldbalanceDest": 0.0,
                    "newbalanceDest": 0.0,
                }
            ]
        }


class ModelRoutingResponse(BaseModel):
    """Model routing response."""

    selected_model: str
    recommendation: str
    complexity_score: int
    estimated_latency_ms: int
    reasoning: List[str]
    use_streaming: bool

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "selected_model": "qwen3:0.6b",
                    "recommendation": "Use fast model for quick fraud detection",
                    "complexity_score": 3,
                    "estimated_latency_ms": 2000,
                    "reasoning": [
                        "High transaction amount ($175,000) requires analysis",
                        "Balance inconsistency detected (92% drain)",
                        "Fast model sufficient for pattern matching"
                    ],
                    "use_streaming": True
                }
            ]
        }


class SafetyCheckRequest(BaseModel):
    """Safety check request."""

    transaction: TransactionRequest
    llm_response: str

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "transaction": {
                        "transaction_id": "TX_SAFETY_001",
                        "type": "TRANSFER",
                        "amount": 85000.0,
                        "oldbalanceOrg": 100000.0,
                        "newbalanceOrig": 15000.0,
                        "oldbalanceDest": 20000.0,
                        "newbalanceDest": 105000.0,
                    },
                    "llm_response": "This transaction appears fraudulent. The large transfer of $85,000 from an account with $100,000 to a destination account is suspicious. CONFIDENCE: 0.95",
                }
            ]
        }


class SafetyCheckResponse(BaseModel):
    """Safety check response."""

    hallucination_detected: bool
    injection_detected: bool
    refusal_detected: bool
    hallucinations: List[dict]
    injections: List[dict]
    recommendation: str

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "hallucination_detected": False,
                    "injection_detected": False,
                    "refusal_detected": False,
                    "hallucinations": [],
                    "injections": [],
                    "recommendation": "Response is safe and accurate. No hallucinations or injection attempts detected."
                }
            ]
        }


# ============================================================================
# TOKEN ANALYSIS ENDPOINTS (Section 3.1.1)
# ============================================================================


@router.get(
    "/token-analysis",
    response_model=TokenAnalysisResponse,
    summary="Analyze token usage for a prompt",
    description="Demonstrates token counting, context window validation, and optimization suggestions",
)
async def analyze_tokens(
    prompt: str = Query(..., description="Prompt text to analyze"),
    max_tokens: Optional[int] = Query(None, description="Optional max token override"),
) -> TokenAnalysisResponse:
    """
    Analyze token usage for a given prompt.

    AGI Interview Signal: "I understand tokenization and context management"
    """
    try:
        analyzer = get_token_analyzer()

        # Count tokens
        token_count = analyzer.count_tokens(prompt)

        # Analyze complexity
        complexity_analysis = analyzer.analyze_prompt_complexity(prompt)

        # Check context window
        validation = analyzer.validate_context_window(
            [{"role": "user", "content": prompt}], max_tokens=max_tokens
        )

        logger.info(
            f"Token analysis: {token_count} tokens, "
            f"{validation['usage_percent']:.1f}% context usage"
        )

        return TokenAnalysisResponse(
            token_count=token_count,
            max_tokens=validation["max_tokens"],
            context_usage_percent=validation["usage_percent"],
            is_within_limit=validation["is_valid"],
            optimization_suggestions=complexity_analysis["recommendations"],
            complexity=complexity_analysis["complexity"],
        )

    except Exception as e:
        logger.error(f"Token analysis failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Token analysis failed: {str(e)}",
        )


# ============================================================================
# SAMPLING CONFIGURATION ENDPOINTS (Section 3.1.2)
# ============================================================================


@router.post(
    "/test-sampling",
    summary="Test sampling configurations",
    description="Generate multiple samples with different sampling parameters",
)
async def test_sampling(
    transaction: TransactionRequest,
    sampling_mode: str = Query("deterministic", description="Sampling mode"),
    num_samples: int = Query(3, ge=1, le=10, description="Number of samples to generate"),
) -> Dict:
    """
    Test sampling configurations with self-consistency.

    AGI Interview Signal: "I understand temperature, top-p, and determinism control"
    """
    try:
        # Get sampling config for mode
        try:
            mode = SamplingMode(sampling_mode.lower())
            config = get_sampling_for_mode(mode)
        except Exception:
            # Default to deterministic
            config = get_sampling_for_task("classification")

        # Create simple prompt
        prompt = f"""Analyze this transaction for fraud:
Type: {transaction.type}
Amount: ${transaction.amount:,.2f}
Balance Change: ${transaction.oldbalanceOrg or 0 - transaction.newbalanceOrig or 0:,.2f}

Is this fraud? Answer 'YES' or 'NO' and explain briefly."""

        # Generate multiple samples
        llm = await get_llm_client()
        generator = MultiSampleGenerator()

        samples = await generator.generate_multiple(
            llm_client=llm,
            prompt=prompt,
            num_samples=num_samples,
            temperature=config.temperature,
            top_p=config.top_p,
            top_k=config.top_k,
        )

        # Perform majority voting
        vote_result = generator.majority_vote(samples, key="response")

        # Explain tradeoffs
        tradeoffs = explain_sampling_tradeoffs(config)

        logger.info(
            f"Sampling test: {num_samples} samples, "
            f"mode={sampling_mode}, confidence={vote_result['confidence']:.2f}"
        )

        return {
            "transaction_id": transaction.transaction_id,
            "sampling_config": {
                "temperature": config.temperature,
                "top_p": config.top_p,
                "top_k": config.top_k,
                "seed": config.seed,
                "mode": sampling_mode,
            },
            "num_samples": num_samples,
            "samples": [s.get("response", "") for s in samples],
            "majority_vote": vote_result,
            "tradeoffs": tradeoffs,
        }

    except Exception as e:
        logger.error(f"Sampling test failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Sampling test failed: {str(e)}",
        )


# ============================================================================
# MODEL ROUTING ENDPOINTS (Section 3.1.3)
# ============================================================================


@router.post(
    "/model-routing",
    response_model=ModelRoutingResponse,
    summary="Get model routing recommendation",
    description="Demonstrates latency vs quality tradeoffs with intelligent model selection",
)
async def get_routing_recommendation(transaction: TransactionRequest) -> ModelRoutingResponse:
    """
    Get model routing recommendation for a transaction.

    AGI Interview Signal: "I understand latency-quality tradeoffs"
    """
    try:
        router_service = get_model_router()

        # Convert to internal transaction format
        from app.models.fraud import Transaction

        txn = Transaction(
            transaction_id=transaction.transaction_id,
            type=transaction.type,
            amount=transaction.amount,
            oldbalanceOrg=transaction.oldbalanceOrg or 0.0,
            newbalanceOrig=transaction.newbalanceOrig or 0.0,
            oldbalanceDest=transaction.oldbalanceDest or 0.0,
            newbalanceDest=transaction.newbalanceDest or 0.0,
        )

        # Get routing decision
        routing = router_service.route_to_model(txn)

        logger.info(
            f"Model routing: {routing['selected_model']} "
            f"(complexity={routing['complexity_score']})"
        )

        return ModelRoutingResponse(**routing)

    except Exception as e:
        logger.error(f"Model routing failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Model routing failed: {str(e)}",
        )


@router.get(
    "/cache-stats",
    summary="Get caching statistics",
    description="Shows caching effectiveness for latency optimization",
)
async def get_cache_stats() -> Dict:
    """
    Get cache statistics from model router.

    Demonstrates caching for latency optimization.
    """
    try:
        router_service = get_model_router()
        stats = router_service.get_cache_stats()

        return {
            "cache_stats": stats,
            "caching_enabled": True,
            "ttl_seconds": stats["pattern_cache_ttl"],
        }

    except Exception as e:
        logger.error(f"Cache stats retrieval failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Cache stats failed: {str(e)}",
        )


# ============================================================================
# SAFETY CHECK ENDPOINTS (Section 3.1.4)
# ============================================================================


@router.post(
    "/test-safety",
    response_model=SafetyCheckResponse,
    summary="Test LLM safety checks",
    description="Demonstrates hallucination detection, prompt injection prevention, and refusal handling",
)
async def test_safety(request: SafetyCheckRequest) -> SafetyCheckResponse:
    """
    Test LLM safety mechanisms.

    AGI Interview Signal: "I understand LLM failure modes and build safety guardrails"
    """
    try:
        safety = get_llm_safety()

        # Convert to internal transaction format
        from app.models.fraud import Transaction

        txn = Transaction(
            transaction_id=request.transaction.transaction_id,
            type=request.transaction.type,
            amount=request.transaction.amount,
            oldbalanceOrg=request.transaction.oldbalanceOrg or 0.0,
            newbalanceOrig=request.transaction.newbalanceOrig or 0.0,
            oldbalanceDest=request.transaction.oldbalanceDest or 0.0,
            newbalanceDest=request.transaction.newbalanceDest or 0.0,
        )

        # Hallucination detection
        hall_check = safety.detect_hallucination(request.llm_response, txn)

        # Prompt injection check (on transaction description if present)
        injection_check = safety.check_prompt_injection(request.llm_response)

        # Refusal detection
        refusal_check = safety.check_refusal(request.llm_response)

        # Determine overall recommendation
        if hall_check["hallucination_detected"] and hall_check["severity"] == "critical":
            recommendation = "reject"
        elif injection_check["injection_detected"]:
            recommendation = "sanitize"
        elif refusal_check["refused"]:
            recommendation = "fallback_to_rules"
        elif hall_check["hallucination_detected"]:
            recommendation = "review"
        else:
            recommendation = "accept"

        logger.info(
            f"Safety check: hallucination={hall_check['hallucination_detected']}, "
            f"injection={injection_check['injection_detected']}, "
            f"refusal={refusal_check['refused']}"
        )

        return SafetyCheckResponse(
            hallucination_detected=hall_check["hallucination_detected"],
            injection_detected=injection_check["injection_detected"],
            refusal_detected=refusal_check["refused"],
            hallucinations=hall_check["hallucinations"],
            injections=injection_check["injections"],
            recommendation=recommendation,
        )

    except Exception as e:
        logger.error(f"Safety check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Safety check failed: {str(e)}",
        )


@router.post(
    "/prompt-compression",
    summary="Test prompt compression",
    description="Demonstrates prompt optimization for latency improvement",
)
async def test_prompt_compression(
    prompt: str = Query(..., description="Prompt to compress")
) -> Dict:
    """
    Test prompt compression for latency optimization.

    AGI Interview Signal: "I optimize prompts for production deployment"
    """
    try:
        router_service = get_model_router()
        result = router_service.compress_prompt(prompt)

        logger.info(f"Prompt compression: {result['reduction_percent']:.1f}% reduction")

        return result

    except Exception as e:
        logger.error(f"Prompt compression failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Prompt compression failed: {str(e)}",
        )
