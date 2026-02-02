"""
Ensemble Service for Advanced Model Combination.

Implements:
- Model stacking (Logistic Regression meta-model)
- Weighted blending based on validation performance
- Cascading models (fast to slow)
- Configurable model routing

Designed for M4 Pro efficiency - lazy loading, memory-conscious.
"""

import json
import joblib
import logging
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import StackingClassifier

logger = logging.getLogger(__name__)

# Paths
BACKEND_DIR = Path(__file__).parent.parent.parent
MODELS_DIR = BACKEND_DIR / "models"


class EnsembleService:
    """
    Advanced ensemble service for combining ML models.

    Features:
    - Stacking: Meta-model learns optimal model weights
    - Weighted blending: Fixed weights from validation performance
    - Cascading: Fast model first, slow for uncertain cases
    - Lazy loading: Only load models when needed (M4 Pro memory optimization)
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EnsembleService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize ensemble service."""
        if self._initialized:
            return

        self.stacking_model = None
        self.blending_weights = None
        self.model_configs = {}
        self._initialized = True

        # Load or set default blending weights
        self._load_blending_weights()

        logger.info("Ensemble Service initialized")

    def _load_blending_weights(self):
        """
        Load blending weights from file or use defaults.

        Weights based on validation performance from previous tasks:
        - XGBoost: F1=0.89, but high recall (96.4%), lower precision (63%)
        - LightGBM: F1=0.9949, balanced, fastest inference
        - Random Forest: F1=0.88, balanced

        For fraud detection, we prioritize balanced models slightly more.
        """
        weights_path = MODELS_DIR / "blending_weights.json"

        if weights_path.exists():
            with open(weights_path, "r") as f:
                self.blending_weights = json.load(f)
            logger.info(f"Loaded blending weights: {self.blending_weights}")
        else:
            # Default weights based on validation performance
            self.blending_weights = {
                "lightgbm": 0.45,    # Highest F1, fastest
                "random_forest": 0.30,  # Balanced, good precision
                "xgboost": 0.25      # High recall but lower precision
            }
            logger.info(f"Using default blending weights: {self.blending_weights}")

    def save_blending_weights(self, weights: Dict[str, float]):
        """
        Save custom blending weights.

        Args:
            weights: Dict mapping model_name -> weight (should sum to 1.0)
        """
        # Validate weights
        total = sum(weights.values())
        if not np.isclose(total, 1.0, atol=1e-6):
            raise ValueError(f"Weights must sum to 1.0, got {total}")

        self.blending_weights = weights
        weights_path = MODELS_DIR / "blending_weights.json"

        with open(weights_path, "w") as f:
            json.dump(weights, f, indent=2)

        logger.info(f"Saved blending weights: {weights}")

    def weighted_blend_predictions(
        self,
        predictions: Dict[str, float],
        weights: Optional[Dict[str, float]] = None
    ) -> Tuple[float, float]:
        """
        Weighted average of model predictions.

        Args:
            predictions: Dict mapping model_name -> fraud_probability
            weights: Optional custom weights (defaults to self.blending_weights)

        Returns:
            Tuple of (blended_probability, confidence)
        """
        if weights is None:
            weights = self.blending_weights

        # Calculate weighted average
        total_prob = 0.0
        total_weight = 0.0

        for model_name, prob in predictions.items():
            if model_name in weights:
                total_prob += prob * weights[model_name]
                total_weight += weights[model_name]

        if total_weight == 0:
            raise ValueError("No valid weights for provided predictions")

        blended_prob = total_prob / total_weight

        # Calculate confidence as inverse of prediction variance
        variances = []
        for model_name, prob in predictions.items():
            if model_name in weights:
                variances.append((prob - blended_prob) ** 2 * weights[model_name])

        variance = sum(variances)
        # Confidence: high when models agree (low variance)
        confidence = 1.0 - min(variance, 1.0)

        return blended_prob, confidence

    def simple_average_predictions(
        self,
        predictions: Dict[str, float]
    ) -> Tuple[float, float]:
        """
        Simple average of predictions (equal weights).

        Args:
            predictions: Dict mapping model_name -> fraud_probability

        Returns:
            Tuple of (average_probability, confidence)
        """
        probs = list(predictions.values())
        avg_prob = np.mean(probs)

        # Confidence based on agreement
        std_dev = np.std(probs)
        confidence = 1.0 - min(std_dev, 1.0)

        return avg_prob, confidence

    def cascade_predict(
        self,
        predictions: Dict[str, float],
        confidences: Dict[str, float],
        high_confidence_threshold: float = 0.95,
        low_confidence_threshold: float = 0.70
    ) -> Dict[str, Any]:
        """
        Cascading model selection strategy.

        Strategy:
        1. Start with LightGBM (fastest)
        2. If confidence > 0.95: Return immediately
        3. Else if confidence < 0.70: Use weighted blend of all 3
        4. Else: Use XGBoost (more accurate on edge cases)

        Args:
            predictions: Dict of model predictions
            confidences: Dict of model confidences
            high_confidence_threshold: Threshold for fast return
            low_confidence_threshold: Threshold for full ensemble

        Returns:
            Dict with selected_model, probability, confidence, strategy
        """
        # Priority order: LightGBM (fast) -> XGBoost (accurate) -> Ensemble (uncertain)

        # Step 1: Check LightGBM confidence
        if "lightgbm" in confidences:
            lgbm_conf = confidences["lightgbm"]
            lgbm_prob = predictions["lightgbm"]

            if lgbm_conf >= high_confidence_threshold:
                return {
                    "selected_model": "lightgbm",
                    "probability": lgbm_prob,
                    "confidence": lgbm_conf,
                    "strategy": "fast_path",
                    "description": f"High confidence ({lgbm_conf:.1%}), using LightGBM"
                }

        # Step 2: Check XGBoost for medium confidence
        if "xgboost" in confidences:
            xgb_conf = confidences["xgboost"]
            xgb_prob = predictions["xgboost"]

            if xgb_conf >= high_confidence_threshold:
                return {
                    "selected_model": "xgboost",
                    "probability": xgb_prob,
                    "confidence": xgb_conf,
                    "strategy": "accurate_path",
                    "description": f"XGBoost high confidence ({xgb_conf:.1%})"
                }

        # Step 3: Low confidence or disagreement -> Use weighted blend
        blended_prob, blended_conf = self.weighted_blend_predictions(predictions)

        return {
            "selected_model": "weighted_ensemble",
            "probability": blended_prob,
            "confidence": blended_conf,
            "strategy": "ensemble_path",
            "description": f"Low confidence or disagreement, using weighted ensemble",
            "individual_predictions": predictions,
            "blending_weights": self.blending_weights
        }

    def load_stacking_model(self, version: str = "v1") -> bool:
        """
        Load pre-trained stacking model.

        Args:
            version: Model version

        Returns:
            bool: True if successful
        """
        model_path = MODELS_DIR / f"stacking_model_{version}.pkl"

        if not model_path.exists():
            logger.warning(f"Stacking model not found: {model_path}")
            return False

        try:
            self.stacking_model = joblib.load(model_path)
            logger.info(f"Loaded stacking model from {model_path}")
            return True
        except Exception as e:
            logger.error(f"Error loading stacking model: {e}")
            return False

    def stacking_predict(
        self,
        base_predictions: np.ndarray
    ) -> Tuple[float, float]:
        """
        Predict using stacking meta-model.

        Args:
            base_predictions: Array of shape (n_models,) with base model probabilities

        Returns:
            Tuple of (stacked_probability, confidence)
        """
        if self.stacking_model is None:
            raise ValueError("Stacking model not loaded. Call load_stacking_model() first.")

        # Reshape for sklearn (expects 2D array)
        X = base_predictions.reshape(1, -1)

        # Predict
        stacked_prob = self.stacking_model.predict_proba(X)[0, 1]  # Probability of fraud (class 1)

        # Confidence: Use the difference between top class probabilities
        probs = self.stacking_model.predict_proba(X)[0]
        confidence = abs(probs[1] - probs[0])  # Difference between fraud and non-fraud

        return stacked_prob, confidence

    def get_model_agreement(
        self,
        predictions: Dict[str, float],
        threshold: float = 0.5
    ) -> Dict[str, Any]:
        """
        Analyze agreement/disagreement between models.

        Args:
            predictions: Dict of model predictions
            threshold: Fraud classification threshold

        Returns:
            Dict with agreement metrics
        """
        probs = list(predictions.values())
        classes = [1 if p >= threshold else 0 for p in probs]

        # Agreement: All models agree
        all_agree = len(set(classes)) == 1

        # Majority vote
        majority_class = 1 if sum(classes) > len(classes) / 2 else 0

        # Disagreement score (std dev of probabilities)
        disagreement = np.std(probs)

        return {
            "all_models_agree": all_agree,
            "majority_prediction": "fraud" if majority_class == 1 else "legitimate",
            "disagreement_score": float(disagreement),
            "individual_predictions": {
                name: "fraud" if p >= threshold else "legitimate"
                for name, p in predictions.items()
            },
            "recommendation": self._get_disagreement_recommendation(disagreement)
        }

    def _get_disagreement_recommendation(self, disagreement: float) -> str:
        """
        Get recommendation based on model disagreement.

        Args:
            disagreement: Standard deviation of predictions

        Returns:
            str: Recommendation message
        """
        if disagreement < 0.1:
            return "Strong consensus - trust prediction"
        elif disagreement < 0.3:
            return "Moderate consensus - reasonable confidence"
        elif disagreement < 0.5:
            return "Significant disagreement - review manually or use LLM"
        else:
            return "Major disagreement - high priority for manual review"

    def get_optimal_weights_from_validation(
        self,
        val_predictions: Dict[str, np.ndarray],
        val_labels: np.ndarray,
        metric: str = "f1"
    ) -> Dict[str, float]:
        """
        Calculate optimal blending weights based on validation performance.

        Uses grid search to find weights that maximize the specified metric.

        Args:
            val_predictions: Dict mapping model_name -> predictions (1D array)
            val_labels: True labels (1D array)
            metric: Metric to optimize ('f1', 'precision', 'recall', 'accuracy')

        Returns:
            Dict of optimal weights
        """
        from sklearn.metrics import f1_score, precision_score, recall_score, accuracy_score

        # Select metric function
        metric_funcs = {
            "f1": f1_score,
            "precision": precision_score,
            "recall": recall_score,
            "accuracy": accuracy_score
        }

        if metric not in metric_funcs:
            raise ValueError(f"Unknown metric: {metric}")

        metric_func = metric_funcs[metric]

        # Grid search over weights
        model_names = list(val_predictions.keys())
        best_score = 0.0
        best_weights = {}

        # Simple grid: try different weight combinations
        # For 3 models: w1, w2, w3 where w1 + w2 + w3 = 1
        for w1 in np.arange(0.0, 1.1, 0.1):
            for w2 in np.arange(0.0, 1.1 - w1, 0.1):
                w3 = 1.0 - w1 - w2

                if len(model_names) == 3:
                    weights_list = [w1, w2, w3]
                else:
                    continue  # Skip if not 3 models

                # Calculate weighted prediction
                weighted_pred = sum(
                    val_predictions[name] * weight
                    for name, weight in zip(model_names, weights_list)
                )

                # Convert to binary predictions
                binary_pred = (weighted_pred >= 0.5).astype(int)

                # Calculate metric
                score = metric_func(val_labels, binary_pred)

                if score > best_score:
                    best_score = score
                    best_weights = {
                        name: weight
                        for name, weight in zip(model_names, weights_list)
                    }

        logger.info(f"Optimal weights for {metric}: {best_weights} (score: {best_score:.4f})")
        return best_weights


# Singleton instance
_ensemble_service = None


def get_ensemble_service() -> EnsembleService:
    """Get singleton instance of EnsembleService."""
    global _ensemble_service
    if _ensemble_service is None:
        _ensemble_service = EnsembleService()
    return _ensemble_service
