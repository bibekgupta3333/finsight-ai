"""
Bias and Fairness Analysis for Fraud Detection System.

This script performs comprehensive bias and fairness audits on the fraud detection
dataset to identify potential biases, discrimination patterns, and fairness issues.

Key Analyses:
1. High-amount vs fraud correlation audit
2. Transaction type bias analysis
3. False positive/negative patterns by amount
4. Statistical parity metrics
5. Fairness constraint recommendations

Author: FinSight AI Team
Date: December 2025
"""

import json
import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy import stats
from sklearn.metrics import classification_report, confusion_matrix

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
ANALYSIS_DIR = DATA_DIR / "analysis"
SPLITS_DIR = DATA_DIR / "splits" / "stratified"


class BiasFairnessAnalyzer:
    """
    Comprehensive bias and fairness analysis for fraud detection.

    Analyzes potential biases across:
    - Transaction amounts
    - Transaction types
    - Account balance levels
    - Temporal patterns
    """

    def __init__(
        self,
        random_seed: int = 42,
        amount_percentiles: List[int] = [25, 50, 75, 90, 95, 99],
    ):
        """
        Initialize bias analyzer.

        Args:
            random_seed: Random seed for reproducibility
            amount_percentiles: Percentiles to use for amount-based analysis
        """
        self.random_seed = random_seed
        self.amount_percentiles = amount_percentiles
        self.report = {
            "metadata": {},
            "correlations": {},
            "biases": {},
            "fairness_metrics": {},
            "recommendations": [],
        }

        np.random.seed(random_seed)

    def load_data(self, data_path: Path) -> pd.DataFrame:
        """Load and prepare data for analysis."""
        logger.info(f"Loading data from {data_path}")
        df = pd.read_csv(data_path)
        logger.info(f"Loaded {len(df):,} transactions")

        # Store metadata
        self.report["metadata"] = {
            "total_transactions": len(df),
            "fraud_count": int(df["isFraud"].sum()),
            "fraud_rate": float(df["isFraud"].mean()),
            "data_path": str(data_path),
        }

        return df

    def analyze_amount_fraud_correlation(self, df: pd.DataFrame) -> Dict[str, any]:
        """
        Audit correlation between high amounts and fraud.

        Tests hypothesis: "High-amount transactions are more likely to be fraud"
        This could lead to bias against legitimate high-value transactions.
        """
        logger.info("=" * 80)
        logger.info("ANALYZING AMOUNT-FRAUD CORRELATION")
        logger.info("=" * 80)

        results = {}

        # 1. Pearson correlation
        correlation = df[["amount", "isFraud"]].corr().iloc[0, 1]
        results["pearson_correlation"] = float(correlation)
        logger.info(f"Pearson correlation (amount vs fraud): {correlation:.4f}")

        # 2. Point-biserial correlation (for binary-continuous)
        point_biserial = stats.pointbiserialr(df["isFraud"], df["amount"])
        results["point_biserial_r"] = float(point_biserial.correlation)
        results["point_biserial_p"] = float(point_biserial.pvalue)
        logger.info(
            f"Point-biserial correlation: r={point_biserial.correlation:.4f}, "
            f"p={point_biserial.pvalue:.4e}"
        )

        # 3. Amount distribution by fraud status
        fraud_amounts = df[df["isFraud"] == 1]["amount"]
        legit_amounts = df[df["isFraud"] == 0]["amount"]

        results["fraud_mean_amount"] = float(fraud_amounts.mean())
        results["legit_mean_amount"] = float(legit_amounts.mean())
        results["fraud_median_amount"] = float(fraud_amounts.median())
        results["legit_median_amount"] = float(legit_amounts.median())

        logger.info(f"\nFraud transactions:")
        logger.info(f"  Mean: ${fraud_amounts.mean():,.2f}")
        logger.info(f"  Median: ${fraud_amounts.median():,.2f}")
        logger.info(f"\nLegitimate transactions:")
        logger.info(f"  Mean: ${legit_amounts.mean():,.2f}")
        logger.info(f"  Median: ${legit_amounts.median():,.2f}")

        # 4. Mann-Whitney U test (non-parametric)
        u_stat, u_p = stats.mannwhitneyu(fraud_amounts, legit_amounts)
        results["mann_whitney_u"] = float(u_stat)
        results["mann_whitney_p"] = float(u_p)
        logger.info(f"\nMann-Whitney U test: U={u_stat:.2e}, p={u_p:.4e}")

        # 5. Fraud rate by amount percentile
        percentile_analysis = []
        for percentile in self.amount_percentiles:
            threshold = df["amount"].quantile(percentile / 100)
            high_amount = df[df["amount"] >= threshold]
            low_amount = df[df["amount"] < threshold]

            high_fraud_rate = high_amount["isFraud"].mean()
            low_fraud_rate = low_amount["isFraud"].mean()

            percentile_analysis.append(
                {
                    "percentile": percentile,
                    "threshold": float(threshold),
                    "high_amount_fraud_rate": float(high_fraud_rate),
                    "low_amount_fraud_rate": float(low_fraud_rate),
                    "ratio": (
                        float(high_fraud_rate / low_fraud_rate) if low_fraud_rate > 0 else None
                    ),
                }
            )

            logger.info(
                f"\nP{percentile} (≥${threshold:,.0f}):"
                f"\n  High amount fraud rate: {high_fraud_rate:.4%}"
                f"\n  Low amount fraud rate: {low_fraud_rate:.4%}"
                f"\n  Ratio: {high_fraud_rate/low_fraud_rate:.2f}x"
                if low_fraud_rate > 0
                else "\n  Ratio: N/A"
            )

        results["percentile_analysis"] = percentile_analysis

        # Interpretation
        if abs(correlation) < 0.1:
            interpretation = "WEAK - Little correlation between amount and fraud"
        elif abs(correlation) < 0.3:
            interpretation = "MODERATE - Some correlation exists"
        else:
            interpretation = "STRONG - Significant correlation detected"

        results["interpretation"] = interpretation
        logger.info(f"\n⚠️  Correlation Strength: {interpretation}")

        self.report["correlations"]["amount_fraud"] = results
        return results

    def analyze_transaction_type_bias(self, df: pd.DataFrame) -> Dict[str, any]:
        """
        Analyze bias across different transaction types.

        Checks if certain transaction types are unfairly associated with fraud.
        """
        logger.info("\n" + "=" * 80)
        logger.info("ANALYZING TRANSACTION TYPE BIAS")
        logger.info("=" * 80)

        results = {}
        type_analysis = []

        for tx_type in df["type"].unique():
            type_data = df[df["type"] == tx_type]
            fraud_rate = type_data["isFraud"].mean()
            count = len(type_data)
            fraud_count = type_data["isFraud"].sum()

            type_analysis.append(
                {
                    "type": tx_type,
                    "count": int(count),
                    "fraud_count": int(fraud_count),
                    "fraud_rate": float(fraud_rate),
                    "percentage_of_total": float(count / len(df)),
                }
            )

            logger.info(
                f"\n{tx_type}:"
                f"\n  Count: {count:,} ({count/len(df):.2%})"
                f"\n  Fraud rate: {fraud_rate:.4%}"
                f"\n  Fraud count: {fraud_count:,}"
            )

        results["type_analysis"] = type_analysis

        # Chi-square test for independence
        contingency = pd.crosstab(df["type"], df["isFraud"])
        chi2, p_value, dof, expected = stats.chi2_contingency(contingency)

        results["chi_square"] = {
            "statistic": float(chi2),
            "p_value": float(p_value),
            "degrees_of_freedom": int(dof),
        }

        logger.info(
            f"\nChi-square test (type independence):"
            f"\n  χ² = {chi2:.2f}"
            f"\n  p-value = {p_value:.4e}"
            f"\n  df = {dof}"
        )

        if p_value < 0.05:
            logger.warning(
                "⚠️  BIAS DETECTED: Transaction type is significantly "
                "associated with fraud (p < 0.05)"
            )
            results["bias_detected"] = True
        else:
            logger.info("✓ No significant bias detected across transaction types")
            results["bias_detected"] = False

        self.report["biases"]["transaction_type"] = results
        return results

    def analyze_false_positive_negative_patterns(self, df: pd.DataFrame) -> Dict[str, any]:
        """
        Analyze potential false positive/negative patterns by amount.

        Since we don't have predictions yet, we simulate a simple rule-based
        classifier to understand potential biases.
        """
        logger.info("\n" + "=" * 80)
        logger.info("ANALYZING FALSE POSITIVE/NEGATIVE PATTERNS")
        logger.info("=" * 80)

        results = {}

        # Simulate simple rule-based predictions
        # Rule: Flag as fraud if amount > 90th percentile OR isFlaggedFraud == 1
        amount_threshold = df["amount"].quantile(0.90)
        df["predicted_fraud"] = (
            (df["amount"] >= amount_threshold) | (df["isFlaggedFraud"] == 1)
        ).astype(int)

        logger.info(f"Using rule-based classifier:")
        logger.info(f"  Amount threshold: ${amount_threshold:,.2f} (P90)")
        logger.info(f"  Rule: amount ≥ threshold OR isFlaggedFraud == 1")

        # Confusion matrix
        cm = confusion_matrix(df["isFraud"], df["predicted_fraud"])
        tn, fp, fn, tp = cm.ravel()

        results["confusion_matrix"] = {
            "true_negative": int(tn),
            "false_positive": int(fp),
            "false_negative": int(fn),
            "true_positive": int(tp),
        }

        logger.info(f"\nConfusion Matrix:")
        logger.info(f"  True Negative (TN): {tn:,}")
        logger.info(f"  False Positive (FP): {fp:,}")
        logger.info(f"  False Negative (FN): {fn:,}")
        logger.info(f"  True Positive (TP): {tp:,}")

        # Metrics
        fpr = fp / (fp + tn) if (fp + tn) > 0 else 0
        fnr = fn / (fn + tp) if (fn + tp) > 0 else 0
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0

        results["metrics"] = {
            "false_positive_rate": float(fpr),
            "false_negative_rate": float(fnr),
            "precision": float(precision),
            "recall": float(recall),
        }

        logger.info(f"\nMetrics:")
        logger.info(f"  False Positive Rate: {fpr:.4%}")
        logger.info(f"  False Negative Rate: {fnr:.4%}")
        logger.info(f"  Precision: {precision:.4%}")
        logger.info(f"  Recall: {recall:.4%}")

        # Analyze FP/FN by amount quartiles
        df["amount_quartile"] = pd.qcut(
            df["amount"], q=4, labels=["Q1 (Low)", "Q2", "Q3", "Q4 (High)"]
        )

        quartile_analysis = []
        for quartile in df["amount_quartile"].unique():
            q_data = df[df["amount_quartile"] == quartile]

            # Calculate FP/FN for this quartile
            q_cm = confusion_matrix(q_data["isFraud"], q_data["predicted_fraud"])
            q_tn, q_fp, q_fn, q_tp = q_cm.ravel()

            q_fpr = q_fp / (q_fp + q_tn) if (q_fp + q_tn) > 0 else 0
            q_fnr = q_fn / (q_fn + q_tp) if (q_fn + q_tp) > 0 else 0

            quartile_analysis.append(
                {
                    "quartile": str(quartile),
                    "count": int(len(q_data)),
                    "false_positive_rate": float(q_fpr),
                    "false_negative_rate": float(q_fnr),
                    "fp_count": int(q_fp),
                    "fn_count": int(q_fn),
                }
            )

            logger.info(
                f"\n{quartile}:"
                f"\n  Count: {len(q_data):,}"
                f"\n  FPR: {q_fpr:.4%} ({q_fp:,} cases)"
                f"\n  FNR: {q_fnr:.4%} ({q_fn:,} cases)"
            )

        results["quartile_analysis"] = quartile_analysis

        # Check for disparate impact
        high_amount_fpr = df[df["amount_quartile"] == "Q4 (High)"]["predicted_fraud"].mean()
        low_amount_fpr = df[df["amount_quartile"] == "Q1 (Low)"]["predicted_fraud"].mean()
        disparate_impact_ratio = low_amount_fpr / high_amount_fpr if high_amount_fpr > 0 else None

        results["disparate_impact"] = {
            "high_amount_prediction_rate": float(high_amount_fpr),
            "low_amount_prediction_rate": float(low_amount_fpr),
            "ratio": float(disparate_impact_ratio) if disparate_impact_ratio else None,
        }

        logger.info(
            f"\nDisparate Impact Analysis:"
            f"\n  High amount (Q4) prediction rate: {high_amount_fpr:.4%}"
            f"\n  Low amount (Q1) prediction rate: {low_amount_fpr:.4%}"
            f"\n  Ratio: {disparate_impact_ratio:.2f}"
            if disparate_impact_ratio
            else "\n  Ratio: N/A"
        )

        # 80% rule check
        if disparate_impact_ratio and disparate_impact_ratio < 0.8:
            logger.warning("⚠️  DISPARATE IMPACT DETECTED: Ratio < 0.8 (80% rule)")
            results["disparate_impact_detected"] = True
        else:
            results["disparate_impact_detected"] = False

        self.report["biases"]["false_positive_negative"] = results
        return results

    def calculate_statistical_parity_metrics(self, df: pd.DataFrame) -> Dict[str, any]:
        """
        Calculate statistical parity and fairness metrics.

        Metrics:
        - Demographic parity (prediction rate equality)
        - Equalized odds (TPR/FPR equality)
        - Equal opportunity (TPR equality)
        """
        logger.info("\n" + "=" * 80)
        logger.info("CALCULATING STATISTICAL PARITY METRICS")
        logger.info("=" * 80)

        results = {}

        # Use predicted_fraud from previous analysis
        if "predicted_fraud" not in df.columns:
            amount_threshold = df["amount"].quantile(0.90)
            df["predicted_fraud"] = (
                (df["amount"] >= amount_threshold) | (df["isFlaggedFraud"] == 1)
            ).astype(int)

        # Define protected groups: transaction types
        protected_groups = df["type"].unique()

        group_metrics = []

        for group in protected_groups:
            group_data = df[df["type"] == group]

            # Prediction rate
            prediction_rate = group_data["predicted_fraud"].mean()

            # True Positive Rate (Recall)
            fraud_cases = group_data[group_data["isFraud"] == 1]
            tpr = fraud_cases["predicted_fraud"].mean() if len(fraud_cases) > 0 else 0

            # False Positive Rate
            legit_cases = group_data[group_data["isFraud"] == 0]
            fpr = legit_cases["predicted_fraud"].mean() if len(legit_cases) > 0 else 0

            # Precision
            predicted_fraud = group_data[group_data["predicted_fraud"] == 1]
            precision = predicted_fraud["isFraud"].mean() if len(predicted_fraud) > 0 else 0

            group_metrics.append(
                {
                    "group": group,
                    "count": int(len(group_data)),
                    "prediction_rate": float(prediction_rate),
                    "true_positive_rate": float(tpr),
                    "false_positive_rate": float(fpr),
                    "precision": float(precision),
                }
            )

            logger.info(
                f"\n{group}:"
                f"\n  Prediction rate: {prediction_rate:.4%}"
                f"\n  TPR (Recall): {tpr:.4%}"
                f"\n  FPR: {fpr:.4%}"
                f"\n  Precision: {precision:.4%}"
            )

        results["group_metrics"] = group_metrics

        # Calculate parity differences
        prediction_rates = [m["prediction_rate"] for m in group_metrics]
        tpr_rates = [m["true_positive_rate"] for m in group_metrics]
        fpr_rates = [m["false_positive_rate"] for m in group_metrics]

        results["parity_analysis"] = {
            "demographic_parity_difference": float(max(prediction_rates) - min(prediction_rates)),
            "equalized_odds_tpr_diff": float(max(tpr_rates) - min(tpr_rates)),
            "equalized_odds_fpr_diff": float(max(fpr_rates) - min(fpr_rates)),
            "max_prediction_rate": float(max(prediction_rates)),
            "min_prediction_rate": float(min(prediction_rates)),
        }

        logger.info(
            f"\nParity Analysis:"
            f"\n  Demographic parity difference: {results['parity_analysis']['demographic_parity_difference']:.4%}"
            f"\n  TPR difference (equalized odds): {results['parity_analysis']['equalized_odds_tpr_diff']:.4%}"
            f"\n  FPR difference (equalized odds): {results['parity_analysis']['equalized_odds_fpr_diff']:.4%}"
        )

        # Fairness threshold: 0.1 (10% difference)
        fairness_threshold = 0.1

        if results["parity_analysis"]["demographic_parity_difference"] > fairness_threshold:
            logger.warning(
                f"⚠️  DEMOGRAPHIC PARITY VIOLATION: Difference > {fairness_threshold:.0%}"
            )
            results["demographic_parity_satisfied"] = False
        else:
            logger.info("✓ Demographic parity satisfied")
            results["demographic_parity_satisfied"] = True

        if (
            results["parity_analysis"]["equalized_odds_tpr_diff"] > fairness_threshold
            or results["parity_analysis"]["equalized_odds_fpr_diff"] > fairness_threshold
        ):
            logger.warning(f"⚠️  EQUALIZED ODDS VIOLATION: Difference > {fairness_threshold:.0%}")
            results["equalized_odds_satisfied"] = False
        else:
            logger.info("✓ Equalized odds satisfied")
            results["equalized_odds_satisfied"] = True

        self.report["fairness_metrics"] = results
        return results

    def generate_recommendations(self) -> List[str]:
        """Generate fairness constraint recommendations based on analysis."""
        logger.info("\n" + "=" * 80)
        logger.info("GENERATING FAIRNESS RECOMMENDATIONS")
        logger.info("=" * 80)

        recommendations = []

        # Amount-fraud correlation recommendations
        amount_corr = self.report["correlations"].get("amount_fraud", {})
        if amount_corr.get("pearson_correlation", 0) > 0.3:
            recommendations.append(
                {
                    "category": "Amount Bias",
                    "severity": "HIGH",
                    "finding": "Strong positive correlation between amount and fraud",
                    "recommendation": "Implement amount-based stratified sampling in training to prevent high-amount bias. Consider separate models for different amount ranges.",
                    "constraint": "Max prediction rate difference across amount quartiles < 10%",
                }
            )

        # Transaction type bias recommendations
        type_bias = self.report["biases"].get("transaction_type", {})
        if type_bias.get("bias_detected", False):
            recommendations.append(
                {
                    "category": "Transaction Type Bias",
                    "severity": "HIGH",
                    "finding": "Significant association between transaction type and fraud",
                    "recommendation": "Apply demographic parity constraint: prediction rates should not vary by more than 10% across transaction types.",
                    "constraint": "max(P(Ŷ=1|type=t)) - min(P(Ŷ=1|type=t)) < 0.1",
                }
            )

        # Disparate impact recommendations
        di = self.report["biases"].get("false_positive_negative", {}).get("disparate_impact", {})
        if di.get("ratio") and di["ratio"] < 0.8:
            recommendations.append(
                {
                    "category": "Disparate Impact",
                    "severity": "CRITICAL",
                    "finding": f"Disparate impact ratio {di['ratio']:.2f} < 0.8",
                    "recommendation": "Apply 80% rule constraint. Rebalance training data or use fairness-aware learning algorithms (e.g., reweighting, adversarial debiasing).",
                    "constraint": "min(P(Ŷ=1|group)) / max(P(Ŷ=1|group)) ≥ 0.8",
                }
            )

        # Statistical parity recommendations
        fairness = self.report.get("fairness_metrics", {})
        if not fairness.get("demographic_parity_satisfied", True):
            recommendations.append(
                {
                    "category": "Demographic Parity",
                    "severity": "MEDIUM",
                    "finding": "Demographic parity violated across transaction types",
                    "recommendation": "Implement post-processing calibration or threshold optimization per group.",
                    "constraint": "Prediction rate difference < 10% across all groups",
                }
            )

        if not fairness.get("equalized_odds_satisfied", True):
            recommendations.append(
                {
                    "category": "Equalized Odds",
                    "severity": "MEDIUM",
                    "finding": "TPR/FPR not equal across groups",
                    "recommendation": "Use equalized odds post-processing or train with fairness constraints (e.g., Fairlearn, AIF360).",
                    "constraint": "max(TPR_diff, FPR_diff) < 10% across groups",
                }
            )

        # General recommendations
        recommendations.append(
            {
                "category": "Monitoring",
                "severity": "MEDIUM",
                "finding": "Continuous monitoring needed",
                "recommendation": "Implement ongoing bias monitoring in production. Track fairness metrics per deployment and retrain if drift detected.",
                "constraint": "Monthly fairness audits with automated alerts",
            }
        )

        recommendations.append(
            {
                "category": "Data Collection",
                "severity": "LOW",
                "finding": "Limited demographic attributes in dataset",
                "recommendation": "Consider collecting more granular features while respecting privacy. Analyze biases across account age, geography, time patterns.",
                "constraint": "Annual bias audit across all available demographics",
            }
        )

        # Log recommendations
        for i, rec in enumerate(recommendations, 1):
            logger.info(f"\n[{i}] {rec['category']} - {rec['severity']}")
            logger.info(f"    Finding: {rec['finding']}")
            logger.info(f"    Recommendation: {rec['recommendation']}")
            logger.info(f"    Constraint: {rec['constraint']}")

        self.report["recommendations"] = recommendations
        return recommendations

    def save_report(self, output_path: Path) -> None:
        """Save comprehensive bias audit report to JSON."""
        logger.info(f"\nSaving bias audit report to {output_path}")

        with open(output_path, "w") as f:
            json.dump(self.report, f, indent=2)

        logger.info(f"✓ Report saved successfully")

        # Also save human-readable summary
        summary_path = output_path.parent / "bias_audit_summary.txt"
        with open(summary_path, "w") as f:
            f.write("=" * 80 + "\n")
            f.write("BIAS AND FAIRNESS AUDIT REPORT\n")
            f.write("=" * 80 + "\n\n")

            f.write("METADATA\n")
            f.write("-" * 80 + "\n")
            for key, value in self.report["metadata"].items():
                f.write(f"{key}: {value}\n")

            f.write("\n\nKEY FINDINGS\n")
            f.write("-" * 80 + "\n")

            # Amount correlation
            amount_corr = self.report["correlations"].get("amount_fraud", {})
            f.write(f"\n1. Amount-Fraud Correlation: {amount_corr.get('interpretation', 'N/A')}\n")
            f.write(f"   Pearson r = {amount_corr.get('pearson_correlation', 0):.4f}\n")

            # Type bias
            type_bias = self.report["biases"].get("transaction_type", {})
            f.write(
                f"\n2. Transaction Type Bias: {'DETECTED' if type_bias.get('bias_detected') else 'NOT DETECTED'}\n"
            )
            f.write(
                f"   Chi-square p-value = {type_bias.get('chi_square', {}).get('p_value', 0):.4e}\n"
            )

            # Fairness
            fairness = self.report.get("fairness_metrics", {})
            f.write(
                f"\n3. Demographic Parity: {'SATISFIED' if fairness.get('demographic_parity_satisfied') else 'VIOLATED'}\n"
            )
            f.write(
                f"4. Equalized Odds: {'SATISFIED' if fairness.get('equalized_odds_satisfied') else 'VIOLATED'}\n"
            )

            f.write("\n\nRECOMMENDATIONS\n")
            f.write("-" * 80 + "\n")
            for i, rec in enumerate(self.report["recommendations"], 1):
                f.write(f"\n[{i}] {rec['category']} ({rec['severity']})\n")
                f.write(f"    {rec['finding']}\n")
                f.write(f"    → {rec['recommendation']}\n")

        logger.info(f"✓ Summary saved to {summary_path}")


def main():
    """Main execution function."""
    logger.info("=" * 80)
    logger.info("BIAS AND FAIRNESS ANALYSIS PIPELINE")
    logger.info("=" * 80)

    # Initialize analyzer
    analyzer = BiasFairnessAnalyzer(random_seed=42)

    # Load cleaned data
    data_path = PROCESSED_DIR / "paysim_cleaned.csv"
    df = analyzer.load_data(data_path)

    # Run analyses
    analyzer.analyze_amount_fraud_correlation(df)
    analyzer.analyze_transaction_type_bias(df)
    analyzer.analyze_false_positive_negative_patterns(df)
    analyzer.calculate_statistical_parity_metrics(df)

    # Generate recommendations
    analyzer.generate_recommendations()

    # Save report
    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = ANALYSIS_DIR / "bias_audit_report.json"
    analyzer.save_report(report_path)

    logger.info("\n" + "=" * 80)
    logger.info("BIAS AND FAIRNESS ANALYSIS COMPLETED")
    logger.info("=" * 80)
    logger.info(f"✓ Detailed report: {report_path}")
    logger.info(f"✓ Summary: {ANALYSIS_DIR / 'bias_audit_summary.txt'}")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()
