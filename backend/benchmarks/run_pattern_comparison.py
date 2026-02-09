"""
Multi-Agent Pattern Comparison Script.

Systematically compares all 6 agent patterns on the same test set:
1. Single-Agent
2. Manager-Worker
3. Planner-Executor-Critic
4. Debate
5. Role-Specialized
6. Swarm

Tracks metrics with MLflow, performs statistical significance testing,
and generates comparison visualizations.

Research Goal: Prove multi-agent patterns outperform single-agent baseline.

Usage:
    python benchmarks/run_pattern_comparison.py --test-size 10 --output reports/benchmarks
    python benchmarks/run_pattern_comparison.py --patterns debate pec --test-size 20
"""

import asyncio
import json
import logging
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import stats

# MLflow tracking
try:
    import mlflow
    MLFLOW_AVAILABLE = True
except ImportError:
    MLFLOW_AVAILABLE = False
    logging.warning("MLflow not available - tracking disabled")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import agents
from app.agents.single_agent import FraudDetectionAgent
from app.agents.multi_agent import (
    ManagerWorkerSystem,
    PlannerExecutorCriticSystem,
    DebateSystem,
    RoleSpecializedSystem,
    SwarmSystem,
)
from app.services.research.benchmark_service import BenchmarkService


# =============================================================================
# PATTERN CONFIGURATIONS
# =============================================================================

PATTERN_CONFIGS = {
    "single": {
        "name": "Single-Agent",
        "class": FraudDetectionAgent,
        "init_params": {"max_steps": 15},
        "description": "Single LLM agent with ReAct-style reasoning",
        "expected_f1": 0.85,
        "expected_latency_p95": 2000,  # ms
    },
    "manager-worker": {
        "name": "Manager-Worker",
        "class": ManagerWorkerSystem,
        "init_params": {"num_workers": 2},  # Reduced for M4 Pro
        "description": "Manager delegates to 2 specialized workers",
        "expected_f1": 0.88,
        "expected_latency_p95": 3500,
    },
    "planner-executor-critic": {
        "name": "Planner-Executor-Critic",
        "class": PlannerExecutorCriticSystem,
        "init_params": {},
        "description": "Three-role pipeline with planning and validation",
        "expected_f1": 0.91,
        "expected_latency_p95": 3200,
    },
    "debate": {
        "name": "Debate",
        "class": DebateSystem,
        "init_params": {},
        "description": "Adversarial debate with prosecutor, defense, judge",
        "expected_f1": 0.91,
        "expected_latency_p95": 3800,
    },
    "role-specialized": {
        "name": "Role-Specialized",
        "class": RoleSpecializedSystem,
        "init_params": {},
        "description": "Domain expert agents (transaction, account, policy)",
        "expected_f1": 0.89,
        "expected_latency_p95": 3500,
    },
    "swarm": {
        "name": "Swarm",
        "class": SwarmSystem,
        "init_params": {"swarm_size": 3, "consensus_threshold": 0.6},  # Reduced size
        "description": "3 agents with threshold-based consensus",
        "expected_f1": 0.87,
        "expected_latency_p95": 4000,
    },
}


# =============================================================================
# PATTERN EVALUATOR
# =============================================================================

