"""
Test All Trained Models Locally

Load and test predictions from:
- Random Forest (random_forest_v1.pkl)
- XGBoost (xgboost_v1.json)
- LightGBM (lightgbm_v1.txt)

Author: FinSight AI Team
Date: February 1, 2026
"""

import json
import pickle
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.preprocessing import OneHotEncoder, StandardScaler

# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
MODELS_DIR = PROJECT_ROOT / "backend" / "models"
DATA_DIR = PROJECT_ROOT / "data"


def load_random_forest():
    """Load Random Forest model and preprocessor."""
    print("\n" + "=" * 80)
    print("LOADING RANDOM FOREST MODEL")
    print("=" * 80)

    model_path = MODELS_DIR / "random_forest_v1.pkl"
    preprocessor_path = MODELS_DIR / "preprocessor.pkl"
    metadata_path = MODELS_DIR / "random_forest_metadata.json"

    with open(model_path, "rb") as f:
        model = pickle.load(f)

    with open(preprocessor_path, "rb") as f:
        preprocessor = pickle.load(f)

    with open(metadata_path, "r") as f:
        metadata = json.load(f)

    print(f"✓ Model loaded: {model_path}")
    print(f"✓ F1-score: {metadata['metrics']['f1_score']:.4f}")
    print(f"✓ Features: {metadata['feature_count']}")

    return model, preprocessor, metadata


def load_xgboost():
    """Load XGBoost model and preprocessor."""
    print("\n" + "=" * 80)
    print("LOADING XGBOOST MODEL")
    print("=" * 80)

    model_path = MODELS_DIR / "xgboost_v1.json"
    preprocessor_path = MODELS_DIR / "xgb_preprocessor_v1.pkl"
    metadata_path = MODELS_DIR / "xgboost_v1_metadata.json"

    model = xgb.Booster()
    model.load_model(str(model_path))

    with open(preprocessor_path, "rb") as f:
        preprocessor = pickle.load(f)

    with open(metadata_path, "r") as f:
        metadata = json.load(f)

    print(f"✓ Model loaded: {model_path}")
    print(f"✓ F1-score: {metadata['metrics']['f1_score']:.4f}")
    print(f"✓ Features: {metadata['feature_count']}")

    return model, preprocessor, metadata


def load_lightgbm():
    """Load LightGBM model."""
    print("\n" + "=" * 80)
    print("LOADING LIGHTGBM MODEL")
    print("=" * 80)

    model_path = MODELS_DIR / "lightgbm_v1.txt"
    metadata_path = MODELS_DIR / "lightgbm_v1_metadata.json"

    model = lgb.Booster(model_file=str(model_path))

    with open(metadata_path, "r") as f:
        metadata = json.load(f)

    print(f"✓ Model loaded: {model_path}")
    print(f"✓ F1-score: {metadata['metrics']['f1_score']:.4f}")
    print(f"✓ Features: {metadata['feature_count']}")

    return model, metadata


def create_sample_transactions():
    """Create sample transactions for testing."""
    print("\n" + "=" * 80)
    print("CREATING SAMPLE TRANSACTIONS")
    print("=" * 80)

    samples = [
        {
            "name": "Normal Payment",
            "type": "PAYMENT",
            "amount": 500.0,
            "oldbalanceOrg": 10000.0,
            "newbalanceOrig": 9500.0,
            "oldbalanceDest": 5000.0,
            "newbalanceDest": 5500.0
        },
        {
            "name": "Suspicious Transfer",
            "type": "TRANSFER",
            "amount": 100000.0,
            "oldbalanceOrg": 120000.0,
            "newbalanceOrig": 20000.0,
            "oldbalanceDest": 0.0,
            "newbalanceDest": 100000.0
        },
        {
            "name": "Small Cash Out",
            "type": "CASH_OUT",
            "amount": 50.0,
            "oldbalanceOrg": 1000.0,
            "newbalanceOrig": 950.0,
            "oldbalanceDest": 0.0,
            "newbalanceDest": 50.0
        },
        {
            "name": "High Value Transfer (Suspicious)",
            "type": "TRANSFER",
            "amount": 500000.0,
            "oldbalanceOrg": 500000.0,
            "newbalanceOrig": 0.0,
            "oldbalanceDest": 0.0,
            "newbalanceDest": 0.0  # Money disappeared!
        }
    ]

    for sample in samples:
        print(f"\n{sample['name']}:")
        print(f"  Type: {sample['type']}, Amount: ${sample['amount']:,.2f}")

    return samples


def prepare_features_rf(sample, scaler, encoder):
    """Prepare features for Random Forest (matches optimized training)."""
    # Numerical features (will be scaled)
    numerical_features = [
        sample["amount"],
        sample["oldbalanceOrg"],
        sample["newbalanceOrig"],
        sample["oldbalanceDest"],
        sample["newbalanceDest"],
        sample["oldbalanceOrg"] - sample["newbalanceOrig"],  # balance_diff_orig
        sample["oldbalanceDest"] - sample["newbalanceDest"],  # balance_diff_dest
        sample["amount"] / (sample["oldbalanceOrg"] + 1)  # amount_to_balance_ratio
    ]

    # Scale numerical features ONLY
    X_num = np.array(numerical_features).reshape(1, -1)
    X_num_scaled = scaler.transform(X_num)

    # Categorical encoding
    X_cat = encoder.transform([[sample["type"]]])

    # Combine scaled numerical + categorical
    X_final = np.hstack([X_num_scaled, X_cat])

    return X_final


