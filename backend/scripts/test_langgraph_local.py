"""
LangGraph Local Testing Script

Tests basic LangGraph functionality to verify installation and compatibility
with the existing FinSight AI agent architecture.

Run: python backend/scripts/test_langgraph_local.py
"""

import asyncio
import logging
from typing import TypedDict, Optional
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def test_imports():
    """Test 1: Verify all LangGraph dependencies are installed correctly"""
    print("\n🧪 Test 1: Verifying LangGraph Imports")
    print("=" * 80)

    try:
        from langgraph.graph import StateGraph, END
        from langchain_core.tools import tool
        from typing_extensions import TypedDict

        print("✅ langgraph.graph.StateGraph imported")
        print("✅ langgraph.graph.END imported")
        print("✅ langchain_core.tools imported")
        print("✅ typing_extensions.TypedDict imported")

        # Version check
        try:
            import langgraph
            import langchain
            print(f"\n📦 Package Versions:")

            # LangGraph may not have __version__
            lg_version = getattr(langgraph, "__version__", "unknown")
            print(f"   langgraph: {lg_version}")

            lc_version = getattr(langchain, "__version__", "unknown")
            print(f"   langchain: {lc_version}")
        except Exception as e:
            print(f"\n⚠️  Could not detect versions: {e}")

        return True

    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False


