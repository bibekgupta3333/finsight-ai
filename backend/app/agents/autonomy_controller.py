"""
Autonomy Controller for Agent Decision-Making.

Manages confidence thresholds, human escalation,
stop conditions, and goal drift prevention.
"""

from typing import Dict, Any, List, Optional, Tuple
from pydantic import BaseModel
from enum import Enum
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class AutonomyLevel(str, Enum):
    """Agent autonomy levels."""
    FULL_AUTO = "full_auto"  # Agent decides without human
    SUPERVISED = "supervised"  # Agent suggests, human approves
    ASSISTIVE = "assistive"  # Human decides, agent assists


class EscalationReason(str, Enum):
    """Reasons for escalating to human."""
    LOW_CONFIDENCE = "low_confidence"
    EDGE_CASE = "edge_case"
    HIGH_VALUE = "high_value"
    CONFLICTING_EVIDENCE = "conflicting_evidence"
    CONSTRAINT_VIOLATION = "constraint_violation"
    CIRCULAR_REASONING = "circular_reasoning"
    TIMEOUT = "timeout"


class StopReason(str, Enum):
    """Reasons for stopping agent execution."""
    SUCCESS = "success"
    MAX_STEPS = "max_steps"
    TIMEOUT = "timeout"
    CIRCULAR_REASONING = "circular_reasoning"
    UNSOLVABLE = "unsolvable"
    CONSTRAINT_VIOLATION = "constraint_violation"


class EscalationTicket(BaseModel):
    """Human escalation ticket."""

    id: str
    transaction_id: str
    reason: EscalationReason
    explanation: str
    suggested_decision: Optional[Dict[str, Any]] = None
    agent_reasoning: List[str] = []
    confidence: float = 0.0
    priority: str = "MEDIUM"  # LOW, MEDIUM, HIGH, CRITICAL
    created_at: datetime = None

    def __init__(self, **data):
        if data.get("created_at") is None:
            data["created_at"] = datetime.now()
        super().__init__(**data)


class StopCondition(BaseModel):
    """Condition that triggers agent stopping."""

    type: StopReason
    triggered: bool = False
    threshold: Optional[float] = None
    current_value: Optional[float] = None
    message: str = ""


class GoalState(BaseModel):
    """Agent goal tracking."""

    goal: str
    achieved: bool = False
    drifted: bool = False
    drift_warnings: List[str] = []
    current_focus: str = ""
    step_count: int = 0


