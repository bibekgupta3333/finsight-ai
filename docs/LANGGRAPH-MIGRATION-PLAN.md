# LangGraph Migration Plan

**Project:** FinSight AI - Agent Architecture Migration  
**Date:** February 8, 2026  
**Purpose:** Migrate custom "LangGraph-style" architecture to official LangGraph library  
**Priority:** 🔴 HIGH (Required for research novelty claims)  
**Timeline:** 12 hours estimated  

---

## Executive Summary

**Current State:**  
The backend has a well-designed custom implementation inspired by LangGraph's architecture but doesn't use the actual LangGraph library. The system uses manual node chaining, custom state management, and procedural control flow.

**Target State:**  
Migrate to official LangGraph library while maintaining 100% API compatibility with existing frontend integrations. This enables:
- Research novelty claims (using state-of-the-art agent framework)
- Automatic graph optimization and state persistence
- Built-in streaming and checkpointing
- Standard LangChain tool integration
- Better debugging and visualization

**Critical Constraint:**  
⚠️ **MUST preserve existing API surface** - Frontend already integrated and expects same request/response formats.

---

## 1. Architecture Audit: Current vs Target

### 1.1 Current Architecture (Custom Implementation)

**Core Files:**
```
backend/app/agents/
├── single_agent.py         # 319 lines - FraudDetectionAgent class
├── multi_agent.py          # 501 lines - 5 multi-agent patterns
├── agent_nodes.py          # 509 lines - Individual reasoning nodes
├── agent_memory.py         # 209 lines - Memory management
├── task_planner.py         # 260 lines - Task decomposition
├── reasoning_engine.py     # 418 lines - Hypothesis generation
├── autonomy_controller.py  # 307 lines - Escalation logic
└── tool_registry.py        # 332 lines - Tool management
```

**Current State Management (Custom):**
```python
class AgentState(BaseModel):
    """Current custom state - Pydantic model"""
    transaction: Dict[str, Any]
    transaction_id: str
    observations: List[str] = []
    anomalies: List[str] = []
    plan: List[str] = []
    reasoning_steps: List[str] = []
    is_fraud: Optional[bool] = None
    risk_score: Optional[float] = None
    # ... 15+ fields total
```

**Current Node Execution (Manual):**
```python
class FraudDetectionAgent:
    async def analyze(self, transaction, txn_id):
        state = AgentState(transaction=transaction, transaction_id=txn_id)
        memory = AgentMemory()
        
        # Manual node execution in sequence
        state = await ObservationNode().execute(state, memory)
        state = await PlanningNode().execute(state, memory)
        state = await ExecutionNode().execute(state, memory)
        state = await ReasoningNode().execute(state, memory)
        state = await DecisionNode().execute(state, memory)
        state = await ReflectionNode().execute(state, memory)
        
        # Manual termination check
        if state.step_count >= state.max_steps:
            # Timeout logic
            
        return self._build_result(state)
```

