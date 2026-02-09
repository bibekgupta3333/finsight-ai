"""
LangGraph-based Multi-Agent Systems for Fraud Detection.

Implements five advanced multi-agent patterns using LangGraph StateGraph:
1. Manager-Worker: Coordinator delegates to specialized workers
2. Planner-Executor-Critic: Planning, execution, and critique roles
3. Debate: Prosecutor vs Defense with Judge arbitration
4. Role-Specialized: Domain experts collaborate
5. Swarm: Parallel agents with consensus voting

Each pattern has its own StateGraph with conditional routing.
Maintains API compatibility with original multi_agent.py.

Migration from Phase 8.2: Uses LangGraph 1.0.7 for standardized agent orchestration.
"""

from typing import Dict, Any, List, Optional, TypedDict, Annotated
from langgraph.graph import StateGraph, END
from pydantic import BaseModel
from enum import Enum
import asyncio
import logging
from datetime import datetime
import operator

from app.agents.langgraph.single_agent import FraudDetectionAgentLangGraph, AgentResult

logger = logging.getLogger(__name__)


# ============================================================================
# Enums and Base Models (Keep API compatibility)
# ============================================================================


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
    """Result from multi-agent system (API compatibility)."""

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


# ============================================================================
# State Definitions (TypedDict for LangGraph)
# ============================================================================


class MultiAgentState(TypedDict, total=False):
    """Base state for all multi-agent patterns."""
    # Input
    transaction: Dict[str, Any]
    transaction_id: str

    # Individual agent results
    agent_results: Dict[str, AgentResult]

    # Aggregation
    is_fraud: bool
    risk_score: float
    confidence: float
    explanation: str
    consensus_strategy: str
    agreement_level: float

    # Metadata
    start_time: datetime
    total_time: float

    # Pattern-specific routing
    pattern_name: str
    current_step: str


class ManagerWorkerState(MultiAgentState, total=False):
    """State for Manager-Worker pattern."""
    num_workers: int
    worker_results: List[AgentResult]
    fraud_votes: int


class PECState(MultiAgentState, total=False):
    """State for Planner-Executor-Critic pattern."""
    planner_result: Optional[AgentResult]
    executor_result: Optional[AgentResult]
    critic_result: Optional[AgentResult]
    disagreement_score: float


class DebateState(MultiAgentState, total=False):
    """State for Debate pattern."""
    prosecutor_result: Optional[AgentResult]
    defense_result: Optional[AgentResult]
    judge_result: Optional[AgentResult]
    prosecutor_strength: float
    defense_strength: float


class RoleSpecializedState(MultiAgentState, total=False):
    """State for Role-Specialized pattern."""
    analyst_result: Optional[AgentResult]
    account_result: Optional[AgentResult]
    policy_result: Optional[AgentResult]
    specialist_weights: Dict[str, float]
    fraud_votes: int


class SwarmState(MultiAgentState, total=False):
    """State for Swarm pattern."""
    swarm_size: int
    consensus_threshold: float
    swarm_results: List[AgentResult]
    fraud_votes: int
    vote_fraction: float


# ============================================================================
# Pattern 1: Manager-Worker System
# ============================================================================


async def manager_delegate_node(state: ManagerWorkerState) -> ManagerWorkerState:
    """Manager node: delegates to workers."""
    logger.info(f"[Manager] Delegating to {state['num_workers']} workers")

    # Create worker agents
    workers = [FraudDetectionAgentLangGraph() for _ in range(state['num_workers'])]

    # Execute all workers in parallel
    tasks = [
        worker.analyze(state['transaction'], f"{state['transaction_id']}_worker_{i}")
        for i, worker in enumerate(workers)
    ]
    worker_results = await asyncio.gather(*tasks)

    state['worker_results'] = worker_results
    state['agent_results'] = {f"worker_{i}": r for i, r in enumerate(worker_results)}
    state['current_step'] = 'aggregate'

    return state


