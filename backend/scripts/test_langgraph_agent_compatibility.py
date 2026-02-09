"""
Test script for Phase 8.2: LangGraph Single Agent Compatibility.

This script validates that both implementations (original and LangGraph)
produce consistent results for the same input transactions.

Usage:
    python backend/scripts/test_langgraph_agent_compatibility.py

Expected output:
    ✅ All tests passed - LangGraph implementation maintains API compatibility
"""

import asyncio
import sys
import os
from datetime import datetime

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.agents import FraudDetectionAgent as OriginalAgent
from app.agents.langgraph import FraudDetectionAgentLangGraph as LangGraphAgent


# ============================================================================
# Test Transactions
# ============================================================================

TEST_TRANSACTIONS = [
    {
        "name": "Legitimate Small Payment",
        "transaction": {
            "transaction_id": "TXN_001",
            "amount": 500.0,
            "type": "PAYMENT",
            "oldbalanceOrg": 10000.0,
            "newbalanceOrig": 9500.0,
            "oldbalanceDest": 2000.0,
            "newbalanceDest": 2500.0,
            "nameOrig": "C123456789",
            "nameDest": "M987654321",
        },
        "expected_fraud": False,
    },
    {
        "name": "High-Value Suspicious Transfer",
        "transaction": {
            "transaction_id": "TXN_002",
            "amount": 200000.0,
            "type": "TRANSFER",
            "oldbalanceOrg": 250000.0,
            "newbalanceOrig": 50000.0,
            "oldbalanceDest": 0.0,
            "newbalanceDest": 0.0,
            "nameOrig": "C987654321",
            "nameDest": "C111222333",
        },
        "expected_fraud": True,
    },
    {
        "name": "Account Draining (CASH_OUT)",
        "transaction": {
            "transaction_id": "TXN_003",
            "amount": 150000.0,
            "type": "CASH_OUT",
            "oldbalanceOrg": 150000.0,
            "newbalanceOrig": 0.0,
            "oldbalanceDest": 0.0,
            "newbalanceDest": 0.0,
            "nameOrig": "C555666777",
            "nameDest": "C999888777",
        },
        "expected_fraud": True,
    },
    {
        "name": "Normal Medium Transfer",
        "transaction": {
            "transaction_id": "TXN_004",
            "amount": 5000.0,
            "type": "TRANSFER",
            "oldbalanceOrg": 20000.0,
            "newbalanceOrig": 15000.0,
            "oldbalanceDest": 10000.0,
            "newbalanceDest": 15000.0,
            "nameOrig": "C111111111",
            "nameDest": "C222222222",
        },
        "expected_fraud": False,
    },
]


# ============================================================================
# Test Functions
# ============================================================================


