"""Data lineage tracking system for FinSight AI.

Tracks data transformations, versions, and dependencies across the pipeline.

Usage:
    from backend.scripts.data_lineage import DataLineage

    lineage = DataLineage()
    lineage.track_transformation(
        input_files=["data/raw/PS_*.csv"],
        output_files=["data/processed/paysim_cleaned.csv"],
        script="backend/scripts/data_cleaning.py",
        operations=["normalize", "mask_pii", "engineer_features"]
    )
    lineage.save()
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


class DataLineage:
    """Track and manage data lineage across transformations."""

    def __init__(self, lineage_file: str = "data/lineage.json") -> None:
        """Initialize data lineage tracker.

        Args:
            lineage_file: Path to lineage tracking JSON file
        """
        self.lineage_file = Path(lineage_file)
        self.lineage: Dict = self._load_lineage()

    def _load_lineage(self) -> Dict:
        """Load existing lineage or create new structure.

        Returns:
            dict: Lineage data structure
        """
        if self.lineage_file.exists():
            with open(self.lineage_file, "r", encoding="utf-8") as f:
                return json.load(f)

        return {
            "project": "FinSight AI - Fraud Detection",
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "data_versions": {},
            "transformations": [],
        }

    def register_data_version(
        self,
        version_name: str,
        files: List[str],
        description: str,
        metadata: Optional[Dict] = None,
    ) -> None:
        """Register a new data version.

        Args:
            version_name: Version identifier (e.g., "v1_raw", "v2_cleaned")
            files: List of file paths in this version
            description: Human-readable description
            metadata: Optional metadata (rows, columns, size, etc.)
        """
        self.lineage["data_versions"][version_name] = {
            "files": files,
            "description": description,
            "metadata": metadata or {},
            "created_at": datetime.now().isoformat(),
        }
        self._update_timestamp()

    def track_transformation(
        self,
        transformation_id: str,
        input_files: List[str],
        output_files: List[str],
        script: str,
        operations: List[str],
        input_version: Optional[str] = None,
        output_version: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> None:
        """Track a data transformation.

        Args:
            transformation_id: Unique identifier for transformation
            input_files: List of input file paths
            output_files: List of output file paths
            script: Script that performed the transformation
            operations: List of operations performed
            input_version: Input data version (e.g., "v1_raw")
            output_version: Output data version (e.g., "v2_cleaned")
            metadata: Optional metadata (execution time, parameters, etc.)
        """
        transformation = {
            "id": transformation_id,
            "input_files": input_files,
            "output_files": output_files,
            "input_version": input_version,
            "output_version": output_version,
            "script": script,
            "operations": operations,
            "metadata": metadata or {},
            "timestamp": datetime.now().isoformat(),
        }

        self.lineage["transformations"].append(transformation)
        self._update_timestamp()

    def get_data_version_info(self, version_name: str) -> Optional[Dict]:
        """Get information about a data version.

        Args:
            version_name: Version identifier

        Returns:
            dict: Version information or None if not found
        """
        return self.lineage["data_versions"].get(version_name)

    def get_transformation_history(self, file_path: str) -> List[Dict]:
        """Get transformation history for a file.

        Args:
            file_path: Path to the file

        Returns:
            list: List of transformations involving this file
        """
        history = []
        for transformation in self.lineage["transformations"]:
            if (
                file_path in transformation["input_files"]
                or file_path in transformation["output_files"]
            ):
                history.append(transformation)
        return history

    def get_lineage_chain(self, file_path: str, direction: str = "backward") -> List[Dict]:
        """Get complete lineage chain for a file.

        Args:
            file_path: Path to the file
            direction: "backward" (inputs) or "forward" (outputs)

        Returns:
            list: Ordered list of transformations
        """
        chain = []
        current_files = [file_path]
        visited = set()

        while current_files:
            next_files = []
            for transformation in self.lineage["transformations"]:
                trans_id = transformation["id"]
                if trans_id in visited:
                    continue

                if direction == "backward":
                    # Find transformations that produced current files
                    if any(f in current_files for f in transformation["output_files"]):
                        chain.append(transformation)
                        next_files.extend(transformation["input_files"])
                        visited.add(trans_id)
                else:
                    # Find transformations that consumed current files
                    if any(f in current_files for f in transformation["input_files"]):
                        chain.append(transformation)
                        next_files.extend(transformation["output_files"])
                        visited.add(trans_id)

            current_files = next_files

        return chain[::-1] if direction == "backward" else chain

    def generate_lineage_report(self) -> str:
        """Generate human-readable lineage report.

        Returns:
            str: Formatted lineage report
        """
        report = []
        report.append("=" * 70)
        report.append("DATA LINEAGE REPORT")
        report.append("=" * 70)
        report.append(f"Project: {self.lineage['project']}")
        report.append(f"Created: {self.lineage['created_at']}")
        report.append(f"Last Updated: {self.lineage['last_updated']}")
        report.append("")

        # Data versions
        report.append("DATA VERSIONS:")
        report.append("-" * 70)
        for version_name, version_info in self.lineage["data_versions"].items():
            report.append(f"\n{version_name}:")
            report.append(f"  Description: {version_info['description']}")
            report.append(f"  Files: {len(version_info['files'])}")
            if version_info["metadata"]:
                report.append("  Metadata:")
                for key, value in version_info["metadata"].items():
                    report.append(f"    {key}: {value}")

        # Transformations
        report.append("\n\nTRANSFORMATIONS:")
        report.append("-" * 70)
        for i, trans in enumerate(self.lineage["transformations"], 1):
            report.append(f"\n{i}. {trans['id']}")
            report.append(f"   Script: {trans['script']}")
            report.append(f"   Operations: {', '.join(trans['operations'])}")
            report.append(f"   Input Version: {trans.get('input_version', 'N/A')}")
            report.append(f"   Output Version: {trans.get('output_version', 'N/A')}")
            report.append(f"   Timestamp: {trans['timestamp']}")

        report.append("\n" + "=" * 70)
        return "\n".join(report)

    def _update_timestamp(self) -> None:
        """Update last_updated timestamp."""
        self.lineage["last_updated"] = datetime.now().isoformat()

    def save(self) -> None:
        """Save lineage to file."""
        self.lineage_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.lineage_file, "w", encoding="utf-8") as f:
            json.dump(self.lineage, f, indent=2)
        print(f"✓ Data lineage saved to {self.lineage_file}")

    def visualize_dag(self) -> str:
        """Generate DAG visualization in Mermaid format.

        Returns:
            str: Mermaid flowchart code
        """
        lines = ["```mermaid", "graph TD"]

        # Add data version nodes
        for version_name in self.lineage["data_versions"].keys():
            node_id = version_name.replace("_", "")
            lines.append(f'    {node_id}["{version_name}"]')

        # Add transformation edges
        for trans in self.lineage["transformations"]:
            input_ver = trans.get("input_version", "").replace("_", "") or "unknown"
            output_ver = trans.get("output_version", "").replace("_", "") or "unknown"
            trans_label = " + ".join(trans["operations"][:2])
            lines.append(f'    {input_ver} -->|"{trans_label}"| {output_ver}')

        lines.append("```")
        return "\n".join(lines)


def setup_initial_lineage() -> None:
    """Setup initial data lineage for FinSight AI project."""
    lineage = DataLineage()

    # Register data versions
    lineage.register_data_version(
        version_name="v1_raw",
        files=["data/raw/PS_20174392719_1491204439457_log.csv"],
        description="Raw PaySim Mobile Money transaction dataset from Kaggle",
        metadata={
            "source": "Kaggle",
            "rows": 6_362_620,
            "columns": 11,
            "size_mb": 493,
            "fraud_rate": 0.0013,
        },
    )

    lineage.register_data_version(
        version_name="v2_cleaned",
        files=["data/processed/paysim_cleaned.csv"],
        description="Cleaned and preprocessed dataset with engineered features",
        metadata={
            "rows": 6_362_620,
            "columns": 30,
            "features_added": 19,
            "normalization": "StandardScaler",
            "pii_masked": True,
        },
    )

    lineage.register_data_version(
        version_name="v3_reasoning",
        files=[
            "data/annotations/fraud_explanations.json",
            "data/annotations/weak_supervision_labels.json",
            "data/annotations/preference_pairs.json",
        ],
        description="LLM explanations, weak supervision, and RLHF annotations",
        metadata={
            "fraud_explanations": 100,
            "weak_supervision_labels": 8213,
            "preference_pairs": 491,
            "weak_supervision_accuracy": 0.9967,
        },
    )

    # Track transformations
    lineage.track_transformation(
        transformation_id="data_cleaning_pipeline",
        input_files=["data/raw/PS_20174392719_1491204439457_log.csv"],
        output_files=["data/processed/paysim_cleaned.csv"],
        script="backend/scripts/data_cleaning.py",
        operations=[
            "handle_missing",
            "remove_duplicates",
            "mask_pii",
            "normalize_amounts",
            "create_temporal_features",
            "engineer_features",
        ],
        input_version="v1_raw",
        output_version="v2_cleaned",
        metadata={
            "execution_time_sec": 45,
            "features_created": 19,
            "quality_checks_passed": True,
        },
    )

    lineage.track_transformation(
        transformation_id="fraud_explanation_generation",
        input_files=["data/processed/paysim_cleaned.csv"],
        output_files=["data/annotations/fraud_explanations.json"],
        script="backend/scripts/generate_explanations.py",
        operations=["extract_fraud_cases", "generate_llm_explanations"],
        input_version="v2_cleaned",
        output_version="v3_reasoning",
        metadata={
            "fraud_cases_processed": 100,
            "avg_confidence": 0.80,
        },
    )

    lineage.track_transformation(
        transformation_id="weak_supervision_generation",
        input_files=["data/processed/paysim_cleaned.csv"],
        output_files=[
            "data/annotations/weak_supervision_labels.json",
            "data/annotations/preference_pairs.json",
        ],
        script="backend/scripts/generate_weak_supervision.py",
        operations=[
            "apply_weak_supervision_rules",
            "generate_preference_pairs",
        ],
        input_version="v2_cleaned",
        output_version="v3_reasoning",
        metadata={
            "weak_supervision_accuracy": 0.9967,
            "avg_rules_triggered": 2.83,
            "preference_pairs_created": 491,
        },
    )

    # Save lineage
    lineage.save()

    # Print report
    print("\n" + lineage.generate_lineage_report())

    # Print DAG
    print("\n\nDAG VISUALIZATION:")
    print(lineage.visualize_dag())


if __name__ == "__main__":
    setup_initial_lineage()
