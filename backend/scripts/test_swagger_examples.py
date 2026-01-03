"""
Test script to validate all Swagger API examples.

This script tests all API endpoints with the prefilled Swagger examples
to ensure they work correctly with qwen3:0.6b model.
"""

import json
import time
from typing import Dict, Any

import requests

BASE_URL = "http://localhost:8000/api/v1"


def print_section(title: str):
    """Print a formatted section header."""
    print(f"\n{'=' * 80}")
    print(f"  {title}")
    print(f"{'=' * 80}\n")


def print_test(test_name: str, passed: bool, details: str = ""):
    """Print test result."""
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status}: {test_name}")
    if details:
        print(f"   {details}")


def test_health_check():
    """Test health check endpoint."""
    print_section("HEALTH CHECK")

    try:
        response = requests.get("http://localhost:8000/health")
        data = response.json()

        passed = (
            response.status_code == 200 and
            data["status"] == "healthy" and
            "queue_stats" in data
        )

        print_test(
            "Health Check",
            passed,
            f"Status: {data['status']}, Workers: {data['queue_stats']['active_workers']}"
        )
        return passed
    except Exception as e:
        print_test("Health Check", False, str(e))
        return False


def test_fraud_analysis():
    """Test fraud analysis endpoint with Swagger example."""
    print_section("FRAUD DETECTION API")

    # Test 1: Single Transaction Analysis
    payload = {
        "transaction": {
            "transaction_id": "TX_SUSPICIOUS_TRANSFER",
            "type": "TRANSFER",
            "amount": 195000.0,
            "oldbalanceOrg": 210000.0,
            "newbalanceOrig": 15000.0,
            "oldbalanceDest": 0.0,
            "newbalanceDest": 195000.0,
            "step": 156
        },
        "client_id": "test_client_001"
    }

    try:
        response = requests.post(f"{BASE_URL}/fraud/analyze", json=payload)
        data = response.json()

        passed = (
            response.status_code == 200 and
            "prediction" in data and
            "transaction_id" in data and
            data["transaction_id"] == "TX_SUSPICIOUS_TRANSFER"
        )

        if passed:
            pred = data["prediction"]
            print_test(
                "Single Transaction Analysis",
                True,
                f"Is Fraud: {pred['is_fraud']}, Confidence: {pred['confidence']:.2f}, "
                f"Risk Level: {pred['risk_level']}, Time: {data['processing_time_ms']:.2f}ms"
            )
        else:
            print_test("Single Transaction Analysis", False, str(data))

        return passed
    except Exception as e:
        print_test("Single Transaction Analysis", False, str(e))
        return False


def test_batch_analysis():
    """Test batch analysis endpoint with Swagger example."""
    payload = {
        "transactions": [
            {
                "transaction_id": "TX_BATCH_CASHOUT_001",
                "type": "CASH_OUT",
                "amount": 98000.0,
                "oldbalanceOrg": 105000.0,
                "newbalanceOrig": 7000.0,
                "oldbalanceDest": 0.0,
                "newbalanceDest": 0.0,
                "step": 48
            },
            {
                "transaction_id": "TX_BATCH_PAYMENT_002",
                "type": "PAYMENT",
                "amount": 2800.0,
                "oldbalanceOrg": 18000.0,
                "newbalanceOrig": 15200.0,
                "oldbalanceDest": 12000.0,
                "newbalanceDest": 14800.0,
                "step": 49
            },
            {
                "transaction_id": "TX_BATCH_TRANSFER_003",
                "type": "TRANSFER",
                "amount": 45000.0,
                "oldbalanceOrg": 80000.0,
                "newbalanceOrig": 35000.0,
                "oldbalanceDest": 15000.0,
                "newbalanceDest": 60000.0,
                "step": 50
            }
        ],
        "client_id": "batch_client_001"
    }

    try:
        response = requests.post(f"{BASE_URL}/fraud/analyze/batch", json=payload)
        data = response.json()

        passed = (
            response.status_code == 202 and
            "task_id" in data and
            data["status"] == "pending"
        )

        if passed:
            print_test(
                "Batch Transaction Submission",
                True,
                f"Task ID: {data['task_id']}, Status: {data['status']}, "
                f"ETA: {data.get('estimated_completion_seconds', 'N/A')}s"
            )

            # Wait and check task status
            task_id = data["task_id"]
            time.sleep(2)

            status_response = requests.get(f"{BASE_URL}/fraud/tasks/{task_id}")
            status_data = status_response.json()

            print_test(
                "Batch Task Status Check",
                status_response.status_code == 200,
                f"Status: {status_data['status']}"
            )
        else:
            print_test("Batch Transaction Submission", False, str(data))

        return passed
    except Exception as e:
        print_test("Batch Transaction Submission", False, str(e))
        return False


