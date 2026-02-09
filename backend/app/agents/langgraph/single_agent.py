"""
LangGraph-based Single-Agent Architecture for Fraud Detection.

This is a refactored version of single_agent.py using LangGraph's StateGraph
for node orchestration. Maintains API compatibility while leveraging LangGraph's
built-in features for state management and execution flow.

Migration from custom implementation:
- AgentState (Pydantic) → FraudDetectionState (TypedDict - LangGraph standard)
- Manual node chaining → StateGraph with add_node/add_edge
- Custom termination → Conditional edges
- Direct node calls → Graph compilation and invocation

Features:
- Async node execution
- State persistence across nodes
- Conditional routing
- Built-in error handling
"""

from typing import Dict, Any, Optional, TypedDict, List
from datetime import datetime
import logging

from langgraph.graph import StateGraph, END
from pydantic import BaseModel

from app.agents.agent_memory import AgentMemory, MemoryType
from app.agents.tool_registry import get_tool_registry

logger = logging.getLogger(__name__)


# ============================================================================
# AgentResult (Pydantic - for API compatibility)
# ============================================================================


class AgentResult(BaseModel):
    """
    Final result from agent execution.
    
    Maintains compatibility with original implementation.
    """

    # Decision
    is_fraud: bool
    risk_score: float
    risk_level: str
    confidence: float
    explanation: str

    # Metadata
    transaction_id: str
    total_steps: int
    termination_reason: str
    execution_time: float

    # Transparency
    observations: list[str]
    anomalies: list[str]
    reasoning_steps: list[str]
    tool_results: Dict[str, Any]

    # Escalation
    should_escalate: bool
    escalation_reason: Optional[str] = None
    self_critique: Optional[str] = None


# ============================================================================
# State Definition (TypedDict - LangGraph Standard)
# ============================================================================


class FraudDetectionState(TypedDict, total=False):
    """
    Agent state using TypedDict (required by LangGraph).

    This replaces the Pydantic AgentState from the original implementation.
    TypedDict provides type hints while remaining compatible with LangGraph's
    state management system.
    """
    # Input
    transaction: Dict[str, Any]
    transaction_id: str

    # Observation
    observations: List[str]
    anomalies: List[str]

    # Planning
    plan: List[str]
    current_step: int

    # Execution
    tool_results: Dict[str, Any]
    execution_errors: List[str]

    # Reasoning
    reasoning_steps: List[str]
    confidence: float

    # Decision
    is_fraud: Optional[bool]
    risk_score: Optional[float]
    risk_level: Optional[str]
    explanation: Optional[str]

    # Reflection
    self_critique: Optional[str]
    should_escalate: bool
    escalation_reason: Optional[str]

    # Metadata
    step_count: int
    max_steps: int
    start_time: datetime


# ============================================================================
# Node Functions (LangGraph-compatible async functions)
# ============================================================================


async def observation_node(state: FraudDetectionState) -> FraudDetectionState:
    """
    Observation node: Parse transaction features and identify anomalies.

    LangGraph node functions receive state and return updated state.

    Args:
        state: Current fraud detection state

    Returns:
        Updated state with observations and anomalies
    """
    logger.info(f"[LangGraph] Observing transaction {state['transaction_id']}")

    transaction = state["transaction"]
    observations = []
    anomalies = []

    # Extract key features
    amount = transaction.get("amount", 0)
    txn_type = transaction.get("type", "UNKNOWN")
    old_balance_orig = transaction.get("oldbalanceOrg", 0)
    new_balance_orig = transaction.get("newbalanceOrig", 0)
    old_balance_dest = transaction.get("oldbalanceDest", 0)
    new_balance_dest = transaction.get("newbalanceDest", 0)

    # Basic observations
    observations.append(f"Transaction type: {txn_type}")
    observations.append(f"Amount: ${amount:,.2f}")
    observations.append(
        f"Sender balance: ${old_balance_orig:,.2f} → ${new_balance_orig:,.2f}"
    )
    observations.append(
        f"Receiver balance: ${old_balance_dest:,.2f} → ${new_balance_dest:,.2f}"
    )

    # Identify anomalies
    if amount > 100000:
        anomalies.append("High-value transaction (>$100k)")

    if new_balance_orig == 0 and old_balance_orig > 0:
        anomalies.append("Sender account completely drained")

    if new_balance_dest == 0 and amount > 1000:
        anomalies.append("Money disappeared (destination balance unchanged)")

    balance_diff_orig = old_balance_orig - new_balance_orig
    if abs(balance_diff_orig - amount) > 0.01 and txn_type in ["TRANSFER", "CASH_OUT"]:
        anomalies.append(
            f"Balance inconsistency: sent ${amount} but balance changed by ${balance_diff_orig}"
        )

    if txn_type in ["TRANSFER", "CASH_OUT"] and amount > 10000:
        anomalies.append(f"High-risk transaction type: {txn_type}")

    # Update state
    state["observations"] = observations
    state["anomalies"] = anomalies
    state["step_count"] = state.get("step_count", 0) + 1

    logger.info(f"[LangGraph] Found {len(anomalies)} anomalies")
    return state


