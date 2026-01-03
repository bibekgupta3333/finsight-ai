"""
Advanced Reasoning Engine for Autonomous Agents.

Implements hypothesis testing, counterfactual reasoning,
uncertainty estimation, and constraint satisfaction.
"""

from typing import Dict, Any, List, Optional, Tuple
from pydantic import BaseModel
from enum import Enum
import logging
from copy import deepcopy

logger = logging.getLogger(__name__)


class HypothesisStatus(str, Enum):
    """Hypothesis evaluation status."""
    PENDING = "pending"
    SUPPORTED = "supported"
    REFUTED = "refuted"
    UNCERTAIN = "uncertain"


class UncertaintySource(str, Enum):
    """Sources of uncertainty in reasoning."""
    DATA = "data"  # Missing or unreliable data
    MODEL = "model"  # Model limitations
    REASONING = "reasoning"  # Logical gaps
    CONFLICT = "conflict"  # Contradictory evidence


class ConstraintType(str, Enum):
    """Types of constraints."""
    HARD = "hard"  # Must be satisfied
    SOFT = "soft"  # Preferred but not required


class Hypothesis(BaseModel):
    """A hypothesis to be tested."""

    id: str
    statement: str
    confidence: float = 0.5  # Prior probability
    status: HypothesisStatus = HypothesisStatus.PENDING
    supporting_evidence: List[str] = []
    refuting_evidence: List[str] = []
    uncertainty_sources: List[UncertaintySource] = []


class CounterfactualScenario(BaseModel):
    """A what-if scenario for counterfactual reasoning."""

    id: str
    description: str
    modifications: Dict[str, Any]  # Field -> new value
    predicted_outcome: Optional[Dict[str, Any]] = None
    actual_outcome: Optional[Dict[str, Any]] = None
    sensitivity: Optional[float] = None  # How much outcome changes


class Constraint(BaseModel):
    """A constraint on agent decisions."""

    id: str
    description: str
    type: ConstraintType
    condition: str  # Python expression or description
    satisfied: Optional[bool] = None
    violation_message: Optional[str] = None


class UncertaintyEstimate(BaseModel):
    """Uncertainty quantification."""

    confidence: float  # Overall confidence [0, 1]
    sources: Dict[UncertaintySource, float]  # Source -> contribution
    propagated: bool = False  # Whether uncertainty was propagated
    explanation: str = ""


