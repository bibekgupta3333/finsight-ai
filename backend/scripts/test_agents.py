"""
Test script for agent-based fraud detection.

Tests single-agent and multi-agent systems locally without pytest.
Run directly with: python backend/scripts/test_agents.py
"""

import asyncio
import json
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Test transactions
TEST_TRANSACTIONS = {
    "legitimate_small": {
        "amount": 500.00,
        "type": "PAYMENT",
        "oldbalanceOrg": 10000.00,
        "newbalanceOrig": 9500.00,
        "oldbalanceDest": 5000.00,
        "newbalanceDest": 5500.00,
        "nameOrig": "C_legitimate",
        "nameDest": "M_merchant",
    },
    "suspicious_transfer": {
        "amount": 150000.00,
        "type": "TRANSFER",
        "oldbalanceOrg": 200000.00,
        "newbalanceOrig": 50000.00,
        "oldbalanceDest": 100000.00,
        "newbalanceDest": 250000.00,
        "nameOrig": "C_suspicious",
        "nameDest": "C_receiver",
    },
    "obvious_fraud": {
        "amount": 300000.00,
        "type": "CASH_OUT",
        "oldbalanceOrg": 300000.00,
        "newbalanceOrig": 0.00,
        "oldbalanceDest": 0.00,
        "newbalanceDest": 0.00,  # Money disappeared
        "nameOrig": "C_victim",
        "nameDest": "C_fraudster",
    },
}


async def test_single_agent():
    """Test single-agent fraud detection."""
    from app.agents import FraudDetectionAgent
    
    logger.info("=" * 70)
    logger.info("TESTING SINGLE-AGENT ARCHITECTURE")
    logger.info("=" * 70)
    
    agent = FraudDetectionAgent(max_steps=20)
    
    for test_name, transaction in TEST_TRANSACTIONS.items():
        logger.info(f"\nTest: {test_name}")
        logger.info(f"Amount: ${transaction['amount']:,.2f}")
        logger.info(f"Type: {transaction['type']}")
        
        result = await agent.analyze(transaction, f"test_{test_name}")
        
        logger.info(f"\n=== RESULT ===")
        logger.info(f"Fraud: {result.is_fraud}")
        logger.info(f"Risk Score: {result.risk_score:.1f}/100")
        logger.info(f"Risk Level: {result.risk_level}")
        logger.info(f"Confidence: {result.confidence:.2%}")
        logger.info(f"Explanation: {result.explanation}")
        logger.info(f"\nObservations ({len(result.observations)}):")
        for obs in result.observations:
            logger.info(f"  - {obs}")
        logger.info(f"\nAnomalies ({len(result.anomalies)}):")
        for anom in result.anomalies:
            logger.info(f"  - {anom}")
        logger.info(f"\nReasoning Steps ({len(result.reasoning_steps)}):")
        for i, step in enumerate(result.reasoning_steps, 1):
            logger.info(f"  {i}. {step}")
        logger.info(f"\nTool Results:")
        for tool, result_data in result.tool_results.items():
            logger.info(f"  - {tool}: {result_data}")
        logger.info(f"\nEscalation: {result.should_escalate}")
        if result.should_escalate:
            logger.info(f"Reason: {result.escalation_reason}")
        logger.info(f"Self-Critique: {result.self_critique}")
        logger.info(f"\nMetadata:")
        logger.info(f"  Steps: {result.total_steps}")
        logger.info(f"  Termination: {result.termination_reason}")
        logger.info(f"  Time: {result.execution_time:.2f}s")
        logger.info("-" * 70)
    
    # Test memory
    logger.info("\n=== MEMORY STATISTICS ===")
    stats = agent.get_memory_stats()
    logger.info(json.dumps(stats, indent=2))


async def test_manager_worker():
    """Test manager-worker multi-agent system."""
    from app.agents import ManagerWorkerSystem
    
    logger.info("\n" + "=" * 70)
    logger.info("TESTING MANAGER-WORKER MULTI-AGENT SYSTEM")
    logger.info("=" * 70)
    
    system = ManagerWorkerSystem(num_workers=3)
    
    transaction = TEST_TRANSACTIONS["suspicious_transfer"]
    logger.info(f"Testing with suspicious transfer: ${transaction['amount']:,.2f}")
    
    result = await system.analyze(transaction, "test_manager_worker")
    
    logger.info(f"\n=== CONSENSUS RESULT ===")
    logger.info(f"Fraud: {result.is_fraud}")
    logger.info(f"Risk Score: {result.risk_score:.1f}/100")
    logger.info(f"Confidence: {result.confidence:.2%}")
    logger.info(f"Explanation: {result.explanation}")
    logger.info(f"Strategy: {result.consensus_strategy}")
    logger.info(f"Agreement: {result.agreement_level:.2%}")
    logger.info(f"Time: {result.total_time:.2f}s")
    logger.info(f"\nIndividual Workers:")
    for worker_id, worker_result in result.agent_results.items():
        logger.info(f"  {worker_id}: fraud={worker_result.is_fraud}, risk={worker_result.risk_score:.1f}")


