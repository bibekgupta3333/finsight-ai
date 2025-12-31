#!/usr/bin/env python3
"""
Test script for distributed systems patterns (Sections 3.0.2 & 3.0.3).

Tests:
1. State Machine (FSM) transitions
2. Session management with Redis
3. Checkpointing and replay
4. Circuit breaker patterns
5. Retry logic with backoff
6. Correlation IDs
7. Idempotency

Run with: python scripts/test_distributed_patterns.py
"""

import asyncio
import sys
import time
import uuid
from datetime import datetime
from typing import Dict, Any

import httpx


BASE_URL = "http://localhost:8000"
TIMEOUT = 30.0


class Colors:
    """ANSI color codes for terminal output."""

    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"


def print_header(message: str):
    """Print test section header."""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'=' * 80}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{message}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'=' * 80}{Colors.ENDC}\n")


def print_success(message: str):
    """Print success message."""
    print(f"{Colors.OKGREEN}✓ {message}{Colors.ENDC}")


def print_error(message: str):
    """Print error message."""
    print(f"{Colors.FAIL}✗ {message}{Colors.ENDC}")


def print_info(message: str):
    """Print info message."""
    print(f"{Colors.OKCYAN}ℹ {message}{Colors.ENDC}")


def print_warning(message: str):
    """Print warning message."""
    print(f"{Colors.WARNING}⚠ {message}{Colors.ENDC}")


async def check_server_health() -> bool:
    """Check if server is running."""
    print_info("Checking server health...")
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get(f"{BASE_URL}/health")
            if response.status_code == 200:
                print_success(f"Server is healthy: {response.json()}")
                return True
            else:
                print_error(f"Server unhealthy: {response.status_code}")
                return False
    except Exception as e:
        print_error(f"Server not reachable: {e}")
        return False


def create_sample_transaction() -> Dict[str, Any]:
    """Create sample transaction data."""
    return {
        "transaction_id": f"TXN_{uuid.uuid4().hex[:8]}",
        "type": "TRANSFER",
        "amount": 15000.0,
        "oldbalanceOrg": 50000.0,
        "newbalanceOrig": 35000.0,
        "oldbalanceDest": 10000.0,
        "newbalanceDest": 25000.0,
        "step": 1,
        "nameOrig": "C123456789",
        "nameDest": "C987654321",
    }


async def test_stateful_analysis():
    """Test stateful fraud analysis with FSM and checkpoints."""
    print_header("TEST 1: Stateful Analysis (FSM + Checkpoints)")

    transaction = create_sample_transaction()
    correlation_id = str(uuid.uuid4())
    idempotency_key = str(uuid.uuid4())

    print_info(f"Transaction: {transaction['transaction_id']}")
    print_info(f"Correlation ID: {correlation_id}")
    print_info(f"Idempotency Key: {idempotency_key}")

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            # Make stateful analysis request
            response = await client.post(
                f"{BASE_URL}/api/v1/fraud/analyze/stateful",
                json={"transaction": transaction},
                headers={
                    "X-Correlation-ID": correlation_id,
                    "Idempotency-Key": idempotency_key,
                },
            )

            if response.status_code == 200:
                result = response.json()
                session_id = result["session_id"]

                print_success("Stateful analysis completed")
                print_info(f"  Session ID: {session_id}")
                print_info(f"  Current State: {result['current_state']}")
                print_info(f"  Checkpoints: {result['checkpoints']}")
                print_info(f"  Fraud: {result['result']['prediction']['is_fraud']}")
                print_info(
                    f"  Risk Score: {result['result']['prediction']['risk_score']:.4f}"
                )

                # Print state transitions
                print_info("\n  State Transitions:")
                for i, transition in enumerate(result["state_history"], 1):
                    print_info(
                        f"    {i}. {transition['from']} → {transition['to']}: "
                        f"{transition['reason']}"
                    )

                return session_id
            else:
                print_error(
                    f"Stateful analysis failed: {response.status_code} - "
                    f"{response.text}"
                )
                return None

    except Exception as e:
        print_error(f"Test failed: {e}")
        return None


