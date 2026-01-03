"""
Single-Agent Architecture for Fraud Detection.

Implements complete agent lifecycle:
- Observation: Parse transaction and identify anomalies
- Planning: Task decomposition and sequencing
- Execution: Tool calls with error handling
- Memory: Multi-tier state management
- Reflection: Self-critique and escalation
- Termination: Success/failure/timeout conditions
"""

from typing import Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel
import logging

from app.agents.agent_memory import AgentMemory, MemoryType
from app.agents.tool_registry import get_tool_registry
from app.agents.agent_nodes import (
    AgentState,
    ObservationNode,
    PlanningNode,
    ExecutionNode,
    ReasoningNode,
    DecisionNode,
    ReflectionNode,
    TerminationNode,
)

logger = logging.getLogger(__name__)


class AgentResult(BaseModel):
    """
    Final result from agent execution.
    """
    
    # Decision
    is_fraud: bool
    risk_score: float
    risk_level: str
    confidence: float
    explanation: str
    
    # Metadata
    transaction_id: str
    total_steps: int
    termination_reason: str
    execution_time: float
    
    # Transparency
    observations: list[str]
    anomalies: list[str]
    reasoning_steps: list[str]
    tool_results: Dict[str, Any]
    
    # Escalation
    should_escalate: bool
    escalation_reason: Optional[str] = None
    self_critique: Optional[str] = None


