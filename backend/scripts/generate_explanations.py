"""Generate LLM explanations for fraud cases in PaySim dataset.

This script creates detailed explanations for fraud transactions to support:
1. Model interpretability
2. Fine-tuning data for LLM reasoning
3. Preference pair generation (RLHF)
4. Human review documentation

Author: FinSight AI Team
Date: December 28, 2025
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
from tqdm import tqdm

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class FraudExplanationGenerator:
    """Generate structured LLM explanations for fraud transactions.

    This class implements the explanation generation strategy for Section 2.4
    of the WBS (Data Labeling & Annotation).
    """

    def __init__(self, data_path: str, output_dir: str) -> None:
        """Initialize the explanation generator.

        Args:
            data_path: Path to cleaned dataset
            output_dir: Directory to save explanations
        """
        self.data_path = Path(data_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Load fraud policies for context
        self.fraud_policies = self._load_fraud_policies()

    def _load_fraud_policies(self) -> Dict[str, str]:
        """Load fraud policy documents for reference.

        Returns:
            Dict mapping transaction type to policy text
        """
        policy_dir = Path(__file__).parent.parent.parent / "data/fraud_policies"
        policies = {}

        if policy_dir.exists():
            for policy_file in policy_dir.glob("*.md"):
                with open(policy_file, "r") as f:
                    policies[policy_file.stem] = f.read()

        return policies

    def _get_fraud_reason(self, row: pd.Series) -> str:
        """Determine fraud reason based on transaction features.

        Args:
            row: Transaction row

        Returns:
            str: Fraud reason code
        """
        reasons = []

        # High-value transaction
        if row.get("is_high_value", 0) == 1:
            reasons.append("HIGH_VALUE")

        # Complete account drainage
        if row.get("zero_balance_orig", 0) == 1:
            reasons.append("ACCOUNT_DRAINAGE")

        # High amount-to-balance ratio (>95%)
        if row.get("amount_to_balance_ratio", 0) > 0.95:
            reasons.append("LIQUIDATION")

        # Balance inconsistency
        if row.get("balance_inconsistency", 0) == 1:
            reasons.append("BALANCE_ANOMALY")

        # Round amount (structuring pattern)
        if row.get("is_round_amount", 0) == 1:
            reasons.append("ROUND_AMOUNT")

        # Midnight transaction (suspicious timing)
        if row.get("hour", 12) in [0, 1, 2, 3, 24]:
            reasons.append("SUSPICIOUS_TIMING")

        # Transfer to cash-out pattern (if detectable)
        if row["type"] == "TRANSFER":
            reasons.append("TRANSFER_FRAUD")
        elif row["type"] == "CASH_OUT":
            reasons.append("CASHOUT_FRAUD")

        # Default if no specific reason
        if not reasons:
            reasons.append("FLAGGED_BY_SYSTEM")

        return "_".join(reasons)

    def generate_explanation(self, row: pd.Series) -> Dict:
        """Generate detailed explanation for a fraud transaction.

        Args:
            row: Transaction row from dataset

        Returns:
            Dict containing structured explanation
        """
        fraud_reason = self._get_fraud_reason(row)

        # Build explanation components
        explanation = {
            "transaction_id": f"TXN_{row.name}",  # Use index as ID
            "type": row["type"],
            "amount": float(row["amount"]),
            "is_fraud": int(row["isFraud"]),
            "is_flagged": int(row.get("isFlaggedFraud", 0)),
            "fraud_reason_code": fraud_reason,
            # Detailed explanation
            "explanation": self._build_explanation_text(row, fraud_reason),
            # Risk factors
            "risk_factors": self._extract_risk_factors(row),
            # Decision rationale
            "decision": "BLOCK" if row["isFraud"] == 1 else "APPROVE",
            "confidence": self._calculate_confidence(row),
            # Supporting evidence
            "evidence": self._extract_evidence(row),
            # Recommended actions
            "recommendations": self._get_recommendations(row, fraud_reason),
        }

        return explanation

    def _build_explanation_text(self, row: pd.Series, fraud_reason: str) -> str:
        """Build human-readable explanation text.

        Args:
            row: Transaction row
            fraud_reason: Fraud reason code

        Returns:
            str: Explanation text
        """
        amount = row["amount"]
        txn_type = row["type"]
        hour = row.get("hour", "unknown")

        # Base explanation
        base = f"This ${amount:,.2f} {txn_type} transaction is classified as FRAUDULENT. "

        # Reason-specific details
        if "HIGH_VALUE" in fraud_reason:
            base += (
                f"The transaction amount exceeds the 99th percentile threshold, "
                f"which is associated with a 24× higher fraud rate. "
            )

        if "ACCOUNT_DRAINAGE" in fraud_reason:
            base += (
                f"The origin account balance was completely drained to zero, "
                f"a strong indicator of account takeover or liquidation fraud. "
            )

        if "LIQUIDATION" in fraud_reason:
            amt_ratio = row.get("amount_to_balance_ratio", 0)
            base += (
                f"The transaction amount ({amt_ratio:.1%} of account balance) "
                f"suggests an attempt to liquidate the entire account. "
            )

        if "BALANCE_ANOMALY" in fraud_reason:
            base += (
                f"The transaction shows balance inconsistencies that violate "
                f"expected accounting rules, indicating potential manipulation. "
            )

        if "ROUND_AMOUNT" in fraud_reason:
            base += (
                f"The exact round-number amount (${amount:,.0f}) is a known "
                f"fraud pattern used in structuring attacks. "
            )

        if "SUSPICIOUS_TIMING" in fraud_reason:
            base += (
                f"The transaction occurred at {hour}:00 (late night/early morning), "
                f"a time period associated with higher fraud rates. "
            )

        # Add fraud type context
        if "TRANSFER_FRAUD" in fraud_reason:
            base += (
                "TRANSFER transactions have a 0.77% fraud rate, 6× higher than "
                "the dataset average. "
            )
        elif "CASHOUT_FRAUD" in fraud_reason:
            base += (
                "CASH_OUT transactions have a 0.18% fraud rate and are frequently "
                "used as the final step in money laundering chains. "
            )

        # Final recommendation
        base += (
            "Based on these indicators, the system recommends BLOCKING this "
            "transaction and escalating to fraud investigation team."
        )

        return base

    def _extract_risk_factors(self, row: pd.Series) -> List[Dict]:
        """Extract risk factors with severity scores.

        Args:
            row: Transaction row

        Returns:
            List of risk factor dictionaries
        """
        factors = []

        # High value
        if row.get("is_high_value", 0) == 1:
            factors.append(
                {
                    "factor": "high_value_transaction",
                    "severity": "HIGH",
                    "value": float(row["amount"]),
                    "threshold": 1615979.50,
                }
            )

        # Zero balance
        if row.get("zero_balance_orig", 0) == 1:
            factors.append(
                {
                    "factor": "account_drainage",
                    "severity": "CRITICAL",
                    "old_balance": float(row.get("oldbalanceOrg", 0)),
                    "new_balance": 0.0,
                }
            )

        # High ratio
        ratio = row.get("amount_to_balance_ratio", 0)
        if ratio > 0.95:
            factors.append(
                {
                    "factor": "liquidation_attempt",
                    "severity": "HIGH",
                    "ratio": float(ratio),
                    "threshold": 0.95,
                }
            )

        # Balance inconsistency
        if row.get("balance_inconsistency", 0) == 1:
            factors.append(
                {
                    "factor": "balance_anomaly",
                    "severity": "MEDIUM",
                    "expected": float(row.get("oldbalanceOrg", 0) - row["amount"]),
                    "actual": float(row.get("newbalanceOrig", 0)),
                }
            )

        # Round amount
        if row.get("is_round_amount", 0) == 1:
            factors.append(
                {
                    "factor": "round_number_structuring",
                    "severity": "MEDIUM",
                    "amount": float(row["amount"]),
                }
            )

        # Suspicious timing
        hour = row.get("hour", 12)
        if hour in [0, 1, 2, 3]:
            factors.append(
                {
                    "factor": "suspicious_timing",
                    "severity": "LOW",
                    "hour": int(hour),
                    "risk_window": "00:00-03:59",
                }
            )

        return factors

    def _calculate_confidence(self, row: pd.Series) -> float:
        """Calculate confidence score for fraud decision.

        Args:
            row: Transaction row

        Returns:
            float: Confidence score (0-1)
        """
        # Start with base confidence
        confidence = 0.60

        # Add confidence for each strong indicator
        if row.get("zero_balance_orig", 0) == 1:
            confidence += 0.15

        if row.get("is_high_value", 0) == 1:
            confidence += 0.10

        if row.get("amount_to_balance_ratio", 0) > 0.95:
            confidence += 0.10

        if row.get("isFlaggedFraud", 0) == 1:
            confidence += 0.05

        # Cap at 0.99 (never 100% certain)
        return min(confidence, 0.99)

    def _extract_evidence(self, row: pd.Series) -> Dict:
        """Extract supporting evidence for decision.

        Args:
            row: Transaction row

        Returns:
            Dict of evidence fields
        """
        return {
            "transaction_type": row["type"],
            "amount": float(row["amount"]),
            "amount_normalized": float(row.get("amount_normalized", 0)),
            "old_balance_origin": float(row.get("oldbalanceOrg", 0)),
            "new_balance_origin": float(row.get("newbalanceOrig", 0)),
            "old_balance_dest": float(row.get("oldbalanceDest", 0)),
            "new_balance_dest": float(row.get("newbalanceDest", 0)),
            "hour_of_day": int(row.get("hour", 0)),
            "day_of_week": int(row.get("day_of_week", 0)),
            "flagged_by_system": bool(row.get("isFlaggedFraud", 0)),
        }

    def _get_recommendations(self, row: pd.Series, fraud_reason: str) -> List[str]:
        """Get recommended actions for this fraud case.

        Args:
            row: Transaction row
            fraud_reason: Fraud reason code

        Returns:
            List of recommended actions
        """
        recommendations = []

        # Always block confirmed fraud
        recommendations.append("BLOCK transaction immediately")

        # Account-specific actions
        if "ACCOUNT_DRAINAGE" in fraud_reason or "LIQUIDATION" in fraud_reason:
            recommendations.append("Freeze origin account pending investigation")
            recommendations.append("Contact account holder for verification")

        # Investigation actions
        if row.get("is_high_value", 0) == 1:
            recommendations.append("Escalate to senior fraud analyst (high-value)")

        if "BALANCE_ANOMALY" in fraud_reason:
            recommendations.append("Audit transaction processing system for errors")

        # Pattern detection
        if row["type"] == "TRANSFER":
            recommendations.append("Monitor destination account for cash-out attempts")

        # Regulatory
        if row["amount"] > 10000:
            recommendations.append("File Suspicious Activity Report (SAR) if confirmed")

        return recommendations

    def generate_all_explanations(
        self,
        limit: Optional[int] = None,
    ) -> pd.DataFrame:
        """Generate explanations for all fraud transactions.

        Args:
            limit: Maximum number of fraud cases to process (None = all)

        Returns:
            pd.DataFrame: Explanations dataframe
        """
        logger.info(f"Loading data from {self.data_path}")
        df = pd.read_csv(self.data_path)

        # Filter to fraud cases only
        fraud_df = df[df["isFraud"] == 1].copy()
        logger.info(f"Found {len(fraud_df):,} fraud transactions")

        if limit:
            fraud_df = fraud_df.head(limit)
            logger.info(f"Processing first {limit} fraud cases")

        # Generate explanations
        explanations = []
        for idx, row in tqdm(
            fraud_df.iterrows(), total=len(fraud_df), desc="Generating explanations"
        ):
            explanation = self.generate_explanation(row)
            explanations.append(explanation)

        # Convert to dataframe
        explanations_df = pd.DataFrame(explanations)

        # Save to JSON (better for nested structures)
        output_path = self.output_dir / "fraud_explanations.json"
        with open(output_path, "w") as f:
            json.dump(explanations, f, indent=2)
        logger.info(f"✓ Saved {len(explanations):,} explanations to {output_path}")

        # Save summary CSV
        summary_df = explanations_df[
            ["transaction_id", "type", "amount", "fraud_reason_code", "decision", "confidence"]
        ]
        summary_path = self.output_dir / "fraud_explanations_summary.csv"
        summary_df.to_csv(summary_path, index=False)
        logger.info(f"✓ Saved summary to {summary_path}")

        return explanations_df


def main() -> None:
    """Main entry point for explanation generation."""
    # Setup paths
    project_root = Path(__file__).parent.parent.parent
    data_path = project_root / "data/processed/paysim_cleaned.csv"
    output_dir = project_root / "data/annotations"

    # Check if cleaned data exists
    if not data_path.exists():
        logger.error(f"Cleaned data not found: {data_path}")
        logger.info("Please run data_cleaning.py first")
        return

    # Generate explanations
    generator = FraudExplanationGenerator(
        data_path=str(data_path),
        output_dir=str(output_dir),
    )

    # Generate explanations for all fraud cases (or limit for testing)
    explanations_df = generator.generate_all_explanations(limit=100)  # First 100 for demo

    # Display sample
    print("\n" + "=" * 80)
    print("SAMPLE FRAUD EXPLANATIONS")
    print("=" * 80)
    print(explanations_df[["transaction_id", "fraud_reason_code", "confidence"]].head(10))
    print(f"\nTotal explanations generated: {len(explanations_df):,}")


if __name__ == "__main__":
    main()
