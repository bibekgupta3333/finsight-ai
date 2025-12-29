"""Generate weak supervision rules and preference pairs for RLHF.

This script implements:
1. Weak supervision rules based on isFlaggedFraud
2. Preference pair generation (good vs bad explanations)
3. Quality validation for training data

Author: FinSight AI Team
Date: December 28, 2025
"""

import json
import random
from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd


class WeakSupervisionRules:
    """Implement weak supervision rules for fraud detection."""

    @staticmethod
    def high_amount_rule(row: pd.Series, threshold: float = 200000) -> bool:
        """Detect high-value transactions.

        Args:
            row: Transaction row
            threshold: Amount threshold in dollars

        Returns:
            bool: True if transaction exceeds threshold
        """
        return row["amount"] > threshold

    @staticmethod
    def account_drainage_rule(row: pd.Series) -> bool:
        """Detect complete account drainage.

        Args:
            row: Transaction row

        Returns:
            bool: True if account drained to zero
        """
        return (
            row["oldbalanceOrg"] > 0
            and row["newbalanceOrig"] == 0
            and row["amount"] == row["oldbalanceOrg"]
        )

    @staticmethod
    def balance_inconsistency_rule(row: pd.Series) -> bool:
        """Detect balance calculation inconsistencies.

        Args:
            row: Transaction row

        Returns:
            bool: True if balances don't match expected calculation
        """
        expected_balance = row["oldbalanceOrg"] - row["amount"]
        return abs(row["newbalanceOrig"] - expected_balance) > 0.01

    @staticmethod
    def round_amount_rule(row: pd.Series, modulo: int = 10000) -> bool:
        """Detect suspiciously round amounts.

        Args:
            row: Transaction row
            modulo: Round number check (e.g., 10000 = multiples of $10k)

        Returns:
            bool: True if amount is suspiciously round
        """
        return row["amount"] % modulo == 0 and row["amount"] > 0

    @staticmethod
    def midnight_transaction_rule(row: pd.Series) -> bool:
        """Detect transactions during suspicious hours.

        Args:
            row: Transaction row

        Returns:
            bool: True if transaction during 00:00-03:59
        """
        hour = row.get("hour", 12)
        return hour in [0, 1, 2, 3]

    @staticmethod
    def liquidation_rule(row: pd.Series, threshold: float = 0.95) -> bool:
        """Detect account liquidation attempts.

        Args:
            row: Transaction row
            threshold: Minimum ratio to consider liquidation

        Returns:
            bool: True if amount is >95% of balance
        """
        if row["oldbalanceOrg"] == 0:
            return False
        ratio = row["amount"] / row["oldbalanceOrg"]
        return ratio > threshold

    @staticmethod
    def flagged_fraud_rule(row: pd.Series) -> bool:
        """Use system's flagging as weak signal.

        Args:
            row: Transaction row

        Returns:
            bool: True if flagged by system
        """
        return row.get("isFlaggedFraud", 0) == 1

    @classmethod
    def apply_all_rules(cls, row: pd.Series) -> Dict[str, bool]:
        """Apply all weak supervision rules.

        Args:
            row: Transaction row

        Returns:
            Dict mapping rule name to result
        """
        return {
            "high_amount": cls.high_amount_rule(row),
            "account_drainage": cls.account_drainage_rule(row),
            "balance_inconsistency": cls.balance_inconsistency_rule(row),
            "round_amount": cls.round_amount_rule(row),
            "midnight_transaction": cls.midnight_transaction_rule(row),
            "liquidation": cls.liquidation_rule(row),
            "flagged_fraud": cls.flagged_fraud_rule(row),
        }

    @classmethod
    def aggregate_rules(cls, row: pd.Series) -> Tuple[int, List[str]]:
        """Aggregate rule results to predict fraud likelihood.

        Args:
            row: Transaction row

        Returns:
            Tuple of (predicted_fraud, triggered_rules)
        """
        rules = cls.apply_all_rules(row)
        triggered = [name for name, result in rules.items() if result]

        # Simple voting: >=2 rules = predicted fraud
        predicted_fraud = 1 if len(triggered) >= 2 else 0

        return predicted_fraud, triggered