async def planning_node(state: FraudDetectionState) -> FraudDetectionState:
    """
    Planning node: Task decomposition and dependency sequencing.

    Args:
        state: Current fraud detection state

    Returns:
        Updated state with execution plan
    """
    logger.info("[LangGraph] Creating execution plan")

    plan = []

    # Always start with policy check
    plan.append("query_fraud_policy")

    # If anomalies detected, calculate risk
    if state.get("anomalies"):
        plan.append("calculate_risk_score")

    # Check account history for context
    plan.append("check_account_history")

    # Generate reasoning based on results
    plan.append("reason_about_fraud")

    # Make final decision
    plan.append("make_decision")

    # If uncertain, escalate
    plan.append("check_escalation")

    state["plan"] = plan
    state["current_step"] = 0
    state["step_count"] = state.get("step_count", 0) + 1

    logger.info(f"[LangGraph] Created plan with {len(plan)} steps")
    return state


async def execution_node(state: FraudDetectionState) -> FraudDetectionState:
    """
    Execution node: Execute tool calls with error handling.

    Args:
        state: Current fraud detection state

    Returns:
        Updated state with tool results
    """
    logger.info("[LangGraph] Executing tools")

    transaction = state["transaction"]
    txn_type = transaction.get("type", "")
    account_id = transaction.get("nameOrig", "UNKNOWN")

    tool_results = state.get("tool_results", {})
    execution_errors = state.get("execution_errors", [])

    tool_registry = get_tool_registry()

    # Execute policy query
    policy_result = await tool_registry.execute_tool(
        "query_fraud_policy",
        {"transaction_type": txn_type},
    )
    if policy_result.success:
        tool_results["policy"] = policy_result.result
    else:
        execution_errors.append(f"Policy query failed: {policy_result.error}")

    # Execute risk calculation
    risk_result = await tool_registry.execute_tool(
        "calculate_risk_score",
        {
            "transaction_id": transaction.get(
                "transaction_id", transaction.get("transactionId", "")
            ),
            "amount": transaction.get("amount", 0.0),
            "transaction_type": transaction.get("type", ""),
            "oldbalance_org": transaction.get("oldbalanceOrg", 0.0),
            "newbalance_orig": transaction.get("newbalanceOrig", 0.0),
            "oldbalance_dest": transaction.get("oldbalanceDest", 0.0),
            "newbalance_dest": transaction.get("newbalanceDest", 0.0),
            "step": 1,
        },
    )
    if risk_result.success:
        tool_results["risk_score"] = risk_result.result
        state["risk_score"] = (
            risk_result.result.get("risk_score", 0.0)
            if isinstance(risk_result.result, dict)
            else risk_result.result
        )
    else:
        execution_errors.append(f"Risk calculation failed: {risk_result.error}")

    # Execute history check
    history_result = await tool_registry.execute_tool(
        "fetch_account_history",
        {"account_id": account_id},
    )
    if history_result.success:
        tool_results["account_history"] = history_result.result
    else:
        execution_errors.append(f"History check failed: {history_result.error}")

    state["tool_results"] = tool_results
    state["execution_errors"] = execution_errors
    state["step_count"] = state.get("step_count", 0) + 1

    logger.info(f"[LangGraph] Executed {len(tool_results)} tools")
    return state


