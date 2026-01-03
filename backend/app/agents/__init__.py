"""
Agent implementations for fraud detection.

This package implements agentic reasoning patterns with observation,
planning, execution, memory, reflection, and termination logic.
"""

from app.agents.single_agent import FraudDetectionAgent, AgentResult
from app.agents.agent_memory import AgentMemory, MemoryType
from app.agents.tool_registry import ToolRegistry, get_tool_registry
from app.agents.multi_agent import (
    ManagerWorkerSystem,
    PlannerExecutorCriticSystem,
    DebateSystem,
    RoleSpecializedSystem,
    SwarmSystem,
    MultiAgentResult,
)

__all__ = [
    # Single Agent
    "FraudDetectionAgent",
    "AgentResult",
    # Memory
    "AgentMemory",
    "MemoryType",
    # Tools
    "ToolRegistry",
    "get_tool_registry",
    # Multi-Agent
    "ManagerWorkerSystem",
    "PlannerExecutorCriticSystem",
    "DebateSystem",
    "RoleSpecializedSystem",
    "SwarmSystem",
    "MultiAgentResult",
]
