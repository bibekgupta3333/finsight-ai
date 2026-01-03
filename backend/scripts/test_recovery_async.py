"""
Test script for Tool Recovery & Async Production Patterns.

Tests Section 3.7 (Tool & Failure Recovery) and Section 3.8 (Async & Production Patterns).
"""

import asyncio
import sys
import time
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, "/Users/bibekgupta/Documents/personal/bibek-portfolio/finsight-ai/backend")

from app.agents.tool_recovery import (
    ToolRecoveryManager,
    ToolHealth,
    FailureCategory,
    RecoveryStrategy,
    FallbackChain,
)
from app.core.async_patterns import (
    WorkerPool,
    WorkerPoolConfig,
    ConnectionPool,
    ConnectionPoolConfig,
    WebSocketManager,
    ResourceManager,
    TaskPriority,
)


def print_section(title: str):
    """Print section header."""
    print(f"\n{'=' * 80}")
    print(f"{title:^80}")
    print(f"{'=' * 80}\n")


# ============================================================================
# Section 3.7: Tool & Failure Recovery Tests
# ============================================================================


async def test_tool_health_checks():
    """Test tool health checking."""
    print_section("TEST 1: Tool Health Checks")

    recovery_manager = ToolRecoveryManager()

    # Healthy tool check
    async def healthy_check():
        await asyncio.sleep(0.1)
        return True

    health = await recovery_manager.check_tool_health("fraud_detector", healthy_check)

    print(f"Tool: {health.tool_name}")
    print(f"Status: {health.status}")
    print(f"Response Time: {health.response_time:.3f}s")
    print(f"Success Rate: {health.success_rate:.1%}")

    assert health.status == ToolHealth.HEALTHY, "Tool should be healthy"
    assert health.success_rate >= 0.95, "Success rate should be high"

    # Unhealthy tool check
    async def failing_check():
        raise Exception("Service unavailable")

    # Run multiple checks to degrade health
    for _ in range(5):
        health = await recovery_manager.check_tool_health("broken_tool", failing_check)

    print(f"\nFailed Tool: {health.tool_name}")
    print(f"Status: {health.status}")
    print(f"Recent Failures: {health.recent_failures}")
    print(f"Error: {health.error_message}")

    assert health.status != ToolHealth.HEALTHY, "Tool should not be healthy"

    print("\n✅ Tool health checks working correctly\n")


async def test_failure_root_cause_analysis():
    """Test root cause analysis."""
    print_section("TEST 2: Failure Root Cause Analysis")

    recovery_manager = ToolRecoveryManager()

    # Test timeout failure
    timeout_exc = Exception("Operation timeout after 30s")
    root_cause = recovery_manager.analyze_failure_root_cause(
        tool_name="slow_api",
        exception=timeout_exc,
        context={},
    )

    print("Timeout Failure Analysis:")
    print(f"Category: {root_cause.category}")
    print(f"Primary Cause: {root_cause.primary_cause}")
    print(f"Confidence: {root_cause.confidence:.1%}")
    print(f"Recommended Strategy: {root_cause.recommended_strategy}")

    assert root_cause.category == FailureCategory.TIMEOUT
    assert root_cause.recommended_strategy == RecoveryStrategy.FALLBACK

    # Test authentication failure
    auth_exc = Exception("403 Forbidden: Invalid API key")
    root_cause = recovery_manager.analyze_failure_root_cause(
        tool_name="external_api",
        exception=auth_exc,
        context={},
    )

    print(f"\nAuthentication Failure Analysis:")
    print(f"Category: {root_cause.category}")
    print(f"Primary Cause: {root_cause.primary_cause}")
    print(f"Recommended Strategy: {root_cause.recommended_strategy}")

    assert root_cause.category == FailureCategory.AUTHENTICATION
    assert root_cause.recommended_strategy == RecoveryStrategy.ESCALATE

    # Test rate limit failure
    rate_exc = Exception("429 Too Many Requests: Rate limit exceeded")
    root_cause = recovery_manager.analyze_failure_root_cause(
        tool_name="api_client",
        exception=rate_exc,
        context={},
    )

    print(f"\nRate Limit Failure Analysis:")
    print(f"Category: {root_cause.category}")
    print(f"Primary Cause: {root_cause.primary_cause}")
    print(f"Recommended Strategy: {root_cause.recommended_strategy}")

    assert root_cause.category == FailureCategory.RATE_LIMIT
    assert root_cause.recommended_strategy == RecoveryStrategy.CACHE

    print("\n✅ Root cause analysis working correctly\n")


