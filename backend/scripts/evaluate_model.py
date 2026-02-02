"""
Comprehensive Model Evaluation Script.

Evaluates trained ML models with metrics, visualizations, and threshold optimization.
Supports Random Forest, XGBoost, and LightGBM models.
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Dict, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
import joblib
import xgboost as xgb
import lightgbm as lgb
from sklearn.model_selection import cross_val_score, StratifiedKFold
from sklearn.preprocessing import StandardScaler, OneHotEncoder

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))
from utils.metrics import (
    ClassificationMetrics,
    BusinessMetrics,
    ThresholdOptimizer,
    MetricsVisualizer,
    generate_metrics_summary
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Paths
BASE_DIR = Path(__file__).parent.parent.parent
DATA_DIR = BASE_DIR / "data"
MODELS_DIR = BASE_DIR / "backend" / "models"
REPORTS_DIR = BASE_DIR / "backend" / "reports" / "evaluation"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


class ModelEvaluator:
    """Comprehensive model evaluation framework."""
    
    def __init__(
        self,
        model_name: str,
        model_type: str,
        max_samples: int = 100000
    ):
        """
        Initialize evaluator.
        
        Args:
            model_name: Name of model (random_forest, xgboost, lightgbm)
            model_type: Type (rf, xgb, lgb)
            max_samples: Maximum samples for memory efficiency
        """
        self.model_name = model_name
        self.model_type = model_type
        self.max_samples = max_samples
        self.model = None
        self.preprocessor = None
        self.feature_names = None
        
        # Metrics calculators
        self.clf_metrics = ClassificationMetrics()
        self.biz_metrics = BusinessMetrics()
        self.threshold_opt = ThresholdOptimizer()
        self.visualizer = MetricsVisualizer()
        
        logger.info(f"Initialized evaluator for {model_name} ({model_type})")
    
    def load_model(self):
        """Load trained model and artifacts."""
        logger.info("=" * 80)
        logger.info("LOADING MODEL")
        logger.info("=" * 80)
        
        if self.model_type == "rf":
            # Random Forest
            model_path = MODELS_DIR / f"{self.model_name}_v1.pkl"
            preprocessor_path = MODELS_DIR / "preprocessor.pkl"
            feature_names_path = MODELS_DIR / "feature_names.json"
            
            self.model = joblib.load(model_path)
            self.preprocessor = joblib.load(preprocessor_path)
            
            with open(feature_names_path, 'r') as f:
                self.feature_names = json.load(f)
            
            logger.info(f"Loaded Random Forest from {model_path}")
            
        elif self.model_type == "xgb":
            # XGBoost
            model_path = MODELS_DIR / f"{self.model_name}_v1.json"
            preprocessor_path = MODELS_DIR / "xgb_preprocessor_v1.pkl"
            feature_names_path = MODELS_DIR / "xgb_feature_names_v1.json"
            
            self.model = xgb.Booster()
            self.model.load_model(str(model_path))
            self.preprocessor = joblib.load(preprocessor_path)
            
            with open(feature_names_path, 'r') as f:
                self.feature_names = json.load(f)
            
            logger.info(f"Loaded XGBoost from {model_path}")
            
        elif self.model_type == "lgb":
            # LightGBM
            model_path = MODELS_DIR / f"{self.model_name}_v1.txt"
            feature_names_path = MODELS_DIR / "lgb_feature_names_v1.json"
            
            self.model = lgb.Booster(model_file=str(model_path))
            
            with open(feature_names_path, 'r') as f:
                self.feature_names = json.load(f)
            
            logger.info(f"Loaded LightGBM from {model_path}")
        
        logger.info(f"Features: {len(self.feature_names)}")
    
    def load_test_data(self) -> Tuple[pd.DataFrame, np.ndarray]:
        """
        Load temporal test set (never seen during training).
        
        Returns:
            X_test, y_test
        """
        logger.info("=" * 80)
        logger.info("LOADING TEST DATA")
        logger.info("=" * 80)
        
        # Try temporal test set first
        test_path = DATA_DIR / "splits" / "temporal" / "test.csv"
        
        if not test_path.exists():
            # Fallback to regular test split
            test_path = DATA_DIR / "splits" / "test.csv"
            logger.warning(f"Temporal test not found, using {test_path}")
        
        # Load with sampling for memory
        df = pd.read_csv(test_path, nrows=self.max_samples)
        
        logger.info(f"Loaded {len(df):,} test samples from {test_path}")
        logger.info(f"Fraud rate: {df['isFraud'].mean():.4f}")
        
        # Prepare features
        X_test, y_test = self.prepare_features(df)
        
        return X_test, y_test
    
    def prepare_features(self, df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """
        Prepare features for prediction.
        
        Args:
            df: Input dataframe
            
        Returns:
            X, y
        """
        y = df["isFraud"].values
        
        if self.model_type == "lgb":
            # LightGBM uses categorical features natively
            numerical_features = [
                "amount", "oldbalanceOrg", "newbalanceOrig",
                "oldbalanceDest", "newbalanceDest"
            ]
            
            X = df.copy()
            X["balance_diff_orig"] = X["oldbalanceOrg"] - X["newbalanceOrig"]
            X["balance_diff_dest"] = X["oldbalanceDest"] - X["newbalanceDest"]
            X["amount_to_balance_ratio"] = X["amount"] / (X["oldbalanceOrg"] + 1)
            
            numerical_features.extend([
                "balance_diff_orig", "balance_diff_dest", "amount_to_balance_ratio"
            ])
            
            # Categorical feature
            X["type"] = X["type"].astype("category")
            all_features = numerical_features + ["type"]
            X = X[all_features]
            
            # Handle NaN/inf
            for col in numerical_features:
                X[col] = X[col].replace([np.inf, -np.inf], np.nan).fillna(0)
            
            # Return as DataFrame for LightGBM (it needs categorical dtype)
            return X, y
        
        else:
            # RF and XGBoost use preprocessor
            numerical_features = [
                "amount", "oldbalanceOrg", "newbalanceOrig",
                "oldbalanceDest", "newbalanceDest"
            ]
            
            X = df.copy()
            X["balance_diff_orig"] = X["oldbalanceOrg"] - X["newbalanceOrig"]
            X["balance_diff_dest"] = X["oldbalanceDest"] - X["newbalanceDest"]
            X["amount_to_balance_ratio"] = X["amount"] / (X["oldbalanceOrg"] + 1)
            
            numerical_features.extend([
                "balance_diff_orig", "balance_diff_dest", "amount_to_balance_ratio"
            ])
            
            # Handle NaN/inf
            for col in numerical_features:
                X[col] = X[col].replace([np.inf, -np.inf], np.nan).fillna(0)
            
            X_num = X[numerical_features]
            
            # One-hot encode categorical
            X_cat = pd.get_dummies(X["type"], prefix="type")
            
            # Combine
            X_combined = pd.concat([X_num, X_cat], axis=1)
            
            # Ensure all expected columns exist (in correct order)
            for col in self.feature_names:
                if col not in X_combined.columns:
                    X_combined[col] = 0
            
            X_combined = X_combined[self.feature_names]
            
            # Apply preprocessing
            if isinstance(self.preprocessor, dict):
                # Preprocessor is dict with scaler (trained on all features)
                X_transformed = self.preprocessor['scaler'].transform(X_combined)
                # For RF, return as DataFrame with column names
                if self.model_type == "rf":
                    X_transformed = pd.DataFrame(X_transformed, columns=self.feature_names)
            else:
                # Preprocessor is a ColumnTransformer or Pipeline
                X_transformed = self.preprocessor.transform(X_combined)
                if self.model_type == "rf":
                    X_transformed = pd.DataFrame(X_transformed, columns=self.feature_names)
            
            return X_transformed, y
    
    def predict(self, X: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Make predictions.
        
        Args:
            X: Feature matrix (or DataFrame for some models)
            
        Returns:
            y_pred (binary), y_pred_proba (probabilities)
        """
        if self.model_type == "rf":
            # Random Forest expects DataFrame with column names
            if not isinstance(X, pd.DataFrame):
                X_df = pd.DataFrame(X, columns=self.feature_names)
            else:
                X_df = X
            
            y_pred_proba = self.model.predict_proba(X_df)[:, 1]
            y_pred = self.model.predict(X_df)
            
        elif self.model_type == "xgb":
            dmatrix = xgb.DMatrix(X, feature_names=self.feature_names)
            y_pred_proba = self.model.predict(dmatrix)
            y_pred = (y_pred_proba > 0.5).astype(int)
            
        elif self.model_type == "lgb":
            y_pred_proba = self.model.predict(X)
            y_pred = (y_pred_proba > 0.5).astype(int)
        
        return y_pred, y_pred_proba
    
    def evaluate_test_set(
        self,
        X_test: np.ndarray,
        y_test: np.ndarray
    ) -> Dict:
        """
        Comprehensive evaluation on test set.
        
        Args:
            X_test: Test features
            y_test: Test labels
            
        Returns:
            Dictionary of results
        """
        logger.info("=" * 80)
        logger.info("EVALUATING ON TEST SET")
        logger.info("=" * 80)
        
        # Predictions
        y_pred, y_pred_proba = self.predict(X_test)
        
        # Classification metrics
        metrics = self.clf_metrics.calculate_all_metrics(y_test, y_pred, y_pred_proba)
        
        # Business metrics
        cost_fp = 5.0  # $5 per manual review
        cost_fn = 100.0  # $100 per missed fraud
        loss_metrics = self.biz_metrics.calculate_expected_loss(
            y_test, y_pred, cost_fp, cost_fn
        )
        
        # Precision at k
        precision_1pct = self.biz_metrics.precision_at_k(y_test, y_pred_proba, k=0.01)
        precision_5pct = self.biz_metrics.precision_at_k(y_test, y_pred_proba, k=0.05)
        
        # Threshold optimization
        opt_threshold_f1, best_f1 = self.threshold_opt.find_optimal_threshold_f1(
            y_test, y_pred_proba
        )
        opt_threshold_cost, min_cost = self.threshold_opt.find_optimal_threshold_cost(
            y_test, y_pred_proba, cost_fp, cost_fn
        )
        risk_thresholds = self.threshold_opt.define_risk_thresholds(
            y_test, y_pred_proba, target_recall=0.95
        )
        
        # Combine all metrics
        results = {
            "model_name": self.model_name,
            "model_type": self.model_type,
            "test_samples": len(y_test),
            "fraud_samples": int(y_test.sum()),
            "fraud_rate": float(y_test.mean()),
            
            **metrics,
            **loss_metrics,
            
            "precision_at_1pct": float(precision_1pct),
            "precision_at_5pct": float(precision_5pct),
            
            "optimal_threshold_f1": float(opt_threshold_f1),
            "best_f1_at_optimal": float(best_f1),
            "optimal_threshold_cost": float(opt_threshold_cost),
            "min_cost_at_optimal": float(min_cost),
            
            **risk_thresholds
        }
        
        # Print summary
        print(generate_metrics_summary(metrics))
        
        logger.info("\n💰 Business Metrics:")
        logger.info(f"  Total Cost: ${loss_metrics['total_cost']:,.2f}")
        logger.info(f"  Cost per Transaction: ${loss_metrics['cost_per_transaction']:.2f}")
        logger.info(f"  Precision @ 1%: {precision_1pct:.4f}")
        logger.info(f"  Precision @ 5%: {precision_5pct:.4f}")
        
        logger.info("\n🎯 Optimal Thresholds:")
        logger.info(f"  F1-Optimal: {opt_threshold_f1:.3f} (F1={best_f1:.4f})")
        logger.info(f"  Cost-Optimal: {opt_threshold_cost:.3f} (Cost=${min_cost:,.2f})")
        logger.info(f"  Approve: < {risk_thresholds['approve_threshold']:.2f}")
        logger.info(f"  Review: {risk_thresholds['approve_threshold']:.2f} - {risk_thresholds['review_threshold']:.2f}")
        logger.info(f"  Block: > {risk_thresholds['block_threshold']:.2f}")
        
        return results
    
    def generate_visualizations(
        self,
        X_test: np.ndarray,
        y_test: np.ndarray,
        save_dir: Path
    ):
        """
        Generate all evaluation visualizations.
        
        Args:
            X_test: Test features
            y_test: Test labels
            save_dir: Directory to save plots
        """
        logger.info("=" * 80)
        logger.info("GENERATING VISUALIZATIONS")
        logger.info("=" * 80)
        
        save_dir.mkdir(parents=True, exist_ok=True)
        
        y_pred, y_pred_proba = self.predict(X_test)
        
        # Confusion matrix (absolute)
        cm_path = save_dir / f"{self.model_name}_confusion_matrix.png"
        self.visualizer.plot_confusion_matrix(
            y_test, y_pred, save_path=cm_path, normalize=False
        )
        logger.info(f"  ✓ Saved confusion matrix: {cm_path}")
        
        # Confusion matrix (normalized)
        cm_norm_path = save_dir / f"{self.model_name}_confusion_matrix_normalized.png"
        self.visualizer.plot_confusion_matrix(
            y_test, y_pred, save_path=cm_norm_path, normalize=True
        )
        logger.info(f"  ✓ Saved normalized confusion matrix: {cm_norm_path}")
        
        # ROC curve
        roc_path = save_dir / f"{self.model_name}_roc_curve.png"
        self.visualizer.plot_roc_curve(
            y_test, y_pred_proba, save_path=roc_path, model_name=self.model_name
        )
        logger.info(f"  ✓ Saved ROC curve: {roc_path}")
        
        # Precision-Recall curve
        pr_path = save_dir / f"{self.model_name}_pr_curve.png"
        self.visualizer.plot_precision_recall_curve(
            y_test, y_pred_proba, save_path=pr_path, model_name=self.model_name
        )
        logger.info(f"  ✓ Saved PR curve: {pr_path}")
        
        # Threshold analysis
        threshold_path = save_dir / f"{self.model_name}_threshold_analysis.png"
        self.visualizer.plot_threshold_analysis(
            y_test, y_pred_proba, save_path=threshold_path
        )
        logger.info(f"  ✓ Saved threshold analysis: {threshold_path}")
    
    def cross_validation_evaluation(
        self,
        X: np.ndarray,
        y: np.ndarray,
        cv: int = 5
    ) -> Dict:
        """
        Perform cross-validation evaluation.
        
        Args:
            X: Features
            y: Labels
            cv: Number of folds
            
        Returns:
            CV results dictionary
        """
        logger.info("=" * 80)
        logger.info(f"CROSS-VALIDATION ({cv}-FOLD STRATIFIED)")
        logger.info("=" * 80)
        
        if self.model_type == "rf":
            # Random Forest supports sklearn CV
            cv_splitter = StratifiedKFold(n_splits=cv, shuffle=True, random_state=42)
            
            f1_scores = cross_val_score(
                self.model, X, y, cv=cv_splitter, scoring='f1', n_jobs=2
            )
            precision_scores = cross_val_score(
                self.model, X, y, cv=cv_splitter, scoring='precision', n_jobs=2
            )
            recall_scores = cross_val_score(
                self.model, X, y, cv=cv_splitter, scoring='recall', n_jobs=2
            )
            
            results = {
                "f1_mean": float(f1_scores.mean()),
                "f1_std": float(f1_scores.std()),
                "precision_mean": float(precision_scores.mean()),
                "precision_std": float(precision_scores.std()),
                "recall_mean": float(recall_scores.mean()),
                "recall_std": float(recall_scores.std()),
                "f1_scores": f1_scores.tolist(),
                "precision_scores": precision_scores.tolist(),
                "recall_scores": recall_scores.tolist()
            }
            
            logger.info(f"  F1-Score:  {results['f1_mean']:.4f} ± {results['f1_std']:.4f}")
            logger.info(f"  Precision: {results['precision_mean']:.4f} ± {results['precision_std']:.4f}")
            logger.info(f"  Recall:    {results['recall_mean']:.4f} ± {results['recall_std']:.4f}")
            
            return results
        
        else:
            logger.info("  ⚠️ Cross-validation skipped (XGBoost/LightGBM require custom CV)")
            return {"message": "CV not implemented for this model type"}
    
    def save_evaluation_report(self, results: Dict, save_path: Path):
        """
        Save evaluation report as JSON.
        
        Args:
            results: Evaluation results
            save_path: Path to save JSON
        """
        with open(save_path, 'w') as f:
            json.dump(results, f, indent=2)
        
        logger.info(f"\n📄 Saved evaluation report: {save_path}")