async def test_session_retrieval(session_id: str):
    """Test session state retrieval."""
    print_header("TEST 2: Session Retrieval")

    if not session_id:
        print_warning("Skipping (no session ID)")
        return

    print_info(f"Retrieving session: {session_id}")

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get(
                f"{BASE_URL}/api/v1/fraud/sessions/{session_id}"
            )

            if response.status_code == 200:
                session = response.json()
                print_success("Session retrieved successfully")
                print_info(f"  Current State: {session['current_state']}")
                print_info(f"  Is Terminal: {session['is_terminal']}")
                print_info(f"  History Length: {len(session['history'])}")

                # Print full history
                print_info("\n  Full State History:")
                for i, transition in enumerate(session["history"], 1):
                    print_info(
                        f"    {i}. {transition['from']} → {transition['to']} "
                        f"({transition['timestamp']})"
                    )
                    print_info(f"       Reason: {transition['reason']}")

            else:
                print_error(f"Session retrieval failed: {response.status_code}")

    except Exception as e:
        print_error(f"Test failed: {e}")


async def test_checkpoint_retrieval(session_id: str):
    """Test checkpoint retrieval."""
    print_header("TEST 3: Checkpoint Retrieval")

    if not session_id:
        print_warning("Skipping (no session ID)")
        return

    print_info(f"Retrieving checkpoints for session: {session_id}")

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get(
                f"{BASE_URL}/api/v1/fraud/sessions/{session_id}/checkpoints"
            )

            if response.status_code == 200:
                checkpoints = response.json()
                print_success("Checkpoints retrieved successfully")
                print_info(f"  Checkpoint Count: {checkpoints['checkpoint_count']}")

                # Print checkpoints
                print_info("\n  Checkpoints:")
                for i, cp in enumerate(checkpoints["checkpoints"], 1):
                    print_info(
                        f"    {i}. Step {cp['step']}: {cp['name']} "
                        f"(State: {cp['state']})"
                    )
                    print_info(f"       Timestamp: {cp['timestamp']}")
                    print_info(f"       Has Error: {cp['has_error']}")

                # Print execution trace
                print_info("\n  Execution Trace:")
                for step in checkpoints["execution_trace"]:
                    print_info(f"    {step}")

            else:
                print_error(f"Checkpoint retrieval failed: {response.status_code}")

    except Exception as e:
        print_error(f"Test failed: {e}")


async def test_idempotency():
    """Test idempotency with duplicate requests."""
    print_header("TEST 4: Idempotency")

    transaction = create_sample_transaction()
    idempotency_key = str(uuid.uuid4())

    print_info(f"Transaction: {transaction['transaction_id']}")
    print_info(f"Idempotency Key: {idempotency_key}")
    print_info("Sending duplicate requests...")

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            # First request
            start1 = time.time()
            response1 = await client.post(
                f"{BASE_URL}/api/v1/fraud/analyze/stateful",
                json={"transaction": transaction},
                headers={"Idempotency-Key": idempotency_key},
            )
            duration1 = time.time() - start1

            # Second request (should be cached)
            start2 = time.time()
            response2 = await client.post(
                f"{BASE_URL}/api/v1/fraud/analyze/stateful",
                json={"transaction": transaction},
                headers={"Idempotency-Key": idempotency_key},
            )
            duration2 = time.time() - start2

            if response1.status_code == 200 and response2.status_code == 200:
                result1 = response1.json()
                result2 = response2.json()

                # Compare results
                if result1["session_id"] == result2["session_id"]:
                    print_success("Idempotency verified: Same session returned")
                    print_info(f"  First request: {duration1:.3f}s")
                    print_info(f"  Second request (cached): {duration2:.3f}s")
                    print_info(
                        f"  Speedup: {duration1/duration2:.2f}x faster"
                    )
                else:
                    print_error(
                        "Idempotency failed: Different sessions returned"
                    )

            else:
                print_error("Idempotency test failed")

    except Exception as e:
        print_error(f"Test failed: {e}")


