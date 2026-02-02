"""
Model Drift Detection Script.

Monitors data and model drift using statistical tests:
- Population Stability Index (PSI) for categorical features
- Kolmogorov-Smirnov test for numerical features
- Performance degradation detection
"""

import argparse
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.metrics import f1_score, precision_score, recall_score, roc_auc_score

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
MODELS_DIR = PROJECT_ROOT / "backend" / "models"
REPORTS_DIR = PROJECT_ROOT / "backend" / "reports" / "drift"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

# Drift thresholds
PSI_THRESHOLDS = {
    "low": 0.1,      # PSI < 0.1: No significant change
    "medium": 0.2,   # PSI 0.1-0.2: Moderate change, monitor
    "high": 0.2      # PSI > 0.2: Significant change, retrain recommended
}

KS_THRESHOLD = 0.05  # p-value threshold for KS test


def calculate_psi(
    expected: pd.Series,
    actual: pd.Series,
    bins: int = 10
) -> float:
    """
    Calculate Population Stability Index (PSI).

    PSI measures distribution drift between two datasets.

    Args:
        expected: Reference/baseline distribution
        actual: Current/production distribution
        bins: Number of bins for discretization

    Returns:
        float: PSI value
    """
    # Handle categorical features
    if expected.dtype == 'object' or expected.dtype.name == 'category':
        expected_counts = expected.value_counts(normalize=True)
        actual_counts = actual.value_counts(normalize=True)

        # Align categories
        all_categories = set(expected_counts.index) | set(actual_counts.index)
        expected_pct = {cat: expected_counts.get(cat, 0.0001) for cat in all_categories}
        actual_pct = {cat: actual_counts.get(cat, 0.0001) for cat in all_categories}

        psi = sum(
            (actual_pct[cat] - expected_pct[cat]) * np.log(actual_pct[cat] / expected_pct[cat])
            for cat in all_categories
        )

    # Handle numerical features
    else:
        # Create bins based on expected distribution
        breakpoints = np.percentile(expected, np.linspace(0, 100, bins + 1))
        breakpoints = np.unique(breakpoints)  # Remove duplicates

        # Bin both distributions
        expected_binned = pd.cut(expected, bins=breakpoints, include_lowest=True)
        actual_binned = pd.cut(actual, bins=breakpoints, include_lowest=True)

        expected_pct = expected_binned.value_counts(normalize=True)
        actual_pct = actual_binned.value_counts(normalize=True)

        # Align bins
        all_bins = set(expected_pct.index) | set(actual_pct.index)
        expected_dict = {b: expected_pct.get(b, 0.0001) for b in all_bins}
        actual_dict = {b: actual_pct.get(b, 0.0001) for b in all_bins}

        psi = sum(
            (actual_dict[b] - expected_dict[b]) * np.log(actual_dict[b] / expected_dict[b])
            for b in all_bins
        )

    return psi


def kolmogorov_smirnov_test(
    reference: pd.Series,
    current: pd.Series
) -> Tuple[float, float]:
    """
    Perform Kolmogorov-Smirnov test for distribution drift.

    Args:
        reference: Reference distribution
        current: Current distribution

    Returns:
        tuple: (KS statistic, p-value)
    """
    statistic, p_value = stats.ks_2samp(reference, current)
    return statistic, p_value


def detect_feature_drift(
    reference_df: pd.DataFrame,
    current_df: pd.DataFrame,
    numerical_features: List[str],
    categorical_features: List[str]
) -> Dict:
    """
    Detect drift for all features.

    Args:
        reference_df: Baseline/training data
        current_df: Production/new data
        numerical_features: List of numerical feature names
        categorical_features: List of categorical feature names

    Returns:
        dict: Drift analysis results
    """
    results = {
        "numerical_features": {},
        "categorical_features": {},
        "drift_detected": False,
        "features_with_drift": []
    }

    # Check numerical features (KS test)
    for feature in numerical_features:
        if feature not in reference_df.columns or feature not in current_df.columns:
            logger.warning(f"Feature {feature} not found in data")
            continue

        ref_data = reference_df[feature].dropna()
        cur_data = current_df[feature].dropna()

        ks_stat, p_value = kolmogorov_smirnov_test(ref_data, cur_data)
        drift = p_value < KS_THRESHOLD

        results["numerical_features"][feature] = {
            "ks_statistic": float(ks_stat),
            "p_value": float(p_value),
            "drift_detected": drift,
            "threshold": KS_THRESHOLD
        }

        if drift:
            results["drift_detected"] = True
            results["features_with_drift"].append(feature)
            logger.warning(f"Drift detected in {feature}: p-value={p_value:.4f}")

    # Check categorical features (PSI)
    for feature in categorical_features:
        if feature not in reference_df.columns or feature not in current_df.columns:
            logger.warning(f"Feature {feature} not found in data")
            continue

        ref_data = reference_df[feature].dropna()
        cur_data = current_df[feature].dropna()

        psi = calculate_psi(ref_data, cur_data)

        if psi < PSI_THRESHOLDS["low"]:
            drift_level = "none"
            drift = False
        elif psi < PSI_THRESHOLDS["medium"]:
            drift_level = "low"
            drift = False
        elif psi < PSI_THRESHOLDS["high"]:
            drift_level = "medium"
            drift = True
        else:
            drift_level = "high"
            drift = True

        results["categorical_features"][feature] = {
            "psi": float(psi),
            "drift_level": drift_level,
            "drift_detected": drift,
            "threshold": PSI_THRESHOLDS["high"]
        }

        if drift:
            results["drift_detected"] = True
            results["features_with_drift"].append(feature)
            logger.warning(f"Drift detected in {feature}: PSI={psi:.4f}")

    return results


