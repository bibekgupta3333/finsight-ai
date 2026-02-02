"""
Train Stacking Model (Meta-Learner).

This script trains a Logistic Regression meta-model on the predictions
from base models (LightGBM, XGBoost, Random Forest).

Optimized for M4 Pro: Uses lazy loading, processes in batches if needed.
"""

import argparse
import joblib
import json
import logging
import sys
from pathlib import Path
from typing import Dict, Tuple

import lightgbm as lgb
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import cross_val_score

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


def load_base_models(version: str = "v1") -> Dict:
    """
    Load all three base models.

    Args:
        version: Model version

    Returns:
        Dict with loaded models and preprocessors
    """
    logger.info(f"Loading base models (version: {version})...")

    models = {}

    # Load LightGBM
    lgbm_path = MODELS_DIR / f"lightgbm_{version}.txt"
    if lgbm_path.exists():
        models["lightgbm"] = lgb.Booster(model_file=str(lgbm_path))
        logger.info(f"✓ Loaded LightGBM from {lgbm_path}")
    else:
        logger.warning(f"✗ LightGBM model not found: {lgbm_path}")

    # Load XGBoost
    xgb_path = MODELS_DIR / f"xgboost_{version}.json"
    if xgb_path.exists():
        xgb_model = xgb.Booster()
        xgb_model.load_model(str(xgb_path))
        models["xgboost"] = xgb_model
        logger.info(f"✓ Loaded XGBoost from {xgb_path}")
    else:
        logger.warning(f"✗ XGBoost model not found: {xgb_path}")

    # Load Random Forest
    rf_path = MODELS_DIR / f"random_forest_{version}.pkl"
    if rf_path.exists():
        models["random_forest"] = joblib.load(rf_path)
        logger.info(f"✓ Loaded Random Forest from {rf_path}")
    else:
        logger.warning(f"✗ Random Forest model not found: {rf_path}")

    # Load feature engineer
    fe_path = MODELS_DIR / f"feature_engineer_{version}.pkl"
    if fe_path.exists():
        feature_engineer = joblib.load(fe_path)
        logger.info(f"✓ Loaded FeatureEngineer from {fe_path}")
    else:
        logger.info("Creating new FeatureEngineer")
        feature_engineer = FeatureEngineer()

    return {
        "models": models,
        "feature_engineer": feature_engineer
    }


def get_base_predictions(
    models: Dict,
    X: pd.DataFrame,
    feature_engineer: FeatureEngineer,
    batch_size: int = 10000
) -> Tuple[np.ndarray, Dict[str, np.ndarray]]:
    """
    Get predictions from all base models.

    Args:
        models: Dict of loaded models
        X: Feature DataFrame
        feature_engineer: Feature engineering instance
        batch_size: Batch size for processing (M4 Pro memory optimization)

    Returns:
        Tuple of (stacked_features, individual_predictions)
    """
    logger.info(f"Generating base model predictions for {len(X)} samples...")

    all_predictions = {}
    n_samples = len(X)

    # Process in batches to avoid memory issues
    for model_name, model in models.items():
        logger.info(f"Predicting with {model_name}...")

        predictions = []

        for start_idx in range(0, n_samples, batch_size):
            end_idx = min(start_idx + batch_size, n_samples)
            X_batch = X.iloc[start_idx:end_idx]

            # Get predictions based on model type
            if model_name == "lightgbm":
                # LightGBM uses categorical features
                X_lgbm = feature_engineer.prepare_features(
                    X_batch,
                    categorical_features=['type'],
                    for_lightgbm=True
                )
                batch_pred = model.predict(X_lgbm)

            elif model_name == "xgboost":
                # XGBoost needs DMatrix
                X_xgb = feature_engineer.prepare_features(
                    X_batch,
                    categorical_features=['type'],
                    for_lightgbm=False
                )
                dmatrix = xgb.DMatrix(X_xgb)
                batch_pred = model.predict(dmatrix)

            else:  # random_forest
                # Random Forest uses one-hot encoded features
                X_rf = feature_engineer.prepare_features(
                    X_batch,
                    categorical_features=['type'],
                    for_lightgbm=False
                )
                batch_pred = model.predict_proba(X_rf)[:, 1]  # Probability of fraud

            predictions.append(batch_pred)

        # Concatenate all batch predictions
        all_predictions[model_name] = np.concatenate(predictions)
        logger.info(f"✓ {model_name}: predictions shape {all_predictions[model_name].shape}")

    # Stack predictions: shape (n_samples, n_models)
    stacked_features = np.column_stack([
        all_predictions["lightgbm"],
        all_predictions["xgboost"],
        all_predictions["random_forest"]
    ])

    logger.info(f"Stacked features shape: {stacked_features.shape}")

    return stacked_features, all_predictions


