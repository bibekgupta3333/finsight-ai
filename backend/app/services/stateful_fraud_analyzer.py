"""
Stateful Fraud Detection Service.

Integrates state machine, checkpointing, and circuit breaker patterns.
"""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Dict, Optional

from app.core.checkpoint import Checkpoint
from app.core.circuit_breaker import get_circuit_breaker
from app.core.retry import RetryConfig, retry_with_backoff
from app.core.session import get_session_manager
from app.core.state_machine import AgentState, StateMachine
from app.models.fraud import (
    FraudAnalysisResponse,
    FraudPrediction,
    Transaction,
)
from app.services.fraud_detection import get_fraud_service

logger = logging.getLogger(__name__)


class StatefulFraudAnalyzer:
    """
    Stateful fraud analyzer with FSM, checkpointing, and resilience patterns.

    Workflow: IDLE → ANALYZING → REASONING → DECIDING → EXPLAINING → COMPLETE
    """

    def __init__(self, session_id: Optional[str] = None):
        """
        Initialize stateful analyzer.

        Args:
            session_id: Session ID (auto-generated if None)
        """
        self.session_id = session_id or str(uuid.uuid4())
        self.session_manager = get_session_manager()
        self.fraud_service = get_fraud_service()
        self.state_machine: Optional[StateMachine] = None
        self.checkpoint: Optional[Checkpoint] = None
        self.step_counter = 0

    async def create_session(self, metadata: Optional[Dict] = None):
        """Create new session with state machine."""
        self.state_machine = await self.session_manager.create_session(
            session_id=self.session_id,
            metadata=metadata or {},
        )
        self.checkpoint = Checkpoint(self.session_id)

        logger.info(f"Created stateful session: {self.session_id}")

    async def load_session(self):
        """Load existing session."""
        self.state_machine = await self.session_manager.get_session(self.session_id)

        if not self.state_machine:
            raise ValueError(f"Session not found: {self.session_id}")

        self.checkpoint = Checkpoint(self.session_id)
        await self.checkpoint.load_checkpoints()

        logger.info(
            f"Loaded session: {self.session_id}, state: {self.state_machine.current_state}"
        )

    async def analyze_transaction(
        self,
        transaction: Transaction,
    ) -> FraudAnalysisResponse:
        """
        Analyze transaction with full state management.

        Args:
            transaction: Transaction to analyze

        Returns:
            Fraud analysis response

        Raises:
            Exception: If analysis fails
        """
        if not self.state_machine:
            await self.create_session(metadata={"transaction_id": transaction.transaction_id})

        try:
            # Step 1: IDLE → ANALYZING
            await self._transition_and_checkpoint(
                to_state=AgentState.ANALYZING,
                step_name="start_analysis",
                input_data=transaction.model_dump(),
            )

            # Step 2: Analyze transaction with circuit breaker
            analysis_result = await self._analyze_with_resilience(transaction)

            # Step 3: ANALYZING → REASONING
            await self._transition_and_checkpoint(
                to_state=AgentState.REASONING,
                step_name="reasoning",
                output_data=analysis_result,
            )

            # Step 4: Decide based on analysis
            decision_result = await self._make_decision(analysis_result)

            # Step 5: REASONING → DECIDING
            await self._transition_and_checkpoint(
                to_state=AgentState.DECIDING,
                step_name="decision",
                output_data=decision_result,
            )

            # Step 6: Generate explanation
            explanation = await self._generate_explanation(
                transaction,
                analysis_result,
                decision_result,
            )

            # Step 7: DECIDING → EXPLAINING
            await self._transition_and_checkpoint(
                to_state=AgentState.EXPLAINING,
                step_name="explanation",
                output_data={"explanation": explanation},
            )

            # Step 8: Complete
            await self._transition_and_checkpoint(
                to_state=AgentState.COMPLETE,
                step_name="complete",
            )

            # Build response
            response = FraudAnalysisResponse(
                transaction_id=transaction.transaction_id,
                prediction=FraudPrediction(**decision_result),
                analyzed_at=datetime.utcnow(),
                session_id=self.session_id,
            )

            logger.info(
                f"Analysis complete: session={self.session_id}, "
                f"fraud={response.prediction.is_fraud}"
            )

            return response

        except Exception as e:
            # Transition to FAILED state
            if self.state_machine:
                await self._transition_and_checkpoint(
                    to_state=AgentState.FAILED,
                    step_name="error",
                    error=str(e),
                )

            logger.error(f"Analysis failed: session={self.session_id}, error={e}")
            raise e

    async def _transition_and_checkpoint(
        self,
        to_state: AgentState,
        step_name: str,
        input_data: Optional[Dict] = None,
        output_data: Optional[Dict] = None,
        error: Optional[str] = None,
    ):
        """Transition state and save checkpoint."""
        # Transition state
        self.state_machine.transition(
            to_state=to_state,
            reason=step_name,
        )

        # Save checkpoint
        self.step_counter += 1
        await self.checkpoint.save_checkpoint(
            state=to_state,
            step_number=self.step_counter,
            step_name=step_name,
            input_data=input_data or {},
            output_data=output_data,
            error=error,
        )

        # Update session
        await self.session_manager.update_session(self.state_machine)

        logger.debug(
            f"State transition: {step_name} → {to_state.value}, "
            f"step={self.step_counter}"
        )

    async def _analyze_with_resilience(self, transaction: Transaction) -> Dict:
        """Analyze with circuit breaker and retry."""
        circuit_breaker = get_circuit_breaker("fraud_analysis")

        # Define retry config
        retry_config = RetryConfig(
            max_attempts=3,
            base_delay=0.5,
            max_delay=5.0,
        )

        # Execute with circuit breaker and retry
        async def analysis_func():
            return await circuit_breaker.call(
                self.fraud_service.analyze_transaction,
                transaction,
            )

        result = await retry_with_backoff(analysis_func, config=retry_config)

        return {
            "risk_features": result.prediction.model_dump(),
            "processing_time_ms": result.processing_time_ms,
        }

    async def _make_decision(self, analysis_result: Dict) -> Dict:
        """Make fraud decision based on analysis."""
        prediction = analysis_result["risk_features"]

        return {
            "is_fraud": prediction["is_fraud"],
            "confidence": prediction["confidence"],
            "risk_score": prediction["risk_score"],
            "risk_level": prediction["risk_level"],
            "explanation": prediction.get("explanation", ""),
            "features": prediction.get("features", {}),
        }

    async def _generate_explanation(
        self,
        transaction: Transaction,
        analysis_result: Dict,
        decision_result: Dict,
    ) -> str:
        """Generate human-readable explanation."""
        is_fraud = decision_result["is_fraud"]
        risk_factors = analysis_result["risk_features"].get("risk_factors", [])

        if is_fraud:
            explanation = f"Fraud detected: {', '.join(risk_factors)}"
        else:
            explanation = "Transaction appears legitimate based on analysis"

        return explanation

    async def resume_from_failure(self) -> FraudAnalysisResponse:
        """Resume analysis from last checkpoint after failure."""
        await self.load_session()

        # Get last checkpoint
        last_checkpoint = await self.checkpoint.get_last_checkpoint()

        if not last_checkpoint:
            raise ValueError("No checkpoint found to resume from")

        logger.info(
            f"Resuming from checkpoint: step={last_checkpoint.step_number}, "
            f"state={last_checkpoint.state}"
        )

        # Resume logic would go here
        # For now, just log and return error
        raise NotImplementedError("Resume from checkpoint not yet implemented")

    async def get_execution_trace(self) -> Dict:
        """Get execution trace for debugging."""
        if not self.checkpoint:
            return {"error": "No checkpoint manager"}

        return {
            "session_id": self.session_id,
            "trace": self.checkpoint.get_execution_trace(),
        }