async def manager_aggregate_node(state: ManagerWorkerState) -> ManagerWorkerState:
    """Manager aggregates worker results."""
    logger.info("[Manager] Aggregating worker results")

    worker_results = state['worker_results']
    num_workers = state['num_workers']

    # Count fraud votes
    fraud_votes = sum(1 for r in worker_results if r.is_fraud)
    is_fraud = fraud_votes > (num_workers / 2)

    # Average metrics
    avg_risk = sum(r.risk_score for r in worker_results) / num_workers
    avg_confidence = sum(r.confidence for r in worker_results) / num_workers
    agreement = fraud_votes / num_workers if is_fraud else (num_workers - fraud_votes) / num_workers

    state['fraud_votes'] = fraud_votes
    state['is_fraud'] = is_fraud
    state['risk_score'] = avg_risk
    state['confidence'] = avg_confidence
    state['agreement_level'] = agreement
    state['explanation'] = f"Manager consensus: {fraud_votes}/{num_workers} workers detected fraud"
    state['consensus_strategy'] = ConsensusStrategy.MAJORITY_VOTE
    state['current_step'] = 'complete'

    return state


def create_manager_worker_graph(num_workers: int = 3) -> StateGraph:
    """Create Manager-Worker pattern graph."""
    graph = StateGraph(ManagerWorkerState)

    # Add nodes
    graph.add_node("delegate", manager_delegate_node)
    graph.add_node("aggregate", manager_aggregate_node)

    # Add edges
    graph.set_entry_point("delegate")
    graph.add_edge("delegate", "aggregate")
    graph.add_edge("aggregate", END)

    return graph.compile()


class ManagerWorkerSystemLangGraph:
    """Manager-Worker pattern using LangGraph StateGraph."""

    def __init__(self, num_workers: int = 3):
        """Initialize manager-worker system."""
        self.num_workers = num_workers
        self.graph = create_manager_worker_graph(num_workers)
        logger.info(f"[LangGraph] Initialized ManagerWorkerSystem with {num_workers} workers")

    async def analyze(
        self,
        transaction: Dict[str, Any],
        transaction_id: str,
    ) -> MultiAgentResult:
        """Analyze transaction using manager-worker pattern."""
        start_time = datetime.now()

        # Initialize state
        initial_state: ManagerWorkerState = {
            'transaction': transaction,
            'transaction_id': transaction_id,
            'num_workers': self.num_workers,
            'pattern_name': 'manager_worker',
            'start_time': start_time,
            'agent_results': {},
            'worker_results': [],
        }

        # Execute graph
        final_state = await self.graph.ainvoke(initial_state)

        # Calculate execution time
        execution_time = (datetime.now() - start_time).total_seconds()

        return MultiAgentResult(
            is_fraud=final_state['is_fraud'],
            risk_score=final_state['risk_score'],
            confidence=final_state['confidence'],
            explanation=final_state['explanation'],
            agent_results=final_state['agent_results'],
            consensus_strategy=final_state['consensus_strategy'],
            agreement_level=final_state['agreement_level'],
            total_time=execution_time,
            transaction_id=transaction_id,
        )


# ============================================================================
# Pattern 2: Planner-Executor-Critic System
# ============================================================================


async def planner_node(state: PECState) -> PECState:
    """Planner creates analysis strategy."""
    logger.info("[Planner] Creating analysis strategy")

    planner = FraudDetectionAgentLangGraph()
    result = await planner.analyze(state['transaction'], f"{state['transaction_id']}_planner")

    state['planner_result'] = result
    state['agent_results']['planner'] = result
    state['current_step'] = 'execute'

    return state


async def executor_node(state: PECState) -> PECState:
    """Executor performs detailed analysis."""
    logger.info("[Executor] Performing detailed analysis")

    executor = FraudDetectionAgentLangGraph()
    result = await executor.analyze(state['transaction'], f"{state['transaction_id']}_executor")

    state['executor_result'] = result
    state['agent_results']['executor'] = result
    state['current_step'] = 'critique'

    return state


async def critic_node(state: PECState) -> PECState:
    """Critic validates executor's result."""
    logger.info("[Critic] Validating results")

    critic = FraudDetectionAgentLangGraph()
    result = await critic.analyze(state['transaction'], f"{state['transaction_id']}_critic")

    state['critic_result'] = result
    state['agent_results']['critic'] = result
    state['current_step'] = 'decide'

    return state


