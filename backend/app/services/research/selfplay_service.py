"""
Self-Play Service - Adversarial Agent Training

Fraud Detection Agent vs Fraud Evasion Agent
AlphaGo-style self-improvement through adversarial play
"""

import json
import random
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from pathlib import Path


class FraudEvasionStrategy(BaseModel):
    """Strategy for evading fraud detection"""
    strategy_id: str
    name: str
    description: str
    modifications: Dict  # How to modify transaction to evade detection
    success_rate: float = 0.0
    times_used: int = 0


class SelfPlayMatch(BaseModel):
    """Single match between detector and evader"""
    match_id: str
    iteration: int
    original_transaction: Dict
    evasion_attempt: Dict
    evasion_strategy: str
    
    # Results
    detector_caught_it: bool
    detector_confidence: float
    evader_successful: bool
    
    # Learning
    detector_improved: bool = False
    evader_improved: bool = False
    
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class SelfPlayStats(BaseModel):
    """Aggregated self-play statistics"""
    total_matches: int
    detector_wins: int
    evader_wins: int
    current_detector_accuracy: float
    current_evader_success_rate: float
    
    # Improvement tracking
    detector_improvement: float  # % improvement from start
    evader_improvement: float
    
    # Best strategies discovered
    most_effective_evasion: Optional[str] = None
    most_robust_detection: Optional[str] = None


