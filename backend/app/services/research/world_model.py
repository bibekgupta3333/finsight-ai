"""
World Models Service

Agent's internal model of transaction environment.
Enables prediction of transaction outcomes and counterfactual simulation.
"""

import json
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class TransactionOutcome(BaseModel):
    """Predicted outcome of a transaction"""
    is_fraud: bool
    confidence: float
    expected_new_balance_orig: float
    expected_new_balance_dest: float
    risk_factors: List[str] = []


class CounterfactualScenario(BaseModel):
    """What-if scenario analysis"""
    scenario_id: str
    description: str
    modified_transaction: Dict
    predicted_outcome: TransactionOutcome
    comparison_to_original: str


class WorldModel:
    """Simple world model for transaction prediction"""
    
    def __init__(self):
        # Learn from observed transactions (simplified)
        self.fraud_patterns = {
            "cash_out_large": {"min_amount": 100000, "fraud_rate": 0.95},
            "disappeared_money": {"fraud_rate": 0.99},
            "account_drained": {"fraud_rate": 0.85},
            "balance_mismatch": {"fraud_rate": 0.75}
        }
    
    def predict_outcome(self, transaction: Dict) -> TransactionOutcome:
        """
        Predict what will happen with this transaction
        
        Internal model of transaction dynamics
        """
        tx_type = transaction.get("type", "")
        amount = transaction.get("amount", 0)
        old_balance_orig = transaction.get("oldbalanceOrg", 0)
        old_balance_dest = transaction.get("oldbalanceDest", 0)
        
        # Predict new balances
        expected_new_balance_orig = max(0, old_balance_orig - amount)
        expected_new_balance_dest = old_balance_dest + amount
        
        # Detect risk factors
        risk_factors = []
        fraud_score = 0.0
        
        # Pattern 1: Large CASH_OUT
        if tx_type == "CASH_OUT" and amount > 100000:
            risk_factors.append("large_cash_out")
            fraud_score += 0.4
        
        # Pattern 2: Account drained
        if expected_new_balance_orig == 0 and old_balance_orig > 0:
            risk_factors.append("account_drained")
            fraud_score += 0.3
        
        # Pattern 3: Balance mismatch (money disappears)
        actual_new_orig = transaction.get("newbalanceOrig", expected_new_balance_orig)
        actual_new_dest = transaction.get("newbalanceDest", expected_new_balance_dest)
        
        if abs(actual_new_orig - expected_new_balance_orig) > 1.0:
            risk_factors.append("balance_mismatch_orig")
            fraud_score += 0.25
        
        if abs(actual_new_dest - expected_new_balance_dest) > 1.0:
            risk_factors.append("balance_mismatch_dest")
            fraud_score += 0.25
        
        # Pattern 4: Money disappeared
        total_before = old_balance_orig + old_balance_dest
        total_after = actual_new_orig + actual_new_dest
        if abs((total_before - amount) - total_after) > 1.0:
            risk_factors.append("money_disappeared")
            fraud_score += 0.5
        
        is_fraud = fraud_score > 0.5
        confidence = min(1.0, fraud_score if is_fraud else 1.0 - fraud_score)
        
        return TransactionOutcome(
            is_fraud=is_fraud,
            confidence=confidence,
            expected_new_balance_orig=expected_new_balance_orig,
            expected_new_balance_dest=expected_new_balance_dest,
            risk_factors=risk_factors
        )
    
    def simulate_counterfactual(
        self,
        original_transaction: Dict,
        modifications: Dict
    ) -> CounterfactualScenario:
        """
        Simulate: 'What if amount was different?' or 'What if type was PAYMENT?'
        
        Counterfactual reasoning for understanding fraud dynamics
        """
        # Create modified transaction
        modified_tx = original_transaction.copy()
        modified_tx.update(modifications)
        
        # Get original and modified predictions
        original_outcome = self.predict_outcome(original_transaction)
        modified_outcome = self.predict_outcome(modified_tx)
        
        # Generate comparison
        if original_outcome.is_fraud != modified_outcome.is_fraud:
            comparison = f"Changing {list(modifications.keys())} REVERSED the fraud prediction"
        elif abs(original_outcome.confidence - modified_outcome.confidence) > 0.2:
            comparison = f"Confidence changed from {original_outcome.confidence:.2f} to {modified_outcome.confidence:.2f}"
        else:
            comparison = "Modification had minimal impact on prediction"
        
        # Create description
        mod_desc = ", ".join(f"{k}={v}" for k, v in modifications.items())
        
        return CounterfactualScenario(
            scenario_id=f"scenario_{datetime.utcnow().timestamp()}",
            description=f"What if {mod_desc}?",
            modified_transaction=modified_tx,
            predicted_outcome=modified_outcome,
            comparison_to_original=comparison
        )
    
    def explain_prediction(self, transaction: Dict) -> str:
        """Explain why the world model predicts this outcome"""
        outcome = self.predict_outcome(transaction)
        
        explanation = f"World Model Prediction: {'FRAUD' if outcome.is_fraud else 'LEGITIMATE'} (confidence: {outcome.confidence:.2f})\n\n"
        
        if outcome.risk_factors:
            explanation += "Risk Factors Detected:\n"
            for factor in outcome.risk_factors:
                explanation += f"  • {factor.replace('_', ' ').title()}\n"
        else:
            explanation += "No significant risk factors detected.\n"
        
        explanation += f"\nPredicted Balances:\n"
        explanation += f"  • Origin: {outcome.expected_new_balance_orig:.2f}\n"
        explanation += f"  • Destination: {outcome.expected_new_balance_dest:.2f}\n"
        
        return explanation


# Global instance
world_model = WorldModel()
