"""
XGBoost Model Training Script with Optuna Hyperparameter Tuning

This script implements memory-optimized XGBoost training:
1. Data loading with stratified sampling (M4 Pro compatible)
2. Feature engineering (13 features)
3. Optuna hyperparameter optimization
4. Early stopping on validation set
5. Model evaluation and artifact saving

Author: FinSight AI Team
Date: February 1, 2026
"""

import argparse
import gc
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Tuple

import numpy as np
import optuna
import pandas as pd
import psutil
import xgboost as xgb
from dotenv import load_dotenv
from sklearn.metrics import (
    accuracy_score,
    auc,
    balanced_accuracy_score,
    classification_report,
    cohen_kappa_score,
    confusion_matrix,
    f1_score,
    matthews_corrcoef,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.preprocessing import OneHotEncoder, StandardScaler

# MLflow for experiment tracking
import mlflow
import mlflow.xgboost

# Load environment variables
load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env.local")

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


class XGBoostTrainer:
    """Memory-efficient XGBoost trainer with Optuna optimization."""

    def __init__(
        self,
        project_root: Path,
        max_samples: int = 50000,
        memory_limit_gb: float = 16.0,
        random_state: int = 42,
        n_trials: int = 20
    ):
        """
        Initialize XGBoost trainer.

        Args:
            project_root: Project root directory
            max_samples: Maximum training samples
            memory_limit_gb: Memory limit in GB
            random_state: Random seed
            n_trials: Number of Optuna trials
        """
        self.project_root = project_root
        self.max_samples = max_samples
        self.memory_limit_gb = memory_limit_gb
        self.random_state = random_state
        self.n_trials = n_trials

        self.scaler = StandardScaler()
        self.encoder = None
        self.feature_names = None
        self.best_model = None
        self.best_params = None

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

    def engineer_features(self, df: pd.DataFrame, fit: bool = False) -> Tuple[np.ndarray, np.ndarray]:
        """
        Engineer features from raw transaction data.

        Args:
            df: Input dataframe
            fit: Whether to fit encoder/scaler

        Returns:
            X: Feature matrix
            y: Target vector
        """
        logger.info("Engineering features...")

        # Target
        y = df["isFraud"].values

        # Basic numerical features
        numerical_features = [
            "amount",
            "oldbalanceOrg",
            "newbalanceOrig",
            "oldbalanceDest",
            "newbalanceDest"
        ]

        # Derived features
        df["balance_diff_orig"] = df["oldbalanceOrg"] - df["newbalanceOrig"]
        df["balance_diff_dest"] = df["oldbalanceDest"] - df["newbalanceDest"]
        df["amount_to_balance_ratio"] = df["amount"] / (df["oldbalanceOrg"] + 1)

        numerical_features.extend([
            "balance_diff_orig",
            "balance_diff_dest",
            "amount_to_balance_ratio"
        ])

        # Categorical encoding
        categorical_features = ["type"]
        if fit:
            self.encoder = OneHotEncoder(sparse_output=False, handle_unknown="ignore")
            categorical_encoded = self.encoder.fit_transform(df[categorical_features])
            categorical_feature_names = self.encoder.get_feature_names_out(categorical_features)
        else:
            categorical_encoded = self.encoder.transform(df[categorical_features])
            categorical_feature_names = self.encoder.get_feature_names_out(categorical_features)

        logger.info(f"Encoding categorical features...")
        logger.info(f"Feature names: {list(categorical_feature_names)}")

        # Combine features
        X_numerical = df[numerical_features].values
        X = np.hstack([X_numerical, categorical_encoded])

        if fit:
            self.feature_names = numerical_features + list(categorical_feature_names)
            logger.info(f"Total features: {len(self.feature_names)}")

        # Handle NaN/inf
        X = np.nan_to_num(X, nan=0.0, posinf=1e10, neginf=-1e10)

        return X, y

    def scale_features(self, X_train: np.ndarray, X_val: np.ndarray, X_test: np.ndarray):
        """Scale features using StandardScaler."""
        logger.info("Scaling numerical features...")

        X_train_scaled = self.scaler.fit_transform(X_train)
        X_val_scaled = self.scaler.transform(X_val)
        X_test_scaled = self.scaler.transform(X_test)

        return X_train_scaled, X_val_scaled, X_test_scaled

    def objective(self, trial: optuna.Trial, X_train: np.ndarray, y_train: np.ndarray, X_val: np.ndarray, y_val: np.ndarray) -> float:
        """
        Optuna objective function for hyperparameter tuning.

        Args:
            trial: Optuna trial object
            X_train, y_train: Training data
            X_val, y_val: Validation data

        Returns:
            Validation F1-score
        """
        # Hyperparameter space
        params = {
            "objective": "binary:logistic",
            "eval_metric": "logloss",
            "tree_method": "hist",  # Fast histogram-based algorithm
            "random_state": self.random_state,

            # Optuna suggestions
            "max_depth": trial.suggest_int("max_depth", 3, 10),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
            "n_estimators": trial.suggest_int("n_estimators", 50, 200, step=50),
            "subsample": trial.suggest_float("subsample", 0.6, 1.0),
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.6, 1.0),
            "min_child_weight": trial.suggest_int("min_child_weight", 1, 7),
            "gamma": trial.suggest_float("gamma", 0.0, 0.5),
            "reg_alpha": trial.suggest_float("reg_alpha", 0.0, 1.0),
            "reg_lambda": trial.suggest_float("reg_lambda", 0.0, 1.0),
            "scale_pos_weight": (y_train == 0).sum() / (y_train == 1).sum()  # Handle imbalance
        }

        # Create DMatrix
        dtrain = xgb.DMatrix(X_train, label=y_train, feature_names=self.feature_names)
        dval = xgb.DMatrix(X_val, label=y_val, feature_names=self.feature_names)

        # Train with early stopping
        model = xgb.train(
            params,
            dtrain,
            num_boost_round=params["n_estimators"],
            evals=[(dval, "validation")],
            early_stopping_rounds=10,
            verbose_eval=False
        )

        # Predict
        y_val_pred_proba = model.predict(dval)
        y_val_pred = (y_val_pred_proba > 0.5).astype(int)

        # Calculate F1-score
        f1 = f1_score(y_val, y_val_pred)

        return f1

    def train_with_optuna(self, X_train: np.ndarray, y_train: np.ndarray, X_val: np.ndarray, y_val: np.ndarray):
        """
        Train XGBoost with Optuna hyperparameter optimization.

        Args:
            X_train, y_train: Training data
            X_val, y_val: Validation data
        """
        logger.info("=" * 80)
        logger.info("STEP 2: XGBOOST TRAINING WITH OPTUNA")
        logger.info("=" * 80)
        logger.info(f"Optuna trials: {self.n_trials}")
        logger.info("Optimizing for F1-score...")

        self._log_memory()

        # Create Optuna study
        study = optuna.create_study(
            direction="maximize",
            sampler=optuna.samplers.TPESampler(seed=self.random_state),
            pruner=optuna.pruners.MedianPruner()
        )

        # Optimize
        study.optimize(
            lambda trial: self.objective(trial, X_train, y_train, X_val, y_val),
            n_trials=self.n_trials,
            show_progress_bar=True
        )

        # Best parameters
        self.best_params = study.best_params
        self.best_params.update({
            "objective": "binary:logistic",
            "eval_metric": "logloss",
            "tree_method": "hist",
            "random_state": self.random_state,
            "scale_pos_weight": (y_train == 0).sum() / (y_train == 1).sum()
        })

        logger.info("=" * 80)
        logger.info("OPTUNA OPTIMIZATION COMPLETE")
        logger.info("=" * 80)
        logger.info(f"Best F1-score: {study.best_value:.4f}")
        logger.info(f"Best parameters: {self.best_params}")

        # Train final model with best parameters
        dtrain = xgb.DMatrix(X_train, label=y_train, feature_names=self.feature_names)
        dval = xgb.DMatrix(X_val, label=y_val, feature_names=self.feature_names)

        self.best_model = xgb.train(
            self.best_params,
            dtrain,
            num_boost_round=self.best_params["n_estimators"],
            evals=[(dtrain, "train"), (dval, "validation")],
            early_stopping_rounds=10,
            verbose_eval=10
        )

        self._log_memory()
        gc.collect()

    def evaluate(self, X_test: np.ndarray, y_test: np.ndarray) -> Dict[str, float]:
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

        dtest = xgb.DMatrix(X_test, label=y_test, feature_names=self.feature_names)

        y_test_pred_proba = self.best_model.predict(dtest)
        y_test_pred = (y_test_pred_proba > 0.5).astype(int)

        # Confusion matrix components (handle edge cases with labels parameter)
        cm = confusion_matrix(y_test, y_test_pred, labels=[0, 1])

        # Handle case where confusion matrix might not be 2x2
        if cm.shape == (2, 2):
            tn, fp, fn, tp = cm.ravel()
        else:
            # Edge case: only one class present
            tn = fp = fn = tp = 0
            if len(cm) > 0:
                if y_test.sum() == 0:  # All negative
                    tn = cm[0, 0]
                else:  # All positive
                    tp = cm[0, 0] if len(cm) == 1 else cm[1, 1]

        # Precision-Recall AUC (handle edge case)
        try:
            precision, recall, _ = precision_recall_curve(y_test, y_test_pred_proba)
            pr_auc = auc(recall, precision)
        except:
            pr_auc = 0.0

        # Comprehensive metrics for thesis research
        metrics = {
            # Basic metrics
            "accuracy": float(accuracy_score(y_test, y_test_pred)),
            "balanced_accuracy": float(balanced_accuracy_score(y_test, y_test_pred)),
            "precision": float(precision_score(y_test, y_test_pred, zero_division=0)),
            "recall": float(recall_score(y_test, y_test_pred, zero_division=0)),
            "f1_score": float(f1_score(y_test, y_test_pred, zero_division=0)),

            # ROC and PR curves
            "roc_auc": float(roc_auc_score(y_test, y_test_pred_proba)),
            "auc_pr": float(pr_auc),

            # Confusion matrix components
            "true_positives": int(tp),
            "true_negatives": int(tn),
            "false_positives": int(fp),
            "false_negatives": int(fn),

            # Rates
            "specificity": float(tn / (tn + fp)) if (tn + fp) > 0 else 0.0,
            "sensitivity": float(tp / (tp + fn)) if (tp + fn) > 0 else 0.0,
            "false_positive_rate": float(fp / (fp + tn)) if (fp + tn) > 0 else 0.0,
            "false_negative_rate": float(fn / (fn + tp)) if (fn + tp) > 0 else 0.0,
            "negative_predictive_value": float(tn / (tn + fn)) if (tn + fn) > 0 else 0.0,

            # Advanced metrics
            "matthews_corrcoef": float(matthews_corrcoef(y_test, y_test_pred)),
            "cohen_kappa": float(cohen_kappa_score(y_test, y_test_pred)),
            "g_mean": float(np.sqrt((tp / (tp + fn)) * (tn / (tn + fp)))) if (tp + fn) > 0 and (tn + fp) > 0 else 0.0,
        }

        logger.info("="*80)
        logger.info("COMPREHENSIVE TEST SET METRICS")
        logger.info("="*80)
        logger.info(f"Accuracy: {metrics['accuracy']:.4f} | Balanced: {metrics['balanced_accuracy']:.4f}")
        logger.info(f"Precision: {metrics['precision']:.4f} | Recall: {metrics['recall']:.4f} | F1: {metrics['f1_score']:.4f}")
        logger.info(f"Specificity: {metrics['specificity']:.4f} | Sensitivity: {metrics['sensitivity']:.4f}")
        logger.info(f"AUC-ROC: {metrics['roc_auc']:.4f} | AUC-PR: {metrics['auc_pr']:.4f}")
        logger.info(f"MCC: {metrics['matthews_corrcoef']:.4f} | Kappa: {metrics['cohen_kappa']:.4f} | G-Mean: {metrics['g_mean']:.4f}")
        logger.info(f"\nConfusion Matrix: TP={tp:,} TN={tn:,} FP={fp:,} FN={fn:,}")
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

        # Save XGBoost model (native format)
        model_path = MODELS_DIR / f"xgboost_{version}.json"
        self.best_model.save_model(str(model_path))
        logger.info(f"Model saved: {model_path}")

        # Save preprocessor
        import pickle
        preprocessor_path = MODELS_DIR / f"xgb_preprocessor_{version}.pkl"
        with open(preprocessor_path, "wb") as f:
            pickle.dump({"scaler": self.scaler, "encoder": self.encoder}, f)
        logger.info(f"Preprocessor saved: {preprocessor_path}")

        # Save feature names
        features_path = MODELS_DIR / f"xgb_feature_names_{version}.json"
        with open(features_path, "w") as f:
            json.dump(self.feature_names, f, indent=2)
        logger.info(f"Feature names saved: {features_path}")

        # Save feature importance
        importance = self.best_model.get_score(importance_type="weight")
        importance_sorted = sorted(importance.items(), key=lambda x: x[1], reverse=True)

        importance_path = MODELS_DIR / f"xgb_feature_importance_{version}.json"
        with open(importance_path, "w") as f:
            json.dump(dict(importance_sorted), f, indent=2)
        logger.info(f"Feature importance saved: {importance_path}")

        # Save metadata
        metadata = {
            "model_name": "xgboost",
            "model_version": version,
            "training_date": datetime.now().isoformat(),
            "dataset_version": "stratified_split",
            "max_samples": self.max_samples,
            "random_state": self.random_state,
            "optuna_trials": self.n_trials,
            "best_parameters": self.best_params,
            "metrics": metrics,
            "feature_count": len(self.feature_names),
            "top_5_features": importance_sorted[:5]
        }

        metadata_path = MODELS_DIR / f"xgboost_{version}_metadata.json"
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)
        logger.info(f"Metadata saved: {metadata_path}")

        logger.info("=" * 80)
        logger.info("TRAINING COMPLETE!")
        logger.info("=" * 80)


