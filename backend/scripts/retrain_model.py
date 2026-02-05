"""
Automated Model Retraining Script.

Triggers retraining when:
- Drift detected (PSI > 0.2)
- Performance degraded (F1 < threshold)
- Sufficient new labeled data (>min_samples)

Optimized for M4 Pro: Memory-efficient, incremental processing.
"""

import argparse
import joblib
import json
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, Tuple

import lightgbm as lgb
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    f1_score, precision_score, recall_score, roc_auc_score, classification_report
)

# Add backend to path
BACKEND_DIR = Path(__file__).parent.parent
sys.path.append(str(BACKEND_DIR))

from app.utils.feature_engineering import FeatureEngineer

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Paths
MODELS_DIR = BACKEND_DIR / "models"
DATA_DIR = BACKEND_DIR.parent / "data"
REPORTS_DIR = BACKEND_DIR / "reports" / "retraining"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


class ModelRetrainingPipeline:
    """
    Automated model retraining pipeline with drift detection and validation.
    """

    def __init__(
        self,
        model_name: str,
        current_version: str = "v1",
        min_f1_threshold: float = 0.85,
        min_samples_threshold: int = 10000,
        max_psi_threshold: float = 0.2
    ):
        """
        Initialize retraining pipeline.

        Args:
            model_name: Model to retrain ("lightgbm", "xgboost", "random_forest")
            current_version: Current model version
            min_f1_threshold: Minimum F1 score to keep model (default: 0.85)
            min_samples_threshold: Minimum new samples needed (default: 10000)
            max_psi_threshold: Maximum PSI for drift (default: 0.2)
        """
        self.model_name = model_name
        self.current_version = current_version
        self.min_f1_threshold = min_f1_threshold
        self.min_samples_threshold = min_samples_threshold
        self.max_psi_threshold = max_psi_threshold

        self.new_version = self._generate_new_version()

        logger.info(f"Initialized retraining pipeline for {model_name}")
        logger.info(f"Current version: {current_version} -> New version: {self.new_version}")

    def _generate_new_version(self) -> str:
        """Generate new version number."""
        # Extract version number and increment
        if self.current_version.startswith("v"):
            version_num = int(self.current_version[1:])
            return f"v{version_num + 1}"
        else:
            return "v2"

    def load_current_model(self) -> Optional[object]:
        """
        Load current production model.

        Returns:
            Current model or None if not found
        """
        try:
            if self.model_name == "lightgbm":
                model_path = MODELS_DIR / f"lightgbm_{self.current_version}.txt"
                if model_path.exists():
                    model = lgb.Booster(model_file=str(model_path))
                    logger.info(f"✓ Loaded current LightGBM model from {model_path}")
                    return model

            elif self.model_name == "xgboost":
                model_path = MODELS_DIR / f"xgboost_{self.current_version}.json"
                if model_path.exists():
                    model = xgb.Booster()
                    model.load_model(str(model_path))
                    logger.info(f"✓ Loaded current XGBoost model from {model_path}")
                    return model

            else:  # random_forest
                model_path = MODELS_DIR / f"random_forest_{self.current_version}.pkl"
                if model_path.exists():
                    model = joblib.load(model_path)
                    logger.info(f"✓ Loaded current Random Forest model from {model_path}")
                    return model

            logger.warning(f"Current model not found for {self.model_name} {self.current_version}")
            return None

        except Exception as e:
            logger.error(f"Error loading current model: {e}")
            return None

    def check_retraining_triggers(
        self,
        new_data: pd.DataFrame,
        current_performance: Optional[Dict] = None,
        drift_detected: bool = False
    ) -> Tuple[bool, str]:
        """
        Check if retraining should be triggered.

        Args:
            new_data: New training data
            current_performance: Current model performance metrics
            drift_detected: Whether drift was detected

        Returns:
            Tuple of (should_retrain, reason)
        """
        reasons = []

        # Trigger 1: Drift detected
        if drift_detected:
            reasons.append("Data drift detected (PSI > 0.2)")

        # Trigger 2: Performance degradation
        if current_performance and current_performance.get("f1_score", 1.0) < self.min_f1_threshold:
            reasons.append(
                f"Performance degraded: F1={current_performance['f1_score']:.4f} < {self.min_f1_threshold}"
            )

        # Trigger 3: Sufficient new data
        if len(new_data) >= self.min_samples_threshold:
            reasons.append(f"Sufficient new data: {len(new_data)} samples")
        else:
            logger.info(
                f"Insufficient new data: {len(new_data)} < {self.min_samples_threshold} samples"
            )

        should_retrain = len(reasons) > 0
        reason = " | ".join(reasons) if reasons else "No triggers met"

        return should_retrain, reason

    def prepare_training_data(
        self,
        original_train: pd.DataFrame,
        new_data: pd.DataFrame,
        max_samples: int = 200000
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Prepare combined training data.

        Args:
            original_train: Original training data
            new_data: New data with labels
            max_samples: Maximum samples to use (M4 Pro memory limit)

        Returns:
            Tuple of (X_train, y_train)
        """
        logger.info(f"Preparing training data...")
        logger.info(f"Original train: {len(original_train)} samples")
        logger.info(f"New data: {len(new_data)} samples")

        # Combine datasets
        combined = pd.concat([original_train, new_data], ignore_index=True)

        # Remove duplicates
        combined = combined.drop_duplicates()
        logger.info(f"After removing duplicates: {len(combined)} samples")

        # Limit samples for M4 Pro
        if len(combined) > max_samples:
            logger.info(f"Sampling {max_samples} from {len(combined)} samples")
            # Stratified sampling to preserve fraud ratio
            fraud_samples = combined[combined['isFraud'] == 1]
            legit_samples = combined[combined['isFraud'] == 0]

            fraud_ratio = len(fraud_samples) / len(combined)
            fraud_count = int(max_samples * fraud_ratio)
            legit_count = max_samples - fraud_count

            fraud_samples = fraud_samples.sample(n=min(fraud_count, len(fraud_samples)), random_state=42)
            legit_samples = legit_samples.sample(n=legit_count, random_state=42)

            combined = pd.concat([fraud_samples, legit_samples], ignore_index=True).sample(frac=1, random_state=42)

        # Separate features and labels
        y_train = combined['isFraud'].values
        X_train = combined.drop(columns=['isFraud'])

        logger.info(f"Final training set: {len(X_train)} samples, fraud rate: {y_train.mean():.2%}")

        return X_train, y_train

    def train_new_model(
        self,
        X_train: pd.DataFrame,
        y_train: np.ndarray,
        X_val: pd.DataFrame,
        y_val: np.ndarray
    ) -> object:
        """
        Train new model version.

        Args:
            X_train: Training features
            y_train: Training labels
            X_val: Validation features
            y_val: Validation labels

        Returns:
            Trained model
        """
        logger.info(f"Training new {self.model_name} model...")

        # Feature engineering
        feature_engineer = FeatureEngineer()

        if self.model_name == "lightgbm":
            # LightGBM training
            X_train_lgbm = feature_engineer.prepare_features(
                X_train, categorical_features=['type'], for_lightgbm=True
            )
            X_val_lgbm = feature_engineer.prepare_features(
                X_val, categorical_features=['type'], for_lightgbm=True
            )

            train_data = lgb.Dataset(X_train_lgbm, label=y_train)
            val_data = lgb.Dataset(X_val_lgbm, label=y_val, reference=train_data)

            params = {
                'objective': 'binary',
                'metric': 'binary_logloss',
                'boosting_type': 'gbdt',
                'num_leaves': 31,
                'learning_rate': 0.05,
                'feature_fraction': 0.9,
                'bagging_fraction': 0.8,
                'bagging_freq': 5,
                'verbose': -1,
                'is_unbalance': True
            }

            model = lgb.train(
                params,
                train_data,
                num_boost_round=500,
                valid_sets=[val_data],
                callbacks=[lgb.early_stopping(stopping_rounds=50), lgb.log_evaluation(period=50)]
            )

            # Save model
            model_path = MODELS_DIR / f"lightgbm_{self.new_version}.txt"
            model.save_model(str(model_path))

        elif self.model_name == "xgboost":
            # XGBoost training
            X_train_xgb = feature_engineer.prepare_features(
                X_train, categorical_features=['type'], for_lightgbm=False
            )
            X_val_xgb = feature_engineer.prepare_features(
                X_val, categorical_features=['type'], for_lightgbm=False
            )

            dtrain = xgb.DMatrix(X_train_xgb, label=y_train)
            dval = xgb.DMatrix(X_val_xgb, label=y_val)

            params = {
                'objective': 'binary:logistic',
                'eval_metric': 'logloss',
                'max_depth': 6,
                'learning_rate': 0.1,
                'subsample': 0.8,
                'colsample_bytree': 0.8,
                'scale_pos_weight': len(y_train) / y_train.sum() - 1
            }

            evals = [(dtrain, 'train'), (dval, 'val')]
            model = xgb.train(
                params,
                dtrain,
                num_boost_round=500,
                evals=evals,
                early_stopping_rounds=50,
                verbose_eval=50
            )

            # Save model
            model_path = MODELS_DIR / f"xgboost_{self.new_version}.json"
            model.save_model(str(model_path))

        else:  # random_forest
            # Random Forest training
            X_train_rf = feature_engineer.prepare_features(
                X_train, categorical_features=['type'], for_lightgbm=False
            )
            X_val_rf = feature_engineer.prepare_features(
                X_val, categorical_features=['type'], for_lightgbm=False
            )

            model = RandomForestClassifier(
                n_estimators=200,
                max_depth=15,
                min_samples_split=10,
                min_samples_leaf=5,
                class_weight='balanced',
                random_state=42,
                n_jobs=-1,
                verbose=1
            )

            model.fit(X_train_rf, y_train)

            # Save model
            model_path = MODELS_DIR / f"random_forest_{self.new_version}.pkl"
            joblib.dump(model, model_path)

        # Save feature engineer
        fe_path = MODELS_DIR / f"feature_engineer_{self.new_version}.pkl"
        joblib.dump(feature_engineer, fe_path)

        logger.info(f"✓ Saved new model to {model_path}")

        return model

    def evaluate_model(
        self,
        model: object,
        X_test: pd.DataFrame,
        y_test: np.ndarray,
        model_version: str
    ) -> Dict:
        """
        Evaluate model performance.

        Args:
            model: Model to evaluate
            X_test: Test features
            y_test: Test labels
            model_version: Model version

        Returns:
            Dict with performance metrics
        """
        logger.info(f"Evaluating {self.model_name} {model_version}...")

        # Feature engineering
        fe_path = MODELS_DIR / f"feature_engineer_{model_version}.pkl"
        if fe_path.exists():
            feature_engineer = joblib.load(fe_path)
        else:
            feature_engineer = FeatureEngineer()

        # Prepare test data based on model type
        if self.model_name == "lightgbm":
            X_test_prep = feature_engineer.prepare_features(
                X_test, categorical_features=['type'], for_lightgbm=True
            )
            y_pred_proba = model.predict(X_test_prep)

        elif self.model_name == "xgboost":
            X_test_prep = feature_engineer.prepare_features(
                X_test, categorical_features=['type'], for_lightgbm=False
            )
            dtest = xgb.DMatrix(X_test_prep)
            y_pred_proba = model.predict(dtest)

        else:  # random_forest
            X_test_prep = feature_engineer.prepare_features(
                X_test, categorical_features=['type'], for_lightgbm=False
            )
            y_pred_proba = model.predict_proba(X_test_prep)[:, 1]

        # Binary predictions
        y_pred = (y_pred_proba >= 0.5).astype(int)

        # Calculate metrics
        f1 = f1_score(y_test, y_pred)
        precision = precision_score(y_test, y_pred)
        recall = recall_score(y_test, y_pred)
        auc = roc_auc_score(y_test, y_pred_proba)

        logger.info(f"\n{self.model_name} {model_version} Performance:")
        logger.info(f"  F1-Score:  {f1:.4f}")
        logger.info(f"  Precision: {precision:.4f}")
        logger.info(f"  Recall:    {recall:.4f}")
        logger.info(f"  ROC-AUC:   {auc:.4f}")

        return {
            "model_name": self.model_name,
            "version": model_version,
            "f1_score": float(f1),
            "precision": float(precision),
            "recall": float(recall),
            "roc_auc": float(auc),
            "test_samples": len(y_test),
            "fraud_rate": float(y_test.mean())
        }

    def compare_and_promote(
        self,
        new_performance: Dict,
        current_performance: Optional[Dict]
    ) -> Tuple[bool, str]:
        """
        Compare new model to current and decide whether to promote.

        Args:
            new_performance: New model performance
            current_performance: Current model performance (or None)

        Returns:
            Tuple of (should_promote, reason)
        """
        if current_performance is None:
            return True, "No current model found - promoting new model"

        new_f1 = new_performance["f1_score"]
        current_f1 = current_performance["f1_score"]

        # Promote if:
        # 1. New F1 >= current F1 (improved or same)
        # 2. New F1 >= threshold (meets minimum standard)

        if new_f1 < self.min_f1_threshold:
            return False, f"New model F1={new_f1:.4f} < threshold={self.min_f1_threshold}"

        if new_f1 >= current_f1:
            improvement = (new_f1 - current_f1) / current_f1 * 100
            return True, f"New model improved F1 by {improvement:.2f}% ({current_f1:.4f} -> {new_f1:.4f})"
        else:
            degradation = (current_f1 - new_f1) / current_f1 * 100
            return False, f"New model degraded F1 by {degradation:.2f}% ({current_f1:.4f} -> {new_f1:.4f})"

    def generate_report(
        self,
        should_retrain: bool,
        trigger_reason: str,
        new_performance: Optional[Dict],
        current_performance: Optional[Dict],
        promoted: bool,
        promotion_reason: str
    ) -> str:
        """
        Generate retraining report.

        Args:
            should_retrain: Whether retraining was triggered
            trigger_reason: Reason for triggering
            new_performance: New model performance
            current_performance: Current model performance
            promoted: Whether new model was promoted
            promotion_reason: Reason for promotion decision

        Returns:
            str: Report file path
        """
        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "model_name": self.model_name,
            "current_version": self.current_version,
            "new_version": self.new_version,
            "retraining_triggered": should_retrain,
            "trigger_reason": trigger_reason,
            "current_performance": current_performance,
            "new_performance": new_performance,
            "promoted": promoted,
            "promotion_reason": promotion_reason,
            "thresholds": {
                "min_f1": self.min_f1_threshold,
                "min_samples": self.min_samples_threshold,
                "max_psi": self.max_psi_threshold
            }
        }

        # Save report
        report_path = REPORTS_DIR / f"{self.model_name}_retrain_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)

        logger.info(f"✓ Saved retraining report to {report_path}")

        return str(report_path)


def main():
    """Main retraining function."""
    parser = argparse.ArgumentParser(description="Automated model retraining")
    parser.add_argument(
        "--model",
        type=str,
        required=True,
        choices=["lightgbm", "xgboost", "random_forest"],
        help="Model to retrain"
    )
    parser.add_argument(
        "--current_version",
        type=str,
        default="v1",
        help="Current model version"
    )
    parser.add_argument(
        "--original_train",
        type=str,
        default=str(DATA_DIR / "splits" / "temporal" / "train.csv"),
        help="Original training data"
    )
    parser.add_argument(
        "--new_data",
        type=str,
        default=str(DATA_DIR / "splits" / "temporal" / "val.csv"),
        help="New data with labels (simulating production feedback)"
    )
    parser.add_argument(
        "--test_data",
        type=str,
        default=str(DATA_DIR / "splits" / "temporal" / "test.csv"),
        help="Test data for evaluation"
    )
    parser.add_argument(
        "--drift_detected",
        action="store_true",
        help="Force retraining due to drift"
    )
    parser.add_argument(
        "--min_f1",
        type=float,
        default=0.85,
        help="Minimum F1 score threshold"
    )
    parser.add_argument(
        "--max_samples",
        type=int,
        default=200000,
        help="Maximum training samples (M4 Pro limit)"
    )

    args = parser.parse_args()

    # Initialize pipeline
    pipeline = ModelRetrainingPipeline(
        model_name=args.model,
        current_version=args.current_version,
        min_f1_threshold=args.min_f1
    )

    # Load current model
    current_model = pipeline.load_current_model()

    # Load data
    logger.info("Loading datasets...")
    original_train = pd.read_csv(args.original_train)
    new_data = pd.read_csv(args.new_data).sample(n=min(20000, len(pd.read_csv(args.new_data))), random_state=42)
    test_data = pd.read_csv(args.test_data).sample(n=min(50000, len(pd.read_csv(args.test_data))), random_state=42)

    # Evaluate current model (if exists)
    current_performance = None
    if current_model:
        y_test = test_data['isFraud'].values
        X_test = test_data.drop(columns=['isFraud'])
        current_performance = pipeline.evaluate_model(
            current_model, X_test, y_test, args.current_version
        )

    # Check retraining triggers
    should_retrain, trigger_reason = pipeline.check_retraining_triggers(
        new_data,
        current_performance,
        drift_detected=args.drift_detected
    )

    logger.info(f"\nRetraining Decision: {should_retrain}")
    logger.info(f"Reason: {trigger_reason}")

    new_performance = None
    promoted = False
    promotion_reason = "Not retrained"

    if should_retrain:
        # Prepare training data
        X_train, y_train = pipeline.prepare_training_data(
            original_train, new_data, max_samples=args.max_samples
        )

        # Use part of new_data as validation
        val_split = int(len(new_data) * 0.2)
        X_val = new_data.drop(columns=['isFraud']).iloc[:val_split]
        y_val = new_data['isFraud'].values[:val_split]

        # Train new model
        new_model = pipeline.train_new_model(X_train, y_train, X_val, y_val)

        # Evaluate new model
        y_test = test_data['isFraud'].values
        X_test = test_data.drop(columns=['isFraud'])
        new_performance = pipeline.evaluate_model(
            new_model, X_test, y_test, pipeline.new_version
        )

        # Compare and decide promotion
        promoted, promotion_reason = pipeline.compare_and_promote(
            new_performance, current_performance
        )

        logger.info(f"\nPromotion Decision: {promoted}")
        logger.info(f"Reason: {promotion_reason}")

        if not promoted:
            logger.warning("⚠️  New model NOT promoted - reverting to current version")

    # Generate report
    report_path = pipeline.generate_report(
        should_retrain, trigger_reason,
        new_performance, current_performance,
        promoted, promotion_reason
    )

    logger.info(f"\n{'='*60}")
    logger.info(f"Retraining Complete")
    logger.info(f"Report: {report_path}")
    logger.info(f"{'='*60}")


if __name__ == "__main__":
    main()