class AutonomyController:
    """
    Controls agent autonomy and decision authority.

    Manages:
    - Confidence-based decision authority
    - Human escalation triggers
    - Stop conditions and timeouts
    - Goal drift detection and prevention

    Example:
        ```python
        controller = AutonomyController(
            max_steps=10,
            timeout_seconds=30,
            min_confidence=0.7
        )

        # Check if should escalate
        should_escalate, reason = controller.should_escalate(
            decision={"is_fraud": True, "confidence": 0.6},
            evidence=evidence
        )

        if should_escalate:
            ticket = controller.create_escalation(
                transaction_id="tx_123",
                reason=reason,
                decision=decision
            )
        ```
    """

    def __init__(
        self,
        max_steps: int = 10,
        timeout_seconds: float = 30.0,
        min_confidence: float = 0.7,
    ):
        """
        Initialize autonomy controller.

        Args:
            max_steps: Maximum reasoning steps
            timeout_seconds: Execution timeout
            min_confidence: Minimum confidence for autonomous decision
        """
        self.max_steps = max_steps
        self.timeout_seconds = timeout_seconds
        self.min_confidence = min_confidence

        self.start_time: Optional[datetime] = None
        self.goal_state: Optional[GoalState] = None
        self.reasoning_history: List[str] = []

        logger.info(
            f"AutonomyController initialized: max_steps={max_steps}, "
            f"timeout={timeout_seconds}s, min_confidence={min_confidence}"
        )

    def start_session(self, goal: str):
        """Start new decision session."""
        self.start_time = datetime.now()
        self.goal_state = GoalState(goal=goal, current_focus=goal)
        self.reasoning_history = []
        logger.info(f"Started session with goal: {goal}")

    def get_autonomy_level(
        self,
        decision: Dict[str, Any],
        evidence: Dict[str, Any],
    ) -> AutonomyLevel:
        """
        Determine appropriate autonomy level based on decision confidence.

        Args:
            decision: Proposed decision
            evidence: Available evidence

        Returns:
            Autonomy level for this decision
        """
        confidence = decision.get("confidence", 0.5)
        amount = evidence.get("amount", 0)

        # High confidence (>0.9): Full autonomy
        if confidence > 0.9:
            return AutonomyLevel.FULL_AUTO

        # Medium confidence (0.7-0.9): Supervised
        if confidence >= self.min_confidence:
            # High-value transactions require supervision even with good confidence
            if amount > 50000:
                return AutonomyLevel.SUPERVISED
            return AutonomyLevel.FULL_AUTO

        # Low confidence (<0.7): Assistive only
        return AutonomyLevel.ASSISTIVE

    def should_escalate(
        self,
        decision: Dict[str, Any],
        evidence: Dict[str, Any],
        reasoning_steps: List[str] = None,
    ) -> Tuple[bool, Optional[EscalationReason]]:
        """
        Determine if decision should be escalated to human.

        Args:
            decision: Proposed decision
            evidence: Available evidence
            reasoning_steps: Agent's reasoning chain

        Returns:
            (should_escalate, reason)
        """
        confidence = decision.get("confidence", 0.5)
        amount = evidence.get("amount", 0)
        reasoning_steps = reasoning_steps or []

        # Low confidence trigger
        if confidence < self.min_confidence:
            logger.info(f"Escalating: low confidence ({confidence:.2f})")
            return True, EscalationReason.LOW_CONFIDENCE

        # High-value trigger ($100k+)
        if amount > 100000:
            logger.info(f"Escalating: high value (${amount:,.0f})")
            return True, EscalationReason.HIGH_VALUE

        # Edge case detection (unusual transaction type or pattern)
        tx_type = evidence.get("type", "")
        if tx_type not in ["PAYMENT", "TRANSFER", "CASH_OUT", "DEBIT", "CASH_IN"]:
            logger.info(f"Escalating: edge case (unknown type: {tx_type})")
            return True, EscalationReason.EDGE_CASE

        # Conflicting evidence (if reasoning contains contradictions)
        if reasoning_steps:
            contradictions = sum(
                1 for step in reasoning_steps
                if any(word in step.lower() for word in ["but", "however", "although"])
            )
            if contradictions > 2:
                logger.info(f"Escalating: conflicting evidence ({contradictions} contradictions)")
                return True, EscalationReason.CONFLICTING_EVIDENCE

        return False, None

    def create_escalation(
        self,
        transaction_id: str,
        reason: EscalationReason,
        decision: Dict[str, Any],
        evidence: Dict[str, Any],
        reasoning_steps: List[str] = None,
    ) -> EscalationTicket:
        """
        Create human escalation ticket.

        Args:
            transaction_id: Transaction ID
            reason: Escalation reason
            decision: Proposed decision
            evidence: Transaction evidence
            reasoning_steps: Agent's reasoning

        Returns:
            Escalation ticket
        """
        # Determine priority
        amount = evidence.get("amount", 0)
        confidence = decision.get("confidence", 0.5)

        if amount > 100000 or confidence < 0.3:
            priority = "CRITICAL"
        elif amount > 50000 or confidence < 0.5:
            priority = "HIGH"
        elif reason in [EscalationReason.CIRCULAR_REASONING, EscalationReason.TIMEOUT]:
            priority = "HIGH"
        else:
            priority = "MEDIUM"

        # Create explanation
        explanations = {
            EscalationReason.LOW_CONFIDENCE: f"Decision confidence ({confidence:.1%}) below threshold ({self.min_confidence:.1%})",
            EscalationReason.HIGH_VALUE: f"Transaction amount (${amount:,.0f}) requires human review",
            EscalationReason.EDGE_CASE: "Unusual transaction pattern detected",
            EscalationReason.CONFLICTING_EVIDENCE: "Contradictory evidence found in analysis",
            EscalationReason.CONSTRAINT_VIOLATION: "Decision violates fraud policy constraints",
            EscalationReason.CIRCULAR_REASONING: "Circular reasoning detected in agent logic",
            EscalationReason.TIMEOUT: "Analysis exceeded time limit",
        }

        ticket = EscalationTicket(
            id=f"esc_{transaction_id}_{datetime.now().timestamp()}",
            transaction_id=transaction_id,
            reason=reason,
            explanation=explanations.get(reason, "Manual review required"),
            suggested_decision=decision,
            agent_reasoning=reasoning_steps or [],
            confidence=confidence,
            priority=priority,
        )

        logger.info(
            f"Created escalation ticket {ticket.id}: "
            f"reason={reason.value}, priority={priority}"
        )

        return ticket

    def check_stop_conditions(
        self,
        step_count: int,
        reasoning_steps: List[str] = None,
    ) -> Tuple[bool, Optional[StopCondition]]:
        """
        Check if agent should stop execution.

        Args:
            step_count: Current step count
            reasoning_steps: Reasoning history

        Returns:
            (should_stop, condition)
        """
        reasoning_steps = reasoning_steps or []

        # Max steps condition
        if step_count >= self.max_steps:
            condition = StopCondition(
                type=StopReason.MAX_STEPS,
                triggered=True,
                threshold=float(self.max_steps),
                current_value=float(step_count),
                message=f"Reached maximum steps ({self.max_steps})",
            )
            logger.warning("Stop condition: max steps reached")
            return True, condition

        # Timeout condition
        if self.start_time:
            elapsed = (datetime.now() - self.start_time).total_seconds()
            if elapsed > self.timeout_seconds:
                condition = StopCondition(
                    type=StopReason.TIMEOUT,
                    triggered=True,
                    threshold=self.timeout_seconds,
                    current_value=elapsed,
                    message=f"Timeout after {elapsed:.1f}s",
                )
                logger.warning("Stop condition: timeout")
                return True, condition

        # Circular reasoning detection
        if self._detect_circular_reasoning(reasoning_steps):
            condition = StopCondition(
                type=StopReason.CIRCULAR_REASONING,
                triggered=True,
                message="Circular reasoning detected",
            )
            logger.warning("Stop condition: circular reasoning")
            return True, condition

        return False, None

    def _detect_circular_reasoning(self, reasoning_steps: List[str]) -> bool:
        """
        Detect circular reasoning in reasoning chain.

        Returns:
            True if circular reasoning detected
        """
        if len(reasoning_steps) < 3:
            return False

        # Check if recent steps repeat earlier conclusions
        recent_steps = reasoning_steps[-3:]
        earlier_steps = reasoning_steps[:-3]

        for recent in recent_steps:
            # Simple similarity check (in production, use embeddings)
            for earlier in earlier_steps:
                # If same reasoning appears twice, it might be circular
                if len(recent) > 20 and recent.lower() == earlier.lower():
                    return True

        return False

    def check_goal_drift(
        self,
        current_focus: str,
        reasoning_steps: List[str] = None,
    ) -> Tuple[bool, List[str]]:
        """
        Check if agent has drifted from original goal.

        Args:
            current_focus: What agent is currently focused on
            reasoning_steps: Recent reasoning

        Returns:
            (has_drifted, warnings)
        """
        if not self.goal_state:
            return False, []

        original_goal = self.goal_state.goal
        warnings = []

        # Update goal state
        self.goal_state.current_focus = current_focus
        self.goal_state.step_count += 1

        # Check if focus matches goal
        goal_keywords = original_goal.lower().split()
        focus_keywords = current_focus.lower().split()

        # Measure keyword overlap
        overlap = set(goal_keywords) & set(focus_keywords)
        overlap_ratio = len(overlap) / max(len(goal_keywords), 1)

        # Drift if overlap is low
        if overlap_ratio < 0.3:
            warnings.append(
                f"Focus '{current_focus}' diverges from goal '{original_goal}'"
            )
            self.goal_state.drifted = True

        # Check reasoning for scope creep
        if reasoning_steps:
            irrelevant_topics = [
                "investment", "advice", "recommendation",
                "portfolio", "tax", "legal"
            ]

            for step in reasoning_steps[-3:]:  # Recent steps
                for topic in irrelevant_topics:
                    if topic in step.lower():
                        warnings.append(
                            f"Reasoning contains irrelevant topic: {topic}"
                        )
                        self.goal_state.drifted = True

        if warnings:
            self.goal_state.drift_warnings.extend(warnings)
            logger.warning(f"Goal drift detected: {len(warnings)} warnings")

        return self.goal_state.drifted, warnings

    def refocus_on_goal(self) -> str:
        """
        Generate refocusing instruction to bring agent back to goal.

        Returns:
            Refocusing instruction
        """
        if not self.goal_state:
            return "Continue with fraud analysis."

        goal = self.goal_state.goal
        drift_count = len(self.goal_state.drift_warnings)

        instruction = (
            f"REFOCUS: Your goal is '{goal}'. "
            f"You have drifted {drift_count} times. "
            f"Return to analyzing fraud indicators only. "
            f"Do not provide financial advice or discuss unrelated topics."
        )

        logger.info("Generated refocusing instruction")
        return instruction

    def get_session_summary(self) -> Dict[str, Any]:
        """
        Get summary of autonomy control session.

        Returns:
            Session summary with metrics
        """
        if not self.start_time or not self.goal_state:
            return {}

        elapsed = (datetime.now() - self.start_time).total_seconds()

        return {
            "goal": self.goal_state.goal,
            "goal_achieved": self.goal_state.achieved,
            "goal_drifted": self.goal_state.drifted,
            "drift_warnings": len(self.goal_state.drift_warnings),
            "steps_taken": self.goal_state.step_count,
            "max_steps": self.max_steps,
            "elapsed_seconds": elapsed,
            "timeout_seconds": self.timeout_seconds,
            "timed_out": elapsed > self.timeout_seconds,
        }
