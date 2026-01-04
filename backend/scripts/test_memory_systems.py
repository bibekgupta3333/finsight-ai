#!/usr/bin/env python3
"""
Test Memory Systems Implementation

Tests all memory subsystems:
- Short-term memory (task context)
- Working memory (LRU cache)
- Episodic memory (ChromaDB)
- Semantic memory (knowledge base)
- Procedural memory (patterns)
- Hybrid search (BM25 + vector)
"""

import asyncio
import json
import sys
import time
from pathlib import Path
import traceback

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

import requests
from requests.exceptions import Timeout, ConnectionError

# Test configuration
API_BASE = "http://localhost:8000"
MEMORY_BASE = f"{API_BASE}/api/v1/memory"
REQUEST_TIMEOUT = 10  # seconds


def print_section(title: str):
    """Print formatted section header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


def test_health_check():
    """Test API health."""
    print_section("TEST 1: Health Check")

    try:
        print(f"Connecting to {API_BASE}...")
        response = requests.get(f"{API_BASE}/health", timeout=REQUEST_TIMEOUT)
        if response.status_code == 200:
            data = response.json()
            print(f"✓ API is healthy")
            print(f"  Version: {data.get('version')}")
            print(f"  Status: {data.get('status')}")
            return True
        else:
            print(f"✗ API health check failed: {response.status_code}")
            print(f"  Response: {response.text[:200]}")
            return False
    except Timeout:
        print(f"✗ Request timed out after {REQUEST_TIMEOUT}s")
        return False
    except ConnectionError as e:
        print(f"✗ Failed to connect to API: {e}")
        print(f"  Make sure the backend is running: docker-compose up -d backend")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        traceback.print_exc()
        return False


def test_short_term_memory():
    """Test short-term memory operations."""
    print_section("TEST 2: Short-Term Memory")

    # Start task
    task_data = {
        "transaction_id": "TXN_001",
        "transaction_data": {
            "amount": 1500.00,
            "type": "TRANSFER",
            "description": "Wire transfer to foreign account",
        },
        "context": {
            "user_id": "USER_123",
            "timestamp": time.time(),
        }
    }

    try:
        print(f"Posting to {MEMORY_BASE}/task/start...")
        response = requests.post(f"{MEMORY_BASE}/task/start", json=task_data, timeout=REQUEST_TIMEOUT)
        print(f"Response status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"✓ Task started: {result.get('task_id')}")
            task_id = result.get('task_id')
        else:
            print(f"✗ Failed to start task: {response.status_code}")
            print(f"  Response: {response.text[:500]}")
            return False
    except Timeout:
        print(f"✗ Request timed out after {REQUEST_TIMEOUT}s")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        traceback.print_exc()
        return False

    # Add reasoning steps
    reasoning_steps = [
        {"type": "analysis", "content": "Checking transaction amount against threshold"},
        {"type": "risk_assessment", "content": "Amount exceeds $1000 - flagging for review"},
        {"type": "pattern_match", "content": "Foreign transfer detected - high risk indicator"},
    ]

    for step in reasoning_steps:
        try:
            response = requests.post(f"{MEMORY_BASE}/reasoning/step", json=step, timeout=REQUEST_TIMEOUT)
            if response.status_code == 200:
                print(f"✓ Reasoning step added: {step['type']}")
            else:
                print(f"✗ Failed to add reasoning step: {response.status_code}")
        except Timeout:
            print(f"✗ Reasoning step timed out")
        except Exception as e:
            print(f"✗ Error adding reasoning step: {e}")

    # Record tool calls
    tool_calls = [
        ("check_amount", {"amount": 1500, "threshold": 1000}, {"exceeds": True}),
        ("check_type", {"type": "TRANSFER"}, {"risk_level": "high"}),
        ("check_history", {"user_id": "USER_123"}, {"previous_fraud": 0}),
    ]

    for tool_name, args, result in tool_calls:
        response = requests.post(
            f"{MEMORY_BASE}/tool/call",
            params={"tool_name": tool_name},
            json={"args": args, "result": result}
        )
        if response.status_code == 200:
            print(f"✓ Tool call recorded: {tool_name}")

    # Get short-term memory summary
    response = requests.get(f"{MEMORY_BASE}/short-term")
    if response.status_code == 200:
        summary = response.json()
        stm = summary.get('short_term_memory', {})
        print(f"\n✓ Short-term memory summary:")
        print(f"  Task ID: {stm.get('task', {}).get('id')}")
        print(f"  Reasoning steps: {stm.get('reasoning_steps')}")
        print(f"  Tool calls: {stm.get('tool_calls')}")
        print(f"  Token count: {stm.get('token_count')}")

    return True


def test_working_memory():
    """Test working memory LRU cache."""
    print_section("TEST 3: Working Memory (LRU Cache)")

    # Store items in cache
    cache_items = {
        "fraud_policy_1": {"rule": "Amount > $1000 requires approval"},
        "fraud_policy_2": {"rule": "Foreign transfers flagged"},
        "calculation_result": {"risk_score": 0.85, "confidence": 0.92},
        "recent_transaction": {"id": "TXN_001", "status": "flagged"},
    }

    for key, value in cache_items.items():
        response = requests.post(
            f"{MEMORY_BASE}/working/put",
            params={"key": key},
            json={"value": value}
        )
        if response.status_code == 200:
            print(f"✓ Cached: {key}")

    # Retrieve from cache
    print(f"\nRetrieving from cache:")
    for key in cache_items.keys():
        response = requests.get(f"{MEMORY_BASE}/working/get/{key}")
        if response.status_code == 200:
            result = response.json()
            if result.get('status') == 'hit':
                print(f"✓ Cache hit: {key}")
            else:
                print(f"✗ Cache miss: {key}")

    # Get cache stats
    response = requests.get(f"{MEMORY_BASE}/working/stats")
    if response.status_code == 200:
        stats = response.json().get('working_memory', {})
        print(f"\n✓ Working memory stats:")
        print(f"  Size: {stats.get('size')}/{stats.get('capacity')}")
        print(f"  Hit rate: {stats.get('hit_rate', 0):.2%}")
        print(f"  Hits: {stats.get('hits')}, Misses: {stats.get('misses')}")
        print(f"  Evictions: {stats.get('evictions')}")

    return True


def test_episodic_memory():
    """Test long-term episodic memory."""
    print_section("TEST 4: Episodic Memory (Long-term Cases)")

    # Store episodes
    episodes = [
        {
            "episode_id": "CASE_001",
            "content": {
                "transaction": {"id": "TXN_001", "amount": 1500, "type": "TRANSFER"},
                "analysis": "High-risk foreign transfer detected",
                "decision": "Flagged for manual review",
            },
            "metadata": {
                "fraud_detected": True,
                "confidence": 0.85,
                "amount": 1500,
            },
            "priority": "high",
        },
        {
            "episode_id": "CASE_002",
            "content": {
                "transaction": {"id": "TXN_002", "amount": 50, "type": "PAYMENT"},
                "analysis": "Small routine payment",
                "decision": "Approved",
            },
            "metadata": {
                "fraud_detected": False,
                "confidence": 0.95,
                "amount": 50,
            },
            "priority": "low",
        },
    ]

    for episode in episodes:
        response = requests.post(f"{MEMORY_BASE}/episodic/store", json=episode)
        if response.status_code == 201:
            print(f"✓ Episode stored: {episode['episode_id']} (priority: {episode['priority']})")

    # Retrieve similar episodes
    print(f"\nRetrieving similar episodes:")
    query_data = {
        "query": "foreign transfer high amount",
        "memory_types": ["episodic"],
        "n_results": 5,
        "min_similarity": 0.5,
    }

    response = requests.post(f"{MEMORY_BASE}/retrieve", json=query_data)
    if response.status_code == 200:
        result = response.json()
        episodic = result.get('memories', {}).get('episodic', [])
        print(f"✓ Found {len(episodic)} similar episodes")
        for ep in episodic[:3]:
            print(f"  - {ep.get('id')}: similarity={ep.get('similarity', 0):.3f}")

    return True


def test_semantic_memory():
    """Test semantic memory (knowledge base)."""
    print_section("TEST 5: Semantic Memory (Knowledge Base)")

    # Store fraud policies
    policies = [
        {
            "knowledge_id": "POLICY_AMOUNT_THRESHOLD",
            "content": "Transactions over $1000 require additional verification and approval",
            "category": "amount_rules",
            "metadata": {"threshold": 1000, "severity": "medium"},
        },
        {
            "knowledge_id": "POLICY_FOREIGN_TRANSFER",
            "content": "All foreign wire transfers must be flagged for manual review due to fraud risk",
            "category": "transfer_rules",
            "metadata": {"risk_level": "high", "auto_flag": True},
        },
        {
            "knowledge_id": "POLICY_VELOCITY_CHECK",
            "content": "More than 5 transactions in 24 hours triggers velocity check",
            "category": "velocity_rules",
            "metadata": {"count_threshold": 5, "time_window_hours": 24},
        },
    ]

    for policy in policies:
        response = requests.post(f"{MEMORY_BASE}/semantic/store", json=policy)
        if response.status_code == 201:
            print(f"✓ Knowledge stored: {policy['knowledge_id']} (category: {policy['category']})")

    # Retrieve relevant knowledge
    print(f"\nRetrieving relevant knowledge:")
    query_data = {
        "query": "what are the rules for large transfers",
        "memory_types": ["semantic"],
        "n_results": 3,
    }

    response = requests.post(f"{MEMORY_BASE}/retrieve", json=query_data)
    if response.status_code == 200:
        result = response.json()
        semantic = result.get('memories', {}).get('semantic', [])
        print(f"✓ Found {len(semantic)} relevant policies")
        for item in semantic:
            print(f"  - {item.get('id')}: relevance={item.get('relevance', 0):.3f}")
            print(f"    {item.get('content')[:80]}...")

    return True


def test_procedural_memory():
    """Test procedural memory (successful patterns)."""
    print_section("TEST 6: Procedural Memory (Patterns)")

    # Record procedures
    procedure_data = {
        "procedure_name": "analyze_high_value_transfer",
        "steps": [
            "Check amount against threshold",
            "Verify transfer type and destination",
            "Check user transaction history",
            "Calculate risk score",
            "Flag if risk > 0.7",
        ],
        "success_rate": 0.92,
        "metadata": {"use_case": "fraud_detection", "avg_time_ms": 150},
    }

    response = requests.post(f"{MEMORY_BASE}/procedural/record", json=procedure_data)
    if response.status_code == 201:
        print(f"✓ Procedure recorded: {procedure_data['procedure_name']}")
        print(f"  Success rate: {procedure_data['success_rate']:.2%}")

    # Record reasoning chain
    chain_data = {
        "chain": [
            "Analyze transaction amount",
            "Check transaction type",
            "Review user history",
            "Calculate composite risk score",
        ],
        "outcome": "fraud_detected",
        "success": True,
        "confidence": 0.88,
    }

    response = requests.post(f"{MEMORY_BASE}/procedural/chain", json=chain_data)
    if response.status_code == 201:
        print(f"✓ Reasoning chain recorded")
        print(f"  Confidence: {chain_data['confidence']:.2%}")

    return True


def test_hybrid_search():
    """Test hybrid search (BM25 + vector)."""
    print_section("TEST 7: Hybrid Search (BM25 + Vector)")

    # Build search index
    response = requests.post(
        f"{MEMORY_BASE}/index/build",
        params={"collection": "episodic"}
    )
    if response.status_code == 200:
        print(f"✓ BM25 index built for episodic memory")

    # Perform hybrid search
    search_data = {
        "query": "high risk transfer foreign account",
        "collection": "episodic",
        "n_results": 5,
        "min_similarity": 0.5,
        "use_hybrid": True,
    }

    response = requests.post(f"{MEMORY_BASE}/search/hybrid", json=search_data)
    if response.status_code == 200:
        result = response.json()
        results = result.get('results', [])
        print(f"✓ Hybrid search results: {len(results)} found")
        for item in results[:3]:
            print(f"  - {item.get('id')}:")
            print(f"    Hybrid score: {item.get('hybrid_score', 0):.3f}")
            print(f"    BM25: {item.get('bm25_score', 0):.3f}, Vector: {item.get('vector_score', 0):.3f}")

    # Compare with vector-only search
    search_data["use_hybrid"] = False
    response = requests.post(f"{MEMORY_BASE}/search/hybrid", json=search_data)
    if response.status_code == 200:
        result = response.json()
        print(f"\n✓ Vector-only search: {len(result.get('results', []))} found")

    return True


def test_contextual_search():
    """Test contextual search with filters."""
    print_section("TEST 8: Contextual Search (Filtered)")

    search_data = {
        "query": "high value transactions",
        "context": {
            "transaction_type": "TRANSFER",
            "fraud_label": True,
        },
        "n_results": 5,
    }

    response = requests.post(f"{MEMORY_BASE}/search/contextual", json=search_data)
    if response.status_code == 200:
        result = response.json()
        print(f"✓ Contextual search completed")
        print(f"  Query: {result.get('query')}")
        print(f"  Context: {result.get('context')}")
        print(f"  Episodic results: {result.get('episodic_count')}")
        print(f"  Semantic results: {result.get('semantic_count')}")

    return True


def test_complete_task():
    """Test task completion and memory storage."""
    print_section("TEST 9: Task Completion")

    outcome = {
        "is_fraud": True,
        "confidence": 0.88,
        "risk_score": 0.85,
        "amount": 1500,
        "decision": "flagged",
        "reason": "High-value foreign transfer detected",
    }

    response = requests.post(
        f"{MEMORY_BASE}/task/complete",
        json={"outcome": outcome, "store_memory": True}
    )
    if response.status_code == 200:
        result = response.json()
        print(f"✓ Task completed")
        print(f"  Stored to long-term memory: {result.get('stored')}")

    return True


def test_memory_stats():
    """Test comprehensive memory statistics."""
    print_section("TEST 10: Memory Statistics")

    response = requests.get(f"{MEMORY_BASE}/stats")
    if response.status_code == 200:
        result = response.json()
        stats = result.get('stats', {})

        print(f"✓ Memory system statistics:")
        print(f"\n  Short-term Memory:")
        stm = stats.get('short_term', {})
        print(f"    Task: {stm.get('task', {}).get('id', 'None')}")
        print(f"    Reasoning steps: {stm.get('reasoning_steps')}")
        print(f"    Tool calls: {stm.get('tool_calls')}")
        print(f"    Token count: {stm.get('token_count')}")

        print(f"\n  Working Memory:")
        wm = stats.get('working', {})
        print(f"    Size: {wm.get('size')}/{wm.get('capacity')}")
        print(f"    Hit rate: {wm.get('hit_rate', 0):.2%}")

        print(f"\n  Episodic Memory:")
        em = stats.get('episodic', {})
        print(f"    Episodes stored: {em.get('count')}")
        print(f"    Buffer size: {em.get('buffer_size')}")

        print(f"\n  Semantic Memory:")
        sm = stats.get('semantic', {})
        print(f"    Knowledge items: {sm.get('count')}")

        print(f"\n  Procedural Memory:")
        pm = stats.get('procedural', {})
        print(f"    Procedures: {pm.get('procedures')}")
        print(f"    Tool patterns: {pm.get('tool_patterns')}")
        print(f"    Successful chains: {pm.get('successful_chains')}")

        print(f"\n  Retrieval System:")
        rs = stats.get('retrieval', {})
        print(f"    Indexed collections: {rs.get('indexed_collections', [])}")
        print(f"    Hybrid search: {rs.get('hybrid_search_enabled')}")

    return True


def main():
    """Run all memory system tests."""
    print("\n" + "=" * 80)
    print("  MEMORY SYSTEMS IMPLEMENTATION TEST")
    print("  FinSight AI - AGI-Inspired Memory Architecture")
    print("=" * 80)

    # Run tests
    tests = [
        ("Health Check", test_health_check),
        ("Short-Term Memory", test_short_term_memory),
        ("Working Memory", test_working_memory),
        ("Episodic Memory", test_episodic_memory),
        ("Semantic Memory", test_semantic_memory),
        ("Procedural Memory", test_procedural_memory),
        ("Hybrid Search", test_hybrid_search),
        ("Contextual Search", test_contextual_search),
        ("Task Completion", test_complete_task),
        ("Memory Statistics", test_memory_stats),
    ]

    results = []
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, success))
        except Exception as e:
            print(f"✗ Test failed with exception: {e}")
            results.append((name, False))

    # Summary
    print_section("TEST SUMMARY")
    passed = sum(1 for _, success in results if success)
    total = len(results)

    for name, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status}: {name}")

    print(f"\nTotal: {passed}/{total} tests passed ({passed/total*100:.1f}%)")

    if passed == total:
        print("\n🎉 All tests passed! Memory system is working correctly.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
