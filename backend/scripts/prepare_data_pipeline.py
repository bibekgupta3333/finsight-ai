"""Complete Data Pipeline - From Raw Data to Vector Database

This script orchestrates the entire data preparation and vectorization pipeline:
1. Data Cleaning & Feature Engineering
2. Dataset Splitting (Stratified & Temporal)
3. Data Augmentation & Balancing
4. Weak Supervision Label Generation
5. Fraud Explanation Generation
6. Bias & Fairness Analysis
7. Data Lineage Tracking
8. Vector Database Preparation (ChromaDB)

Usage:
    python scripts/prepare_data_pipeline.py [--skip-steps STEPS]

Options:
    --skip-steps STEPS    Comma-separated list of steps to skip
                         (e.g., "cleaning,splitting,augmentation")
    --limit-fraud N       Limit fraud cases for explanations (default: 100)
    --limit-vector N      Limit fraud cases for vectorization (default: 500)
    --quick              Run in quick mode (skip augmentation, limit samples)

Author: FinSight AI Team
Date: January 5, 2026
"""

import argparse
import logging
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class DataPipelineOrchestrator:
    """Orchestrate complete data pipeline from raw data to vector database."""

    def __init__(
        self,
        project_root: Path,
        skip_steps: Optional[List[str]] = None,
        quick_mode: bool = False,
        limit_fraud_explanations: int = 100,
        limit_vector_cases: int = 500,
    ):
        """Initialize pipeline orchestrator.

        Args:
            project_root: Root directory of the project
            skip_steps: List of step names to skip
            quick_mode: If True, run in quick mode with reduced processing
            limit_fraud_explanations: Max fraud cases for explanation generation
            limit_vector_cases: Max fraud cases for vectorization
        """
        self.project_root = project_root
        self.backend_dir = project_root / "backend"
        self.scripts_dir = self.backend_dir / "scripts"
        self.data_dir = project_root / "data"

        self.skip_steps = skip_steps or []
        self.quick_mode = quick_mode
        self.limit_fraud_explanations = limit_fraud_explanations
        self.limit_vector_cases = limit_vector_cases

        # Pipeline steps configuration
        self.pipeline_steps = [
            {
                "name": "cleaning",
                "title": "Data Cleaning & Feature Engineering",
                "script": "data_cleaning.py",
                "required_input": self.data_dir / "raw" / "PS_20174392719_1491204439457_log.csv",
                "output": self.data_dir / "processed" / "paysim_cleaned.csv",
            },
            {
                "name": "splitting",
                "title": "Dataset Splitting",
                "script": "dataset_splitting.py",
                "required_input": self.data_dir / "processed" / "paysim_cleaned.csv",
                "output": self.data_dir / "splits" / "stratified" / "train.csv",
            },
            {
                "name": "augmentation",
                "title": "Data Augmentation & Balancing",
                "script": "data_augmentation.py",
                "required_input": self.data_dir / "splits" / "stratified" / "train.csv",
                "output": self.data_dir / "balanced" / "train_balanced_combined.csv",
            },
            {
                "name": "weak_supervision",
                "title": "Weak Supervision & RLHF Labels",
                "script": "generate_weak_supervision.py",
                "required_input": self.data_dir / "processed" / "paysim_cleaned.csv",
                "output": self.data_dir / "annotations" / "weak_supervision_labels.json",
            },
            {
                "name": "explanations",
                "title": "Fraud Explanation Generation",
                "script": "generate_explanations.py",
                "required_input": self.data_dir / "processed" / "paysim_cleaned.csv",
                "output": self.data_dir / "annotations" / "fraud_explanations.json",
            },
            {
                "name": "bias_analysis",
                "title": "Bias & Fairness Analysis",
                "script": "bias_fairness_analysis.py",
                "required_input": self.data_dir / "processed" / "paysim_cleaned.csv",
                "output": self.data_dir / "analysis" / "bias_audit_report.json",
            },
            {
                "name": "lineage",
                "title": "Data Lineage Tracking",
                "script": "data_lineage.py",
                "required_input": None,  # No specific input required
                "output": self.data_dir / "lineage.json",
            },
            {
                "name": "vectorization",
                "title": "Vector Database Preparation",
                "script": "vectorize_data.py",
                "required_input": self.data_dir / "processed" / "paysim_cleaned.csv",
                "output": None,  # ChromaDB - no file output
            },
        ]

        # Stats tracking
        self.completed_steps = []
        self.failed_steps = []
        self.skipped_steps = []
        self.step_durations = {}

    def check_prerequisites(self) -> bool:
        """Check if all prerequisites are met.

        Returns:
            True if prerequisites are met, False otherwise
        """
        logger.info("Checking prerequisites...")

        # Check if raw data exists
        raw_data = self.data_dir / "raw" / "PS_20174392719_1491204439457_log.csv"
        if not raw_data.exists():
            logger.error(f"Raw data not found: {raw_data}")
            logger.error("Please download the PaySim dataset first.")
            return False

        logger.info(f"✓ Raw data found: {raw_data}")

        # Check if all script files exist
        missing_scripts = []
        for step in self.pipeline_steps:
            script_path = self.scripts_dir / step["script"]
            if not script_path.exists():
                missing_scripts.append(step["script"])

        if missing_scripts:
            logger.error(f"Missing scripts: {', '.join(missing_scripts)}")
            return False

        logger.info(f"✓ All {len(self.pipeline_steps)} pipeline scripts found")

        # Check ChromaDB connection (for vectorization step)
        try:
            import chromadb
            client = chromadb.HttpClient(host="localhost", port=8001)
            client.heartbeat()
            logger.info("✓ ChromaDB connection successful (localhost:8001)")
        except Exception as e:
            logger.warning(f"⚠ ChromaDB not available: {e}")
            logger.warning("  Vectorization step may fail if ChromaDB is not running")
            logger.warning("  Start ChromaDB with: docker-compose up -d chromadb")

        return True

    def should_skip_step(self, step_name: str, output_path: Optional[Path]) -> bool:
        """Check if a step should be skipped.

        Args:
            step_name: Name of the step
            output_path: Expected output file path

        Returns:
            True if step should be skipped, False otherwise
        """
        # Check explicit skip list
        if step_name in self.skip_steps:
            logger.info(f"⏭ Skipping {step_name} (explicitly skipped)")
            return True

        # In quick mode, skip augmentation
        if self.quick_mode and step_name == "augmentation":
            logger.info(f"⏭ Skipping {step_name} (quick mode)")
            return True

        # Check if output already exists and is recent
        if output_path and output_path.exists():
            age_hours = (time.time() - output_path.stat().st_mtime) / 3600
            if age_hours < 24:  # Less than 24 hours old
                logger.info(
                    f"⏭ Skipping {step_name} (output exists and is recent: {age_hours:.1f}h old)"
                )
                return True

        return False

    def run_script(self, script_name: str, step_name: str) -> bool:
        """Run a pipeline script.

        Args:
            script_name: Name of the script file
            step_name: Name of the step (for logging)

        Returns:
            True if script succeeded, False otherwise
        """
        script_path = self.scripts_dir / script_name

        logger.info(f"Running: {script_name}")
        start_time = time.time()

        try:
            # Run script as subprocess
            result = subprocess.run(
                [sys.executable, str(script_path)],
                cwd=str(self.backend_dir),
                capture_output=True,
                text=True,
            )

            duration = time.time() - start_time
            self.step_durations[step_name] = duration

            if result.returncode == 0:
                logger.info(f"✓ {step_name} completed in {duration:.1f}s")
                return True
            else:
                logger.error(f"✗ {step_name} failed (exit code: {result.returncode})")
                logger.error(f"STDERR: {result.stderr}")
                return False

        except Exception as e:
            duration = time.time() - start_time
            self.step_durations[step_name] = duration
            logger.error(f"✗ {step_name} failed with exception: {e}")
            return False

    def run_pipeline(self) -> bool:
        """Run the complete data pipeline.

        Returns:
            True if all steps succeeded, False otherwise
        """
        logger.info("")
        logger.info("=" * 80)
        logger.info("DATA PIPELINE ORCHESTRATION - STARTING")
        logger.info("=" * 80)
        logger.info(f"Project Root: {self.project_root}")
        logger.info(f"Quick Mode: {self.quick_mode}")
        logger.info(f"Skip Steps: {', '.join(self.skip_steps) if self.skip_steps else 'None'}")
        logger.info("")

        total_start_time = time.time()

        for i, step in enumerate(self.pipeline_steps, 1):
            step_name = step["name"]
            step_title = step["title"]
            script_name = step["script"]
            required_input = step["required_input"]
            output_path = step["output"]

            logger.info("")
            logger.info("=" * 80)
            logger.info(f"STEP {i}/{len(self.pipeline_steps)}: {step_title}")
            logger.info("=" * 80)

            # Check if step should be skipped
            if self.should_skip_step(step_name, output_path):
                self.skipped_steps.append(step_name)
                continue

            # Check if required input exists
            if required_input and not required_input.exists():
                logger.error(f"✗ Required input not found: {required_input}")
                logger.error(f"  Cannot proceed with {step_name}")
                self.failed_steps.append(step_name)
                continue

            # Run the script
            success = self.run_script(script_name, step_name)

            if success:
                self.completed_steps.append(step_name)

                # Verify output was created (if applicable)
                if output_path and not output_path.exists():
                    logger.warning(f"⚠ Expected output not found: {output_path}")
            else:
                self.failed_steps.append(step_name)
                logger.error(f"✗ Step {i} ({step_name}) failed")

                # Ask if user wants to continue
                if i < len(self.pipeline_steps):
                    response = input("\nContinue with remaining steps? (y/n): ").lower()
                    if response != 'y':
                        logger.info("Pipeline execution stopped by user")
                        break

        total_duration = time.time() - total_start_time

        # Print summary
        self.print_summary(total_duration)

        return len(self.failed_steps) == 0

    def print_summary(self, total_duration: float):
        """Print pipeline execution summary.

        Args:
            total_duration: Total execution time in seconds
        """
        logger.info("")
        logger.info("=" * 80)
        logger.info("DATA PIPELINE EXECUTION SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Total Duration: {total_duration:.1f}s ({total_duration / 60:.1f}m)")
        logger.info("")

        # Completed steps
        logger.info(f"✓ Completed Steps ({len(self.completed_steps)}):")
        for step in self.completed_steps:
            duration = self.step_durations.get(step, 0)
            logger.info(f"  - {step}: {duration:.1f}s")

        # Skipped steps
        if self.skipped_steps:
            logger.info(f"\n⏭ Skipped Steps ({len(self.skipped_steps)}):")
            for step in self.skipped_steps:
                logger.info(f"  - {step}")

        # Failed steps
        if self.failed_steps:
            logger.info(f"\n✗ Failed Steps ({len(self.failed_steps)}):")
            for step in self.failed_steps:
                logger.info(f"  - {step}")

        logger.info("")
        logger.info("=" * 80)

        # Final status
        if not self.failed_steps:
            logger.info("🎉 DATA PIPELINE COMPLETED SUCCESSFULLY!")
            logger.info("")
            logger.info("Next Steps:")
            logger.info("  1. Review generated data in data/ directory")
            logger.info("  2. Start backend API: cd backend && poetry run uvicorn app.main:app")
            logger.info("  3. Access ChromaDB collections at localhost:8001")
        else:
            logger.info("⚠ PIPELINE COMPLETED WITH ERRORS")
            logger.info(f"  {len(self.failed_steps)} step(s) failed")
            logger.info("  Review logs above for details")

        logger.info("=" * 80)

    def generate_report(self, output_file: str = "pipeline_report.json"):
        """Generate a detailed JSON report of the pipeline execution.

        Args:
            output_file: Output file name for the report
        """
        import json
        from datetime import datetime

        report = {
            "timestamp": datetime.now().isoformat(),
            "project_root": str(self.project_root),
            "quick_mode": self.quick_mode,
            "skipped_steps_config": self.skip_steps,
            "execution": {
                "completed": self.completed_steps,
                "skipped": self.skipped_steps,
                "failed": self.failed_steps,
            },
            "durations": self.step_durations,
            "total_duration": sum(self.step_durations.values()),
        }

        report_path = self.data_dir / output_file
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)

        logger.info(f"📊 Report saved to: {report_path}")