def detect_performance_drift(
    y_true_ref: np.ndarray,
    y_pred_ref: np.ndarray,
    y_true_cur: np.ndarray,
    y_pred_cur: np.ndarray,
    threshold: float = 0.05
) -> Dict:
    """
    Detect model performance degradation.

    Args:
        y_true_ref: Reference true labels
        y_pred_ref: Reference predictions
        y_true_cur: Current true labels
        y_pred_cur: Current predictions
        threshold: Performance drop threshold (default: 5%)

    Returns:
        dict: Performance drift analysis
    """
    # Calculate metrics for reference
    ref_metrics = {
        "f1": f1_score(y_true_ref, y_pred_ref),
        "precision": precision_score(y_true_ref, y_pred_ref, zero_division=0),
        "recall": recall_score(y_true_ref, y_pred_ref, zero_division=0),
    }

    # Calculate metrics for current
    cur_metrics = {
        "f1": f1_score(y_true_cur, y_pred_cur),
        "precision": precision_score(y_true_cur, y_pred_cur, zero_division=0),
        "recall": recall_score(y_true_cur, y_pred_cur, zero_division=0),
    }

    # Calculate drops
    drops = {
        metric: ref_metrics[metric] - cur_metrics[metric]
        for metric in ref_metrics
    }

    # Detect degradation
    degradation = any(drop > threshold for drop in drops.values())

    results = {
        "reference_metrics": ref_metrics,
        "current_metrics": cur_metrics,
        "metric_drops": drops,
        "performance_degradation": degradation,
        "threshold": threshold
    }

    if degradation:
        logger.warning(
            f"Performance degradation detected: "
            f"F1 drop={drops['f1']:.4f}, "
            f"Precision drop={drops['precision']:.4f}, "
            f"Recall drop={drops['recall']:.4f}"
        )

    return results


def main():
    """Run drift detection analysis."""
    parser = argparse.ArgumentParser(description="Detect model and data drift")
    parser.add_argument(
        "--reference",
        type=str,
        default="test",
        help="Reference dataset (train/val/test)"
    )
    parser.add_argument(
        "--current",
        type=str,
        required=True,
        help="Current dataset file path"
    )
    parser.add_argument(
        "--max-samples",
        type=int,
        default=50000,
        help="Max samples to analyze"
    )
    args = parser.parse_args()

    logger.info("=" * 80)
    logger.info("DRIFT DETECTION ANALYSIS")
    logger.info("=" * 80)

    # Load reference data (from splits)
    splits_dir = DATA_DIR / "splits" / "stratified"
    ref_path = splits_dir / f"{args.reference}.csv"

    if not ref_path.exists():
        logger.error(f"Reference data not found: {ref_path}")
        return

    logger.info(f"Loading reference data: {ref_path}")
    reference_df = pd.read_csv(ref_path)

    if len(reference_df) > args.max_samples:
        reference_df = reference_df.sample(n=args.max_samples, random_state=42)

    logger.info(f"Reference samples: {len(reference_df):,}")

    # Load current data
    current_path = Path(args.current)
    if not current_path.exists():
        logger.error(f"Current data not found: {current_path}")
        return

    logger.info(f"Loading current data: {current_path}")
    current_df = pd.read_csv(current_path)

    if len(current_df) > args.max_samples:
        current_df = current_df.sample(n=args.max_samples, random_state=42)

    logger.info(f"Current samples: {len(current_df):,}")

    # Define features
    numerical_features = ["amount", "hour_of_day", "day_of_week", "is_weekend"]
    categorical_features = ["merchant_category_code", "transaction_type"]

    # Detect feature drift
    logger.info("\nAnalyzing feature drift...")
    drift_results = detect_feature_drift(
        reference_df,
        current_df,
        numerical_features,
        categorical_features
    )

    # Print results
    logger.info("\n" + "=" * 80)
    logger.info("DRIFT DETECTION RESULTS")
    logger.info("=" * 80)

    logger.info("\nNumerical Features (Kolmogorov-Smirnov Test):")
    for feature, result in drift_results["numerical_features"].items():
        status = "DRIFT" if result["drift_detected"] else "OK"
        logger.info(
            f"  {feature}: {status} "
            f"(KS={result['ks_statistic']:.4f}, p={result['p_value']:.4f})"
        )

    logger.info("\nCategorical Features (Population Stability Index):")
    for feature, result in drift_results["categorical_features"].items():
        status = "DRIFT" if result["drift_detected"] else "OK"
        logger.info(
            f"  {feature}: {status} "
            f"(PSI={result['psi']:.4f}, level={result['drift_level']})"
        )

    # Overall assessment
    logger.info("\n" + "=" * 80)
    if drift_results["drift_detected"]:
        logger.warning(
            f"DRIFT DETECTED in {len(drift_results['features_with_drift'])} features: "
            f"{', '.join(drift_results['features_with_drift'])}"
        )
        logger.warning("RECOMMENDATION: Retrain model with recent data")
    else:
        logger.info("NO SIGNIFICANT DRIFT DETECTED")
        logger.info("Model can continue serving predictions")

    # Save report
    report = {
        "timestamp": datetime.now().isoformat(),
        "reference_dataset": str(ref_path),
        "current_dataset": str(current_path),
        "reference_samples": len(reference_df),
        "current_samples": len(current_df),
        "drift_analysis": drift_results,
        "recommendation": "retrain" if drift_results["drift_detected"] else "continue"
    }

    report_path = REPORTS_DIR / f"drift_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    logger.info(f"\nDrift report saved: {report_path}")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()