async def test_implementation(agent_name: str, agent, transaction_data: dict) -> dict:
    """
    Test a single implementation with a transaction.

    Args:
        agent_name: Name of the agent (for logging)
        agent: Agent instance
        transaction_data: Transaction test data

    Returns:
        Test result dictionary
    """
    transaction = transaction_data["transaction"]
    txn_id = transaction["transaction_id"]

    try:
        result = await agent.analyze(transaction, txn_id)

        return {
            "success": True,
            "is_fraud": result.is_fraud,
            "risk_score": result.risk_score,
            "risk_level": result.risk_level,
            "confidence": result.confidence,
            "total_steps": result.total_steps,
            "execution_time": result.execution_time,
            "escalation": result.should_escalate,
            "anomalies_count": len(result.anomalies),
            "reasoning_count": len(result.reasoning_steps),
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


async def compare_implementations(transaction_data: dict) -> dict:
    """
    Compare original and LangGraph implementations on same transaction.

    Args:
        transaction_data: Transaction test data

    Returns:
        Comparison results
    """
    print(f"\n{'='*80}")
    print(f"Testing: {transaction_data['name']}")
    print(f"{'='*80}")

    # Initialize both agents
    original_agent = OriginalAgent(max_steps=20)
    langgraph_agent = LangGraphAgent(max_steps=20)

    # Test original implementation
    original_result = await test_implementation(
        "Original", original_agent, transaction_data
    )

    # Test LangGraph implementation
    langgraph_result = await test_implementation(
        "LangGraph", langgraph_agent, transaction_data
    )

    # Compare results
    if not original_result["success"] or not langgraph_result["success"]:
        print("❌ FAILED - One or both implementations errored")
        if not original_result["success"]:
            print(f"   Original error: {original_result.get('error')}")
        if not langgraph_result["success"]:
            print(f"   LangGraph error: {langgraph_result.get('error')}")
        return {"passed": False, "reason": "Implementation error"}

    # Check fraud detection consistency
    fraud_match = original_result["is_fraud"] == langgraph_result["is_fraud"]

    # Check risk level consistency (allow some variation)
    risk_score_diff = abs(
        original_result["risk_score"] - langgraph_result["risk_score"]
    )
    risk_consistent = risk_score_diff < 10.0  # Allow 10-point variation

    # Print comparison
    print("\n📊 Results Comparison:")
    print(f"\n   Original Implementation:")
    print(f"      Fraud: {original_result['is_fraud']}")
    print(f"      Risk Score: {original_result['risk_score']:.1f}")
    print(f"      Risk Level: {original_result['risk_level']}")
    print(f"      Confidence: {original_result['confidence']:.2f}")
    print(f"      Steps: {original_result['total_steps']}")
    print(f"      Time: {original_result['execution_time']:.3f}s")
    print(f"      Anomalies: {original_result['anomalies_count']}")
    print(f"      Reasoning: {original_result['reasoning_count']}")

    print(f"\n   LangGraph Implementation:")
    print(f"      Fraud: {langgraph_result['is_fraud']}")
    print(f"      Risk Score: {langgraph_result['risk_score']:.1f}")
    print(f"      Risk Level: {langgraph_result['risk_level']}")
    print(f"      Confidence: {langgraph_result['confidence']:.2f}")
    print(f"      Steps: {langgraph_result['total_steps']}")
    print(f"      Time: {langgraph_result['execution_time']:.3f}s")
    print(f"      Anomalies: {langgraph_result['anomalies_count']}")
    print(f"      Reasoning: {langgraph_result['reasoning_count']}")

    print(f"\n   Consistency Check:")
    print(f"      Fraud Detection Match: {'✅' if fraud_match else '❌'}")
    print(f"      Risk Score Difference: {risk_score_diff:.1f} ({'✅' if risk_consistent else '❌'})")

    # Overall pass/fail
    passed = fraud_match and risk_consistent

    if passed:
        print(f"\n✅ PASSED - Implementations are consistent")
    else:
        reasons = []
        if not fraud_match:
            reasons.append("Fraud detection mismatch")
        if not risk_consistent:
            reasons.append(f"Risk score difference too large ({risk_score_diff:.1f})")
        print(f"\n❌ FAILED - {', '.join(reasons)}")

    return {
        "passed": passed,
        "fraud_match": fraud_match,
        "risk_score_diff": risk_score_diff,
        "original": original_result,
        "langgraph": langgraph_result,
    }


async def run_all_tests():
    """Run all compatibility tests."""
    print("\n" + "=" * 80)
    print("🧪 LANGGRAPH AGENT COMPATIBILITY TESTING")
    print("=" * 80)
    print(f"Testing {len(TEST_TRANSACTIONS)} transactions...")
    print(f"Comparing: Original vs LangGraph implementations")

    results = []
    passed = 0
    failed = 0

    for transaction_data in TEST_TRANSACTIONS:
        result = await compare_implementations(transaction_data)
        results.append(
            {
                "name": transaction_data["name"],
                "result": result,
            }
        )

        if result["passed"]:
            passed += 1
        else:
            failed += 1

        # Small delay between tests
        await asyncio.sleep(0.5)

    # Print summary
    print("\n" + "=" * 80)
    print("📊 TEST SUMMARY")
    print("=" * 80)

    for test in results:
        status = "✅ PASS" if test["result"]["passed"] else "❌ FAIL"
        print(f"   {status} - {test['name']}")

    print(f"\n   Total: {len(results)} | Passed: {passed} | Failed: {failed}")

    if failed == 0:
        print("\n🎉 ALL TESTS PASSED - LangGraph implementation maintains API compatibility!")
        print("   Both implementations produce consistent fraud detection results.")
        print("\n   Next steps:")
        print("   1. Set USE_LANGGRAPH=true in .env.local to enable LangGraph")
        print("   2. Test with frontend integration")
        print("   3. Monitor performance and error rates")
        return 0
    else:
        print(
            f"\n⚠️  {failed} TEST(S) FAILED - Review implementation differences"
        )
        print("   LangGraph implementation may need adjustments for consistency.")
        return 1


# ============================================================================
# Main Execution
# ============================================================================

if __name__ == "__main__":
    print("\nStarting LangGraph compatibility tests...")
    print("This will compare original and LangGraph implementations side by side.\n")

    exit_code = asyncio.run(run_all_tests())

    print("\n" + "=" * 80)
    print("Testing complete!")
    print("=" * 80 + "\n")

    sys.exit(exit_code)
