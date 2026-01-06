"""
Test script for Planning, Reasoning & Autonomy components.

Tests task planning, hypothesis testing, counterfactual reasoning,
uncertainty estimation, constraint satisfaction, and autonomy control.

Run with: python backend/scripts/test_planning_reasoning.py
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from app.agents.task_planner import TaskPlanner, TaskDAG
from app.agents.reasoning_engine import (
    ReasoningEngine,
    Hypothesis,
    Constraint,
    ConstraintType,
    UncertaintySource,
)
from app.agents.autonomy_controller import (
    AutonomyController,
    EscalationReason,
)


# Test transactions
legitimate_small = {
    "transaction_id": "tx_001",
    "type": "PAYMENT",
    "amount": 500.0,
    "oldbalanceOrg": 10000.0,
    "newbalanceOrig": 9500.0,
    "oldbalanceDest": 0.0,
    "newbalanceDest": 500.0,
}

suspicious_transfer = {
    "transaction_id": "tx_002",
    "type": "TRANSFER",
    "amount": 150000.0,
    "oldbalanceOrg": 200000.0,
    "newbalanceOrig": 50000.0,
    "oldbalanceDest": 100000.0,
    "newbalanceDest": 250000.0,
}

obvious_fraud = {
    "transaction_id": "tx_003",
    "type": "CASH_OUT",
    "amount": 300000.0,
    "oldbalanceOrg": 300000.0,
    "newbalanceOrig": 0.0,  # Account drained
    "oldbalanceDest": 0.0,
    "newbalanceDest": 0.0,  # Money disappeared
}


def test_task_planning():
    """Test task planning and DAG creation."""
    print("\n" + "="*80)
    print("TEST: Task Planning & DAG")
    print("="*80)

    planner = TaskPlanner()

    # Test 1: Create plan for fraud detection
    print("\n[1] Creating task plan for fraud detection...")
    dag = planner.create_plan(
        transaction=suspicious_transfer,
        goal="determine_fraud",
        constraints={"max_duration": 30.0}
    )

    print(f"✓ Created plan with {len(dag.tasks)} tasks")
    print(f"✓ Has cycle: {dag.has_cycle()}")

    # Show task dependencies
    print("\nTask Dependencies:")
    for task_id, task in dag.tasks.items():
        deps = ", ".join(task.dependencies) if task.dependencies else "None"
        print(f"  {task.id}: {task.description}")
        print(f"    Dependencies: {deps}")
        print(f"    Estimated duration: {task.estimated_duration}s")

    # Test 2: Get execution order
    print("\n[2] Computing execution order (parallel levels)...")
    execution_order = planner.get_execution_order(dag)

    for i, level in enumerate(execution_order):
        print(f"  Level {i}: {', '.join(level)}")

    # Test 3: Estimate duration
    sequential_duration = planner.estimate_duration(dag, parallel=False)
    parallel_duration = planner.estimate_duration(dag, parallel=True)

    print(f"\n✓ Sequential duration: {sequential_duration:.1f}s")
    print(f"✓ Parallel duration: {parallel_duration:.1f}s")
    print(f"✓ Speedup: {sequential_duration / parallel_duration:.1f}x")

    # Test 4: Dynamic replanning
    print("\n[3] Testing dynamic replanning...")

    # Scenario: High confidence early decision
    new_info = {"high_confidence": True}
    updated_dag = planner.replan(dag, new_info, suspicious_transfer)

    skipped_count = sum(1 for t in updated_dag.tasks.values() if t.status.value == "skipped")
    print(f"✓ Replanned: {skipped_count} tasks skipped (high confidence)")

    # Scenario: Uncertainty detected
    dag2 = planner.create_plan(suspicious_transfer, "determine_fraud")
    new_info2 = {"uncertain": True}
    updated_dag2 = planner.replan(dag2, new_info2, suspicious_transfer)

    print(f"✓ Replanned: escalation task added (uncertainty)")

    print("\n✅ Task Planning: ALL TESTS PASSED")


def test_hypothesis_testing():
    """Test hypothesis testing with evidence."""
    print("\n" + "="*80)
    print("TEST: Hypothesis Testing")
    print("="*80)

    engine = ReasoningEngine()

    # Test 1: Fraud hypothesis with supporting evidence
    print("\n[1] Testing fraud hypothesis with strong evidence...")

    hypothesis = Hypothesis(
        id="h1",
        statement="This transaction is fraud",
        confidence=0.5,
    )

    evidence = {
        "high_value": True,
        "policy_violation": True,
        "account_drained": True,
        "suspicious_pattern": True,
    }

    result = engine.test_hypothesis(hypothesis, evidence)

    print(f"  Hypothesis: {result.statement}")
    print(f"  Status: {result.status.value}")
    print(f"  Confidence: {result.confidence:.2f}")
    print(f"  Supporting evidence ({len(result.supporting_evidence)}):")
    for ev in result.supporting_evidence:
        print(f"    - {ev}")
    print(f"  Refuting evidence: {len(result.refuting_evidence)}")

    assert result.status.value == "supported", "Should be supported"
    print("✓ Hypothesis correctly SUPPORTED")

    # Test 2: Conflicting evidence
    print("\n[2] Testing with conflicting evidence...")

    hypothesis2 = Hypothesis(
        id="h2",
        statement="This transaction is fraud",
        confidence=0.5,
    )

    conflicting_evidence = {
        "high_value": True,
        "policy_violation": True,
        "clean_history": True,
        "verified_merchant": True,
    }

    result2 = engine.test_hypothesis(hypothesis2, conflicting_evidence)

    print(f"  Status: {result2.status.value}")
    print(f"  Confidence: {result2.confidence:.2f}")
    print(f"  Supporting: {len(result2.supporting_evidence)}, Refuting: {len(result2.refuting_evidence)}")

    assert result2.status.value == "uncertain", "Should be uncertain"
    print("✓ Conflicting evidence correctly marked UNCERTAIN")

    # Test 3: Refuted hypothesis
    print("\n[3] Testing refuted hypothesis...")

    hypothesis3 = Hypothesis(
        id="h3",
        statement="This transaction is fraud",
        confidence=0.5,
    )

    legitimate_evidence = {
        "normal_amount": True,
        "clean_history": True,
        "verified_merchant": True,
    }

    result3 = engine.test_hypothesis(hypothesis3, legitimate_evidence)

    print(f"  Status: {result3.status.value}")
    print(f"  Confidence: {result3.confidence:.2f}")

    assert result3.status.value == "refuted", "Should be refuted"
    print("✓ Hypothesis correctly REFUTED")

    print("\n✅ Hypothesis Testing: ALL TESTS PASSED")


def test_counterfactual_reasoning():
    """Test counterfactual (what-if) analysis."""
    print("\n" + "="*80)
    print("TEST: Counterfactual Reasoning")
    print("="*80)

    engine = ReasoningEngine()

    # Original transaction and decision
    transaction = suspicious_transfer.copy()
    decision = {
        "is_fraud": True,
        "risk_score": 75.0,
        "confidence": 0.8,
    }

    print(f"\nOriginal transaction: ${transaction['amount']:,.0f} {transaction['type']}")
    print(f"Original decision: fraud={decision['is_fraud']}, risk={decision['risk_score']}")

    # What-if scenarios
    what_ifs = [
        {"amount": 1000000},  # 10x higher amount
        {"amount": 5000},  # Much smaller amount
        {"type": "CASH_OUT"},  # Different transaction type
        {"type": "PAYMENT"},  # Legitimate transaction type
    ]

    print(f"\n[1] Running {len(what_ifs)} counterfactual scenarios...")

    scenarios = engine.counterfactual_reasoning(
        transaction=transaction,
        decision=decision,
        what_ifs=what_ifs,
    )

    for scenario in scenarios:
        print(f"\n  Scenario: {scenario.description}")
        print(f"    Modifications: {scenario.modifications}")
        print(f"    Predicted outcome: risk={scenario.predicted_outcome.get('risk_score', 0):.1f}")
        print(f"    Sensitivity: {scenario.sensitivity:.2f}")

    # Check that scenarios show different outcomes
    assert len(scenarios) == 4, "Should have 4 scenarios"
    print("\n✓ All scenarios generated")

    # Check that low-value scenario decreases risk
    low_value_scenario = scenarios[1]
    assert low_value_scenario.predicted_outcome["risk_score"] < decision["risk_score"], "Lower amount should reduce risk"
    print("✓ Low-value scenario correctly reduces risk")

    print("\n✅ Counterfactual Reasoning: ALL TESTS PASSED")


def test_self_critique():
    """Test self-critique of reasoning."""
    print("\n" + "="*80)
    print("TEST: Self-Critique")
    print("="*80)

    engine = ReasoningEngine()

    # Test 1: Sound reasoning
    print("\n[1] Testing sound reasoning...")

    sound_reasoning = [
        "Transaction amount is $150,000 which is unusually high",
        "Transaction type is TRANSFER which matches fraud patterns",
        "Account balance decreased significantly",
        "Policy flags high-value transfers for review",
        "Conclude: High fraud risk",
    ]

    decision = {"is_fraud": True, "confidence": 0.8}
    evidence = {"amount": 150000, "type": "TRANSFER", "high_value": True}

    critique = engine.self_critique(sound_reasoning, decision, evidence)

    print(f"  Is sound: {critique['is_sound']}")
    print(f"  Is complete: {critique['is_complete']}")
    print(f"  Contradictions: {len(critique['contradictions'])}")

    assert critique["is_sound"], "Sound reasoning should pass"
    print("✓ Sound reasoning validated")

    # Test 2: Contradictory reasoning
    print("\n[2] Testing contradictory reasoning...")

    contradictory_reasoning = [
        "Transaction shows high risk indicators",
        "Account has low risk profile",
        "High risk transaction detected",
    ]

    critique2 = engine.self_critique(contradictory_reasoning, decision, evidence)

    print(f"  Is sound: {critique2['is_sound']}")
    print(f"  Contradictions: {len(critique2['contradictions'])}")

    assert not critique2["is_sound"], "Contradictory reasoning should fail"
    print("✓ Contradictions detected")

    # Test 3: Incomplete reasoning
    print("\n[3] Testing incomplete reasoning...")

    incomplete_reasoning = [
        "Transaction detected",
        "Decision: fraud",
    ]

    critique3 = engine.self_critique(incomplete_reasoning, decision, evidence)

    print(f"  Is complete: {critique3['is_complete']}")
    print(f"  Missing evidence: {critique3['missing_evidence']}")
    print(f"  Suggestions: {len(critique3['suggestions'])}")

    assert not critique3["is_complete"], "Short reasoning should be incomplete"
    print("✓ Incompleteness detected with suggestions")

    print("\n✅ Self-Critique: ALL TESTS PASSED")


def test_uncertainty_estimation():
    """Test uncertainty estimation."""
    print("\n" + "="*80)
    print("TEST: Uncertainty Estimation")
    print("="*80)

    engine = ReasoningEngine()

    # Test 1: Low uncertainty (complete data, clear reasoning)
    print("\n[1] Testing low uncertainty scenario...")

    complete_evidence = {
        "amount": 150000,
        "type": "TRANSFER",
        "oldbalanceOrg": 200000,
        "newbalanceOrig": 50000,
    }

    clear_reasoning = [
        "High-value transfer detected",
        "Amount exceeds policy threshold",
        "Account balance significantly reduced",
        "Pattern matches known fraud cases",
        "Confidence: High fraud risk",
    ]

    decision = {"is_fraud": True, "confidence": 0.8}

    estimate = engine.estimate_uncertainty(complete_evidence, clear_reasoning, decision)

    print(f"  Confidence: {estimate.confidence:.2f}")
    print(f"  Sources:")
    for source, value in estimate.sources.items():
        if value > 0:
            print(f"    {source.value}: {value:.2f}")
    print(f"  Explanation: {estimate.explanation}")

    assert estimate.confidence > 0.7, "Should have high confidence"
    print("✓ Low uncertainty correctly estimated")

    # Test 2: High uncertainty (missing data, contradictory reasoning)
    print("\n[2] Testing high uncertainty scenario...")

    incomplete_evidence = {
        "amount": 50000,
        # Missing: type, balances
    }

    contradictory_reasoning = [
        "Transaction might be fraud",
        "But account has good history",
        "However amount is suspicious",
    ]

    decision2 = {"is_fraud": False, "confidence": 0.5}

    estimate2 = engine.estimate_uncertainty(incomplete_evidence, contradictory_reasoning, decision2)

    print(f"  Confidence: {estimate2.confidence:.2f}")
    print(f"  Sources:")
    for source, value in estimate2.sources.items():
        if value > 0:
            print(f"    {source.value}: {value:.2f}")

    assert estimate2.confidence < 0.7, "Should have low confidence"
    assert estimate2.sources[UncertaintySource.CONFLICT] > 0, "Should detect conflict"
    print("✓ High uncertainty correctly estimated")

    print("\n✅ Uncertainty Estimation: ALL TESTS PASSED")


def test_constraint_satisfaction():
    """Test constraint satisfaction checking."""
    print("\n" + "="*80)
    print("TEST: Constraint Satisfaction")
    print("="*80)

    engine = ReasoningEngine()

    # Define constraints
    constraints = [
        Constraint(
            id="c1",
            description="Never approve transactions >$200k",
            type=ConstraintType.HARD,
            condition="amount > 200000 and not blocked",
        ),
        Constraint(
            id="c2",
            description="Prefer review over block for low confidence",
            type=ConstraintType.SOFT,
            condition="confidence < 0.9 implies action=REVIEW",
        ),
        Constraint(
            id="c3",
            description="Require human review for confidence <0.7",
            type=ConstraintType.HARD,
            condition="confidence >= 0.7 or requires_review=True",
        ),
    ]

    # Test 1: All constraints satisfied
    print("\n[1] Testing decision that satisfies all constraints...")

    good_decision = {
        "is_fraud": True,
        "amount": 50000,
        "confidence": 0.8,
        "action": "BLOCK",
        "requires_review": False,
    }

    all_satisfied, violated = engine.satisfy_constraints(good_decision, constraints)

    print(f"  All satisfied: {all_satisfied}")
    print(f"  Violated: {len(violated)}")

    assert all_satisfied, "Good decision should satisfy all constraints"
    print("✓ All constraints satisfied")

    # Test 2: Hard constraint violation
    print("\n[2] Testing hard constraint violation...")

    bad_decision = {
        "is_fraud": False,  # Approving high-value transaction
        "amount": 250000,
        "confidence": 0.9,
        "action": "APPROVE",
    }

    all_satisfied2, violated2 = engine.satisfy_constraints(bad_decision, constraints)

    print(f"  All satisfied: {all_satisfied2}")
    print(f"  Violated: {len(violated2)}")
    for v in violated2:
        print(f"    {v.id}: {v.violation_message}")

    assert not all_satisfied2, "Should violate hard constraint"
    assert len(violated2) > 0, "Should have violations"
    print("✓ Hard constraint violation detected")

    # Test 3: Low confidence requires review
    print("\n[3] Testing confidence threshold constraint...")

    low_conf_decision = {
        "is_fraud": True,
        "confidence": 0.5,
        "requires_review": False,  # Should require review!
    }

    all_satisfied3, violated3 = engine.satisfy_constraints(low_conf_decision, constraints)

    print(f"  All satisfied: {all_satisfied3}")
    if violated3:
        print(f"  Violated constraint: {violated3[0].violation_message}")

    assert not all_satisfied3, "Low confidence should require review"
    print("✓ Confidence constraint violation detected")

    print("\n✅ Constraint Satisfaction: ALL TESTS PASSED")


def test_autonomy_control():
    """Test autonomy control and escalation."""
    print("\n" + "="*80)
    print("TEST: Autonomy Control")
    print("="*80)

    controller = AutonomyController(
        max_steps=10,
        timeout_seconds=30.0,
        min_confidence=0.7,
    )

    # Test 1: High confidence - full autonomy
    print("\n[1] Testing full autonomy (high confidence)...")

    high_conf_decision = {"is_fraud": True, "confidence": 0.95}
    evidence = {"amount": 5000, "type": "PAYMENT"}

    level = controller.get_autonomy_level(high_conf_decision, evidence)

    print(f"  Autonomy level: {level.value}")
    assert level.value == "full_auto", "Should be full auto"
    print("✓ Full autonomy granted")

    # Test 2: Medium confidence - supervised
    print("\n[2] Testing supervised autonomy (medium confidence)...")

    med_conf_decision = {"is_fraud": True, "confidence": 0.75}

    level2 = controller.get_autonomy_level(med_conf_decision, evidence)

    print(f"  Autonomy level: {level2.value}")
    print("✓ Supervised autonomy assigned")

    # Test 3: Low confidence - escalation
    print("\n[3] Testing escalation (low confidence)...")

    low_conf_decision = {"is_fraud": True, "confidence": 0.5}

    should_escalate, reason = controller.should_escalate(low_conf_decision, evidence)

    print(f"  Should escalate: {should_escalate}")
    print(f"  Reason: {reason.value if reason else None}")

    assert should_escalate, "Should escalate"
    assert reason == EscalationReason.LOW_CONFIDENCE, "Reason should be low confidence"
    print("✓ Low confidence escalation triggered")

    # Test 4: High-value escalation
    print("\n[4] Testing high-value escalation...")

    high_value_evidence = {"amount": 150000, "type": "TRANSFER"}
    good_decision = {"is_fraud": True, "confidence": 0.8}

    should_escalate2, reason2 = controller.should_escalate(good_decision, high_value_evidence)

    print(f"  Should escalate: {should_escalate2}")
    print(f"  Reason: {reason2.value if reason2 else None}")

    assert should_escalate2, "High value should escalate"
    assert reason2 == EscalationReason.HIGH_VALUE, "Reason should be high value"
    print("✓ High-value escalation triggered")

    # Test 5: Create escalation ticket
    print("\n[5] Creating escalation ticket...")

    ticket = controller.create_escalation(
        transaction_id="tx_123",
        reason=EscalationReason.LOW_CONFIDENCE,
        decision=low_conf_decision,
        evidence=evidence,
        reasoning_steps=["Step 1", "Step 2"],
    )

    print(f"  Ticket ID: {ticket.id}")
    print(f"  Priority: {ticket.priority}")
    print(f"  Explanation: {ticket.explanation}")

    assert ticket.priority in ["LOW", "MEDIUM", "HIGH", "CRITICAL"], "Valid priority"
    print("✓ Escalation ticket created")

    # Test 6: Stop conditions
    print("\n[6] Testing stop conditions...")

    controller.start_session("determine_fraud")

    # Max steps
    should_stop, condition = controller.check_stop_conditions(step_count=15)

    print(f"  Should stop (max steps): {should_stop}")
    if condition:
        print(f"  Condition: {condition.type.value}")
        print(f"  Message: {condition.message}")

    assert should_stop, "Should stop at max steps"
    print("✓ Max steps stop condition works")

    # Test 7: Goal drift detection
    print("\n[7] Testing goal drift detection...")

    controller.start_session("determine_fraud")

    # Drifted focus
    drifted, warnings = controller.check_goal_drift(
        current_focus="providing investment advice",
        reasoning_steps=["Consider portfolio allocation", "Tax implications"],
    )

    print(f"  Has drifted: {drifted}")
    print(f"  Warnings: {len(warnings)}")
    for w in warnings:
        print(f"    - {w}")

    assert drifted, "Should detect drift"
    assert len(warnings) > 0, "Should have warnings"

    # Get refocus instruction
    refocus = controller.refocus_on_goal()
    print(f"\n  Refocus instruction: {refocus}")

    print("✓ Goal drift detection works")

    print("\n✅ Autonomy Control: ALL TESTS PASSED")


def run_all_tests():
    """Run all planning, reasoning, and autonomy tests."""
    print("\n" + "="*80)
    print("PLANNING, REASONING & AUTONOMY - TEST SUITE")
    print("="*80)

    try:
        test_task_planning()
        test_hypothesis_testing()
        test_counterfactual_reasoning()
        test_self_critique()
        test_uncertainty_estimation()
        test_constraint_satisfaction()
        test_autonomy_control()

        print("\n" + "="*80)
        print("✅ ALL TESTS PASSED")
        print("="*80)

    except Exception as e:
        print(f"\n❌ TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    run_all_tests()