async def pec_decision_node(state: PECState) -> PECState:
    """Make final decision based on executor and critic."""
    logger.info("[PEC] Making final decision")

    executor_result = state['executor_result']
    critic_result = state['critic_result']

    # Calculate disagreement
    disagreement = abs(executor_result.risk_score - critic_result.risk_score)
    state['disagreement_score'] = disagreement

    if disagreement > 30:
        # Major disagreement - use conservative estimate
        final_fraud = executor_result.is_fraud or critic_result.is_fraud
        final_risk = max(executor_result.risk_score, critic_result.risk_score)
        explanation = f"Executor and Critic disagree (Δ={disagreement:.1f}) - escalating"
        confidence = min(executor_result.confidence, critic_result.confidence) * 0.7
    else:
        # Agreement - use executor's result
        final_fraud = executor_result.is_fraud
        final_risk = executor_result.risk_score
        explanation = f"Planner-Executor-Critic consensus: fraud={final_fraud}"
        confidence = min(executor_result.confidence, critic_result.confidence)

    agreement = 1.0 - (disagreement / 100.0)

    state['is_fraud'] = final_fraud
    state['risk_score'] = final_risk
    state['confidence'] = confidence
    state['explanation'] = explanation
    state['agreement_level'] = agreement
    state['consensus_strategy'] = 'planner_executor_critic'
    state['current_step'] = 'complete'

    return state


def create_pec_graph() -> StateGraph:
    """Create Planner-Executor-Critic pattern graph."""
    graph = StateGraph(PECState)

    # Add nodes
    graph.add_node("planner", planner_node)
    graph.add_node("executor", executor_node)
    graph.add_node("critic", critic_node)
    graph.add_node("decide", pec_decision_node)

    # Add edges (sequential flow)
    graph.set_entry_point("planner")
    graph.add_edge("planner", "executor")
    graph.add_edge("executor", "critic")
    graph.add_edge("critic", "decide")
    graph.add_edge("decide", END)

    return graph.compile()


class PlannerExecutorCriticSystemLangGraph:
    """Planner-Executor-Critic pattern using LangGraph StateGraph."""

    def __init__(self):
        """Initialize PEC system."""
        self.graph = create_pec_graph()
        logger.info("[LangGraph] Initialized PlannerExecutorCriticSystem")

    async def analyze(
        self,
        transaction: Dict[str, Any],
        transaction_id: str,
    ) -> MultiAgentResult:
        """Analyze using planner-executor-critic pattern."""
        start_time = datetime.now()

        # Initialize state
        initial_state: PECState = {
            'transaction': transaction,
            'transaction_id': transaction_id,
            'pattern_name': 'planner_executor_critic',
            'start_time': start_time,
            'agent_results': {},
        }

        # Execute graph
        final_state = await self.graph.ainvoke(initial_state)

        # Calculate execution time
        execution_time = (datetime.now() - start_time).total_seconds()

        return MultiAgentResult(
            is_fraud=final_state['is_fraud'],
            risk_score=final_state['risk_score'],
            confidence=final_state['confidence'],
            explanation=final_state['explanation'],
            agent_results=final_state['agent_results'],
            consensus_strategy=final_state['consensus_strategy'],
            agreement_level=final_state['agreement_level'],
            total_time=execution_time,
            transaction_id=transaction_id,
        )


# ============================================================================
# Pattern 3: Debate System
# ============================================================================


async def debate_prosecution_node(state: DebateState) -> DebateState:
    """Prosecutor argues transaction IS fraud."""
    logger.info("[Prosecutor] Building case for fraud")

    prosecutor = FraudDetectionAgentLangGraph()
    result = await prosecutor.analyze(state['transaction'], f"{state['transaction_id']}_prosecutor")

    state['prosecutor_result'] = result
    state['agent_results']['prosecutor'] = result
    state['prosecutor_strength'] = result.risk_score * result.confidence

    return state