async def test_fallback_chains():
    """Test fallback chain execution."""
    print_section("TEST 3: Fallback Chains")

    recovery_manager = ToolRecoveryManager()

    # Register fallback chain
    chain = FallbackChain(
        primary="primary_api",
        secondary="backup_api",
        tertiary="local_cache",
        cache_fallback=True,
    )
    recovery_manager.register_fallback_chain(chain)

    print(f"Registered fallback chain:")
    print(f"  Primary: {chain.primary}")
    print(f"  Secondary: {chain.secondary}")
    print(f"  Tertiary: {chain.tertiary}")
    print(f"  Cache Fallback: {chain.cache_fallback}")

    # Mock execution function
    call_count = {"primary_api": 0, "backup_api": 0, "local_cache": 0}

    async def execute_tool(tool_name: str, parameters: dict):
        call_count[tool_name] += 1

        if tool_name == "primary_api":
            raise Exception("Primary API timeout")
        elif tool_name == "backup_api":
            return {"source": "backup", "data": parameters}
        elif tool_name == "local_cache":
            return {"source": "cache", "data": parameters}

    # Execute with fallback
    success, result, tool_used = await recovery_manager.execute_with_fallback(
        tool_name="primary_api",
        parameters={"transaction_id": "tx_123"},
        execute_func=execute_tool,
    )

    print(f"\nFallback Execution:")
    print(f"  Success: {success}")
    print(f"  Tool Used: {tool_used}")
    print(f"  Result: {result}")
    print(f"  Calls Made: {call_count}")

    assert success, "Fallback should succeed"
    assert tool_used == "backup_api", "Should use backup API"
    assert call_count["primary_api"] == 1, "Should try primary once"
    assert call_count["backup_api"] == 1, "Should try backup once"

    print("\n✅ Fallback chains working correctly\n")


async def test_partial_result_aggregation():
    """Test partial result aggregation."""
    print_section("TEST 4: Partial Result Aggregation")

    recovery_manager = ToolRecoveryManager()

    # Test with 70% completion (usable)
    partial = recovery_manager.aggregate_partial_results(
        tool_name="batch_processor",
        completed_parts=["part1", "part2", "part3", "part4", "part5", "part6", "part7"],
        failed_parts=["part8", "part9", "part10"],
        total_parts=10,
    )

    print(f"Partial Result (70% complete):")
    print(f"  Tool: {partial.tool_name}")
    print(f"  Completion Rate: {partial.completion_rate:.1%}")
    print(f"  Usable: {partial.usable}")
    print(f"  Completed: {len(partial.completed_parts)}")
    print(f"  Failed: {len(partial.failed_parts)}")
    print(f"  Warnings: {partial.warnings}")

    assert partial.completion_rate == 0.7
    assert partial.usable, "70% should be usable"

    # Test with 30% completion (not usable)
    partial = recovery_manager.aggregate_partial_results(
        tool_name="batch_processor",
        completed_parts=["part1", "part2", "part3"],
        failed_parts=["part4", "part5", "part6", "part7", "part8", "part9", "part10"],
        total_parts=10,
    )

    print(f"\nPartial Result (30% complete):")
    print(f"  Completion Rate: {partial.completion_rate:.1%}")
    print(f"  Usable: {partial.usable}")

    assert partial.completion_rate == 0.3
    assert not partial.usable, "30% should not be usable"

    print("\n✅ Partial result aggregation working correctly\n")


async def test_incident_reporting():
    """Test incident creation and reporting."""
    print_section("TEST 5: Incident Reporting")

    recovery_manager = ToolRecoveryManager()

    # Create incidents with different severities
    incidents = []

    # Critical incident (authentication failure)
    auth_exc = Exception("401 Unauthorized")
    incident = recovery_manager.create_incident(
        tool_name="payment_api",
        exception=auth_exc,
        context={},
        recovery_attempted=True,
        recovery_successful=False,
    )
    incidents.append(incident)

    print(f"Incident 1: {incident.id}")
    print(f"  Severity: {incident.severity}")
    print(f"  Category: {incident.failure_category}")
    print(f"  Tool: {incident.tool_name}")

    assert incident.severity == "CRITICAL"

    # High severity incident (timeout)
    timeout_exc = Exception("timeout after 30s")
    incident = recovery_manager.create_incident(
        tool_name="fraud_detector",
        exception=timeout_exc,
        context={},
        recovery_attempted=True,
        recovery_successful=True,
    )
    incidents.append(incident)

    print(f"\nIncident 2: {incident.id}")
    print(f"  Severity: {incident.severity}")
    print(f"  Recovery Successful: {incident.recovery_successful}")

    assert incident.severity == "HIGH"
    assert incident.recovery_successful

    # Get recovery statistics
    stats = recovery_manager.get_recovery_statistics()

    print(f"\nRecovery Statistics:")
    print(f"  Total Incidents: {stats['total_incidents']}")
    print(f"  Recovery Attempted: {stats['recovery_attempted']}")
    print(f"  Recovery Successful: {stats['recovery_successful']}")
    print(f"  Recovery Rate: {stats['recovery_rate']:.1%}")
    print(f"  Category Breakdown: {stats['category_breakdown']}")

    assert stats["total_incidents"] == 2
    assert stats["recovery_rate"] == 0.5  # 1 out of 2 succeeded

    print("\n✅ Incident reporting working correctly\n")