class ReasoningEngine:
    """
    Advanced reasoning engine for fraud detection.

    Provides:
    - Self-critique of reasoning
    - Hypothesis testing
    - Counterfactual reasoning
    - Uncertainty estimation
    - Constraint satisfaction

    Example:
        ```python
        engine = ReasoningEngine()

        # Test hypothesis
        hypothesis = Hypothesis(
            id="h1",
            statement="This transaction is fraud",
            confidence=0.7
        )

        evidence = {
            "high_value": True,
            "policy_violation": True,
            "clean_history": True
        }

        result = engine.test_hypothesis(hypothesis, evidence)
        # result.status == HypothesisStatus.UNCERTAIN (conflicting evidence)
        ```
    """

    def self_critique(
        self,
        reasoning_steps: List[str],
        decision: Dict[str, Any],
        evidence: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Critique own reasoning for soundness and completeness.

        Args:
            reasoning_steps: Chain of reasoning
            decision: Final decision
            evidence: Available evidence

        Returns:
            Critique with issues found and suggestions
        """
        logger.info("Performing self-critique")

        critique = {
            "is_sound": True,
            "is_complete": True,
            "contradictions": [],
            "missing_evidence": [],
            "unsupported_claims": [],
            "suggestions": [],
        }

        # Check for contradictions
        for i, step in enumerate(reasoning_steps):
            for j, other_step in enumerate(reasoning_steps):
                if i >= j:
                    continue

                # Simple contradiction detection
                if "high risk" in step.lower() and "low risk" in other_step.lower():
                    critique["contradictions"].append({
                        "step1": i,
                        "step2": j,
                        "description": "Risk assessment contradiction"
                    })
                    critique["is_sound"] = False

        # Check if all evidence was considered
        evidence_keys = set(evidence.keys())
        mentioned_evidence = set()

        for step in reasoning_steps:
            for key in evidence_keys:
                if key in step.lower().replace("_", " "):
                    mentioned_evidence.add(key)

        missing = evidence_keys - mentioned_evidence
        if missing:
            critique["missing_evidence"] = list(missing)
            critique["is_complete"] = False
            critique["suggestions"].append(
                f"Consider evidence: {', '.join(missing)}"
            )

        # Check if reasoning supports decision
        decision_is_fraud = decision.get("is_fraud", False)
        fraud_indicators = sum(
            1 for step in reasoning_steps
            if "fraud" in step.lower() or "suspicious" in step.lower()
        )

        if decision_is_fraud and fraud_indicators == 0:
            critique["unsupported_claims"].append(
                "Decision is fraud but no fraud indicators in reasoning"
            )
            critique["is_sound"] = False

        # Check reasoning chain length
        if len(reasoning_steps) < 3:
            critique["suggestions"].append(
                "Reasoning chain is short - consider more detailed analysis"
            )

        return critique

    def test_hypothesis(
        self,
        hypothesis: Hypothesis,
        evidence: Dict[str, Any],
    ) -> Hypothesis:
        """
        Test hypothesis against evidence.

        Args:
            hypothesis: Hypothesis to test
            evidence: Available evidence

        Returns:
            Updated hypothesis with status and evidence
        """
        logger.info(f"Testing hypothesis: {hypothesis.statement}")

        supporting = []
        refuting = []

        # Fraud hypothesis testing
        if "fraud" in hypothesis.statement.lower():
            # Supporting evidence for fraud
            if evidence.get("high_value"):
                supporting.append("Transaction amount is unusually high")

            if evidence.get("policy_violation"):
                supporting.append("Transaction violates fraud policy")

            if evidence.get("account_drained"):
                supporting.append("Account balance drained")

            if evidence.get("suspicious_pattern"):
                supporting.append("Matches known fraud pattern")

            # Refuting evidence for fraud
            if evidence.get("clean_history"):
                refuting.append("Account has clean history")

            if evidence.get("normal_amount"):
                refuting.append("Transaction amount is normal")

            if evidence.get("verified_merchant"):
                refuting.append("Merchant is verified and trusted")

        # Update hypothesis
        hypothesis.supporting_evidence = supporting
        hypothesis.refuting_evidence = refuting

        # Determine status based on evidence balance
        support_count = len(supporting)
        refute_count = len(refuting)

        if support_count > refute_count + 1:
            hypothesis.status = HypothesisStatus.SUPPORTED
            hypothesis.confidence = min(0.95, 0.5 + (support_count * 0.1))
        elif refute_count > support_count + 1:
            hypothesis.status = HypothesisStatus.REFUTED
            hypothesis.confidence = max(0.05, 0.5 - (refute_count * 0.1))
        else:
            hypothesis.status = HypothesisStatus.UNCERTAIN
            hypothesis.confidence = 0.5
            hypothesis.uncertainty_sources.append(UncertaintySource.CONFLICT)

        logger.info(
            f"Hypothesis {hypothesis.status.value}: "
            f"confidence={hypothesis.confidence:.2f}, "
            f"support={support_count}, refute={refute_count}"
        )

        return hypothesis

    def counterfactual_reasoning(
        self,
        transaction: Dict[str, Any],
        decision: Dict[str, Any],
        what_ifs: List[Dict[str, Any]],
    ) -> List[CounterfactualScenario]:
        """
        Perform counterfactual reasoning (what-if analysis).

        Args:
            transaction: Original transaction
            decision: Original decision
            what_ifs: List of modifications to test
                e.g., [{"amount": 1000000}, {"type": "CASH_OUT"}]

        Returns:
            List of counterfactual scenarios with predictions
        """
        logger.info(f"Performing {len(what_ifs)} counterfactual analyses")

        scenarios = []

        for i, modifications in enumerate(what_ifs):
            # Create modified transaction
            modified = deepcopy(transaction)
            modified.update(modifications)

            # Predict outcome (heuristic)
            predicted = self._predict_outcome(modified, decision)

            scenario = CounterfactualScenario(
                id=f"cf_{i}",
                description=self._describe_modification(modifications),
                modifications=modifications,
                predicted_outcome=predicted,
            )

            # Calculate sensitivity (how much did outcome change?)
            scenario.sensitivity = self._calculate_sensitivity(
                decision, predicted
            )

            scenarios.append(scenario)

            logger.info(
                f"Scenario {scenario.id}: {scenario.description} -> "
                f"sensitivity={scenario.sensitivity:.2f}"
            )

        return scenarios

    def _predict_outcome(
        self,
        transaction: Dict[str, Any],
        original_decision: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Predict outcome for modified transaction."""
        # Heuristic prediction logic - recalculate from scratch
        amount = transaction.get("amount", 0)
        tx_type = transaction.get("type", "")

        # Start with base risk
        risk_score = 0.0

        # Amount-based risk
        if amount > 100000:
            risk_score += 40
        elif amount > 50000:
            risk_score += 25
        elif amount > 10000:
            risk_score += 10

        # Type-based risk
        if tx_type in ["CASH_OUT", "TRANSFER"]:
            risk_score += 20
        elif tx_type == "PAYMENT":
            risk_score += 5

        # Balance checks
        old_balance = transaction.get("oldbalanceOrg", 0)
        new_balance = transaction.get("newbalanceOrig", 0)

        if old_balance > 0 and new_balance == 0:
            risk_score += 30  # Account drained

        risk_score = min(100, max(0, risk_score))

        return {
            "risk_score": risk_score,
            "is_fraud": risk_score >= 50,
            "confidence": 0.7,
        }

    def _describe_modification(self, modifications: Dict[str, Any]) -> str:
        """Create human-readable description of modification."""
        parts = []
        for key, value in modifications.items():
            parts.append(f"{key}={value}")
        return f"What if {', '.join(parts)}?"

    def _calculate_sensitivity(
        self,
        original: Dict[str, Any],
        modified: Dict[str, Any]
    ) -> float:
        """
        Calculate how sensitive outcome is to modification.

        Returns:
            Sensitivity score [0, 1]
        """
        orig_risk = original.get("risk_score", 0)
        mod_risk = modified.get("risk_score", 0)

        # Normalized difference
        sensitivity = abs(mod_risk - orig_risk) / 100.0
        return min(1.0, sensitivity)

    def estimate_uncertainty(
        self,
        evidence: Dict[str, Any],
        reasoning_steps: List[str],
        decision: Dict[str, Any],
    ) -> UncertaintyEstimate:
        """
        Estimate uncertainty in decision.

        Args:
            evidence: Available evidence
            reasoning_steps: Chain of reasoning
            decision: Final decision

        Returns:
            Uncertainty estimate with sources
        """
        logger.info("Estimating uncertainty")

        sources = {
            UncertaintySource.DATA: 0.0,
            UncertaintySource.MODEL: 0.0,
            UncertaintySource.REASONING: 0.0,
            UncertaintySource.CONFLICT: 0.0,
        }

        # Data uncertainty - missing fields
        expected_fields = {"amount", "type", "oldbalanceOrg", "newbalanceOrig"}
        available_fields = set(evidence.keys())
        missing_ratio = len(expected_fields - available_fields) / len(expected_fields)
        sources[UncertaintySource.DATA] = missing_ratio * 0.3

        # Reasoning uncertainty - short chain or contradictions
        if len(reasoning_steps) < 3:
            sources[UncertaintySource.REASONING] = 0.2

        # Check for contradictory reasoning
        contradictions = sum(
            1 for step in reasoning_steps
            if ("but" in step.lower() or "however" in step.lower())
        )
        if contradictions > 0:
            sources[UncertaintySource.CONFLICT] = min(0.3, contradictions * 0.1)

        # Model uncertainty (fixed for heuristic models)
        sources[UncertaintySource.MODEL] = 0.1

        # Combine sources (sum with saturation)
        total_uncertainty = min(1.0, sum(sources.values()))
        confidence = 1.0 - total_uncertainty

        explanation_parts = []
        for source, value in sources.items():
            if value > 0.05:
                explanation_parts.append(f"{source.value}={value:.2f}")

        estimate = UncertaintyEstimate(
            confidence=confidence,
            sources=sources,
            propagated=True,
            explanation=f"Uncertainty from: {', '.join(explanation_parts)}",
        )

        logger.info(f"Uncertainty estimate: confidence={confidence:.2f}")
        return estimate

    def satisfy_constraints(
        self,
        decision: Dict[str, Any],
        constraints: List[Constraint],
    ) -> Tuple[bool, List[Constraint]]:
        """
        Check if decision satisfies constraints.

        Args:
            decision: Proposed decision
            constraints: List of constraints

        Returns:
            (all_satisfied, violated_constraints)
        """
        logger.info(f"Checking {len(constraints)} constraints")

        violated = []

        for constraint in constraints:
            satisfied = self._check_constraint(decision, constraint)
            constraint.satisfied = satisfied

            if not satisfied:
                if constraint.type == ConstraintType.HARD:
                    violated.append(constraint)
                    logger.warning(f"Hard constraint violated: {constraint.description}")
                else:
                    logger.info(f"Soft constraint violated: {constraint.description}")

        all_satisfied = len(violated) == 0
        return all_satisfied, violated

    def _check_constraint(
        self,
        decision: Dict[str, Any],
        constraint: Constraint
    ) -> bool:
        """Check single constraint."""
        # Hard-coded constraint checks (in production, parse condition)
        condition = constraint.condition.lower()

        # Never approve >$200k
        if "200" in condition and "amount" in condition:
            amount = decision.get("amount", 0)
            if amount > 200000 and decision.get("is_fraud") == False:
                constraint.violation_message = f"Amount ${amount} exceeds $200k threshold"
                return False

        # Prefer review over block
        if "review" in condition and "block" in condition:
            action = decision.get("action", "")
            confidence = decision.get("confidence", 1.0)
            if action == "BLOCK" and confidence < 0.9:
                constraint.violation_message = "Should review instead of block (low confidence)"
                return constraint.type == ConstraintType.SOFT  # Soft constraint allows violation

        # Confidence threshold for auto-decision (two forms)
        if "confidence" in condition and ("threshold" in condition or "0.7" in condition):
            confidence = decision.get("confidence", 0.5)
            requires_review = decision.get("requires_review", None)

            # If confidence < 0.7, should require review
            if confidence < 0.7:
                if requires_review is False:
                    constraint.violation_message = f"Confidence {confidence:.2f} below 0.7 threshold - requires review"
                    return False
                elif requires_review is None:
                    # Not explicitly set - treat as pass since constraint says "or"
                    pass

        return True

    def propagate_uncertainty(
        self,
        uncertainties: List[UncertaintyEstimate],
    ) -> UncertaintyEstimate:
        """
        Propagate uncertainties through reasoning chain.

        Args:
            uncertainties: List of uncertainty estimates

        Returns:
            Combined uncertainty estimate
        """
        if not uncertainties:
            return UncertaintyEstimate(confidence=1.0, sources={})

        # Combine confidences (product for independent events)
        combined_confidence = 1.0
        for unc in uncertainties:
            combined_confidence *= unc.confidence

        # Combine sources (max contribution from each source)
        combined_sources = {}
        for source in UncertaintySource:
            max_contrib = max(
                (unc.sources.get(source, 0.0) for unc in uncertainties),
                default=0.0
            )
            if max_contrib > 0:
                combined_sources[source] = max_contrib

        return UncertaintyEstimate(
            confidence=combined_confidence,
            sources=combined_sources,
            propagated=True,
            explanation=f"Propagated from {len(uncertainties)} estimates",
        )
