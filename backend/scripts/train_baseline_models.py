"""
Random Forest Baseline Model Training Script

This script implements the complete ML pipeline:
1. Data loading and preparation
2. Feature engineering (categorical encoding, numerical features, derived features)
3. Feature scaling
4. Class imbalance handling (SMOTE)
5. Random Forest training with hyperparameter tuning
6. Model evaluation and artifact saving

Author: FinSight AI Team
Date: February 1, 2026
"""

import json
import pickle
import warnings
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
from imblearn.over_sampling import SMOTE
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

# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
PROCESSED_DIR = DATA_DIR / "processed"
BALANCED_DIR = DATA_DIR / "balanced"
SPLITS_DIR = DATA_DIR / "splits" / "stratified"
MODELS_DIR = PROJECT_ROOT / "backend" / "models"

# Create models directory
MODELS_DIR.mkdir(exist_ok=True, parents=True)


class FraudMLPipeline:
    """Complete ML pipeline for fraud detection."""

    def __init__(self, use_smote: bool = True, random_state: int = 42, max_samples: int = None):
        """
        Initialize ML pipeline.

        Args:
            use_smote: Whether to use SMOTE-balanced data
            random_state: Random seed for reproducibility
            max_samples: Maximum samples to load (for memory optimization)
        """
        self.use_smote = use_smote
        self.random_state = random_state
        self.max_samples = max_samples
        self.scaler = StandardScaler()
        self.encoder = None
        self.feature_names = None
        self.model = None
        self.metadata = {}

    def load_data(self) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """Load train, validation, and test datasets."""
        print("=" * 80)
        print("STEP 1: LOADING DATA")
        print("=" * 80)

        if self.use_smote:
            # Use SMOTE-balanced training data
            train_path = BALANCED_DIR / "train_balanced_smote.csv"
            print(f"Loading SMOTE-balanced training data from: {train_path}")
        else:
            # Use regular stratified split
            train_path = SPLITS_DIR / "train.csv"
            print(f"Loading regular training data from: {train_path}")

        val_path = SPLITS_DIR / "val.csv"
        # Load with optional sampling for memory optimization
        if self.max_samples:
            print(f"\n⚠️  Memory optimization: Limiting to {self.max_samples:,} samples")
            # Stratified sampling to maintain class balance
            train_full = pd.read_csv(train_path)
            if len(train_full) > self.max_samples:
                fraud = train_full[train_full['isFraud'] == 1]
                normal = train_full[train_full['isFraud'] == 0]

                n_fraud = min(len(fraud), self.max_samples // 2)
                n_normal = self.max_samples - n_fraud

                fraud_sample = fraud.sample(n=n_fraud, random_state=self.random_state)
                normal_sample = normal.sample(n=n_normal, random_state=self.random_state)

                train_df = pd.concat([fraud_sample, normal_sample]).sample(frac=1, random_state=self.random_state)
                print(f"  Sampled {len(fraud_sample):,} fraud + {len(normal_sample):,} normal = {len(train_df):,} total")
            else:
                train_df = train_full
        else:
            train_df = pd.read_csv(train_path)

        val_df = pd.read_csv(val_path)
        test_df = pd.read_csv(test_path)

        print(f"\nTraining set shape: {train_df.shape}")
        print(f"Validation set shape: {val_df.shape}")
        print(f"Test set shape: {test_df.shape}")

        print(f"\nTraining set fraud rate: {train_df['isFraud'].mean():.4f}")
        print(f"Validation set fraud rate: {val_df['isFraud'].mean():.4f}")
        print(f"Test set fraud rate: {test_df['isFraud'].mean():.4f}")

        return train_df, val_df, test_df

    def engineer_features(
        self, df: pd.DataFrame, fit: bool = False
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Engineer features from raw data.

        Args:
            df: Input dataframe
            fit: Whether to fit transformers (True for train, False for val/test)

        Returns:
            X: Feature matrix
            y: Target vector
        """
        print("\n" + "=" * 80)
        print("STEP 2: FEATURE ENGINEERING")
        print("=" * 80)

        df = df.copy()

        # Target variable
        y = df["isFraud"].values

        # Categorical features for one-hot encoding
        categorical_features = ["type"]
        print(f"\nCategorical features: {categorical_features}")
        print(f"Transaction types: {df['type'].unique().tolist()}")

        # Numerical features (already created by data cleaning script)
        numerical_features = [
            "amount",
            "oldbalanceOrg",
            "newbalanceOrig",
            "oldbalanceDest",
            "newbalanceDest",
            "amount_normalized",
            "hour",
            "day",
            "day_of_week",
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

        print(f"\nNumerical features ({len(numerical_features)}): {numerical_features[:5]}...")

        # Derived features (additional feature engineering)
        print("\nCreating derived features...")

        # Transaction velocity features (amount per hour bins)
        df["amount_per_hour"] = df["amount"] / (df["hour"] + 1)

        # Balance drain ratio (how much of original balance was drained)
        df["balance_drain_ratio"] = np.where(
            df["oldbalanceOrg"] > 0,
            (df["oldbalanceOrg"] - df["newbalanceOrig"]) / df["oldbalanceOrg"],
            0,
        )

        # Destination balance growth
        df["dest_balance_growth"] = np.where(
            df["oldbalanceDest"] > 0,
            (df["newbalanceDest"] - df["oldbalanceDest"]) / df["oldbalanceDest"],
            0,
        )

        # Flag for complete balance drain
        df["complete_drain"] = (
            (df["oldbalanceOrg"] > 0) & (df["newbalanceOrig"] == 0)
        ).astype(int)

        # Flag for disappeared money (money left origin but didn't arrive at destination)
        df["money_disappeared"] = (
            df["balance_change_orig"] + df["balance_change_dest"]
        ).abs()

        # Add derived features to numerical features list
        derived_features = [
            "amount_per_hour",
            "balance_drain_ratio",
            "dest_balance_growth",
            "complete_drain",
            "money_disappeared",
        ]
        numerical_features.extend(derived_features)

        print(f"Added {len(derived_features)} derived features")
        print(f"Total numerical features: {len(numerical_features)}")

        # One-hot encode categorical features
        if fit:
            self.encoder = OneHotEncoder(sparse_output=False, handle_unknown="ignore")
            categorical_encoded = self.encoder.fit_transform(df[categorical_features])
            categorical_feature_names = self.encoder.get_feature_names_out(
                categorical_features
            )
        else:
            categorical_encoded = self.encoder.transform(df[categorical_features])
            categorical_feature_names = self.encoder.get_feature_names_out(
                categorical_features
            )

        print(
            f"\nOne-hot encoded categorical features: {categorical_encoded.shape[1]} features"
        )
        print(f"Feature names: {list(categorical_feature_names)}")

        # Combine numerical and categorical features
        X_numerical = df[numerical_features].values
        X = np.hstack([X_numerical, categorical_encoded])

        # Store feature names
        if fit:
            self.feature_names = numerical_features + list(categorical_feature_names)
            print(f"\nTotal features: {len(self.feature_names)}")

        # Handle any NaN or inf values
        X = np.nan_to_num(X, nan=0.0, posinf=1e10, neginf=-1e10)

        return X, y

    def scale_features(self, X_train: np.ndarray, X_val: np.ndarray, X_test: np.ndarray):
        """
        Scale features using StandardScaler.

        Args:
            X_train: Training features
            X_val: Validation features
            X_test: Test features

        Returns:
            Scaled features
        """
        print("\n" + "=" * 80)
        print("STEP 3: FEATURE SCALING")
        print("=" * 80)

        print("Fitting StandardScaler on training data...")
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_val_scaled = self.scaler.transform(X_val)
        X_test_scaled = self.scaler.transform(X_test)

        print(f"Training features scaled: {X_train_scaled.shape}")
        print(f"Validation features scaled: {X_val_scaled.shape}")
        print(f"Test features scaled: {X_test_scaled.shape}")

        # Print scaling statistics
        print(f"\nScaling statistics (first 5 features):")
        for i in range(min(5, len(self.feature_names))):
            mean = self.scaler.mean_[i]
            std = self.scaler.scale_[i]
            print(f"  {self.feature_names[i]}: mean={mean:.4f}, std={std:.4f}")

        return X_train_scaled, X_val_scaled, X_test_scaled

    def train_random_forest(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: np.ndarray,
        y_val: np.ndarray, (optimized for memory)
            param_grid = {
                "n_estimators": [50, 100],  # Reduced for memory
                "max_depth": [10, 20],  # Removed None to limit memory
                "min_samples_split": [5],  # Single value for speed
                "min_samples_leaf": [2],  # Single value for speed
                "class_weight": ["balanced"],  # Handle class imbalance
            }

            print(f"Parameter grid: {param_grid}")
            print(f"Total combinations: {2 * 2 * 1 * 1 * 1} (reduced for M4 Pro)")

            # Initialize base model
            rf_base = RandomForestClassifier(
                random_state=self.random_state,
                n_jobs=2,  # Limit parallel jobs for memory
                verbose=0,
                max_samples=0.8  # Use only 80% of samples per tree
            )

            # Setup GridSearchCV with stratified k-fold (reduced folds)
            cv = StratifiedKFold(n_splits=3, shuffle=True, random_state=self.random_state)
            grid_search = GridSearchCV(
                estimator=rf_base,
                param_grid=param_grid,
                cv=cv,
                scoring="f1",  # Optimize for F1-score
                n_jobs=1,  # Sequential search to limit memoryors": [100, 200],  # Reduced for faster training
                "max_depth": [10, 20, None],
                "min_samples_split": [2, 5],
                "min_samples_leaf": [1, 2],
                "class_weight": ["balanced"],  # Handle class imbalance
            }

            print(f"Parameter grid: {param_grid}")

            # Initialize base model
            rf_base = RandomForestClassifier(
                random_state=self.random_state, n_jobs=-1, verbose=0
            )

            # Setup GridSearchCV with stratified k-fold
            cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=self.random_state)
            grid_search = GridSearchCV(
                estimator=rf_base,
                param_grid=param_grid,
                cv=cv,
                scoring="f1",  # Optimize for F1-score
                n_jobs=-1,
                verbose=2,
            )

            # Fit grid search
            print("\nStarting grid search...")
            grid_search.fit(X_train, y_train)

            # Best model
            self.model = grid_search.best_estimator_
            best_params = grid_search.best_params_
            best_score = grid_search.best_score_

            print("\n" + "=" * 80)
            print("HYPERPARAMETER TUNING RESULTS")
            print("=" * 80)
            print(f"\nBest parameters: {best_params}")
            print(f"Best cross-validation F1-score: {best_score:.4f}")

            # Store in metadata
            self.metadata["hyperparameters"] = best_params
            self.metadata["cv_f1_score"] = float(best_score)
            self.metadata["cv_folds"] = 5

        else:
            print("\nTraining Random Forest with default parameters...")
            self.model = RandomForestClassifier(
                n_estimators=200,
                max_depth=20,
                min_samples_split=2,
                min_samples_leaf=1,
                class_weight="balanced",
                random_state=self.random_state,
                n_jobs=-1,
                verbose=1,
            )
            self.model.fit(X_train, y_train)

        # Validation set evaluation
        print("\nEvaluating on validation set...")
        y_val_pred = self.model.predict(X_val)
        y_val_proba = self.model.predict_proba(X_val)[:, 1]

        val_metrics = self._calculate_metrics(y_val, y_val_pred, y_val_proba)
        self.metadata["validation_metrics"] = val_metrics

        print("\n" + "=" * 80)
        print("VALIDATION SET PERFORMANCE")
        print("=" * 80)
        self._print_metrics(val_metrics)

    def evaluate_test_set(
        self, X_test: np.ndarray, y_test: np.ndarray
    ) -> Dict[str, float]:
        """
        Evaluate model on test set.

        Args:
            X_test: Test features
            y_test: Test labels

        Returns:
            Dictionary of test metrics
        """
        print("\n" + "=" * 80)
        print("STEP 5: TEST SET EVALUATION")
        print("=" * 80)

        y_test_pred = self.model.predict(X_test)
        y_test_proba = self.model.predict_proba(X_test)[:, 1]

        test_metrics = self._calculate_metrics(y_test, y_test_pred, y_test_proba)
        self.metadata["test_metrics"] = test_metrics

        self._print_metrics(test_metrics)

        # Confusion matrix
        cm = confusion_matrix(y_test, y_test_pred)
        print("\nConfusion Matrix:")
        print(cm)

        return test_metrics

    def _calculate_metrics(
        self, y_true: np.ndarray, y_pred: np.ndarray, y_proba: np.ndarray
    ) -> Dict[str, float]:
        """Calculate classification metrics."""
        metrics = {
            "accuracy": float(accuracy_score(y_true, y_pred)),
            "precision": float(precision_score(y_true, y_pred)),
            "recall": float(recall_score(y_true, y_pred)),
            "f1_score": float(f1_score(y_true, y_pred)),
            "auc_roc": float(roc_auc_score(y_true, y_proba)),
        }
        return metrics

    def _print_metrics(self, metrics: Dict[str, float]):
        """Print metrics in a formatted way."""
        print(f"\nAccuracy:  {metrics['accuracy']:.4f}")
        print(f"Precision: {metrics['precision']:.4f}")
        print(f"Recall:    {metrics['recall']:.4f}")
        print(f"F1-Score:  {metrics['f1_score']:.4f}")
        print(f"AUC-ROC:   {metrics['auc_roc']:.4f}")

    def get_feature_importance(self, top_n: int = 20) -> pd.DataFrame:
        """
        Get feature importance from trained model.

        Args:
            top_n: Number of top features to return

        Returns:
            DataFrame with feature names and importance scores
        """
        print("\n" + "=" * 80)
        print("FEATURE IMPORTANCE")
        print("=" * 80)

        importances = self.model.feature_importances_
        feature_importance_df = pd.DataFrame(
            {"feature": self.feature_names, "importance": importances}
        ).sort_values(by="importance", ascending=False)

        print(f"\nTop {top_n} most important features:")
        print(feature_importance_df.head(top_n).to_string(index=False))

        self.metadata["top_features"] = feature_importance_df.head(top_n).to_dict(
            orient="records"
        )

        return feature_importance_df

    def save_model(self, version: str = "v1"):
        """
        Save model and all artifacts.

        Args:
            version: Model version string
        """
        print("\n" + "=" * 80)
        print("STEP 6: SAVING MODEL ARTIFACTS")
        print("=" * 80)

        # Model filename
        model_path = MODELS_DIR / f"random_forest_{version}.pkl"

        # Save model
        print(f"\nSaving Random Forest model to: {model_path}")
        with open(model_path, "wb") as f:
            pickle.dump(self.model, f)
        print(f"✓ Model saved ({model_path.stat().st_size / 1024 / 1024:.2f} MB)")

        # Save scaler
        scaler_path = MODELS_DIR / f"scaler_{version}.pkl"
        print(f"\nSaving StandardScaler to: {scaler_path}")
        with open(scaler_path, "wb") as f:
            pickle.dump(self.scaler, f)
        print(f"✓ Scaler saved ({scaler_path.stat().st_size / 1024:.2f} KB)")

        # Save encoder
        encoder_path = MODELS_DIR / f"encoder_{version}.pkl"
        print(f"\nSaving OneHotEncoder to: {encoder_path}")
        with open(encoder_path, "wb") as f:
            pickle.dump(self.encoder, f)
        print(f"✓ Encoder saved ({encoder_path.stat().st_size / 1024:.2f} KB)")

        # Save feature names
        features_path = MODELS_DIR / f"feature_names_{version}.json"
        print(f"\nSaving feature names to: {features_path}")
        with open(features_path, "w") as f:
            json.dump(self.feature_names, f, indent=2)
        print(f"✓ Feature names saved ({len(self.feature_names)} features)")

        # Save metadata
        self.metadata.update(
            {
                "model_version": version,
                "model_type": "RandomForestClassifier",
                "training_date": datetime.now().isoformat(),
                "dataset": "train_balanced_smote.csv" if self.use_smote else "train.csv",
                "random_state": self.random_state,
                "n_features": len(self.feature_names),
                "model_path": str(model_path.relative_to(PROJECT_ROOT)),
                "scaler_path": str(scaler_path.relative_to(PROJECT_ROOT)),
                "encoder_path": str(encoder_path.relative_to(PROJECT_ROOT)),
                "feature_names_path": str(features_path.relative_to(PROJECT_ROOT)),
            }
        )

        metadata_path = MODELS_DIR / f"random_forest_{version}_metadata.json"
        print(f"\nSaving training metadata to: {metadata_path}")
        with open(metadata_path, "w") as f:
            json.dump(self.metadata, f, indent=2)
        print(f"✓ Metadata saved")

        # Create model registry entry
        self._update_model_registry(version)

        print("\n" + "=" * 80)
        print("✓ ALL ARTIFACTS SAVED SUCCESSFULLY")
        print("=" * 80)

    def _update_model_registry(self, version: str):
        """Update or create model registry file."""
        registry_path = MODELS_DIR / "model_registry.json"

        if registry_path.exists():
            with open(registry_path, "r") as f:
                registry = json.load(f)
        else:
            registry = {"models": []}

        # Add new model entry
        model_entry = {
            "version": version,
            "model_type": "RandomForestClassifier",
            "created_at": datetime.now().isoformat(),
            "f1_score": self.metadata["test_metrics"]["f1_score"],
            "precision": self.metadata["test_metrics"]["precision"],
            "recall": self.metadata["test_metrics"]["recall"],
            "auc_roc": self.metadata["test_metrics"]["auc_roc"],
    import argparse

    parser = argparse.ArgumentParser(description='Train Random Forest fraud detection model')
    parser.add_argument('--max-samples', type=int, default=50000,
                        help='Maximum training samples (default: 50000 for M4 Pro)')
    parser.add_argument('--no-tune', action='store_true',
                        help='Skip hyperparameter tuning')
    args = parser.parse_args()

    print("=" * 80)
    print("RANDOM FOREST BASELINE MODEL TRAINING (MEMORY OPTIMIZED)")
    print("=" * 80)
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Project: FinSight AI - Fraud Detection")
    print(f"Max samples: {args.max_samples:,}")
    print("=" * 80)

    # Initialize pipeline
    pipeline = FraudMLPipeline(use_smote=True, random_state=42, max_samples=args.max_samples
        if existing_idx is not None:
            registry["models"][existing_idx] = model_entry
        else:
            registry["models"].append(model_entry)

        # Sort by creation date (newest first)
        registry["models"].sort(key=lambda x: x["created_at"], reverse=True)

        with open(registry_path, "w") as f:
            json.dump(registry, f, indent=2)

        print(f"\n✓ Model registry updated: {registry_path}")


def main():
    """Main training pipeline."""
    print("=" * 80)
    print("RANDOM FOREST BASELINE MODEL TRAINING")
    print("=" * 80)
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Project: FinSight AI - Fraud Detection")
    print("=" * 80)

    # Initialize pipeline
    pipeline = FraudMLPipeline(use_smote=True, random_state=42)not args.no_tun

    # Step 1: Load data
    train_df, val_df, test_df = pipeline.load_data()

    # Step 2: Feature engineering
    X_train, y_train = pipeline.engineer_features(train_df, fit=True)
    X_val, y_val = pipeline.engineer_features(val_df, fit=False)
    X_test, y_test = pipeline.engineer_features(test_df, fit=False)

    # Step 3: Feature scaling
    X_train, X_val, X_test = pipeline.scale_features(X_train, X_val, X_test)

    # Step 4: Train model with hyperparameter tuning
    pipeline.train_random_forest(X_train, y_train, X_val, y_val, tune_hyperparameters=True)

    # Step 5: Evaluate on test set
    test_metrics = pipeline.evaluate_test_set(X_test, y_test)

    # Get feature importance
    pipeline.get_feature_importance(top_n=20)

    # Step 6: Save all artifacts
    pipeline.save_model(version="v1")

    print("\n" + "=" * 80)
    print("✓ TRAINING COMPLETE!")
    print("=" * 80)
    print("\nModel performance summary:")
    print(f"  F1-Score: {test_metrics['f1_score']:.4f}")
    print(f"  Precision: {test_metrics['precision']:.4f}")
    print(f"  Recall: {test_metrics['recall']:.4f}")
    print(f"  AUC-ROC: {test_metrics['auc_roc']:.4f}")
    print("\nModel artifacts saved to: backend/models/")
    print("=" * 80)


if __name__ == "__main__":
    main()
