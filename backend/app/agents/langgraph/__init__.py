"""
LangGraph-based agent implementations.

This package contains LangGraph StateGraph implementations of fraud detection agents,
providing a cleaner separation from the original custom implementations.

Phase 8.2: Single Agent LangGraph Migration
Phase 8.3: Multi-Agent LangGraph Migration
- Uses LangGraph 1.0.7 StateGraph for orchestration
- TypedDict state management (LangGraph standard)
- Maintains API compatibility with original implementation
"""

from app.agents.langgraph.single_agent import (
    FraudDetectionAgentLangGraph,
    AgentResult,
    FraudDetectionState,
)

from app.agents.langgraph.multi_agent import (
    # Multi-agent systems
    ManagerWorkerSystemLangGraph,
    PlannerExecutorCriticSystemLangGraph,
    DebateSystemLangGraph,
    RoleSpecializedSystemLangGraph,
    SwarmSystemLangGraph,

    # Shared models
    MultiAgentResult,
    AgentRole,
    ConsensusStrategy,

    # Visualization
    export_pattern_diagrams,
)

__all__ = [
    # Single agent
    "FraudDetectionAgentLangGraph",
    "AgentResult",
    "FraudDetectionState",

    # Multi-agent systems
    "ManagerWorkerSystemLangGraph",
    "PlannerExecutorCriticSystemLangGraph",
    "DebateSystemLangGraph",
    "RoleSpecializedSystemLangGraph",
    "SwarmSystemLangGraph",

    # Models
    "MultiAgentResult",
    "AgentRole",
    "ConsensusStrategy",

    # Utils
    "export_pattern_diagrams",
]
