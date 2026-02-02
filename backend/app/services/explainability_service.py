"""
Model Explainability Service using SHAP.

Provides feature importance and SHAP values for fraud detection models.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
import shap
from matplotlib import pyplot as plt

logger = logging.getLogger(__name__)

# Paths
BACKEND_DIR = Path(__file__).parent.parent.parent
REPORTS_DIR = BACKEND_DIR / "reports" / "explainability"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


class ExplainabilityService:
    """
    SHAP-based explainability service.

    Provides feature importance, SHAP values, and visualizations
    for fraud detection model predictions.
    """

    def __init__(self):
        """Initialize explainability service."""
        self.explainers = {}
        self.background_data = {}
        logger.info("Explainability Service initialized")

    def create_explainer(
        self,
        model,
        model_name: str,
        background_data: pd.DataFrame,
        model_type: str = "tree"
    ):
        """
        Create SHAP explainer for a model.

        Args:
            model: Trained model
            model_name: Model identifier
            background_data: Background dataset for SHAP
            model_type: Model type ("tree", "linear", "kernel")
        """
        try:
            # Select appropriate explainer
            if model_type == "tree":
                # TreeExplainer for tree-based models (RF, XGBoost, LightGBM)
                explainer = shap.TreeExplainer(
                    model,
                    background_data,
                    feature_perturbation="tree_path_dependent"
                )
            elif model_type == "linear":
                explainer = shap.LinearExplainer(model, background_data)
            else:
                # KernelExplainer for any model (slower but universal)
                explainer = shap.KernelExplainer(
                    model.predict_proba,
                    background_data.sample(min(100, len(background_data)))
                )

            self.explainers[model_name] = explainer
            self.background_data[model_name] = background_data

            logger.info(f"Created SHAP explainer for {model_name}")

        except Exception as e:
            logger.error(f"Failed to create explainer for {model_name}: {e}")
            raise

    def explain_prediction(
        self,
        features: pd.DataFrame,
        model_name: str
    ) -> Dict:
        """
        Get SHAP values for a prediction.

        Args:
            features: Feature DataFrame (single row or multiple)
            model_name: Model identifier

        Returns:
            dict: SHAP values and feature importance
        """
        if model_name not in self.explainers:
            raise ValueError(f"No explainer found for {model_name}")

        explainer = self.explainers[model_name]

        # Compute SHAP values
        shap_values = explainer.shap_values(features)

        # Handle binary classification (shap_values is list of 2 arrays)
        if isinstance(shap_values, list):
            # Use fraud class (index 1) SHAP values
            shap_values_fraud = shap_values[1]
        else:
            shap_values_fraud = shap_values

        # For single prediction
        if len(features) == 1:
            feature_names = features.columns.tolist()
            feature_values = features.iloc[0].values
            shap_vals = shap_values_fraud[0]

            # Sort by absolute SHAP value
            importance_order = np.argsort(np.abs(shap_vals))[::-1]

            explanation = {
                "feature_importance": [
                    {
                        "feature": feature_names[i],
                        "value": float(feature_values[i]),
                        "shap_value": float(shap_vals[i]),
                        "importance": float(np.abs(shap_vals[i]))
                    }
                    for i in importance_order
                ],
                "base_value": float(explainer.expected_value[1] if isinstance(explainer.expected_value, list) else explainer.expected_value),
                "prediction_value": float(np.sum(shap_vals) + (explainer.expected_value[1] if isinstance(explainer.expected_value, list) else explainer.expected_value))
            }

            return explanation

        # For batch predictions
        else:
            return {
                "shap_values": shap_values_fraud.tolist(),
                "feature_names": features.columns.tolist(),
                "base_value": float(explainer.expected_value[1] if isinstance(explainer.expected_value, list) else explainer.expected_value),
                "sample_count": len(features)
            }

    def get_global_importance(
        self,
        model_name: str,
        top_k: int = 10
    ) -> Dict:
        """
        Get global feature importance for a model.

        Args:
            model_name: Model identifier
            top_k: Number of top features to return

        Returns:
            dict: Global feature importance
        """
        if model_name not in self.explainers:
            raise ValueError(f"No explainer found for {model_name}")

        if model_name not in self.background_data:
            raise ValueError(f"No background data for {model_name}")

        explainer = self.explainers[model_name]
        background = self.background_data[model_name]

        # Compute SHAP values for background data
        shap_values = explainer.shap_values(background)

        # Handle binary classification
        if isinstance(shap_values, list):
            shap_values_fraud = shap_values[1]
        else:
            shap_values_fraud = shap_values

        # Calculate mean absolute SHAP value for each feature
        mean_abs_shap = np.abs(shap_values_fraud).mean(axis=0)

        # Get feature names
        feature_names = background.columns.tolist()

        # Sort by importance
        importance_order = np.argsort(mean_abs_shap)[::-1][:top_k]

        importance = {
            "features": [
                {
                    "feature": feature_names[i],
                    "importance": float(mean_abs_shap[i]),
                    "rank": rank + 1
                }
                for rank, i in enumerate(importance_order)
            ],
            "model": model_name,
            "sample_size": len(background)
        }

        return importance

    def plot_waterfall(
        self,
        features: pd.DataFrame,
        model_name: str,
        max_display: int = 10,
        save_path: Optional[Path] = None
    ) -> str:
        """
        Create SHAP waterfall plot for a single prediction.

        Args:
            features: Single feature row
            model_name: Model identifier
            max_display: Max features to display
            save_path: Path to save plot (optional)

        Returns:
            str: Path to saved plot
        """
        if model_name not in self.explainers:
            raise ValueError(f"No explainer found for {model_name}")

        explainer = self.explainers[model_name]

        # Compute SHAP values
        shap_values = explainer(features)

        # Create waterfall plot
        fig, ax = plt.subplots(figsize=(10, 6))
        shap.plots.waterfall(shap_values[0], max_display=max_display, show=False)

        # Save plot
        if save_path is None:
            save_path = REPORTS_DIR / f"{model_name}_waterfall.png"

        plt.tight_layout()
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        plt.close()

        logger.info(f"Saved waterfall plot: {save_path}")
        return str(save_path)

    def plot_force(
        self,
        features: pd.DataFrame,
        model_name: str,
        save_path: Optional[Path] = None
    ) -> str:
        """
        Create SHAP force plot for a single prediction.

        Args:
            features: Single feature row
            model_name: Model identifier
            save_path: Path to save plot (optional)

        Returns:
            str: Path to saved HTML
        """
        if model_name not in self.explainers:
            raise ValueError(f"No explainer found for {model_name}")

        explainer = self.explainers[model_name]

        # Compute SHAP values
        shap_values = explainer(features)

        # Create force plot
        if save_path is None:
            save_path = REPORTS_DIR / f"{model_name}_force.html"

        force_plot = shap.plots.force(
            shap_values[0],
            matplotlib=False,
            show=False
        )

        # Save as HTML
        shap.save_html(str(save_path), force_plot)

        logger.info(f"Saved force plot: {save_path}")
        return str(save_path)

    def plot_summary(
        self,
        model_name: str,
        plot_type: str = "bar",
        max_display: int = 10,
        save_path: Optional[Path] = None
    ) -> str:
        """
        Create SHAP summary plot for global feature importance.

        Args:
            model_name: Model identifier
            plot_type: Plot type ("bar", "dot", "violin")
            max_display: Max features to display
            save_path: Path to save plot (optional)

        Returns:
            str: Path to saved plot
        """
        if model_name not in self.explainers:
            raise ValueError(f"No explainer found for {model_name}")

        if model_name not in self.background_data:
            raise ValueError(f"No background data for {model_name}")

        explainer = self.explainers[model_name]
        background = self.background_data[model_name]

        # Compute SHAP values
        shap_values = explainer(background)

        # Create summary plot
        fig, ax = plt.subplots(figsize=(10, 8))

        if plot_type == "bar":
            shap.plots.bar(shap_values, max_display=max_display, show=False)
        elif plot_type == "dot":
            shap.plots.beeswarm(shap_values, max_display=max_display, show=False)
        elif plot_type == "violin":
            shap.summary_plot(
                shap_values.values,
                background,
                plot_type="violin",
                max_display=max_display,
                show=False
            )

        # Save plot
        if save_path is None:
            save_path = REPORTS_DIR / f"{model_name}_summary_{plot_type}.png"

        plt.tight_layout()
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        plt.close()

        logger.info(f"Saved summary plot: {save_path}")
        return str(save_path)

    def explain_batch(
        self,
        features: pd.DataFrame,
        model_name: str,
        top_k: int = 5
    ) -> List[Dict]:
        """
        Explain multiple predictions.

        Args:
            features: Feature DataFrame (multiple rows)
            model_name: Model identifier
            top_k: Number of top features per prediction

        Returns:
            list: Explanations for each prediction
        """
        if model_name not in self.explainers:
            raise ValueError(f"No explainer found for {model_name}")

        explainer = self.explainers[model_name]

        # Compute SHAP values
        shap_values = explainer.shap_values(features)

        # Handle binary classification
        if isinstance(shap_values, list):
            shap_values_fraud = shap_values[1]
        else:
            shap_values_fraud = shap_values

        feature_names = features.columns.tolist()
        explanations = []

        for i in range(len(features)):
            feature_vals = features.iloc[i].values
            shap_vals = shap_values_fraud[i]

            # Sort by absolute SHAP value
            importance_order = np.argsort(np.abs(shap_vals))[::-1][:top_k]

            explanation = {
                "index": i,
                "top_features": [
                    {
                        "feature": feature_names[idx],
                        "value": float(feature_vals[idx]),
                        "shap_value": float(shap_vals[idx]),
                        "importance": float(np.abs(shap_vals[idx]))
                    }
                    for idx in importance_order
                ]
            }

            explanations.append(explanation)

        return explanations


# Global instance
explainability_service = ExplainabilityService()