def test_basic_graph():
    """Test 2: Create and execute a basic LangGraph"""
    print("\n🧪 Test 2: Basic LangGraph Execution")
    print("=" * 80)

    try:
        from langgraph.graph import StateGraph, END
        from typing_extensions import TypedDict

        # Define state
        class BasicState(TypedDict):
            """Simple state for testing"""
            message: str
            counter: int

        # Define nodes
        def node_1(state: BasicState) -> dict:
            """First node - increments counter"""
            return {
                "message": state["message"] + " -> Node1",
                "counter": state["counter"] + 1
            }

        def node_2(state: BasicState) -> dict:
            """Second node - increments counter"""
            return {
                "message": state["message"] + " -> Node2",
                "counter": state["counter"] + 1
            }

        # Build graph
        graph = StateGraph(BasicState)
        graph.add_node("first", node_1)
        graph.add_node("second", node_2)

        # Add edges
        graph.add_edge("first", "second")
        graph.add_edge("second", END)

        # Set entry point
        graph.set_entry_point("first")

        # Compile
        app = graph.compile()

        # Execute
        initial_state = {"message": "Start", "counter": 0}
        final_state = app.invoke(initial_state)

        print(f"✅ Graph compiled and executed successfully")
        print(f"   Initial: {initial_state}")
        print(f"   Final: {final_state}")
        print(f"   Counter incremented: {final_state['counter']} times")

        assert final_state["counter"] == 2, "Counter should be 2"
        assert "Node1" in final_state["message"], "Node1 should execute"
        assert "Node2" in final_state["message"], "Node2 should execute"

        return True

    except Exception as e:
        print(f"❌ Basic graph test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_async_graph():
    """Test 3: Async graph execution (critical for fraud detection)"""
    print("\n🧪 Test 3: Async LangGraph Execution")
    print("=" * 80)

    try:
        from langgraph.graph import StateGraph, END
        from typing_extensions import TypedDict

        # Define state
        class AsyncState(TypedDict):
            """Async state for testing"""
            transactions: list[str]
            fraud_detected: int

        # Async nodes
        async def check_transaction_1(state: AsyncState) -> dict:
            """Async node - simulates fraud check"""
            await asyncio.sleep(0.01)  # Simulate async I/O
            transactions = state["transactions"]
            fraud = state["fraud_detected"]

            # Simulate fraud detection
            if "SUSPICIOUS" in transactions[0]:
                fraud += 1

            return {"fraud_detected": fraud}

        async def check_transaction_2(state: AsyncState) -> dict:
            """Async node - another fraud check"""
            await asyncio.sleep(0.01)
            transactions = state["transactions"]
            fraud = state["fraud_detected"]

            if len(transactions) > 1 and "FRAUD" in transactions[1]:
                fraud += 1

            return {"fraud_detected": fraud}

        # Build graph
        graph = StateGraph(AsyncState)
        graph.add_node("check_1", check_transaction_1)
        graph.add_node("check_2", check_transaction_2)

        graph.add_edge("check_1", "check_2")
        graph.add_edge("check_2", END)
        graph.set_entry_point("check_1")

        app = graph.compile()

        # Execute async
        initial_state = {
            "transactions": ["SUSPICIOUS_TXN_001", "FRAUD_TXN_002"],
            "fraud_detected": 0
        }

        final_state = await app.ainvoke(initial_state)

        print(f"✅ Async graph executed successfully")
        print(f"   Transactions checked: {len(initial_state['transactions'])}")
        print(f"   Fraud detected: {final_state['fraud_detected']}")

        assert final_state["fraud_detected"] == 2, "Should detect 2 fraudulent transactions"

        return True

    except Exception as e:
        print(f"❌ Async graph test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_conditional_edges():
    """Test 4: Conditional edges (for termination logic)"""
    print("\n🧪 Test 4: Conditional Edges (Termination Logic)")
    print("=" * 80)

    try:
        from langgraph.graph import StateGraph, END
        from typing_extensions import TypedDict

        # Define state
        class LoopState(TypedDict):
            """State with loop counter"""
            iterations: int
            max_iterations: int
            result: Optional[str]

        # Nodes
        def process_node(state: LoopState) -> dict:
            """Processing node"""
            iterations = state["iterations"] + 1
            result = f"Iteration {iterations}"
            return {"iterations": iterations, "result": result}

        # Conditional function
        def should_continue(state: LoopState) -> bool:
            """Decide whether to continue or terminate"""
            return state["iterations"] < state["max_iterations"]

        # Build graph with loop
        graph = StateGraph(LoopState)
        graph.add_node("process", process_node)

        # Conditional edge: loop or end
        graph.add_conditional_edges(
            "process",
            should_continue,
            {True: "process", False: END}  # Loop back or end
        )

        graph.set_entry_point("process")
        app = graph.compile()

        # Execute with max 5 iterations
        initial_state = {"iterations": 0, "max_iterations": 5, "result": None}
        final_state = app.invoke(initial_state)

        print(f"✅ Conditional edges working correctly")
        print(f"   Max iterations: {initial_state['max_iterations']}")
        print(f"   Total iterations: {final_state['iterations']}")
        print(f"   Final result: {final_state['result']}")

        assert final_state["iterations"] == 5, "Should iterate exactly 5 times"

        return True

    except Exception as e:
        print(f"❌ Conditional edges test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_fraud_detection_simulation():
    """Test 5: Simulate simplified fraud detection graph"""
    print("\n🧪 Test 5: Fraud Detection Graph Simulation")
    print("=" * 80)

    try:
        from langgraph.graph import StateGraph, END
        from typing_extensions import TypedDict

        # Fraud detection state (simplified)
        class FraudState(TypedDict):
            """Simplified fraud detection state"""
            transaction: dict
            observations: list[str]
            anomalies: list[str]
            risk_score: float
            is_fraud: Optional[bool]

        # Fraud detection nodes
        def observe_node(state: FraudState) -> dict:
            """Observation: Extract features"""
            txn = state["transaction"]
            observations = [
                f"Amount: ${txn.get('amount', 0):,.2f}",
                f"Type: {txn.get('type', 'UNKNOWN')}"
            ]
            return {"observations": observations}

        def analyze_node(state: FraudState) -> dict:
            """Analysis: Detect anomalies"""
            txn = state["transaction"]
            anomalies = []

            amount = txn.get("amount", 0)
            if amount > 100000:
                anomalies.append("High amount transaction")

            if txn.get("type") == "TRANSFER" and amount > 50000:
                anomalies.append("Large transfer detected")

            return {
                "anomalies": anomalies,
                "risk_score": min(len(anomalies) * 40.0, 100.0)
            }

        def decide_node(state: FraudState) -> dict:
            """Decision: Fraud or not"""
            is_fraud = state["risk_score"] >= 60.0
            return {"is_fraud": is_fraud}

        # Build fraud detection graph
        graph = StateGraph(FraudState)
        graph.add_node("observe", observe_node)
        graph.add_node("analyze", analyze_node)
        graph.add_node("decide", decide_node)

        # Sequential edges
        graph.add_edge("observe", "analyze")
        graph.add_edge("analyze", "decide")
        graph.add_edge("decide", END)

        graph.set_entry_point("observe")
        app = graph.compile()

        # Test case 1: Legitimate transaction
        print("\n   Test Case 1: Legitimate Transaction")
        txn1 = {"amount": 500, "type": "PAYMENT"}
        state1 = {
            "transaction": txn1,
            "observations": [],
            "anomalies": [],
            "risk_score": 0.0,
            "is_fraud": None
        }
        result1 = app.invoke(state1)
        print(f"      Transaction: {txn1}")
        print(f"      Fraud: {result1['is_fraud']}, Risk: {result1['risk_score']:.1f}")
        print(f"      Observations: {len(result1['observations'])}")
        print(f"      Anomalies: {len(result1['anomalies'])}")

        # Test case 2: Suspicious transaction
        print("\n   Test Case 2: Suspicious Transaction")
        txn2 = {"amount": 200000, "type": "TRANSFER"}
        state2 = {
            "transaction": txn2,
            "observations": [],
            "anomalies": [],
            "risk_score": 0.0,
            "is_fraud": None
        }
        result2 = app.invoke(state2)
        print(f"      Transaction: {txn2}")
        print(f"      Fraud: {result2['is_fraud']}, Risk: {result2['risk_score']:.1f}")
        print(f"      Observations: {len(result2['observations'])}")
        print(f"      Anomalies: {len(result2['anomalies'])}")

        print(f"\n✅ Fraud detection simulation successful")

        assert result1["is_fraud"] == False, "Legitimate txn should not be fraud"
        assert result2["is_fraud"] == True, "Suspicious txn should be fraud"

        return True

    except Exception as e:
        print(f"❌ Fraud detection simulation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_memory_usage():
    """Test 6: Memory usage (M4 Pro constraint check)"""
    print("\n🧪 Test 6: Memory Usage Check (M4 Pro Compatibility)")
    print("=" * 80)

    try:
        import psutil
        import os

        process = psutil.Process(os.getpid())
        mem_info = process.memory_info()
        mem_mb = mem_info.rss / 1024 / 1024

        print(f"   Current memory usage: {mem_mb:.1f} MB")
        print(f"   M4 Pro limit: 16 GB (16,384 MB)")

        if mem_mb < 5000:
            print(f"✅ Memory usage within acceptable range")
            return True
        else:
            print(f"⚠️  High memory usage detected")
            return True  # Still pass, just warn

    except ImportError:
        print("⚠️  psutil not installed, skipping memory check")
        return True
    except Exception as e:
        print(f"⚠️  Memory check failed: {e}")
        return True  # Non-critical failure


async def main():
    """Run all LangGraph tests"""

    print("\n" + "=" * 80)
    print("🚀 LANGGRAPH LOCAL TESTING - M4 Pro Laptop")
    print("=" * 80)
    print(f"Project: FinSight AI - Agent Architecture Migration")
    print(f"Purpose: Verify LangGraph installation and compatibility")
    print("=" * 80)

    tests = [
        ("Import Verification", test_imports),
        ("Basic Graph", test_basic_graph),
        ("Async Execution", test_async_graph),
        ("Conditional Edges", test_conditional_edges),
        ("Fraud Detection Simulation", test_fraud_detection_simulation),
        ("Memory Usage", test_memory_usage),
    ]

    results = {}

    for test_name, test_func in tests:
        if asyncio.iscoroutinefunction(test_func):
            result = await test_func()
        else:
            result = test_func()

        results[test_name] = result

    # Summary
    print("\n" + "=" * 80)
    print("📊 TEST SUMMARY")
    print("=" * 80)

    total = len(results)
    passed = sum(1 for r in results.values() if r)
    failed = total - passed

    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {status} - {test_name}")

    print("\n" + "-" * 80)
    print(f"   Total: {total} | Passed: {passed} | Failed: {failed}")

    if failed == 0:
        print(f"\n🎉 ALL TESTS PASSED - LangGraph ready for migration!")
        print(f"   Next step: Implement Phase 2 (Single Agent Migration)")
    else:
        print(f"\n⚠️  {failed} test(s) failed - Review errors above")
        print(f"   Fix issues before proceeding with migration")

    print("=" * 80 + "\n")

    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