async def reasoning_node(state: FraudDetectionState) -> FraudDetectionState:
    """
    Reasoning node: Chain-of-thought reasoning about fraud.

    Args:
        state: Current fraud detection state

    Returns:
        Updated state with reasoning steps
    """
    logger.info("[LangGraph] Reasoning about fraud indicators")

    reasoning_steps = []

    # Step 1: Analyze observations
    anomalies = state.get("anomalies", [])
    if anomalies:
        reasoning_steps.append(
            f"Detected {len(anomalies)} anomalies: {', '.join(anomalies)}"
        )
    else:
        reasoning_steps.append("No significant anomalies detected in transaction pattern")

    # Step 2: Apply policy
    tool_results = state.get("tool_results", {})
    policy = tool_results.get("policy", "No policy found")
    reasoning_steps.append(f"Policy check: {policy}")

    # Step 3: Risk assessment
    risk_score = state.get("risk_score") or 0.0
    if risk_score >= 80:
        reasoning_steps.append(
            f"CRITICAL risk score ({risk_score:.1f}/100) - strong fraud indicators"
        )
    elif risk_score >= 60:
        reasoning_steps.append(
            f"HIGH risk score ({risk_score:.1f}/100) - multiple fraud indicators"
        )
    elif risk_score >= 40:
        reasoning_steps.append(
            f"MEDIUM risk score ({risk_score:.1f}/100) - some concerns"
        )
    else:
        reasoning_steps.append(
            f"LOW risk score ({risk_score:.1f}/100) - appears legitimate"
        )

    # Step 4: Account history context
    history = tool_results.get("account_history", {})
    fraud_incidents = history.get("fraud_incidents", 0)
    if fraud_incidents > 0:
        reasoning_steps.append(
            f"Account has {fraud_incidents} prior fraud incidents - elevated concern"
        )
    else:
        reasoning_steps.append("Account has clean history - no prior fraud incidents")

    # Step 5: Final synthesis
    if risk_score >= 70:
        reasoning_steps.append("Conclusion: Strong evidence of fraud - recommend BLOCK")
    elif risk_score >= 40:
        reasoning_steps.append("Conclusion: Moderate fraud risk - recommend REVIEW")
    else:
        reasoning_steps.append("Conclusion: Low fraud risk - recommend APPROVE")

    state["reasoning_steps"] = reasoning_steps
    state["step_count"] = state.get("step_count", 0) + 1

    logger.info(f"[LangGraph] Generated {len(reasoning_steps)} reasoning steps")
    return state


async def decision_node(state: FraudDetectionState) -> FraudDetectionState:
    """
    Decision node: Make final fraud determination.

    Args:
        state: Current fraud detection state

    Returns:
        Updated state with fraud decision
    """
    logger.info("[LangGraph] Making fraud decision")

    risk_score = state.get("risk_score") or 0.0

    # Determine fraud classification
    if risk_score >= 70:
        state["is_fraud"] = True
        state["risk_level"] = "CRITICAL"
        state["confidence"] = 0.9
    elif risk_score >= 50:
        state["is_fraud"] = True
        state["risk_level"] = "HIGH"
        state["confidence"] = 0.75
    elif risk_score >= 30:
        state["is_fraud"] = False
        state["risk_level"] = "MEDIUM"
        state["confidence"] = 0.6
    else:
        state["is_fraud"] = False
        state["risk_level"] = "LOW"
        state["confidence"] = 0.85

    # Generate explanation
    explanation_parts = []
    explanation_parts.append(f"Risk Score: {risk_score:.1f}/100 ({state['risk_level']})")

    anomalies = state.get("anomalies", [])
    if anomalies:
        explanation_parts.append(f"Anomalies: {'; '.join(anomalies)}")

    reasoning_steps = state.get("reasoning_steps", [])
    if reasoning_steps:
        explanation_parts.append(f"Reasoning: {reasoning_steps[-1]}")

    state["explanation"] = " | ".join(explanation_parts)
    state["step_count"] = state.get("step_count", 0) + 1

    logger.info(f"[LangGraph] Decision: fraud={state['is_fraud']}, confidence={state['confidence']:.2f}")
    return state


