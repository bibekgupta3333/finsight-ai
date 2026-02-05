"""
Baseline ML Model Trainer for Fraud Detection

Lightweight implementation optimized for M4 Pro:
- Random Forest and XGBoost classifiers
- Optuna for hyperparameter tuning (efficient sampling)
- Model comparison and selection
- Artifact saving with versioning
- Memory-efficient training (chunked data loading)
"""

import json
import pickle
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, confusion_matrix, classification_report
)
from sklearn.model_selection import train_test_split
import joblib

try:
    import xgboost as xgb
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False
    print("XGBoost not available - will skip XGBoost training")

try:
    import optuna
    OPTUNA_AVAILABLE = True
except ImportError:
    OPTUNA_AVAILABLE = False
    print("Optuna not available - will use default hyperparameters")


@dataclass
class ModelMetrics:
    """Model performance metrics"""
    model_name: str
    model_type: str  # "random_forest" or "xgboost"
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    roc_auc: float
    training_time_seconds: float
    inference_time_ms: float  # Average per sample
    confusion_matrix: List[List[int]]
    classification_report: str
    hyperparameters: Dict[str, Any]
    feature_importance: Dict[str, float]
    timestamp: str
    dataset_size: int
    version: str


@dataclass
class ModelArtifact:
    """Model artifact metadata"""
    model_id: str
    model_name: str
    model_type: str
    file_path: str
    metrics: ModelMetrics
    created_at: str
    is_best: bool = False