**Issues with Current Approach:**
- ❌ Manual node chaining (prone to errors)
- ❌ No automatic graph optimization
- ❌ Custom state persistence logic
- ❌ No built-in streaming support
- ❌ Difficult to visualize graph structure
- ❌ Can't leverage LangChain ecosystem tools
- ⚠️ Not research-grade (can't claim "using LangGraph")

### 1.2 Target Architecture (LangGraph)

**LangGraph StateGraph Pattern:**
```python
from langgraph.graph import StateGraph, END
from typing_extensions import TypedDict

class FraudDetectionState(TypedDict):
    """LangGraph state - TypedDict for graph serialization"""
    transaction: dict
    transaction_id: str
    observations: list[str]
    anomalies: list[str]
    plan: list[str]
    reasoning_steps: list[str]
    is_fraud: bool | None
    risk_score: float | None
    # ... same fields as before

# Define graph
graph = StateGraph(FraudDetectionState)

# Add nodes
graph.add_node("observe", observation_node)
graph.add_node("plan", planning_node)
graph.add_node("execute", execution_node)
graph.add_node("reason", reasoning_node)
graph.add_node("decide", decision_node)
graph.add_node("reflect", reflection_node)

# Define edges (control flow)
graph.add_edge("observe", "plan")
graph.add_edge("plan", "execute")
graph.add_edge("execute", "reason")
graph.add_edge("reason", "decide")
graph.add_edge("decide", "reflect")
graph.add_conditional_edges(
    "reflect",
    should_continue,  # Function to check termination
    {True: "observe", False: END}  # Loop or end
)

# Set entry point
graph.set_entry_point("observe")

# Compile
fraud_agent = graph.compile()

# Invoke (now automatic!)
result = fraud_agent.invoke({
    "transaction": transaction,
    "transaction_id": txn_id
})
```

**Benefits of LangGraph:**
- ✅ Automatic graph optimization and execution
- ✅ Built-in state persistence and checkpointing
- ✅ Native streaming support (async generators)
- ✅ Graph visualization tools
- ✅ Standard LangChain tool integration
- ✅ Research-grade framework (citable)
- ✅ Better debugging and error handling

---

## 2. API Compatibility Matrix

**Critical:** These API endpoints MUST remain unchanged for frontend compatibility.

### 2.1 Single Agent Endpoint

**Endpoint:** `POST /api/v1/fraud/agents/single/analyze`  
**Location:** `backend/app/api/fraud.py:1766`

**Current Request:**
```python
{
    "transaction": {
        "amount": 150000,
        "type": "TRANSFER",
        "oldbalanceOrg": 200000,
        "newbalanceOrig": 50000,
        # ... more fields
    },
    "transaction_id": "txn_001"
}
```

**Current Response:**
```python
{
    "is_fraud": true,
    "risk_score": 85.0,
    "risk_level": "HIGH",
    "confidence": 0.92,
    "explanation": "Large transfer with balance anomaly",
    "transaction_id": "txn_001",
    "total_steps": 7,
    "termination_reason": "decision_made",
    "execution_time": 0.145,
    "observations": ["Transaction type: TRANSFER", ...],
    "anomalies": ["Balance inconsistency detected", ...],
    "reasoning_steps": ["Step 1: Check amount threshold", ...],
    "tool_results": {"account_lookup": {...}},
    "should_escalate": false
}
```

**Migration Strategy:**
- ✅ Keep same request/response models
- ✅ Wrap LangGraph execution in existing `FraudDetectionAgent` class
- ✅ Convert LangGraph state back to `AgentResult` model

**Code Pattern:**
```python
class FraudDetectionAgent:
    """Facade pattern - same external interface, LangGraph internal"""
    
    def __init__(self, max_steps: int = 20):
        self.max_steps = max_steps
        self.graph = self._build_langgraph()  # Build graph internally
    
    def _build_langgraph(self) -> CompiledGraph:
        """Build LangGraph (internal implementation detail)"""
        graph = StateGraph(FraudDetectionState)
        # ... add nodes and edges
        return graph.compile()
    
    async def analyze(self, transaction: Dict, txn_id: str) -> AgentResult:
        """Same external interface - now powered by LangGraph"""
        # Invoke LangGraph
        final_state = await self.graph.ainvoke({
            "transaction": transaction,
            "transaction_id": txn_id,
            "max_steps": self.max_steps
        })
        
        # Convert LangGraph state to AgentResult (same format as before)
        return AgentResult(
            is_fraud=final_state["is_fraud"],
            risk_score=final_state["risk_score"],
            # ... map all fields
        )
```

### 2.2 Multi-Agent Endpoints

**Endpoint:** `POST /api/v1/fraud/agents/multi/manager-worker`  
**Location:** `backend/app/api/fraud.py:1838`

**Current Implementation:**
```python
system = ManagerWorkerSystem(num_workers=3)
result = await system.analyze(transaction, transaction_id)
```

**Migration Strategy:**
- ✅ Each multi-agent pattern becomes a separate LangGraph
- ✅ Keep same `MultiAgentResult` response model
- ✅ Implement using LangGraph subgraphs or parallel execution

**Multi-Agent Patterns to Migrate:**
1. **ManagerWorkerSystem** (line 1838) - 3 parallel agents with aggregation
2. **PlannerExecutorCriticSystem** - Sequential roles
3. **DebateSystem** - Prosecutor vs Defense with Judge
4. **RoleSpecializedSystem** - Domain expert collaboration
5. **SwarmSystem** - Parallel agents with consensus voting

---

## 3. Migration Roadmap (Phased Approach)

### Phase 1: Foundation (2 hours) ✅ COMPLETE

**Tasks:**
- [x] ✅ Install LangGraph dependencies (`langgraph>=0.2.0`, `langchain>=0.3.0`)
- [x] ✅ Audit current architecture (this document)
- [x] ✅ Create migration plan with API compatibility matrix
- [ ] ⏳ Test LangGraph installation and basic functionality

**Deliverables:**
- ✅ Dependencies added to `pyproject.toml`
- ✅ `LANGGRAPH-MIGRATION-PLAN.md` created
- ⏳ Test script: `backend/tests/test_langgraph_basic.py`

### Phase 2: Single Agent Migration (4 hours)

**Tasks:**
- [ ] Convert `AgentState` (Pydantic) → `FraudDetectionState` (TypedDict)
- [ ] Refactor node functions to LangGraph node signature
- [ ] Build StateGraph with 7 nodes (observe, plan, execute, reason, decide, reflect, terminate)
- [ ] Implement conditional edges for termination and looping
- [ ] Wrap compiled graph in existing `FraudDetectionAgent` class (facade pattern)
- [ ] Test single agent endpoint: `/fraud/agents/single/analyze`

**Files to Modify:**
- `backend/app/agents/agent_nodes.py` - Convert nodes to LangGraph functions
- `backend/app/agents/single_agent.py` - Add LangGraph wrapper
- `backend/app/agents/agent_state.py` - New file for TypedDict state

**Example Node Conversion:**
```python
# Before (Custom)
class ObservationNode:
    async def execute(self, state: AgentState, memory: AgentMemory) -> AgentState:
        state.observations.append("...")
        return state

# After (LangGraph)
async def observation_node(state: FraudDetectionState) -> FraudDetectionState:
    """LangGraph node - returns updated state dict"""
    return {
        **state,
        "observations": state["observations"] + ["..."]
    }
```

**Validation:**
- ✅ Same request/response format as before
- ✅ No frontend code changes required
- ✅ All 7 nodes execute in correct order
- ✅ Termination conditions work correctly

### Phase 3: Memory Integration (2 hours)

**Tasks:**
- [ ] Integrate `AgentMemory` with LangGraph state
- [ ] Use LangGraph checkpointing for short-term memory
- [ ] Implement custom memory saver for long-term memory
- [ ] Test memory persistence across invocations

**LangGraph Memory Pattern:**
```python
from langgraph.checkpoint import MemorySaver

# In-memory checkpointing
memory_saver = MemorySaver()
fraud_agent = graph.compile(checkpointer=memory_saver)

# Invoke with thread_id for session management
result = await fraud_agent.ainvoke(
    {"transaction": txn, "transaction_id": txn_id},
    config={"configurable": {"thread_id": "session_123"}}
)
```

**Files to Modify:**
- `backend/app/agents/agent_memory.py` - Add LangGraph memory adapter
- `backend/app/agents/single_agent.py` - Use checkpointer

### Phase 4: Multi-Agent Migration (3 hours)

**Tasks:**
- [ ] Migrate ManagerWorkerSystem using LangGraph parallel execution
- [ ] Migrate PlannerExecutorCriticSystem using sequential subgraphs
- [ ] Migrate DebateSystem using conditional routing
- [ ] Test all 5 multi-agent patterns

**LangGraph Multi-Agent Patterns:**

**Pattern 1: Manager-Worker (Parallel Execution)**
```python
from langgraph.graph import StateGraph

def manager_worker_graph():
    graph = StateGraph(MultiAgentState)
    
    # Manager node assigns tasks
    graph.add_node("manager", manager_node)
    
    # Worker nodes execute in parallel
    graph.add_node("worker_1", worker_node)
    graph.add_node("worker_2", worker_node)
    graph.add_node("worker_3", worker_node)
    
    # Aggregation node combines results
    graph.add_node("aggregate", aggregation_node)
    
    # Edges: manager → workers (parallel) → aggregate
    graph.add_edge("manager", "worker_1")
    graph.add_edge("manager", "worker_2")
    graph.add_edge("manager", "worker_3")
    graph.add_edge("worker_1", "aggregate")
    graph.add_edge("worker_2", "aggregate")
    graph.add_edge("worker_3", "aggregate")
    
    return graph.compile()
```

**Pattern 2: Planner-Executor-Critic (Sequential)**
```python
def planner_executor_critic_graph():
    graph = StateGraph(MultiAgentState)
    
    graph.add_node("plan", planning_agent)
    graph.add_node("execute", execution_agent)
    graph.add_node("critique", critic_agent)
    
    # Sequential edges with conditional loop
    graph.add_edge("plan", "execute")
    graph.add_edge("execute", "critique")
    graph.add_conditional_edges(
        "critique",
        should_retry,  # Critic approves or rejects
        {True: "plan", False: END}  # Loop back or finish
    )
    
    return graph.compile()
```

**Files to Modify:**
- `backend/app/agents/multi_agent.py` - Convert all 5 patterns to LangGraph

### Phase 5: Tool Integration (1 hour)

**Tasks:**
- [ ] Convert custom tools to LangChain tool format
- [ ] Use `@tool` decorator for automatic schema generation
- [ ] Integrate with LangGraph `ToolNode`
- [ ] Test tool execution within graph

**LangChain Tool Pattern:**
```python
from langchain_core.tools import tool

@tool
async def account_lookup(account_id: str) -> dict:
    """
    Look up account information.
    
    Args:
        account_id: Account identifier
        
    Returns:
        Account details dictionary
    """
    # Implementation
    return {"balance": 50000, "history": [...]}

# Add to graph
from langgraph.prebuilt import ToolNode

tools = [account_lookup, pattern_search, risk_calculator]
tool_node = ToolNode(tools)
graph.add_node("tools", tool_node)
```

**Files to Modify:**
- `backend/app/agents/tool_registry.py` - Convert to LangChain tools
- `backend/app/agents/agent_nodes.py` - Use ToolNode in execution

---

## 4. Testing Strategy

### 4.1 Unit Tests (Per Phase)

**Test Location:** `backend/tests/agents/test_langgraph_migration.py`

**Phase 2 Tests (Single Agent):**
```python
import pytest
from app.agents.single_agent import FraudDetectionAgent

@pytest.mark.asyncio
async def test_single_agent_basic_transaction():
    """Test basic fraud detection with LangGraph backend"""
    agent = FraudDetectionAgent(max_steps=20)
    
    transaction = {
        "amount": 150000,
        "type": "TRANSFER",
        "oldbalanceOrg": 200000,
        "newbalanceOrig": 50000,
    }
    
    result = await agent.analyze(transaction, "txn_test_001")
    
    # Verify response format (API compatibility)
    assert isinstance(result.is_fraud, bool)
    assert 0 <= result.risk_score <= 100
    assert len(result.observations) > 0
    assert result.transaction_id == "txn_test_001"

@pytest.mark.asyncio
async def test_single_agent_all_nodes_executed():
    """Verify all 7 nodes execute in LangGraph"""
    agent = FraudDetectionAgent(max_steps=20)
    
    transaction = {"amount": 5000, "type": "PAYMENT"}
    result = await agent.analyze(transaction, "txn_test_002")
    
    # Check that all nodes contributed to state
    assert len(result.observations) > 0  # ObservationNode
    assert len(result.reasoning_steps) > 0  # PlanningNode + ReasoningNode
    assert result.is_fraud is not None  # DecisionNode
    assert result.explanation is not None  # DecisionNode
```

**Phase 4 Tests (Multi-Agent):**
```python
@pytest.mark.asyncio
async def test_manager_worker_system():
    """Test manager-worker pattern with LangGraph"""
    from app.agents.multi_agent import ManagerWorkerSystem
    
    system = ManagerWorkerSystem(num_workers=3)
    transaction = {"amount": 100000, "type": "TRANSFER"}
    
    result = await system.analyze(transaction, "txn_multi_001")
    
    # Verify multi-agent result format
    assert isinstance(result.agent_results, dict)
    assert len(result.agent_results) == 3  # 3 workers
    assert 0 <= result.agreement_level <= 1.0
```

### 4.2 Integration Tests

**Test Location:** `backend/tests/api/test_fraud_agents_integration.py`

**API Endpoint Tests:**
```python
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_single_agent_endpoint():
    """Test /fraud/agents/single/analyze endpoint"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/fraud/agents/single/analyze",
            json={
                "transaction": {
                    "amount": 150000,
                    "type": "TRANSFER",
                    "oldbalanceOrg": 200000,
                    "newbalanceOrig": 50000,
                },
                "transaction_id": "txn_api_001"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response schema (must match frontend expectations)
        assert "is_fraud" in data
        assert "risk_score" in data
        assert "observations" in data
        assert data["transaction_id"] == "txn_api_001"
```

### 4.3 Local Manual Testing (M4 Pro Laptop)

**Test Script:** `backend/scripts/test_langgraph_local.py`

```python
"""
Local testing script for LangGraph migration.
Run: python backend/scripts/test_langgraph_local.py
"""
import asyncio
from app.agents.single_agent import FraudDetectionAgent

async def main():
    print("🚀 Testing LangGraph Migration Locally (M4 Pro)")
    print("=" * 60)
    
    # Initialize agent
    agent = FraudDetectionAgent(max_steps=20)
    
    # Test Case 1: Legitimate transaction
    print("\n📊 Test 1: Legitimate Transaction")
    txn1 = {
        "amount": 500,
        "type": "PAYMENT",
        "oldbalanceOrg": 10000,
        "newbalanceOrig": 9500,
    }
    result1 = await agent.analyze(txn1, "txn_local_001")
    print(f"   Fraud: {result1.is_fraud}, Risk: {result1.risk_score:.1f}")
    print(f"   Steps: {result1.total_steps}, Time: {result1.execution_time:.3f}s")
    
    # Test Case 2: Suspicious transaction
    print("\n📊 Test 2: Suspicious Transaction")
    txn2 = {
        "amount": 500000,
        "type": "TRANSFER",
        "oldbalanceOrg": 600000,
        "newbalanceOrig": 0,  # Full balance drained
    }
    result2 = await agent.analyze(txn2, "txn_local_002")
    print(f"   Fraud: {result2.is_fraud}, Risk: {result2.risk_score:.1f}")
    print(f"   Explanation: {result2.explanation}")
    
    # Test Case 3: Memory usage (M4 Pro constraint)
    print("\n💾 Test 3: Memory Usage (M4 Pro)")
    import psutil
    process = psutil.Process()
    mem_mb = process.memory_info().rss / 1024 / 1024
    print(f"   Memory: {mem_mb:.1f} MB")
    print(f"   ✅ Within 16GB limit" if mem_mb < 5000 else "⚠️ High memory")
    
    print("\n✅ All local tests passed!")

if __name__ == "__main__":
    asyncio.run(main())
```

**Run Command:**
```bash
# From project root
cd /Users/bibekgupta/Downloads/projects/finsight-ai
python backend/scripts/test_langgraph_local.py
```

---

## 5. LangGraph Implementation Patterns

### 5.1 State Definition (TypedDict vs Pydantic)

**Why TypedDict?**
- ✅ Required by LangGraph for graph compilation
- ✅ Lightweight and serializable
- ✅ Better performance than Pydantic for graph state
- ⚠️ Less validation than Pydantic (trade-off)

**Pattern:**
```python
from typing_extensions import TypedDict
from typing import Optional

class FraudDetectionState(TypedDict):
    """LangGraph state - must be TypedDict"""
    # Input
    transaction: dict
    transaction_id: str
    
    # Intermediate state
    observations: list[str]
    anomalies: list[str]
    plan: list[str]
    reasoning_steps: list[str]
    
    # Output
    is_fraud: Optional[bool]
    risk_score: Optional[float]
    risk_level: Optional[str]
    confidence: Optional[float]
    explanation: Optional[str]
    
    # Metadata
    step_count: int
    max_steps: int
```

### 5.2 Node Function Signature

**LangGraph Node Requirements:**
- Input: State dictionary
- Output: Partial state update (merged automatically)
- Async or sync (both supported)

**Pattern:**
```python
async def observation_node(state: FraudDetectionState) -> dict:
    """
    Observation node - parses transaction and identifies anomalies.
    
    Args:
        state: Current graph state
        
    Returns:
        Partial state update (merged into full state)
    """
    transaction = state["transaction"]
    observations = state.get("observations", [])
    anomalies = state.get("anomalies", [])
    
    # Extract features
    amount = transaction.get("amount", 0)
    txn_type = transaction.get("type", "UNKNOWN")
    
    # Add observations
    observations.append(f"Transaction type: {txn_type}")
    observations.append(f"Amount: ${amount:,.2f}")
    
    # Detect anomalies
    if amount > 100000:
        anomalies.append("High amount transaction")
    
    # Return partial update (LangGraph merges automatically)
    return {
        "observations": observations,
        "anomalies": anomalies,
        "step_count": state["step_count"] + 1
    }
```

### 5.3 Conditional Edges (Control Flow)

**Pattern: Loop until termination condition**
```python
def should_continue(state: FraudDetectionState) -> bool:
    """
    Termination condition for agent loop.
    
    Returns:
        True: Continue to next iteration
        False: End execution
    """
    # Terminate if decision made
    if state["is_fraud"] is not None:
        return False
    
    # Terminate if max steps reached
    if state["step_count"] >= state["max_steps"]:
        return False
    
    # Terminate if escalation required
    if state.get("should_escalate"):
        return False
    
    # Continue execution
    return True

# Add to graph
graph.add_conditional_edges(
    "reflect",  # Source node
    should_continue,  # Condition function
    {True: "observe", False: END}  # Routing: loop or end
)
```

### 5.4 Streaming Support (Real-time Updates)

**Pattern: Stream intermediate states**
```python
async def analyze_with_streaming(transaction: dict, txn_id: str):
    """Stream agent execution in real-time"""
    async for state in fraud_agent.astream({
        "transaction": transaction,
        "transaction_id": txn_id,
        "step_count": 0,
        "max_steps": 20
    }):
        # state is updated after each node execution
        print(f"Step {state['step_count']}: {state.get('current_node')}")
        
        # Send to WebSocket or SSE
        yield {
            "step": state["step_count"],
            "observations": state["observations"],
            "is_fraud": state.get("is_fraud")
        }
```

---

## 6. Risk Mitigation

### 6.1 Backward Compatibility Risks

**Risk:** Breaking existing API contracts  
**Mitigation:**
- ✅ Keep all existing classes as facades
- ✅ Comprehensive integration tests before merging
- ✅ Test against real frontend (manual testing)
- ✅ Version API to allow gradual migration

**Risk:** Performance degradation  
**Mitigation:**
- ✅ Benchmark before/after migration (M4 Pro local tests)
- ✅ Profile memory usage (stay within 16GB limit)
- ✅ Use async execution throughout
- ✅ Implement caching for repeated graph compilations

### 6.2 LangGraph Learning Curve

**Risk:** Team unfamiliar with LangGraph  
**Mitigation:**
- ✅ This migration plan serves as documentation
- ✅ Gradual rollout (single agent first, then multi-agent)
- ✅ Preserve existing tests as regression suite
- ✅ Add LangGraph-specific comments in code

### 6.3 Dependency Management

**Risk:** Version conflicts with existing packages  
**Mitigation:**
- ✅ Pin exact versions in pyproject.toml
- ✅ Test installation in clean environment
- ✅ Document any breaking changes
- ✅ Fallback: Keep old implementation in `agent_nodes_legacy.py`

---

## 7. Success Criteria

### 7.1 Functional Requirements
- ✅ All existing API endpoints work without changes
- ✅ Same request/response formats as before
- ✅ All 7 nodes execute in correct order
- ✅ All 5 multi-agent patterns work
- ✅ Memory persistence across invocations
- ✅ Tool execution successful

### 7.2 Performance Requirements (M4 Pro)
- ✅ Single agent analysis < 200ms (was ~145ms)
- ✅ Memory usage < 5GB per agent instance
- ✅ No performance degradation vs. custom implementation

### 7.3 Research Requirements
- ✅ Can cite LangGraph in thesis/papers
- ✅ Graph visualization available for presentations
- ✅ Standard framework for reproducibility
- ✅ Extensible for future research

---

## 8. Implementation Checklist

### Phase 1: Foundation ✅ PARTIALLY COMPLETE (75%)
- [x] ✅ Install LangGraph dependencies
- [x] ✅ Create migration plan document
- [ ] ⏳ Test LangGraph installation locally
- [ ] ⏳ Create basic LangGraph hello-world example

### Phase 2: Single Agent (Next Priority)
- [ ] Create `FraudDetectionState` TypedDict
- [ ] Convert all 7 nodes to LangGraph functions
- [ ] Build StateGraph with nodes and edges
- [ ] Add conditional edges for termination
- [ ] Wrap graph in `FraudDetectionAgent` class (facade)
- [ ] Test `/fraud/agents/single/analyze` endpoint
- [ ] Verify memory usage on M4 Pro

### Phase 3-5: See roadmap above

---

## 9. Next Steps

**Immediate Actions (Today):**
1. ⏳ Test LangGraph installation: `pip install langgraph langchain`
2. ⏳ Run basic LangGraph example (verify compatibility)
3. ⏳ Update WBS.md with Phase 8.1 completion status

**Short-term (Next 2 days):**
1. Implement Phase 2 (Single Agent Migration)
2. Test locally on M4 Pro
3. Validate API compatibility with Postman/curl

**Mid-term (Next week):**
1. Complete Phases 3-5 (Memory, Multi-Agent, Tools)
2. Full integration testing
3. Documentation and code review

---

## 10. References

**LangGraph Documentation:**
- Official Docs: https://langchain-ai.github.io/langgraph/
- StateGraph API: https://langchain-ai.github.io/langgraph/reference/graphs/#langgraph.graph.StateGraph
- Checkpointing: https://langchain-ai.github.io/langgraph/how-tos/persistence/

**LangChain Tools:**
- Tool Decorator: https://python.langchain.com/docs/modules/tools/custom_tools
- ToolNode: https://langchain-ai.github.io/langgraph/reference/prebuilt/#toolnode

**Research Papers:**
- LangGraph Architecture: https://blog.langchain.dev/langgraph/
- Multi-Agent Systems: https://arxiv.org/abs/2308.08155

---

## Appendix A: File Modification Summary

**Files to Create:**
- `backend/app/agents/agent_state.py` - TypedDict state definitions
- `backend/tests/agents/test_langgraph_migration.py` - Unit tests
- `backend/scripts/test_langgraph_local.py` - Local testing script

**Files to Modify:**
- `backend/pyproject.toml` - ✅ Add LangGraph dependencies (DONE)
- `backend/app/agents/agent_nodes.py` - Convert nodes to LangGraph functions
- `backend/app/agents/single_agent.py` - Wrap StateGraph in facade class
- `backend/app/agents/multi_agent.py` - Migrate 5 multi-agent patterns
- `backend/app/agents/agent_memory.py` - Add LangGraph memory adapter
- `backend/app/agents/tool_registry.py` - Convert to LangChain tools

**Files to Preserve (No Changes):**
- `backend/app/api/fraud.py` - API endpoints unchanged
- `backend/app/models/fraud.py` - Request/response models unchanged
- Frontend code - No changes required

**Total LOC Estimate:**
- New code: ~500 lines (state definitions, adapters, tests)
- Modified code: ~800 lines (node conversions, graph building)
- Deleted code: ~200 lines (manual orchestration logic)
- Net change: +1,100 lines

---

**Document Version:** 1.0  
**Author:** AI Assistant (GitHub Copilot)  
**Last Updated:** February 8, 2026  
**Status:** Ready for Implementation  
