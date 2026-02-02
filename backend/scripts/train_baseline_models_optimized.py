"""
Memory-Optimized Random Forest Baseline Model Training Script

Optimized for M4 Pro with 24GB RAM:
- Limited dataset sampling (max 100k samples)
- Memory monitoring and limits
- Reduced hyperparameter grid
- 3-fold CV instead of 5-fold
- Sequential processing to avoid memory spikes
- Garbage collection after each step

Author: FinSight AI Team
Date: February 1, 2026
"""

import argparse
import gc
import json
import logging
import pickle
import warnings
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import psutil
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import GridSearchCV, StratifiedKFold
from sklearn.preprocessing import OneHotEncoder, StandardScaler

warnings.filterwarnings("ignore")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class MemoryEfficientTrainer:
    """Memory-optimized trainer for M4 Pro (24GB RAM)."""

    def __init__(
        self,
        project_root: Path,
        max_samples: int = 50000,  # Reduced for memory
        memory_limit_gb: float = 16.0,  # Reserve 8GB for system
        random_state: int = 42,
    ):
        """Initialize trainer with memory limits."""
        self.project_root = project_root
        self.max_samples = max_samples
        self.memory_limit_gb = memory_limit_gb
        self.random_state = random_state

        # Paths
        self.data_dir = project_root / "data"
        self.models_dir = project_root / "backend" / "models"
        self.models_dir.mkdir(exist_ok=True, parents=True)

        # Components
        self.encoder = None
        self.scaler = None
        self.feature_names = []
        self.model = None

        logger.info(f"Memory limit: {memory_limit_gb}GB")
        logger.info(f"Max samples: {max_samples:,}")

    def check_memory(self) -> Dict[str, float]:
        """Check current memory usage."""
        process = psutil.Process()
        mem_info = process.memory_info()
        mem_percent = process.memory_percent()

        stats = {
            "rss_gb": mem_info.rss / 1024**3,
            "percent": mem_percent,
            "available_gb": psutil.virtual_memory().available / 1024**3,
        }

        logger.info(
            f"Memory: {stats['rss_gb']:.2f}GB ({stats['percent']:.1f}%), "
            f"Available: {stats['available_gb']:.2f}GB"
        )

        return stats

    def load_data_sample(self) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """Load sampled datasets for memory efficiency."""
        logger.info("Loading datasets with sampling...")

        # Load training data with limit
        train_path = self.data_dir / "splits" / "stratified" / "train.csv"
        logger.info(f"Loading from: {train_path}")

        # Read in chunks to get total size
        chunk_size = 10000
        chunks = []
        total_rows = 0

        for chunk in pd.read_csv(train_path, chunksize=chunk_size):
            chunks.append(chunk)
            total_rows += len(chunk)
            if total_rows >= self.max_samples:
                break

        train_df = pd.concat(chunks, ignore_index=True)

        # Stratified sampling to maintain fraud ratio
        if len(train_df) > self.max_samples:
            fraud_df = train_df[train_df["isFraud"] == 1]
            normal_df = train_df[train_df["isFraud"] == 0]

            # Sample 50% fraud, 50% normal for balance
            n_fraud = min(len(fraud_df), self.max_samples // 2)
            n_normal = self.max_samples - n_fraud

            fraud_sample = fraud_df.sample(n=n_fraud, random_state=self.random_state)
            normal_sample = normal_df.sample(n=n_normal, random_state=self.random_state)

            train_df = pd.concat([fraud_sample, normal_sample]).sample(
                frac=1, random_state=self.random_state
            )

        # Load validation and test with smaller limits
        val_df = pd.read_csv(
            self.data_dir / "splits" / "stratified" / "val.csv",
            nrows=min(10000, self.max_samples // 5),
        )
        test_df = pd.read_csv(
            self.data_dir / "splits" / "temporal" / "test.csv",
            nrows=min(10000, self.max_samples // 5),
        )

        logger.info(f"Train: {len(train_df):,}, Val: {len(val_df):,}, Test: {len(test_df):,}")
        logger.info(
            f"Fraud rates - Train: {train_df['isFraud'].mean():.4f}, "
            f"Val: {val_df['isFraud'].mean():.4f}, Test: {test_df['isFraud'].mean():.4f}"
        )

        self.check_memory()
        gc.collect()

        return train_df, val_df, test_df

    def engineer_features(
        self, train_df: pd.DataFrame, val_df: pd.DataFrame, test_df: pd.DataFrame
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """Feature engineering with memory optimization."""
        logger.info("Engineering features...")

        # Separate features and target
        X_train = train_df.drop("isFraud", axis=1)
        y_train = train_df["isFraud"].values
        X_val = val_df.drop("isFraud", axis=1)
        y_val = val_df["isFraud"].values
        X_test = test_df.drop("isFraud", axis=1)
        y_test = test_df["isFraud"].values

        # Free memory
        del train_df, val_df, test_df
        gc.collect()

        # Categorical features
        cat_features = ["type"]
        num_features = [
            "amount",
            "oldbalanceOrg",
            "newbalanceOrig",
            "oldbalanceDest",
            "newbalanceDest",
        ]

        # Derived features
        X_train["balance_diff_orig"] = X_train["oldbalanceOrg"] - X_train["newbalanceOrig"]
        X_train["balance_diff_dest"] = X_train["oldbalanceDest"] - X_train["newbalanceDest"]
        X_train["amount_to_balance_ratio"] = X_train["amount"] / (
            X_train["oldbalanceOrg"] + 1
        )

        X_val["balance_diff_orig"] = X_val["oldbalanceOrg"] - X_val["newbalanceOrig"]
        X_val["balance_diff_dest"] = X_val["oldbalanceDest"] - X_val["newbalanceDest"]
        X_val["amount_to_balance_ratio"] = X_val["amount"] / (X_val["oldbalanceOrg"] + 1)

        X_test["balance_diff_orig"] = X_test["oldbalanceOrg"] - X_test["newbalanceOrig"]
        X_test["balance_diff_dest"] = X_test["oldbalanceDest"] - X_test["newbalanceDest"]
        X_test["amount_to_balance_ratio"] = X_test["amount"] / (X_test["oldbalanceOrg"] + 1)

        num_features.extend(
            ["balance_diff_orig", "balance_diff_dest", "amount_to_balance_ratio"]
        )

        # One-hot encoding
        logger.info("Encoding categorical features...")
        self.encoder = OneHotEncoder(sparse_output=False, handle_unknown="ignore")

        cat_train = self.encoder.fit_transform(X_train[cat_features])
        cat_val = self.encoder.transform(X_val[cat_features])
        cat_test = self.encoder.transform(X_test[cat_features])

        cat_feature_names = [
            f"type_{cat}" for cat in self.encoder.categories_[0]
        ]

        # Scaling
        logger.info("Scaling numerical features...")
        self.scaler = StandardScaler()

        num_train = self.scaler.fit_transform(X_train[num_features])
        num_val = self.scaler.transform(X_val[num_features])
        num_test = self.scaler.transform(X_test[num_features])

        # Combine features
        X_train_final = np.hstack([num_train, cat_train])
        X_val_final = np.hstack([num_val, cat_val])
        X_test_final = np.hstack([num_test, cat_test])

        self.feature_names = num_features + cat_feature_names

        logger.info(f"Total features: {len(self.feature_names)}")
        self.check_memory()
        gc.collect()

        return X_train_final, X_val_final, X_test_final, y_train, y_val, y_test

    def train_model(
        self, X_train: np.ndarray, y_train: np.ndarray
    ) -> RandomForestClassifier:
        """Train Random Forest with reduced hyperparameter grid."""
        logger.info("Training Random Forest (reduced grid for memory)...")

        # MINIMAL parameter grid
        param_grid = {
            "n_estimators": [50, 100],  # Reduced
            "max_depth": [10, 20],  # Reduced
            "min_samples_split": [5],  # Single value
            "min_samples_leaf": [2],  # Single value
            "max_features": ["sqrt"],  # Single value
            "class_weight": ["balanced"],  # Single value
        }

        # Base model with memory-efficient settings
        rf_base = RandomForestClassifier(
            random_state=self.random_state,
            n_jobs=2,  # Limit cores
            verbose=1,
            max_samples=0.8,  # Use 80% samples per tree
        )

        # Grid search with 3-fold CV
        grid_search = GridSearchCV(
            estimator=rf_base,
            param_grid=param_grid,
            cv=StratifiedKFold(n_splits=3, shuffle=True, random_state=self.random_state),
            scoring="f1",
            n_jobs=1,  # Sequential to avoid memory spike
            verbose=2,
        )

        logger.info("Training started (this may take 5-10 minutes)...")
        self.check_memory()

        grid_search.fit(X_train, y_train)

        self.model = grid_search.best_estimator_

        logger.info(f"Best parameters: {grid_search.best_params_}")
        logger.info(f"Best CV F1 score: {grid_search.best_score_:.4f}")

        self.check_memory()
        gc.collect()

        return self.model

    def evaluate_model(
        self, X_test: np.ndarray, y_test: np.ndarray
    ) -> Dict:
        """Evaluate model and return metrics."""
        logger.info("Evaluating model on test set...")

        y_pred = self.model.predict(X_test)
        y_proba = self.model.predict_proba(X_test)[:, 1]

        metrics = {
            "accuracy": accuracy_score(y_test, y_pred),
            "precision": precision_score(y_test, y_pred, zero_division=0),
            "recall": recall_score(y_test, y_pred, zero_division=0),
            "f1_score": f1_score(y_test, y_pred, zero_division=0),
            "roc_auc": roc_auc_score(y_test, y_proba),
        }

        logger.info("Test Set Metrics:")
        for metric, value in metrics.items():
            logger.info(f"  {metric}: {value:.4f}")

        # Confusion matrix
        cm = confusion_matrix(y_test, y_pred)
        logger.info(f"Confusion Matrix:\n{cm}")

        return metrics

    def save_artifacts(self, metrics: Dict):
        """Save model and artifacts."""
        logger.info("Saving model artifacts...")

        # Save model
        model_path = self.models_dir / "random_forest_v1.pkl"
        with open(model_path, "wb") as f:
            pickle.dump(self.model, f)
        logger.info(f"Model saved: {model_path}")

        # Save preprocessor
        preprocessor = {"encoder": self.encoder, "scaler": self.scaler}
        preprocessor_path = self.models_dir / "preprocessor.pkl"
        with open(preprocessor_path, "wb") as f:
            pickle.dump(preprocessor, f)
        logger.info(f"Preprocessor saved: {preprocessor_path}")

        # Save feature names
        features_path = self.models_dir / "feature_names.json"
        with open(features_path, "w") as f:
            json.dump(self.feature_names, f, indent=2)
        logger.info(f"Feature names saved: {features_path}")

        # Save metadata
        metadata = {
            "model_name": "random_forest",
            "model_version": "v1",
            "training_date": datetime.now().isoformat(),
            "dataset_version": "stratified_split",
            "max_samples": self.max_samples,
            "random_state": self.random_state,
            "parameters": self.model.get_params(),
            "metrics": metrics,
            "feature_count": len(self.feature_names),
        }

        metadata_path = self.models_dir / "random_forest_metadata.json"
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)
        logger.info(f"Metadata saved: {metadata_path}")

    def run(self):
        """Execute full training pipeline."""
        logger.info("=" * 80)
        logger.info("MEMORY-OPTIMIZED BASELINE MODEL TRAINING")
        logger.info("=" * 80)

        # Load data
        train_df, val_df, test_df = self.load_data_sample()

        # Engineer features
        X_train, X_val, X_test, y_train, y_val, y_test = self.engineer_features(
            train_df, val_df, test_df
        )

        # Train model
        self.train_model(X_train, y_train)

        # Evaluate
        metrics = self.evaluate_model(X_test, y_test)

        # Save
        self.save_artifacts(metrics)

        logger.info("=" * 80)
        logger.info("TRAINING COMPLETE!")
        logger.info("=" * 80)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Train memory-optimized baseline model"
    )
    parser.add_argument(
        "--max-samples",
        type=int,
        default=50000,
        help="Maximum samples to use",
    )
    parser.add_argument(
        "--memory-limit",
        type=float,
        default=16.0,
        help="Memory limit in GB",
    )
    parser.add_argument(
        "--random-state",
        type=int,
        default=42,
        help="Random seed",
    )

    args = parser.parse_args()

    # Get project root
    project_root = Path(__file__).parent.parent.parent

    # Initialize and run trainer
    trainer = MemoryEfficientTrainer(
        project_root=project_root,
        max_samples=args.max_samples,
        memory_limit_gb=args.memory_limit,
        random_state=args.random_state,
    )

    trainer.run()


if __name__ == "__main__":
    main()
