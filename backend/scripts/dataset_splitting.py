"""Dataset splitting pipeline for PaySim fraud detection.

This script implements multiple splitting strategies:
1. Stratified split (maintains fraud rate across splits)
2. Temporal split (respects time ordering for production simulation)

Both strategies produce train/val/test splits (60/20/20).

AGI Best Practices:
- Reproducible (fixed random seed)
- Class balance preservation (stratified)
- Temporal validity (time-aware split)
- Documented decisions
- Quality assertions

Author: FinSight AI Team
Date: December 29, 2025
"""

import json
import logging
from pathlib import Path
from typing import Dict, Tuple

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class DatasetSplitter:
    """Dataset splitting pipeline with stratified and temporal strategies.
    
    Attributes:
        data_path: Path to cleaned dataset
        output_dir: Directory to save splits
        train_size: Proportion for training set (default 0.6)
        val_size: Proportion for validation set (default 0.2)
        test_size: Proportion for test set (default 0.2)
        random_seed: Random seed for reproducibility
    """

    def __init__(
        self,
        data_path: str,
        output_dir: str,
        train_size: float = 0.6,
        val_size: float = 0.2,
        test_size: float = 0.2,
        random_seed: int = 42,
    ) -> None:
        """Initialize the dataset splitter.
        
        Args:
            data_path: Path to cleaned dataset CSV
            output_dir: Directory to save split datasets
            train_size: Training set proportion
            val_size: Validation set proportion
            test_size: Test set proportion
            random_seed: Random seed for reproducibility
        
        Raises:
            ValueError: If split proportions don't sum to 1.0
        """
        if not np.isclose(train_size + val_size + test_size, 1.0):
            raise ValueError(
                f"Split proportions must sum to 1.0. "
                f"Got: {train_size + val_size + test_size}"
            )

        self.data_path = Path(data_path)
        self.output_dir = Path(output_dir)
        self.train_size = train_size
        self.val_size = val_size
        self.test_size = test_size
        self.random_seed = random_seed

        # Create output directories
        self.stratified_dir = self.output_dir / "stratified"
        self.temporal_dir = self.output_dir / "temporal"
        self.stratified_dir.mkdir(parents=True, exist_ok=True)
        self.temporal_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Initialized DatasetSplitter with seed {random_seed}")
        logger.info(f"Split ratios: Train={train_size}, Val={val_size}, Test={test_size}")

    def load_data(self) -> pd.DataFrame:
        """Load cleaned dataset.
        
        Returns:
            Loaded DataFrame
        
        Raises:
            FileNotFoundError: If data file doesn't exist
        """
        logger.info(f"Loading data from {self.data_path}")
        
        if not self.data_path.exists():
            raise FileNotFoundError(f"Data file not found: {self.data_path}")
        
        df = pd.read_csv(self.data_path)
        logger.info(f"Loaded {len(df):,} transactions")
        logger.info(f"Columns: {list(df.columns)}")
        
        # Validate required columns
        required_cols = ["isFraud", "step"]
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            raise ValueError(f"Missing required columns: {missing_cols}")
        
        return df

    def stratified_split(
        self, df: pd.DataFrame
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """Perform stratified split maintaining fraud rate across splits.
        
        This method uses sklearn's train_test_split with stratification on
        the target variable (isFraud) to ensure each split maintains the same
        fraud rate as the original dataset (~0.13%).
        
        Args:
            df: Input DataFrame
        
        Returns:
            Tuple of (train_df, val_df, test_df)
        """
        logger.info("=" * 80)
        logger.info("STRATIFIED SPLIT")
        logger.info("=" * 80)
        
        # Calculate fraud rate
        fraud_rate = df["isFraud"].mean()
        logger.info(f"Overall fraud rate: {fraud_rate:.4%}")
        logger.info(f"Total fraud cases: {df['isFraud'].sum():,}")
        logger.info(f"Total legitimate cases: {(~df['isFraud'].astype(bool)).sum():,}")
        
        # First split: separate test set
        train_val_df, test_df = train_test_split(
            df,
            test_size=self.test_size,
            random_state=self.random_seed,
            stratify=df["isFraud"],
        )
        
        # Second split: separate train and validation
        # Adjust val_size relative to remaining data
        val_size_adjusted = self.val_size / (self.train_size + self.val_size)
        train_df, val_df = train_test_split(
            train_val_df,
            test_size=val_size_adjusted,
            random_state=self.random_seed,
            stratify=train_val_df["isFraud"],
        )
        
        # Validate splits
        self._validate_split(train_df, val_df, test_df, fraud_rate, "Stratified")
        
        return train_df, val_df, test_df

    def temporal_split(
        self, df: pd.DataFrame
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """Perform temporal split respecting time ordering.
        
        This method splits data chronologically based on the 'step' column,
        which represents time periods. This simulates real-world deployment
        where models are trained on past data and tested on future data.
        
        Note: This split does NOT guarantee identical fraud rates across splits
        as fraud patterns may vary over time (realistic scenario).
        
        Args:
            df: Input DataFrame (must have 'step' column)
        
        Returns:
            Tuple of (train_df, val_df, test_df)
        """
        logger.info("=" * 80)
        logger.info("TEMPORAL SPLIT")
        logger.info("=" * 80)
        
        # Sort by time
        df_sorted = df.sort_values("step").reset_index(drop=True)
        
        # Calculate split indices
        n = len(df_sorted)
        train_end = int(n * self.train_size)
        val_end = int(n * (self.train_size + self.val_size))
        
        # Split by time
        train_df = df_sorted.iloc[:train_end].copy()
        val_df = df_sorted.iloc[train_end:val_end].copy()
        test_df = df_sorted.iloc[val_end:].copy()
        
        # Log temporal boundaries
        logger.info(f"Train period: step {train_df['step'].min()} to {train_df['step'].max()}")
        logger.info(f"Val period: step {val_df['step'].min()} to {val_df['step'].max()}")
        logger.info(f"Test period: step {test_df['step'].min()} to {test_df['step'].max()}")
        
        # Validate splits
        fraud_rate = df["isFraud"].mean()
        self._validate_split(train_df, val_df, test_df, fraud_rate, "Temporal")
        
        return train_df, val_df, test_df

    def _validate_split(
        self,
        train_df: pd.DataFrame,
        val_df: pd.DataFrame,
        test_df: pd.DataFrame,
        original_fraud_rate: float,
        split_type: str,
    ) -> None:
        """Validate split quality and log statistics.
        
        Args:
            train_df: Training set
            val_df: Validation set
            test_df: Test set
            original_fraud_rate: Original dataset fraud rate
            split_type: Type of split (for logging)
        """
        total = len(train_df) + len(val_df) + len(test_df)
        
        logger.info(f"\n{split_type} Split Statistics:")
        logger.info(f"{'Set':<12} {'Count':>12} {'Fraud':>12} {'Fraud Rate':>12} {'% of Total':>12}")
        logger.info("-" * 64)
        
        for name, df_split in [("Train", train_df), ("Val", val_df), ("Test", test_df)]:
            count = len(df_split)
            fraud_count = df_split["isFraud"].sum()
            fraud_rate = df_split["isFraud"].mean()
            pct_total = count / total * 100
            
            logger.info(
                f"{name:<12} {count:>12,} {fraud_count:>12,} "
                f"{fraud_rate:>11.4%} {pct_total:>11.1f}%"
            )
        
        logger.info("-" * 64)
        logger.info(f"{'Total':<12} {total:>12,}")
        logger.info(f"Original fraud rate: {original_fraud_rate:.4%}")
        
        # Assertions for data quality
        assert len(train_df) > 0, "Train set is empty"
        assert len(val_df) > 0, "Validation set is empty"
        assert len(test_df) > 0, "Test set is empty"
        assert len(train_df) + len(val_df) + len(test_df) == total, "Data loss detected"
        
        # Check for data leakage (no row should appear in multiple splits)
        train_indices = set(train_df.index)
        val_indices = set(val_df.index)
        test_indices = set(test_df.index)
        
        assert len(train_indices & val_indices) == 0, "Data leakage: train-val overlap"
        assert len(train_indices & test_indices) == 0, "Data leakage: train-test overlap"
        assert len(val_indices & test_indices) == 0, "Data leakage: val-test overlap"
        
        logger.info("✓ Split validation passed")

    def save_splits(
        self,
        train_df: pd.DataFrame,
        val_df: pd.DataFrame,
        test_df: pd.DataFrame,
        split_type: str,
    ) -> Dict[str, str]:
        """Save split datasets to CSV files.
        
        Args:
            train_df: Training set
            val_df: Validation set
            test_df: Test set
            split_type: 'stratified' or 'temporal'
        
        Returns:
            Dictionary with paths to saved files
        """
        output_subdir = self.stratified_dir if split_type == "stratified" else self.temporal_dir
        
        paths = {}
        for name, df_split in [("train", train_df), ("val", val_df), ("test", test_df)]:
            file_path = output_subdir / f"{name}.csv"
            df_split.to_csv(file_path, index=False)
            paths[name] = str(file_path)
            logger.info(f"Saved {name} set to {file_path} ({len(df_split):,} rows)")
        
        return paths

    def generate_metadata(
        self,
        train_df: pd.DataFrame,
        val_df: pd.DataFrame,
        test_df: pd.DataFrame,
        split_type: str,
        split_paths: Dict[str, str],
    ) -> Dict:
        """Generate metadata for split documentation.
        
        Args:
            train_df: Training set
            val_df: Validation set
            test_df: Test set
            split_type: 'stratified' or 'temporal'
            split_paths: Paths to saved split files
        
        Returns:
            Metadata dictionary
        """
        metadata = {
            "split_type": split_type,
            "split_config": {
                "train_size": self.train_size,
                "val_size": self.val_size,
                "test_size": self.test_size,
                "random_seed": self.random_seed,
            },
            "split_statistics": {},
            "split_paths": split_paths,
        }
        
        for name, df_split in [("train", train_df), ("val", val_df), ("test", test_df)]:
            metadata["split_statistics"][name] = {
                "total_count": int(len(df_split)),
                "fraud_count": int(df_split["isFraud"].sum()),
                "legitimate_count": int((~df_split["isFraud"].astype(bool)).sum()),
                "fraud_rate": float(df_split["isFraud"].mean()),
            }
        
        # Add temporal bounds for temporal split
        if split_type == "temporal":
            for name, df_split in [("train", train_df), ("val", val_df), ("test", test_df)]:
                metadata["split_statistics"][name]["time_range"] = {
                    "min_step": int(df_split["step"].min()),
                    "max_step": int(df_split["step"].max()),
                }
        
        return metadata

    def run_all_splits(self) -> Dict:
        """Execute both stratified and temporal splits.
        
        Returns:
            Combined metadata for both split strategies
        """
        logger.info("Starting dataset splitting pipeline")
        
        # Load data
        df = self.load_data()
        
        # Stratified split
        logger.info("\n" + "=" * 80)
        logger.info("EXECUTING STRATIFIED SPLIT")
        logger.info("=" * 80)
        train_strat, val_strat, test_strat = self.stratified_split(df)
        strat_paths = self.save_splits(train_strat, val_strat, test_strat, "stratified")
        strat_metadata = self.generate_metadata(
            train_strat, val_strat, test_strat, "stratified", strat_paths
        )
        
        # Temporal split
        logger.info("\n" + "=" * 80)
        logger.info("EXECUTING TEMPORAL SPLIT")
        logger.info("=" * 80)
        train_temp, val_temp, test_temp = self.temporal_split(df)
        temp_paths = self.save_splits(train_temp, val_temp, test_temp, "temporal")
        temp_metadata = self.generate_metadata(
            train_temp, val_temp, test_temp, "temporal", temp_paths
        )
        
        # Save combined metadata
        metadata = {
            "stratified": strat_metadata,
            "temporal": temp_metadata,
        }
        
        metadata_path = self.output_dir / "split_metadata.json"
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"\n✓ All splits completed successfully")
        logger.info(f"✓ Metadata saved to {metadata_path}")
        
        return metadata


def main():
    """Main execution function."""
    # Paths
    project_root = Path(__file__).parent.parent.parent
    data_path = project_root / "data/processed/paysim_cleaned.csv"
    output_dir = project_root / "data/splits"
    
    # Create splitter
    splitter = DatasetSplitter(
        data_path=str(data_path),
        output_dir=str(output_dir),
        train_size=0.6,
        val_size=0.2,
        test_size=0.2,
        random_seed=42,
    )
    
    # Run all splits
    metadata = splitter.run_all_splits()
    
    logger.info("\n" + "=" * 80)
    logger.info("DATASET SPLITTING COMPLETED")
    logger.info("=" * 80)
    logger.info(f"Stratified splits saved to: {splitter.stratified_dir}")
    logger.info(f"Temporal splits saved to: {splitter.temporal_dir}")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()