def test_llm_token_analysis():
    """Test LLM token analysis endpoint."""
    print_section("LLM ENGINEERING API - TOKEN ANALYSIS")

    try:
        params = {
            "prompt": "Analyze this high-value CASH_OUT transaction of $98,000 from an account with $105,000 balance"
        }
        response = requests.get(f"{BASE_URL}/llm/token-analysis", params=params)
        data = response.json()

        passed = (
            response.status_code == 200 and
            "token_count" in data and
            "max_tokens" in data and
            data["max_tokens"] == 32768  # Qwen3 context window
        )

        if passed:
            print_test(
                "Token Analysis",
                True,
                f"Tokens: {data['token_count']}, Max: {data['max_tokens']}, "
                f"Usage: {data['context_usage_percent']:.2f}%, Complexity: {data['complexity']}"
            )
        else:
            print_test("Token Analysis", False, str(data))

        return passed
    except Exception as e:
        print_test("Token Analysis", False, str(e))
        return False


def test_model_routing():
    """Test model routing endpoint with Swagger example."""
    print_section("LLM ENGINEERING API - MODEL ROUTING")

    payload = {
        "transaction_id": "TX_LLM_TEST_001",
        "type": "CASH_OUT",
        "amount": 175000.0,
        "oldbalanceOrg": 190000.0,
        "newbalanceOrig": 15000.0,
        "oldbalanceDest": 0.0,
        "newbalanceDest": 0.0
    }

    try:
        response = requests.post(f"{BASE_URL}/llm/model-routing", json=payload)
        data = response.json()

        passed = (
            response.status_code == 200 and
            "selected_model" in data and
            data["selected_model"] == "qwen3:0.6b"  # Verify correct model
        )

        if passed:
            print_test(
                "Model Routing",
                True,
                f"Model: {data['selected_model']}, Complexity: {data['complexity_score']}, "
                f"Est. Latency: {data['estimated_latency_ms']}ms, Streaming: {data['use_streaming']}"
            )
        else:
            print_test("Model Routing", False, str(data))

        return passed
    except Exception as e:
        print_test("Model Routing", False, str(e))
        return False


def test_sampling_deterministic():
    """Test sampling endpoint with deterministic mode."""
    print_section("LLM ENGINEERING API - SAMPLING")

    payload = {
        "transaction_id": "TX_LLM_TEST_001",
        "type": "TRANSFER",
        "amount": 85000.0,
        "oldbalanceOrg": 100000.0,
        "newbalanceOrig": 15000.0,
        "oldbalanceDest": 20000.0,
        "newbalanceDest": 105000.0
    }

    try:
        params = {
            "sampling_mode": "deterministic",
            "num_samples": 2
        }
        response = requests.post(
            f"{BASE_URL}/llm/test-sampling",
            json=payload,
            params=params
        )
        data = response.json()

        passed = (
            response.status_code == 200 and
            "samples" in data and
            len(data["samples"]) == 2 and
            "majority_vote" in data
        )

        if passed:
            print_test(
                "Deterministic Sampling",
                True,
                f"Samples: {len(data['samples'])}, "
                f"Majority Confidence: {data['majority_vote']['confidence']:.2f}, "
                f"Temperature: {data['sampling_config']['temperature']}"
            )

            # Check if samples are identical (deterministic)
            all_same = len(set(data["samples"])) == 1
            print_test(
                "Deterministic Consistency",
                all_same,
                "All samples identical (expected for deterministic mode)"
            )
        else:
            print_test("Deterministic Sampling", False, str(data))

        return passed
    except Exception as e:
        print_test("Deterministic Sampling", False, str(e))
        return False


