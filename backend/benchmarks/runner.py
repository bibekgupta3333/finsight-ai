"""
Benchmark Runner.

Orchestrates benchmark execution:
1. Load configuration
2. Initialize baselines
3. Load test datasets
4. Run evaluations
5. Collect metrics
6. Generate reports

Usage:
    from benchmarks.runner import BenchmarkRunner

    runner = BenchmarkRunner("benchmarks/config.yaml")
    results = runner.run()
    report = runner.generate_report(results)
"""

import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import yaml

from .baselines import create_baseline, BaselineEvaluator, PredictionResult

logger = logging.getLogger(__name__)


class BenchmarkRunner:
    """Orchestrates benchmark execution."""

    def __init__(self, config_path: str = "benchmarks/config.yaml"):
        """
        Initialize benchmark runner.

        Args:
            config_path: Path to configuration file
        """
        self.config_path = Path(config_path)
        self.config = None
        self.baselines: Dict[str, BaselineEvaluator] = {}
        self.results = []

        # Load configuration
        self._load_config()

    def _load_config(self):
        """Load YAML configuration."""
        try:
            with open(self.config_path, "r") as f:
                self.config = yaml.safe_load(f)
            logger.info(f"Loaded config from {self.config_path}")
        except Exception as e:
            logger.exception(f"Failed to load config: {e}")
            raise

    def initialize_baselines(self) -> Dict[str, bool]:
        """
        Initialize all enabled baselines.

        Returns:
            dict: Baseline name -> success status
        """
        status = {}

        baseline_configs = self.config.get("baselines", [])
        for baseline_config in baseline_configs:
            name = baseline_config.get("name")

            if not baseline_config.get("enabled", True):
                logger.info(f"Skipping disabled baseline: {name}")
                status[name] = False
                continue

            logger.info(f"Initializing baseline: {name}")
            baseline = create_baseline(baseline_config)

            if baseline:
                self.baselines[name] = baseline
                status[name] = True
                logger.info(f"✓ Baseline ready: {name}")
            else:
                status[name] = False
                logger.warning(f"✗ Failed to initialize: {name}")

        return status

    def _load_test_dataset(self, dataset_config: Dict) -> List[Dict]:
        """
        Load test dataset from configuration.

        Args:
            dataset_config: Dataset configuration dict

        Returns:
            list: Test transactions with expected labels
        """
        name = dataset_config.get("name")

        try:
            # Inline data
            if "inline_data" in dataset_config:
                logger.info(f"Loading inline dataset: {name}")
                return dataset_config["inline_data"]

            # Service-based (benchmark_service)
            elif dataset_config.get("source") == "service":
                logger.info(f"Loading dataset from service: {name}")
                try:
                    from app.services.research.benchmark_service import benchmark_service

                    test_cases = benchmark_service.get_test_suite()

                    # Convert to standard format
                    dataset = []
                    for test_case in test_cases:
                        tx = test_case.transaction.copy()
                        tx["expected"] = test_case.expected_prediction
                        tx["test_id"] = test_case.test_id
                        tx["category"] = test_case.category
                        tx["difficulty"] = test_case.difficulty
                        dataset.append(tx)

                    logger.info(f"Loaded {len(dataset)} test cases from service")
                    return dataset

                except ImportError:
                    logger.warning("benchmark_service not available")
                    return []

            # CSV file
            elif "path" in dataset_config:
                path = Path(dataset_config["path"])
                if not path.exists():
                    logger.warning(f"Dataset file not found: {path}")
                    return []

                logger.info(f"Loading dataset from file: {path}")
                df = pd.read_csv(path)

                # Sample if needed
                sample_size = self.config.get("execution", {}).get("sample_size", 1000)
                if len(df) > sample_size:
                    random_seed = self.config.get("execution", {}).get("random_seed", 42)
                    df = df.sample(n=sample_size, random_state=random_seed)
                    logger.info(f"Sampled {sample_size} from {len(df)} rows")

                # Convert to dict records
                return df.to_dict("records")

            else:
                logger.warning(f"Unknown dataset source for {name}")
                return []

        except Exception as e:
            logger.exception(f"Error loading dataset {name}: {e}")
            return []

    def run_baseline(
        self,
        baseline_name: str,
        test_data: List[Dict],
        dataset_name: str
    ) -> List[Dict]:
        """
        Run a baseline on test data.

        Args:
            baseline_name: Name of baseline to run
            test_data: Test transactions
            dataset_name: Name of dataset

        Returns:
            list: Results for each prediction
        """
        if baseline_name not in self.baselines:
            logger.warning(f"Baseline not initialized: {baseline_name}")
            return []

        baseline = self.baselines[baseline_name]
        results = []

        logger.info(f"Running {baseline_name} on {len(test_data)} samples...")

        start_time = time.time()

        for i, transaction in enumerate(test_data):
            # Extract expected label
            expected = transaction.get("expected", "legitimate")

            # Make prediction
            pred_result = baseline.predict(transaction)

            # Check correctness
            correct = pred_result.prediction == expected

            # Record result
            result = {
                "baseline": baseline_name,
                "dataset": dataset_name,
                "test_id": transaction.get("test_id", f"{dataset_name}_{i}"),
                "expected": expected,
                "prediction": pred_result.prediction,
                "confidence": pred_result.confidence,
                "correct": correct,
                "latency_ms": pred_result.latency_ms,
                "metadata": pred_result.metadata,
                "error": pred_result.error,
                "timestamp": datetime.utcnow().isoformat()
            }
            results.append(result)

            # Progress logging
            if (i + 1) % 10 == 0 or (i + 1) == len(test_data):
                logger.info(f"  Progress: {i+1}/{len(test_data)}")

        elapsed = time.time() - start_time
        logger.info(f"Completed in {elapsed:.2f}s")

        return results

    def run(self) -> List[Dict]:
        """
        Run all benchmarks.

        Returns:
            list: All results
        """
        logger.info("=" * 80)
        logger.info("BENCHMARK SUITE EXECUTION")
        logger.info("=" * 80)

        # Initialize baselines
        logger.info("\n1. Initializing baselines...")
        baseline_status = self.initialize_baselines()

        active_baselines = [name for name, status in baseline_status.items() if status]
        logger.info(f"Active baselines: {active_baselines}")

        if not active_baselines:
            logger.error("No baselines available!")
            return []

        # Load test datasets
        logger.info("\n2. Loading test datasets...")
        datasets = {}
        dataset_configs = self.config.get("test_datasets", [])

        for dataset_config in dataset_configs:
            name = dataset_config.get("name")
            if not dataset_config.get("enabled", True):
                logger.info(f"Skipping disabled dataset: {name}")
                continue

            data = self._load_test_dataset(dataset_config)
            if data:
                datasets[name] = data
                logger.info(f"✓ Loaded {name}: {len(data)} samples")

        if not datasets:
            logger.error("No datasets available!")
            return []

        # Run benchmarks
        logger.info("\n3. Running benchmarks...")
        all_results = []

        for baseline_name in active_baselines:
            for dataset_name, test_data in datasets.items():
                logger.info(f"\n→ {baseline_name} on {dataset_name}")

                results = self.run_baseline(baseline_name, test_data, dataset_name)
                all_results.extend(results)

        self.results = all_results

        logger.info("\n" + "=" * 80)
        logger.info(f"BENCHMARK COMPLETE: {len(all_results)} predictions")
        logger.info("=" * 80)

        return all_results

    def calculate_metrics(self, results: List[Dict]) -> Dict:
        """
        Calculate evaluation metrics from results.

        Args:
            results: List of result dicts

        Returns:
            dict: Metrics
        """
        if not results:
            return {}

        df = pd.DataFrame(results)

        # Filter out errors
        df_valid = df[df["error"].isna()].copy()

        if len(df_valid) == 0:
            return {"error": "No valid predictions"}

        # Overall metrics
        total = len(df_valid)
        correct = df_valid["correct"].sum()
        accuracy = correct / total if total > 0 else 0.0

        # Classification metrics
        tp = len(df_valid[(df_valid["expected"] == "fraud") & (df_valid["prediction"] == "fraud")])
        tn = len(df_valid[(df_valid["expected"] == "legitimate") & (df_valid["prediction"] == "legitimate")])
        fp = len(df_valid[(df_valid["expected"] == "legitimate") & (df_valid["prediction"] == "fraud")])
        fn = len(df_valid[(df_valid["expected"] == "fraud") & (df_valid["prediction"] == "legitimate")])

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

        # Latency metrics
        latencies = df_valid["latency_ms"].dropna()
        latency_p50 = float(np.percentile(latencies, 50)) if len(latencies) > 0 else 0.0
        latency_p95 = float(np.percentile(latencies, 95)) if len(latencies) > 0 else 0.0
        latency_p99 = float(np.percentile(latencies, 99)) if len(latencies) > 0 else 0.0

        # Confidence
        avg_confidence = float(df_valid["confidence"].mean())

        return {
            "total_predictions": total,
            "correct": int(correct),
            "incorrect": int(total - correct),
            "accuracy": accuracy,
            "precision": precision,
            "recall": recall,
            "f1_score": f1_score,
            "true_positives": tp,
            "true_negatives": tn,
            "false_positives": fp,
            "false_negatives": fn,
            "false_positive_rate": fp / (fp + tn) if (fp + tn) > 0 else 0.0,
            "false_negative_rate": fn / (fn + tp) if (fn + tp) > 0 else 0.0,
            "latency_p50_ms": latency_p50,
            "latency_p95_ms": latency_p95,
            "latency_p99_ms": latency_p99,
            "avg_confidence": avg_confidence
        }

    def generate_report(self, results: List[Dict] = None) -> Dict:
        """
        Generate comprehensive benchmark report.

        Args:
            results: Results to analyze (uses self.results if None)

        Returns:
            dict: Report
        """
        if results is None:
            results = self.results

        if not results:
            return {"error": "No results available"}

        df = pd.DataFrame(results)

        # Overall metrics
        overall_metrics = self.calculate_metrics(results)

        # Per-baseline metrics
        per_baseline = {}
        for baseline in df["baseline"].unique():
            baseline_results = df[df["baseline"] == baseline].to_dict("records")
            per_baseline[baseline] = self.calculate_metrics(baseline_results)

        # Per-dataset metrics
        per_dataset = {}
        for dataset in df["dataset"].unique():
            dataset_results = df[df["dataset"] == dataset].to_dict("records")
            per_dataset[dataset] = self.calculate_metrics(dataset_results)

        # Comparison table (sorted by F1-score)
        comparison = []
        for baseline, metrics in per_baseline.items():
            comparison.append({
                "baseline": baseline,
                "accuracy": metrics.get("accuracy", 0.0),
                "precision": metrics.get("precision", 0.0),
                "recall": metrics.get("recall", 0.0),
                "f1_score": metrics.get("f1_score", 0.0),
                "latency_p95_ms": metrics.get("latency_p95_ms", 0.0)
            })

        comparison.sort(key=lambda x: x["f1_score"], reverse=True)

        # Best baseline
        best_baseline = comparison[0]["baseline"] if comparison else None

        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "config_file": str(self.config_path),
            "total_predictions": len(results),
            "baselines_tested": list(per_baseline.keys()),
            "datasets_tested": list(per_dataset.keys()),
            "overall_metrics": overall_metrics,
            "per_baseline": per_baseline,
            "per_dataset": per_dataset,
            "comparison_table": comparison,
            "best_baseline": best_baseline,
            "recommendations": self._generate_recommendations(comparison)
        }

        return report

    def _generate_recommendations(self, comparison: List[Dict]) -> List[str]:
        """Generate recommendations based on results."""
        recommendations = []

        if not comparison:
            return ["No baselines tested"]

        best = comparison[0]

        # Performance recommendations
        if best["f1_score"] < 0.7:
            recommendations.append(
                "⚠️  Best F1-score is low (<0.7). Consider tuning models or adding features."
            )
        elif best["f1_score"] > 0.95:
            recommendations.append(
                "✓ Excellent F1-score (>0.95). Model performance is strong."
            )

        # Latency recommendations
        if best["latency_p95_ms"] > 1000:
            recommendations.append(
                "⚠️  High latency (>1s p95). Consider optimization or caching."
            )
        elif best["latency_p95_ms"] < 100:
            recommendations.append(
                "✓ Low latency (<100ms p95). Good for real-time applications."
            )

        # Precision/Recall tradeoff
        if best["precision"] < 0.6:
            recommendations.append(
                "⚠️  Low precision. Many false positives. Consider increasing decision threshold."
            )

        if best["recall"] < 0.6:
            recommendations.append(
                "⚠️  Low recall. Missing fraud cases. Consider lowering decision threshold."
            )

        # Best model recommendation
        recommendations.append(
            f"💡 Recommended baseline: {best['baseline']} "
            f"(F1={best['f1_score']:.3f}, Latency={best['latency_p95_ms']:.1f}ms)"
        )

        return recommendations

    def save_results(self, output_dir: str = "data/benchmarks/results"):
        """
        Save results to disk.

        Args:
            output_dir: Output directory
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

        # Save raw results
        results_file = output_path / f"benchmark_results_{timestamp}.json"
        with open(results_file, "w") as f:
            json.dump(self.results, f, indent=2, default=str)
        logger.info(f"Saved results to {results_file}")

        # Save report
        report = self.generate_report()
        report_file = output_path / f"benchmark_report_{timestamp}.json"
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2, default=str)
        logger.info(f"Saved report to {report_file}")

        # Save Markdown report
        md_file = output_path / f"benchmark_report_{timestamp}.md"
        self._save_markdown_report(report, md_file)
        logger.info(f"Saved markdown report to {md_file}")

    def _save_markdown_report(self, report: Dict, output_file: Path):
        """Generate markdown report."""
        with open(output_file, "w") as f:
            f.write("# Benchmark Report\n\n")
            f.write(f"**Generated:** {report['timestamp']}\n\n")

            f.write("## Summary\n\n")
            f.write(f"- **Total Predictions:** {report['total_predictions']}\n")
            f.write(f"- **Baselines Tested:** {', '.join(report['baselines_tested'])}\n")
            f.write(f"- **Datasets Tested:** {', '.join(report['datasets_tested'])}\n")
            f.write(f"- **Best Baseline:** {report['best_baseline']}\n\n")

            f.write("## Comparison Table\n\n")
            f.write("| Baseline | Accuracy | Precision | Recall | F1-Score | Latency (p95) |\n")
            f.write("|----------|----------|-----------|--------|----------|---------------|\n")

            for row in report['comparison_table']:
                f.write(
                    f"| {row['baseline']} | "
                    f"{row['accuracy']:.3f} | "
                    f"{row['precision']:.3f} | "
                    f"{row['recall']:.3f} | "
                    f"{row['f1_score']:.3f} | "
                    f"{row['latency_p95_ms']:.1f}ms |\n"
                )

            f.write("\n## Per-Baseline Metrics\n\n")
            for baseline, metrics in report['per_baseline'].items():
                f.write(f"### {baseline}\n\n")
                f.write(f"- Accuracy: {metrics['accuracy']:.3f}\n")
                f.write(f"- Precision: {metrics['precision']:.3f}\n")
                f.write(f"- Recall: {metrics['recall']:.3f}\n")
                f.write(f"- F1-Score: {metrics['f1_score']:.3f}\n")
                f.write(f"- True Positives: {metrics['true_positives']}\n")
                f.write(f"- False Positives: {metrics['false_positives']}\n")
                f.write(f"- False Negatives: {metrics['false_negatives']}\n")
                f.write(f"- Latency (p50): {metrics['latency_p50_ms']:.2f}ms\n")
                f.write(f"- Latency (p95): {metrics['latency_p95_ms']:.2f}ms\n\n")

            f.write("\n## Recommendations\n\n")
            for rec in report['recommendations']:
                f.write(f"- {rec}\n")
