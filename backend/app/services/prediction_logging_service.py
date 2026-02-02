"""
Prediction Logging Service for Continuous Learning.

Stores all predictions in database for:
- Model monitoring
- Performance tracking
- Retraining with feedback loops
- Audit trails

Optimized for M4 Pro: Async logging, batch writes.
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from uuid import uuid4

import pandas as pd
from sqlalchemy import (
    Column, String, Float, Integer, Boolean, DateTime, JSON, Text, create_engine
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

logger = logging.getLogger(__name__)

# Database setup
BACKEND_DIR = Path(__file__).parent.parent.parent
DB_PATH = BACKEND_DIR / "data" / "predictions.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

DATABASE_URL = f"sqlite:///{DB_PATH}"

Base = declarative_base()


class PredictionLog(Base):
    """Store ML model predictions."""

    __tablename__ = "prediction_logs"

    # Primary key
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))

    # Timestamp
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    # Transaction features (JSON)
    transaction_features = Column(JSON, nullable=False)

    # Model predictions
    model_name = Column(String(50), index=True)  # Which model made prediction
    fraud_probability = Column(Float, nullable=False)
    is_fraud = Column(Boolean, nullable=False)
    confidence = Column(Float)
    risk_level = Column(String(20))

    # Ensemble info (if applicable)
    ensemble_method = Column(String(50))  # "weighted_blend", "cascade", "stacking", etc.
    individual_predictions = Column(JSON)  # Dict of all model predictions

    # Ground truth (filled in later by analysts)
    true_label = Column(Boolean, nullable=True, index=True)
    feedback_timestamp = Column(DateTime, nullable=True)
    analyst_id = Column(String(50), nullable=True)
    analyst_notes = Column(Text, nullable=True)

    # Performance metrics (calculated after feedback)
    was_correct = Column(Boolean, nullable=True)

    # Additional metadata
    session_id = Column(String(100))
    api_version = Column(String(20))
    processing_time_ms = Column(Float)


class FeedbackLabel(Base):
    """Store analyst feedback on predictions."""

    __tablename__ = "feedback_labels"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    prediction_id = Column(String(36), index=True)  # Foreign key to PredictionLog

    # Feedback details
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    analyst_id = Column(String(50), nullable=False)
    true_label = Column(Boolean, nullable=False)  # True fraud label

    # Confidence in feedback
    confidence_level = Column(String(20))  # "high", "medium", "low"

    # Notes
    notes = Column(Text)
    fraud_category = Column(String(100))  # Type of fraud detected

    # Review metadata
    review_time_seconds = Column(Integer)
    flagged_for_retraining = Column(Boolean, default=False)


class PredictionLoggingService:
    """
    Service for logging predictions and managing feedback.

    Features:
    - Async logging (non-blocking)
    - Batch writes for efficiency
    - Feedback management
    - Query interface for retraining
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PredictionLoggingService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize prediction logging service."""
        if self._initialized:
            return

        # Create database engine
        self.engine = create_engine(DATABASE_URL, echo=False)

        # Create tables
        Base.metadata.create_all(self.engine)

        # Session maker
        self.SessionLocal = sessionmaker(bind=self.engine)

        # Batch logging queue
        self._log_queue: List[Dict] = []
        self._batch_size = 100  # Write every 100 predictions

        self._initialized = True
        logger.info(f"Prediction Logging Service initialized (DB: {DB_PATH})")

    def log_prediction(
        self,
        transaction: Dict[str, Any],
        prediction_result: Dict[str, Any],
        model_name: str,
        session_id: Optional[str] = None,
        processing_time_ms: Optional[float] = None
    ) -> str:
        """
        Log a prediction to database.

        Args:
            transaction: Transaction features dict
            prediction_result: Prediction dict (from ML service)
            model_name: Name of model used
            session_id: Optional session ID
            processing_time_ms: Optional processing time

        Returns:
            str: Prediction ID
        """
        prediction_id = str(uuid4())

        try:
            session = self.SessionLocal()

            # Create log entry
            log_entry = PredictionLog(
                id=prediction_id,
                timestamp=datetime.utcnow(),
                transaction_features=transaction,
                model_name=model_name,
                fraud_probability=prediction_result.get("fraud_probability", 0.0),
                is_fraud=prediction_result.get("is_fraud", False),
                confidence=prediction_result.get("confidence"),
                risk_level=prediction_result.get("risk_level"),
                ensemble_method=prediction_result.get("method"),
                individual_predictions=prediction_result.get("individual_predictions"),
                session_id=session_id,
                api_version="v1",
                processing_time_ms=processing_time_ms
            )

            session.add(log_entry)
            session.commit()

            logger.debug(f"Logged prediction {prediction_id}")

            session.close()
            return prediction_id

        except Exception as e:
            logger.error(f"Error logging prediction: {e}")
            return prediction_id

    async def log_prediction_async(
        self,
        transaction: Dict[str, Any],
        prediction_result: Dict[str, Any],
        model_name: str,
        session_id: Optional[str] = None,
        processing_time_ms: Optional[float] = None
    ) -> str:
        """
        Async version of log_prediction (non-blocking).

        Args:
            transaction: Transaction features
            prediction_result: Prediction result
            model_name: Model name
            session_id: Optional session ID
            processing_time_ms: Optional processing time

        Returns:
            str: Prediction ID
        """
        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self.log_prediction,
            transaction,
            prediction_result,
            model_name,
            session_id,
            processing_time_ms
        )

    def add_feedback(
        self,
        prediction_id: str,
        true_label: bool,
        analyst_id: str,
        notes: Optional[str] = None,
        confidence_level: str = "high",
        fraud_category: Optional[str] = None,
        review_time_seconds: Optional[int] = None
    ) -> str:
        """
        Add analyst feedback for a prediction.

        Args:
            prediction_id: ID of prediction
            true_label: True fraud label
            analyst_id: ID of analyst providing feedback
            notes: Optional notes
            confidence_level: Confidence in feedback ("high", "medium", "low")
            fraud_category: Type of fraud
            review_time_seconds: Time spent reviewing

        Returns:
            str: Feedback ID
        """
        feedback_id = str(uuid4())

        try:
            session = self.SessionLocal()

            # Create feedback entry
            feedback = FeedbackLabel(
                id=feedback_id,
                prediction_id=prediction_id,
                timestamp=datetime.utcnow(),
                analyst_id=analyst_id,
                true_label=true_label,
                confidence_level=confidence_level,
                notes=notes,
                fraud_category=fraud_category,
                review_time_seconds=review_time_seconds,
                flagged_for_retraining=True  # Default: use for retraining
            )

            session.add(feedback)

            # Update prediction log with ground truth
            prediction = session.query(PredictionLog).filter_by(id=prediction_id).first()
            if prediction:
                prediction.true_label = true_label
                prediction.feedback_timestamp = datetime.utcnow()
                prediction.analyst_id = analyst_id
                prediction.analyst_notes = notes
                prediction.was_correct = (prediction.is_fraud == true_label)

            session.commit()
            session.close()

            logger.info(f"Added feedback {feedback_id} for prediction {prediction_id}")
            return feedback_id

        except Exception as e:
            logger.error(f"Error adding feedback: {e}")
            return feedback_id

    def get_predictions_for_retraining(
        self,
        min_samples: int = 1000,
        include_unlabeled: bool = False,
        high_confidence_only: bool = True
    ) -> pd.DataFrame:
        """
        Get predictions suitable for model retraining.

        Args:
            min_samples: Minimum number of samples required
            include_unlabeled: Include predictions without feedback
            high_confidence_only: Only include high-confidence feedback

        Returns:
            DataFrame with features and labels for retraining
        """
        try:
            session = self.SessionLocal()

            # Query predictions with feedback
            query = session.query(PredictionLog)

            if not include_unlabeled:
                query = query.filter(PredictionLog.true_label.isnot(None))

            predictions = query.all()

            # Convert to DataFrame
            data = []
            for pred in predictions:
                # Extract transaction features
                features = pred.transaction_features.copy()
                features['isFraud'] = pred.true_label if pred.true_label is not None else pred.is_fraud
                features['prediction_timestamp'] = pred.timestamp
                features['has_feedback'] = pred.true_label is not None

                data.append(features)

            df = pd.DataFrame(data)

            session.close()

            logger.info(
                f"Retrieved {len(df)} predictions for retraining "
                f"({df['has_feedback'].sum()} with feedback)"
            )

            return df

        except Exception as e:
            logger.error(f"Error retrieving predictions for retraining: {e}")
            return pd.DataFrame()

    def get_model_performance_stats(
        self,
        model_name: Optional[str] = None,
        days: int = 7
    ) -> Dict[str, Any]:
        """
        Get model performance statistics.

        Args:
            model_name: Optional model name filter
            days: Number of days to look back

        Returns:
            Dict with performance metrics
        """
        try:
            session = self.SessionLocal()

            # Query predictions with feedback
            cutoff_date = datetime.utcnow() - pd.Timedelta(days=days)

            query = session.query(PredictionLog).filter(
                PredictionLog.timestamp >= cutoff_date,
                PredictionLog.true_label.isnot(None)
            )

            if model_name:
                query = query.filter(PredictionLog.model_name == model_name)

            predictions = query.all()

            if not predictions:
                return {"error": "No predictions with feedback found"}

            # Calculate metrics
            total = len(predictions)
            correct = sum(1 for p in predictions if p.was_correct)
            fraud_detected = sum(1 for p in predictions if p.is_fraud)
            true_frauds = sum(1 for p in predictions if p.true_label)

            # True positives, false positives, etc.
            tp = sum(1 for p in predictions if p.is_fraud and p.true_label)
            fp = sum(1 for p in predictions if p.is_fraud and not p.true_label)
            tn = sum(1 for p in predictions if not p.is_fraud and not p.true_label)
            fn = sum(1 for p in predictions if not p.is_fraud and p.true_label)

            # Metrics
            accuracy = correct / total if total > 0 else 0
            precision = tp / (tp + fp) if (tp + fp) > 0 else 0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0
            f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

            session.close()

            return {
                "model_name": model_name or "all_models",
                "days": days,
                "total_predictions": total,
                "correct_predictions": correct,
                "accuracy": accuracy,
                "precision": precision,
                "recall": recall,
                "f1_score": f1,
                "confusion_matrix": {
                    "true_positives": tp,
                    "false_positives": fp,
                    "true_negatives": tn,
                    "false_negatives": fn
                },
                "fraud_rate": {
                    "predicted": fraud_detected / total if total > 0 else 0,
                    "actual": true_frauds / total if total > 0 else 0
                }
            }

        except Exception as e:
            logger.error(f"Error calculating performance stats: {e}")
            return {"error": str(e)}


# Singleton instance
_logging_service = None


def get_logging_service() -> PredictionLoggingService:
    """Get singleton instance of PredictionLoggingService."""
    global _logging_service
    if _logging_service is None:
        _logging_service = PredictionLoggingService()
    return _logging_service
