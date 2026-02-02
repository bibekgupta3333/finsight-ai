"""
LightGBM Model Training Script (Memory Optimized)

This script implements fast LightGBM training:
1. Data loading with sampling (M4 Pro compatible)
2. Native categorical feature support
3. Fast training with early stopping
4. Model evaluation and artifact saving

Author: FinSight AI Team
Date: February 1, 2026
"""

import argparse
import gc
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Tuple

import lightgbm as lgb
import mlflow
import mlflow.lightgbm
import numpy as np
import pandas as pd
import psutil
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.preprocessing import StandardScaler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
SPLITS_DIR = DATA_DIR / "splits" / "stratified"
MODELS_DIR = PROJECT_ROOT / "backend" / "models"

MODELS_DIR.mkdir(exist_ok=True, parents=True)


class LightGBMTrainer:
    """Memory-efficient LightGBM trainer with native categorical support."""

    def __init__(
        self,
        project_root: Path,
        max_samples: int = 50000,
        memory_limit_gb: float = 16.0,
        random_state: int = 42
    ):
        """
        Initialize LightGBM trainer.

        Args:
            project_root: Project root directory
            max_samples: Maximum training samples
            memory_limit_gb: Memory limit in GB
            random_state: Random seed
        """
        self.project_root = project_root
        self.max_samples = max_samples
        self.memory_limit_gb = memory_limit_gb
        self.random_state = random_state

        self.scaler = StandardScaler()
        self.feature_names = None
        self.categorical_features = None
        self.model = None

    def _log_memory(self):
        """Log current memory usage."""
        process = psutil.Process()
        mem_info = process.memory_info()
        mem_gb = mem_info.rss / 1024**3
        available_gb = psutil.virtual_memory().available / 1024**3
        logger.info(f"Memory: {mem_gb:.2f}GB ({mem_gb/24*100:.1f}%), Available: {available_gb:.2f}GB")

    def load_data_sample(self) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """Load and sample data for memory efficiency."""
        logger.info("=" * 80)
        logger.info("STEP 1: LOADING DATA")
        logger.info("=" * 80)

        train_path = SPLITS_DIR / "train.csv"
        val_path = SPLITS_DIR / "val.csv"
        test_path = DATA_DIR / "splits" / "temporal" / "test.csv"

        logger.info(f"Loading from: {train_path}")

        # Load with sampling
        train_df = pd.read_csv(train_path, nrows=self.max_samples)
        val_df = pd.read_csv(val_path, nrows=self.max_samples // 5)
        test_df = pd.read_csv(test_path, nrows=self.max_samples // 5)

        logger.info(f"Train: {len(train_df):,}, Val: {len(val_df):,}, Test: {len(test_df):,}")
        logger.info(f"Fraud rates - Train: {train_df['isFraud'].mean():.4f}, Val: {val_df['isFraud'].mean():.4f}, Test: {test_df['isFraud'].mean():.4f}")

        self._log_memory()
        return train_df, val_df, test_df

    def engineer_features(self, df: pd.DataFrame, fit: bool = False) -> Tuple[pd.DataFrame, np.ndarray]:
        """
        Engineer features - LightGBM supports categorical natively.

        Args:
            df: Input dataframe
            fit: Whether to fit scaler

        Returns:
            X: Feature dataframe (with categorical column)
            y: Target vector
        """
        logger.info("Engineering features...")

        # Target
        y = df["isFraud"].values

        # Create feature dataframe
        X = df.copy()

        # Basic numerical features
        numerical_features = [
            "amount",
            "oldbalanceOrg",
            "newbalanceOrig",
            "oldbalanceDest",
            "newbalanceDest"
        ]

        # Derived features
        X["balance_diff_orig"] = X["oldbalanceOrg"] - X["newbalanceOrig"]
        X["balance_diff_dest"] = X["oldbalanceDest"] - X["newbalanceDest"]
        X["amount_to_balance_ratio"] = X["amount"] / (X["oldbalanceOrg"] + 1)

        numerical_features.extend([
            "balance_diff_orig",
            "balance_diff_dest",
            "amount_to_balance_ratio"
        ])

        # Categorical feature (LightGBM handles this natively)
        categorical_features = ["type"]

        # Convert categorical to category dtype
        for cat_col in categorical_features:
            X[cat_col] = X[cat_col].astype("category")

        # Select features
        all_features = numerical_features + categorical_features
        X = X[all_features]

        if fit:
            self.feature_names = all_features
            self.categorical_features = categorical_features
            logger.info(f"Total features: {len(self.feature_names)}")
            logger.info(f"Categorical features: {self.categorical_features}")
            logger.info(f"Numerical features: {numerical_features}")

        # Handle NaN/inf in numerical columns only
        for col in numerical_features:
            X[col] = X[col].replace([np.inf, -np.inf], np.nan).fillna(0)

        return X, y

    def train_lightgbm(
        self,
        X_train: pd.DataFrame,
        y_train: np.ndarray,
        X_val: pd.DataFrame,
        y_val: np.ndarray
    ):
        """
        Train LightGBM with early stopping.

        Args:
            X_train, y_train: Training data
            X_val, y_val: Validation data
        """
        logger.info("=" * 80)
        logger.info("STEP 2: LIGHTGBM TRAINING")
        logger.info("=" * 80)

        self._log_memory()

        # Create LightGBM datasets
        train_data = lgb.Dataset(
            X_train,
            label=y_train,
            categorical_feature=self.categorical_features,
            free_raw_data=False
        )

        val_data = lgb.Dataset(
            X_val,
            label=y_val,
            categorical_feature=self.categorical_features,
            reference=train_data,
            free_raw_data=False
        )

        # Calculate scale_pos_weight for class imbalance
        neg_count = (y_train == 0).sum()
        pos_count = (y_train == 1).sum()
        scale_pos_weight = neg_count / pos_count if pos_count > 0 else 1.0

        logger.info(f"Class distribution - Negative: {neg_count:,}, Positive: {pos_count:,}")
        logger.info(f"Scale pos weight: {scale_pos_weight:.2f}")

        # LightGBM parameters (optimized for fraud detection)
        params = {
            "objective": "binary",
            "metric": ["binary_logloss", "auc"],
            "boosting_type": "gbdt",
            "num_leaves": 31,
            "learning_rate": 0.01,  # Reduced for larger datasets
            "feature_fraction": 0.8,
            "bagging_fraction": 0.8,
            "bagging_freq": 5,
            "min_data_in_leaf": 20,
            "min_sum_hessian_in_leaf": 1e-3,
            "lambda_l1": 0.1,
            "lambda_l2": 0.1,
            "max_depth": -1,  # No limit
            "verbose": 1,
            "random_state": self.random_state,
            "scale_pos_weight": scale_pos_weight,  # Better than is_unbalance
            "num_threads": 2  # Limit for M4 Pro
        }

        logger.info("Training parameters:")
        for key, value in params.items():
            logger.info(f"  {key}: {value}")

        # Train with early stopping
        logger.info("\nTraining LightGBM (with early stopping)...")

        callbacks = [
            lgb.log_evaluation(period=50),
            lgb.early_stopping(stopping_rounds=50)  # More patience
        ]

        self.model = lgb.train(
            params,
            train_data,
            num_boost_round=1000,  # More rounds for larger dataset
            valid_sets=[train_data, val_data],
            valid_names=["train", "validation"],
            callbacks=callbacks
        )

        logger.info(f"\nBest iteration: {self.model.best_iteration}")
        logger.info(f"Best score: {self.model.best_score}")

        self._log_memory()
        gc.collect()

    def evaluate(self, X_test: pd.DataFrame, y_test: np.ndarray) -> Dict[str, float]:
        """
        Evaluate model on test set.

        Args:
            X_test: Test features
            y_test: Test labels

        Returns:
            Dictionary of metrics
        """
        logger.info("=" * 80)
        logger.info("STEP 3: TEST SET EVALUATION")
        logger.info("=" * 80)

        y_test_pred_proba = self.model.predict(X_test, num_iteration=self.model.best_iteration)
        y_test_pred = (y_test_pred_proba > 0.5).astype(int)

        metrics = {
            "accuracy": float(accuracy_score(y_test, y_test_pred)),
            "precision": float(precision_score(y_test, y_test_pred, zero_division=0)),
            "recall": float(recall_score(y_test, y_test_pred, zero_division=0)),
            "f1_score": float(f1_score(y_test, y_test_pred, zero_division=0)),
            "roc_auc": float(roc_auc_score(y_test, y_test_pred_proba))
        }

        logger.info("Test Set Metrics:")
        for metric, value in metrics.items():
            logger.info(f"  {metric}: {value:.4f}")

        cm = confusion_matrix(y_test, y_test_pred)
        logger.info(f"Confusion Matrix:\n{cm}")

        return metrics

    def save_model(self, metrics: Dict[str, float], version: str = "v1"):
        """
        Save model and artifacts.

        Args:
            metrics: Test metrics
            version: Model version
        """
        logger.info("=" * 80)
        logger.info("STEP 4: SAVING MODEL ARTIFACTS")
        logger.info("=" * 80)

        # Save LightGBM model (native format)
        model_path = MODELS_DIR / f"lightgbm_{version}.txt"
        self.model.save_model(str(model_path), num_iteration=self.model.best_iteration)
        logger.info(f"Model saved: {model_path}")

        # Save feature names
        features_path = MODELS_DIR / f"lgb_feature_names_{version}.json"
        with open(features_path, "w") as f:
            json.dump(self.feature_names, f, indent=2)
        logger.info(f"Feature names saved: {features_path}")

        # Save feature importance
        importance = self.model.feature_importance(importance_type="gain")
        importance_dict = dict(zip(self.feature_names, importance.tolist()))
        importance_sorted = sorted(importance_dict.items(), key=lambda x: x[1], reverse=True)

        importance_path = MODELS_DIR / f"lgb_feature_importance_{version}.json"
        with open(importance_path, "w") as f:
            json.dump(dict(importance_sorted), f, indent=2)
        logger.info(f"Feature importance saved: {importance_path}")

        logger.info("\nTop 5 most important features:")
        for feature, importance_val in importance_sorted[:5]:
            logger.info(f"  {feature}: {importance_val:.2f}")

        # Save metadata
        metadata = {
            "model_name": "lightgbm",
            "model_version": version,
            "training_date": datetime.now().isoformat(),
            "dataset_version": "stratified_split",
            "max_samples": self.max_samples,
            "random_state": self.random_state,
            "best_iteration": self.model.best_iteration,
            "metrics": metrics,
            "feature_count": len(self.feature_names),
            "categorical_features": self.categorical_features,
            "top_5_features": importance_sorted[:5]
        }

        metadata_path = MODELS_DIR / f"lightgbm_{version}_metadata.json"
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)
        logger.info(f"Metadata saved: {metadata_path}")

        logger.info("=" * 80)
        logger.info("TRAINING COMPLETE!")
        logger.info("=" * 80)


def main():
    """Main training pipeline."""
    parser = argparse.ArgumentParser(description="Train LightGBM fraud detection model")
    parser.add_argument("--max-samples", type=int, default=50000,
                        help="Maximum training samples (default: 50000 for M4 Pro)")
    parser.add_argument("--memory-limit", type=float, default=16.0,
                        help="Memory limit in GB (default: 16.0)")
    args = parser.parse_args()

    logger.info("=" * 80)
    logger.info("LIGHTGBM MODEL TRAINING (MEMORY OPTIMIZED)")
    logger.info("=" * 80)
    logger.info(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Max samples: {args.max_samples:,}")
    logger.info(f"Memory limit: {args.memory_limit}GB")
    logger.info("=" * 80)

    # Setup MLflow
    mlflow.set_tracking_uri(f"file://{PROJECT_ROOT / 'backend' / 'mlruns'}")
    mlflow.set_experiment("baseline_models")

    # Initialize trainer
    trainer = LightGBMTrainer(
        project_root=PROJECT_ROOT,
        max_samples=args.max_samples,
        memory_limit_gb=args.memory_limit
    )

    # Load data
    train_df, val_df, test_df = trainer.load_data_sample()

    # Feature engineering
    X_train, y_train = trainer.engineer_features(train_df, fit=True)
    X_val, y_val = trainer.engineer_features(val_df, fit=False)
    X_test, y_test = trainer.engineer_features(test_df, fit=False)

     # Start MLflow run
    with mlflow.start_run(run_name="lightgbm_fraud_detection"):
        # Log parameters
        lgb_params = {
            "objective": "binary",
            "metric": ["binary_logloss", "auc"],
            "boosting_type": "gbdt",
            "num_leaves": 31,
            "learning_rate": 0.01,
            "feature_fraction": 0.9,
            "bagging_fraction": 0.8,
            "bagging_freq": 5,
            "verbose": -1,
            "max_depth": -1,
            "min_child_samples": 20,
            "num_boost_round": 1000,
            "early_stopping_rounds": 50,
            "max_samples": args.max_samples,
            "memory_limit_gb": args.memory_limit
        }
        mlflow.log_params(lgb_params)

        # Train
        trainer.train_lightgbm(X_train, y_train, X_val, y_val)

        # Evaluate
        metrics = trainer.evaluate(X_test, y_test)

        # Log metrics
        mlflow.log_metrics(metrics)

        # Log model
        mlflow.lightgbm.log_model(trainer.model, "model")

        # Log artifacts
        metadata_path = MODELS_DIR / "lightgbm_v1_metadata.json"
        if metadata_path.exists():
            mlflow.log_artifact(str(metadata_path), "metadata")

        # Set tags
        mlflow.set_tags({
            "model_type": "lightgbm",
            "framework": "lightgbm",
            "task": "fraud_detection",
            "best_model": "true"
        })

    # Save
    trainer.save_model(metrics, version="v1")

    logger.info(f"\nFinal F1-Score: {metrics['f1_score']:.4f}")
    logger.info("\nView results in MLflow UI:")
    logger.info("  mlflow ui --backend-store-uri file://./mlruns --port 5000")
    logger.info("  http://localhost:5000")


if __name__ == "__main__":
    main()