# ============================================================================
# Section 3.8: Async & Production Patterns Tests
# ============================================================================


async def test_worker_pool():
    """Test worker pool with background tasks."""
    print_section("TEST 6: Worker Pool & Background Tasks")

    pool = WorkerPool(WorkerPoolConfig(max_workers=3, queue_size=50))
    await pool.start()

    # Submit tasks with different priorities
    async def sample_task(task_id: str, duration: float):
        await asyncio.sleep(duration)
        return f"Task {task_id} completed"

    task_ids = []

    # Critical task
    task_id = await pool.submit_task(
        "critical_fraud_analysis",
        sample_task,
        "critical_1",
        0.5,
        priority=TaskPriority.CRITICAL,
    )
    task_ids.append(task_id)

    # Normal tasks
    for i in range(5):
        task_id = await pool.submit_task(
            f"normal_task_{i}",
            sample_task,
            f"normal_{i}",
            1.0,
            priority=TaskPriority.NORMAL,
        )
        task_ids.append(task_id)

    # Low priority task
    task_id = await pool.submit_task(
        "low_priority_task",
        sample_task,
        "low_1",
        0.5,
        priority=TaskPriority.LOW,
    )
    task_ids.append(task_id)

    print(f"Submitted {len(task_ids)} tasks")

    # Get initial statistics
    stats = pool.get_statistics()
    print(f"\nInitial Stats:")
    print(f"  Workers: {stats['workers']}")
    print(f"  Queued Tasks: {stats['queued_tasks']}")
    print(f"  Queue by Priority: {stats['queue_by_priority']}")

    # Wait for tasks to complete
    await asyncio.sleep(3.0)

    # Get final statistics
    stats = pool.get_statistics()
    print(f"\nFinal Stats:")
    print(f"  Total Processed: {stats['total_processed']}")
    print(f"  Running Tasks: {stats['running_tasks']}")
    print(f"  Queued Tasks: {stats['queued_tasks']}")

    # Check task status
    task = await pool.get_task(task_ids[0])
    print(f"\nCritical Task Status:")
    print(f"  Name: {task.name}")
    print(f"  Status: {task.status}")
    print(f"  Priority: {task.priority}")
    print(f"  Progress: {task.progress:.1%}")

    assert stats["total_processed"] >= 3, "At least 3 tasks should complete"

    # Shutdown pool
    await pool.shutdown()

    print("\n✅ Worker pool working correctly\n")


async def test_connection_pool():
    """Test connection pooling."""
    print_section("TEST 7: Connection Pool")

    # Mock connection functions
    connection_count = {"created": 0, "closed": 0}

    async def create_connection():
        connection_count["created"] += 1
        return f"conn_{connection_count['created']}"

    async def close_connection(conn):
        connection_count["closed"] += 1

    pool = ConnectionPool(
        name="database",
        create_func=create_connection,
        close_func=close_connection,
        config=ConnectionPoolConfig(min_connections=2, max_connections=5),
    )

    # Acquire multiple connections
    connections = []
    for i in range(4):
        conn = await pool.acquire()
        connections.append(conn)
        print(f"Acquired connection: {conn}")

    stats = pool.get_statistics()
    print(f"\nPool Statistics (4 in use):")
    print(f"  Available: {stats['available']}")
    print(f"  In Use: {stats['in_use']}")
    print(f"  Total Created: {stats['total_created']}")

    assert stats["in_use"] == 4
    assert stats["total_created"] == 4

    # Release connections
    for conn in connections[:2]:
        await pool.release(conn)

    stats = pool.get_statistics()
    print(f"\nPool Statistics (2 released):")
    print(f"  Available: {stats['available']}")
    print(f"  In Use: {stats['in_use']}")

    assert stats["available"] == 2
    assert stats["in_use"] == 2

    # Close all connections
    await pool.close_all()

    stats = pool.get_statistics()
    print(f"\nPool Statistics (closed):")
    print(f"  Total Closed: {stats['total_closed']}")

    assert stats["total_closed"] >= 4

    print("\n✅ Connection pool working correctly\n")