async def debate_defense_node(state: DebateState) -> DebateState:
    """Defense argues transaction is legitimate."""
    logger.info("[Defense] Building case for legitimacy")

    defense = FraudDetectionAgentLangGraph()
    result = await defense.analyze(state['transaction'], f"{state['transaction_id']}_defense")

    state['defense_result'] = result
    state['agent_results']['defense'] = result
    state['defense_strength'] = (100 - result.risk_score) * result.confidence

    return state


async def debate_judge_node(state: DebateState) -> DebateState:
    """Judge makes final ruling based on arguments."""
    logger.info("[Judge] Making final ruling")

    # Wait for both prosecutor and defense to complete
    # (In LangGraph, this happens via graph structure)

    judge = FraudDetectionAgentLangGraph()
    result = await judge.analyze(state['transaction'], f"{state['transaction_id']}_judge")

    state['judge_result'] = result
    state['agent_results']['judge'] = result
    state['current_step'] = 'verdict'

    return state


async def debate_verdict_node(state: DebateState) -> DebateState:
    """Make final verdict based on all arguments."""
    logger.info("[Debate] Reaching verdict")

    prosecutor_result = state['prosecutor_result']
    defense_result = state['defense_result']
    judge_result = state['judge_result']

    # Judge's ruling is primary
    final_fraud = judge_result.is_fraud
    final_risk = judge_result.risk_score

    # Adjust confidence based on debate agreement
    if prosecutor_result.is_fraud == defense_result.is_fraud:
        # Both sides agree - high confidence
        confidence = 0.95
        agreement = 1.0
        explanation = f"Unanimous: Both sides agree transaction is {'FRAUD' if final_fraud else 'LEGITIMATE'}"
    else:
        # Disagreement - moderate confidence
        confidence = judge_result.confidence * 0.8
        argument_gap = abs(state['prosecutor_strength'] - state['defense_strength'])
        agreement = max(0.5, 1.0 - (argument_gap / 100.0))
        explanation = (
            f"Judge ruled {'FRAUD' if final_fraud else 'LEGITIMATE'} "
            f"(Prosecutor: {prosecutor_result.risk_score:.1f}, "
            f"Defense: {defense_result.risk_score:.1f})"
        )

    state['is_fraud'] = final_fraud
    state['risk_score'] = final_risk
    state['confidence'] = confidence
    state['explanation'] = explanation
    state['agreement_level'] = agreement
    state['consensus_strategy'] = 'debate'
    state['current_step'] = 'complete'

    return state


async def debate_parallel_node(state: DebateState) -> DebateState:
    """Run prosecutor and defense in parallel."""
    logger.info("[Debate] Starting parallel arguments")

    # Execute prosecutor and defense in parallel using asyncio
    prosecutor = FraudDetectionAgentLangGraph()
    defense = FraudDetectionAgentLangGraph()

    prosecutor_task = prosecutor.analyze(state['transaction'], f"{state['transaction_id']}_prosecutor")
    defense_task = defense.analyze(state['transaction'], f"{state['transaction_id']}_defense")

    prosecutor_result, defense_result = await asyncio.gather(prosecutor_task, defense_task)

    state['prosecutor_result'] = prosecutor_result
    state['defense_result'] = defense_result
    state['agent_results']['prosecutor'] = prosecutor_result
    state['agent_results']['defense'] = defense_result
    state['prosecutor_strength'] = prosecutor_result.risk_score * prosecutor_result.confidence
    state['defense_strength'] = (100 - defense_result.risk_score) * defense_result.confidence
    state['current_step'] = 'judge'

    return state


def create_debate_graph() -> StateGraph:
    """Create Debate pattern graph."""
    graph = StateGraph(DebateState)

    # Add nodes
    graph.add_node("parallel_debate", debate_parallel_node)
    graph.add_node("judge", debate_judge_node)
    graph.add_node("verdict", debate_verdict_node)

    # Sequential flow with internal parallelism in parallel_debate node
    graph.set_entry_point("parallel_debate")
    graph.add_edge("parallel_debate", "judge")
    graph.add_edge("judge", "verdict")
    graph.add_edge("verdict", END)

    return graph.compile()