def test_prompt_patterns():
    """Test advanced prompting patterns."""
    print_section("ADVANCED PROMPTING PATTERNS")

    # Correct payload structure matching FraudAnalysisRequest with proper field names
    payload = {
        "transaction": {
            "transaction_id": "TX_PATTERN_TEST",
            "type": "CASH_OUT",
            "amount": 120000.0,
            "oldbalanceOrg": 150000.0,
            "newbalanceOrig": 30000.0,
            "oldbalanceDest": 0.0,
            "newbalanceDest": 0.0
        }
    }

    patterns = [
        ("ReAct", "/fraud/analyze/react"),
        ("Chain-of-Thought", "/fraud/analyze/cot"),
        ("Tree-of-Thought", "/fraud/analyze/tot"),
    ]

    results = []
    for pattern_name, endpoint in patterns:
        try:
            response = requests.post(f"{BASE_URL}{endpoint}", json=payload)
            passed = response.status_code == 200

            if passed:
                data = response.json()
                print_test(
                    f"{pattern_name} Pattern",
                    True,
                    f"Pattern: {data.get('pattern', 'N/A')}"
                )
            else:
                print_test(f"{pattern_name} Pattern", False, f"Status: {response.status_code}")

            results.append(passed)
        except Exception as e:
            print_test(f"{pattern_name} Pattern", False, str(e))
            results.append(False)

    return all(results)


def test_circuit_breakers():
    """Test circuit breaker status endpoint."""
    print_section("RESILIENCE & MONITORING")

    try:
        response = requests.get(f"{BASE_URL}/fraud/circuit-breakers")
        data = response.json()

        passed = response.status_code == 200 and "circuit_breakers" in data

        if passed:
            print_test(
                "Circuit Breaker Status",
                True,
                f"Found {len(data['circuit_breakers'])} circuit breakers"
            )
        else:
            print_test("Circuit Breaker Status", False, str(data))

        return passed
    except Exception as e:
        print_test("Circuit Breaker Status", False, str(e))
        return False


def test_stats():
    """Test statistics endpoint."""
    try:
        response = requests.get(f"{BASE_URL}/fraud/stats")
        data = response.json()

        # Actual response has 'queue' and 'service' keys, not 'queue_stats'
        passed = response.status_code == 200 and "queue" in data and "service" in data

        if passed:
            queue_stats = data["queue"]
            service_stats = data["service"]
            print_test(
                "Service Statistics",
                True,
                f"Queue Size: {queue_stats.get('queue_size', 0)}, "
                f"Completed: {queue_stats.get('completed_tasks', 0)}, "
                f"Total Analyzed: {service_stats.get('total_analyzed', 0)}"
            )
        else:
            print_test("Service Statistics", False, str(data))

        return passed
    except Exception as e:
        print_test("Service Statistics", False, str(e))
        return False


def main():
    """Run all tests."""
    print("\n")
    print("█" * 80)
    print("  FINSIGHT AI - SWAGGER EXAMPLES VALIDATION")
    print("  Testing all API endpoints with prefilled examples")
    print("  LLM Model: qwen3:0.6b (Ollama)")
    print("█" * 80)

    results = {}

    # Test all endpoints
    results["Health Check"] = test_health_check()
    results["Fraud Analysis"] = test_fraud_analysis()
    results["Batch Analysis"] = test_batch_analysis()
    results["Token Analysis"] = test_llm_token_analysis()
    results["Model Routing"] = test_model_routing()
    results["Sampling"] = test_sampling_deterministic()
    results["Prompt Patterns"] = test_prompt_patterns()
    results["Circuit Breakers"] = test_circuit_breakers()
    results["Statistics"] = test_stats()

    # Summary
    print_section("TEST SUMMARY")

    passed_count = sum(1 for v in results.values() if v)
    total_count = len(results)
    pass_rate = (passed_count / total_count) * 100

    for test_name, passed in results.items():
        status = "✅" if passed else "❌"
        print(f"{status} {test_name}")

    print(f"\n{'=' * 80}")
    print(f"RESULTS: {passed_count}/{total_count} tests passed ({pass_rate:.1f}%)")
    print(f"{'=' * 80}\n")

    if pass_rate == 100:
        print("🎉 All Swagger examples are working correctly!")
        print("✅ Ready to use Swagger UI at: http://localhost:8000/docs")
    elif pass_rate >= 80:
        print("⚠️  Most Swagger examples are working. Check failures above.")
    else:
        print("❌ Multiple failures detected. Please review the errors above.")

    print()
    return pass_rate == 100


if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