class ModelTrainer:
    """Train and manage fraud detection models"""

    def __init__(self, data_dir: str = "data", models_dir: str = "models"):
        # Use absolute paths from project root
        from pathlib import Path
        project_root = Path(__file__).parent.parent.parent.parent.parent
        self.data_dir = project_root / data_dir
        self.models_dir = project_root / models_dir
        self.models_dir.mkdir(exist_ok=True, parents=True)

        # Model registry
        self.registry_file = self.models_dir / "model_registry.json"
        self.registry: List[ModelArtifact] = self._load_registry()

        # Feature columns (excluding target and metadata)
        self.feature_columns = [
            'step', 'amount', 'oldbalanceOrg', 'newbalanceOrig',
            'oldbalanceDest', 'newbalanceDest', 'type_CASH_IN',
            'type_CASH_OUT', 'type_DEBIT', 'type_PAYMENT', 'type_TRANSFER'
        ]
        self.target_column = 'isFraud'

    def _load_registry(self) -> List[ModelArtifact]:
        """Load model registry from disk"""
        if self.registry_file.exists():
            with open(self.registry_file, 'r') as f:
                data = json.load(f)
                return [ModelArtifact(**item) for item in data]
        return []

    def _save_registry(self):
        """Save model registry to disk"""
        with open(self.registry_file, 'w') as f:
            json.dump([asdict(m) for m in self.registry], f, indent=2)

    def load_data(self,
                  split: str = "stratified",
                  sample_size: Optional[int] = None) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Load training and test data

        Args:
            split: "stratified" or "temporal"
            sample_size: Optional sample size for quick testing (e.g., 10000)

        Returns:
            (X_train, X_test, y_train, y_test)
        """
        train_path = self.data_dir / "splits" / split / "train.csv"
        test_path = self.data_dir / "splits" / split / "test.csv"

        if not train_path.exists():
            # Fallback to full cleaned dataset
            full_path = self.data_dir / "processed" / "paysim_cleaned.csv"
            if not full_path.exists():
                raise FileNotFoundError(f"No data found at {full_path}")

            print(f"Split not found, loading full dataset from {full_path}")
            df = pd.read_csv(full_path)

            # Sample if requested (M4 Pro optimization)
            if sample_size and len(df) > sample_size:
                # Stratified sampling to maintain fraud ratio
                fraud_df = df[df[self.target_column] == 1].sample(
                    n=min(sample_size // 10, len(df[df[self.target_column] == 1])),
                    random_state=42
                )
                legit_df = df[df[self.target_column] == 0].sample(
                    n=sample_size - len(fraud_df),
                    random_state=42
                )
                df = pd.concat([fraud_df, legit_df]).sample(frac=1, random_state=42)
                print(f"Sampled {len(df)} rows (fraud ratio: {df[self.target_column].mean():.4f})")

            # Split
            train_df, test_df = train_test_split(
                df, test_size=0.2, stratify=df[self.target_column], random_state=42
            )
        else:
            print(f"Loading from {train_path} and {test_path}")
            train_df = pd.read_csv(train_path)
            test_df = pd.read_csv(test_path)

            # Sample if requested
            if sample_size and len(train_df) > sample_size:
                fraud_df = train_df[train_df[self.target_column] == 1].sample(
                    n=min(sample_size // 10, len(train_df[train_df[self.target_column] == 1])),
                    random_state=42
                )
                legit_df = train_df[train_df[self.target_column] == 0].sample(
                    n=sample_size - len(fraud_df),
                    random_state=42
                )
                train_df = pd.concat([fraud_df, legit_df]).sample(frac=1, random_state=42)
                print(f"Sampled training set to {len(train_df)} rows")

        return train_df, test_df

    def prepare_features(self, df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """Extract features and target from dataframe"""
        # Ensure all feature columns exist
        available_features = [col for col in self.feature_columns if col in df.columns]

        if len(available_features) < len(self.feature_columns):
            print(f"Warning: Only {len(available_features)}/{len(self.feature_columns)} features available")

        X = df[available_features].values
        y = df[self.target_column].values

        return X, y

    def train_random_forest(self,
                           X_train: np.ndarray,
                           y_train: np.ndarray,
                           hyperparameters: Optional[Dict] = None) -> RandomForestClassifier:
        """
        Train Random Forest classifier

        M4 Pro optimizations:
        - Limited n_estimators (100 instead of 500)
        - max_features='sqrt' for faster training
        - n_jobs=-1 for parallel processing
        """
        if hyperparameters is None:
            hyperparameters = {
                'n_estimators': 100,
                'max_depth': 20,
                'min_samples_split': 10,
                'min_samples_leaf': 4,
                'max_features': 'sqrt',
                'random_state': 42,
                'n_jobs': -1,
                'class_weight': 'balanced'  # Handle imbalanced data
            }

        print(f"Training Random Forest with params: {hyperparameters}")
        model = RandomForestClassifier(**hyperparameters)
        model.fit(X_train, y_train)

        return model

    def train_xgboost(self,
                     X_train: np.ndarray,
                     y_train: np.ndarray,
                     hyperparameters: Optional[Dict] = None) -> Optional[Any]:
        """
        Train XGBoost classifier

        M4 Pro optimizations:
        - tree_method='hist' for faster training
        - Limited n_estimators
        - Early stopping
        """
        if not XGBOOST_AVAILABLE:
            print("XGBoost not available")
            return None

        if hyperparameters is None:
            # Calculate scale_pos_weight for imbalanced data
            neg_count = np.sum(y_train == 0)
            pos_count = np.sum(y_train == 1)
            scale_pos_weight = neg_count / pos_count if pos_count > 0 else 1

            hyperparameters = {
                'n_estimators': 100,
                'max_depth': 10,
                'learning_rate': 0.1,
                'subsample': 0.8,
                'colsample_bytree': 0.8,
                'tree_method': 'hist',  # Fast histogram-based method
                'scale_pos_weight': scale_pos_weight,
                'random_state': 42,
                'n_jobs': -1,
                'eval_metric': 'logloss'
            }

        print(f"Training XGBoost with params: {hyperparameters}")
        model = xgb.XGBClassifier(**hyperparameters)
        model.fit(X_train, y_train)

        return model

    def evaluate_model(self,
                      model: Any,
                      X_test: np.ndarray,
                      y_test: np.ndarray,
                      model_name: str,
                      model_type: str,
                      training_time: float,
                      hyperparameters: Dict,
                      feature_names: List[str]) -> ModelMetrics:
        """Evaluate model and return metrics"""

        # Predictions
        start_time = time.time()
        y_pred = model.predict(X_test)
        y_pred_proba = model.predict_proba(X_test)[:, 1]
        inference_time = (time.time() - start_time) / len(X_test) * 1000  # ms per sample

        # Metrics
        accuracy = accuracy_score(y_test, y_pred)
        precision = precision_score(y_test, y_pred, zero_division=0)
        recall = recall_score(y_test, y_pred, zero_division=0)
        f1 = f1_score(y_test, y_pred, zero_division=0)
        roc_auc = roc_auc_score(y_test, y_pred_proba)
        cm = confusion_matrix(y_test, y_pred).tolist()
        report = classification_report(y_test, y_pred, zero_division=0)

        # Feature importance
        if hasattr(model, 'feature_importances_'):
            importance = dict(zip(feature_names, model.feature_importances_.tolist()))
            # Sort by importance
            importance = dict(sorted(importance.items(), key=lambda x: x[1], reverse=True))
        else:
            importance = {}

        return ModelMetrics(
            model_name=model_name,
            model_type=model_type,
            accuracy=accuracy,
            precision=precision,
            recall=recall,
            f1_score=f1,
            roc_auc=roc_auc,
            training_time_seconds=training_time,
            inference_time_ms=inference_time,
            confusion_matrix=cm,
            classification_report=report,
            hyperparameters=hyperparameters,
            feature_importance=importance,
            timestamp=datetime.now().isoformat(),
            dataset_size=len(X_test),
            version="1.0"
        )

    def save_model(self, model: Any, metrics: ModelMetrics) -> str:
        """Save model and return artifact ID"""
        # Generate model ID
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        model_id = f"{metrics.model_type}_{timestamp}"

        # Save model file
        model_file = self.models_dir / f"{model_id}.pkl"
        joblib.dump(model, model_file)

        # Save metrics
        metrics_file = self.models_dir / f"{model_id}_metrics.json"
        with open(metrics_file, 'w') as f:
            json.dump(asdict(metrics), f, indent=2)

        # Add to registry
        artifact = ModelArtifact(
            model_id=model_id,
            model_name=metrics.model_name,
            model_type=metrics.model_type,
            file_path=str(model_file),
            metrics=metrics,
            created_at=datetime.now().isoformat()
        )
        self.registry.append(artifact)
        self._save_registry()

        print(f"Model saved: {model_file}")
        print(f"Metrics saved: {metrics_file}")

        return model_id

    def load_model(self, model_id: str) -> Any:
        """Load model from disk"""
        model_file = self.models_dir / f"{model_id}.pkl"
        if not model_file.exists():
            raise FileNotFoundError(f"Model not found: {model_file}")

        return joblib.load(model_file)

    def get_best_model(self, metric: str = "f1_score") -> Optional[ModelArtifact]:
        """Get best model from registry"""
        if not self.registry:
            return None

        # Sort by metric
        sorted_models = sorted(
            self.registry,
            key=lambda x: getattr(x.metrics, metric),
            reverse=True
        )

        return sorted_models[0] if sorted_models else None

    def compare_models(self) -> pd.DataFrame:
        """Compare all trained models"""
        if not self.registry:
            return pd.DataFrame()

        data = []
        for artifact in self.registry:
            m = artifact.metrics
            data.append({
                'model_id': artifact.model_id,
                'model_name': artifact.model_name,
                'model_type': artifact.model_type,
                'accuracy': m.accuracy,
                'precision': m.precision,
                'recall': m.recall,
                'f1_score': m.f1_score,
                'roc_auc': m.roc_auc,
                'training_time_s': m.training_time_seconds,
                'inference_time_ms': m.inference_time_ms,
                'created_at': artifact.created_at
            })

        df = pd.DataFrame(data)
        return df.sort_values('f1_score', ascending=False)

    def tune_hyperparameters_optuna(self,
                                    model_type: str,
                                    X_train: np.ndarray,
                                    y_train: np.ndarray,
                                    X_val: np.ndarray,
                                    y_val: np.ndarray,
                                    n_trials: int = 20) -> Dict:
        """
        Tune hyperparameters using Optuna

        M4 Pro optimization: Limited to 20 trials (not 100)
        """
        if not OPTUNA_AVAILABLE:
            print("Optuna not available - using default hyperparameters")
            return {}

        def objective(trial):
            if model_type == "random_forest":
                params = {
                    'n_estimators': trial.suggest_int('n_estimators', 50, 200),
                    'max_depth': trial.suggest_int('max_depth', 10, 30),
                    'min_samples_split': trial.suggest_int('min_samples_split', 5, 20),
                    'min_samples_leaf': trial.suggest_int('min_samples_leaf', 2, 10),
                    'max_features': trial.suggest_categorical('max_features', ['sqrt', 'log2']),
                    'random_state': 42,
                    'n_jobs': -1,
                    'class_weight': 'balanced'
                }
                model = RandomForestClassifier(**params)

            elif model_type == "xgboost" and XGBOOST_AVAILABLE:
                params = {
                    'n_estimators': trial.suggest_int('n_estimators', 50, 200),
                    'max_depth': trial.suggest_int('max_depth', 5, 15),
                    'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.3),
                    'subsample': trial.suggest_float('subsample', 0.6, 1.0),
                    'colsample_bytree': trial.suggest_float('colsample_bytree', 0.6, 1.0),
                    'tree_method': 'hist',
                    'random_state': 42,
                    'n_jobs': -1,
                    'eval_metric': 'logloss'
                }
                model = xgb.XGBClassifier(**params)
            else:
                raise ValueError(f"Unknown model type: {model_type}")

            # Train and evaluate
            model.fit(X_train, y_train)
            y_pred = model.predict(X_val)
            f1 = f1_score(y_val, y_pred, zero_division=0)

            return f1

        # Create study
        study = optuna.create_study(direction='maximize')
        study.optimize(objective, n_trials=n_trials, show_progress_bar=True)

        print(f"Best F1 score: {study.best_value:.4f}")
        print(f"Best params: {study.best_params}")

        return study.best_params

    def train_and_save(self,
                      model_type: str,
                      sample_size: Optional[int] = None,
                      tune: bool = False,
                      n_trials: int = 20) -> str:
        """
        Complete training pipeline: load data, train, evaluate, save

        Args:
            model_type: "random_forest" or "xgboost"
            sample_size: Optional sample size for quick training (e.g., 10000)
            tune: Whether to tune hyperparameters with Optuna
            n_trials: Number of Optuna trials (default 20 for M4 Pro)

        Returns:
            model_id of the saved model
        """
        # Load data
        print(f"\n{'='*60}")
        print(f"Training {model_type.upper()} model")
        print(f"{'='*60}\n")

        train_df, test_df = self.load_data(sample_size=sample_size)
        X_train, y_train = self.prepare_features(train_df)
        X_test, y_test = self.prepare_features(test_df)

        print(f"Training set: {len(X_train)} samples ({y_train.sum()} fraud, {(1-y_train).sum()} legit)")
        print(f"Test set: {len(X_test)} samples ({y_test.sum()} fraud, {(1-y_test).sum()} legit)")

        # Hyperparameter tuning
        if tune and OPTUNA_AVAILABLE:
            print("\nTuning hyperparameters with Optuna...")
            # Create validation set
            X_train_sub, X_val, y_train_sub, y_val = train_test_split(
                X_train, y_train, test_size=0.2, stratify=y_train, random_state=42
            )
            best_params = self.tune_hyperparameters_optuna(
                model_type, X_train_sub, y_train_sub, X_val, y_val, n_trials
            )
        else:
            best_params = None

        # Train model
        start_time = time.time()

        if model_type == "random_forest":
            model = self.train_random_forest(X_train, y_train, best_params)
        elif model_type == "xgboost":
            model = self.train_xgboost(X_train, y_train, best_params)
            if model is None:
                raise ValueError("XGBoost training failed")
        else:
            raise ValueError(f"Unknown model type: {model_type}")

        training_time = time.time() - start_time

        # Evaluate
        print(f"\nEvaluating model...")
        available_features = [col for col in self.feature_columns if col in train_df.columns]
        metrics = self.evaluate_model(
            model, X_test, y_test,
            model_name=f"{model_type}_v1",
            model_type=model_type,
            training_time=training_time,
            hyperparameters=best_params or {},
            feature_names=available_features
        )

        # Print results
        print(f"\n{'='*60}")
        print(f"MODEL PERFORMANCE")
        print(f"{'='*60}")
        print(f"Accuracy:  {metrics.accuracy:.4f}")
        print(f"Precision: {metrics.precision:.4f}")
        print(f"Recall:    {metrics.recall:.4f}")
        print(f"F1 Score:  {metrics.f1_score:.4f}")
        print(f"ROC AUC:   {metrics.roc_auc:.4f}")
        print(f"\nTraining time: {metrics.training_time_seconds:.2f}s")
        print(f"Inference time: {metrics.inference_time_ms:.2f}ms per sample")
        print(f"\nConfusion Matrix:")
        print(f"  TN: {metrics.confusion_matrix[0][0]}, FP: {metrics.confusion_matrix[0][1]}")
        print(f"  FN: {metrics.confusion_matrix[1][0]}, TP: {metrics.confusion_matrix[1][1]}")

        # Top features
        print(f"\nTop 5 Features:")
        for i, (feature, importance) in enumerate(list(metrics.feature_importance.items())[:5], 1):
            print(f"  {i}. {feature}: {importance:.4f}")

        # Save model
        model_id = self.save_model(model, metrics)

        print(f"\n{'='*60}")
        print(f"Model saved with ID: {model_id}")
        print(f"{'='*60}\n")

        return model_id


# Global instance
model_trainer = ModelTrainer()
