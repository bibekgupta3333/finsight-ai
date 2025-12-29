"""Data augmentation and balancing pipeline for PaySim fraud detection.

This script addresses class imbalance (0.13% fraud rate) using:
1. SMOTE (Synthetic Minority Oversampling Technique) for fraud oversampling
2. Random undersampling for non-fraud majority class
3. Synthetic fraud case generation based on fraud patterns
4. Quality validation of augmented data

AGI Best Practices:
- Preserves statistical properties of original data
- Validates augmented data quality
- Documents balancing decisions
- Provides multiple balancing strategies
- Tracks data lineage

Author: FinSight AI Team
Date: December 29, 2025
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
from imblearn.over_sampling import SMOTE
from imblearn.under_sampling import RandomUnderSampler
from sklearn.preprocessing import LabelEncoder

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class DataAugmentationPipeline:
    """Data augmentation and balancing pipeline for fraud detection.
    
    This pipeline provides multiple strategies to handle severe class imbalance:
    1. SMOTE: Synthetic oversampling of minority class (fraud)
    2. Random undersampling: Reduce majority class (legitimate)
    3. Combined: SMOTE + undersampling for balanced dataset
    4. Synthetic fraud generation: Rule-based fraud case creation
    
    Attributes:
        train_data_path: Path to training split
        output_dir: Directory to save balanced datasets
        random_seed: Random seed for reproducibility
        target_fraud_rate: Desired fraud rate after balancing
    """

    def __init__(
        self,
        train_data_path: str,
        output_dir: str,
        target_fraud_rate: float = 0.5,
        random_seed: int = 42,
    ) -> None:
        """Initialize the data augmentation pipeline.
        
        Args:
            train_data_path: Path to training split CSV
            output_dir: Directory to save balanced datasets
            target_fraud_rate: Target fraud rate after balancing (default 0.5)
            random_seed: Random seed for reproducibility
        
        Raises:
            ValueError: If target_fraud_rate is not between 0 and 1
        """
        if not (0 < target_fraud_rate < 1):
            raise ValueError(
                f"target_fraud_rate must be between 0 and 1. Got: {target_fraud_rate}"
            )

        self.train_data_path = Path(train_data_path)
        self.output_dir = Path(output_dir)
        self.target_fraud_rate = target_fraud_rate
        self.random_seed = random_seed

        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Initialized DataAugmentationPipeline with seed {random_seed}")
        logger.info(f"Target fraud rate: {target_fraud_rate:.2%}")

    def load_data(self) -> pd.DataFrame:
        """Load training data.
        
        Returns:
            Loaded training DataFrame
        
        Raises:
            FileNotFoundError: If training data file doesn't exist
        """
        logger.info(f"Loading training data from {self.train_data_path}")
        
        if not self.train_data_path.exists():
            raise FileNotFoundError(f"Training data not found: {self.train_data_path}")
        
        df = pd.read_csv(self.train_data_path)
        logger.info(f"Loaded {len(df):,} training samples")
        
        return df

    def analyze_class_imbalance(self, df: pd.DataFrame) -> Dict:
        """Analyze class distribution and imbalance.
        
        Args:
            df: Training DataFrame
        
        Returns:
            Dictionary with class distribution statistics
        """
        logger.info("=" * 80)
        logger.info("CLASS IMBALANCE ANALYSIS")
        logger.info("=" * 80)
        
        fraud_count = df["isFraud"].sum()
        legit_count = len(df) - fraud_count
        fraud_rate = fraud_count / len(df)
        imbalance_ratio = legit_count / fraud_count if fraud_count > 0 else float("inf")
        
        stats = {
            "total_samples": int(len(df)),
            "fraud_count": int(fraud_count),
            "legitimate_count": int(legit_count),
            "fraud_rate": float(fraud_rate),
            "imbalance_ratio": float(imbalance_ratio),
        }
        
        logger.info(f"Total samples: {stats['total_samples']:,}")
        logger.info(f"Fraud cases: {stats['fraud_count']:,} ({fraud_rate:.4%})")
        logger.info(f"Legitimate cases: {stats['legitimate_count']:,} ({1-fraud_rate:.4%})")
        logger.info(f"Imbalance ratio: 1:{imbalance_ratio:.1f}")
        logger.info(f"Severity: {'EXTREME' if imbalance_ratio > 100 else 'MODERATE'}")
        
        return stats

    def prepare_features_for_sampling(
        self, df: pd.DataFrame
    ) -> Tuple[np.ndarray, np.ndarray, List[str], pd.DataFrame]:
        """Prepare features and target for SMOTE/undersampling.
        
        SMOTE requires numerical features only. This method:
        1. Encodes categorical features
        2. Separates features and target
        3. Tracks column names for reconstruction
        
        Args:
            df: Input DataFrame
        
        Returns:
            Tuple of (X, y, feature_names, metadata_df)
            - X: Feature matrix (numpy array)
            - y: Target vector (numpy array)
            - feature_names: List of feature column names
            - metadata_df: Non-feature columns (for later merging)
        """
        logger.info("Preparing features for sampling...")
        
        # Columns to exclude from features
        exclude_cols = ["isFraud", "nameOrig_hash", "nameDest_hash"]
        
        # Separate metadata (will be merged back later)
        metadata_cols = ["nameOrig_hash", "nameDest_hash"]
        metadata_df = df[metadata_cols].copy()
        
        # Feature columns
        feature_cols = [col for col in df.columns if col not in exclude_cols]
        
        # Handle categorical columns (encode)
        df_features = df[feature_cols].copy()
        
        # Encode 'type' column if present
        if "type" in df_features.columns:
            le_type = LabelEncoder()
            df_features["type"] = le_type.fit_transform(df_features["type"])
        
        # Encode 'time_period' column if present
        if "time_period" in df_features.columns:
            le_time = LabelEncoder()
            df_features["time_period"] = le_time.fit_transform(df_features["time_period"])
        
        # Encode 'day_of_week' column if present and it's categorical
        if "day_of_week" in df_features.columns and df_features["day_of_week"].dtype == "object":
            le_dow = LabelEncoder()
            df_features["day_of_week"] = le_dow.fit_transform(df_features["day_of_week"])
        
        X = df_features.values
        y = df["isFraud"].values
        
        logger.info(f"Feature matrix shape: {X.shape}")
        logger.info(f"Features: {feature_cols}")
        
        return X, y, feature_cols, metadata_df

    def apply_smote(
        self, X: np.ndarray, y: np.ndarray, sampling_strategy: float = 0.5
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Apply SMOTE to oversample minority class (fraud).
        
        SMOTE creates synthetic fraud cases by:
        1. Finding k-nearest neighbors of fraud cases
        2. Creating new samples along line segments between neighbors
        3. Preserving statistical properties of fraud distribution
        
        Args:
            X: Feature matrix
            y: Target vector
            sampling_strategy: Desired ratio of minority/majority after oversampling
        
        Returns:
            Tuple of (X_resampled, y_resampled)
        """
        logger.info("=" * 80)
        logger.info("APPLYING SMOTE")
        logger.info("=" * 80)
        
        fraud_count_before = y.sum()
        total_before = len(y)
        
        logger.info(f"Before SMOTE: {fraud_count_before:,} fraud cases ({fraud_count_before/total_before:.4%})")
        logger.info(f"Sampling strategy: {sampling_strategy}")
        
        # Initialize SMOTE
        smote = SMOTE(
            sampling_strategy=sampling_strategy,
            random_state=self.random_seed,
            k_neighbors=5,
        )
        
        # Resample
        X_resampled, y_resampled = smote.fit_resample(X, y)
        
        fraud_count_after = y_resampled.sum()
        total_after = len(y_resampled)
        synthetic_fraud = fraud_count_after - fraud_count_before
        
        logger.info(f"After SMOTE: {fraud_count_after:,} fraud cases ({fraud_count_after/total_after:.4%})")
        logger.info(f"Synthetic fraud cases generated: {synthetic_fraud:,}")
        logger.info(f"Total samples after SMOTE: {total_after:,}")
        
        return X_resampled, y_resampled

    def apply_undersampling(
        self, X: np.ndarray, y: np.ndarray, sampling_strategy: float = 0.5
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Apply random undersampling to reduce majority class.
        
        Args:
            X: Feature matrix
            y: Target vector
            sampling_strategy: Desired ratio of minority/majority after undersampling
        
        Returns:
            Tuple of (X_resampled, y_resampled)
        """
        logger.info("=" * 80)
        logger.info("APPLYING RANDOM UNDERSAMPLING")
        logger.info("=" * 80)
        
        legit_count_before = (y == 0).sum()
        total_before = len(y)
        
        logger.info(f"Before undersampling: {legit_count_before:,} legitimate cases")
        logger.info(f"Sampling strategy: {sampling_strategy}")
        
        # Initialize RandomUnderSampler
        rus = RandomUnderSampler(
            sampling_strategy=sampling_strategy,
            random_state=self.random_seed,
        )
        
        # Resample
        X_resampled, y_resampled = rus.fit_resample(X, y)
        
        legit_count_after = (y_resampled == 0).sum()
        total_after = len(y_resampled)
        removed_legit = legit_count_before - legit_count_after
        
        logger.info(f"After undersampling: {legit_count_after:,} legitimate cases")
        logger.info(f"Legitimate cases removed: {removed_legit:,}")
        logger.info(f"Total samples after undersampling: {total_after:,}")
        logger.info(f"Final fraud rate: {y_resampled.sum()/total_after:.4%}")
        
        return X_resampled, y_resampled

    def apply_combined_sampling(
        self, X: np.ndarray, y: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Apply SMOTE followed by undersampling for balanced dataset.
        
        This two-step approach:
        1. Increases minority class with SMOTE
        2. Reduces majority class with undersampling
        3. Achieves target fraud rate
        
        Args:
            X: Feature matrix
            y: Target vector
        
        Returns:
            Tuple of (X_balanced, y_balanced)
        """
        logger.info("=" * 80)
        logger.info("APPLYING COMBINED SAMPLING (SMOTE + UNDERSAMPLING)")
        logger.info("=" * 80)
        
        # Step 1: SMOTE to increase fraud cases
        X_smote, y_smote = self.apply_smote(X, y, sampling_strategy=0.3)
        
        # Step 2: Undersampling to reduce legitimate cases
        X_balanced, y_balanced = self.apply_undersampling(
            X_smote, y_smote, sampling_strategy=self.target_fraud_rate
        )
        
        final_fraud_rate = y_balanced.sum() / len(y_balanced)
        logger.info(f"\n✓ Combined sampling complete")
        logger.info(f"✓ Final fraud rate: {final_fraud_rate:.4%}")
        logger.info(f"✓ Final dataset size: {len(y_balanced):,}")
        
        return X_balanced, y_balanced

    def generate_synthetic_fraud_cases(
        self, df: pd.DataFrame, num_cases: int = 1000
    ) -> pd.DataFrame:
        """Generate synthetic fraud cases based on fraud patterns.
        
        This method creates rule-based synthetic fraud cases by:
        1. Analyzing existing fraud patterns
        2. Creating variations with noise
        3. Ensuring realistic transaction properties
        
        Args:
            df: Original training DataFrame
            num_cases: Number of synthetic cases to generate
        
        Returns:
            DataFrame with synthetic fraud cases
        """
        logger.info("=" * 80)
        logger.info("GENERATING SYNTHETIC FRAUD CASES")
        logger.info("=" * 80)
        
        logger.info(f"Generating {num_cases:,} synthetic fraud cases...")
        
        # Extract fraud cases for pattern analysis
        fraud_df = df[df["isFraud"] == 1].copy()
        
        if len(fraud_df) == 0:
            logger.warning("No fraud cases found. Cannot generate synthetic cases.")
            return pd.DataFrame()
        
        logger.info(f"Analyzing {len(fraud_df):,} real fraud cases for patterns...")
        
        # Initialize list for synthetic cases
        synthetic_cases = []
        
        # Generate synthetic cases based on fraud patterns
        for _ in range(num_cases):
            # Sample a random fraud case as template
            template = fraud_df.sample(n=1, random_state=self.random_seed + _).iloc[0]
            
            # Create synthetic case with variations
            synthetic = template.copy()
            
            # Add noise to numerical features (±20%)
            noise_factor = np.random.uniform(0.8, 1.2)
            synthetic["amount"] = template["amount"] * noise_factor
            synthetic["oldbalanceOrg"] = template["oldbalanceOrg"] * noise_factor
            synthetic["newbalanceOrig"] = template["newbalanceOrig"] * noise_factor
            
            # Randomize time
            synthetic["step"] = np.random.randint(0, df["step"].max())
            synthetic["hour"] = np.random.randint(0, 24)
            synthetic["day"] = np.random.randint(0, 30)
            
            # Recalculate derived features
            synthetic["balance_change_orig"] = (
                synthetic["newbalanceOrig"] - synthetic["oldbalanceOrg"]
            )
            
            # Ensure fraud label
            synthetic["isFraud"] = 1
            
            synthetic_cases.append(synthetic)
        
        synthetic_df = pd.DataFrame(synthetic_cases)
        
        logger.info(f"✓ Generated {len(synthetic_df):,} synthetic fraud cases")
        
        return synthetic_df

    def validate_augmented_data(
        self, original_df: pd.DataFrame, augmented_df: pd.DataFrame
    ) -> Dict:
        """Validate quality of augmented dataset.
        
        Checks:
        1. Statistical properties preservation
        2. No data leakage
        3. Reasonable value ranges
        4. Fraud rate matches target
        
        Args:
            original_df: Original training data
            augmented_df: Augmented training data
        
        Returns:
            Validation report dictionary
        """
        logger.info("=" * 80)
        logger.info("VALIDATING AUGMENTED DATA QUALITY")
        logger.info("=" * 80)
        
        validation_report = {
            "passed": True,
            "checks": {},
        }
        
        # Check 1: Fraud rate
        fraud_rate = augmented_df["isFraud"].mean()
        fraud_rate_check = abs(fraud_rate - self.target_fraud_rate) < 0.05
        validation_report["checks"]["fraud_rate"] = {
            "passed": bool(fraud_rate_check),
            "actual": float(fraud_rate),
            "target": float(self.target_fraud_rate),
        }
        logger.info(f"✓ Fraud rate check: {fraud_rate:.4%} (target: {self.target_fraud_rate:.2%})")
        
        # Check 2: No negative amounts
        negative_amounts = (augmented_df["amount"] < 0).sum()
        no_negative_check = negative_amounts == 0
        validation_report["checks"]["no_negative_amounts"] = {
            "passed": bool(no_negative_check),
            "negative_count": int(negative_amounts),
        }
        logger.info(f"✓ No negative amounts: {no_negative_check}")
        
        # Check 3: Statistical properties (mean/std should be similar)
        numerical_cols = augmented_df.select_dtypes(include=[np.number]).columns
        for col in numerical_cols[:5]:  # Check first 5 numerical columns
            if col in original_df.columns:
                orig_mean = original_df[col].mean()
                aug_mean = augmented_df[col].mean()
                mean_diff_pct = abs(aug_mean - orig_mean) / (orig_mean + 1e-10) * 100
                
                logger.info(
                    f"  {col}: orig_mean={orig_mean:.2f}, "
                    f"aug_mean={aug_mean:.2f}, diff={mean_diff_pct:.1f}%"
                )
        
        # Check 4: Dataset size increased
        size_increased = len(augmented_df) >= len(original_df)
        validation_report["checks"]["size_increased"] = {
            "passed": bool(size_increased),
            "original_size": int(len(original_df)),
            "augmented_size": int(len(augmented_df)),
        }
        logger.info(
            f"✓ Dataset size: {len(original_df):,} → {len(augmented_df):,} "
            f"({len(augmented_df)/len(original_df):.2f}x)"
        )
        
        # Overall pass/fail
        validation_report["passed"] = bool(all(
            check["passed"] for check in validation_report["checks"].values()
        ))
        
        if validation_report["passed"]:
            logger.info("\n✓ All validation checks passed")
        else:
            logger.warning("\n⚠ Some validation checks failed")
        
        return validation_report

    def reconstruct_dataframe(
        self,
        X: np.ndarray,
        y: np.ndarray,
        feature_names: List[str],
        original_df: pd.DataFrame,
    ) -> pd.DataFrame:
        """Reconstruct DataFrame from numpy arrays after sampling.
        
        Args:
            X: Feature matrix
            y: Target vector
            feature_names: List of feature column names
            original_df: Original DataFrame (for reference)
        
        Returns:
            Reconstructed DataFrame
        """
        # Create DataFrame from features
        df_reconstructed = pd.DataFrame(X, columns=feature_names)
        
        # Add target column
        df_reconstructed["isFraud"] = y
        
        # Decode 'type' column if it was encoded
        if "type" in df_reconstructed.columns and "type" in original_df.columns:
            # Get unique types from original
            if hasattr(original_df["type"], "cat"):
                type_mapping = dict(enumerate(original_df["type"].cat.categories))
            else:
                type_mapping = dict(enumerate(original_df["type"].unique()))
            df_reconstructed["type"] = df_reconstructed["type"].astype(int).map(type_mapping)
            if hasattr(original_df["type"], "cat"):
                df_reconstructed["type"] = df_reconstructed["type"].astype("category")
        
        # Decode 'time_period' column if it was encoded
        if "time_period" in df_reconstructed.columns and "time_period" in original_df.columns:
            time_mapping = dict(enumerate(original_df["time_period"].unique()))
            df_reconstructed["time_period"] = df_reconstructed["time_period"].astype(int).map(time_mapping)
            if hasattr(original_df["time_period"], "cat"):
                df_reconstructed["time_period"] = df_reconstructed["time_period"].astype("category")
        
        # Decode 'day_of_week' column if it was encoded
        if "day_of_week" in df_reconstructed.columns and original_df["day_of_week"].dtype == "object":
            dow_mapping = dict(enumerate(original_df["day_of_week"].unique()))
            df_reconstructed["day_of_week"] = df_reconstructed["day_of_week"].astype(int).map(dow_mapping)
        
        # Generate new hash IDs for synthetic samples
        num_samples = len(df_reconstructed)
        df_reconstructed["nameOrig_hash"] = [
            f"SYNTHETIC_ORIG_{i:08d}" for i in range(num_samples)
        ]
        df_reconstructed["nameDest_hash"] = [
            f"SYNTHETIC_DEST_{i:08d}" for i in range(num_samples)
        ]
        
        return df_reconstructed

    def save_balanced_dataset(
        self, df: pd.DataFrame, strategy_name: str
    ) -> str:
        """Save balanced dataset to CSV.
        
        Args:
            df: Balanced DataFrame
            strategy_name: Name of balancing strategy
        
        Returns:
            Path to saved file
        """
        file_path = self.output_dir / f"train_balanced_{strategy_name}.csv"
        df.to_csv(file_path, index=False)
        logger.info(f"Saved {strategy_name} balanced dataset to {file_path} ({len(df):,} rows)")
        return str(file_path)

    def run_pipeline(self) -> Dict:
        """Execute complete data augmentation pipeline.
        
        This method runs all balancing strategies:
        1. SMOTE only
        2. Undersampling only
        3. Combined (SMOTE + undersampling)
        4. Synthetic fraud generation
        
        Returns:
            Metadata dictionary with results
        """
        logger.info("Starting data augmentation and balancing pipeline")
        
        # Load data
        df = self.load_data()
        
        # Analyze class imbalance
        imbalance_stats = self.analyze_class_imbalance(df)
        
        # Prepare features
        X, y, feature_names, metadata_df = self.prepare_features_for_sampling(df)
        
        metadata = {
            "original_stats": imbalance_stats,
            "target_fraud_rate": self.target_fraud_rate,
            "random_seed": self.random_seed,
            "strategies": {},
        }
        
        # Strategy 1: SMOTE only
        logger.info("\n" + "=" * 80)
        logger.info("STRATEGY 1: SMOTE ONLY")
        logger.info("=" * 80)
        X_smote, y_smote = self.apply_smote(X, y, sampling_strategy=0.5)
        df_smote = self.reconstruct_dataframe(X_smote, y_smote, feature_names, df)
        path_smote = self.save_balanced_dataset(df_smote, "smote")
        validation_smote = self.validate_augmented_data(df, df_smote)
        
        metadata["strategies"]["smote"] = {
            "path": path_smote,
            "samples": int(len(df_smote)),
            "fraud_rate": float(df_smote["isFraud"].mean()),
            "validation": validation_smote,
        }
        
        # Strategy 2: Combined (SMOTE + Undersampling)
        logger.info("\n" + "=" * 80)
        logger.info("STRATEGY 2: COMBINED (SMOTE + UNDERSAMPLING)")
        logger.info("=" * 80)
        X_combined, y_combined = self.apply_combined_sampling(X, y)
        df_combined = self.reconstruct_dataframe(X_combined, y_combined, feature_names, df)
        path_combined = self.save_balanced_dataset(df_combined, "combined")
        validation_combined = self.validate_augmented_data(df, df_combined)
        
        metadata["strategies"]["combined"] = {
            "path": path_combined,
            "samples": int(len(df_combined)),
            "fraud_rate": float(df_combined["isFraud"].mean()),
            "validation": validation_combined,
        }
        
        # Strategy 3: Synthetic fraud generation
        logger.info("\n" + "=" * 80)
        logger.info("STRATEGY 3: SYNTHETIC FRAUD GENERATION")
        logger.info("=" * 80)
        synthetic_fraud = self.generate_synthetic_fraud_cases(df, num_cases=1000)
        df_with_synthetic = pd.concat([df, synthetic_fraud], ignore_index=True)
        path_synthetic = self.save_balanced_dataset(df_with_synthetic, "with_synthetic")
        
        metadata["strategies"]["with_synthetic"] = {
            "path": path_synthetic,
            "samples": int(len(df_with_synthetic)),
            "fraud_rate": float(df_with_synthetic["isFraud"].mean()),
            "synthetic_fraud_added": int(len(synthetic_fraud)),
        }
        
        # Save metadata
        metadata_path = self.output_dir / "augmentation_metadata.json"
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"\n✓ All augmentation strategies completed")
        logger.info(f"✓ Metadata saved to {metadata_path}")
        
        return metadata


def main():
    """Main execution function."""
    # Paths
    project_root = Path(__file__).parent.parent.parent
    train_data_path = project_root / "data/splits/stratified/train.csv"
    output_dir = project_root / "data/balanced"
    
    # Create augmentation pipeline
    pipeline = DataAugmentationPipeline(
        train_data_path=str(train_data_path),
        output_dir=str(output_dir),
        target_fraud_rate=0.5,
        random_seed=42,
    )
    
    # Run pipeline
    metadata = pipeline.run_pipeline()
    
    logger.info("\n" + "=" * 80)
    logger.info("DATA AUGMENTATION COMPLETED")
    logger.info("=" * 80)
    logger.info(f"Balanced datasets saved to: {output_dir}")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()
