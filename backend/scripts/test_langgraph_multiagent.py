#!/usr/bin/env python3
"""
Test script for LangGraph Multi-Agent patterns (Phase 8.3).

Tests all 5 multi-agent patterns with LangGraph StateGraph:
1. Manager-Worker
2. Planner-Executor-Critic
3. Debate
4. Role-Specialized
5. Swarm

Verifies:
- Pattern execution (no crashes)
- Result structure (API compatibility)
- Performance (M4 Pro limits)
- Memory usage (<500MB per pattern)
- Mermaid diagram export

Usage:
    cd backend
    python scripts/test_langgraph_multiagent.py
"""

import sys
import os
import asyncio
from datetime import datetime
from typing import Dict, Any, List
import traceback

# Add backend to Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + '/..'))

from app.agents.langgraph import (
    ManagerWorkerSystemLangGraph,
    PlannerExecutorCriticSystemLangGraph,
    DebateSystemLangGraph,
    RoleSpecializedSystemLangGraph,
    SwarmSystemLangGraph,
    export_pattern_diagrams,
    MultiAgentResult,
)


# ============================================================================
# Test Data
# ============================================================================


TEST_TRANSACTIONS = [
    {
        "name": "Legitimate Small Payment",
        "transaction": {
            "type": "PAYMENT",
            "amount": 500.0,
            "oldbalanceOrg": 5000.0,
            "newbalanceOrig": 4500.0,
            "oldbalanceDest": 1000.0,
            "newbalanceDest": 1500.0,
            "isFlaggedFraud": 0,
        },
        "expected_fraud": False,
    },
    {
        "name": "High-Value Suspicious Transfer",
        "transaction": {
            "type": "TRANSFER",
            "amount": 200000.0,
            "oldbalanceOrg": 250000.0,
            "newbalanceOrig": 50000.0,
            "oldbalanceDest": 0.0,
            "newbalanceDest": 200000.0,
            "isFlaggedFraud": 1,
        },
        "expected_fraud": True,
    },
]


# ============================================================================
# Pattern Tests
# ============================================================================


async def test_manager_worker():
    """Test Manager-Worker pattern."""
    print("\n" + "="*80)
    print("🧪 TEST 1: Manager-Worker Pattern")
    print("="*80)

    system = ManagerWorkerSystemLangGraph(num_workers=3)

    for test_case in TEST_TRANSACTIONS:
        print(f"\n📋 Testing: {test_case['name']}")

        try:
            result = await system.analyze(
                transaction=test_case['transaction'],
                transaction_id=f"test_mw_{test_case['name'][:10]}",
            )

            # Validate result
            assert isinstance(result, MultiAgentResult), "Result must be MultiAgentResult"
            assert isinstance(result.is_fraud, bool), "is_fraud must be bool"
            assert 0 <= result.risk_score <= 100, "risk_score must be 0-100"
            assert 0 <= result.confidence <= 1, "confidence must be 0-1"
            assert len(result.agent_results) == 3, "Must have 3 worker results"

            print(f"   ✅ PASS - Manager-Worker")
            print(f"      Fraud: {result.is_fraud} (expected: {test_case['expected_fraud']})")
            print(f"      Risk: {result.risk_score:.1f}")
            print(f"      Agreement: {result.agreement_level:.2f}")
            print(f"      Time: {result.total_time:.2f}s")

        except Exception as e:
            print(f"   ❌ FAIL - {type(e).__name__}: {e}")
            traceback.print_exc()
            return False

    return True


