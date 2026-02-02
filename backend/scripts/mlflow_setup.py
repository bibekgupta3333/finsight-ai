"""
MLflow Experiment Tracking Setup.

Initialize MLflow tracking server and configure experiments
for fraud detection model training and evaluation.
"""

import os
import mlflow
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Paths
BACKEND_DIR = Path(__file__).parent.parent
MLRUNS_DIR = BACKEND_DIR / "mlruns"
MODELS_DIR = BACKEND_DIR / "models"


def setup_mlflow():
    """
    Configure MLflow tracking server with local file store.

    Returns:
        str: Tracking URI
    """
    # Create mlruns directory
    MLRUNS_DIR.mkdir(parents=True, exist_ok=True)

    # Set tracking URI to local file store
    tracking_uri = f"file://{MLRUNS_DIR.absolute()}"
    mlflow.set_tracking_uri(tracking_uri)

    logger.info(f"MLflow tracking URI: {tracking_uri}")
    logger.info(f"MLflow artifacts location: {MLRUNS_DIR}")

    return tracking_uri


def create_experiments():
    """
    Create experiment groups for organized tracking.

    Returns:
        dict: Experiment names and IDs
    """
    experiments = {}

    experiment_configs = [
        ("baseline_models", "RF, XGBoost, LightGBM baseline training"),
        ("model_evaluation", "Model performance evaluation and metrics"),
        ("hyperparameter_tuning", "Optuna and grid search experiments"),
        ("ensemble_models", "Model stacking and blending experiments"),
    ]

    for exp_name, description in experiment_configs:
        try:
            exp_id = mlflow.create_experiment(
                name=exp_name,
                artifact_location=str(MLRUNS_DIR / exp_name)
            )
            experiments[exp_name] = exp_id
            logger.info(f"Created experiment: {exp_name} (ID: {exp_id})")
        except Exception as e:
            # Experiment might already exist
            exp = mlflow.get_experiment_by_name(exp_name)
            if exp:
                experiments[exp_name] = exp.experiment_id
                logger.info(f"Using existing experiment: {exp_name} (ID: {exp.experiment_id})")
            else:
                logger.error(f"Error creating experiment {exp_name}: {e}")

    return experiments


def log_model_training(
    experiment_name: str,
    model_name: str,
    params: dict,
    metrics: dict,
    model=None,
    artifacts: dict = None
):
    """
    Log model training run to MLflow.

    Args:
        experiment_name: Name of experiment
        model_name: Model name (e.g., "random_forest")
        params: Hyperparameters dict
        metrics: Performance metrics dict
        model: Trained model object (optional)
        artifacts: Dict of artifact paths to log (optional)

    Returns:
        str: Run ID
    """
    # Set experiment
    mlflow.set_experiment(experiment_name)

    with mlflow.start_run(run_name=model_name) as run:
        # Log parameters
        for param_name, param_value in params.items():
            mlflow.log_param(param_name, param_value)

        # Log metrics
        for metric_name, metric_value in metrics.items():
            mlflow.log_metric(metric_name, metric_value)

        # Log model
        if model is not None:
            try:
                if model_name.startswith("random_forest"):
                    mlflow.sklearn.log_model(model, "model")
                elif model_name.startswith("xgboost"):
                    mlflow.xgboost.log_model(model, "model")
                elif model_name.startswith("lightgbm"):
                    mlflow.lightgbm.log_model(model, "model")
            except Exception as e:
                logger.warning(f"Could not log model: {e}")

        # Log artifacts (plots, reports, etc.)
        if artifacts:
            for artifact_name, artifact_path in artifacts.items():
                if Path(artifact_path).exists():
                    mlflow.log_artifact(artifact_path, artifact_name)

        # Log tags
        mlflow.set_tags({
            "model_type": model_name.split("_")[0],
            "framework": "sklearn" if "forest" in model_name else model_name.split("_")[0],
            "task": "fraud_detection"
        })

        run_id = run.info.run_id
        logger.info(f"Logged run {run_id} for {model_name}")

        return run_id


def start_tracking_ui(port: int = 5000):
    """
    Start MLflow tracking UI server.

    Args:
        port: Port number (default: 5000)

    Note:
        Run this in a separate terminal:
        cd backend && python -c "from scripts.mlflow_setup import start_tracking_ui; start_tracking_ui()"
        Or use: mlflow ui --backend-store-uri file://./mlruns --port 5000
    """
    logger.info(f"Starting MLflow UI on port {port}...")
    logger.info(f"Access at: http://localhost:{port}")
    logger.info(f"Tracking URI: {mlflow.get_tracking_uri()}")

    # This would block, so instructions provided above
    print("\n" + "="*80)
    print("To start MLflow UI, run in a separate terminal:")
    print(f"  cd {BACKEND_DIR}")
    print(f"  mlflow ui --backend-store-uri file://./mlruns --port {port}")
    print("="*80 + "\n")


def get_best_run(experiment_name: str, metric: str = "f1_score"):
    """
    Get best run from an experiment based on metric.

    Args:
        experiment_name: Name of experiment
        metric: Metric to optimize (default: f1_score)

    Returns:
        mlflow.entities.Run: Best run object
    """
    experiment = mlflow.get_experiment_by_name(experiment_name)
    if not experiment:
        logger.error(f"Experiment {experiment_name} not found")
        return None

    runs = mlflow.search_runs(
        experiment_ids=[experiment.experiment_id],
        order_by=[f"metrics.{metric} DESC"],
        max_results=1
    )

    if runs.empty:
        logger.warning(f"No runs found in {experiment_name}")
        return None

    best_run = runs.iloc[0]
    logger.info(f"Best run in {experiment_name}: {best_run['run_id']}")
    logger.info(f"  {metric}: {best_run[f'metrics.{metric}']}")

    return best_run


if __name__ == "__main__":
    # Setup MLflow
    tracking_uri = setup_mlflow()

    # Create experiments
    experiments = create_experiments()

    # Print summary
    print("\n" + "="*80)
    print("MLFLOW SETUP COMPLETE")
    print("="*80)
    print(f"Tracking URI: {tracking_uri}")
    print(f"\nExperiments created:")
    for exp_name, exp_id in experiments.items():
        print(f"  - {exp_name} (ID: {exp_id})")

    print("\n" + "="*80)
    print("NEXT STEPS:")
    print("="*80)
    print("1. Start MLflow UI:")
    print(f"   cd {BACKEND_DIR}")
    print("   mlflow ui --backend-store-uri file://./mlruns --port 5000")
    print("   Access at: http://localhost:5000")
    print("\n2. Training scripts now log to MLflow automatically")
    print("3. View experiments, metrics, and artifacts in the UI")
    print("="*80 + "\n")