class SelfPlayService:
    """Service for adversarial self-play training"""
    
    def __init__(self, storage_path: str = "data/selfplay"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.matches_file = self.storage_path / "matches.jsonl"
        
        # Initialize evasion strategies
        self.evasion_strategies = [
            FraudEvasionStrategy(
                strategy_id="split_amount",
                name="Amount Splitting",
                description="Split large fraud into multiple small transactions",
                modifications={"amount": "divide_by_5"}
            ),
            FraudEvasionStrategy(
                strategy_id="balance_manipulation",
                name="Balance Manipulation",
                description="Adjust balances to look normal",
                modifications={"newbalanceOrig": "make_consistent", "newbalanceDest": "make_consistent"}
            ),
            FraudEvasionStrategy(
                strategy_id="type_disguise",
                name="Transaction Type Disguise",
                description="Use PAYMENT instead of CASH_OUT/TRANSFER",
                modifications={"type": "PAYMENT"}
            ),
            FraudEvasionStrategy(
                strategy_id="gradual_drain",
                name="Gradual Account Drain",
                description="Drain account slowly, not all at once",
                modifications={"amount": "reduce_by_half", "newbalanceOrig": "leave_some"}
            ),
        ]
    
    def create_evasion_attempt(
        self,
        fraud_transaction: Dict,
        strategy: FraudEvasionStrategy
    ) -> Dict:
        """
        Evader agent modifies fraud transaction to try to evade detection
        """
        evaded_tx = fraud_transaction.copy()
        
        # Apply strategy modifications
        if "amount" in strategy.modifications:
            mod = strategy.modifications["amount"]
            if mod == "divide_by_5":
                evaded_tx["amount"] = fraud_transaction["amount"] / 5
            elif mod == "reduce_by_half":
                evaded_tx["amount"] = fraud_transaction["amount"] / 2
        
        if "type" in strategy.modifications:
            evaded_tx["type"] = strategy.modifications["type"]
        
        if "newbalanceOrig" in strategy.modifications:
            # Make balance look consistent
            evaded_tx["newbalanceOrig"] = fraud_transaction["oldbalanceOrg"] - evaded_tx["amount"]
        
        if "newbalanceDest" in strategy.modifications:
            # Make destination balance look consistent
            evaded_tx["newbalanceDest"] = fraud_transaction["oldbalanceDest"] + evaded_tx["amount"]
        
        return evaded_tx
    
    async def play_match(
        self,
        fraud_transaction: Dict,
        detector_func,  # Function that takes transaction and returns (is_fraud, confidence)
        iteration: int
    ) -> SelfPlayMatch:
        """
        Play one match: evader tries to evade, detector tries to catch
        """
        # Evader selects strategy (with some randomness for exploration)
        strategy = random.choice(self.evasion_strategies)
        
        # Create evasion attempt
        evaded_tx = self.create_evasion_attempt(fraud_transaction, strategy)
        
        # Detector analyzes evaded transaction
        is_fraud, confidence = await detector_func(evaded_tx)
        
        # Determine winner
        detector_caught_it = is_fraud and confidence > 0.7
        evader_successful = not detector_caught_it
        
        # Update strategy stats
        strategy.times_used += 1
        if evader_successful:
            strategy.success_rate = (
                (strategy.success_rate * (strategy.times_used - 1) + 1.0) / strategy.times_used
            )
        else:
            strategy.success_rate = (
                (strategy.success_rate * (strategy.times_used - 1) + 0.0) / strategy.times_used
            )
        
        match = SelfPlayMatch(
            match_id=f"match_{iteration}_{datetime.utcnow().timestamp()}",
            iteration=iteration,
            original_transaction=fraud_transaction,
            evasion_attempt=evaded_tx,
            evasion_strategy=strategy.name,
            detector_caught_it=detector_caught_it,
            detector_confidence=confidence,
            evader_successful=evader_successful
        )
        
        # Record match
        with open(self.matches_file, "a") as f:
            f.write(match.model_dump_json() + "\n")
        
        return match
    
    def get_stats(self, last_n_matches: Optional[int] = None) -> SelfPlayStats:
        """Get self-play statistics"""
        
        if not self.matches_file.exists():
            return SelfPlayStats(
                total_matches=0,
                detector_wins=0,
                evader_wins=0,
                current_detector_accuracy=0.0,
                current_evader_success_rate=0.0,
                detector_improvement=0.0,
                evader_improvement=0.0
            )
        
        matches = []
        with open(self.matches_file, "r") as f:
            for line in f:
                matches.append(SelfPlayMatch.model_validate_json(line))
        
        if last_n_matches:
            matches = matches[-last_n_matches:]
        
        total = len(matches)
        if total == 0:
            return SelfPlayStats(
                total_matches=0,
                detector_wins=0,
                evader_wins=0,
                current_detector_accuracy=0.0,
                current_evader_success_rate=0.0,
                detector_improvement=0.0,
                evader_improvement=0.0
            )
        
        detector_wins = sum(1 for m in matches if m.detector_caught_it)
        evader_wins = sum(1 for m in matches if m.evader_successful)
        
        current_detector_accuracy = detector_wins / total
        current_evader_success_rate = evader_wins / total
        
        # Calculate improvement (compare first 25% vs last 25%)
        if total >= 20:
            early_matches = matches[:total//4]
            recent_matches = matches[-total//4:]
            
            early_detector_accuracy = sum(1 for m in early_matches if m.detector_caught_it) / len(early_matches)
            recent_detector_accuracy = sum(1 for m in recent_matches if m.detector_caught_it) / len(recent_matches)
            
            detector_improvement = (recent_detector_accuracy - early_detector_accuracy) * 100
            evader_improvement = -detector_improvement  # Inverse relationship
        else:
            detector_improvement = 0.0
            evader_improvement = 0.0
        
        # Find most effective strategies
        strategy_success = {}
        for strategy in self.evasion_strategies:
            strategy_matches = [m for m in matches if m.evasion_strategy == strategy.name]
            if strategy_matches:
                success_rate = sum(1 for m in strategy_matches if m.evader_successful) / len(strategy_matches)
                strategy_success[strategy.name] = success_rate
        
        most_effective = max(strategy_success.items(), key=lambda x: x[1])[0] if strategy_success else None
        
        return SelfPlayStats(
            total_matches=total,
            detector_wins=detector_wins,
            evader_wins=evader_wins,
            current_detector_accuracy=current_detector_accuracy,
            current_evader_success_rate=current_evader_success_rate,
            detector_improvement=detector_improvement,
            evader_improvement=evader_improvement,
            most_effective_evasion=most_effective
        )
    
    def get_hardest_evasions(self, limit: int = 10) -> List[Dict]:
        """Get evasion attempts that successfully fooled the detector"""
        
        if not self.matches_file.exists():
            return []
        
        successful_evasions = []
        with open(self.matches_file, "r") as f:
            for line in f:
                match = SelfPlayMatch.model_validate_json(line)
                if match.evader_successful:
                    successful_evasions.append({
                        "match_id": match.match_id,
                        "iteration": match.iteration,
                        "strategy": match.evasion_strategy,
                        "evaded_transaction": match.evasion_attempt,
                        "detector_confidence": match.detector_confidence
                    })
        
        # Sort by detector confidence (ascending) - hardest are where detector was most confident it was legit
        successful_evasions.sort(key=lambda x: x["detector_confidence"])
        
        return successful_evasions[:limit]


# Global instance
selfplay_service = SelfPlayService()