class PatternEvaluator:
    """Evaluates a single pattern on test set."""

    def __init__(self, pattern_id: str, config: Dict):
        """
        Initialize pattern evaluator.

        Args:
            pattern_id: Pattern identifier (e.g., "debate")
            config: Pattern configuration dict
        """
        self.pattern_id = pattern_id
        self.config = config
        self.name = config["name"]

        # Initialize agent/system
        agent_class = config["class"]
        init_params = config["init_params"]
        self.agent = agent_class(**init_params)

        logger.info(f"Initialized {self.name} pattern")

    async def evaluate_transaction(
        self, transaction: Dict, expected: str, test_id: str
    ) -> Dict[str, Any]:
        """
        Evaluate single transaction.

        Args:
            transaction: Transaction dict
            expected: Expected label ("fraud" or "legitimate")
            test_id: Test case identifier

        Returns:
            Result dict with metrics
        """
        start_time = time.time()

        try:
            # Run analysis
            result = await self.agent.analyze(transaction, test_id)

            # Calculate latency
            latency_ms = (time.time() - start_time) * 1000

            # Determine prediction
            is_fraud = result.is_fraud if hasattr(result, "is_fraud") else result.prediction == "fraud"
            confidence = result.confidence if hasattr(result, "confidence") else 0.5
            risk_score = result.risk_score if hasattr(result, "risk_score") else 0.0

            # Check correctness
            prediction = "fraud" if is_fraud else "legitimate"
            correct = prediction == expected

            # Count agent calls (for multi-agent)
            num_agents = len(result.agent_results) if hasattr(result, "agent_results") else 1

            return {
                "test_id": test_id,
                "pattern": self.pattern_id,
                "prediction": prediction,
                "expected": expected,
                "correct": correct,
                "confidence": confidence,
                "risk_score": risk_score,
                "latency_ms": latency_ms,
                "num_agents": num_agents,
                "error": None,
            }

        except Exception as e:
            logger.error(f"Error evaluating {test_id} with {self.name}: {e}")
            return {
                "test_id": test_id,
                "pattern": self.pattern_id,
                "prediction": None,
                "expected": expected,
                "correct": False,
                "confidence": 0.0,
                "risk_score": 0.0,
                "latency_ms": (time.time() - start_time) * 1000,
                "num_agents": 0,
                "error": str(e),
            }

    async def evaluate_batch(
        self, test_cases: List[Dict]
    ) -> List[Dict[str, Any]]:
        """
        Evaluate batch of test cases.

        Args:
            test_cases: List of test case dicts with 'transaction' and 'expected'

        Returns:
            List of result dicts
        """
        results = []
        for i, test_case in enumerate(test_cases, 1):
            logger.info(
                f"{self.name}: Evaluating {i}/{len(test_cases)} - {test_case.get('test_id', 'unknown')}"
            )

            result = await self.evaluate_transaction(
                test_case["transaction"],
                test_case["expected"],
                test_case.get("test_id", f"test_{i}"),
            )
            results.append(result)

            # Small delay to avoid overwhelming system (M4 Pro constraint)
            await asyncio.sleep(0.5)

        return results


# =============================================================================
# PATTERN COMPARATOR
# =============================================================================