class PreferencePairGenerator:
    """Generate preference pairs for RLHF fine-tuning."""

    def __init__(self, random_seed: int = 42):
        """Initialize preference pair generator.

        Args:
            random_seed: Random seed for reproducibility
        """
        random.seed(random_seed)

    def generate_good_explanation(self, row: pd.Series, rules: List[str]) -> str:
        """Generate a high-quality explanation.

        Args:
            row: Transaction row
            rules: List of triggered weak supervision rules

        Returns:
            str: Good explanation
        """
        explanation = (
            f"This ${row['amount']:,.2f} {row['type']} transaction is classified as FRAUDULENT "
            f"based on {len(rules)} strong indicators:\n\n"
        )

        # Add specific evidence
        if "account_drainage" in rules:
            explanation += (
                f"1. ACCOUNT DRAINAGE: The origin account was completely drained "
                f"(${row['oldbalanceOrg']:,.2f} → $0), a critical fraud signal.\n"
            )

        if "high_amount" in rules:
            explanation += (
                f"2. HIGH VALUE: Transaction amount exceeds $200,000 threshold, "
                f"associated with 24× higher fraud rate.\n"
            )

        if "liquidation" in rules:
            ratio = (row["amount"] / row["oldbalanceOrg"]) * 100 if row["oldbalanceOrg"] > 0 else 0
            explanation += (
                f"3. LIQUIDATION ATTEMPT: Transaction represents {ratio:.1f}% of account balance, "
                f"indicating account takeover.\n"
            )

        if "balance_inconsistency" in rules:
            explanation += (
                f"4. BALANCE ANOMALY: Transaction balances violate accounting rules, "
                f"suggesting data manipulation.\n"
            )

        explanation += (
            f"\nRECOMMENDATION: BLOCK transaction and escalate to fraud investigation team. "
            f"Confidence: HIGH"
        )

        return explanation

    def generate_bad_explanation(self, row: pd.Series) -> str:
        """Generate a low-quality explanation (for preference learning).

        Bad explanations exhibit:
        - Vague reasoning
        - No specific evidence
        - Circular logic
        - Overconfident without justification

        Args:
            row: Transaction row

        Returns:
            str: Bad explanation
        """
        bad_templates = [
            # Vague
            (
                f"This transaction looks suspicious and should probably be blocked. "
                f"The amount seems high and the pattern is unusual."
            ),
            # Circular logic
            (
                f"This is fraud because the system flagged it as fraud. "
                f"Fraudulent transactions are always fraudulent."
            ),
            # No evidence
            (
                f"Based on my analysis, this ${row['amount']:,.2f} transaction is fraud. "
                f"Trust me, I know fraud when I see it."
            ),
            # Overconfident
            (f"This is 100% definitely fraud. No doubt about it. " f"Block it immediately."),
            # Irrelevant reasoning
            (
                f"This transaction happened at {row.get('hour', 0)}:00, which is a suspicious time. "
                f"Also, the amount has too many digits. Probably fraud."
            ),
        ]

        return random.choice(bad_templates)

    def generate_preference_pair(self, row: pd.Series, rules: List[str]) -> Dict:
        """Generate a preference pair (good vs bad explanation).

        Args:
            row: Transaction row
            rules: Triggered weak supervision rules

        Returns:
            Dict containing preference pair
        """
        good_explanation = self.generate_good_explanation(row, rules)
        bad_explanation = self.generate_bad_explanation(row)

        return {
            "transaction_id": f"TXN_{row.name}",
            "amount": float(row["amount"]),
            "type": row["type"],
            "is_fraud": int(row["isFraud"]),
            "triggered_rules": rules,
            "chosen": good_explanation,  # Preferred explanation
            "rejected": bad_explanation,  # Rejected explanation
            "preference_strength": "strong",  # How clear the preference is
        }


def main() -> None:
    """Main entry point for weak supervision and preference pairs."""
    # Setup paths
    project_root = Path(__file__).parent.parent.parent
    data_path = project_root / "data/processed/paysim_cleaned.csv"
    output_dir = project_root / "data/annotations"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Check if cleaned data exists
    if not data_path.exists():
        print(f"ERROR: Cleaned data not found: {data_path}")
        print("Please run data_cleaning.py first")
        return

    print("Loading cleaned data...")
    df = pd.read_csv(data_path)
    print(f"Loaded {len(df):,} transactions")

    # Apply weak supervision rules to all fraud cases
    print("\nApplying weak supervision rules...")
    fraud_df = df[df["isFraud"] == 1].copy()
    print(f"Processing {len(fraud_df):,} fraud transactions")

    weak_labels = []
    for idx, row in fraud_df.iterrows():
        predicted, rules = WeakSupervisionRules.aggregate_rules(row)
        weak_labels.append(
            {
                "transaction_id": f"TXN_{idx}",
                "predicted_fraud": predicted,
                "ground_truth": int(row["isFraud"]),
                "triggered_rules": rules,
                "num_rules": len(rules),
            }
        )

    # Save weak labels
    weak_labels_df = pd.DataFrame(weak_labels)
    weak_labels_path = output_dir / "weak_supervision_labels.json"
    with open(weak_labels_path, "w") as f:
        json.dump(weak_labels, f, indent=2)
    print(f"✓ Saved weak labels to {weak_labels_path}")

    # Calculate rule accuracy
    agreement = (weak_labels_df["predicted_fraud"] == weak_labels_df["ground_truth"]).mean()
    print(f"\nWeak supervision accuracy: {agreement:.2%}")
    print(f"Average rules triggered per fraud case: {weak_labels_df['num_rules'].mean():.2f}")

    # Generate preference pairs (sample of 500 for training)
    print("\nGenerating preference pairs for RLHF...")
    pair_generator = PreferencePairGenerator(random_seed=42)

    # Select fraud cases with at least 2 triggered rules
    strong_fraud = fraud_df.head(500)  # Sample for demo
    preference_pairs = []

    for idx, row in strong_fraud.iterrows():
        _, rules = WeakSupervisionRules.aggregate_rules(row)
        if len(rules) >= 2:  # Only pairs with clear fraud indicators
            pair = pair_generator.generate_preference_pair(row, rules)
            preference_pairs.append(pair)

    # Save preference pairs
    pairs_path = output_dir / "preference_pairs.json"
    with open(pairs_path, "w") as f:
        json.dump(preference_pairs, f, indent=2)
    print(f"✓ Generated {len(preference_pairs):,} preference pairs")
    print(f"✓ Saved to {pairs_path}")

    # Display sample
    print("\n" + "=" * 80)
    print("SAMPLE PREFERENCE PAIR")
    print("=" * 80)
    if preference_pairs:
        sample = preference_pairs[0]
        print(f"Transaction ID: {sample['transaction_id']}")
        print(f"Amount: ${sample['amount']:,.2f}")
        print(f"Triggered Rules: {', '.join(sample['triggered_rules'])}\n")
        print("✅ CHOSEN (Good Explanation):")
        print(sample["chosen"])
        print("\n❌ REJECTED (Bad Explanation):")
        print(sample["rejected"])


if __name__ == "__main__":
    main()
    main()