def main():
    """Main entry point for the data pipeline."""
    parser = argparse.ArgumentParser(
        description="Complete Data Pipeline - From Raw Data to Vector Database"
    )
    parser.add_argument(
        "--skip-steps",
        type=str,
        default="",
        help="Comma-separated list of steps to skip (e.g., 'cleaning,splitting')",
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Run in quick mode (skip augmentation, limit samples)",
    )
    parser.add_argument(
        "--limit-fraud",
        type=int,
        default=100,
        help="Limit fraud cases for explanation generation (default: 100)",
    )
    parser.add_argument(
        "--limit-vector",
        type=int,
        default=500,
        help="Limit fraud cases for vectorization (default: 500)",
    )
    parser.add_argument(
        "--generate-report",
        action="store_true",
        help="Generate detailed JSON report after execution",
    )

    args = parser.parse_args()

    # Parse skip steps
    skip_steps = [s.strip() for s in args.skip_steps.split(",") if s.strip()]

    # Get project root
    project_root = Path(__file__).parent.parent.parent

    # Initialize orchestrator
    orchestrator = DataPipelineOrchestrator(
        project_root=project_root,
        skip_steps=skip_steps,
        quick_mode=args.quick,
        limit_fraud_explanations=args.limit_fraud,
        limit_vector_cases=args.limit_vector,
    )

    # Check prerequisites
    if not orchestrator.check_prerequisites():
        logger.error("Prerequisites check failed. Cannot proceed.")
        sys.exit(1)

    # Run pipeline
    success = orchestrator.run_pipeline()

    # Generate report if requested
    if args.generate_report:
        orchestrator.generate_report()

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
