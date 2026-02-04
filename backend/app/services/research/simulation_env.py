"""
Simulated Fraud Detection Environment

Creates synthetic fraud scenarios for safe testing before production deployment.
Generates adversarial test cases and provides a sandbox for agent exploration.
"""

import json
import logging
import random
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Literal
from pydantic import BaseModel, Field
from enum import Enum

logger = logging.getLogger(__name__)


class FraudScenarioType(str, Enum):
    """Types of fraud scenarios"""
    BASIC_FRAUD = "basic_fraud"
    SOPHISTICATED_FRAUD = "sophisticated_fraud"
    COORDINATED_ATTACK = "coordinated_attack"
    ACCOUNT_TAKEOVER = "account_takeover"
    MONEY_LAUNDERING = "money_laundering"
    SYNTHETIC_IDENTITY = "synthetic_identity"


class TransactionType(str, Enum):
    """Transaction types"""
    PAYMENT = "PAYMENT"
    TRANSFER = "TRANSFER"
    CASH_OUT = "CASH_OUT"
    DEBIT = "DEBIT"
    CASH_IN = "CASH_IN"


class SyntheticTransaction(BaseModel):
    """Synthetic transaction for testing"""
    transaction_id: str = Field(default_factory=lambda: f"sim_{uuid.uuid4().hex[:12]}")
    type: TransactionType
    amount: float
    oldbalanceOrg: float
    newbalanceOrig: float
    oldbalanceDest: float
    newbalanceDest: float
    is_fraud: bool
    fraud_type: Optional[str] = None
    difficulty: int = Field(ge=1, le=5)  # 1=easy, 5=very hard
    scenario: FraudScenarioType
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class SimulationScenario(BaseModel):
    """Complete simulation scenario"""
    scenario_id: str = Field(default_factory=lambda: f"scenario_{uuid.uuid4().hex[:8]}")
    scenario_type: FraudScenarioType
    transactions: List[SyntheticTransaction]
    expected_detections: int
    adversarial_techniques: List[str]
    description: str
    difficulty: int


class SimulationResult(BaseModel):
    """Result of running simulation"""
    scenario_id: str
    total_transactions: int
    detected_fraud: int
    missed_fraud: int
    false_positives: int
    true_negatives: int
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    agent_performance: str  # excellent, good, fair, poor


