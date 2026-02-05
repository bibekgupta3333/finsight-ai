"""
Feedback Collection Service - RLHF (Reinforcement Learning from Human Feedback)

Implements lightweight feedback collection for improving agent explanations.
Stores user preferences (thumbs up/down) and aggregates feedback for retraining.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from enum import Enum


class FeedbackType(str, Enum):
    """Feedback types"""
    THUMBS_UP = "thumbs_up"
    THUMBS_DOWN = "thumbs_down"
    REPORT = "report"


class FeedbackRating(int, Enum):
    """Numeric ratings"""
    VERY_BAD = 1
    BAD = 2
    NEUTRAL = 3
    GOOD = 4
    EXCELLENT = 5


class FeedbackData(BaseModel):
    """Feedback data model"""
    feedback_id: str
    transaction_id: str
    explanation: str
    feedback_type: FeedbackType
    rating: Optional[FeedbackRating] = None
    comment: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    
    # Context
    prediction: str  # fraud/legitimate
    confidence: float
    reasoning_steps: List[str] = []
    
    # Metadata
    model_version: str = "v2.1"
    agent_type: str = "single"  # single, debate, swarm, etc.


class FeedbackStats(BaseModel):
    """Aggregated feedback statistics"""
    total_feedback: int
    thumbs_up_count: int
    thumbs_down_count: int
    average_rating: float
    feedback_rate: float  # % of analyses that received feedback
    
    # By agent type
    stats_by_agent: Dict[str, Dict[str, int]] = {}
    
    # By prediction
    correct_fraud_detections: int = 0
    false_positives: int = 0
    missed_frauds: int = 0
    correct_legitimate: int = 0


class FeedbackService:
    """Service for managing user feedback and preferences"""
    
    def __init__(self, storage_path: str = "data/feedback"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.feedback_file = self.storage_path / "feedback_log.jsonl"
        
    def collect_feedback(self, feedback: FeedbackData) -> Dict:
        """
        Collect feedback from user
        
        Args:
            feedback: Feedback data
            
        Returns:
            Confirmation with feedback_id
        """
        # Append to JSONL file (one JSON per line)
        with open(self.feedback_file, "a") as f:
            f.write(feedback.model_dump_json() + "\n")
        
        return {
            "status": "success",
            "feedback_id": feedback.feedback_id,
            "message": "Feedback collected successfully",
            "timestamp": feedback.timestamp.isoformat()
        }
    
    def get_feedback_stats(self) -> FeedbackStats:
        """Get aggregated feedback statistics"""
        
        if not self.feedback_file.exists():
            return FeedbackStats(
                total_feedback=0,
                thumbs_up_count=0,
                thumbs_down_count=0,
                average_rating=0.0,
                feedback_rate=0.0
            )
        
        feedbacks = []
        with open(self.feedback_file, "r") as f:
            for line in f:
                feedbacks.append(FeedbackData.model_validate_json(line))
        
        total = len(feedbacks)
        thumbs_up = sum(1 for f in feedbacks if f.feedback_type == FeedbackType.THUMBS_UP)
        thumbs_down = sum(1 for f in feedbacks if f.feedback_type == FeedbackType.THUMBS_DOWN)
        
        # Calculate average rating (only for feedbacks with ratings)
        ratings = [f.rating.value for f in feedbacks if f.rating is not None]
        avg_rating = sum(ratings) / len(ratings) if ratings else 0.0
        
        # Stats by agent type
        stats_by_agent = {}
        for feedback in feedbacks:
            agent_type = feedback.agent_type
            if agent_type not in stats_by_agent:
                stats_by_agent[agent_type] = {
                    "thumbs_up": 0,
                    "thumbs_down": 0,
                    "total": 0
                }
            stats_by_agent[agent_type]["total"] += 1
            if feedback.feedback_type == FeedbackType.THUMBS_UP:
                stats_by_agent[agent_type]["thumbs_up"] += 1
            elif feedback.feedback_type == FeedbackType.THUMBS_DOWN:
                stats_by_agent[agent_type]["thumbs_down"] += 1
        
        return FeedbackStats(
            total_feedback=total,
            thumbs_up_count=thumbs_up,
            thumbs_down_count=thumbs_down,
            average_rating=avg_rating,
            feedback_rate=0.0,  # Would need total analyses count
            stats_by_agent=stats_by_agent
        )
    
    def get_positive_examples(self, limit: int = 100) -> List[FeedbackData]:
        """Get examples with positive feedback for training"""
        
        if not self.feedback_file.exists():
            return []
        
        positive_feedbacks = []
        with open(self.feedback_file, "r") as f:
            for line in f:
                feedback = FeedbackData.model_validate_json(line)
                if feedback.feedback_type == FeedbackType.THUMBS_UP:
                    positive_feedbacks.append(feedback)
        
        # Sort by timestamp (most recent first)
        positive_feedbacks.sort(key=lambda x: x.timestamp, reverse=True)
        
        return positive_feedbacks[:limit]
    
    def get_negative_examples(self, limit: int = 100) -> List[FeedbackData]:
        """Get examples with negative feedback for improvement"""
        
        if not self.feedback_file.exists():
            return []
        
        negative_feedbacks = []
        with open(self.feedback_file, "r") as f:
            for line in f:
                feedback = FeedbackData.model_validate_json(line)
                if feedback.feedback_type == FeedbackType.THUMBS_DOWN:
                    negative_feedbacks.append(feedback)
        
        # Sort by timestamp (most recent first)
        negative_feedbacks.sort(key=lambda x: x.timestamp, reverse=True)
        
        return negative_feedbacks[:limit]
    
    def export_for_training(self, output_path: Optional[str] = None) -> str:
        """
        Export feedback in format suitable for fine-tuning
        
        Returns preference pairs: (good_explanation, bad_explanation) for RLHF
        """
        output_path = output_path or str(self.storage_path / "preference_pairs.json")
        
        positive = self.get_positive_examples(limit=1000)
        negative = self.get_negative_examples(limit=1000)
        
        # Create preference pairs
        preference_pairs = []
        
        # Simple pairing: match by transaction type or amount range
        for pos_feedback in positive:
            for neg_feedback in negative:
                # Only pair if they're for similar transactions
                if (pos_feedback.prediction == neg_feedback.prediction and
                    abs(pos_feedback.confidence - neg_feedback.confidence) < 0.3):
                    
                    preference_pairs.append({
                        "transaction_id_good": pos_feedback.transaction_id,
                        "transaction_id_bad": neg_feedback.transaction_id,
                        "good_explanation": pos_feedback.explanation,
                        "bad_explanation": neg_feedback.explanation,
                        "prediction": pos_feedback.prediction,
                        "confidence_good": pos_feedback.confidence,
                        "confidence_bad": neg_feedback.confidence,
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    
                    # Limit pairs to avoid combinatorial explosion
                    if len(preference_pairs) >= 500:
                        break
            
            if len(preference_pairs) >= 500:
                break
        
        # Save to file
        with open(output_path, "w") as f:
            json.dump(preference_pairs, f, indent=2)
        
        return output_path


# Global instance
feedback_service = FeedbackService()