class DebateSystemLangGraph:
    """Debate pattern using LangGraph StateGraph."""

    def __init__(self):
        """Initialize debate system."""
        self.graph = create_debate_graph()
        logger.info("[LangGraph] Initialized DebateSystem")

    async def analyze(
        self,
        transaction: Dict[str, Any],
        transaction_id: str,
    ) -> MultiAgentResult:
        """Analyze using debate pattern."""
        start_time = datetime.now()

        # Initialize state
        initial_state: DebateState = {
            'transaction': transaction,
            'transaction_id': transaction_id,
            'pattern_name': 'debate',
            'start_time': start_time,
            'agent_results': {},
        }

        # Execute graph
        final_state = await self.graph.ainvoke(initial_state)

        # Calculate execution time
        execution_time = (datetime.now() - start_time).total_seconds()

        return MultiAgentResult(
            is_fraud=final_state['is_fraud'],
            risk_score=final_state['risk_score'],
            confidence=final_state['confidence'],
            explanation=final_state['explanation'],
            agent_results=final_state['agent_results'],
            consensus_strategy=final_state['consensus_strategy'],
            agreement_level=final_state['agreement_level'],
            total_time=execution_time,
            transaction_id=transaction_id,
        )


# ============================================================================
# Pattern 4: Role-Specialized System
# ============================================================================


async def specialist_analyst_node(state: RoleSpecializedState) -> RoleSpecializedState:
    """Transaction analyst examines transaction patterns."""
    logger.info("[Analyst] Analyzing transaction patterns")

    analyst = FraudDetectionAgentLangGraph()
    result = await analyst.analyze(state['transaction'], f"{state['transaction_id']}_analyst")

    state['analyst_result'] = result
    state['agent_results']['transaction_analyst'] = result

    return state


async def specialist_account_node(state: RoleSpecializedState) -> RoleSpecializedState:
    """Account specialist analyzes account history."""
    logger.info("[Account Specialist] Analyzing account history")

    specialist = FraudDetectionAgentLangGraph()
    result = await specialist.analyze(state['transaction'], f"{state['transaction_id']}_account")

    state['account_result'] = result
    state['agent_results']['account_specialist'] = result

    return state


async def specialist_policy_node(state: RoleSpecializedState) -> RoleSpecializedState:
    """Policy expert checks compliance."""
    logger.info("[Policy Expert] Checking compliance")

    expert = FraudDetectionAgentLangGraph()
    result = await expert.analyze(state['transaction'], f"{state['transaction_id']}_policy")

    state['policy_result'] = result
    state['agent_results']['policy_expert'] = result

    return state


async def specialist_consensus_node(state: RoleSpecializedState) -> RoleSpecializedState:
    """Aggregate specialist results with weighted voting."""
    logger.info("[Specialists] Reaching weighted consensus")

    analyst_result = state['analyst_result']
    account_result = state['account_result']
    policy_result = state['policy_result']

    # Weighted voting
    weights = state['specialist_weights']

    weighted_risk = (
        analyst_result.risk_score * weights['analyst'] +
        account_result.risk_score * weights['account'] +
        policy_result.risk_score * weights['policy']
    )

    # Consensus if >= 2 specialists agree
    fraud_votes = sum([
        analyst_result.is_fraud,
        account_result.is_fraud,
        policy_result.is_fraud,
    ])

    is_fraud = fraud_votes >= 2
    agreement = fraud_votes / 3.0 if is_fraud else (3 - fraud_votes) / 3.0

    state['fraud_votes'] = fraud_votes
    state['is_fraud'] = is_fraud
    state['risk_score'] = weighted_risk
    state['confidence'] = agreement
    state['explanation'] = f"Specialist consensus: {fraud_votes}/3 experts detected fraud (weighted risk: {weighted_risk:.1f})"
    state['agreement_level'] = agreement
    state['consensus_strategy'] = ConsensusStrategy.WEIGHTED_VOTE
    state['current_step'] = 'complete'

    return state