def main():
    """Main evaluation pipeline."""
    parser = argparse.ArgumentParser(description="Evaluate trained ML models")
    parser.add_argument(
        "--model",
        type=str,
        required=True,
        choices=["random_forest", "xgboost", "lightgbm", "all"],
        help="Model to evaluate (or 'all' for all models)"
    )
    parser.add_argument(
        "--max-samples",
        type=int,
        default=100000,
        help="Maximum test samples (default: 100000)"
    )
    parser.add_argument(
        "--skip-cv",
        action="store_true",
        help="Skip cross-validation"
    )
    parser.add_argument(
        "--skip-viz",
        action="store_true",
        help="Skip visualization generation"
    )
    
    args = parser.parse_args()
    
    # Model configurations
    models_to_evaluate = []
    if args.model == "all":
        models_to_evaluate = [
            ("random_forest", "rf"),
            ("xgboost", "xgb"),
            ("lightgbm", "lgb")
        ]
    elif args.model == "random_forest":
        models_to_evaluate = [("random_forest", "rf")]
    elif args.model == "xgboost":
        models_to_evaluate = [("xgboost", "xgb")]
    elif args.model == "lightgbm":
        models_to_evaluate = [("lightgbm", "lgb")]
    
    # Evaluate each model
    for model_name, model_type in models_to_evaluate:
        logger.info("\n" + "=" * 80)
        logger.info(f"EVALUATING: {model_name.upper()}")
        logger.info("=" * 80 + "\n")
        
        try:
            # Initialize evaluator
            evaluator = ModelEvaluator(
                model_name=model_name,
                model_type=model_type,
                max_samples=args.max_samples
            )
            
            # Load model
            evaluator.load_model()
            
            # Load test data
            X_test, y_test = evaluator.load_test_data()
            
            # Evaluate
            results = evaluator.evaluate_test_set(X_test, y_test)
            
            # Cross-validation (optional)
            if not args.skip_cv and model_type == "rf":
                cv_results = evaluator.cross_validation_evaluation(X_test, y_test, cv=3)
                results["cross_validation"] = cv_results
            
            # Visualizations
            if not args.skip_viz:
                viz_dir = REPORTS_DIR / model_name
                evaluator.generate_visualizations(X_test, y_test, viz_dir)
            
            # Save report
            report_path = REPORTS_DIR / f"{model_name}_evaluation_report.json"
            evaluator.save_evaluation_report(results, report_path)
            
            logger.info(f"\n✅ {model_name.upper()} evaluation complete!\n")
        
        except Exception as e:
            logger.error(f"❌ Error evaluating {model_name}: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    logger.info("=" * 80)
    logger.info("EVALUATION COMPLETE")
    logger.info(f"Reports saved to: {REPORTS_DIR}")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()