def prepare_features_xgb(sample, preprocessor):
    """Prepare features for XGBoost (same as RF)."""
    scaler = preprocessor["scaler"]
    encoder = preprocessor["encoder"]

    # Same as RF
    return prepare_features_rf(sample, scaler, encoder)


def prepare_features_lgb(sample):
    """Prepare features for LightGBM."""
    features = [
        sample["amount"],
        sample["oldbalanceOrg"],
        sample["newbalanceOrig"],
        sample["oldbalanceDest"],
        sample["newbalanceDest"],
        sample["oldbalanceOrg"] - sample["newbalanceOrig"],  # balance_diff_orig
        sample["oldbalanceDest"] - sample["newbalanceDest"],  # balance_diff_dest
        sample["amount"] / (sample["oldbalanceOrg"] + 1),  # amount_to_balance_ratio
        sample["type"]  # categorical
    ]

    df = pd.DataFrame([features], columns=[
        "amount", "oldbalanceOrg", "newbalanceOrig", "oldbalanceDest",
        "newbalanceDest", "balance_diff_orig", "balance_diff_dest",
        "amount_to_balance_ratio", "type"
    ])

    df["type"] = df["type"].astype("category")

    return df


def test_models():
    """Test all three models with sample transactions."""
    print("=" * 80)
    print("TESTING ALL TRAINED MODELS")
    print("=" * 80)

    # Load models
    rf_model, rf_preprocessor, rf_metadata = load_random_forest()
    xgb_model, xgb_preprocessor, xgb_metadata = load_xgboost()
    lgb_model, lgb_metadata = load_lightgbm()

    # Create samples
    samples = create_sample_transactions()

    # Test predictions
    print("\n" + "=" * 80)
    print("PREDICTION RESULTS")
    print("=" * 80)

    for i, sample in enumerate(samples, 1):
        print(f"\n{i}. {sample['name']}")
        print(f"   Type: {sample['type']}, Amount: ${sample['amount']:,.2f}")

        try:
            # Random Forest
            X_rf = prepare_features_rf(sample, rf_preprocessor["scaler"], rf_preprocessor["encoder"])
            rf_proba = rf_model.predict_proba(X_rf)[0][1]
            rf_pred = "FRAUD" if rf_proba > 0.5 else "LEGIT"
            print(f"   Random Forest:  {rf_pred} (risk: {rf_proba*100:.2f}%)")
        except Exception as e:
            print(f"   Random Forest:  ERROR - {str(e)[:50]}")

        try:
            # XGBoost - use its own feature prep
            X_xgb_num = np.array([
                sample["amount"], sample["oldbalanceOrg"], sample["newbalanceOrig"],
                sample["oldbalanceDest"], sample["newbalanceDest"],
                sample["oldbalanceOrg"] - sample["newbalanceOrig"],
                sample["oldbalanceDest"] - sample["newbalanceDest"],
                sample["amount"] / (sample["oldbalanceOrg"] + 1)
            ]).reshape(1, -1)
            X_xgb_cat = xgb_preprocessor["encoder"].transform([[sample["type"]]])
            X_xgb = np.hstack([X_xgb_num, X_xgb_cat])
            X_xgb_scaled = xgb_preprocessor["scaler"].transform(X_xgb)

            feature_names = ["amount", "oldbalanceOrg", "newbalanceOrig", "oldbalanceDest",
                            "newbalanceDest", "balance_diff_orig", "balance_diff_dest",
                            "amount_to_balance_ratio", "type_CASH_IN", "type_CASH_OUT",
                            "type_DEBIT", "type_PAYMENT", "type_TRANSFER"]
            dmatrix = xgb.DMatrix(X_xgb_scaled, feature_names=feature_names)
            xgb_proba = xgb_model.predict(dmatrix)[0]
            xgb_pred = "FRAUD" if xgb_proba > 0.5 else "LEGIT"
            print(f"   XGBoost:        {xgb_pred} (risk: {xgb_proba*100:.2f}%)")
        except Exception as e:
            print(f"   XGBoost:        ERROR - {str(e)[:50]}")

        try:
            # LightGBM
            X_lgb = prepare_features_lgb(sample)
            lgb_proba = lgb_model.predict(X_lgb)[0]
            lgb_pred = "FRAUD" if lgb_proba > 0.5 else "LEGIT"
            print(f"   LightGBM:       {lgb_pred} (risk: {lgb_proba*100:.2f}%)")
        except Exception as e:
            print(f"   LightGBM:       ERROR - {str(e)[:50]}")

    print("\n" + "=" * 80)
    print("MODEL COMPARISON SUMMARY")
    print("=" * 80)
    print(f"\nRandom Forest - F1: {rf_metadata['metrics']['f1_score']:.4f}, Precision: {rf_metadata['metrics']['precision']:.4f}, Recall: {rf_metadata['metrics']['recall']:.4f}")
    print(f"XGBoost       - F1: {xgb_metadata['metrics']['f1_score']:.4f}, Precision: {xgb_metadata['metrics']['precision']:.4f}, Recall: {xgb_metadata['metrics']['recall']:.4f}")
    print(f"LightGBM      - F1: {lgb_metadata['metrics']['f1_score']:.4f}, Precision: {lgb_metadata['metrics']['precision']:.4f}, Recall: {lgb_metadata['metrics']['recall']:.4f}")

    print("\n✓ ALL MODELS LOADED AND TESTED SUCCESSFULLY!")
    print("=" * 80)


if __name__ == "__main__":
    test_models()
