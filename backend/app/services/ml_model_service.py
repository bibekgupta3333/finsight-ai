"""
ML Model Service for Fraud Detection Predictions.

Provides model loading, feature extraction, and prediction logic
for Random Forest, XGBoost, and LightGBM models.
"""

import joblib
import lightgbm as lgb
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import xgboost as xgb

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)

# Paths
BACKEND_DIR = Path(__file__).parent.parent.parent
MODELS_DIR = BACKEND_DIR / "models"


class MLModelService:
    """
    Singleton service for ML model predictions.

    Handles model loading, feature extraction, and predictions
    for all three baseline models (RF, XGBoost, LightGBM).
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MLModelService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize model service."""
        if self._initialized:
            return

        self.models = {}
        self.preprocessors = {}
        self.metadata = {}
        self.feature_names = None
        self.categorical_features = None

        self._initialized = True
        logger.info("ML Model Service initialized")

    def load_model(self, model_name: str, version: str = "v1") -> bool:
        """
        Load a specific model and its preprocessor.

        Args:
            model_name: Model name ("random_forest", "xgboost", "lightgbm")
            version: Model version (default: "v1")

        Returns:
            bool: True if successful
        """
        try:
            # Construct paths based on model type
            if model_name == "lightgbm":
                model_path = MODELS_DIR / f"lightgbm_{version}.txt"
            elif model_name == "xgboost":
                model_path = MODELS_DIR / f"xgboost_{version}.json"
            else:  # random_forest
                model_path = MODELS_DIR / f"random_forest_{version}.pkl"

            preprocessor_path = MODELS_DIR / f"{model_name}_{version}_preprocessor.pkl"
            if model_name == "xgboost":
                preprocessor_path = MODELS_DIR / f"xgb_preprocessor_{version}.pkl"

            metadata_path = MODELS_DIR / f"{model_name}_{version}_metadata.json"

            # Check files exist
            if not model_path.exists():
                logger.error(f"Model file not found: {model_path}")
                return False

            # Load model based on type
            if model_name == "lightgbm":
                self.models[model_name] = lgb.Booster(model_file=str(model_path))
            elif model_name == "xgboost":
                self.models[model_name] = xgb.Booster()
                self.models[model_name].load_model(str(model_path))
            else:  # random_forest
                self.models[model_name] = joblib.load(model_path)

            logger.info(f"Loaded model: {model_name} from {model_path}")

            # Load preprocessor
            if preprocessor_path.exists():
                preprocessor = joblib.load(preprocessor_path)

                # Handle different preprocessor formats
                if isinstance(preprocessor, dict):
                    self.preprocessors[model_name] = preprocessor.get("scaler")
                else:
                    self.preprocessors[model_name] = preprocessor

                logger.info(f"Loaded preprocessor: {model_name}")
            else:
                logger.warning(f"No preprocessor found for {model_name}")
                self.preprocessors[model_name] = None

            # Load metadata
            if metadata_path.exists():
                import json
                with open(metadata_path, "r") as f:
                    self.metadata[model_name] = json.load(f)

                # Store feature names and categorical features from first model
                if self.feature_names is None:
                    self.feature_names = self.metadata[model_name].get("feature_names", [])
                    self.categorical_features = self.metadata[model_name].get("categorical_features", [])

                logger.info(f"Loaded metadata: {model_name}")

            return True

        except Exception as e:
            logger.error(f"Error loading model {model_name}: {e}")
            return False

    def load_all_models(self, version: str = "v1") -> Dict[str, bool]:
        """
        Load all available models.

        Args:
            version: Model version (default: "v1")

        Returns:
            dict: Loading status for each model
        """
        model_names = ["random_forest", "xgboost", "lightgbm"]
        results = {}

        for model_name in model_names:
            results[model_name] = self.load_model(model_name, version)

        loaded = sum(results.values())
        logger.info(f"Loaded {loaded}/{len(model_names)} models")

        return results

    def extract_features(self, transaction: Dict) -> pd.DataFrame:
        """
        Extract features from transaction data.

        Args:
            transaction: Transaction dict with required fields

        Returns:
            pd.DataFrame: Feature dataframe ready for prediction
        """
        # Required fields
        required_fields = [
            "amount", "oldbalanceOrg", "newbalanceOrig",
            "oldbalanceDest", "newbalanceDest", "type"
        ]

        # Check required fields
        missing = [f for f in required_fields if f not in transaction]
        if missing:
            raise ValueError(f"Missing required fields: {missing}")

        # Calculate derived features
        balance_diff_orig = transaction["newbalanceOrig"] - transaction["oldbalanceOrg"]
        balance_diff_dest = transaction["newbalanceDest"] - transaction["oldbalanceDest"]
        amount_to_balance_ratio = (
            transaction["amount"] / transaction["oldbalanceOrg"]
            if transaction["oldbalanceOrg"] > 0 else 0
        )

        # Create feature dict
        features = {
            "amount": float(transaction["amount"]),
            "oldbalanceOrg": float(transaction["oldbalanceOrg"]),
            "newbalanceOrig": float(transaction["newbalanceOrig"]),
            "oldbalanceDest": float(transaction["oldbalanceDest"]),
            "newbalanceDest": float(transaction["newbalanceDest"]),
            "balance_diff_orig": float(balance_diff_orig),
            "balance_diff_dest": float(balance_diff_dest),
            "amount_to_balance_ratio": float(amount_to_balance_ratio),
            "type": str(transaction["type"])
        }

        # Create DataFrame
        df = pd.DataFrame([features])

        # Convert type to category for LightGBM
        df["type"] = df["type"].astype("category")

        return df

    def predict(
        self,
        transaction: Dict,
        model_name: str = "lightgbm",
        return_proba: bool = True
    ) -> Dict:
        """
        Make prediction for a single transaction.

        Args:
            transaction: Transaction dict
            model_name: Model to use (default: "lightgbm")
            return_proba: Return probability scores (default: True)

        Returns:
            dict: Prediction results with label, probability, and confidence
        """
        # Check model loaded
        if model_name not in self.models:
            raise ValueError(f"Model {model_name} not loaded. Call load_model() first.")

        model = self.models[model_name]
        preprocessor = self.preprocessors.get(model_name)

        # Extract features
        features_df = self.extract_features(transaction)

        # Prepare features for different models
        if model_name == "random_forest":
            # RF: One-hot encode categorical features
            features_encoded = pd.get_dummies(
                features_df,
                columns=["type"],
                drop_first=False
            )

            # Ensure all expected features present (from training)
            expected_features = [
                "amount", "oldbalanceOrg", "newbalanceOrig",
                "oldbalanceDest", "newbalanceDest", "balance_diff_orig",
                "balance_diff_dest", "amount_to_balance_ratio",
                "type_CASH_IN", "type_CASH_OUT", "type_DEBIT",
                "type_PAYMENT", "type_TRANSFER"
            ]

            for col in expected_features:
                if col not in features_encoded.columns:
                    features_encoded[col] = 0

            # Reorder columns to match training
            features_encoded = features_encoded[expected_features]

            # Scale numerical features
            if preprocessor is not None:
                numerical_cols = [
                    "amount", "oldbalanceOrg", "newbalanceOrig",
                    "oldbalanceDest", "newbalanceDest", "balance_diff_orig",
                    "balance_diff_dest", "amount_to_balance_ratio"
                ]
                features_encoded[numerical_cols] = preprocessor.transform(
                    features_encoded[numerical_cols]
                )

            X = features_encoded

        elif model_name == "xgboost":
            # XGBoost: One-hot encode + scale all features
            features_encoded = pd.get_dummies(
                features_df,
                columns=["type"],
                drop_first=False
            )

            # Ensure all expected features present
            expected_features = [
                "amount", "oldbalanceOrg", "newbalanceOrig",
                "oldbalanceDest", "newbalanceDest", "balance_diff_orig",
                "balance_diff_dest", "amount_to_balance_ratio",
                "type_CASH_IN", "type_CASH_OUT", "type_DEBIT",
                "type_PAYMENT", "type_TRANSFER"
            ]

            for col in expected_features:
                if col not in features_encoded.columns:
                    features_encoded[col] = 0

            features_encoded = features_encoded[expected_features]

            # Scale all features
            if preprocessor is not None:
                features_encoded = pd.DataFrame(
                    preprocessor.transform(features_encoded),
                    columns=features_encoded.columns
                )

            # Keep as DataFrame for XGBoost Booster (needs feature names)
            X = features_encoded

        elif model_name == "lightgbm":
            # LightGBM: Keep categorical features as category dtype
            X = features_df

        else:
            raise ValueError(f"Unknown model: {model_name}")

        # Make prediction
        if model_name == "lightgbm":
            # LightGBM Booster expects numpy array
            prediction = int(model.predict(X)[0] > 0.5)
        elif model_name == "xgboost":
            # XGBoost Booster expects DMatrix
            dmatrix = xgb.DMatrix(X)
            prediction = int(model.predict(dmatrix)[0] > 0.5)
        else:
            # Scikit-learn model
            prediction = int(model.predict(X)[0])

        # Get probabilities
        if return_proba:
            try:
                if model_name == "random_forest":
                    proba = model.predict_proba(X)[0]
                    fraud_prob = float(proba[1])
                    confidence = float(max(proba))
                elif model_name == "lightgbm":
                    # LightGBM returns probabilities directly
                    fraud_prob = float(model.predict(X)[0])
                    confidence = max(fraud_prob, 1 - fraud_prob)
                elif model_name == "xgboost":
                    # XGBoost with DMatrix
                    dmatrix = xgb.DMatrix(X)
                    fraud_prob = float(model.predict(dmatrix)[0])
                    confidence = max(fraud_prob, 1 - fraud_prob)
                else:
                    fraud_prob = 1.0 if prediction == 1 else 0.0
                    confidence = 1.0
            except Exception as e:
                logger.warning(f"Could not get probabilities: {e}")
                fraud_prob = 1.0 if prediction == 1 else 0.0
                confidence = 1.0
        else:
            fraud_prob = 1.0 if prediction == 1 else 0.0
            confidence = 1.0

        # Build result
        result = {
            "prediction": prediction,
            "is_fraud": bool(prediction == 1),
            "fraud_probability": fraud_prob,
            "confidence": confidence,
            "model": model_name,
            "risk_level": self._get_risk_level(fraud_prob)
        }

        return result

    def predict_batch(
        self,
        transactions: List[Dict],
        model_name: str = "lightgbm"
    ) -> List[Dict]:
        """
        Make predictions for multiple transactions.

        Args:
            transactions: List of transaction dicts
            model_name: Model to use

        Returns:
            list: Prediction results for each transaction
        """
        results = []

        for transaction in transactions:
            try:
                result = self.predict(transaction, model_name)
                results.append(result)
            except Exception as e:
                logger.error(f"Prediction error: {e}")
                results.append({
                    "prediction": -1,
                    "is_fraud": False,
                    "fraud_probability": 0.0,
                    "confidence": 0.0,
                    "model": model_name,
                    "risk_level": "error",
                    "error": str(e)
                })

        return results

    def ensemble_predict(
        self,
        transaction: Dict,
        models: Optional[List[str]] = None,
        voting: str = "soft"
    ) -> Dict:
        """
        Ensemble prediction using multiple models.

        Args:
            transaction: Transaction dict
            models: List of model names (default: all loaded models)
            voting: "soft" (avg probabilities) or "hard" (majority vote)

        Returns:
            dict: Ensemble prediction results
        """
        if models is None:
            models = list(self.models.keys())

        # Get predictions from all models
        predictions = []
        probabilities = []

        for model_name in models:
            if model_name in self.models:
                result = self.predict(transaction, model_name)
                predictions.append(result["prediction"])
                probabilities.append(result["fraud_probability"])

        if not predictions:
            raise ValueError("No models available for ensemble")

        # Ensemble logic
        if voting == "soft":
            # Average probabilities
            avg_prob = float(np.mean(probabilities))
            ensemble_prediction = 1 if avg_prob >= 0.5 else 0
        else:
            # Majority vote
            ensemble_prediction = 1 if sum(predictions) > len(predictions) / 2 else 0
            avg_prob = float(sum(predictions)) / len(predictions)

        result = {
            "prediction": ensemble_prediction,
            "is_fraud": bool(ensemble_prediction == 1),
            "fraud_probability": avg_prob,
            "confidence": float(np.std(probabilities)),  # Lower std = higher confidence
            "model": f"ensemble_{voting}",
            "individual_predictions": {
                model: pred for model, pred in zip(models, predictions)
            },
            "individual_probabilities": {
                model: prob for model, prob in zip(models, probabilities)
            },
            "risk_level": self._get_risk_level(avg_prob)
        }

        return result

    def _get_risk_level(self, probability: float) -> str:
        """
        Map fraud probability to risk level.

        Args:
            probability: Fraud probability (0-1)

        Returns:
            str: Risk level ("low", "medium", "high", "critical")
        """
        if probability < 0.25:
            return "low"
        elif probability < 0.5:
            return "medium"
        elif probability < 0.75:
            return "high"
        else:
            return "critical"

    def get_model_info(self, model_name: str) -> Dict:
        """
        Get model metadata and performance info.

        Args:
            model_name: Model name

        Returns:
            dict: Model information
        """
        if model_name not in self.models:
            return {"error": f"Model {model_name} not loaded"}

        info = {
            "name": model_name,
            "loaded": True,
            "metadata": self.metadata.get(model_name, {}),
            "has_preprocessor": self.preprocessors.get(model_name) is not None
        }

        return info


# Global instance
ml_service = MLModelService()