class PatternComparator:
    """Compares multiple patterns with statistical testing."""

    def __init__(self, output_dir: str = "data/benchmarks/pattern_comparison"):
        """
        Initialize pattern comparator.

        Args:
            output_dir: Directory for saving results
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.results_file = self.output_dir / f"pattern_comparison_{self.timestamp}.json"

        # Initialize MLflow
        if MLFLOW_AVAILABLE:
            mlflow.set_experiment("multi-agent-pattern-comparison")

    def calculate_metrics(self, results: List[Dict]) -> Dict[str, float]:
        """
        Calculate classification and performance metrics.

        Args:
            results: List of evaluation results

        Returns:
            Dict of metrics
        """
        # Filter successful predictions
        valid_results = [r for r in results if r["prediction"] is not None]

        if not valid_results:
            logger.warning("No valid results to calculate metrics")
            return {}

        # Classification metrics
        correct = sum(1 for r in valid_results if r["correct"])
        total = len(valid_results)
        accuracy = correct / total if total > 0 else 0.0

        # Precision, Recall, F1
        tp = sum(1 for r in valid_results if r["correct"] and r["prediction"] == "fraud")
        fp = sum(1 for r in valid_results if not r["correct"] and r["prediction"] == "fraud")
        fn = sum(1 for r in valid_results if not r["correct"] and r["prediction"] == "legitimate")
        tn = sum(1 for r in valid_results if r["correct"] and r["prediction"] == "legitimate")

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

        # Performance metrics
        latencies = [r["latency_ms"] for r in valid_results]
        latency_p50 = np.percentile(latencies, 50) if latencies else 0.0
        latency_p95 = np.percentile(latencies, 95) if latencies else 0.0
        latency_mean = np.mean(latencies) if latencies else 0.0

        # Confidence
        confidences = [r["confidence"] for r in valid_results]
        avg_confidence = np.mean(confidences) if confidences else 0.0

        # Agent efficiency
        num_agents = [r["num_agents"] for r in valid_results]
        avg_agents = np.mean(num_agents) if num_agents else 1.0

        # Error rate
        error_rate = sum(1 for r in results if r["error"] is not None) / len(results) if results else 0.0

        return {
            "accuracy": accuracy,
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "latency_p50": latency_p50,
            "latency_p95": latency_p95,
            "latency_mean": latency_mean,
            "avg_confidence": avg_confidence,
            "avg_agents": avg_agents,
            "error_rate": error_rate,
            "total_tests": total,
            "true_positives": tp,
            "false_positives": fp,
            "false_negatives": fn,
            "true_negatives": tn,
        }

    async def compare_patterns(
        self,
        patterns: List[str],
        test_cases: List[Dict],
        track_mlflow: bool = True,
    ) -> Dict[str, Any]:
        """
        Compare multiple patterns on same test set.

        Args:
            patterns: List of pattern IDs to compare
            test_cases: Test cases with transaction and expected label
            track_mlflow: Whether to track with MLflow

        Returns:
            Comparison results dict
        """
        all_results = {}
        all_metrics = {}

        logger.info(f"\n{'=' * 70}")
        logger.info(f"PATTERN COMPARISON: {len(patterns)} patterns on {len(test_cases)} test cases")
        logger.info(f"{'=' * 70}\n")

        for pattern_id in patterns:
            if pattern_id not in PATTERN_CONFIGS:
                logger.warning(f"Unknown pattern: {pattern_id}, skipping")
                continue

            config = PATTERN_CONFIGS[pattern_id]
            logger.info(f"\n--- Evaluating: {config['name']} ---")

            # Initialize evaluator
            evaluator = PatternEvaluator(pattern_id, config)

            # Run evaluation
            pattern_results = await evaluator.evaluate_batch(test_cases)
            all_results[pattern_id] = pattern_results

            # Calculate metrics
            metrics = self.calculate_metrics(pattern_results)
            all_metrics[pattern_id] = metrics

            # Print summary
            logger.info(f"\n{config['name']} Results:")
            logger.info(f"  Accuracy: {metrics['accuracy']:.3f}")
            logger.info(f"  F1-Score: {metrics['f1']:.3f}")
            logger.info(f"  Precision: {metrics['precision']:.3f}")
            logger.info(f"  Recall: {metrics['recall']:.3f}")
            logger.info(f"  Latency P95: {metrics['latency_p95']:.1f}ms")
            logger.info(f"  Avg Agents: {metrics['avg_agents']:.1f}")

            # Track in MLflow
            if track_mlflow and MLFLOW_AVAILABLE:
                with mlflow.start_run(run_name=f"pattern_{pattern_id}_{self.timestamp}"):
                    mlflow.log_params({
                        "pattern_id": pattern_id,
                        "pattern_name": config["name"],
                        "description": config["description"],
                        "test_size": len(test_cases),
                    })

                    mlflow.log_metrics({
                        "f1": metrics["f1"],
                        "precision": metrics["precision"],
                        "recall": metrics["recall"],
                        "accuracy": metrics["accuracy"],
                        "latency_p50": metrics["latency_p50"],
                        "latency_p95": metrics["latency_p95"],
                        "avg_confidence": metrics["avg_confidence"],
                        "avg_agents": metrics["avg_agents"],
                        "error_rate": metrics["error_rate"],
                    })

                    mlflow.set_tag("pattern", pattern_id)
                    mlflow.set_tag("experiment_type", "pattern_comparison")

        # Aggregate comparison
        comparison = {
            "timestamp": self.timestamp,
            "test_size": len(test_cases),
            "patterns": patterns,
            "results": all_results,
            "metrics": all_metrics,
        }

        # Save results
        with open(self.results_file, "w") as f:
            json.dump(comparison, f, indent=2)

        logger.info(f"\n✅ Results saved to: {self.results_file}")

        return comparison

    def perform_statistical_tests(
        self, comparison: Dict[str, Any], baseline_pattern: str = "single"
    ) -> Dict[str, Any]:
        """
        Perform statistical significance testing.

        Compares each pattern against the baseline using:
        - Paired t-test (parametric)
        - Wilcoxon signed-rank test (non-parametric)
        - Cohen's d (effect size)

        Args:
            comparison: Comparison results from compare_patterns()
            baseline_pattern: Pattern to compare against (default: "single")

        Returns:
            Statistical test results
        """
        logger.info(f"\n{'=' * 70}")
        logger.info("STATISTICAL SIGNIFICANCE TESTING")
        logger.info(f"{'=' * 70}\n")

        all_results = comparison["results"]

        if baseline_pattern not in all_results:
            logger.error(f"Baseline pattern '{baseline_pattern}' not found")
            return {}

        baseline_results = all_results[baseline_pattern]
        baseline_correct = [1 if r["correct"] else 0 for r in baseline_results]

        statistical_tests = {}

        for pattern_id, pattern_results in all_results.items():
            if pattern_id == baseline_pattern:
                continue  # Skip self-comparison

            logger.info(f"\n--- {PATTERN_CONFIGS[pattern_id]['name']} vs {PATTERN_CONFIGS[baseline_pattern]['name']} ---")

            # Extract correctness scores (paired data)
            pattern_correct = [1 if r["correct"] else 0 for r in pattern_results]

            # Ensure same length
            min_len = min(len(baseline_correct), len(pattern_correct))
            baseline_subset = baseline_correct[:min_len]
            pattern_subset = pattern_correct[:min_len]

            # Paired t-test
            t_stat, t_pvalue = stats.ttest_rel(pattern_subset, baseline_subset)

            # Wilcoxon signed-rank test (non-parametric)
            try:
                wilcoxon_stat, wilcoxon_pvalue = stats.wilcoxon(pattern_subset, baseline_subset)
            except ValueError:
                # All differences are zero
                wilcoxon_stat, wilcoxon_pvalue = 0.0, 1.0

            # Cohen's d (effect size)
            diff = np.array(pattern_subset) - np.array(baseline_subset)
            cohens_d = np.mean(diff) / (np.std(diff) + 1e-8)

            # Confidence interval (95%)
            mean_diff = np.mean(diff)
            std_err = stats.sem(diff)
            ci_95 = stats.t.interval(0.95, len(diff) - 1, loc=mean_diff, scale=std_err)

            statistical_tests[pattern_id] = {
                "baseline": baseline_pattern,
                "t_statistic": float(t_stat),
                "t_pvalue": float(t_pvalue),
                "wilcoxon_statistic": float(wilcoxon_stat),
                "wilcoxon_pvalue": float(wilcoxon_pvalue),
                "cohens_d": float(cohens_d),
                "mean_difference": float(mean_diff),
                "ci_95_lower": float(ci_95[0]),
                "ci_95_upper": float(ci_95[1]),
                "sample_size": min_len,
            }

            # Interpret results
            significant = t_pvalue < 0.05
            effect_size_label = (
                "large" if abs(cohens_d) > 0.8
                else "medium" if abs(cohens_d) > 0.5
                else "small"
            )

            logger.info(f"  T-test: t={t_stat:.3f}, p={t_pvalue:.4f} {'✅ Significant' if significant else '❌ Not significant'}")
            logger.info(f"  Wilcoxon: W={wilcoxon_stat:.1f}, p={wilcoxon_pvalue:.4f}")
            logger.info(f"  Cohen's d: {cohens_d:.3f} ({effect_size_label} effect)")
            logger.info(f"  Mean diff: {mean_diff:.3f} (95% CI: [{ci_95[0]:.3f}, {ci_95[1]:.3f}])")

        # Save statistical results
        stats_file = self.output_dir / f"statistical_tests_{self.timestamp}.json"
        with open(stats_file, "w") as f:
            json.dump(statistical_tests, f, indent=2)

        logger.info(f"\n✅ Statistical results saved to: {stats_file}")

        return statistical_tests


# =============================================================================
# TEST DATA PREPARATION
# =============================================================================

def prepare_test_cases(test_size: int = 10) -> List[Dict]:
    """
    Prepare test cases from benchmark service.

    Args:
        test_size: Number of test cases to use (limited for M4 Pro)

    Returns:
        List of test case dicts
    """
    logger.info(f"Loading test cases (max {test_size})...")

    # Initialize benchmark service
    benchmark_service = BenchmarkService()
    all_cases = benchmark_service.get_test_suite()

    # Select diverse test cases
    test_cases = []
    for test_case in all_cases[:test_size]:
        test_cases.append({
            "test_id": test_case.test_id,
            "transaction": test_case.transaction,
            "expected": test_case.expected_prediction,
            "category": test_case.category,
            "difficulty": test_case.difficulty,
        })

    logger.info(f"Loaded {len(test_cases)} test cases")
    return test_cases


# =============================================================================
# MAIN
# =============================================================================

async def main():
    """Run pattern comparison experiment."""
    import argparse

    parser = argparse.ArgumentParser(description="Multi-Agent Pattern Comparison")
    parser.add_argument(
        "--patterns",
        nargs="+",
        default=list(PATTERN_CONFIGS.keys()),
        choices=list(PATTERN_CONFIGS.keys()),
        help="Patterns to compare (default: all)",
    )
    parser.add_argument(
        "--test-size",
        type=int,
        default=10,
        help="Number of test cases (default: 10, limited for M4 Pro)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="data/benchmarks/pattern_comparison",
        help="Output directory for results",
    )
    parser.add_argument(
        "--no-mlflow",
        action="store_true",
        help="Disable MLflow tracking",
    )
    parser.add_argument(
        "--baseline",
        type=str,
        default="single",
        help="Baseline pattern for statistical comparison (default: single)",
    )

    args = parser.parse_args()

    # Prepare test cases
    test_cases = prepare_test_cases(test_size=args.test_size)

    # Initialize comparator
    comparator = PatternComparator(output_dir=args.output)

    # Run comparison
    comparison = await comparator.compare_patterns(
        patterns=args.patterns,
        test_cases=test_cases,
        track_mlflow=not args.no_mlflow and MLFLOW_AVAILABLE,
    )

    # Statistical testing
    statistical_tests = comparator.perform_statistical_tests(
        comparison, baseline_pattern=args.baseline
    )

    # Print final summary
    logger.info(f"\n{'=' * 70}")
    logger.info("PATTERN COMPARISON SUMMARY")
    logger.info(f"{'=' * 70}\n")

    # Sort patterns by F1 score
    metrics = comparison["metrics"]
    sorted_patterns = sorted(
        metrics.items(), key=lambda x: x[1]["f1"], reverse=True
    )

    logger.info("\nPattern Rankings (by F1 Score):")
    for i, (pattern_id, pattern_metrics) in enumerate(sorted_patterns, 1):
        name = PATTERN_CONFIGS[pattern_id]["name"]
        f1 = pattern_metrics["f1"]
        latency = pattern_metrics["latency_p95"]
        logger.info(f"{i}. {name:25s} F1={f1:.3f}  Latency P95={latency:.1f}ms")

    logger.info(f"\n✅ Experiment complete!")
    logger.info(f"   Results: {comparator.results_file}")


if __name__ == "__main__":
    asyncio.run(main())