async def specialist_parallel_node(state: RoleSpecializedState) -> RoleSpecializedState:
    """Run all specialists in parallel."""
    logger.info("[Specialists] Analyzing in parallel")

    # Execute all specialists in parallel using asyncio
    analyst = FraudDetectionAgentLangGraph()
    account = FraudDetectionAgentLangGraph()
    policy = FraudDetectionAgentLangGraph()

    analyst_task = analyst.analyze(state['transaction'], f"{state['transaction_id']}_analyst")
    account_task = account.analyze(state['transaction'], f"{state['transaction_id']}_account")
    policy_task = policy.analyze(state['transaction'], f"{state['transaction_id']}_policy")

    analyst_result, account_result, policy_result = await asyncio.gather(
        analyst_task, account_task, policy_task
    )

    state['analyst_result'] = analyst_result
    state['account_result'] = account_result
    state['policy_result'] = policy_result
    state['agent_results']['transaction_analyst'] = analyst_result
    state['agent_results']['account_specialist'] = account_result
    state['agent_results']['policy_expert'] = policy_result
    state['current_step'] = 'consensus'

    return state


def create_role_specialized_graph() -> StateGraph:
    """Create Role-Specialized pattern graph."""
    graph = StateGraph(RoleSpecializedState)

    # Add nodes
    graph.add_node("parallel_specialists", specialist_parallel_node)
    graph.add_node("consensus", specialist_consensus_node)

    # Sequential flow with internal parallelism in parallel_specialists node
    graph.set_entry_point("parallel_specialists")
    graph.add_edge("parallel_specialists", "consensus")
    graph.add_edge("consensus", END)

    return graph.compile()


class RoleSpecializedSystemLangGraph:
    """Role-Specialized pattern using LangGraph StateGraph."""

    def __init__(self):
        """Initialize role-specialized system."""
        self.graph = create_role_specialized_graph()
        self.weights = {
            'analyst': 0.4,  # Transaction patterns most important
            'account': 0.3,  # Account history important
            'policy': 0.3,   # Policy compliance important
        }
        logger.info("[LangGraph] Initialized RoleSpecializedSystem")

    async def analyze(
        self,
        transaction: Dict[str, Any],
        transaction_id: str,
    ) -> MultiAgentResult:
        """Analyze using role-specialized pattern."""
        start_time = datetime.now()

        # Initialize state
        initial_state: RoleSpecializedState = {
            'transaction': transaction,
            'transaction_id': transaction_id,
            'pattern_name': 'role_specialized',
            'start_time': start_time,
            'agent_results': {},
            'specialist_weights': self.weights,
        }

        # Execute graph
        final_state = await self.graph.ainvoke(initial_state)

        # Calculate execution time
        execution_time = (datetime.now() - start_time).total_seconds()

        return MultiAgentResult(
            is_fraud=final_state['is_fraud'],
            risk_score=final_state['risk_score'],
            confidence=final_state['confidence'],
            explanation=final_state['explanation'],
            agent_results=final_state['agent_results'],
            consensus_strategy=final_state['consensus_strategy'],
            agreement_level=final_state['agreement_level'],
            total_time=execution_time,
            transaction_id=transaction_id,
        )


# ============================================================================
# Pattern 5: Swarm System
# ============================================================================


async def swarm_analyze_node(state: SwarmState) -> SwarmState:
    """All swarm agents analyze in parallel."""
    swarm_size = state['swarm_size']
    logger.info(f"[Swarm] {swarm_size} agents analyzing in parallel")

    # Create swarm agents
    agents = [FraudDetectionAgentLangGraph() for _ in range(swarm_size)]

    # Execute all agents in parallel
    tasks = [
        agent.analyze(state['transaction'], f"{state['transaction_id']}_swarm_{i}")
        for i, agent in enumerate(agents)
    ]
    results = await asyncio.gather(*tasks)

    state['swarm_results'] = results
    state['agent_results'] = {f"swarm_{i}": r for i, r in enumerate(results)}
    state['current_step'] = 'consensus'

    return state


