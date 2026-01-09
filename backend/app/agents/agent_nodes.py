"""
Agent Nodes for Fraud Detection Workflow.

Implements individual nodes in the agent reasoning graph following
LangGraph-style node-based architecture.
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from datetime import datetime
import logging

from app.agents.agent_memory import AgentMemory, MemoryType
from app.agents.tool_registry import get_tool_registry

logger = logging.getLogger(__name__)


class AgentState(BaseModel):
    """
    State passed between agent nodes.

    Similar to LangGraph's state management.
    """

    # Input
    transaction: Dict[str, Any]
    transaction_id: str

    # Observation
    observations: List[str] = []
    anomalies: List[str] = []

    # Planning
    plan: List[str] = []
    current_step: int = 0

    # Execution
    tool_results: Dict[str, Any] = {}
    execution_errors: List[str] = []

    # Reasoning
    reasoning_steps: List[str] = []
    confidence: float = 0.0

    # Decision
    is_fraud: Optional[bool] = None
    risk_score: Optional[float] = None
    risk_level: Optional[str] = None
    explanation: Optional[str] = None

    # Reflection
    self_critique: Optional[str] = None
    should_escalate: bool = False
    escalation_reason: Optional[str] = None

    # Metadata
    step_count: int = 0
    max_steps: int = 20
    start_time: datetime = None

    class Config:
        arbitrary_types_allowed = True


class ObservationNode:
    """
    Observation module: Parse transaction features and identify anomalies.
    """

    async def execute(self, state: AgentState, memory: AgentMemory) -> AgentState:
        """
        Execute observation node.

        Args:
            state: Current agent state
            memory: Agent memory

        Returns:
            Updated state with observations
        """
        logger.info(f"Observing transaction {state.transaction_id}")

        transaction = state.transaction
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
        observations.append(f"Sender balance: ${old_balance_orig:,.2f} → ${new_balance_orig:,.2f}")
        observations.append(f"Receiver balance: ${old_balance_dest:,.2f} → ${new_balance_dest:,.2f}")

        # Identify anomalies
        if amount > 100000:
            anomalies.append("High-value transaction (>$100k)")

        if new_balance_orig == 0 and old_balance_orig > 0:
            anomalies.append("Sender account completely drained")

        if new_balance_dest == 0 and amount > 1000:
            anomalies.append("Money disappeared (destination balance unchanged)")

        balance_diff_orig = old_balance_orig - new_balance_orig
        if abs(balance_diff_orig - amount) > 0.01 and txn_type in ["TRANSFER", "CASH_OUT"]:
            anomalies.append(f"Balance inconsistency: sent ${amount} but balance changed by ${balance_diff_orig}")

        if txn_type in ["TRANSFER", "CASH_OUT"] and amount > 10000:
            anomalies.append(f"High-risk transaction type: {txn_type}")

        # Update state
        state.observations = observations
        state.anomalies = anomalies
        state.step_count += 1

        # Store in short-term memory
        memory.store("transaction", transaction, MemoryType.SHORT_TERM)
        memory.store("observations", observations, MemoryType.SHORT_TERM)
        memory.store("anomalies", anomalies, MemoryType.SHORT_TERM)

        logger.info(f"Found {len(anomalies)} anomalies")
        return state


class PlanningNode:
    """
    Planning module: Task decomposition and dependency sequencing.
    """

    async def execute(self, state: AgentState, memory: AgentMemory) -> AgentState:
        """
        Execute planning node.

        Args:
            state: Current agent state
            memory: Agent memory

        Returns:
            Updated state with execution plan
        """
        logger.info("Creating execution plan")

        plan = []

        # Always start with policy check
        plan.append("query_fraud_policy")

        # If anomalies detected, calculate risk
        if state.anomalies:
            plan.append("calculate_risk_score")

        # Check account history for context
        plan.append("check_account_history")

        # Generate reasoning based on results
        plan.append("reason_about_fraud")

        # Make final decision
        plan.append("make_decision")

        # If uncertain, escalate
        plan.append("check_escalation")

        state.plan = plan
        state.current_step = 0
        state.step_count += 1

        # Store plan in working memory
        memory.store("plan", plan, MemoryType.WORKING)

        logger.info(f"Created plan with {len(plan)} steps")
        return state


class ExecutionNode:
    """
    Execution engine: Execute tool calls with error handling.
    """

    def __init__(self):
        """Initialize execution node."""
        self.tool_registry = get_tool_registry()

    async def execute(self, state: AgentState, memory: AgentMemory) -> AgentState:
        """
        Execute tools in the plan.

        Args:
            state: Current agent state
            memory: Agent memory

        Returns:
            Updated state with tool results
        """
        logger.info("Executing tools")

        transaction = state.transaction
        txn_type = transaction.get("type", "")
        account_id = transaction.get("nameOrig", "UNKNOWN")

        # Execute policy query
        policy_result = await self.tool_registry.execute_tool(
            "query_fraud_policy",
            {"transaction_type": txn_type},
        )
        if policy_result.success:
            state.tool_results["policy"] = policy_result.result
            memory.store("policy", policy_result.result, MemoryType.WORKING)
        else:
            state.execution_errors.append(f"Policy query failed: {policy_result.error}")

        # Execute risk calculation
        risk_result = await self.tool_registry.execute_tool(
            "calculate_risk_score",
            {
                "transaction_id": transaction.get("transaction_id", transaction.get("transactionId", "")),
                "amount": transaction.get("amount", 0.0),
                "transaction_type": transaction.get("type", ""),
                "oldbalance_org": transaction.get("oldbalanceOrg", 0.0),
                "newbalance_orig": transaction.get("newbalanceOrig", 0.0),
                "oldbalance_dest": transaction.get("oldbalanceDest", 0.0),
                "newbalance_dest": transaction.get("newbalanceDest", 0.0),
                "step": 1,  # Default step value for risk calculation
            },
        )
        if risk_result.success:
            state.tool_results["risk_score"] = risk_result.result
            state.risk_score = risk_result.result.get("risk_score", 0.0) if isinstance(risk_result.result, dict) else risk_result.result
            memory.store("risk_score", risk_result.result, MemoryType.WORKING)
        else:
            state.execution_errors.append(f"Risk calculation failed: {risk_result.error}")

        # Execute history check
        history_result = await self.tool_registry.execute_tool(
            "fetch_account_history",
            {"account_id": account_id},
        )
        if history_result.success:
            state.tool_results["account_history"] = history_result.result
            memory.store("account_history", history_result.result, MemoryType.WORKING)
        else:
            state.execution_errors.append(f"History check failed: {history_result.error}")

        state.step_count += 1
        logger.info(f"Executed {len(state.tool_results)} tools")
        return state


class ReasoningNode:
    """
    Reasoning module: Chain-of-thought reasoning about fraud.
    """

    async def execute(self, state: AgentState, memory: AgentMemory) -> AgentState:
        """
        Execute reasoning node.

        Args:
            state: Current agent state
            memory: Agent memory

        Returns:
            Updated state with reasoning
        """
        logger.info("Reasoning about fraud indicators")

        reasoning_steps = []

        # Step 1: Analyze observations
        if state.anomalies:
            reasoning_steps.append(
                f"Detected {len(state.anomalies)} anomalies: {', '.join(state.anomalies)}"
            )
        else:
            reasoning_steps.append("No significant anomalies detected in transaction pattern")

        # Step 2: Apply policy
        policy = state.tool_results.get("policy", "No policy found")
        reasoning_steps.append(f"Policy check: {policy}")

        # Step 3: Risk assessment
        risk_score = state.risk_score or 0.0
        if risk_score >= 80:
            reasoning_steps.append(f"CRITICAL risk score ({risk_score:.1f}/100) - strong fraud indicators")
        elif risk_score >= 60:
            reasoning_steps.append(f"HIGH risk score ({risk_score:.1f}/100) - multiple fraud indicators")
        elif risk_score >= 40:
            reasoning_steps.append(f"MEDIUM risk score ({risk_score:.1f}/100) - some concerns")
        else:
            reasoning_steps.append(f"LOW risk score ({risk_score:.1f}/100) - appears legitimate")

        # Step 4: Account history context
        history = state.tool_results.get("account_history", {})
        fraud_incidents = history.get("fraud_incidents", 0)
        if fraud_incidents > 0:
            reasoning_steps.append(f"Account has {fraud_incidents} prior fraud incidents - elevated concern")
        else:
            reasoning_steps.append("Account has clean history - no prior fraud incidents")

        # Step 5: Final synthesis
        if risk_score >= 70:
            reasoning_steps.append("Conclusion: Strong evidence of fraud - recommend BLOCK")
        elif risk_score >= 40:
            reasoning_steps.append("Conclusion: Moderate fraud risk - recommend REVIEW")
        else:
            reasoning_steps.append("Conclusion: Low fraud risk - recommend APPROVE")

        state.reasoning_steps = reasoning_steps
        state.step_count += 1

        # Store reasoning in working memory
        memory.store("reasoning", reasoning_steps, MemoryType.WORKING)

        logger.info(f"Generated {len(reasoning_steps)} reasoning steps")
        return state


class DecisionNode:
    """
    Decision module: Make final fraud determination.
    """

    async def execute(self, state: AgentState, memory: AgentMemory) -> AgentState:
        """
        Execute decision node.

        Args:
            state: Current agent state
            memory: Agent memory

        Returns:
            Updated state with decision
        """
        logger.info("Making fraud decision")

        risk_score = state.risk_score or 0.0

        # Determine fraud classification
        if risk_score >= 70:
            state.is_fraud = True
            state.risk_level = "CRITICAL"
            state.confidence = 0.9
        elif risk_score >= 50:
            state.is_fraud = True
            state.risk_level = "HIGH"
            state.confidence = 0.75
        elif risk_score >= 30:
            state.is_fraud = False
            state.risk_level = "MEDIUM"
            state.confidence = 0.6
        else:
            state.is_fraud = False
            state.risk_level = "LOW"
            state.confidence = 0.85

        # Generate explanation
        explanation_parts = []
        explanation_parts.append(f"Risk Score: {risk_score:.1f}/100 ({state.risk_level})")

        if state.anomalies:
            explanation_parts.append(f"Anomalies: {'; '.join(state.anomalies)}")

        if state.reasoning_steps:
            explanation_parts.append(f"Reasoning: {state.reasoning_steps[-1]}")  # Use conclusion

        state.explanation = " | ".join(explanation_parts)
        state.step_count += 1

        # Store decision in working memory
        memory.store("decision", {
            "is_fraud": state.is_fraud,
            "risk_score": risk_score,
            "risk_level": state.risk_level,
            "confidence": state.confidence,
        }, MemoryType.WORKING)

        logger.info(f"Decision: fraud={state.is_fraud}, confidence={state.confidence:.2f}")
        return state


class ReflectionNode:
    """
    Reflection module: Self-critique and escalation logic.
    """

    async def execute(self, state: AgentState, memory: AgentMemory) -> AgentState:
        """
        Execute reflection node.

        Args:
            state: Current agent state
            memory: Agent memory

        Returns:
            Updated state with reflection
        """
        logger.info("Reflecting on decision")

        # Self-critique: Check decision consistency
        critiques = []

        # Check 1: Does confidence match risk level?
        if state.risk_level == "CRITICAL" and state.confidence < 0.8:
            critiques.append("CRITICAL risk but low confidence - inconsistent")

        # Check 2: Are there contradictions?
        if state.is_fraud and state.risk_score < 50:
            critiques.append("Classified as fraud but low risk score - contradiction")

        # Check 3: Did we gather enough evidence?
        if not state.tool_results:
            critiques.append("No tool results available - insufficient evidence")

        # Check 4: Are reasoning steps sound?
        if len(state.reasoning_steps) < 3:
            critiques.append("Insufficient reasoning steps - analysis too shallow")

        state.self_critique = "; ".join(critiques) if critiques else "Decision appears consistent"

        # Escalation logic
        should_escalate = False
        escalation_reason = None

        # Escalate if low confidence
        if state.confidence < 0.7:
            should_escalate = True
            escalation_reason = f"Low confidence ({state.confidence:.2f}) - human review needed"

        # Escalate if critiques found
        if critiques:
            should_escalate = True
            escalation_reason = f"Decision inconsistencies: {state.self_critique}"

        # Escalate if high-value and uncertain
        amount = state.transaction.get("amount", 0)
        if amount > 100000 and state.risk_level == "MEDIUM":
            should_escalate = True
            escalation_reason = f"High-value transaction (${amount:,.0f}) with uncertain risk"

        state.should_escalate = should_escalate
        state.escalation_reason = escalation_reason
        state.step_count += 1

        # If escalating, use tool
        if should_escalate:
            tool_registry = get_tool_registry()
            escalation_result = await tool_registry.execute_tool(
                "escalate_to_human",
                {
                    "transaction_id": state.transaction_id,
                    "reason": escalation_reason,
                },
            )
            if escalation_result.success:
                state.tool_results["escalation"] = escalation_result.result

        # Store reflection in working memory
        memory.store("reflection", {
            "self_critique": state.self_critique,
            "should_escalate": should_escalate,
            "escalation_reason": escalation_reason,
        }, MemoryType.WORKING)

        logger.info(f"Reflection: escalate={should_escalate}")
        return state


class TerminationNode:
    """
    Termination logic: Determine if agent should continue or stop.
    """

    def should_terminate(self, state: AgentState) -> tuple[bool, str]:
        """
        Check if agent should terminate.

        Returns:
            (should_stop, reason) tuple
        """
        # Success: Decision made
        if state.is_fraud is not None:
            return True, "success"

        # Failure: Max steps exceeded
        if state.step_count >= state.max_steps:
            return True, "max_steps"

        # Failure: Execution errors
        if len(state.execution_errors) > 3:
            return True, "too_many_errors"

        # Timeout: Would need to check elapsed time
        if state.start_time:
            from datetime import datetime
            elapsed = (datetime.now() - state.start_time).total_seconds()
            if elapsed > 30:
                return True, "timeout"

        # Continue
        return False, "continue"