async def reflection_node(state: FraudDetectionState) -> FraudDetectionState:
    """
    Reflection node: Self-critique and escalation logic.

    Args:
        state: Current fraud detection state

    Returns:
        Updated state with reflection and escalation decision
    """
    logger.info("[LangGraph] Reflecting on decision")

    # Self-critique: Check decision consistency
    critiques = []

    # Check 1: Does confidence match risk level?
    risk_level = state.get("risk_level", "")
    confidence = state.get("confidence", 0.0)
    if risk_level == "CRITICAL" and confidence < 0.8:
        critiques.append("CRITICAL risk but low confidence - inconsistent")

    # Check 2: Are there contradictions?
    is_fraud = state.get("is_fraud")
    risk_score = state.get("risk_score", 0.0)
    if is_fraud and risk_score < 50:
        critiques.append("Classified as fraud but low risk score - contradiction")

    # Check 3: Did we gather enough evidence?
    tool_results = state.get("tool_results", {})
    if not tool_results:
        critiques.append("No tool results available - insufficient evidence")

    # Check 4: Are reasoning steps sound?
    reasoning_steps = state.get("reasoning_steps", [])
    if len(reasoning_steps) < 3:
        critiques.append("Insufficient reasoning steps - analysis too shallow")

    state["self_critique"] = (
        "; ".join(critiques) if critiques else "Decision appears consistent"
    )

    # Escalation logic
    should_escalate = False
    escalation_reason = None

    # Escalate if low confidence
    if confidence < 0.7:
        should_escalate = True
        escalation_reason = f"Low confidence ({confidence:.2f}) - human review needed"

    # Escalate if critiques found
    if critiques:
        should_escalate = True
        escalation_reason = f"Decision inconsistencies: {state['self_critique']}"

    # Escalate if high-value and uncertain
    transaction = state["transaction"]
    amount = transaction.get("amount", 0)
    if amount > 100000 and risk_level == "MEDIUM":
        should_escalate = True
        escalation_reason = f"High-value transaction (${amount:,.0f}) with uncertain risk"

    state["should_escalate"] = should_escalate
    state["escalation_reason"] = escalation_reason
    state["step_count"] = state.get("step_count", 0) + 1

    # If escalating, use tool
    if should_escalate:
        tool_registry = get_tool_registry()
        escalation_result = await tool_registry.execute_tool(
            "escalate_to_human",
            {
                "transaction_id": state["transaction_id"],
                "reason": escalation_reason,
            },
        )
        if escalation_result.success:
            tool_results = state.get("tool_results", {})
            tool_results["escalation"] = escalation_result.result
            state["tool_results"] = tool_results

    logger.info(f"[LangGraph] Reflection: escalate={should_escalate}")
    return state


# ============================================================================
# Graph Construction (LangGraph StateGraph)
# ============================================================================


def create_fraud_detection_graph() -> StateGraph:
    """
    Create LangGraph StateGraph for fraud detection workflow.

    This replaces the manual node chaining from the original implementation.
    LangGraph automatically handles:
    - State persistence across nodes
    - Node execution order
    - Error propagation
    - Conditional routing

    Returns:
        Compiled StateGraph ready for execution
    """
    # Initialize graph with state schema
    workflow = StateGraph(FraudDetectionState)

    # Add nodes (replaces manual node initialization)
    workflow.add_node("observation", observation_node)
    workflow.add_node("planning", planning_node)
    workflow.add_node("execution", execution_node)
    workflow.add_node("reasoning", reasoning_node)
    workflow.add_node("decision", decision_node)
    workflow.add_node("reflection", reflection_node)

    # Add edges (replaces manual node chaining in _agent_loop)
    workflow.set_entry_point("observation")
    workflow.add_edge("observation", "planning")
    workflow.add_edge("planning", "execution")
    workflow.add_edge("execution", "reasoning")
    workflow.add_edge("reasoning", "decision")
    workflow.add_edge("decision", "reflection")
    workflow.add_edge("reflection", END)

    # Compile graph
    return workflow.compile()


# ============================================================================
# Agent Wrapper (API Compatibility Layer)
# ============================================================================


