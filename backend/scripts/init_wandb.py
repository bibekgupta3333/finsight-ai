"""Initialize Weights & Biases project for FinSight AI fraud detection.

This script sets up W&B project, logs data versions, and tracks dataset metadata.

Usage:
    python backend/scripts/init_wandb.py
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import pandas as pd
import wandb


class WandBDataVersioning:
    """Manages data versioning and tracking with Weights & Biases."""

    def __init__(
        self,
        project_name: str = "finsight-fraud-detection",
        entity: str = None,
    ) -> None:
        """Initialize W&B data versioning.

        Args:
            project_name: Name of the W&B project
            entity: W&B team/user name (None for personal account)
        """
        self.project_name = project_name
        self.entity = entity
        self.data_dir = Path("data")

    def initialize_project(self) -> wandb.sdk.wandb_run.Run:
        """Initialize W&B project and create a new run.

        Returns:
            wandb.Run: Active W&B run object
        """
        run = wandb.init(
            project=self.project_name,
            entity=self.entity,
            job_type="data_versioning",
            tags=["data-prep", "versioning", "fraud-detection"],
            config={
                "dataset": "PaySim Mobile Money",
                "task": "fraud_detection",
                "framework": "finsight-ai",
            },
        )
        print(f"✓ Initialized W&B project: {self.project_name}")
        print(f"  Run URL: {run.url}")
        return run

    def log_raw_data_version(self) -> wandb.Artifact:
        """Log raw PaySim dataset as v1_raw artifact.

        Returns:
            wandb.Artifact: Raw data artifact
        """
        raw_data_path = self.data_dir / "raw" / "PS_20174392719_1491204439457_log.csv"

        # Create artifact
        artifact = wandb.Artifact(
            name="paysim_raw_data",
            type="raw_dataset",
            description="Raw PaySim Mobile Money transaction dataset",
            metadata={
                "source": "Kaggle PaySim Synthetic Financial Dataset",
                "rows": 6_362_620,
                "columns": 11,
                "size_mb": 493,
                "fraud_rate": 0.0013,
                "version": "v1_raw",
                "timestamp": datetime.now().isoformat(),
            },
        )

        # Add file (reference only, don't upload large file)
        if raw_data_path.exists():
            artifact.add_reference(
                f"file://{raw_data_path.absolute()}",
                name="paysim_raw.csv",
            )
            print(f"✓ Added raw data reference: {raw_data_path}")

        # Log artifact
        wandb.log_artifact(artifact)
        print("✓ Logged v1_raw artifact to W&B")
        return artifact

    def log_cleaned_data_version(self) -> wandb.Artifact:
        """Log cleaned dataset as v2_cleaned artifact.

        Returns:
            wandb.Artifact: Cleaned data artifact
        """
        cleaned_data_path = self.data_dir / "processed" / "paysim_cleaned.csv"
        metadata_path = self.data_dir / "processed" / "cleaned_metadata.json"

        # Load metadata
        metadata = {}
        if metadata_path.exists():
            with open(metadata_path, "r", encoding="utf-8") as f:
                metadata = json.load(f)

        # Create artifact
        artifact = wandb.Artifact(
            name="paysim_cleaned_data",
            type="cleaned_dataset",
            description="Cleaned and preprocessed PaySim dataset with " "engineered features",
            metadata={
                "version": "v2_cleaned",
                "rows": metadata.get("rows", 6_362_620),
                "columns": metadata.get("columns", 30),
                "features_added": 19,  # 30 - 11 original
                "normalization": "StandardScaler",
                "pii_masked": True,
                "fraud_features": 11,
                "temporal_features": 4,
                "timestamp": datetime.now().isoformat(),
                **metadata,
            },
        )

        # Add file reference
        if cleaned_data_path.exists():
            artifact.add_reference(
                f"file://{cleaned_data_path.absolute()}",
                name="paysim_cleaned.csv",
            )
            print(f"✓ Added cleaned data reference: {cleaned_data_path}")

        # Add metadata file
        if metadata_path.exists():
            artifact.add_file(str(metadata_path), name="metadata.json")

        # Log artifact
        wandb.log_artifact(artifact)
        print("✓ Logged v2_cleaned artifact to W&B")
        return artifact

    def log_reasoning_data_version(self) -> wandb.Artifact:
        """Log annotation/reasoning data as v3_reasoning artifact.

        Returns:
            wandb.Artifact: Reasoning data artifact
        """
        annotations_dir = self.data_dir / "annotations"

        # Create artifact
        artifact = wandb.Artifact(
            name="paysim_reasoning_annotations",
            type="annotation_dataset",
            description="LLM explanations, weak supervision labels, and "
            "preference pairs for RLHF",
            metadata={
                "version": "v3_reasoning",
                "fraud_explanations": 100,
                "weak_supervision_labels": 8213,
                "preference_pairs": 491,
                "weak_supervision_accuracy": 0.9967,
                "annotation_types": [
                    "llm_explanations",
                    "weak_supervision",
                    "preference_pairs",
                ],
                "timestamp": datetime.now().isoformat(),
            },
        )

        # Add annotation files
        annotation_files = [
            "fraud_explanations.json",
            "weak_supervision_labels.json",
            "preference_pairs.json",
        ]

        for filename in annotation_files:
            file_path = annotations_dir / filename
            if file_path.exists():
                artifact.add_file(str(file_path), name=filename)
                print(f"  Added: {filename}")

        # Log artifact
        wandb.log_artifact(artifact)
        print("✓ Logged v3_reasoning artifact to W&B")
        return artifact

    def log_data_lineage(self) -> None:
        """Log data lineage and transformation pipeline to W&B."""
        lineage = {
            "pipeline_stages": [
                {
                    "stage": "1_data_loading",
                    "input": "raw/PS_*.csv",
                    "output": "raw/PS_*.csv",
                    "script": "notebooks/01-data-loading-eda.ipynb",
                    "operations": ["load_csv", "profile_data"],
                },
                {
                    "stage": "2_data_cleaning",
                    "input": "raw/PS_*.csv",
                    "output": "processed/paysim_cleaned.csv",
                    "script": "backend/scripts/data_cleaning.py",
                    "operations": [
                        "handle_missing",
                        "remove_duplicates",
                        "mask_pii",
                        "normalize_amounts",
                        "create_temporal_features",
                        "engineer_features",
                    ],
                },
                {
                    "stage": "3_annotation",
                    "input": "processed/paysim_cleaned.csv",
                    "output": "annotations/*.json",
                    "scripts": [
                        "backend/scripts/generate_explanations.py",
                        "backend/scripts/generate_weak_supervision.py",
                    ],
                    "operations": [
                        "generate_explanations",
                        "weak_supervision_rules",
                        "preference_pair_generation",
                    ],
                },
            ],
            "data_versions": {
                "v1_raw": {
                    "name": "paysim_raw_data",
                    "rows": 6_362_620,
                    "columns": 11,
                    "fraud_rate": 0.0013,
                },
                "v2_cleaned": {
                    "name": "paysim_cleaned_data",
                    "rows": 6_362_620,
                    "columns": 30,
                    "features_added": 19,
                },
                "v3_reasoning": {
                    "name": "paysim_reasoning_annotations",
                    "explanations": 100,
                    "weak_labels": 8213,
                    "preference_pairs": 491,
                },
            },
        }

        # Log lineage as config
        wandb.config.update({"data_lineage": lineage})

        # Create lineage table
        lineage_table = wandb.Table(
            columns=["Stage", "Input", "Output", "Operations"],
            data=[
                [
                    stage["stage"],
                    stage["input"],
                    stage["output"],
                    ", ".join(stage["operations"]),
                ]
                for stage in lineage["pipeline_stages"]
            ],
        )
        wandb.log({"data_lineage_pipeline": lineage_table})
        print("✓ Logged data lineage to W&B")

    def log_dataset_statistics(self) -> None:
        """Log dataset statistics and visualizations to W&B."""
        # Load cleaned data sample for stats
        cleaned_path = self.data_dir / "processed" / "paysim_cleaned.csv"

        if not cleaned_path.exists():
            print("⚠ Cleaned data not found, skipping statistics")
            return

        # Read sample (first 100k rows for visualization)
        print("Loading data sample for statistics...")
        df = pd.read_csv(cleaned_path, nrows=100_000)

        # Log basic statistics
        stats = {
            "total_transactions": 100_000,  # Sample
            "fraud_count": int(df["isFraud"].sum()),
            "fraud_rate": float(df["isFraud"].mean()),
            "avg_amount": float(df["amount"].mean()),
            "median_amount": float(df["amount"].median()),
            "transaction_types": df["type"].value_counts().to_dict(),
        }
        wandb.log(stats)

        # Create fraud distribution table
        fraud_dist = wandb.Table(
            columns=["Transaction Type", "Count", "Fraud Count", "Fraud Rate"],
            data=[
                [
                    tx_type,
                    len(df[df["type"] == tx_type]),
                    int(df[df["type"] == tx_type]["isFraud"].sum()),
                    float(df[df["type"] == tx_type]["isFraud"].mean()),
                ]
                for tx_type in df["type"].unique()
            ],
        )
        wandb.log({"fraud_distribution": fraud_dist})

        print("✓ Logged dataset statistics to W&B")

    def run(self) -> None:
        """Execute complete W&B data versioning workflow."""
        print("\n" + "=" * 70)
        print("Weights & Biases Data Versioning")
        print("=" * 70 + "\n")

        # Initialize project
        run = self.initialize_project()

        try:
            # Log data versions
            print("\nLogging data artifacts...")
            self.log_raw_data_version()
            self.log_cleaned_data_version()
            self.log_reasoning_data_version()

            # Log lineage
            print("\nLogging data lineage...")
            self.log_data_lineage()

            # Log statistics
            print("\nLogging dataset statistics...")
            self.log_dataset_statistics()

            print("\n" + "=" * 70)
            print("✓ W&B Data Versioning Complete!")
            print(f"  View your data: {run.url}")
            print("=" * 70 + "\n")

        finally:
            # Finish run
            run.finish()


def main() -> None:
    """Main entry point."""
    versioning = WandBDataVersioning()
    versioning.run()


if __name__ == "__main__":
    main()
