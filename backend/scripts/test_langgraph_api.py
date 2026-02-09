#!/usr/bin/env python3
"""
Test script for LangGraph API endpoints.

Tests all 6 LangGraph agent endpoints:
- /agents/langgraph/single
- /agents/langgraph/manager-worker
- /agents/langgraph/planner-executor-critic
- /agents/langgraph/debate
- /agents/langgraph/role-specialized
- /agents/langgraph/swarm

Usage:
    # Start backend server first:
    cd /Users/bibekgupta/Downloads/projects/finsight-ai
    pnpm backend:local

    # Then run tests:
    cd backend
    python scripts/test_langgraph_api.py
"""

import asyncio
import sys
import httpx
from typing import Dict, Any
from datetime import datetime


BASE_URL = "http://localhost:8000/api/v1/fraud"


# Test transaction data
TEST_TRANSACTION = {
    "transaction_id": "test_langgraph_api_001",
    "amount": 200000.0,
    "type": "TRANSFER",
    "oldbalanceOrg": 250000.0,
    "newbalanceOrig": 50000.0,
    "oldbalanceDest": 0.0,
    "newbalanceDest": 200000.0,
    "nameOrig": "C1234567890",
    "nameDest": "C9876543210",
}


async def test_endpoint(
    client: httpx.AsyncClient,
    endpoint: str,
    params: Dict[str, Any] = None,
) -> Dict[str, Any]:
    """Test a single endpoint."""
    print(f"\n{'='*80}")
    print(f"Testing: {endpoint}")
    print(f"{'='*80}")

    try:
        response = await client.post(
            f"{BASE_URL}{endpoint}",
            json=TEST_TRANSACTION,
            params=params or {},
            timeout=30.0,
        )

        if response.status_code == 200:
            data = response.json()
            print(f"✅ SUCCESS - Status: {response.status_code}")
            print(f"   Agent Type: {data.get('agent_type')}")
            print(f"   Fraud: {data.get('is_fraud')}")
            print(f"   Risk Score: {data.get('risk_score'):.1f}")
            print(f"   Confidence: {data.get('confidence'):.2f}")
            print(f"   Agreement: {data.get('agreement_level', 'N/A')}")
            if 'execution_time' in data:
                print(f"   Execution Time: {data['execution_time']:.3f}s")
            if 'total_time' in data:
                print(f"   Total Time: {data['total_time']:.3f}s")
            print(f"   Explanation: {data.get('explanation', 'N/A')[:80]}...")

            return {"status": "pass", "data": data}
        else:
            print(f"❌ FAIL - Status: {response.status_code}")
            print(f"   Error: {response.text}")
            return {"status": "fail", "error": response.text}

    except Exception as e:
        print(f"❌ ERROR - {type(e).__name__}: {e}")
        return {"status": "error", "error": str(e)}


async def run_all_tests():
    """Run all LangGraph API endpoint tests."""
    print("\n" + "="*80)
    print("🧪 LangGraph API Endpoint Test Suite")
    print("="*80)
    print(f"⏰ Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🌐 Base URL: {BASE_URL}")
    print(f"📋 Test Transaction: {TEST_TRANSACTION['transaction_id']}")

    start_time = datetime.now()

    # Test endpoints
    tests = [
        ("Single Agent", "/agents/langgraph/single", None),
        ("Manager-Worker", "/agents/langgraph/manager-worker", {"num_workers": 3}),
        ("Planner-Executor-Critic", "/agents/langgraph/planner-executor-critic", None),
        ("Debate", "/agents/langgraph/debate", None),
        ("Role-Specialized", "/agents/langgraph/role-specialized", None),
        ("Swarm (5 agents)", "/agents/langgraph/swarm", {"swarm_size": 5, "threshold": 0.6}),
    ]

    results = {}

    async with httpx.AsyncClient() as client:
        # Check if server is running by testing a simple endpoint
        try:
            test_response = await client.get(f"{BASE_URL}/../../health", timeout=5.0)
        except Exception:
            # Try alternative health check
            try:
                test_response = await client.get("http://localhost:8000/health", timeout=5.0)
            except Exception as e:
                print(f"\n❌ ERROR: Cannot connect to backend server")
                print(f"   {type(e).__name__}: {e}")
                print("   Start server with: pnpm backend:local")
                return False

        print("\n✅ Backend server is running")

        # Run tests
        for test_name, endpoint, params in tests:
            result = await test_endpoint(client, endpoint, params)
            results[test_name] = result

    # Print summary
    print("\n" + "="*80)
    print("📊 TEST SUMMARY")
    print("="*80)

    passed = sum(1 for r in results.values() if r["status"] == "pass")
    failed = sum(1 for r in results.values() if r["status"] == "fail")
    errors = sum(1 for r in results.values() if r["status"] == "error")
    total = len(results)

    for test_name, result in results.items():
        if result["status"] == "pass":
            print(f"   ✅ PASS - {test_name}")
        elif result["status"] == "fail":
            print(f"   ❌ FAIL - {test_name}")
        else:
            print(f"   ❌ ERROR - {test_name}")

    print(f"\n   Total: {total} | Passed: {passed} | Failed: {failed} | Errors: {errors}")

    if passed == total:
        print("\n🎉 ALL TESTS PASSED - LangGraph API endpoints working!")
    else:
        print(f"\n⚠️  {failed + errors} test(s) failed - review logs above")

    execution_time = (datetime.now() - start_time).total_seconds()
    print(f"\n⏱️  Total execution time: {execution_time:.2f}s")

    return passed == total


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