async def swarm_consensus_node(state: SwarmState) -> SwarmState:
    """Aggregate swarm results with threshold-based consensus."""
    logger.info("[Swarm] Reaching consensus")

    results = state['swarm_results']
    swarm_size = state['swarm_size']
    consensus_threshold = state['consensus_threshold']

    # Count fraud votes
    fraud_votes = sum(1 for r in results if r.is_fraud)
    vote_fraction = fraud_votes / swarm_size

    # Determine consensus
    is_fraud = vote_fraction >= consensus_threshold

    # Average metrics
    avg_risk = sum(r.risk_score for r in results) / swarm_size
    avg_confidence = sum(r.confidence for r in results) / swarm_size

    # Agreement is how close to unanimous
    agreement = vote_fraction if is_fraud else (1.0 - vote_fraction)

    state['fraud_votes'] = fraud_votes
    state['vote_fraction'] = vote_fraction
    state['is_fraud'] = is_fraud
    state['risk_score'] = avg_risk
    state['confidence'] = avg_confidence
    state['explanation'] = f"Swarm consensus: {fraud_votes}/{swarm_size} agents detected fraud ({vote_fraction:.1%})"
    state['agreement_level'] = agreement
    state['consensus_strategy'] = ConsensusStrategy.THRESHOLD
    state['current_step'] = 'complete'

    return state


def create_swarm_graph() -> StateGraph:
    """Create Swarm pattern graph."""
    graph = StateGraph(SwarmState)

    # Add nodes
    graph.add_node("swarm_analyze", swarm_analyze_node)
    graph.add_node("consensus", swarm_consensus_node)

    # Add edges
    graph.set_entry_point("swarm_analyze")
    graph.add_edge("swarm_analyze", "consensus")
    graph.add_edge("consensus", END)

    return graph.compile()


class SwarmSystemLangGraph:
    """Swarm intelligence pattern using LangGraph StateGraph."""

    def __init__(self, swarm_size: int = 5, consensus_threshold: float = 0.6):
        """Initialize swarm system."""
        self.swarm_size = swarm_size
        self.consensus_threshold = consensus_threshold
        self.graph = create_swarm_graph()
        logger.info(f"[LangGraph] Initialized SwarmSystem with {swarm_size} agents")

    async def analyze(
        self,
        transaction: Dict[str, Any],
        transaction_id: str,
    ) -> MultiAgentResult:
        """Analyze using swarm pattern."""
        start_time = datetime.now()

        # Initialize state
        initial_state: SwarmState = {
            'transaction': transaction,
            'transaction_id': transaction_id,
            'pattern_name': 'swarm',
            'start_time': start_time,
            'agent_results': {},
            'swarm_size': self.swarm_size,
            'consensus_threshold': self.consensus_threshold,
            'swarm_results': [],
        }

        # Execute graph
        final_state = await self.graph.ainvoke(initial_state)

        # Calculate execution time
        execution_time = (datetime.now() - start_time).total_seconds()

        return MultiAgentResult(
            is_fraud=final_state['is_fraud'],
            risk_score=final_state['risk_score'],
            confidence=final_state['confidence'],
            explanation=final_state['explanation'],
            agent_results=final_state['agent_results'],
            consensus_strategy=final_state['consensus_strategy'],
            agreement_level=final_state['agreement_level'],
            total_time=execution_time,
            transaction_id=transaction_id,
        )


# ============================================================================
# Visualization Export
# ============================================================================


def export_pattern_diagrams(output_dir: str = "docs/diagrams"):
    """Export Mermaid diagrams for all patterns."""
    import os
    os.makedirs(output_dir, exist_ok=True)

    patterns = {
        'manager_worker': create_manager_worker_graph(3),
        'planner_executor_critic': create_pec_graph(),
        'debate': create_debate_graph(),
        'role_specialized': create_role_specialized_graph(),
        'swarm': create_swarm_graph(),
    }

    for pattern_name, graph in patterns.items():
        try:
            mermaid_code = graph.get_graph().draw_mermaid()
            output_file = os.path.join(output_dir, f"langgraph-{pattern_name}.mmd")

            with open(output_file, 'w') as f:
                f.write(mermaid_code)

            logger.info(f"✅ Exported {pattern_name} diagram to {output_file}")
        except Exception as e:
            logger.error(f"❌ Failed to export {pattern_name} diagram: {e}")

    logger.info(f"📊 Diagram export complete: {len(patterns)} patterns")