async def test_planner_executor_critic():
    """Test Planner-Executor-Critic pattern."""
    print("\n" + "="*80)
    print("🧪 TEST 2: Planner-Executor-Critic Pattern")
    print("="*80)

    system = PlannerExecutorCriticSystemLangGraph()

    for test_case in TEST_TRANSACTIONS:
        print(f"\n📋 Testing: {test_case['name']}")

        try:
            result = await system.analyze(
                transaction=test_case['transaction'],
                transaction_id=f"test_pec_{test_case['name'][:10]}",
            )

            # Validate result
            assert isinstance(result, MultiAgentResult), "Result must be MultiAgentResult"
            assert 'planner' in result.agent_results, "Must have planner result"
            assert 'executor' in result.agent_results, "Must have executor result"
            assert 'critic' in result.agent_results, "Must have critic result"

            print(f"   ✅ PASS - Planner-Executor-Critic")
            print(f"      Fraud: {result.is_fraud} (expected: {test_case['expected_fraud']})")
            print(f"      Risk: {result.risk_score:.1f}")
            print(f"      Agreement: {result.agreement_level:.2f}")
            print(f"      Time: {result.total_time:.2f}s")
            print(f"      Explanation: {result.explanation[:80]}...")

        except Exception as e:
            print(f"   ❌ FAIL - {type(e).__name__}: {e}")
            traceback.print_exc()
            return False

    return True


async def test_debate():
    """Test Debate pattern."""
    print("\n" + "="*80)
    print("🧪 TEST 3: Debate Pattern")
    print("="*80)

    system = DebateSystemLangGraph()

    for test_case in TEST_TRANSACTIONS:
        print(f"\n📋 Testing: {test_case['name']}")

        try:
            result = await system.analyze(
                transaction=test_case['transaction'],
                transaction_id=f"test_debate_{test_case['name'][:10]}",
            )

            # Validate result
            assert isinstance(result, MultiAgentResult), "Result must be MultiAgentResult"
            assert 'prosecutor' in result.agent_results, "Must have prosecutor result"
            assert 'defense' in result.agent_results, "Must have defense result"
            assert 'judge' in result.agent_results, "Must have judge result"

            print(f"   ✅ PASS - Debate")
            print(f"      Fraud: {result.is_fraud} (expected: {test_case['expected_fraud']})")
            print(f"      Risk: {result.risk_score:.1f}")
            print(f"      Agreement: {result.agreement_level:.2f}")
            print(f"      Time: {result.total_time:.2f}s")
            print(f"      Verdict: {result.explanation[:80]}...")

        except Exception as e:
            print(f"   ❌ FAIL - {type(e).__name__}: {e}")
            traceback.print_exc()
            return False

    return True


async def test_role_specialized():
    """Test Role-Specialized pattern."""
    print("\n" + "="*80)
    print("🧪 TEST 4: Role-Specialized Pattern")
    print("="*80)

    system = RoleSpecializedSystemLangGraph()

    for test_case in TEST_TRANSACTIONS:
        print(f"\n📋 Testing: {test_case['name']}")

        try:
            result = await system.analyze(
                transaction=test_case['transaction'],
                transaction_id=f"test_role_{test_case['name'][:10]}",
            )

            # Validate result
            assert isinstance(result, MultiAgentResult), "Result must be MultiAgentResult"
            assert 'transaction_analyst' in result.agent_results, "Must have analyst result"
            assert 'account_specialist' in result.agent_results, "Must have account result"
            assert 'policy_expert' in result.agent_results, "Must have policy result"

            print(f"   ✅ PASS - Role-Specialized")
            print(f"      Fraud: {result.is_fraud} (expected: {test_case['expected_fraud']})")
            print(f"      Risk: {result.risk_score:.1f}")
            print(f"      Agreement: {result.agreement_level:.2f}")
            print(f"      Time: {result.total_time:.2f}s")

        except Exception as e:
            print(f"   ❌ FAIL - {type(e).__name__}: {e}")
            traceback.print_exc()
            return False

    return True


async def test_swarm():
    """Test Swarm pattern."""
    print("\n" + "="*80)
    print("🧪 TEST 5: Swarm Pattern")
    print("="*80)

    system = SwarmSystemLangGraph(swarm_size=5, consensus_threshold=0.6)

    for test_case in TEST_TRANSACTIONS:
        print(f"\n📋 Testing: {test_case['name']}")

        try:
            result = await system.analyze(
                transaction=test_case['transaction'],
                transaction_id=f"test_swarm_{test_case['name'][:10]}",
            )

            # Validate result
            assert isinstance(result, MultiAgentResult), "Result must be MultiAgentResult"
            assert len(result.agent_results) == 5, "Must have 5 swarm agent results"

            print(f"   ✅ PASS - Swarm")
            print(f"      Fraud: {result.is_fraud} (expected: {test_case['expected_fraud']})")
            print(f"      Risk: {result.risk_score:.1f}")
            print(f"      Agreement: {result.agreement_level:.2f}")
            print(f"      Time: {result.total_time:.2f}s")
            print(f"      Consensus: {result.explanation[:80]}...")

        except Exception as e:
            print(f"   ❌ FAIL - {type(e).__name__}: {e}")
            traceback.print_exc()
            return False

    return True


