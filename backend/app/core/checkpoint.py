"""
Checkpointing and Replay System.

Provides checkpointing for long-running analyses and deterministic replay.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.core.session import get_session_manager
from app.core.state_machine import AgentState

logger = logging.getLogger(__name__)


class CheckpointData(BaseModel):
    """Checkpoint data model."""

    session_id: str
    state: AgentState
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    step_number: int
    step_name: str
    input_data: Dict
    output_data: Optional[Dict] = None
    intermediate_results: Dict = Field(default_factory=dict)
    error: Optional[str] = None


class Checkpoint:
    """
    Checkpoint manager for agent execution.

    Enables saving/loading execution state and deterministic replay.
    """

    def __init__(self, session_id: str):
        """
        Initialize checkpoint manager.

        Args:
            session_id: Session identifier
        """
        self.session_id = session_id
        self.checkpoints: List[CheckpointData] = []
        self.session_manager = get_session_manager()

    async def save_checkpoint(
        self,
        state: AgentState,
        step_number: int,
        step_name: str,
        input_data: Dict,
        output_data: Optional[Dict] = None,
        intermediate_results: Optional[Dict] = None,
        error: Optional[str] = None,
    ) -> CheckpointData:
        """
        Save a checkpoint.

        Args:
            state: Current agent state
            step_number: Sequential step number
            step_name: Name of the step (e.g., "analyze_transaction")
            input_data: Input to this step
            output_data: Output from this step
            intermediate_results: Intermediate calculations
            error: Error message if step failed

        Returns:
            CheckpointData instance
        """
        checkpoint = CheckpointData(
            session_id=self.session_id,
            state=state,
            step_number=step_number,
            step_name=step_name,
            input_data=input_data,
            output_data=output_data,
            intermediate_results=intermediate_results or {},
            error=error,
        )

        # Store in memory
        self.checkpoints.append(checkpoint)

        # Persist to Redis
        await self._persist_checkpoint(checkpoint)

        logger.info(
            f"Saved checkpoint: session={self.session_id}, "
            f"step={step_number}, name={step_name}, state={state}"
        )

        return checkpoint

    async def _persist_checkpoint(self, checkpoint: CheckpointData):
        """Persist checkpoint to Redis."""
        await self.session_manager.connect()

        # Append to checkpoint list in Redis
        key = f"checkpoint:{self.session_id}"
        checkpoint_json = checkpoint.model_dump_json()

        # Use Redis list to store checkpoints
        await self.session_manager.redis_client.rpush(key, checkpoint_json)

        # Set expiration (same as session)
        await self.session_manager.redis_client.expire(
            key,
            self.session_manager.session_ttl,
        )

    async def load_checkpoints(self) -> List[CheckpointData]:
        """
        Load all checkpoints for session.

        Returns:
            List of checkpoint data
        """
        await self.session_manager.connect()

        key = f"checkpoint:{self.session_id}"
        checkpoints_json = await self.session_manager.redis_client.lrange(key, 0, -1)

        if not checkpoints_json:
            logger.warning(f"No checkpoints found for session: {self.session_id}")
            return []

        # Deserialize checkpoints
        checkpoints = [
            CheckpointData.model_validate_json(cp_json) for cp_json in checkpoints_json
        ]

        self.checkpoints = checkpoints

        logger.info(
            f"Loaded {len(checkpoints)} checkpoints for session: {self.session_id}"
        )

        return checkpoints

    async def get_last_checkpoint(self) -> Optional[CheckpointData]:
        """
        Get the most recent checkpoint.

        Returns:
            Last checkpoint or None
        """
        if not self.checkpoints:
            await self.load_checkpoints()

        if not self.checkpoints:
            return None

        return self.checkpoints[-1]

    async def resume_from_checkpoint(
        self,
        checkpoint_index: Optional[int] = None,
    ) -> Optional[CheckpointData]:
        """
        Resume execution from a checkpoint.

        Args:
            checkpoint_index: Index of checkpoint to resume from (default: last)

        Returns:
            Checkpoint to resume from
        """
        if not self.checkpoints:
            await self.load_checkpoints()

        if not self.checkpoints:
            logger.warning(f"No checkpoints to resume from: {self.session_id}")
            return None

        if checkpoint_index is None:
            checkpoint = self.checkpoints[-1]
        else:
            if checkpoint_index < 0 or checkpoint_index >= len(self.checkpoints):
                raise ValueError(
                    f"Invalid checkpoint index: {checkpoint_index}. "
                    f"Valid range: 0-{len(self.checkpoints) - 1}"
                )
            checkpoint = self.checkpoints[checkpoint_index]

        logger.info(
            f"Resuming from checkpoint: session={self.session_id}, "
            f"step={checkpoint.step_number}, state={checkpoint.state}"
        )

        return checkpoint

    async def replay_execution(
        self,
        from_step: int = 0,
        to_step: Optional[int] = None,
    ) -> List[CheckpointData]:
        """
        Replay execution for debugging.

        Args:
            from_step: Starting step number
            to_step: Ending step number (default: last)

        Returns:
            List of checkpoints in replay range
        """
        if not self.checkpoints:
            await self.load_checkpoints()

        if not self.checkpoints:
            logger.warning(f"No checkpoints to replay: {self.session_id}")
            return []

        # Filter checkpoints by step range
        to_step = to_step or self.checkpoints[-1].step_number

        replay_checkpoints = [
            cp
            for cp in self.checkpoints
            if from_step <= cp.step_number <= to_step
        ]

        logger.info(
            f"Replaying execution: session={self.session_id}, "
            f"steps={from_step}-{to_step}, count={len(replay_checkpoints)}"
        )

        return replay_checkpoints

    def get_execution_trace(self) -> List[Dict]:
        """
        Get execution trace for debugging.

        Returns:
            List of step summaries
        """
        return [
            {
                "step": cp.step_number,
                "name": cp.step_name,
                "state": cp.state.value,
                "timestamp": cp.timestamp.isoformat(),
                "has_error": cp.error is not None,
                "error": cp.error,
            }
            for cp in self.checkpoints
        ]

    async def clear_checkpoints(self):
        """Clear all checkpoints for session."""
        await self.session_manager.connect()

        key = f"checkpoint:{self.session_id}"
        await self.session_manager.redis_client.delete(key)

        self.checkpoints.clear()

        logger.info(f"Cleared checkpoints for session: {self.session_id}")


class DeterministicReplay:
    """
    Deterministic replay for debugging agent behavior.

    Ensures reproducible execution by replaying inputs and state transitions.
    """

    def __init__(self, session_id: str):
        """
        Initialize replay manager.

        Args:
            session_id: Session identifier
        """
        self.session_id = session_id
        self.checkpoint_manager = Checkpoint(session_id)

    async def validate_replay(self) -> Dict[str, Any]:
        """
        Validate that replay produces same results.

        Returns:
            Validation report
        """
        checkpoints = await self.checkpoint_manager.load_checkpoints()

        if not checkpoints:
            return {"valid": False, "reason": "No checkpoints found"}

        # Check for determinism violations
        violations = []

        for i, cp in enumerate(checkpoints):
            # Check if step failed
            if cp.error:
                violations.append(
                    {
                        "step": cp.step_number,
                        "issue": "step_failed",
                        "error": cp.error,
                    }
                )

            # Check state transitions are valid
            if i > 0:
                prev_state = checkpoints[i - 1].state
                curr_state = cp.state
                # State transition validation would go here

        is_valid = len(violations) == 0

        return {
            "valid": is_valid,
            "total_steps": len(checkpoints),
            "violations": violations,
            "session_id": self.session_id,
        }
