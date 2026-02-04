"""
Distribution Shift from Tools Monitor

Tracks how tool usage affects data distribution and agent behavior.
Monitors for tool over-reliance and ensures generalization capabilities.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from collections import defaultdict
import statistics

logger = logging.getLogger(__name__)


class ToolUsageRecord(BaseModel):
    """Record of tool usage in a session"""
    session_id: str
    tool_name: str
    input_data: Dict[str, Any]
    output_data: Dict[str, Any]
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    success: bool = True


class DistributionMetrics(BaseModel):
    """Metrics for data distribution"""
    mean: float
    std_dev: float
    min_val: float
    max_val: float
    sample_size: int


class ToolRelianceReport(BaseModel):
    """Report on tool over-reliance"""
    tool_name: str
    usage_frequency: float  # 0-1
    success_rate_with_tool: float
    success_rate_without_tool: float
    over_reliance_detected: bool
    recommendation: str


class DistributionShiftMonitor:
    """Monitor distribution shift caused by tool usage"""

    def __init__(self, data_dir: str = "data/distribution_shift"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.tool_usage_log = self.data_dir / "tool_usage_log.jsonl"
        self.baseline_distributions = self.data_dir / "baseline_distributions.json"
        self.tool_free_results = self.data_dir / "tool_free_results.jsonl"

    def record_tool_usage(
        self,
        session_id: str,
        tool_name: str,
        input_data: Dict[str, Any],
        output_data: Dict[str, Any],
        success: bool = True
    ) -> None:
        """Record tool usage for distribution analysis"""
        record = ToolUsageRecord(
            session_id=session_id,
            tool_name=tool_name,
            input_data=input_data,
            output_data=output_data,
            success=success
        )

        with open(self.tool_usage_log, "a") as f:
            f.write(record.model_dump_json() + "\n")

        logger.info(f"Recorded tool usage: {tool_name} for session {session_id}")

    def get_distribution_metrics(
        self,
        values: List[float]
    ) -> DistributionMetrics:
        """Calculate distribution metrics"""
        if not values:
            return DistributionMetrics(
                mean=0.0,
                std_dev=0.0,
                min_val=0.0,
                max_val=0.0,
                sample_size=0
            )

        return DistributionMetrics(
            mean=statistics.mean(values),
            std_dev=statistics.stdev(values) if len(values) > 1 else 0.0,
            min_val=min(values),
            max_val=max(values),
            sample_size=len(values)
        )

    def analyze_tool_impact(
        self,
        tool_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Analyze how tools change data distribution"""
        if not self.tool_usage_log.exists():
            return {
                "status": "no_data",
                "message": "No tool usage data available"
            }

        # Load tool usage records
        records = []
        with open(self.tool_usage_log, "r") as f:
            for line in f:
                records.append(json.loads(line))

        # Group by tool
        by_tool = defaultdict(list)
        for record in records:
            if tool_name is None or record["tool_name"] == tool_name:
                by_tool[record["tool_name"]].append(record)

        # Analyze distribution changes
        tool_impacts = {}
        for tool, tool_records in by_tool.items():
            # Extract confidence values or amounts
            with_tool_values = []
            for r in tool_records:
                if "confidence" in r["output_data"]:
                    with_tool_values.append(r["output_data"]["confidence"])
                elif "amount" in r["input_data"]:
                    with_tool_values.append(r["input_data"]["amount"])

            if with_tool_values:
                metrics = self.get_distribution_metrics(with_tool_values)
                tool_impacts[tool] = {
                    "distribution": metrics.model_dump(),
                    "usage_count": len(tool_records),
                    "success_rate": sum(1 for r in tool_records if r["success"]) / len(tool_records)
                }

        return {
            "status": "analyzed",
            "total_records": len(records),
            "tools_analyzed": list(tool_impacts.keys()),
            "tool_impacts": tool_impacts
        }

    def detect_tool_exploitation(
        self,
        tool_name: str
    ) -> Dict[str, Any]:
        """Detect if agent is exploiting a tool"""
        if not self.tool_usage_log.exists():
            return {
                "exploitation_detected": False,
                "reason": "No usage data"
            }

        # Load records
        records = []
        with open(self.tool_usage_log, "r") as f:
            for line in f:
                record = json.loads(line)
                if record["tool_name"] == tool_name:
                    records.append(record)

        if len(records) < 10:
            return {
                "exploitation_detected": False,
                "reason": "Insufficient data"
            }

        # Check for exploitation patterns
        exploitation_signals = []

        # 1. Unrealistically high success rate (>95%)
        success_rate = sum(1 for r in records if r["success"]) / len(records)
        if success_rate > 0.95:
            exploitation_signals.append("unusually_high_success_rate")

        # 2. Repetitive input patterns (same inputs repeated)
        input_hashes = [json.dumps(r["input_data"], sort_keys=True) for r in records]
        unique_inputs = len(set(input_hashes))
        repetition_rate = 1 - (unique_inputs / len(records))
        if repetition_rate > 0.7:
            exploitation_signals.append("repetitive_inputs")

        # 3. Output manipulation (all outputs very similar)
        if len(records) > 5:
            output_values = []
            for r in records:
                if "confidence" in r["output_data"]:
                    output_values.append(r["output_data"]["confidence"])
            if output_values and statistics.stdev(output_values) < 0.05:
                exploitation_signals.append("uniform_outputs")

        return {
            "exploitation_detected": len(exploitation_signals) > 0,
            "signals": exploitation_signals,
            "success_rate": success_rate,
            "repetition_rate": repetition_rate,
            "total_uses": len(records)
        }

    def check_tool_reliance(
        self,
        tool_name: str
    ) -> ToolRelianceReport:
        """Check if agent is over-reliant on a tool"""
        # Load all records
        all_records = []
        tool_records = []

        if self.tool_usage_log.exists():
            with open(self.tool_usage_log, "r") as f:
                for line in f:
                    record = json.loads(line)
                    all_records.append(record)
                    if record["tool_name"] == tool_name:
                        tool_records.append(record)

        # Load tool-free results
        tool_free_records = []
        if self.tool_free_results.exists():
            with open(self.tool_free_results, "r") as f:
                for line in f:
                    tool_free_records.append(json.loads(line))

        # Calculate metrics
        total_sessions = len(set(r["session_id"] for r in all_records))
        tool_sessions = len(set(r["session_id"] for r in tool_records))

        usage_frequency = tool_sessions / total_sessions if total_sessions > 0 else 0.0

        success_with = sum(1 for r in tool_records if r["success"]) / len(tool_records) if tool_records else 0.0
        success_without = sum(1 for r in tool_free_records if r["success"]) / len(tool_free_records) if tool_free_records else 0.0

        # Detect over-reliance
        over_reliance = (
            usage_frequency > 0.8 and  # Used in >80% of sessions
            success_with > success_without + 0.3  # 30%+ better with tool
        )

        recommendation = "Tool is used appropriately"
        if over_reliance:
            recommendation = "Agent is over-reliant on this tool. Consider training without tool to improve generalization."
        elif usage_frequency > 0.9:
            recommendation = "Very high tool usage. Monitor for degradation in tool-free performance."

        return ToolRelianceReport(
            tool_name=tool_name,
            usage_frequency=usage_frequency,
            success_rate_with_tool=success_with,
            success_rate_without_tool=success_without,
            over_reliance_detected=over_reliance,
            recommendation=recommendation
        )

    def test_tool_free_performance(
        self,
        session_id: str,
        input_data: Dict[str, Any],
        prediction: str,
        success: bool
    ) -> Dict[str, Any]:
        """Test agent performance without tools (fallback capability)"""
        result = {
            "session_id": session_id,
            "input_data": input_data,
            "prediction": prediction,
            "success": success,
            "timestamp": datetime.utcnow().isoformat()
        }

        with open(self.tool_free_results, "a") as f:
            f.write(json.dumps(result) + "\n")

        logger.info(f"Recorded tool-free result for session {session_id}")

        return {
            "status": "recorded",
            "session_id": session_id,
            "prediction": prediction
        }

    def get_generalization_report(self) -> Dict[str, Any]:
        """Report on generalization outside tool scope"""
        # Compare performance with vs without tools
        tool_sessions = set()
        tool_success = []

        if self.tool_usage_log.exists():
            with open(self.tool_usage_log, "r") as f:
                for line in f:
                    record = json.loads(line)
                    tool_sessions.add(record["session_id"])
                    tool_success.append(record["success"])

        tool_free_success = []
        if self.tool_free_results.exists():
            with open(self.tool_free_results, "r") as f:
                for line in f:
                    record = json.loads(line)
                    tool_free_success.append(record["success"])

        with_tools_rate = sum(tool_success) / len(tool_success) if tool_success else 0.0
        without_tools_rate = sum(tool_free_success) / len(tool_free_success) if tool_free_success else 0.0

        generalization_gap = with_tools_rate - without_tools_rate

        status = "good"
        if generalization_gap > 0.3:
            status = "poor"
        elif generalization_gap > 0.15:
            status = "moderate"

        return {
            "success_rate_with_tools": with_tools_rate,
            "success_rate_without_tools": without_tools_rate,
            "generalization_gap": generalization_gap,
            "generalization_status": status,
            "recommendation": (
                "Good generalization" if status == "good"
                else "Agent may be too dependent on tools. Increase tool-free training."
            ),
            "samples_with_tools": len(tool_success),
            "samples_without_tools": len(tool_free_success)
        }


# Global instance
distribution_monitor = DistributionShiftMonitor()