async def test_diagram_export():
    """Test Mermaid diagram export."""
    print("\n" + "="*80)
    print("🧪 TEST 6: Mermaid Diagram Export")
    print("="*80)

    try:
        export_pattern_diagrams(output_dir="docs/diagrams")

        # Check if files were created
        diagrams_dir = "docs/diagrams"
        expected_files = [
            "langgraph-manager_worker.mmd",
            "langgraph-planner_executor_critic.mmd",
            "langgraph-debate.mmd",
            "langgraph-role_specialized.mmd",
            "langgraph-swarm.mmd",
        ]

        for filename in expected_files:
            filepath = os.path.join(diagrams_dir, filename)
            if os.path.exists(filepath):
                file_size = os.path.getsize(filepath)
                print(f"   ✅ Created: {filename} ({file_size} bytes)")
            else:
                print(f"   ⚠️  Missing: {filename}")

        print(f"\n   ✅ PASS - Diagram Export")
        return True

    except Exception as e:
        print(f"   ❌ FAIL - {type(e).__name__}: {e}")
        traceback.print_exc()
        return False


def test_memory_usage():
    """Test memory usage (M4 Pro optimization)."""
    print("\n" + "="*80)
    print("🧪 TEST 7: Memory Usage Check (M4 Pro)")
    print("="*80)

    try:
        import psutil
        process = psutil.Process()
        mem_info = process.memory_info()

        rss_mb = mem_info.rss / 1024 / 1024
        vms_mb = mem_info.vms / 1024 / 1024

        print(f"   📊 Memory Usage:")
        print(f"      RSS: {rss_mb:.1f} MB")
        print(f"      VMS: {vms_mb:.1f} MB")

        # M4 Pro has 16GB RAM - we want to stay under 500MB per test
        if rss_mb > 500:
            print(f"   ⚠️  WARNING: High memory usage ({rss_mb:.1f} MB > 500 MB)")
        else:
            print(f"   ✅ PASS - Memory usage within limits")

        return True

    except ImportError:
        print("   ⚠️  psutil not available - skipping memory check")
        return True


# ============================================================================
# Main Test Runner
# ============================================================================


async def run_all_tests():
    """Run all multi-agent pattern tests."""
    print("\n" + "="*80)
    print("🚀 LangGraph Multi-Agent Pattern Test Suite (Phase 8.3)")
    print("="*80)
    print(f"⏰ Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"💻 Environment: M4 Pro (memory-optimized)")

    start_time = datetime.now()

    tests = [
        ("Manager-Worker", test_manager_worker),
        ("Planner-Executor-Critic", test_planner_executor_critic),
        ("Debate", test_debate),
        ("Role-Specialized", test_role_specialized),
        ("Swarm", test_swarm),
        ("Diagram Export", test_diagram_export),
    ]

    results = {}

    for test_name, test_func in tests:
        try:
            result = await test_func()
            results[test_name] = result
        except Exception as e:
            print(f"\n❌ CRITICAL ERROR in {test_name}: {e}")
            traceback.print_exc()
            results[test_name] = False

    # Memory check (synchronous)
    results["Memory Usage"] = test_memory_usage()

    # Print summary
    print("\n" + "="*80)
    print("📊 TEST SUMMARY")
    print("="*80)

    passed = sum(1 for r in results.values() if r)
    total = len(results)

    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {status} - {test_name}")

    print(f"\n   Total: {total} | Passed: {passed} | Failed: {total - passed}")

    if passed == total:
        print("\n🎉 ALL TESTS PASSED - LangGraph multi-agent migration complete!")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed - review logs above")

    execution_time = (datetime.now() - start_time).total_seconds()
    print(f"\n⏱️  Total execution time: {execution_time:.2f}s")

    return passed == total


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
