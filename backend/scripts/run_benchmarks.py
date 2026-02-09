#!/usr/bin/env python3
"""
Run Benchmark Suite.

Tests different fraud detection baselines and generates comparative reports.

Usage:
    python scripts/run_benchmarks.py
    python scripts/run_benchmarks.py --baselines xgboost lightgbm
    python scripts/run_benchmarks.py --dataset quick_test
    python scripts/run_benchmarks.py --output results/my_benchmark
"""

import argparse
import json
import logging
import sys
from pathlib import Path

# Add backend to path
BACKEND_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from benchmarks.runner import BenchmarkRunner

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("data/benchmarks/benchmark_run.log")
    ]
)

logger = logging.getLogger(__name__)


def main():
    """Run benchmark suite."""
    parser = argparse.ArgumentParser(
        description="Run fraud detection benchmark suite"
    )
    parser.add_argument(
        "--config",
        type=str,
        default="benchmarks/config.yaml",
        help="Path to benchmark configuration file"
    )
    parser.add_argument(
        "--baselines",
        type=str,
        nargs="+",
        default=None,
        help="Specific baselines to test (default: all enabled)"
    )
    parser.add_argument(
        "--dataset",
        type=str,
        default=None,
        help="Specific dataset to use (default: all enabled)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="data/benchmarks/results",
        help="Output directory for results"
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Don't save results to disk"
    )

    args = parser.parse_args()

    logger.info("=" * 80)
    logger.info("FRAUD DETECTION BENCHMARK SUITE")
    logger.info("=" * 80)
    logger.info(f"Config: {args.config}")

    try:
        # Initialize runner
        runner = BenchmarkRunner(config_path=args.config)

        # Filter baselines if specified
        if args.baselines:
            logger.info(f"Filtering to baselines: {args.baselines}")
            all_baselines = runner.config.get("baselines", [])
            for baseline in all_baselines:
                if baseline["name"] not in args.baselines:
                    baseline["enabled"] = False

        # Filter datasets if specified
        if args.dataset:
            logger.info(f"Filtering to dataset: {args.dataset}")
            all_datasets = runner.config.get("test_datasets", [])
            for dataset in all_datasets:
                if dataset["name"] != args.dataset:
                    dataset["enabled"] = False

        # Run benchmarks
        results = runner.run()

        if not results:
            logger.error("No results generated!")
            return 1

        # Generate report
        logger.info("\n" + "=" * 80)
        logger.info("GENERATING REPORT")
        logger.info("=" * 80)

        report = runner.generate_report(results)

        # Print summary
        print("\n" + "=" * 80)
        print("BENCHMARK SUMMARY")
        print("=" * 80)
        print(f"\nTotal Predictions: {report['total_predictions']}")
        print(f"Baselines Tested: {', '.join(report['baselines_tested'])}")
        print(f"Best Baseline: {report['best_baseline']}")

        print("\nCOMPARISON TABLE:")
        print("-" * 80)
        print(f"{'Baseline':<20} {'Accuracy':<10} {'Precision':<10} {'Recall':<10} {'F1-Score':<10} {'Latency (p95)'}")
        print("-" * 80)

        for row in report['comparison_table']:
            print(
                f"{row['baseline']:<20} "
                f"{row['accuracy']:<10.3f} "
                f"{row['precision']:<10.3f} "
                f"{row['recall']:<10.3f} "
                f"{row['f1_score']:<10.3f} "
                f"{row['latency_p95_ms']:<10.1f}ms"
            )

        print("\nRECOMMENDATIONS:")
        for rec in report['recommendations']:
            print(f"  {rec}")

        # Save results
        if not args.no_save:
            logger.info("\nSaving results...")
            runner.save_results(output_dir=args.output)
            logger.info(f"Results saved to {args.output}/")

        print("\n" + "=" * 80)
        print("✓ BENCHMARK COMPLETE")
        print("=" * 80)

        return 0

    except Exception as e:
        logger.exception(f"Benchmark failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
