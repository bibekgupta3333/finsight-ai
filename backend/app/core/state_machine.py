"""
Finite State Machine for Agent States.

Implements state transitions for fraud detection agent:
IDLE → ANALYZING → REASONING → DECIDING → EXPLAINING → COMPLETE
"""

import logging
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class AgentState(str, Enum):
    """Agent states for fraud detection workflow."""

    IDLE = "IDLE"
    ANALYZING = "ANALYZING"
    REASONING = "REASONING"
    DECIDING = "DECIDING"
    EXPLAINING = "EXPLAINING"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class StateTransition(BaseModel):
    """State transition record."""

    from_state: AgentState
    to_state: AgentState
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict = Field(default_factory=dict)
    reason: Optional[str] = None


class StateMachine:
    """
    Finite State Machine for agent workflow.

    Enforces valid state transitions and maintains transition history.
    """

    # Valid state transitions
    TRANSITIONS: Dict[AgentState, List[AgentState]] = {
        AgentState.IDLE: [AgentState.ANALYZING, AgentState.CANCELLED],
        AgentState.ANALYZING: [
            AgentState.REASONING,
            AgentState.FAILED,
            AgentState.CANCELLED,
        ],
        AgentState.REASONING: [
            AgentState.DECIDING,
            AgentState.FAILED,
            AgentState.CANCELLED,
        ],
        AgentState.DECIDING: [
            AgentState.EXPLAINING,
            AgentState.COMPLETE,  # Skip explanation if not needed
            AgentState.FAILED,
            AgentState.CANCELLED,
        ],
        AgentState.EXPLAINING: [
            AgentState.COMPLETE,
            AgentState.FAILED,
            AgentState.CANCELLED,
        ],
        AgentState.COMPLETE: [],  # Terminal state
        AgentState.FAILED: [AgentState.ANALYZING],  # Retry from analysis
        AgentState.CANCELLED: [],  # Terminal state
    }

    def __init__(
        self,
        session_id: str,
        initial_state: AgentState = AgentState.IDLE,
    ):
        """
        Initialize state machine.

        Args:
            session_id: Unique session identifier
            initial_state: Starting state (default: IDLE)
        """
        self.session_id = session_id
        self.current_state = initial_state
        self.history: List[StateTransition] = []
        self.metadata: Dict = {}

        logger.info(f"StateMachine initialized: session={session_id}, state={initial_state}")

    def transition(
        self,
        to_state: AgentState,
        reason: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> bool:
        """
        Transition to a new state.

        Args:
            to_state: Target state
            reason: Reason for transition
            metadata: Additional metadata

        Returns:
            True if transition succeeded, False otherwise

        Raises:
            ValueError: If transition is invalid
        """
        # Check if transition is valid
        if to_state not in self.TRANSITIONS[self.current_state]:
            valid_states = ", ".join([s.value for s in self.TRANSITIONS[self.current_state]])
            raise ValueError(
                f"Invalid transition: {self.current_state.value} → {to_state.value}. "
                f"Valid next states: {valid_states}"
            )

        # Record transition
        transition = StateTransition(
            from_state=self.current_state,
            to_state=to_state,
            reason=reason,
            metadata=metadata or {},
        )
        self.history.append(transition)

        # Update state
        old_state = self.current_state
        self.current_state = to_state

        logger.info(
            f"State transition: session={self.session_id}, "
            f"{old_state.value} → {to_state.value}, reason={reason}"
        )

        return True

    def can_transition_to(self, to_state: AgentState) -> bool:
        """Check if transition to state is valid."""
        return to_state in self.TRANSITIONS[self.current_state]

    def is_terminal(self) -> bool:
        """Check if current state is terminal."""
        return self.current_state in [
            AgentState.COMPLETE,
            AgentState.FAILED,
            AgentState.CANCELLED,
        ]

    def get_state(self) -> AgentState:
        """Get current state."""
        return self.current_state

    def get_history(self) -> List[StateTransition]:
        """Get state transition history."""
        return self.history.copy()

    def to_dict(self) -> Dict:
        """Serialize state machine to dict."""
        return {
            "session_id": self.session_id,
            "current_state": self.current_state.value,
            "metadata": self.metadata,
            "history": [
                {
                    "from_state": t.from_state.value,
                    "to_state": t.to_state.value,
                    "timestamp": t.timestamp.isoformat(),
                    "reason": t.reason,
                    "metadata": t.metadata,
                }
                for t in self.history
            ],
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "StateMachine":
        """Deserialize state machine from dict."""
        sm = cls(
            session_id=data["session_id"],
            initial_state=AgentState(data["current_state"]),
        )
        sm.metadata = data.get("metadata", {})

        # Restore history
        for h in data.get("history", []):
            sm.history.append(
                StateTransition(
                    from_state=AgentState(h["from_state"]),
                    to_state=AgentState(h["to_state"]),
                    timestamp=datetime.fromisoformat(h["timestamp"]),
                    reason=h.get("reason"),
                    metadata=h.get("metadata", {}),
                )
            )

        return sm