class FraudDetectionAgent:
    """
    Single-agent fraud detection system.
    
    Follows LangGraph-style node-based architecture with:
    1. Observation → Parse transaction features
    2. Planning → Decompose into tasks
    3. Execution → Execute tools
    4. Reasoning → Chain-of-thought analysis
    5. Decision → Make final determination
    6. Reflection → Self-critique and escalation
    7. Termination → Check stopping conditions
    
    Example:
        ```python
        agent = FraudDetectionAgent(max_steps=20)
        
        transaction = {
            "amount": 150000,
            "type": "TRANSFER",
            "oldbalanceOrg": 200000,
            "newbalanceOrig": 50000,
            "nameOrig": "C123456789",
            "nameDest": "D987654321",
        }
        
        result = await agent.analyze(transaction, "txn_001")
        print(f"Fraud: {result.is_fraud}, Risk: {result.risk_score}")
        ```
    """
    
    def __init__(self, max_steps: int = 20):
        """
        Initialize fraud detection agent.
        
        Args:
            max_steps: Maximum reasoning steps before timeout
        """
        self.max_steps = max_steps
        self.memory = AgentMemory()
        
        # Initialize nodes
        self.observation_node = ObservationNode()
        self.planning_node = PlanningNode()
        self.execution_node = ExecutionNode()
        self.reasoning_node = ReasoningNode()
        self.decision_node = DecisionNode()
        self.reflection_node = ReflectionNode()
        self.termination_node = TerminationNode()
        
        logger.info(f"Initialized FraudDetectionAgent (max_steps={max_steps})")
    
    async def analyze(
        self,
        transaction: Dict[str, Any],
        transaction_id: str,
    ) -> AgentResult:
        """
        Analyze transaction for fraud using agent reasoning loop.
        
        This implements the core agent loop:
        1. Observe → 2. Plan → 3. Execute → 4. Reason → 5. Decide → 6. Reflect → 7. Terminate
        
        Args:
            transaction: Transaction data
            transaction_id: Unique transaction identifier
        
        Returns:
            AgentResult with fraud determination and reasoning trace
        
        Raises:
            ValueError: If transaction is invalid
        """
        start_time = datetime.now()
        
        # Validate input
        if not transaction:
            raise ValueError("Transaction cannot be empty")
        
        if not transaction_id:
            raise ValueError("Transaction ID is required")
        
        logger.info(f"Starting analysis for transaction {transaction_id}")
        
        # Initialize state
        state = AgentState(
            transaction=transaction,
            transaction_id=transaction_id,
            max_steps=self.max_steps,
            start_time=start_time,
        )
        
        # Clear memory for fresh analysis
        self.memory.clear()
        
        try:
            # Execute agent loop
            state = await self._agent_loop(state)
            
            # Calculate execution time
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # Check termination reason
            _, termination_reason = self.termination_node.should_terminate(state)
            
            # Build result
            result = AgentResult(
                # Decision
                is_fraud=state.is_fraud if state.is_fraud is not None else False,
                risk_score=state.risk_score or 0.0,
                risk_level=state.risk_level or "UNKNOWN",
                confidence=state.confidence,
                explanation=state.explanation or "Analysis incomplete",
                # Metadata
                transaction_id=transaction_id,
                total_steps=state.step_count,
                termination_reason=termination_reason,
                execution_time=execution_time,
                # Transparency
                observations=state.observations,
                anomalies=state.anomalies,
                reasoning_steps=state.reasoning_steps,
                tool_results=state.tool_results,
                # Escalation
                should_escalate=state.should_escalate,
                escalation_reason=state.escalation_reason,
                self_critique=state.self_critique,
            )
            
            # Store result in long-term memory for future reference
            self.memory.store(
                f"result_{transaction_id}",
                result.dict(),
                MemoryType.LONG_TERM,
                metadata={"timestamp": datetime.now().isoformat()},
            )
            
            logger.info(
                f"Analysis complete: fraud={result.is_fraud}, "
                f"risk={result.risk_score:.1f}, steps={result.total_steps}, "
                f"time={execution_time:.2f}s"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Agent execution failed: {e}", exc_info=True)
            
            # Return safe default
            execution_time = (datetime.now() - start_time).total_seconds()
            return AgentResult(
                is_fraud=False,
                risk_score=0.0,
                risk_level="ERROR",
                confidence=0.0,
                explanation=f"Agent execution failed: {str(e)}",
                transaction_id=transaction_id,
                total_steps=state.step_count,
                termination_reason="error",
                execution_time=execution_time,
                observations=state.observations,
                anomalies=state.anomalies,
                reasoning_steps=state.reasoning_steps,
                tool_results=state.tool_results,
                should_escalate=True,
                escalation_reason=f"Agent error: {str(e)}",
                self_critique="Execution failed",
            )
    
    async def _agent_loop(self, state: AgentState) -> AgentState:
        """
        Main agent reasoning loop.
        
        Executes nodes in sequence until termination condition is met.
        
        Args:
            state: Current agent state
        
        Returns:
            Final agent state
        """
        # Node execution order (LangGraph-style graph)
        while True:
            # Check termination before each step
            should_stop, reason = self.termination_node.should_terminate(state)
            if should_stop:
                logger.info(f"Agent terminated: {reason}")
                break
            
            # Execute node pipeline
            try:
                # 1. Observation
                if state.step_count == 0:
                    state = await self.observation_node.execute(state, self.memory)
                    logger.debug(f"Observation complete: {len(state.observations)} observations")
                
                # 2. Planning
                if state.step_count == 1:
                    state = await self.planning_node.execute(state, self.memory)
                    logger.debug(f"Planning complete: {len(state.plan)} steps")
                
                # 3. Execution
                if state.step_count == 2:
                    state = await self.execution_node.execute(state, self.memory)
                    logger.debug(f"Execution complete: {len(state.tool_results)} results")
                
                # 4. Reasoning
                if state.step_count == 3:
                    state = await self.reasoning_node.execute(state, self.memory)
                    logger.debug(f"Reasoning complete: {len(state.reasoning_steps)} steps")
                
                # 5. Decision
                if state.step_count == 4:
                    state = await self.decision_node.execute(state, self.memory)
                    logger.debug(f"Decision complete: fraud={state.is_fraud}")
                
                # 6. Reflection
                if state.step_count == 5:
                    state = await self.reflection_node.execute(state, self.memory)
                    logger.debug(f"Reflection complete: escalate={state.should_escalate}")
                    # After reflection, we're done
                    break
                
            except Exception as e:
                logger.error(f"Node execution error at step {state.step_count}: {e}")
                state.execution_errors.append(str(e))
                # Don't break - let termination logic handle it
        
        return state
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """
        Get current memory statistics.
        
        Returns:
            Memory usage statistics
        """
        return self.memory.get_stats()
    
    def get_memory_contents(self, memory_type: Optional[MemoryType] = None) -> list:
        """
        Get memory contents for inspection.
        
        Args:
            memory_type: Type of memory to retrieve (None for all)
        
        Returns:
            List of memory entries
        """
        return self.memory.list_memories(memory_type)
    
    def reset_memory(self):
        """Reset all agent memory."""
        self.memory.clear()
        logger.info("Agent memory reset")
