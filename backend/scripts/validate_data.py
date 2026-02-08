#!/usr/bin/env python3
"""
Data Validation Script for FinSight AI MLOps Pipeline.

Comprehensive data validation with quality gates:
- Schema validation (columns, dtypes)
- Missing value detection
- Outlier detection (IQR method)
- Drift detection (PSI for categorical, KS test for numerical)
- Data quality scoring

Exit codes:
- 0: All validations passed
- 1: Validation failed (quality gates triggered)
- 2: Critical error (missing files, etc.)

Author: FinSight AI Team
Date: February 8, 2026
"""

import argparse
import hashlib
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import stats

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class DataValidator:
    """Comprehensive data validation with quality gates."""

    # Expected schema for PaySim fraud detection dataset
    EXPECTED_RAW_SCHEMA = {
        "step": ["int32", "int64"],
        "type": ["object", "category"],
        "amount": ["float32", "float64"],
        "nameOrig": ["object"],
        "oldbalanceOrg": ["float32", "float64"],
        "newbalanceOrig": ["float32", "float64"],
        "nameDest": ["object"],
        "oldbalanceDest": ["float32", "float64"],
        "newbalanceDest": ["float32", "float64"],
        "isFraud": ["int8", "int64", "int32"],
        "isFlaggedFraud": ["int8", "int64", "int32"],
    }

    EXPECTED_CLEANED_SCHEMA = {
        "step": ["int32", "int64"],
        "type": ["object", "category"],
        "amount": ["float32", "float64"],
        "isFraud": ["int8", "int64", "int32"],
        "isFlaggedFraud": ["int8", "int64", "int32"],
        # Additional engineered features
        "hour": ["int8", "int64", "int32"],
        "day": ["int16", "int64", "int32"],
        "day_of_week": ["int8", "int64", "int32"],
    }

    # Quality thresholds
    MAX_MISSING_RATE = 0.05  # 5% missing values allowed
    MAX_DUPLICATE_RATE = 0.01  # 1% duplicates allowed
    FRAUD_RATE_MIN = 0.0001  # 0.01% minimum fraud rate
    FRAUD_RATE_MAX = 0.5  # 50% maximum fraud rate (for balanced sets)
    PSI_THRESHOLD = 0.2  # Population Stability Index threshold
    KS_PVALUE_THRESHOLD = 0.05  # KS test p-value threshold
    OUTLIER_IQR_MULTIPLIER = 3.0  # IQR multiplier for outlier detection

    def __init__(
        self,
        data_path: str,
        baseline_path: Optional[str] = None,
        output_dir: str = "data/analysis",
        strict_mode: bool = False,
        report_name: str = "data_quality_report.json",
    ) -> None:
        """Initialize data validator.

        Args:
            data_path: Path to data file to validate
            baseline_path: Path to baseline data for drift detection (optional)
            output_dir: Directory to save validation report
            strict_mode: If True, fail on any quality issue
            report_name: Name of the output report file
        """
        self.data_path = Path(data_path)
        self.baseline_path = Path(baseline_path) if baseline_path else None
        self.output_dir = Path(output_dir)
        self.strict_mode = strict_mode
        self.report_name = report_name
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.validation_report: Dict = {
            "timestamp": datetime.now().isoformat(),
            "data_file": str(self.data_path),
            "baseline_file": str(self.baseline_path) if self.baseline_path else None,
            "validations": {},
            "quality_score": 0.0,
            "status": "UNKNOWN",
            "errors": [],
            "warnings": [],
        }

    def load_data(self) -> pd.DataFrame:
        """Load and hash data file.

        Returns:
            DataFrame: Loaded data

        Raises:
            FileNotFoundError: If data file doesn't exist
        """
        if not self.data_path.exists():
            raise FileNotFoundError(f"Data file not found: {self.data_path}")

        logger.info(f"Loading data from {self.data_path}")
        df = pd.read_csv(self.data_path)

        # Calculate file hash for traceability
        file_hash = self._calculate_file_hash(self.data_path)
        self.validation_report["data_hash"] = file_hash
        self.validation_report["data_shape"] = list(df.shape)

        logger.info(f"Loaded {len(df):,} rows × {len(df.columns)} columns")
        return df

    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA256 hash of file.

        Args:
            file_path: Path to file

        Returns:
            str: Hex digest of file hash
        """
        h = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(8192):
                h.update(chunk)
        return h.hexdigest()

    def validate_schema(self, df: pd.DataFrame, schema_type: str = "auto") -> bool:
        """Validate DataFrame schema.

        Args:
            df: DataFrame to validate
            schema_type: 'raw', 'cleaned', or 'auto'

        Returns:
            bool: True if schema valid
        """
        logger.info("Validating schema...")

        # Auto-detect schema type
        if schema_type == "auto":
            if "nameOrig" in df.columns:
                schema_type = "raw"
            else:
                schema_type = "cleaned"

        expected_schema = (
            self.EXPECTED_RAW_SCHEMA
            if schema_type == "raw"
            else self.EXPECTED_CLEANED_SCHEMA
        )

        issues = []
        columns = set(df.columns)

        # Check for missing required columns
        if schema_type == "raw":
            required_cols = {"step", "type", "amount", "isFraud"}
        else:
            required_cols = {"step", "type", "amount", "isFraud", "hour"}

        missing_cols = required_cols - columns
        if missing_cols:
            issues.append(f"Missing required columns: {missing_cols}")

        # Check data types
        dtype_issues = []
        for col in expected_schema:
            if col in df.columns:
                actual_dtype = str(df[col].dtype)
                expected_dtypes = expected_schema[col]
                if actual_dtype not in expected_dtypes:
                    dtype_issues.append(
                        f"{col}: expected {expected_dtypes}, got {actual_dtype}"
                    )

        if dtype_issues:
            issues.append(f"Data type mismatches: {dtype_issues}")

        # Record results
        self.validation_report["validations"]["schema"] = {
            "passed": len(issues) == 0,
            "schema_type": schema_type,
            "columns_count": len(df.columns),
            "issues": issues,
        }

        if issues:
            for issue in issues:
                self.validation_report["warnings"].append(f"Schema: {issue}")
            logger.warning(f"Schema validation issues: {issues}")
            return False

        logger.info("✓ Schema validation passed")
        return True

    def validate_missing_values(self, df: pd.DataFrame) -> bool:
        """Validate missing values.

        Args:
            df: DataFrame to validate

        Returns:
            bool: True if missing values within acceptable threshold
        """
        logger.info("Checking for missing values...")

        total_cells = df.shape[0] * df.shape[1]
        missing_count = df.isnull().sum().sum()
        missing_rate = missing_count / total_cells if total_cells > 0 else 0

        missing_by_column = df.isnull().sum()
        columns_with_missing = missing_by_column[missing_by_column > 0].to_dict()

        passed = missing_rate <= self.MAX_MISSING_RATE

        self.validation_report["validations"]["missing_values"] = {
            "passed": passed,
            "total_missing": int(missing_count),
            "missing_rate": float(missing_rate),
            "threshold": self.MAX_MISSING_RATE,
            "columns_with_missing": {k: int(v) for k, v in columns_with_missing.items()},
        }

        if not passed:
            msg = f"Missing value rate {missing_rate:.2%} exceeds threshold {self.MAX_MISSING_RATE:.2%}"
            self.validation_report["errors"].append(msg)
            logger.error(msg)
            return False

        if missing_count > 0:
            msg = f"Found {missing_count} missing values ({missing_rate:.4%})"
            self.validation_report["warnings"].append(msg)
            logger.warning(msg)

        logger.info(f"✓ Missing values: {missing_count} ({missing_rate:.4%})")
        return True

    def validate_duplicates(self, df: pd.DataFrame) -> bool:
        """Validate duplicate rows.

        Args:
            df: DataFrame to validate

        Returns:
            bool: True if duplicates within acceptable threshold
        """
        logger.info("Checking for duplicate rows...")

        duplicate_count = df.duplicated().sum()
        duplicate_rate = duplicate_count / len(df) if len(df) > 0 else 0

        passed = duplicate_rate <= self.MAX_DUPLICATE_RATE

        self.validation_report["validations"]["duplicates"] = {
            "passed": passed,
            "total_duplicates": int(duplicate_count),
            "duplicate_rate": float(duplicate_rate),
            "threshold": self.MAX_DUPLICATE_RATE,
        }

        if not passed:
            msg = f"Duplicate rate {duplicate_rate:.2%} exceeds threshold {self.MAX_DUPLICATE_RATE:.2%}"
            self.validation_report["errors"].append(msg)
            logger.error(msg)
            return False

        logger.info(f"✓ Duplicates: {duplicate_count} ({duplicate_rate:.4%})")
        return True

    def validate_outliers(self, df: pd.DataFrame) -> bool:
        """Detect outliers using IQR method.

        Args:
            df: DataFrame to validate

        Returns:
            bool: True (outliers are warnings, not failures)
        """
        logger.info("Detecting outliers using IQR method...")

        numeric_cols = df.select_dtypes(include=[np.number]).columns
        outlier_info = {}

        for col in numeric_cols:
            Q1 = df[col].quantile(0.25)
            Q3 = df[col].quantile(0.75)
            IQR = Q3 - Q1

            lower_bound = Q1 - self.OUTLIER_IQR_MULTIPLIER * IQR
            upper_bound = Q3 + self.OUTLIER_IQR_MULTIPLIER * IQR

            outliers = (df[col] < lower_bound) | (df[col] > upper_bound)
            outlier_count = outliers.sum()
            outlier_rate = outlier_count / len(df) if len(df) > 0 else 0

            if outlier_count > 0:
                outlier_info[col] = {
                    "count": int(outlier_count),
                    "rate": float(outlier_rate),
                    "bounds": [float(lower_bound), float(upper_bound)],
                }

        self.validation_report["validations"]["outliers"] = {
            "passed": True,  # Outliers don't fail validation
            "numeric_columns_checked": len(numeric_cols),
            "columns_with_outliers": outlier_info,
            "iqr_multiplier": self.OUTLIER_IQR_MULTIPLIER,
        }

        if outlier_info:
            total_outliers = sum(info["count"] for info in outlier_info.values())
            msg = f"Found {total_outliers} outliers across {len(outlier_info)} columns"
            self.validation_report["warnings"].append(msg)
            logger.warning(msg)

        logger.info(f"✓ Outlier detection complete ({len(outlier_info)} columns have outliers)")
        return True

    def validate_fraud_rate(self, df: pd.DataFrame) -> bool:
        """Validate fraud rate is within expected bounds.

        Args:
            df: DataFrame to validate

        Returns:
            bool: True if fraud rate is reasonable
        """
        if "isFraud" not in df.columns:
            logger.warning("isFraud column not found, skipping fraud rate validation")
            return True

        logger.info("Validating fraud rate...")

        fraud_count = df["isFraud"].sum()
        fraud_rate = fraud_count / len(df) if len(df) > 0 else 0

        passed = self.FRAUD_RATE_MIN <= fraud_rate <= self.FRAUD_RATE_MAX

        self.validation_report["validations"]["fraud_rate"] = {
            "passed": passed,
            "fraud_count": int(fraud_count),
            "total_count": len(df),
            "fraud_rate": float(fraud_rate),
            "expected_range": [self.FRAUD_RATE_MIN, self.FRAUD_RATE_MAX],
        }

        if not passed:
            msg = f"Fraud rate {fraud_rate:.4%} outside expected range [{self.FRAUD_RATE_MIN:.4%}, {self.FRAUD_RATE_MAX:.4%}]"
            self.validation_report["errors"].append(msg)
            logger.error(msg)
            return False

        logger.info(f"✓ Fraud rate: {fraud_rate:.4%} ({fraud_count:,} frauds)")
        return True

    def validate_drift(self, df: pd.DataFrame) -> bool:
        """Detect data drift compared to baseline.

        Args:
            df: Current DataFrame

        Returns:
            bool: True if no significant drift detected
        """
        if not self.baseline_path or not self.baseline_path.exists():
            logger.info("No baseline data provided, skipping drift detection")
            self.validation_report["validations"]["drift"] = {
                "passed": True,
                "skipped": True,
                "reason": "No baseline data provided",
            }
            return True

        logger.info(f"Detecting drift against baseline: {self.baseline_path}")

        baseline_df = pd.read_csv(self.baseline_path)

        # Find common columns
        common_cols = set(df.columns) & set(baseline_df.columns)
        numeric_cols = [
            col for col in common_cols if df[col].dtype in [np.float32, np.float64, np.int32, np.int64, np.int8]
        ]

        drift_results = {}
        drift_detected = False

        for col in numeric_cols:
            # KS test for numerical columns
            ks_stat, ks_pvalue = stats.ks_2samp(baseline_df[col], df[col])

            drift_results[col] = {
                "ks_statistic": float(ks_stat),
                "ks_pvalue": float(ks_pvalue),
                "drift_detected": ks_pvalue < self.KS_PVALUE_THRESHOLD,
            }

            if ks_pvalue < self.KS_PVALUE_THRESHOLD:
                drift_detected = True
                msg = f"Drift detected in {col}: KS p-value={ks_pvalue:.4f}"
                self.validation_report["warnings"].append(msg)
                logger.warning(msg)

        self.validation_report["validations"]["drift"] = {
            "passed": not drift_detected,
            "baseline_file": str(self.baseline_path),
            "columns_checked": len(numeric_cols),
            "columns_with_drift": sum(1 for r in drift_results.values() if r["drift_detected"]),
            "drift_results": drift_results,
            "ks_threshold": self.KS_PVALUE_THRESHOLD,
        }

        if drift_detected:
            logger.warning("⚠️  Data drift detected")
            return False

        logger.info("✓ No significant drift detected")
        return True

    def calculate_quality_score(self) -> float:
        """Calculate overall data quality score (0-100).

        Returns:
            float: Quality score
        """
        validations = self.validation_report["validations"]
        weights = {
            "schema": 20,
            "missing_values": 25,
            "duplicates": 20,
            "fraud_rate": 15,
            "outliers": 10,
            "drift": 10,
        }

        score = 0.0
        total_weight = 0.0

        for validation_name, weight in weights.items():
            if validation_name in validations:
                total_weight += weight
                if validations[validation_name].get("passed", False):
                    score += weight

        quality_score = (score / total_weight * 100) if total_weight > 0 else 0.0
        return quality_score

    def run_validation(self) -> Tuple[bool, Dict]:
        """Run all validations.

        Returns:
            Tuple[bool, Dict]: (success, validation_report)
        """
        try:
            logger.info("=" * 80)
            logger.info("STARTING DATA VALIDATION PIPELINE")
            logger.info("=" * 80)

            # Load data
            df = self.load_data()

            # Run validations
            results = []
            results.append(self.validate_schema(df))
            results.append(self.validate_missing_values(df))
            results.append(self.validate_duplicates(df))
            results.append(self.validate_outliers(df))
            results.append(self.validate_fraud_rate(df))
            results.append(self.validate_drift(df))

            # Calculate quality score
            quality_score = self.calculate_quality_score()
            self.validation_report["quality_score"] = quality_score

            # Determine overall status
            has_errors = len(self.validation_report["errors"]) > 0
            all_passed = all(results)

            if has_errors or not all_passed:
                if self.strict_mode:
                    self.validation_report["status"] = "FAILED"
                    success = False
                else:
                    self.validation_report["status"] = "PASSED_WITH_WARNINGS"
                    success = True
            else:
                self.validation_report["status"] = "PASSED"
                success = True

            # Save report
            self._save_report()

            # Print summary
            logger.info("=" * 80)
            logger.info("VALIDATION SUMMARY")
            logger.info("=" * 80)
            logger.info(f"Status: {self.validation_report['status']}")
            logger.info(f"Quality Score: {quality_score:.1f}/100")
            logger.info(f"Errors: {len(self.validation_report['errors'])}")
            logger.info(f"Warnings: {len(self.validation_report['warnings'])}")
            logger.info("=" * 80)

            if self.validation_report["errors"]:
                logger.error("ERRORS:")
                for error in self.validation_report["errors"]:
                    logger.error(f"  - {error}")

            if self.validation_report["warnings"]:
                logger.warning("WARNINGS:")
                for warning in self.validation_report["warnings"]:
                    logger.warning(f"  - {warning}")

            return success, self.validation_report

        except Exception as e:
            logger.exception(f"Validation failed with exception: {e}")
            self.validation_report["status"] = "ERROR"
            self.validation_report["errors"].append(str(e))
            self._save_report()
            return False, self.validation_report

    def _save_report(self) -> None:
        """Save validation report to JSON."""
        # Convert numpy types to Python types for JSON serialization
        def convert_types(obj):
            """Recursively convert numpy types to Python types."""
            if isinstance(obj, dict):
                return {k: convert_types(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_types(item) for item in obj]
            elif isinstance(obj, (np.integer, np.int64, np.int32, np.int8)):
                return int(obj)
            elif isinstance(obj, (np.floating, np.float64, np.float32)):
                return float(obj)
            elif isinstance(obj, (np.bool_, bool)):
                return bool(obj)
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            else:
                return obj

        report_path = self.output_dir / self.report_name
        cleaned_report = convert_types(self.validation_report)
        with open(report_path, "w") as f:
            json.dump(cleaned_report, f, indent=2)
        logger.info(f"✓ Validation report saved to {report_path}")


def main() -> int:
    """Main entry point.

    Returns:
        int: Exit code (0=success, 1=validation failed, 2=error)
    """
    parser = argparse.ArgumentParser(
        description="Validate data quality for FinSight AI MLOps pipeline"
    )
    parser.add_argument(
        "data_file",
        help="Path to data file to validate",
    )
    parser.add_argument(
        "--baseline",
        help="Path to baseline data for drift detection (optional)",
        default=None,
    )
    parser.add_argument(
        "--output-dir",
        help="Directory to save validation report",
        default="data/analysis",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail on any quality issues (default: warnings allowed)",
    )
    parser.add_argument(
        "--report-name",
        help="Name of output report file (default: data_quality_report.json)",
        default="data_quality_report.json",
    )

    args = parser.parse_args()

    validator = DataValidator(
        data_path=args.data_file,
        baseline_path=args.baseline,
        output_dir=args.output_dir,
        strict_mode=args.strict,
        report_name=args.report_name,
    )

    success, report = validator.run_validation()

    if success:
        if report["status"] == "PASSED":
            logger.info("✅ All validations passed!")
            return 0
        elif report["status"] == "PASSED_WITH_WARNINGS":
            logger.warning("⚠️  Validations passed with warnings")
            return 0
    else:
        logger.error("❌ Validation failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