def main():
    """Main training pipeline."""
    parser = argparse.ArgumentParser(description="Train XGBoost fraud detection model")
    parser.add_argument("--max-samples", type=int, default=50000,
                        help="Maximum training samples (default: 50000 for M4 Pro)")
    parser.add_argument("--n-trials", type=int, default=20,
                        help="Number of Optuna trials (default: 20)")
    parser.add_argument("--memory-limit", type=float, default=16.0,
                        help="Memory limit in GB (default: 16.0)")
    parser.add_argument("--run-name", type=str, default=None,
                        help="MLflow run name (default: auto-generated)")
    args = parser.parse_args()

    logger.info("=" * 80)
    logger.info("XGBOOST MODEL TRAINING WITH OPTUNA (MEMORY OPTIMIZED)")
    logger.info("=" * 80)
    logger.info(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Max samples: {args.max_samples:,}")
    logger.info(f"Optuna trials: {args.n_trials}")
    logger.info(f"Memory limit: {args.memory_limit}GB")
    logger.info("=" * 80)

    # Setup MLflow
    mlflow_uri = os.getenv("MLFLOW_TRACKING_URI", "file://./mlruns")
    mlflow_experiment = os.getenv("MLFLOW_EXPERIMENT_NAME", "finsight-fraud-detection")
    mlflow.set_tracking_uri(mlflow_uri)
    mlflow.set_experiment(mlflow_experiment)

    logger.info(f"MLflow Tracking URI: {mlflow_uri}")
    logger.info(f"MLflow Experiment: {mlflow_experiment}")
    logger.info("=" * 80)

    # Initialize trainer
    trainer = XGBoostTrainer(
        project_root=PROJECT_ROOT,
        max_samples=args.max_samples,
        memory_limit_gb=args.memory_limit,
        n_trials=args.n_trials
    )

    # Start MLflow run
    run_name = args.run_name or f"xgboost_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    with mlflow.start_run(run_name=run_name) as run:
        # Log training configuration
        mlflow.log_params({
            "model_type": "xgboost",
            "max_samples": args.max_samples,
            "memory_limit_gb": args.memory_limit,
            "n_optuna_trials": args.n_trials,
            "random_state": trainer.random_state,
        })

        # Load data
        train_df, val_df, test_df = trainer.load_data_sample()

        # Log dataset sizes
        mlflow.log_params({
            "train_samples": len(train_df),
            "val_samples": len(val_df),
            "test_samples": len(test_df),
            "train_fraud_rate": float(train_df['isFraud'].mean()),
            "val_fraud_rate": float(val_df['isFraud'].mean()),
            "test_fraud_rate": float(test_df['isFraud'].mean()),
        })

        # Feature engineering
        X_train, y_train = trainer.engineer_features(train_df, fit=True)
        X_val, y_val = trainer.engineer_features(val_df, fit=False)
        X_test, y_test = trainer.engineer_features(test_df, fit=False)

        # Log feature count
        mlflow.log_param("n_features", len(trainer.feature_names))

        # Scale features
        X_train, X_val, X_test = trainer.scale_features(X_train, X_val, X_test)

        # Train with Optuna
        trainer.train_with_optuna(X_train, y_train, X_val, y_val)

        # Log best hyperparameters
        for param, value in trainer.best_params.items():
            mlflow.log_param(f"best_{param}", value)

        # Evaluate
        metrics = trainer.evaluate(X_test, y_test)

        # Log all metrics
        mlflow.log_metrics(metrics)

        # Save model artifacts
        version = f"v1_{datetime.now().strftime('%Y%m%d')}"
        trainer.save_model(metrics, version=version)

        # Log model to MLflow
        model_path = MODELS_DIR / f"xgboost_{version}.json"
        mlflow.xgboost.log_model(
            trainer.best_model,
            "model",
            registered_model_name="xgboost-fraud-detector"
        )

        # Log artifacts
        mlflow.log_artifacts(str(MODELS_DIR), artifact_path="models")

        # Set tags for easy filtering
        mlflow.set_tags({
            "model_family": "gradient_boosting",
            "algorithm": "xgboost",
            "stage": "development",
            "optimization": "optuna",
            "hardware": "M4_Pro",
            "dataset_version": "stratified_split",
        })

        logger.info(f"\nMLflow Run ID: {run.info.run_id}")
        logger.info(f"Final F1-Score: {metrics['f1_score']:.4f}")
        logger.info(f"\nView experiments at: {mlflow_uri}")
        if "dagshub" in mlflow_uri:
            logger.info("DagsHub UI: https://dagshub.com/bibekgupta3333/finsight-ai/experiments")


if __name__ == "__main__":
    main()