class FraudSimulationEnvironment:
    """Safe simulation environment for fraud detection testing"""

    def __init__(self, data_dir: str = "data/simulation"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.scenarios_file = self.data_dir / "scenarios.jsonl"
        self.results_file = self.data_dir / "simulation_results.jsonl"
        self.synthetic_transactions = self.data_dir / "synthetic_transactions.jsonl"

    def generate_synthetic_transaction(
        self,
        fraud_probability: float = 0.5,
        difficulty: int = 3
    ) -> SyntheticTransaction:
        """Generate a single synthetic transaction"""
        is_fraud = random.random() < fraud_probability

        # Choose transaction type
        if is_fraud:
            tx_type = random.choice([TransactionType.CASH_OUT, TransactionType.TRANSFER])
        else:
            tx_type = random.choice([TransactionType.PAYMENT, TransactionType.TRANSFER, TransactionType.DEBIT])

        # Generate amounts based on difficulty
        if difficulty <= 2:
            # Easy: obvious fraud patterns
            if is_fraud:
                amount = random.uniform(100000, 1000000)
                old_balance = random.uniform(amount, amount * 2)
                new_balance = old_balance - amount
                dest_old = 0
                dest_new = 0 if random.random() < 0.5 else amount * random.uniform(0.5, 0.9)
            else:
                amount = random.uniform(10, 10000)
                old_balance = random.uniform(amount * 2, amount * 10)
                new_balance = old_balance - amount
                dest_old = random.uniform(0, 10000)
                dest_new = dest_old + amount
        else:
            # Hard: subtle patterns
            if is_fraud:
                # Sophisticated fraud with partial transfers
                amount = random.uniform(5000, 50000)
                old_balance = random.uniform(amount * 2, amount * 5)
                new_balance = old_balance - amount
                # Partial money disappearance
                dest_old = random.uniform(0, 5000)
                dest_new = dest_old + amount * random.uniform(0.7, 0.95)
            else:
                amount = random.uniform(100, 100000)
                old_balance = random.uniform(amount, amount * 10)
                new_balance = old_balance - amount
                dest_old = random.uniform(0, 50000)
                dest_new = dest_old + amount

        # Determine scenario
        if is_fraud:
            if amount > 100000:
                scenario = FraudScenarioType.BASIC_FRAUD
                fraud_type = "large_unauthorized_transfer"
            elif dest_new < dest_old + amount * 0.8:
                scenario = FraudScenarioType.MONEY_LAUNDERING
                fraud_type = "money_disappearance"
            else:
                scenario = FraudScenarioType.SOPHISTICATED_FRAUD
                fraud_type = "balance_manipulation"
        else:
            scenario = FraudScenarioType.BASIC_FRAUD  # Legitimate transaction
            fraud_type = None

        return SyntheticTransaction(
            type=tx_type,
            amount=amount,
            oldbalanceOrg=old_balance,
            newbalanceOrig=new_balance,
            oldbalanceDest=dest_old,
            newbalanceDest=dest_new,
            is_fraud=is_fraud,
            fraud_type=fraud_type,
            difficulty=difficulty,
            scenario=scenario
        )

    def generate_batch(
        self,
        count: int = 100,
        fraud_ratio: float = 0.3,
        difficulty_range: tuple = (1, 5)
    ) -> List[SyntheticTransaction]:
        """Generate a batch of synthetic transactions"""
        transactions = []

        for _ in range(count):
            difficulty = random.randint(difficulty_range[0], difficulty_range[1])
            tx = self.generate_synthetic_transaction(
                fraud_probability=fraud_ratio,
                difficulty=difficulty
            )
            transactions.append(tx)

            # Save to file
            with open(self.synthetic_transactions, "a") as f:
                f.write(tx.model_dump_json() + "\n")

        logger.info(f"Generated {count} synthetic transactions")
        return transactions

    def create_adversarial_scenario(
        self,
        scenario_type: FraudScenarioType,
        num_transactions: int = 10
    ) -> SimulationScenario:
        """Create an adversarial fraud scenario"""
        transactions = []
        adversarial_techniques = []

        if scenario_type == FraudScenarioType.SOPHISTICATED_FRAUD:
            # Gradual account drainage
            adversarial_techniques = [
                "gradual_drainage",
                "small_incremental_transfers",
                "time_distributed_fraud"
            ]
            initial_balance = 100000
            for i in range(num_transactions):
                amount = random.uniform(5000, 10000)
                old_bal = initial_balance - (i * 8000)
                new_bal = old_bal - amount

                tx = SyntheticTransaction(
                    type=TransactionType.TRANSFER,
                    amount=amount,
                    oldbalanceOrg=old_bal,
                    newbalanceOrig=new_bal,
                    oldbalanceDest=0,
                    newbalanceDest=amount * 0.8,  # Money disappears
                    is_fraud=True,
                    fraud_type="gradual_drainage",
                    difficulty=4,
                    scenario=scenario_type
                )
                transactions.append(tx)

        elif scenario_type == FraudScenarioType.COORDINATED_ATTACK:
            # Multiple accounts, coordinated transfers
            adversarial_techniques = [
                "multi_account_coordination",
                "circular_transfers",
                "layering"
            ]
            for i in range(num_transactions):
                amount = random.uniform(10000, 50000)
                tx = SyntheticTransaction(
                    type=TransactionType.TRANSFER,
                    amount=amount,
                    oldbalanceOrg=random.uniform(50000, 200000),
                    newbalanceOrig=random.uniform(30000, 150000),
                    oldbalanceDest=random.uniform(0, 50000),
                    newbalanceDest=random.uniform(10000, 80000),
                    is_fraud=True,
                    fraud_type="coordinated_attack",
                    difficulty=5,
                    scenario=scenario_type,
                    metadata={"attack_cluster_id": "cluster_001"}
                )
                transactions.append(tx)

        elif scenario_type == FraudScenarioType.ACCOUNT_TAKEOVER:
            # Sudden pattern change
            adversarial_techniques = [
                "pattern_shift",
                "legitimate_then_fraud",
                "behavioral_mimicry"
            ]
            # First 5: legitimate
            for i in range(5):
                amount = random.uniform(100, 1000)
                old_bal = 50000 - (i * 900)
                tx = SyntheticTransaction(
                    type=TransactionType.PAYMENT,
                    amount=amount,
                    oldbalanceOrg=old_bal,
                    newbalanceOrig=old_bal - amount,
                    oldbalanceDest=10000,
                    newbalanceDest=10000 + amount,
                    is_fraud=False,
                    difficulty=2,
                    scenario=scenario_type
                )
                transactions.append(tx)
            # Next 5: fraud after takeover
            for i in range(5):
                amount = random.uniform(10000, 30000)
                old_bal = 45000 - (i * 20000)
                tx = SyntheticTransaction(
                    type=TransactionType.CASH_OUT,
                    amount=amount,
                    oldbalanceOrg=old_bal,
                    newbalanceOrig=old_bal - amount,
                    oldbalanceDest=0,
                    newbalanceDest=0,
                    is_fraud=True,
                    fraud_type="account_takeover",
                    difficulty=4,
                    scenario=scenario_type
                )
                transactions.append(tx)
        else:
            # Basic fraud scenario
            adversarial_techniques = ["none"]
            for _ in range(num_transactions):
                tx = self.generate_synthetic_transaction(
                    fraud_probability=0.5,
                    difficulty=2
                )
                transactions.append(tx)

        expected_detections = sum(1 for tx in transactions if tx.is_fraud)
        avg_difficulty = sum(tx.difficulty for tx in transactions) / len(transactions)

        scenario = SimulationScenario(
            scenario_type=scenario_type,
            transactions=transactions,
            expected_detections=expected_detections,
            adversarial_techniques=adversarial_techniques,
            description=f"{scenario_type.value} with {num_transactions} transactions",
            difficulty=int(avg_difficulty)
        )

        # Save scenario
        with open(self.scenarios_file, "a") as f:
            f.write(scenario.model_dump_json() + "\n")

        logger.info(f"Created adversarial scenario: {scenario.scenario_id}")
        return scenario

    def run_simulation(
        self,
        scenario_id: str,
        detector_function: Optional[Any] = None
    ) -> SimulationResult:
        """Run a simulation scenario"""
        # Load scenario
        scenario = None
        if self.scenarios_file.exists():
            with open(self.scenarios_file, "r") as f:
                for line in f:
                    s = json.loads(line)
                    if s["scenario_id"] == scenario_id:
                        scenario = SimulationScenario(**s)
                        break

        if not scenario:
            raise ValueError(f"Scenario {scenario_id} not found")

        # Simple detector if none provided
        if detector_function is None:
            def simple_detector(tx: Dict) -> bool:
                # Heuristic: large CASH_OUT or balance mismatch
                if tx["type"] == "CASH_OUT" and tx["amount"] > 50000:
                    return True
                expected_dest = tx["oldbalanceDest"] + tx["amount"]
                if abs(expected_dest - tx["newbalanceDest"]) > tx["amount"] * 0.2:
                    return True
                return False
            detector_function = simple_detector

        # Run detection on each transaction
        tp = 0  # True positives
        fp = 0  # False positives
        tn = 0  # True negatives
        fn = 0  # False negatives

        for tx in scenario.transactions:
            tx_dict = tx.model_dump()
            predicted_fraud = detector_function(tx_dict)

            if tx.is_fraud and predicted_fraud:
                tp += 1
            elif tx.is_fraud and not predicted_fraud:
                fn += 1
            elif not tx.is_fraud and predicted_fraud:
                fp += 1
            else:
                tn += 1

        # Calculate metrics
        total = len(scenario.transactions)
        accuracy = (tp + tn) / total if total > 0 else 0.0
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

        # Performance rating
        if f1 >= 0.9:
            performance = "excellent"
        elif f1 >= 0.75:
            performance = "good"
        elif f1 >= 0.6:
            performance = "fair"
        else:
            performance = "poor"

        result = SimulationResult(
            scenario_id=scenario_id,
            total_transactions=total,
            detected_fraud=tp,
            missed_fraud=fn,
            false_positives=fp,
            true_negatives=tn,
            accuracy=accuracy,
            precision=precision,
            recall=recall,
            f1_score=f1,
            agent_performance=performance
        )

        # Save result
        with open(self.results_file, "a") as f:
            f.write(result.model_dump_json() + "\n")

        logger.info(f"Simulation complete: {scenario_id}, F1={f1:.2f}")
        return result

    def get_safe_exploration_space(self) -> Dict[str, Any]:
        """Get parameters for safe exploration"""
        return {
            "transaction_types": [t.value for t in TransactionType],
            "amount_ranges": {
                "micro": (1, 100),
                "small": (100, 1000),
                "medium": (1000, 10000),
                "large": (10000, 100000),
                "very_large": (100000, 1000000)
            },
            "fraud_scenarios": [s.value for s in FraudScenarioType],
            "difficulty_levels": list(range(1, 6)),
            "safe_limits": {
                "max_transactions_per_batch": 10000,
                "max_amount": 10000000,
                "max_scenario_duration_minutes": 60
            },
            "recommended_practice": {
                "start_difficulty": 1,
                "gradual_increase": True,
                "validate_before_production": True,
                "test_adversarial_scenarios": True
            }
        }

    def get_simulation_stats(self) -> Dict[str, Any]:
        """Get statistics about simulations run"""
        scenarios_run = 0
        avg_f1 = []

        if self.results_file.exists():
            with open(self.results_file, "r") as f:
                for line in f:
                    result = json.loads(line)
                    scenarios_run += 1
                    avg_f1.append(result["f1_score"])

        return {
            "total_scenarios_run": scenarios_run,
            "average_f1_score": sum(avg_f1) / len(avg_f1) if avg_f1 else 0.0,
            "best_f1_score": max(avg_f1) if avg_f1 else 0.0,
            "worst_f1_score": min(avg_f1) if avg_f1 else 0.0
        }


# Global instance
simulation_env = FraudSimulationEnvironment()
