"""
Pattern Comparison Visualization Generator.

Generates publication-ready visualizations for multi-agent pattern comparison:
1. Bar chart: F1 score by pattern
2. Scatter plot: Latency vs F1 (Pareto frontier)
3. Heatmap: Pattern performance across transaction types
4. Statistical significance plots

Usage:
    python benchmarks/generate_visualizations.py results/pattern_comparison_20260209_123456.json
    python benchmarks/generate_visualizations.py --input results/*.json --output figures/
"""

import argparse
import json
import logging
from pathlib import Path
from typing import Dict, List, Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

# Configure matplotlib for publication quality
plt.rcParams.update({
    'figure.figsize': (10, 6),
    'figure.dpi': 300,
    'font.size': 11,
    'font.family': 'serif',
    'axes.labelsize': 12,
    'axes.titlesize': 14,
    'xtick.labelsize': 10,
    'ytick.labelsize': 10,
    'legend.fontsize': 10,
    'lines.linewidth': 2,
    'axes.grid': True,
    'grid.alpha': 0.3,
})

# Seaborn styling
sns.set_palette("husl")
sns.set_style("whitegrid")

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


# =============================================================================
# VISUALIZATION FUNCTIONS
# =============================================================================

class PatternVisualizer:
    """Generates visualizations for pattern comparison results."""

    def __init__(self, output_dir: str = "data/benchmarks/figures"):
        """
        Initialize visualizer.

        Args:
            output_dir: Directory to save figures
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Saving figures to: {self.output_dir}")

    def load_comparison_results(self, results_file: str) -> Dict[str, Any]:
        """
        Load comparison results from JSON.

        Args:
            results_file: Path to results JSON

        Returns:
            Comparison results dict
        """
        with open(results_file, 'r') as f:
            return json.load(f)

    def plot_f1_scores(self, metrics: Dict[str, Dict], timestamp: str = ""):
        """
        Plot bar chart of F1 scores by pattern.

        Args:
            metrics: Pattern metrics dict
            timestamp: Experiment timestamp
        """
        logger.info("Generating F1 score bar chart...")

        # Extract F1 scores
        patterns = []
        f1_scores = []
        precisions = []
        recalls = []

        for pattern_id, pattern_metrics in sorted(
            metrics.items(), key=lambda x: x[1]["f1"], reverse=True
        ):
            patterns.append(self._get_pattern_name(pattern_id))
            f1_scores.append(pattern_metrics["f1"])
            precisions.append(pattern_metrics["precision"])
            recalls.append(pattern_metrics["recall"])

        # Create figure
        fig, ax = plt.subplots(figsize=(12, 6))

        x = np.arange(len(patterns))
        width = 0.25

        # Plot bars
        bars1 = ax.bar(x - width, precisions, width, label='Precision', alpha=0.8)
        bars2 = ax.bar(x, f1_scores, width, label='F1-Score', alpha=0.8)
        bars3 = ax.bar(x + width, recalls, width, label='Recall', alpha=0.8)

        # Styling
        ax.set_xlabel('Agent Pattern', fontweight='bold')
        ax.set_ylabel('Score', fontweight='bold')
        ax.set_title('Multi-Agent Pattern Comparison: Classification Metrics', fontweight='bold', pad=20)
        ax.set_xticks(x)
        ax.set_xticklabels(patterns, rotation=15, ha='right')
        ax.legend(loc='lower right')
        ax.set_ylim(0, 1.1)
        ax.axhline(y=0.9, color='red', linestyle='--', alpha=0.5, label='90% threshold')

        # Add value labels on bars
        for bars in [bars1, bars2, bars3]:
            for bar in bars:
                height = bar.get_height()
                ax.text(
                    bar.get_x() + bar.get_width() / 2.,
                    height,
                    f'{height:.3f}',
                    ha='center',
                    va='bottom',
                    fontsize=8,
                )

        plt.tight_layout()

        # Save
        output_file = self.output_dir / f"f1_comparison_{timestamp}.png"
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        logger.info(f"✅ Saved: {output_file}")
        plt.close()

    def plot_latency_vs_f1(self, metrics: Dict[str, Dict], timestamp: str = ""):
        """
        Plot scatter: Latency vs F1 (Pareto frontier).

        Shows trade-off between accuracy and speed.

        Args:
            metrics: Pattern metrics dict
            timestamp: Experiment timestamp
        """
        logger.info("Generating Latency vs F1 scatter plot...")

        # Extract data
        patterns = []
        f1_scores = []
        latencies = []

        for pattern_id, pattern_metrics in metrics.items():
            patterns.append(self._get_pattern_name(pattern_id))
            f1_scores.append(pattern_metrics["f1"])
            latencies.append(pattern_metrics["latency_p95"])

        # Create figure
        fig, ax = plt.subplots(figsize=(10, 8))

        # Scatter plot
        scatter = ax.scatter(
            latencies,
            f1_scores,
            s=200,
            alpha=0.7,
            c=range(len(patterns)),
            cmap='viridis',
            edgecolors='black',
            linewidth=1.5,
        )

        # Annotate points
        for i, pattern in enumerate(patterns):
            ax.annotate(
                pattern,
                (latencies[i], f1_scores[i]),
                xytext=(10, 5),
                textcoords='offset points',
                fontsize=9,
                bbox=dict(boxstyle='round,pad=0.3', facecolor='yellow', alpha=0.3),
            )

        # Pareto frontier (approximate)
        # Find points not dominated by others
        pareto_indices = []
        for i in range(len(f1_scores)):
            is_pareto = True
            for j in range(len(f1_scores)):
                if i != j:
                    # Check if j dominates i (higher F1 AND lower latency)
                    if f1_scores[j] >= f1_scores[i] and latencies[j] <= latencies[i]:
                        if f1_scores[j] > f1_scores[i] or latencies[j] < latencies[i]:
                            is_pareto = False
                            break
            if is_pareto:
                pareto_indices.append(i)

        # Draw Pareto frontier
        if len(pareto_indices) > 1:
            pareto_f1 = [f1_scores[i] for i in pareto_indices]
            pareto_lat = [latencies[i] for i in pareto_indices]
            sorted_pairs = sorted(zip(pareto_lat, pareto_f1))
            pareto_lat_sorted, pareto_f1_sorted = zip(*sorted_pairs)
            ax.plot(
                pareto_lat_sorted,
                pareto_f1_sorted,
                'r--',
                alpha=0.5,
                linewidth=2,
                label='Pareto Frontier (approx)',
            )

        # Styling
        ax.set_xlabel('Latency P95 (ms)', fontweight='bold')
        ax.set_ylabel('F1-Score', fontweight='bold')
        ax.set_title('Multi-Agent Patterns: Accuracy vs Speed Trade-off', fontweight='bold', pad=20)
        ax.grid(True, alpha=0.3)
        ax.legend()

        # Add quadrant lines
        median_f1 = np.median(f1_scores)
        median_latency = np.median(latencies)
        ax.axhline(y=median_f1, color='gray', linestyle=':', alpha=0.5)
        ax.axvline(x=median_latency, color='gray', linestyle=':', alpha=0.5)

        plt.tight_layout()

        # Save
        output_file = self.output_dir / f"latency_vs_f1_{timestamp}.png"
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        logger.info(f"✅ Saved: {output_file}")
        plt.close()

    def plot_performance_heatmap(
        self, results: Dict[str, List[Dict]], timestamp: str = ""
    ):
        """
        Plot heatmap of pattern performance across test categories.

        Args:
            results: Pattern results dict
            timestamp: Experiment timestamp
        """
        logger.info("Generating performance heatmap...")

        # Extract category-wise performance
        performance_data = []

        for pattern_id, pattern_results in results.items():
            pattern_name = self._get_pattern_name(pattern_id)

            # Group by category
            category_performance = {}
            for result in pattern_results:
                category = result.get("category", "unknown")
                if category not in category_performance:
                    category_performance[category] = []
                category_performance[category].append(1 if result["correct"] else 0)

            # Calculate accuracy per category
            for category, correct_list in category_performance.items():
                accuracy = np.mean(correct_list) if correct_list else 0.0
                performance_data.append({
                    "Pattern": pattern_name,
                    "Category": category,
                    "Accuracy": accuracy,
                })

        # Create DataFrame
        df = pd.DataFrame(performance_data)

        if df.empty:
            logger.warning("No category data available for heatmap")
            return

        # Pivot for heatmap
        pivot_df = df.pivot(index="Pattern", columns="Category", values="Accuracy")

        # Create figure
        fig, ax = plt.subplots(figsize=(12, 8))

        # Heatmap
        sns.heatmap(
            pivot_df,
            annot=True,
            fmt=".3f",
            cmap="RdYlGn",
            center=0.8,
            vmin=0.0,
            vmax=1.0,
            cbar_kws={'label': 'Accuracy'},
            linewidths=0.5,
            ax=ax,
        )

        # Styling
        ax.set_title('Pattern Performance Across Test Categories', fontweight='bold', pad=20)
        ax.set_xlabel('Test Category', fontweight='bold')
        ax.set_ylabel('Agent Pattern', fontweight='bold')
        plt.xticks(rotation=30, ha='right')
        plt.yticks(rotation=0)

        plt.tight_layout()

        # Save
        output_file = self.output_dir / f"performance_heatmap_{timestamp}.png"
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        logger.info(f"✅ Saved: {output_file}")
        plt.close()

    def plot_statistical_significance(
        self, statistical_tests: Dict[str, Dict], timestamp: str = ""
    ):
        """
        Plot statistical significance results.

        Visualizes p-values and effect sizes.

        Args:
            statistical_tests: Statistical test results
            timestamp: Experiment timestamp
        """
        logger.info("Generating statistical significance plot...")

        if not statistical_tests:
            logger.warning("No statistical test results available")
            return

        # Extract data
        patterns = []
        p_values = []
        cohens_d = []
        mean_diffs = []
        ci_lowers = []
        ci_uppers = []

        for pattern_id, test_result in statistical_tests.items():
            patterns.append(self._get_pattern_name(pattern_id))
            p_values.append(test_result["t_pvalue"])
            cohens_d.append(test_result["cohens_d"])
            mean_diffs.append(test_result["mean_difference"])
            ci_lowers.append(test_result["ci_95_lower"])
            ci_uppers.append(test_result["ci_95_upper"])

        # Create figure with 2 subplots
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

        # Plot 1: P-values
        ax1.barh(patterns, [-np.log10(p) for p in p_values], color='steelblue', alpha=0.7)
        ax1.axvline(x=-np.log10(0.05), color='red', linestyle='--', label='p=0.05 threshold')
        ax1.axvline(x=-np.log10(0.01), color='darkred', linestyle='--', label='p=0.01 threshold')
        ax1.set_xlabel('-log10(p-value)', fontweight='bold')
        ax1.set_ylabel('Pattern', fontweight='bold')
        ax1.set_title('Statistical Significance vs Baseline', fontweight='bold')
        ax1.legend()
        ax1.grid(True, alpha=0.3, axis='x')

        # Plot 2: Effect sizes with CI
        y_pos = np.arange(len(patterns))
        ax2.errorbar(
            mean_diffs,
            y_pos,
            xerr=[
                [mean_diffs[i] - ci_lowers[i] for i in range(len(mean_diffs))],
                [ci_uppers[i] - mean_diffs[i] for i in range(len(mean_diffs))]
            ],
            fmt='o',
            markersize=8,
            capsize=5,
            capthick=2,
            color='darkgreen',
            alpha=0.7,
        )
        ax2.axvline(x=0, color='gray', linestyle='-', alpha=0.5)
        ax2.set_yticks(y_pos)
        ax2.set_yticklabels(patterns)
        ax2.set_xlabel('Mean Accuracy Difference (95% CI)', fontweight='bold')
        ax2.set_ylabel('Pattern', fontweight='bold')
        ax2.set_title('Effect Size vs Baseline', fontweight='bold')
        ax2.grid(True, alpha=0.3, axis='x')

        plt.tight_layout()

        # Save
        output_file = self.output_dir / f"statistical_significance_{timestamp}.png"
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        logger.info(f"✅ Saved: {output_file}")
        plt.close()

    def plot_confusion_matrices(
        self, results: Dict[str, List[Dict]], timestamp: str = ""
    ):
        """
        Plot confusion matrices for each pattern.

        Args:
            results: Pattern results dict
            timestamp: Experiment timestamp
        """
        logger.info("Generating confusion matrices...")

        num_patterns = len(results)
        cols = 3
        rows = (num_patterns + cols - 1) // cols

        fig, axes = plt.subplots(rows, cols, figsize=(15, 5 * rows))
        axes = axes.flatten() if num_patterns > 1 else [axes]

        for idx, (pattern_id, pattern_results) in enumerate(results.items()):
            pattern_name = self._get_pattern_name(pattern_id)

            # Build confusion matrix
            tp = sum(1 for r in pattern_results if r["correct"] and r["prediction"] == "fraud")
            fp = sum(1 for r in pattern_results if not r["correct"] and r["prediction"] == "fraud")
            fn = sum(1 for r in pattern_results if not r["correct"] and r["prediction"] == "legitimate")
            tn = sum(1 for r in pattern_results if r["correct"] and r["prediction"] == "legitimate")

            cm = np.array([[tp, fp], [fn, tn]])

            # Plot
            ax = axes[idx]
            sns.heatmap(
                cm,
                annot=True,
                fmt='d',
                cmap='Blues',
                cbar=False,
                ax=ax,
                xticklabels=['Fraud', 'Legit'],
                yticklabels=['Fraud', 'Legit'],
            )
            ax.set_title(pattern_name, fontweight='bold')
            ax.set_xlabel('Predicted')
            ax.set_ylabel('Actual')

        # Hide unused subplots
        for idx in range(num_patterns, len(axes)):
            axes[idx].axis('off')

        plt.tight_layout()

        # Save
        output_file = self.output_dir / f"confusion_matrices_{timestamp}.png"
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        logger.info(f"✅ Saved: {output_file}")
        plt.close()

    def generate_all_visualizations(self, results_file: str):
        """
        Generate all visualizations from results file.

        Args:
            results_file: Path to comparison results JSON
        """
        logger.info(f"\n{'=' * 70}")
        logger.info("GENERATING VISUALIZATIONS")
        logger.info(f"{'=' * 70}\n")

        # Load results
        comparison = self.load_comparison_results(results_file)

        timestamp = comparison.get("timestamp", "")
        metrics = comparison.get("metrics", {})
        results = comparison.get("results", {})

        # Generate plots
        self.plot_f1_scores(metrics, timestamp)
        self.plot_latency_vs_f1(metrics, timestamp)
        self.plot_performance_heatmap(results, timestamp)
        self.plot_confusion_matrices(results, timestamp)

        # Statistical tests (if available)
        stats_file = Path(results_file).parent / f"statistical_tests_{timestamp}.json"
        if stats_file.exists():
            with open(stats_file, 'r') as f:
                statistical_tests = json.load(f)
            self.plot_statistical_significance(statistical_tests, timestamp)

        logger.info(f"\n✅ All visualizations generated!")
        logger.info(f"   Output directory: {self.output_dir}")

    @staticmethod
    def _get_pattern_name(pattern_id: str) -> str:
        """Map pattern ID to readable name."""
        name_map = {
            "single": "Single-Agent",
            "manager-worker": "Manager-Worker",
            "planner-executor-critic": "Planner-Executor-Critic",
            "debate": "Debate",
            "role-specialized": "Role-Specialized",
            "swarm": "Swarm",
        }
        return name_map.get(pattern_id, pattern_id)


# =============================================================================
# MAIN
# =============================================================================

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate visualizations for pattern comparison results"
    )
    parser.add_argument(
        "results_file",
        type=str,
        help="Path to pattern comparison results JSON",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="data/benchmarks/figures",
        help="Output directory for figures (default: data/benchmarks/figures)",
    )

    args = parser.parse_args()

    # Check file exists
    if not Path(args.results_file).exists():
        logger.error(f"Results file not found: {args.results_file}")
        return

    # Generate visualizations
    visualizer = PatternVisualizer(output_dir=args.output)
    visualizer.generate_all_visualizations(args.results_file)


if __name__ == "__main__":
    main()