async def test_planner_executor_critic():
    """Test planner-executor-critic system."""
    from app.agents import PlannerExecutorCriticSystem
    
    logger.info("\n" + "=" * 70)
    logger.info("TESTING PLANNER-EXECUTOR-CRITIC SYSTEM")
    logger.info("=" * 70)
    
    system = PlannerExecutorCriticSystem()
    
    transaction = TEST_TRANSACTIONS["obvious_fraud"]
    logger.info(f"Testing with obvious fraud: ${transaction['amount']:,.2f}")
    
    result = await system.analyze(transaction, "test_pec")
    
    logger.info(f"\n=== RESULT ===")
    logger.info(f"Fraud: {result.is_fraud}")
    logger.info(f"Risk Score: {result.risk_score:.1f}/100")
    logger.info(f"Confidence: {result.confidence:.2%}")
    logger.info(f"Explanation: {result.explanation}")
    logger.info(f"Agreement: {result.agreement_level:.2%}")
    logger.info(f"Time: {result.total_time:.2f}s")
    logger.info(f"\nAgent Results:")
    for agent_id, agent_result in result.agent_results.items():
        logger.info(f"  {agent_id}: fraud={agent_result.is_fraud}, risk={agent_result.risk_score:.1f}, conf={agent_result.confidence:.2%}")


async def test_debate():
    """Test debate system."""
    from app.agents import DebateSystem
    
    logger.info("\n" + "=" * 70)
    logger.info("TESTING DEBATE SYSTEM (Prosecutor vs Defense)")
    logger.info("=" * 70)
    
    system = DebateSystem()
    
    transaction = TEST_TRANSACTIONS["suspicious_transfer"]
    logger.info(f"Testing with suspicious transfer: ${transaction['amount']:,.2f}")
    
    result = await system.analyze(transaction, "test_debate")
    
    logger.info(f"\n=== JUDGE'S RULING ===")
    logger.info(f"Fraud: {result.is_fraud}")
    logger.info(f"Risk Score: {result.risk_score:.1f}/100")
    logger.info(f"Confidence: {result.confidence:.2%}")
    logger.info(f"Explanation: {result.explanation}")
    logger.info(f"Agreement: {result.agreement_level:.2%}")
    logger.info(f"Time: {result.total_time:.2f}s")
    logger.info(f"\nDebate Positions:")
    for agent_id, agent_result in result.agent_results.items():
        logger.info(f"  {agent_id}: fraud={agent_result.is_fraud}, risk={agent_result.risk_score:.1f}")


async def test_role_specialized():
    """Test role-specialized system."""
    from app.agents import RoleSpecializedSystem
    
    logger.info("\n" + "=" * 70)
    logger.info("TESTING ROLE-SPECIALIZED SYSTEM (Domain Experts)")
    logger.info("=" * 70)
    
    system = RoleSpecializedSystem()
    
    transaction = TEST_TRANSACTIONS["suspicious_transfer"]
    logger.info(f"Testing with suspicious transfer: ${transaction['amount']:,.2f}")
    
    result = await system.analyze(transaction, "test_specialists")
    
    logger.info(f"\n=== EXPERT CONSENSUS ===")
    logger.info(f"Fraud: {result.is_fraud}")
    logger.info(f"Risk Score: {result.risk_score:.1f}/100 (weighted)")
    logger.info(f"Confidence: {result.confidence:.2%}")
    logger.info(f"Explanation: {result.explanation}")
    logger.info(f"Strategy: {result.consensus_strategy}")
    logger.info(f"Agreement: {result.agreement_level:.2%}")
    logger.info(f"Time: {result.total_time:.2f}s")
    logger.info(f"\nSpecialist Opinions:")
    for specialist_id, specialist_result in result.agent_results.items():
        logger.info(f"  {specialist_id}: fraud={specialist_result.is_fraud}, risk={specialist_result.risk_score:.1f}")


