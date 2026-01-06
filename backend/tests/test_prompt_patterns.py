"""
Test script for Advanced Prompting Patterns (Section 3.2).

Tests all implemented patterns:
- Prompt Hierarchy & Control
- ReAct, CoT, ToT patterns
- Debate/Critique
- Self-Critique & Reflection
- Prompt Engineering techniques
"""

import asyncio
import json
from datetime import datetime
import httpx

# Configuration
BASE_URL = "http://localhost:8000/api/v1"
TIMEOUT = 60.0

# Colors for output
class Color:
    GREEN = '\033[92m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    YELLOW = '\033[93m'
    END = '\033[0m'


def print_header(text: str):
    """Print section header."""
    print(f"\n{'=' * 80}")
    print(f"{Color.BLUE}{text}{Color.END}")
    print('=' * 80)


def print_success(text: str):
    """Print success message."""
    print(f"{Color.GREEN}✓ {text}{Color.END}")


def print_error(text: str):
    """Print error message."""
    print(f"{Color.RED}✗ {text}{Color.END}")


def print_info(text: str):
    """Print info message."""
    print(f"{Color.YELLOW}ℹ {text}{Color.END}")


def create_sample_transaction():
    """Create a sample fraud transaction for testing."""
    return {
        "transaction_id": f"TXN_{datetime.now().strftime('%H%M%S')}",
        "type": "TRANSFER",
        "amount": 500000.0,
        "oldbalanceOrg": 500000.0,
        "newbalanceOrig": 0.0,
        "oldbalanceDest": 0.0,
        "newbalanceDest": 0.0,  # Money disappeared!
        "nameOrig": "C123456789",
        "nameDest": "C987654321",
        "isFraud": 1,  # Ground truth
    }


async def test_prompt_templates():
    """Test 1: Prompt template management."""
    print_header("TEST 1: Prompt Template Management")

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get(f"{BASE_URL}/fraud/prompts/templates")

            if response.status_code == 200:
                data = response.json()
                templates = data.get("templates", [])

                print_success(f"Retrieved {len(templates)} prompt templates")

                for tmpl in templates:
                    print_info(f"  Template: {tmpl['template_id']}")
                    print_info(f"    Level: {tmpl['level']}")
                    print_info(f"    Version: {tmpl['version']}")
                    print_info(f"    Active: {tmpl['active']}")
                    print_info(f"    Constraints: {tmpl['constraint_count']}")

                return True
            else:
                print_error(f"Failed: {response.status_code} - {response.text}")
                return False

    except Exception as e:
        print_error(f"Test failed: {e}")
        return False


async def test_hierarchical_prompt():
    """Test 2: Hierarchical prompt building."""
    print_header("TEST 2: Hierarchical Prompt Building")

    transaction = create_sample_transaction()

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.post(
                f"{BASE_URL}/fraud/prompts/build",
                json=transaction,
            )

            if response.status_code == 200:
                data = response.json()

                print_success("Hierarchical prompt built successfully")
                print_info(f"  Few-shot examples: {data['few_shot_examples_count']}")
                print_info(f"  Estimated tokens: {data['estimated_tokens']}")
                print_info(f"  Prompt length: {len(data['full_prompt'])} chars")

                # Show snippet
                prompt = data['full_prompt']
                print_info("\n  Prompt structure:")
                for line in prompt.split('\n')[:20]:
                    if line.strip().startswith('==='):
                        print_info(f"    {line}")

                return True
            else:
                print_error(f"Failed: {response.status_code} - {response.text}")
                return False

    except Exception as e:
        print_error(f"Test failed: {e}")
        return False


async def test_react_pattern():
    """Test 3: ReAct (Reasoning + Acting) pattern."""
    print_header("TEST 3: ReAct Pattern")

    transaction = create_sample_transaction()

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.post(
                f"{BASE_URL}/fraud/analyze/react",
                json={"transaction": transaction},
            )

            if response.status_code == 200:
                data = response.json()

                print_success("ReAct analysis completed")
                print_info(f"  Pattern: {data['pattern']}")
                print_info(f"  Steps taken: {data['steps_taken']}")

                # Show reasoning trace
                if 'result' in data and 'trace' in data['result']:
                    print_info("\n  Reasoning Trace:")
                    for step in data['result']['trace'][:3]:  # Show first 3 steps
                        print_info(f"    Thought: {step.get('thought', 'N/A')[:80]}...")
                        print_info(f"    Action: {step.get('action', 'N/A')}")
                        print_info(f"    Observation: {step.get('observation', 'N/A')[:80]}...")

                return True
            else:
                print_error(f"Failed: {response.status_code} - {response.text}")
                return False

    except Exception as e:
        print_error(f"Test failed: {e}")
        return False


async def test_cot_pattern():
    """Test 4: Chain-of-Thought pattern."""
    print_header("TEST 4: Chain-of-Thought Pattern")

    transaction = create_sample_transaction()

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.post(
                f"{BASE_URL}/fraud/analyze/cot",
                json={"transaction": transaction},
            )

            if response.status_code == 200:
                data = response.json()

                print_success("CoT analysis completed")
                print_info(f"  Pattern: {data['pattern']}")
                print_info(f"  Reasoning steps: {data['reasoning_steps']}")

                # Show steps
                if 'result' in data and 'steps' in data['result']:
                    print_info("\n  Reasoning Steps:")
                    for i, step in enumerate(data['result']['steps'][:5], 1):
                        reasoning = step.get('reasoning', 'N/A')
                        if isinstance(reasoning, str):
                            print_info(f"    Step {i}: {reasoning[:100]}...")

                return True
            else:
                print_error(f"Failed: {response.status_code} - {response.text}")
                return False

    except Exception as e:
        print_error(f"Test failed: {e}")
        return False


async def test_tot_pattern():
    """Test 5: Tree-of-Thought pattern."""
    print_header("TEST 5: Tree-of-Thought Pattern")

    transaction = create_sample_transaction()

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.post(
                f"{BASE_URL}/fraud/analyze/tot",
                json={"transaction": transaction},
            )

            if response.status_code == 200:
                data = response.json()

                print_success("ToT analysis completed")
                print_info(f"  Pattern: {data['pattern']}")
                print_info(f"  Paths explored: {data['paths_explored']}")

                # Show best path
                if 'result' in data:
                    result = data['result']
                    print_info(f"  Tree depth: {result.get('tree_depth', 0)}")
                    print_info(f"  Best path score: {result.get('score', 0):.2f}")

                return True
            else:
                print_error(f"Failed: {response.status_code} - {response.text}")
                return False

    except Exception as e:
        print_error(f"Test failed: {e}")
        return False


async def test_debate_pattern():
    """Test 6: Debate pattern."""
    print_header("TEST 6: Debate Pattern (Prosecutor vs Defense)")

    transaction = create_sample_transaction()

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.post(
                f"{BASE_URL}/fraud/analyze/debate",
                json={"transaction": transaction},
            )

            if response.status_code == 200:
                data = response.json()

                print_success("Debate analysis completed")
                print_info(f"  Pattern: {data['pattern']}")
                print_info(f"  Debate rounds: {data['debate_rounds']}")
                print_info(f"  Arguments presented: {data['arguments_count']}")

                # Show arguments
                if 'result' in data and 'arguments' in data['result']:
                    print_info("\n  Debate Summary:")
                    for arg in data['result']['arguments'][:4]:  # Show first 4
                        position = arg.get('position', 'unknown')
                        argument = arg.get('argument', 'N/A')
                        print_info(f"    {position.upper()}: {argument[:80]}...")

                return True
            else:
                print_error(f"Failed: {response.status_code} - {response.text}")
                return False

    except Exception as e:
        print_error(f"Test failed: {e}")
        return False


async def test_self_critique():
    """Test 7: Self-Critique pattern."""
    print_header("TEST 7: Self-Critique Pattern")

    transaction = create_sample_transaction()

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.post(
                f"{BASE_URL}/fraud/analyze/self-critique",
                json={"transaction": transaction},
            )

            if response.status_code == 200:
                data = response.json()

                print_success("Self-Critique analysis completed")
                print_info(f"  Pattern: {data['pattern']}")
                print_info(f"  Revisions made: {data['revisions']}")

                # Show revision history
                if 'result' in data and 'revisions' in data['result']:
                    print_info("\n  Revision History:")
                    for rev in data['result']['revisions']:
                        iteration = rev.get('iteration', 0)
                        critique = rev.get('critique', {})
                        issues = critique.get('issues_found', [])
                        print_info(f"    Iteration {iteration}: Found {len(issues)} issues")
                        if issues:
                            print_info(f"      Issues: {', '.join(issues[:3])}")

                return True
            else:
                print_error(f"Failed: {response.status_code} - {response.text}")
                return False

    except Exception as e:
        print_error(f"Test failed: {e}")
        return False


async def test_reflection():
    """Test 8: Reflection pattern."""
    print_header("TEST 8: Reflection Pattern")

    transaction = create_sample_transaction()
    initial_decision = {
        "is_fraud": True,
        "risk_score": 85.0,
        "confidence": 0.95,
        "reasoning": "High-value transfer with balance inconsistencies",
    }

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.post(
                f"{BASE_URL}/fraud/analyze/reflection",
                json={
                    "transaction": transaction,
                    "initial_decision": initial_decision,
                },
            )

            if response.status_code == 200:
                data = response.json()

                print_success("Reflection validation completed")
                print_info(f"  Pattern: {data['pattern']}")
                print_info(f"  Should escalate: {data['should_escalate']}")

                # Show validation results
                if 'result' in data:
                    result = data['result']
                    policy_check = result.get('policy_alignment', {})
                    reasoning_check = result.get('reasoning_validation', {})

                    print_info("\n  Validation Results:")
                    print_info(f"    Policy aligned: {policy_check.get('aligned', True)}")
                    print_info(f"    Reasoning valid: {reasoning_check.get('valid', True)}")

                    if result.get('should_escalate'):
                        print_info(f"    Escalation reason: {result.get('escalation_reason', 'N/A')}")

                return True
            else:
                print_error(f"Failed: {response.status_code} - {response.text}")
                return False

    except Exception as e:
        print_error(f"Test failed: {e}")
        return False


async def test_few_shot_examples():
    """Test 9: Few-shot example selection."""
    print_header("TEST 9: Few-Shot Examples")

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get(
                f"{BASE_URL}/fraud/prompts/few-shot-examples",
                params={"count": 5, "ensure_diversity": True},
            )

            if response.status_code == 200:
                data = response.json()

                print_success(f"Retrieved {data['count']} few-shot examples")

                # Show example categories
                examples = data.get('examples', [])
                categories = {}
                for ex in examples:
                    cat = ex.get('category', 'unknown')
                    categories[cat] = categories.get(cat, 0) + 1

                print_info("\n  Example Distribution:")
                for cat, count in categories.items():
                    print_info(f"    {cat}: {count}")

                # Show difficulty range
                difficulties = [ex.get('difficulty', 1) for ex in examples]
                print_info(f"  Difficulty range: {min(difficulties)} - {max(difficulties)}")

                return True
            else:
                print_error(f"Failed: {response.status_code} - {response.text}")
                return False

    except Exception as e:
        print_error(f"Test failed: {e}")
        return False


async def test_prompt_compression():
    """Test 10: Prompt compression."""
    print_header("TEST 10: Prompt Compression")

    # Create a long prompt
    long_prompt = """
=== SYSTEM PROMPT ===
You are a fraud detection specialist with extensive experience.

=== CONSTRAINTS ===
1. Never provide financial advice
2. Only analyze fraud indicators
3. Cite evidence from transaction data
4. Return JSON output only

=== EXAMPLES ===
Example 1: High-value transfer...
Example 2: Normal payment...
Example 3: Suspicious cash-out...
(many more examples...)

=== POLICIES ===
Policy 1: TRANSFER > 100k = high risk
Policy 2: Balance inconsistencies = fraud
Policy 3: Multiple rapid transactions = suspicious
(many more policies...)

=== USER PROMPT ===
Analyze this transaction...
    """

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.post(
                f"{BASE_URL}/fraud/prompts/compress",
                json={"text": long_prompt, "max_tokens": 500},
            )

            if response.status_code == 200:
                data = response.json()

                print_success("Prompt compressed successfully")
                print_info(f"  Original length: {data['original_length']} chars")
                print_info(f"  Compressed length: {data['compressed_length']} chars")
                print_info(f"  Compression ratio: {data['compression_ratio']:.2%}")
                print_info(f"  Estimated tokens: {data['estimated_tokens']}")

                return True
            else:
                print_error(f"Failed: {response.status_code} - {response.text}")
                return False

    except Exception as e:
        print_error(f"Test failed: {e}")
        return False


async def test_output_schema():
    """Test 11: Output schema specification."""
    print_header("TEST 11: Output Schema Specification")

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get(f"{BASE_URL}/fraud/prompts/output-schema")

            if response.status_code == 200:
                data = response.json()
                schema = data.get('schema', {})

                print_success("Output schema retrieved")
                print_info(f"  Schema name: {schema.get('schema_name')}")
                print_info(f"  Required fields: {len(schema.get('required_fields', []))}")
                print_info(f"  Field types defined: {len(schema.get('field_types', {}))}")

                # Show required fields
                print_info("\n  Required Fields:")
                for field in schema.get('required_fields', []):
                    field_type = schema.get('field_types', {}).get(field, 'unknown')
                    print_info(f"    {field}: {field_type}")

                return True
            else:
                print_error(f"Failed: {response.status_code} - {response.text}")
                return False

    except Exception as e:
        print_error(f"Test failed: {e}")
        return False


async def test_output_validation():
    """Test 12: Output validation."""
    print_header("TEST 12: Output Validation")

    # Valid output
    valid_output = {
        "is_fraud": True,
        "risk_score": 85.0,
        "risk_level": "CRITICAL",
        "reasoning": "High-value transfer with balance inconsistencies",
        "confidence": 0.95,
        "evidence": ["amount > 100k", "newbalanceDest = 0"],
    }

    # Invalid output (missing fields)
    invalid_output = {
        "is_fraud": True,
        # Missing risk_score, risk_level, reasoning
    }

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            # Test valid output
            response1 = await client.post(
                f"{BASE_URL}/fraud/prompts/validate-output",
                json={"output": valid_output},
            )

            if response1.status_code == 200:
                data1 = response1.json()

                if data1['is_valid']:
                    print_success("Valid output passed validation")
                else:
                    print_error(f"Valid output failed: {data1.get('error')}")

            # Test invalid output
            response2 = await client.post(
                f"{BASE_URL}/fraud/prompts/validate-output",
                json={"output": invalid_output},
            )

            if response2.status_code == 200:
                data2 = response2.json()

                if not data2['is_valid']:
                    print_success(f"Invalid output correctly rejected: {data2.get('error')}")
                else:
                    print_error("Invalid output incorrectly passed validation")

            return True

    except Exception as e:
        print_error(f"Test failed: {e}")
        return False


async def test_role_playing():
    """Test 13: Role-playing instructions."""
    print_header("TEST 13: Role-Playing Instructions")

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get(f"{BASE_URL}/fraud/prompts/role-playing")

            if response.status_code == 200:
                data = response.json()

                print_success("Role-playing prompt retrieved")
                print_info(f"  Role: {data.get('role')}")
                print_info(f"  Benefits: {len(data.get('benefits', []))}")

                # Show benefits
                print_info("\n  Benefits:")
                for benefit in data.get('benefits', []):
                    print_info(f"    - {benefit}")

                # Show snippet of prompt
                prompt = data.get('prompt', '')
                lines = prompt.split('\n')[:15]
                print_info("\n  Prompt Snippet:")
                for line in lines:
                    if line.strip():
                        print_info(f"    {line}")

                return True
            else:
                print_error(f"Failed: {response.status_code} - {response.text}")
                return False

    except Exception as e:
        print_error(f"Test failed: {e}")
        return False


async def run_all_tests():
    """Run all tests."""
    print_header("Advanced Prompting Patterns Test Suite")
    print_info(f"Base URL: {BASE_URL}")
    print_info(f"Timeout: {TIMEOUT}s")
    print_info(f"Timestamp: {datetime.now().isoformat()}")

    # Check server health
    print_info("Checking server health...")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get("http://localhost:8000/health")
            if response.status_code == 200:
                print_success(f"Server is healthy: {response.json()}")
            else:
                print_error("Server health check failed!")
                return
    except Exception as e:
        print_error(f"Cannot connect to server: {e}")
        return

    # Run all tests
    tests = [
        ("Prompt Templates", test_prompt_templates),
        ("Hierarchical Prompt", test_hierarchical_prompt),
        ("ReAct Pattern", test_react_pattern),
        ("Chain-of-Thought", test_cot_pattern),
        ("Tree-of-Thought", test_tot_pattern),
        ("Debate Pattern", test_debate_pattern),
        ("Self-Critique", test_self_critique),
        ("Reflection", test_reflection),
        ("Few-Shot Examples", test_few_shot_examples),
        ("Prompt Compression", test_prompt_compression),
        ("Output Schema", test_output_schema),
        ("Output Validation", test_output_validation),
        ("Role-Playing", test_role_playing),
    ]

    results = []
    for name, test_func in tests:
        try:
            result = await test_func()
            results.append((name, result))
        except Exception as e:
            print_error(f"{name} failed with exception: {e}")
            results.append((name, False))

    # Summary
    print_header("Test Suite Complete")

    passed = sum(1 for _, result in results if result)
    total = len(results)

    print_info(f"\nResults: {passed}/{total} tests passed")

    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        color = Color.GREEN if result else Color.RED
        print(f"  {color}{status}{Color.END} - {name}")

    if passed == total:
        print_success("\n🎉 All tests passed!")
    else:
        print_error(f"\n⚠️  {total - passed} test(s) failed")


if __name__ == "__main__":
    asyncio.run(run_all_tests())