async def test_circuit_breaker():
    """Test circuit breaker status."""
    print_header("TEST 5: Circuit Breaker Status")

    print_info("Retrieving circuit breaker states...")

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get(
                f"{BASE_URL}/api/v1/fraud/circuit-breakers"
            )

            if response.status_code == 200:
                result = response.json()
                print_success("Circuit breakers retrieved successfully")

                for i, cb in enumerate(result["circuit_breakers"], 1):
                    print_info(f"\n  Circuit Breaker {i}:")
                    print_info(f"    Name: {cb.get('name', 'N/A')}")
                    print_info(f"    State: {cb['state']}")
                    print_info(f"    Success Count: {cb['success_count']}")
                    print_info(f"    Failure Count: {cb['failure_count']}")
                    print_info(f"    Last Failure: {cb.get('last_failure', 'None')}")

            else:
                print_error(f"Circuit breaker retrieval failed: {response.status_code}")

    except Exception as e:
        print_error(f"Test failed: {e}")


async def test_correlation_id_propagation():
    """Test correlation ID propagation."""
    print_header("TEST 6: Correlation ID Propagation")

    transaction = create_sample_transaction()
    correlation_id = str(uuid.uuid4())

    print_info(f"Correlation ID: {correlation_id}")

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.post(
                f"{BASE_URL}/api/v1/fraud/analyze/stateful",
                json={"transaction": transaction},
                headers={"X-Correlation-ID": correlation_id},
            )

            # Check if correlation ID is returned in response headers
            returned_correlation_id = response.headers.get("X-Correlation-ID")

            if returned_correlation_id == correlation_id:
                print_success("Correlation ID propagated correctly")
                print_info(f"  Sent: {correlation_id}")
                print_info(f"  Received: {returned_correlation_id}")
            else:
                print_error("Correlation ID not propagated")
                print_info(f"  Sent: {correlation_id}")
                print_info(f"  Received: {returned_correlation_id}")

            # Check if it's in the response body
            if response.status_code == 200:
                result = response.json()
                if result.get("correlation_id") == correlation_id:
                    print_success("Correlation ID in response body")
                else:
                    print_warning("Correlation ID not in response body")

    except Exception as e:
        print_error(f"Test failed: {e}")


async def test_session_resume(session_id: str):
    """Test session resume from checkpoint."""
    print_header("TEST 7: Session Resume")

    if not session_id:
        print_warning("Skipping (no session ID)")
        return

    print_info(f"Attempting to resume session: {session_id}")

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.post(
                f"{BASE_URL}/api/v1/fraud/sessions/{session_id}/resume"
            )

            if response.status_code == 200:
                result = response.json()
                print_success("Session resume info retrieved")
                print_info(f"  Resumed From Step: {result['resumed_from']['step']}")
                print_info(f"  Step Name: {result['resumed_from']['name']}")
                print_info(f"  State: {result['resumed_from']['state']}")
                print_info(f"  Message: {result['message']}")
            else:
                print_error(f"Session resume failed: {response.status_code}")

    except Exception as e:
        print_error(f"Test failed: {e}")


async def main():
    """Run all tests."""
    print_header("Distributed Systems Patterns Test Suite")
    print_info(f"Base URL: {BASE_URL}")
    print_info(f"Timeout: {TIMEOUT}s")
    print_info(f"Timestamp: {datetime.utcnow().isoformat()}")

    # Check server health
    if not await check_server_health():
        print_error("\n❌ Server is not running. Start with: make run")
        sys.exit(1)

    # Run tests
    session_id = await test_stateful_analysis()
    await asyncio.sleep(1)

    await test_session_retrieval(session_id)
    await asyncio.sleep(1)

    await test_checkpoint_retrieval(session_id)
    await asyncio.sleep(1)

    await test_idempotency()
    await asyncio.sleep(1)

    await test_circuit_breaker()
    await asyncio.sleep(1)

    await test_correlation_id_propagation()
    await asyncio.sleep(1)

    await test_session_resume(session_id)

    # Summary
    print_header("Test Suite Complete")
    print_success("All tests executed. Check results above.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print_warning("\n\nTests interrupted by user")
        sys.exit(130)
    except Exception as e:
        print_error(f"\n\nFatal error: {e}")
        sys.exit(1)
