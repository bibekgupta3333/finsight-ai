"""
Multi-Agent Systems for Fraud Detection.

Implements five advanced multi-agent patterns:
1. Manager-Worker: Coordinator delegates to specialized workers
2. Planner-Executor-Critic: Planning, execution, and critique roles
3. Debate: Prosecutor vs Defense with Judge arbitration
4. Role-Specialized: Domain experts collaborate
5. Swarm: Parallel agents with consensus voting
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from enum import Enum
import asyncio
import logging
from datetime import datetime

from app.agents.single_agent import FraudDetectionAgent, AgentResult

logger = logging.getLogger(__name__)


class AgentRole(str, Enum):
    """Agent roles in multi-agent systems."""
    MANAGER = "manager"
    WORKER = "worker"
    PLANNER = "planner"
    EXECUTOR = "executor"
    CRITIC = "critic"
    PROSECUTOR = "prosecutor"
    DEFENSE = "defense"
    JUDGE = "judge"
    SPECIALIST = "specialist"
    SWARM_AGENT = "swarm_agent"


class ConsensusStrategy(str, Enum):
    """Consensus strategies for multi-agent decision making."""
    MAJORITY_VOTE = "majority_vote"
    WEIGHTED_VOTE = "weighted_vote"
    UNANIMOUS = "unanimous"
    THRESHOLD = "threshold"


class MultiAgentResult(BaseModel):
    """Result from multi-agent system."""

    # Final consensus
    is_fraud: bool
    risk_score: float
    confidence: float
    explanation: str

    # Individual agent results
    agent_results: Dict[str, AgentResult]

    # Consensus metadata
    consensus_strategy: str
    agreement_level: float  # 0.0 to 1.0

    # Execution
    total_time: float
    transaction_id: str


class ManagerWorkerSystem:
    """
    Manager-Worker pattern.

    Manager coordinates multiple specialized worker agents:
    - Manager decomposes task and assigns to workers
    - Workers execute in parallel
    - Manager aggregates results

    Example:
        ```python
        system = ManagerWorkerSystem(num_workers=3)
        result = await system.analyze(transaction, "txn_001")
        ```
    """

    def __init__(self, num_workers: int = 3):
        """
        Initialize manager-worker system.

        Args:
            num_workers: Number of worker agents
        """
        self.num_workers = num_workers
        self.workers = [FraudDetectionAgent() for _ in range(num_workers)]
        logger.info(f"Initialized ManagerWorkerSystem with {num_workers} workers")

    async def analyze(
        self,
        transaction: Dict[str, Any],
        transaction_id: str,
    ) -> MultiAgentResult:
        """
        Analyze transaction using manager-worker pattern.

        Args:
            transaction: Transaction data
            transaction_id: Transaction identifier

        Returns:
            Multi-agent consensus result
        """
        start_time = datetime.now()
        logger.info(f"Manager delegating to {self.num_workers} workers")

        # Execute all workers in parallel
        tasks = [
            worker.analyze(transaction, f"{transaction_id}_worker_{i}")
            for i, worker in enumerate(self.workers)
        ]
        worker_results = await asyncio.gather(*tasks)

        # Manager aggregates results
        fraud_votes = sum(1 for r in worker_results if r.is_fraud)
        is_fraud = fraud_votes > (self.num_workers / 2)

        avg_risk = sum(r.risk_score for r in worker_results) / self.num_workers
        avg_confidence = sum(r.confidence for r in worker_results) / self.num_workers
        agreement = fraud_votes / self.num_workers if is_fraud else (self.num_workers - fraud_votes) / self.num_workers

        execution_time = (datetime.now() - start_time).total_seconds()

        return MultiAgentResult(
            is_fraud=is_fraud,
            risk_score=avg_risk,
            confidence=avg_confidence,
            explanation=f"Manager consensus: {fraud_votes}/{self.num_workers} workers detected fraud",
            agent_results={f"worker_{i}": r for i, r in enumerate(worker_results)},
            consensus_strategy=ConsensusStrategy.MAJORITY_VOTE,
            agreement_level=agreement,
            total_time=execution_time,
            transaction_id=transaction_id,
        )


class PlannerExecutorCriticSystem:
    """
    Planner-Executor-Critic pattern.

    Three specialized roles:
    - Planner: Creates analysis strategy
    - Executor: Executes the plan
    - Critic: Reviews and validates results

    Example:
        ```python
        system = PlannerExecutorCriticSystem()
        result = await system.analyze(transaction, "txn_001")
        ```
    """

    def __init__(self):
        """Initialize planner-executor-critic system."""
        self.planner = FraudDetectionAgent(max_steps=10)
        self.executor = FraudDetectionAgent(max_steps=20)
        self.critic = FraudDetectionAgent(max_steps=10)
        logger.info("Initialized PlannerExecutorCriticSystem")

    async def analyze(
        self,
        transaction: Dict[str, Any],
        transaction_id: str,
    ) -> MultiAgentResult:
        """
        Analyze using planner-executor-critic pattern.

        Args:
            transaction: Transaction data
            transaction_id: Transaction identifier

        Returns:
            Multi-agent result with critique
        """
        start_time = datetime.now()

        # 1. Planner creates strategy (quick analysis)
        logger.info("Planner creating analysis strategy")
        planner_result = await self.planner.analyze(transaction, f"{transaction_id}_planner")

        # 2. Executor performs detailed analysis
        logger.info("Executor performing detailed analysis")
        executor_result = await self.executor.analyze(transaction, f"{transaction_id}_executor")

        # 3. Critic validates executor's result
        logger.info("Critic validating results")
        critic_result = await self.critic.analyze(transaction, f"{transaction_id}_critic")

        # Combine insights: Executor's decision with Critic's validation
        # If critic and executor disagree significantly, escalate
        disagreement = abs(executor_result.risk_score - critic_result.risk_score)

        if disagreement > 30:
            # Major disagreement - use more conservative estimate
            final_fraud = executor_result.is_fraud or critic_result.is_fraud
            final_risk = max(executor_result.risk_score, critic_result.risk_score)
            explanation = f"Executor and Critic disagree (Δ={disagreement:.1f}) - escalating"
        else:
            # Agreement - use executor's result
            final_fraud = executor_result.is_fraud
            final_risk = executor_result.risk_score
            explanation = f"Planner-Executor-Critic consensus: fraud={final_fraud}"

        execution_time = (datetime.now() - start_time).total_seconds()
        agreement = 1.0 - (disagreement / 100.0)

        return MultiAgentResult(
            is_fraud=final_fraud,
            risk_score=final_risk,
            confidence=min(executor_result.confidence, critic_result.confidence),
            explanation=explanation,
            agent_results={
                "planner": planner_result,
                "executor": executor_result,
                "critic": critic_result,
            },
            consensus_strategy="planner_executor_critic",
            agreement_level=agreement,
            total_time=execution_time,
            transaction_id=transaction_id,
        )


class DebateSystem:
    """
    Debate pattern.

    Adversarial agents debate the fraud classification:
    - Prosecutor: Argues transaction IS fraud
    - Defense: Argues transaction is legitimate
    - Judge: Makes final ruling based on arguments

    Example:
        ```python
        system = DebateSystem()
        result = await system.analyze(transaction, "txn_001")
        ```
    """

    def __init__(self):
        """Initialize debate system."""
        self.prosecutor = FraudDetectionAgent(max_steps=15)
        self.defense = FraudDetectionAgent(max_steps=15)
        self.judge = FraudDetectionAgent(max_steps=10)
        logger.info("Initialized DebateSystem")

    async def analyze(
        self,
        transaction: Dict[str, Any],
        transaction_id: str,
    ) -> MultiAgentResult:
        """
        Analyze using debate pattern.

        Args:
            transaction: Transaction data
            transaction_id: Transaction identifier

        Returns:
            Multi-agent result with debate outcome
        """
        start_time = datetime.now()

        # Run prosecutor and defense in parallel
        logger.info("Starting debate between Prosecutor and Defense")
        prosecutor_task = self.prosecutor.analyze(transaction, f"{transaction_id}_prosecutor")
        defense_task = self.defense.analyze(transaction, f"{transaction_id}_defense")

        prosecutor_result, defense_result = await asyncio.gather(
            prosecutor_task,
            defense_task,
        )

        # Judge makes final ruling
        logger.info("Judge making final ruling")
        judge_result = await self.judge.analyze(transaction, f"{transaction_id}_judge")

        # Judge considers both arguments
        # If prosecutor has high confidence fraud AND defense has low confidence non-fraud, likely fraud
        prosecutor_strength = prosecutor_result.risk_score * prosecutor_result.confidence
        defense_strength = (100 - defense_result.risk_score) * defense_result.confidence

        # Weight judge's opinion most heavily
        final_fraud = judge_result.is_fraud
        final_risk = judge_result.risk_score

        # But adjust confidence based on debate agreement
        if prosecutor_result.is_fraud == defense_result.is_fraud:
            # Both sides agree - high confidence
            confidence = 0.95
            agreement = 1.0
            explanation = f"Unanimous: Both sides agree transaction is {'FRAUD' if final_fraud else 'LEGITIMATE'}"
        else:
            # Disagreement - moderate confidence
            confidence = judge_result.confidence * 0.8
            argument_gap = abs(prosecutor_strength - defense_strength)
            agreement = max(0.5, 1.0 - (argument_gap / 100.0))
            explanation = (
                f"Judge ruled {'FRAUD' if final_fraud else 'LEGITIMATE'} "
                f"(Prosecutor: {prosecutor_result.risk_score:.1f}, "
                f"Defense: {defense_result.risk_score:.1f})"
            )

        execution_time = (datetime.now() - start_time).total_seconds()

        return MultiAgentResult(
            is_fraud=final_fraud,
            risk_score=final_risk,
            confidence=confidence,
            explanation=explanation,
            agent_results={
                "prosecutor": prosecutor_result,
                "defense": defense_result,
                "judge": judge_result,
            },
            consensus_strategy="debate",
            agreement_level=agreement,
            total_time=execution_time,
            transaction_id=transaction_id,
        )


class RoleSpecializedSystem:
    """
    Role-specialized pattern.

    Domain experts collaborate:
    - Transaction Analyst: Examines transaction patterns
    - Account Specialist: Analyzes account history
    - Policy Expert: Checks compliance and policies

    Example:
        ```python
        system = RoleSpecializedSystem()
        result = await system.analyze(transaction, "txn_001")
        ```
    """

    def __init__(self):
        """Initialize role-specialized system."""
        self.transaction_analyst = FraudDetectionAgent(max_steps=15)
        self.account_specialist = FraudDetectionAgent(max_steps=15)
        self.policy_expert = FraudDetectionAgent(max_steps=10)
        logger.info("Initialized RoleSpecializedSystem")

    async def analyze(
        self,
        transaction: Dict[str, Any],
        transaction_id: str,
    ) -> MultiAgentResult:
        """
        Analyze using role-specialized pattern.

        Args:
            transaction: Transaction data
            transaction_id: Transaction identifier

        Returns:
            Multi-agent result with specialist consensus
        """
        start_time = datetime.now()

        # All specialists analyze in parallel
        logger.info("Specialists analyzing transaction")
        results = await asyncio.gather(
            self.transaction_analyst.analyze(transaction, f"{transaction_id}_analyst"),
            self.account_specialist.analyze(transaction, f"{transaction_id}_account"),
            self.policy_expert.analyze(transaction, f"{transaction_id}_policy"),
        )

        analyst_result, account_result, policy_result = results

        # Weighted voting: Each specialist has expertise weight
        weights = {
            "analyst": 0.4,  # Transaction patterns most important
            "account": 0.3,  # Account history important
            "policy": 0.3,   # Policy compliance important
        }

        weighted_risk = (
            analyst_result.risk_score * weights["analyst"] +
            account_result.risk_score * weights["account"] +
            policy_result.risk_score * weights["policy"]
        )

        # Consensus if >= 2 specialists agree
        fraud_votes = sum([
            analyst_result.is_fraud,
            account_result.is_fraud,
            policy_result.is_fraud,
        ])

        is_fraud = fraud_votes >= 2
        agreement = fraud_votes / 3.0 if is_fraud else (3 - fraud_votes) / 3.0

        execution_time = (datetime.now() - start_time).total_seconds()

        return MultiAgentResult(
            is_fraud=is_fraud,
            risk_score=weighted_risk,
            confidence=agreement,
            explanation=f"Specialist consensus: {fraud_votes}/3 experts detected fraud (weighted risk: {weighted_risk:.1f})",
            agent_results={
                "transaction_analyst": analyst_result,
                "account_specialist": account_result,
                "policy_expert": policy_result,
            },
            consensus_strategy=ConsensusStrategy.WEIGHTED_VOTE,
            agreement_level=agreement,
            total_time=execution_time,
            transaction_id=transaction_id,
        )


class SwarmSystem:
    """
    Swarm intelligence pattern.

    Multiple agents run in parallel and vote on result:
    - All agents analyze independently
    - Consensus through voting
    - Emergent intelligence from collective

    Example:
        ```python
        system = SwarmSystem(swarm_size=5, consensus_threshold=0.6)
        result = await system.analyze(transaction, "txn_001")
        ```
    """

    def __init__(self, swarm_size: int = 5, consensus_threshold: float = 0.6):
        """
        Initialize swarm system.

        Args:
            swarm_size: Number of agents in swarm
            consensus_threshold: Fraction needed for consensus (0.0-1.0)
        """
        self.swarm_size = swarm_size
        self.consensus_threshold = consensus_threshold
        self.agents = [FraudDetectionAgent() for _ in range(swarm_size)]
        logger.info(f"Initialized SwarmSystem with {swarm_size} agents")

    async def analyze(
        self,
        transaction: Dict[str, Any],
        transaction_id: str,
    ) -> MultiAgentResult:
        """
        Analyze using swarm pattern.

        Args:
            transaction: Transaction data
            transaction_id: Transaction identifier

        Returns:
            Multi-agent result with swarm consensus
        """
        start_time = datetime.now()

        # All agents run in parallel
        logger.info(f"Swarm of {self.swarm_size} agents analyzing")
        tasks = [
            agent.analyze(transaction, f"{transaction_id}_swarm_{i}")
            for i, agent in enumerate(self.agents)
        ]
        results = await asyncio.gather(*tasks)

        # Count votes
        fraud_votes = sum(1 for r in results if r.is_fraud)
        vote_fraction = fraud_votes / self.swarm_size

        # Determine consensus
        is_fraud = vote_fraction >= self.consensus_threshold

        # Average metrics
        avg_risk = sum(r.risk_score for r in results) / self.swarm_size
        avg_confidence = sum(r.confidence for r in results) / self.swarm_size

        # Agreement is how close to unanimous
        agreement = vote_fraction if is_fraud else (1.0 - vote_fraction)

        execution_time = (datetime.now() - start_time).total_seconds()

        return MultiAgentResult(
            is_fraud=is_fraud,
            risk_score=avg_risk,
            confidence=avg_confidence,
            explanation=f"Swarm consensus: {fraud_votes}/{self.swarm_size} agents detected fraud ({vote_fraction:.1%})",
            agent_results={f"swarm_{i}": r for i, r in enumerate(results)},
            consensus_strategy=ConsensusStrategy.THRESHOLD,
            agreement_level=agreement,
            total_time=execution_time,
            transaction_id=transaction_id,
        )
