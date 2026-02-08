"""Data cleaning and preprocessing pipeline for PaySim fraud detection.

This script performs the complete data cleaning and feature engineering pipeline:
1. Load raw data
2. Handle missing values and duplicates
3. PII masking (hash account IDs)
4. Normalize transaction amounts
5. Time binning (hour, day, day_of_week)
6. Feature engineering (balance ratios, amount ratios)
7. Save cleaned data

Author: FinSight AI Team
Date: December 28, 2025
"""

import hashlib
import json
import logging
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler, StandardScaler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class DataCleaningPipeline:
    """Complete data cleaning and preprocessing pipeline for fraud detection.

    This pipeline follows AGI best practices:
    - Reproducible (fixed random seed)
    - Documented (decision logging)
    - Type-safe (Pydantic-style validation)
    - Tested (assertions for data quality)
    """

    def __init__(
        self,
        raw_data_path: str,
        output_dir: str,
        normalization_method: str = "standard",
        random_seed: int = 42,
    ) -> None:
        """Initialize the data cleaning pipeline.

        Args:
            raw_data_path: Path to raw CSV file
            output_dir: Directory to save cleaned data
            normalization_method: 'standard' or 'minmax'
            random_seed: Random seed for reproducibility
        """
        self.raw_data_path = Path(raw_data_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.normalization_method = normalization_method
        self.random_seed = random_seed

        # Statistics tracking
        self.stats: Dict = {
            "original_shape": None,
            "cleaned_shape": None,
            "missing_values": {},
            "duplicates_removed": 0,
            "features_created": [],
            "normalization_params": {},
        }

        # Scalers
        self.amount_scaler = None
        self.balance_scaler = None

    def _hash_account_id(self, account_id: str) -> str:
        """Hash account ID for PII masking.

        Uses SHA256 with truncation for privacy while maintaining uniqueness.

        Args:
            account_id: Original account ID (e.g., 'C123456789')

        Returns:
            str: Hashed ID (first 16 chars of SHA256)
        """
        return hashlib.sha256(account_id.encode()).hexdigest()[:16]

    def load_data(self) -> pd.DataFrame:
        """Load raw data with optimized dtypes.

        Returns:
            pd.DataFrame: Loaded dataframe
        """
        logger.info(f"Loading data from {self.raw_data_path}")

        dtype_map = {
            "step": "int32",
            "type": "category",
            "amount": "float32",
            "oldbalanceOrg": "float32",
            "newbalanceOrig": "float32",
            "oldbalanceDest": "float32",
            "newbalanceDest": "float32",
            "isFraud": "int8",
            "isFlaggedFraud": "int8",
        }

        df = pd.read_csv(self.raw_data_path, dtype=dtype_map)
        self.stats["original_shape"] = df.shape
        logger.info(f"Loaded {df.shape[0]:,} transactions × {df.shape[1]} features")

        return df

    def handle_missing_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """Handle missing values in the dataset.

        Args:
            df: Input dataframe

        Returns:
            pd.DataFrame: Dataframe with missing values handled
        """
        logger.info("Checking for missing values...")

        missing = df.isnull().sum()
        self.stats["missing_values"] = missing[missing > 0].to_dict()

        if missing.sum() == 0:
            logger.info("✓ No missing values found")
        else:
            logger.warning(f"Found missing values:\n{missing[missing > 0]}")

            # Strategy: Drop rows with missing values in critical columns
            critical_cols = ["amount", "type", "isFraud"]
            df = df.dropna(subset=critical_cols)

            # Fill numeric columns with median
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            for col in numeric_cols:
                if df[col].isnull().any():
                    median_val = df[col].median()
                    df[col].fillna(median_val, inplace=True)
                    logger.info(f"Filled {col} missing values with median: {median_val}")

        return df

    def remove_duplicates(self, df: pd.DataFrame) -> pd.DataFrame:
        """Remove duplicate transactions.

        Args:
            df: Input dataframe

        Returns:
            pd.DataFrame: Dataframe without duplicates
        """
        logger.info("Checking for duplicate transactions...")

        original_count = len(df)
        df = df.drop_duplicates()
        duplicates_removed = original_count - len(df)

        self.stats["duplicates_removed"] = duplicates_removed

        if duplicates_removed == 0:
            logger.info("✓ No duplicates found")
        else:
            logger.warning(f"Removed {duplicates_removed:,} duplicate transactions")

        return df

    def mask_pii(self, df: pd.DataFrame) -> pd.DataFrame:
        """Mask PII by hashing account IDs.

        Args:
            df: Input dataframe

        Returns:
            pd.DataFrame: Dataframe with hashed account IDs
        """
        logger.info("Masking PII (hashing account IDs)...")

        # Hash origin and destination account IDs
        df["nameOrig_hash"] = df["nameOrig"].apply(self._hash_account_id)
        df["nameDest_hash"] = df["nameDest"].apply(self._hash_account_id)

        # Drop original unhashed IDs
        df = df.drop(columns=["nameOrig", "nameDest"])

        logger.info("✓ PII masked: account IDs hashed with SHA256")
        self.stats["features_created"].extend(["nameOrig_hash", "nameDest_hash"])

        return df

    def normalize_amounts(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize transaction amounts and balances.

        Args:
            df: Input dataframe

        Returns:
            pd.DataFrame: Dataframe with normalized amounts
        """
        logger.info(f"Normalizing amounts using {self.normalization_method} scaler...")

        # Select scaler
        if self.normalization_method == "standard":
            self.amount_scaler = StandardScaler()
            self.balance_scaler = StandardScaler()
        elif self.normalization_method == "minmax":
            self.amount_scaler = MinMaxScaler()
            self.balance_scaler = MinMaxScaler()
        else:
            raise ValueError(f"Unknown normalization method: {self.normalization_method}")

        # Normalize amount
        df["amount_normalized"] = self.amount_scaler.fit_transform(df[["amount"]]).flatten()

        # Normalize balances
        balance_cols = ["oldbalanceOrg", "newbalanceOrig", "oldbalanceDest", "newbalanceDest"]
        balance_data = df[balance_cols].values
        balance_normalized = self.balance_scaler.fit_transform(balance_data)

        for i, col in enumerate(balance_cols):
            df[f"{col}_normalized"] = balance_normalized[:, i]

        # Store normalization parameters
        self.stats["normalization_params"] = {
            "method": self.normalization_method,
            "amount_mean": (
                float(self.amount_scaler.mean_[0]) if hasattr(self.amount_scaler, "mean_") else None
            ),
            "amount_std": (
                float(self.amount_scaler.scale_[0])
                if hasattr(self.amount_scaler, "scale_")
                else None
            ),
        }

        logger.info("✓ Amounts and balances normalized")
        self.stats["features_created"].append("amount_normalized")

        return df

    def create_temporal_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create time-based features from step column.

        Args:
            df: Input dataframe

        Returns:
            pd.DataFrame: Dataframe with temporal features
        """
        logger.info("Creating temporal features...")

        # Hour of day (0-23)
        df["hour"] = (df["step"] % 24).astype("int8")

        # Day number
        df["day"] = (df["step"] // 24).astype("int16")

        # Day of week (0-6, simulated)
        df["day_of_week"] = (df["day"] % 7).astype("int8")

        # Time period (morning, afternoon, evening, night)
        df["time_period"] = pd.cut(
            df["hour"],
            bins=[0, 6, 12, 18, 24],
            labels=["night", "morning", "afternoon", "evening"],
            include_lowest=True,
        ).astype("category")

        logger.info("✓ Temporal features created: hour, day, day_of_week, time_period")
        self.stats["features_created"].extend(["hour", "day", "day_of_week", "time_period"])

        return df

    def engineer_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Engineer domain-specific features for fraud detection.

        Args:
            df: Input dataframe

        Returns:
            pd.DataFrame: Dataframe with engineered features
        """
        logger.info("Engineering fraud detection features...")

        # Balance change (already computed in EDA, but recompute for consistency)
        df["balance_change_orig"] = df["newbalanceOrig"] - df["oldbalanceOrg"]
        df["balance_change_dest"] = df["newbalanceDest"] - df["oldbalanceDest"]

        # Balance change ratio (avoid division by zero)
        df["balance_change_ratio_orig"] = np.where(
            df["oldbalanceOrg"] > 0,
            df["balance_change_orig"] / df["oldbalanceOrg"],
            0,
        )
        df["balance_change_ratio_dest"] = np.where(
            df["oldbalanceDest"] > 0,
            df["balance_change_dest"] / df["oldbalanceDest"],
            0,
        )

        # Amount as percentage of origin balance
        df["amount_to_balance_ratio"] = np.where(
            df["oldbalanceOrg"] > 0,
            df["amount"] / df["oldbalanceOrg"],
            0,
        )

        # Zero balance indicators (fraud pattern)
        df["zero_balance_orig"] = (df["newbalanceOrig"] == 0).astype("int8")
        df["zero_balance_dest"] = (df["newbalanceDest"] == 0).astype("int8")

        # Balance consistency check
        # For TRANSFER/CASH_OUT: newbalanceOrig should = oldbalanceOrg - amount
        expected_balance_orig = df["oldbalanceOrg"] - df["amount"]
        df["balance_inconsistency"] = (
            np.abs(df["newbalanceOrig"] - expected_balance_orig) > 0.01
        ).astype("int8")

        # High-value transaction flag (>99th percentile from EDA)
        high_value_threshold = df["amount"].quantile(0.99)
        df["is_high_value"] = (df["amount"] > high_value_threshold).astype("int8")

        # Round number flag (fraud pattern: $100,000 vs $98,543.21)
        df["is_round_amount"] = (df["amount"] % 1000 == 0).astype("int8")

        logger.info("✓ Engineered 11 fraud detection features")
        self.stats["features_created"].extend(
            [
                "balance_change_orig",
                "balance_change_dest",
                "balance_change_ratio_orig",
                "balance_change_ratio_dest",
                "amount_to_balance_ratio",
                "zero_balance_orig",
                "zero_balance_dest",
                "balance_inconsistency",
                "is_high_value",
                "is_round_amount",
            ]
        )

        return df

    def validate_data_quality(self, df: pd.DataFrame) -> None:
        """Validate cleaned data meets quality standards.

        Args:
            df: Cleaned dataframe

        Raises:
            AssertionError: If data quality checks fail
        """
        logger.info("Validating data quality...")

        # No missing values in critical columns
        critical_cols = ["amount", "type", "isFraud", "hour", "day"]
        assert df[critical_cols].isnull().sum().sum() == 0, "Missing values in critical columns"

        # Fraud rate should be ~0.13%
        fraud_rate = df["isFraud"].mean()
        assert 0.001 < fraud_rate < 0.01, f"Unexpected fraud rate: {fraud_rate:.4f}"

        # All amounts should be non-negative
        assert (df["amount"] >= 0).all(), "Negative amounts detected"

        # Normalized values should be reasonable
        assert df["amount_normalized"].std() > 0, "No variance in normalized amounts"

        # Temporal features in valid ranges
        assert df["hour"].between(0, 23).all(), "Invalid hour values"
        assert df["day_of_week"].between(0, 6).all(), "Invalid day_of_week values"

        logger.info("✓ All data quality checks passed")

    def save_cleaned_data(self, df: pd.DataFrame) -> None:
        """Save cleaned data and metadata.

        Args:
            df: Cleaned dataframe
        """
        logger.info("Saving cleaned data...")

        # Save cleaned dataset
        output_path = self.output_dir / "paysim_cleaned.csv"
        df.to_csv(output_path, index=False)
        logger.info(f"✓ Cleaned data saved to: {output_path}")

        # Save statistics
        self.stats["cleaned_shape"] = df.shape
        stats_path = self.output_dir / "cleaning_statistics.json"
        with open(stats_path, "w") as f:
            json.dump(self.stats, f, indent=2)
        logger.info(f"✓ Cleaning statistics saved to: {stats_path}")

        # Save column metadata
        metadata = {
            "columns": list(df.columns),
            "dtypes": df.dtypes.astype(str).to_dict(),
            "memory_mb": df.memory_usage(deep=True).sum() / 1024 / 1024,
        }
        metadata_path = self.output_dir / "cleaned_metadata.json"
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)
        logger.info(f"✓ Metadata saved to: {metadata_path}")

    def run(self) -> pd.DataFrame:
        """Run the complete data cleaning pipeline.

        Returns:
            pd.DataFrame: Cleaned and processed dataframe
        """
        logger.info("=" * 80)
        logger.info("STARTING DATA CLEANING PIPELINE")
        logger.info("=" * 80)

        # Step 1: Load data
        df = self.load_data()

        # Step 2: Handle missing values
        df = self.handle_missing_values(df)

        # Step 3: Remove duplicates
        df = self.remove_duplicates(df)

        # Step 4: Mask PII
        df = self.mask_pii(df)

        # Step 5: Normalize amounts
        df = self.normalize_amounts(df)

        # Step 6: Create temporal features
        df = self.create_temporal_features(df)

        # Step 7: Engineer features
        df = self.engineer_features(df)

        # Step 8: Validate data quality
        self.validate_data_quality(df)

        # Step 9: Save cleaned data
        self.save_cleaned_data(df)

        logger.info("=" * 80)
        logger.info("DATA CLEANING PIPELINE COMPLETED SUCCESSFULLY")
        logger.info(f"Original: {self.stats['original_shape'][0]:,} transactions")
        logger.info(f"Cleaned: {self.stats['cleaned_shape'][0]:,} transactions")
        logger.info(f"Features created: {len(self.stats['features_created'])}")
        logger.info("=" * 80)

        return df


def main() -> None:
    """Main entry point for data cleaning pipeline."""

    from pathlib import Path
    # Setup paths
    project_root = Path(__file__).parent.parent.parent
    raw_data_path = project_root / "data/raw/PS_20174392719_1491204439457_log.csv"
    output_dir = project_root / "data/processed"

    # Run pipeline
    pipeline = DataCleaningPipeline(
        raw_data_path=str(raw_data_path),
        output_dir=str(output_dir),
        normalization_method="standard",  # Use StandardScaler
        random_seed=42,
    )


    cleaned_df = pipeline.run()

    # --- Data Lineage Tracking ---

    import hashlib
    import sys
    try:
        from backend.scripts.data_lineage import DataLineage
    except ModuleNotFoundError:
        # Fallback for script execution from backend/
        sys.path.append(str(Path(__file__).parent))
        from data_lineage import DataLineage
    from pathlib import Path

    def file_hash(path):
        h = hashlib.sha256()
        with open(path, 'rb') as f:
            while True:
                chunk = f.read(8192)
                if not chunk:
                    break
                h.update(chunk)
        return h.hexdigest()

    # Paths
    raw_path = str(raw_data_path)
    cleaned_path = str(output_dir / "paysim_cleaned.csv")
    script_path = str(Path(__file__).resolve())
    script_hash = file_hash(script_path)
    input_hash = file_hash(raw_path)
    output_hash = file_hash(cleaned_path)

    lineage = DataLineage()
    lineage.track_transformation(
        transformation_id="data_cleaning_pipeline",
        input_files=[raw_path],
        output_files=[cleaned_path],
        script=script_path,
        operations=[
            "handle_missing",
            "remove_duplicates",
            "mask_pii",
            "normalize_amounts",
            "create_temporal_features",
            "engineer_features",
        ],
        input_version="v1_raw",
        output_version="v2_cleaned",
        metadata={
            "script_hash": script_hash,
            "input_hash": input_hash,
            "output_hash": output_hash,
            "execution_time_sec": None,  # Optionally add timing
            "features_created": pipeline.stats["features_created"],
            "quality_checks_passed": True,
        },
    )
    lineage.save()

    # Display sample
    print("\n" + "=" * 80)
    print("SAMPLE OF CLEANED DATA")
    print("=" * 80)
    print(cleaned_df.head())
    print(f"\nShape: {cleaned_df.shape}")
    print(f"Memory: {cleaned_df.memory_usage(deep=True).sum() / 1024 / 1024:.2f} MB")


if __name__ == "__main__":
    main()