def train_stacking_model(
    X_val: pd.DataFrame,
    y_val: np.ndarray,
    models: Dict,
    feature_engineer: FeatureEngineer,
    version: str = "v1"
) -> LogisticRegression:
    """
    Train Logistic Regression meta-model on base predictions.

    Args:
        X_val: Validation features
        y_val: Validation labels
        models: Dict of base models
        feature_engineer: Feature engineering instance
        version: Model version

    Returns:
        Trained stacking model
    """
    logger.info("Training stacking meta-model...")

    # Get base model predictions
    X_stacked, individual_preds = get_base_predictions(
        models, X_val, feature_engineer, batch_size=10000
    )

    # Train Logistic Regression on stacked predictions
    meta_model = LogisticRegression(
        max_iter=1000,
        random_state=42,
        class_weight='balanced',  # Handle imbalanced data
        solver='lbfgs'
    )

    meta_model.fit(X_stacked, y_val)
    logger.info("✓ Meta-model training complete")

    # Evaluate meta-model
    y_pred = meta_model.predict(X_stacked)
    y_pred_proba = meta_model.predict_proba(X_stacked)[:, 1]

    f1 = f1_score(y_val, y_pred)
    precision = precision_score(y_val, y_pred)
    recall = recall_score(y_val, y_pred)
    auc = roc_auc_score(y_val, y_pred_proba)

    logger.info(f"\nStacking Model Performance:")
    logger.info(f"  F1-Score:  {f1:.4f}")
    logger.info(f"  Precision: {precision:.4f}")
    logger.info(f"  Recall:    {recall:.4f}")
    logger.info(f"  ROC-AUC:   {auc:.4f}")

    # Compare to individual models
    logger.info(f"\nIndividual Model Performance:")
    for model_name, preds in individual_preds.items():
        pred_binary = (preds >= 0.5).astype(int)
        f1_ind = f1_score(y_val, pred_binary)
        logger.info(f"  {model_name}: F1 = {f1_ind:.4f}")

    # Save model
    output_path = MODELS_DIR / f"stacking_model_{version}.pkl"
    joblib.dump(meta_model, output_path)
    logger.info(f"✓ Saved stacking model to {output_path}")

    # Save metadata
    metadata = {
        "version": version,
        "meta_model": "LogisticRegression",
        "base_models": list(models.keys()),
        "performance": {
            "f1_score": float(f1),
            "precision": float(precision),
            "recall": float(recall),
            "roc_auc": float(auc)
        },
        "model_coefficients": {
            "lightgbm": float(meta_model.coef_[0][0]),
            "xgboost": float(meta_model.coef_[0][1]),
            "random_forest": float(meta_model.coef_[0][2]),
            "intercept": float(meta_model.intercept_[0])
        }
    }

    metadata_path = MODELS_DIR / f"stacking_model_{version}_metadata.json"
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)
    logger.info(f"✓ Saved metadata to {metadata_path}")

    # Print learned weights
    logger.info(f"\nLearned Model Weights (coefficients):")
    logger.info(f"  LightGBM:      {meta_model.coef_[0][0]:.4f}")
    logger.info(f"  XGBoost:       {meta_model.coef_[0][1]:.4f}")
    logger.info(f"  Random Forest: {meta_model.coef_[0][2]:.4f}")
    logger.info(f"  Intercept:     {meta_model.intercept_[0]:.4f}")

    return meta_model


def main():
    """Main training function."""
    parser = argparse.ArgumentParser(description="Train stacking meta-model")
    parser.add_argument(
        "--val_data",
        type=str,
        default=str(DATA_DIR / "splits" / "temporal" / "val.csv"),
        help="Path to validation data CSV"
    )
    parser.add_argument(
        "--version",
        type=str,
        default="v1",
        help="Model version"
    )
    parser.add_argument(
        "--max_samples",
        type=int,
        default=50000,
        help="Maximum samples to use (M4 Pro memory limit)"
    )

    args = parser.parse_args()

    # Load validation data
    logger.info(f"Loading validation data from {args.val_data}...")
    df_val = pd.read_csv(args.val_data)

    # Limit samples for M4 Pro
    if len(df_val) > args.max_samples:
        logger.info(f"Sampling {args.max_samples} from {len(df_val)} samples")
        df_val = df_val.sample(n=args.max_samples, random_state=42)

    logger.info(f"Using {len(df_val)} validation samples")

    # Separate features and labels
    y_val = df_val['isFraud'].values
    X_val = df_val.drop(columns=['isFraud'])

    logger.info(f"Fraud rate: {y_val.mean():.2%}")

    # Load base models
    model_artifacts = load_base_models(args.version)

    if len(model_artifacts["models"]) < 3:
        logger.error("Need all 3 base models to train stacking model")
        sys.exit(1)

    # Train stacking model
    stacking_model = train_stacking_model(
        X_val,
        y_val,
        model_artifacts["models"],
        model_artifacts["feature_engineer"],
        args.version
    )

    logger.info("\n✓ Stacking model training complete!")
    logger.info(f"Model saved to: {MODELS_DIR / f'stacking_model_{args.version}.pkl'}")


if __name__ == "__main__":
    main()