async def test_swarm():
    """Test swarm intelligence system."""
    from app.agents import SwarmSystem
    
    logger.info("\n" + "=" * 70)
    logger.info("TESTING SWARM INTELLIGENCE (5 agents, 60% threshold)")
    logger.info("=" * 70)
    
    system = SwarmSystem(swarm_size=5, consensus_threshold=0.6)
    
    transaction = TEST_TRANSACTIONS["obvious_fraud"]
    logger.info(f"Testing with obvious fraud: ${transaction['amount']:,.2f}")
    
    result = await system.analyze(transaction, "test_swarm")
    
    logger.info(f"\n=== SWARM CONSENSUS ===")
    logger.info(f"Fraud: {result.is_fraud}")
    logger.info(f"Risk Score: {result.risk_score:.1f}/100 (average)")
    logger.info(f"Confidence: {result.confidence:.2%}")
    logger.info(f"Explanation: {result.explanation}")
    logger.info(f"Agreement: {result.agreement_level:.2%}")
    logger.info(f"Time: {result.total_time:.2f}s")
    logger.info(f"\nSwarm Vote Distribution:")
    fraud_count = sum(1 for r in result.agent_results.values() if r.is_fraud)
    logger.info(f"  Fraud: {fraud_count}/5")
    logger.info(f"  Legitimate: {5 - fraud_count}/5")


async def test_tool_registry():
    """Test tool registry and individual tools."""
    from app.agents.tool_registry import get_tool_registry
    
    logger.info("\n" + "=" * 70)
    logger.info("TESTING TOOL REGISTRY")
    logger.info("=" * 70)
    
    registry = get_tool_registry()
    
    # List tools
    logger.info("\n=== REGISTERED TOOLS ===")
    tools = registry.list_tools()
    logger.info(f"Total: {len(tools)}")
    for tool in tools:
        logger.info(f"  - {tool}")
    
    # Test each tool
    logger.info("\n=== TESTING TOOLS ===")
    
    transaction = TEST_TRANSACTIONS["suspicious_transfer"]
    
    # Test calculate_risk_score
    logger.info("\n1. calculate_risk_score")
    result = await registry.execute("calculate_risk_score", {"transaction": transaction})
    logger.info(f"   Success: {result.success}")
    logger.info(f"   Result: {result.result}")
    logger.info(f"   Time: {result.execution_time:.3f}s")
    
    # Test query_fraud_policy
    logger.info("\n2. query_fraud_policy")
    result = await registry.execute("query_fraud_policy", {"transaction_type": "TRANSFER"})
    logger.info(f"   Success: {result.success}")
    logger.info(f"   Result: {result.result}")
    logger.info(f"   Time: {result.execution_time:.3f}s")
    
    # Test check_account_history
    logger.info("\n3. check_account_history")
    result = await registry.execute("check_account_history", {"account_id": "C_suspicious"})
    logger.info(f"   Success: {result.success}")
    logger.info(f"   Result: {result.result}")
    logger.info(f"   Time: {result.execution_time:.3f}s")
    
    # Test escalate_to_human
    logger.info("\n4. escalate_to_human")
    result = await registry.execute(
        "escalate_to_human",
        {"transaction_id": "test_123", "reason": "Test escalation"}
    )
    logger.info(f"   Success: {result.success}")
    logger.info(f"   Result: {result.result}")
    logger.info(f"   Time: {result.execution_time:.3f}s")
    
    # Test parallel execution
    logger.info("\n=== TESTING PARALLEL EXECUTION ===")
    tool_calls = [
        {"tool_name": "calculate_risk_score", "parameters": {"transaction": transaction}},
        {"tool_name": "query_fraud_policy", "parameters": {"transaction_type": "TRANSFER"}},
        {"tool_name": "check_account_history", "parameters": {"account_id": "C_suspicious"}},
    ]
    
    start = datetime.now()
    results = await registry.execute_parallel(tool_calls)
    total_time = (datetime.now() - start).total_seconds()
    
    logger.info(f"Executed {len(results)} tools in {total_time:.3f}s (parallel)")
    for i, result in enumerate(results, 1):
        logger.info(f"  {i}. {result.tool_name}: success={result.success}, time={result.execution_time:.3f}s")


async def run_all_tests():
    """Run all tests."""
    start_time = datetime.now()
    
    logger.info("\n" + "#" * 70)
    logger.info("# AGENT-BASED FRAUD DETECTION TEST SUITE")
    logger.info("#" * 70)
    
    try:
        # Test infrastructure first
        await test_tool_registry()
        
        # Test single-agent
        await test_single_agent()
        
        # Test multi-agent systems
        await test_manager_worker()
        await test_planner_executor_critic()
        await test_debate()
        await test_role_specialized()
        await test_swarm()
        
        total_time = (datetime.now() - start_time).total_seconds()
        
        logger.info("\n" + "#" * 70)
        logger.info(f"# ALL TESTS COMPLETE - Total Time: {total_time:.2f}s")
        logger.info("#" * 70)
        
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(run_all_tests())