class FraudDetectionAgentLangGraph:
    """
    LangGraph-based fraud detection agent.

    Maintains API compatibility with original FraudDetectionAgent while
    using LangGraph's StateGraph for node orchestration.

    This is a facade pattern - provides same interface as single_agent.py
    but uses LangGraph under the hood.
    """

    def __init__(self, max_steps: int = 20):
        """
        Initialize LangGraph-based fraud detection agent.

        Args:
            max_steps: Maximum reasoning steps before timeout
        """
        self.max_steps = max_steps
        self.memory = AgentMemory()
        self.graph = create_fraud_detection_graph()

        logger.info(
            f"[LangGraph] Initialized FraudDetectionAgentLangGraph (max_steps={max_steps})"
        )

    async def analyze(
        self,
        transaction: Dict[str, Any],
        transaction_id: str,
    ) -> AgentResult:
        """
        Analyze transaction for fraud using LangGraph.

        This method maintains API compatibility with the original implementation.

        Args:
            transaction: Transaction data
            transaction_id: Unique transaction identifier

        Returns:
            AgentResult with fraud determination and reasoning trace

        Raises:
            ValueError: If transaction is invalid
        """
        start_time = datetime.now()

        # Validate input
        if not transaction:
            raise ValueError("Transaction cannot be empty")

        if not transaction_id:
            raise ValueError("Transaction ID is required")

        logger.info(f"[LangGraph] Starting analysis for transaction {transaction_id}")

        # Initialize state (TypedDict instead of Pydantic)
        initial_state: FraudDetectionState = {
            "transaction": transaction,
            "transaction_id": transaction_id,
            "observations": [],
            "anomalies": [],
            "plan": [],
            "current_step": 0,
            "tool_results": {},
            "execution_errors": [],
            "reasoning_steps": [],
            "confidence": 0.0,
            "is_fraud": None,
            "risk_score": None,
            "risk_level": None,
            "explanation": None,
            "self_critique": None,
            "should_escalate": False,
            "escalation_reason": None,
            "step_count": 0,
            "max_steps": self.max_steps,
            "start_time": start_time,
        }

        # Clear memory for fresh analysis
        self.memory.clear()

        try:
            # Execute LangGraph (replaces manual _agent_loop)
            final_state = await self.graph.ainvoke(initial_state)

            # Calculate execution time
            execution_time = (datetime.now() - start_time).total_seconds()

            # Build result (maintain compatibility with AgentResult)
            result = AgentResult(
                # Decision
                is_fraud=final_state.get("is_fraud", False),
                risk_score=final_state.get("risk_score", 0.0),
                risk_level=final_state.get("risk_level", "UNKNOWN"),
                confidence=final_state.get("confidence", 0.0),
                explanation=final_state.get("explanation", "Analysis incomplete"),
                # Metadata
                transaction_id=transaction_id,
                total_steps=final_state.get("step_count", 0),
                termination_reason="success",
                execution_time=execution_time,
                # Transparency
                observations=final_state.get("observations", []),
                anomalies=final_state.get("anomalies", []),
                reasoning_steps=final_state.get("reasoning_steps", []),
                tool_results=final_state.get("tool_results", {}),
                # Escalation
                should_escalate=final_state.get("should_escalate", False),
                escalation_reason=final_state.get("escalation_reason"),
                self_critique=final_state.get("self_critique"),
            )

            # Store result in long-term memory
            self.memory.store(
                f"result_{transaction_id}",
                result.dict(),
                MemoryType.LONG_TERM,
                metadata={"timestamp": datetime.now().isoformat()},
            )

            logger.info(
                f"[LangGraph] Analysis complete: fraud={result.is_fraud}, "
                f"risk={result.risk_score:.1f}, steps={result.total_steps}, "
                f"time={execution_time:.2f}s"
            )

            return result

        except Exception as e:
            logger.error(f"[LangGraph] Agent execution failed: {e}", exc_info=True)

            # Return safe default
            execution_time = (datetime.now() - start_time).total_seconds()
            return AgentResult(
                is_fraud=False,
                risk_score=0.0,
                risk_level="ERROR",
                confidence=0.0,
                explanation=f"Agent execution failed: {str(e)}",
                transaction_id=transaction_id,
                total_steps=0,
                termination_reason="error",
                execution_time=execution_time,
                observations=[],
                anomalies=[],
                reasoning_steps=[],
                tool_results={},
                should_escalate=True,
                escalation_reason=f"Agent error: {str(e)}",
                self_critique="Execution failed",
            )

    def get_memory_stats(self) -> Dict[str, Any]:
        """Get current memory statistics."""
        return self.memory.get_stats()

    def get_memory_contents(self, memory_type: Optional[MemoryType] = None) -> list:
        """Get memory contents for inspection."""
        return self.memory.list_memories(memory_type)

    def reset_memory(self):
        """Reset all agent memory."""
        self.memory.clear()
        logger.info("[LangGraph] Agent memory reset")