async def test_websocket_manager():
    """Test WebSocket manager."""
    print_section("TEST 8: WebSocket Manager")

    manager = WebSocketManager()

    # Mock WebSocket
    class MockWebSocket:
        def __init__(self, client_id):
            self.client_id = client_id
            self.messages = []

        async def accept(self):
            pass

        async def send_json(self, data):
            self.messages.append(data)

    # Connect clients
    ws1 = MockWebSocket("client_1")
    ws2 = MockWebSocket("client_2")

    await manager.connect("client_1", ws1)
    await manager.connect("client_2", ws2)

    # Subscribe to topics
    await manager.subscribe("client_1", "fraud_alerts")
    await manager.subscribe("client_2", "fraud_alerts")
    await manager.subscribe("client_1", "system_status")

    stats = manager.get_statistics()
    print(f"WebSocket Statistics:")
    print(f"  Total Connections: {stats['total_connections']}")
    print(f"  Total Topics: {stats['total_topics']}")
    print(f"  Subscriptions: {stats['subscriptions_per_topic']}")

    assert stats["total_connections"] == 2
    assert stats["subscriptions_per_topic"]["fraud_alerts"] == 2

    # Broadcast to topic
    await manager.broadcast("fraud_alerts", {"alert": "High risk transaction detected"})

    print(f"\nClient 1 messages: {len(ws1.messages)}")
    print(f"Client 2 messages: {len(ws2.messages)}")

    assert len(ws1.messages) == 1
    assert len(ws2.messages) == 1

    # Send to specific client
    success = await manager.send_to_client("client_1", {"info": "Personal message"})

    print(f"\nDirect message sent: {success}")
    print(f"Client 1 total messages: {len(ws1.messages)}")

    assert success
    assert len(ws1.messages) == 2

    # Disconnect client
    manager.disconnect("client_1")

    stats = manager.get_statistics()
    print(f"\nAfter disconnect:")
    print(f"  Total Connections: {stats['total_connections']}")

    assert stats["total_connections"] == 1

    print("\n✅ WebSocket manager working correctly\n")


async def test_resource_manager():
    """Test resource management and cleanup."""
    print_section("TEST 9: Resource Manager")

    manager = ResourceManager()

    # Mock resources
    cleanup_called = {"count": 0}

    async def cleanup_resource(resource):
        cleanup_called["count"] += 1

    # Register resources
    for i in range(5):
        manager.register(
            resource_id=f"resource_{i}",
            resource={"id": i, "data": f"Resource {i}"},
            cleanup_func=cleanup_resource,
        )

    stats = manager.get_statistics()
    print(f"Initial Statistics:")
    print(f"  Total Resources: {stats['total_resources']}")
    print(f"  Idle Resources: {stats['idle_resources']}")

    assert stats["total_resources"] == 5

    # Simulate time passing
    await asyncio.sleep(0.5)

    # Cleanup specific resource
    cleaned = await manager.cleanup("resource_0")

    print(f"\nCleaned resource_0: {cleaned}")
    print(f"Cleanup calls: {cleanup_called['count']}")

    assert cleaned
    assert cleanup_called["count"] == 1

    # Touch a resource to mark it as active
    manager.touch("resource_1")

    # Cleanup idle resources (with very short timeout)
    cleaned_count = await manager.cleanup_idle(idle_timeout=0.1)

    print(f"\nCleaned idle resources: {cleaned_count}")
    print(f"Total cleanup calls: {cleanup_called['count']}")

    # At least some resources should be cleaned
    assert cleaned_count >= 1

    # Cleanup all remaining
    remaining = await manager.cleanup_all()

    stats = manager.get_statistics()
    print(f"\nFinal Statistics:")
    print(f"  Total Resources: {stats['total_resources']}")

    assert stats["total_resources"] == 0

    print("\n✅ Resource manager working correctly\n")


# ============================================================================
# Main Test Runner
# ============================================================================


async def main():
    """Run all tests."""
    print("\n" + "=" * 80)
    print("TESTING SECTIONS 3.7 & 3.8: Tool Recovery & Async Patterns")
    print("=" * 80)

    start_time = time.time()

    try:
        # Section 3.7 Tests
        await test_tool_health_checks()
        await test_failure_root_cause_analysis()
        await test_fallback_chains()
        await test_partial_result_aggregation()
        await test_incident_reporting()

        # Section 3.8 Tests
        await test_worker_pool()
        await test_connection_pool()
        await test_websocket_manager()
        await test_resource_manager()

        elapsed = time.time() - start_time

        print_section("ALL TESTS PASSED ✅")
        print(f"Total execution time: {elapsed:.2f}s")
        print(f"\nSummary:")
        print(f"  Section 3.7: Tool & Failure Recovery - 5/5 tests passing")
        print(f"  Section 3.8: Async & Production Patterns - 4/4 tests passing")
        print(f"  Total: 9/9 tests passing")

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
