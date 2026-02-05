"""
Comprehensive Metrics Collection System

Tracks detailed performance metrics across all dimensions:
- Task success rates (classification accuracy, alignment, completion)
- Tool accuracy (selection, parameters, necessity)
- Cost metrics (tokens, API calls, $ cost)
- Latency metrics (p50, p95, p99, step breakdown)
- Recovery metrics (failure recovery, escalation, human intervention)
- Alignment violations (safety, constraints, refusals)
"""

import json
import logging
import time
import statistics
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Literal
from pydantic import BaseModel, Field
from collections import defaultdict
from enum import Enum

logger = logging.getLogger(__name__)


class TaskResult(BaseModel):
    """Result of a single task execution"""
    task_id: str
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    transaction_id: str
    ground_truth: Optional[str] = None  # true label if known
    predicted: str
    correct: Optional[bool] = None
    aligned_with_human: Optional[bool] = None
    completed: bool
    error: Optional[str] = None


class ToolCall(BaseModel):
    """Record of a tool call"""
    call_id: str = Field(default_factory=lambda: f"tool_{int(time.time() * 1000)}")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    tool_name: str
    tool_input: Dict[str, Any]
    tool_output: Optional[Dict[str, Any]] = None
    success: bool
    error: Optional[str] = None
    duration_ms: float
    was_necessary: Optional[bool] = None  # Was the tool call needed?
    parameter_correctness: Optional[float] = None  # 0-1 score


class CostMetrics(BaseModel):
    """Cost tracking for a task"""
    task_id: str
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    token_usage: int
    api_calls: int
    cost_usd: float
    model_used: str


class LatencyMetrics(BaseModel):
    """Latency measurements"""
    task_id: str
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    total_latency_ms: float
    reasoning_latency_ms: float
    tool_call_latency_ms: float
    step_latencies: List[float]


class RecoveryEvent(BaseModel):
    """Failure recovery event"""
    event_id: str = Field(default_factory=lambda: f"recovery_{int(time.time() * 1000)}")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    task_id: str
    failure_type: str
    recovery_attempted: bool
    recovery_successful: bool
    recovery_time_ms: Optional[float] = None
    escalated_to_human: bool
    human_intervention_time_ms: Optional[float] = None


class AlignmentViolation(BaseModel):
    """Safety or alignment violation"""
    violation_id: str = Field(default_factory=lambda: f"violation_{int(time.time() * 1000)}")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    task_id: str
    violation_type: Literal["safety", "constraint", "refusal_failure", "false_refusal"]
    description: str
    severity: Literal["low", "medium", "high", "critical"]
    rule_violated: Optional[str] = None


class AggregatedMetrics(BaseModel):
    """Aggregated metrics summary"""
    time_period: str
    start_time: str
    end_time: str

    # Task metrics
    total_tasks: int
    successful_tasks: int
    task_success_rate: float
    classification_accuracy: Optional[float] = None
    human_alignment_rate: Optional[float] = None

    # Tool metrics
    total_tool_calls: int
    successful_tool_calls: int
    tool_success_rate: float
    avg_parameter_correctness: Optional[float] = None
    unnecessary_tool_calls: int

    # Cost metrics
    total_tokens: int
    total_api_calls: int
    total_cost_usd: float
    avg_cost_per_task: float

    # Latency metrics
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    avg_latency_ms: float

    # Recovery metrics
    total_failures: int
    recoveries_attempted: int
    successful_recoveries: int
    recovery_rate: float
    escalation_rate: float

    # Alignment metrics
    total_violations: int
    critical_violations: int
    high_violations: int


class MetricsCollector:
    """Comprehensive metrics collection and analysis"""

    def __init__(self, data_dir: str = "data/metrics"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.tasks_file = self.data_dir / "task_results.jsonl"
        self.tools_file = self.data_dir / "tool_calls.jsonl"
        self.costs_file = self.data_dir / "costs.jsonl"
        self.latencies_file = self.data_dir / "latencies.jsonl"
        self.recoveries_file = self.data_dir / "recoveries.jsonl"
        self.violations_file = self.data_dir / "violations.jsonl"

    def record_task(
        self,
        task_id: str,
        transaction_id: str,
        predicted: str,
        ground_truth: Optional[str] = None,
        aligned_with_human: Optional[bool] = None,
        completed: bool = True,
        error: Optional[str] = None
    ) -> TaskResult:
        """Record task execution result"""
        correct = None
        if ground_truth:
            correct = predicted.lower() == ground_truth.lower()

        result = TaskResult(
            task_id=task_id,
            transaction_id=transaction_id,
            ground_truth=ground_truth,
            predicted=predicted,
            correct=correct,
            aligned_with_human=aligned_with_human,
            completed=completed,
            error=error
        )

        with open(self.tasks_file, "a") as f:
            f.write(result.model_dump_json() + "\n")

        logger.debug(f"Recorded task {task_id}: correct={correct}, completed={completed}")
        return result

    def record_tool_call(
        self,
        tool_name: str,
        tool_input: Dict[str, Any],
        tool_output: Optional[Dict[str, Any]],
        success: bool,
        duration_ms: float,
        error: Optional[str] = None,
        was_necessary: Optional[bool] = None,
        parameter_correctness: Optional[float] = None
    ) -> ToolCall:
        """Record tool call metrics"""
        call = ToolCall(
            tool_name=tool_name,
            tool_input=tool_input,
            tool_output=tool_output,
            success=success,
            duration_ms=duration_ms,
            error=error,
            was_necessary=was_necessary,
            parameter_correctness=parameter_correctness
        )

        with open(self.tools_file, "a") as f:
            f.write(call.model_dump_json() + "\n")

        logger.debug(f"Recorded tool call: {tool_name}, success={success}")
        return call

    def record_cost(
        self,
        task_id: str,
        token_usage: int,
        api_calls: int,
        cost_usd: float,
        model_used: str = "mistral-7b"
    ) -> CostMetrics:
        """Record cost metrics"""
        metrics = CostMetrics(
            task_id=task_id,
            token_usage=token_usage,
            api_calls=api_calls,
            cost_usd=cost_usd,
            model_used=model_used
        )

        with open(self.costs_file, "a") as f:
            f.write(metrics.model_dump_json() + "\n")

        logger.debug(f"Recorded cost for {task_id}: {cost_usd} USD, {token_usage} tokens")
        return metrics

    def record_latency(
        self,
        task_id: str,
        total_latency_ms: float,
        reasoning_latency_ms: float,
        tool_call_latency_ms: float,
        step_latencies: List[float]
    ) -> LatencyMetrics:
        """Record latency metrics"""
        metrics = LatencyMetrics(
            task_id=task_id,
            total_latency_ms=total_latency_ms,
            reasoning_latency_ms=reasoning_latency_ms,
            tool_call_latency_ms=tool_call_latency_ms,
            step_latencies=step_latencies
        )

        with open(self.latencies_file, "a") as f:
            f.write(metrics.model_dump_json() + "\n")

        logger.debug(f"Recorded latency for {task_id}: {total_latency_ms:.2f}ms")
        return metrics

    def record_recovery(
        self,
        task_id: str,
        failure_type: str,
        recovery_attempted: bool,
        recovery_successful: bool,
        recovery_time_ms: Optional[float] = None,
        escalated_to_human: bool = False,
        human_intervention_time_ms: Optional[float] = None
    ) -> RecoveryEvent:
        """Record failure recovery event"""
        event = RecoveryEvent(
            task_id=task_id,
            failure_type=failure_type,
            recovery_attempted=recovery_attempted,
            recovery_successful=recovery_successful,
            recovery_time_ms=recovery_time_ms,
            escalated_to_human=escalated_to_human,
            human_intervention_time_ms=human_intervention_time_ms
        )

        with open(self.recoveries_file, "a") as f:
            f.write(event.model_dump_json() + "\n")

        logger.info(f"Recorded recovery for {task_id}: success={recovery_successful}")
        return event

    def record_violation(
        self,
        task_id: str,
        violation_type: Literal["safety", "constraint", "refusal_failure", "false_refusal"],
        description: str,
        severity: Literal["low", "medium", "high", "critical"],
        rule_violated: Optional[str] = None
    ) -> AlignmentViolation:
        """Record alignment violation"""
        violation = AlignmentViolation(
            task_id=task_id,
            violation_type=violation_type,
            description=description,
            severity=severity,
            rule_violated=rule_violated
        )

        with open(self.violations_file, "a") as f:
            f.write(violation.model_dump_json() + "\n")

        logger.warning(f"Recorded {severity} {violation_type} violation for {task_id}")
        return violation

    def _load_records(self, file_path: Path, days: int = 7) -> List[Dict]:
        """Load records from the last N days"""
        if not file_path.exists():
            return []

        cutoff = datetime.utcnow() - timedelta(days=days)
        records = []

        with open(file_path, "r") as f:
            for line in f:
                record = json.loads(line)
                record_time = datetime.fromisoformat(record["timestamp"])
                if record_time >= cutoff:
                    records.append(record)

        return records

    def get_aggregated_metrics(self, days: int = 7) -> AggregatedMetrics:
        """Get aggregated metrics for the last N days"""
        start_time = datetime.utcnow() - timedelta(days=days)
        end_time = datetime.utcnow()

        # Load all records
        tasks = self._load_records(self.tasks_file, days)
        tools = self._load_records(self.tools_file, days)
        costs = self._load_records(self.costs_file, days)
        latencies = self._load_records(self.latencies_file, days)
        recoveries = self._load_records(self.recoveries_file, days)
        violations = self._load_records(self.violations_file, days)

        # Task metrics
        total_tasks = len(tasks)
        successful_tasks = sum(1 for t in tasks if t["completed"] and not t["error"])
        task_success_rate = successful_tasks / total_tasks if total_tasks > 0 else 0.0

        tasks_with_truth = [t for t in tasks if t["correct"] is not None]
        classification_accuracy = (
            sum(1 for t in tasks_with_truth if t["correct"]) / len(tasks_with_truth)
            if tasks_with_truth else None
        )

        tasks_with_alignment = [t for t in tasks if t["aligned_with_human"] is not None]
        human_alignment_rate = (
            sum(1 for t in tasks_with_alignment if t["aligned_with_human"]) / len(tasks_with_alignment)
            if tasks_with_alignment else None
        )

        # Tool metrics
        total_tool_calls = len(tools)
        successful_tool_calls = sum(1 for t in tools if t["success"])
        tool_success_rate = successful_tool_calls / total_tool_calls if total_tool_calls > 0 else 0.0

        tools_with_correctness = [t for t in tools if t["parameter_correctness"] is not None]
        avg_parameter_correctness = (
            statistics.mean(t["parameter_correctness"] for t in tools_with_correctness)
            if tools_with_correctness else None
        )

        unnecessary_tool_calls = sum(1 for t in tools if t.get("was_necessary") is False)

        # Cost metrics
        total_tokens = sum(c["token_usage"] for c in costs)
        total_api_calls = sum(c["api_calls"] for c in costs)
        total_cost_usd = sum(c["cost_usd"] for c in costs)
        avg_cost_per_task = total_cost_usd / total_tasks if total_tasks > 0 else 0.0

        # Latency metrics
        all_latencies = [l["total_latency_ms"] for l in latencies]
        if all_latencies:
            sorted_latencies = sorted(all_latencies)
            p50_idx = int(len(sorted_latencies) * 0.50)
            p95_idx = int(len(sorted_latencies) * 0.95)
            p99_idx = int(len(sorted_latencies) * 0.99)

            p50_latency_ms = sorted_latencies[p50_idx]
            p95_latency_ms = sorted_latencies[p95_idx]
            p99_latency_ms = sorted_latencies[p99_idx]
            avg_latency_ms = statistics.mean(all_latencies)
        else:
            p50_latency_ms = p95_latency_ms = p99_latency_ms = avg_latency_ms = 0.0

        # Recovery metrics
        total_failures = sum(1 for t in tasks if t["error"] is not None)
        recoveries_attempted = sum(1 for r in recoveries if r["recovery_attempted"])
        successful_recoveries = sum(1 for r in recoveries if r["recovery_successful"])
        recovery_rate = successful_recoveries / recoveries_attempted if recoveries_attempted > 0 else 0.0
        escalations = sum(1 for r in recoveries if r["escalated_to_human"])
        escalation_rate = escalations / total_failures if total_failures > 0 else 0.0

        # Alignment metrics
        total_violations = len(violations)
        critical_violations = sum(1 for v in violations if v["severity"] == "critical")
        high_violations = sum(1 for v in violations if v["severity"] == "high")

        return AggregatedMetrics(
            time_period=f"last_{days}_days",
            start_time=start_time.isoformat(),
            end_time=end_time.isoformat(),
            total_tasks=total_tasks,
            successful_tasks=successful_tasks,
            task_success_rate=task_success_rate,
            classification_accuracy=classification_accuracy,
            human_alignment_rate=human_alignment_rate,
            total_tool_calls=total_tool_calls,
            successful_tool_calls=successful_tool_calls,
            tool_success_rate=tool_success_rate,
            avg_parameter_correctness=avg_parameter_correctness,
            unnecessary_tool_calls=unnecessary_tool_calls,
            total_tokens=total_tokens,
            total_api_calls=total_api_calls,
            total_cost_usd=total_cost_usd,
            avg_cost_per_task=avg_cost_per_task,
            p50_latency_ms=p50_latency_ms,
            p95_latency_ms=p95_latency_ms,
            p99_latency_ms=p99_latency_ms,
            avg_latency_ms=avg_latency_ms,
            total_failures=total_failures,
            recoveries_attempted=recoveries_attempted,
            successful_recoveries=successful_recoveries,
            recovery_rate=recovery_rate,
            escalation_rate=escalation_rate,
            total_violations=total_violations,
            critical_violations=critical_violations,
            high_violations=high_violations
        )

    def get_tool_breakdown(self) -> Dict[str, Any]:
        """Get detailed breakdown by tool"""
        tools = self._load_records(self.tools_file, days=7)

        tool_stats = defaultdict(lambda: {
            "total_calls": 0,
            "successful_calls": 0,
            "avg_duration_ms": [],
            "errors": []
        })

        for tool in tools:
            name = tool["tool_name"]
            tool_stats[name]["total_calls"] += 1
            if tool["success"]:
                tool_stats[name]["successful_calls"] += 1
            tool_stats[name]["avg_duration_ms"].append(tool["duration_ms"])
            if tool.get("error"):
                tool_stats[name]["errors"].append(tool["error"])

        # Calculate averages
        breakdown = {}
        for name, stats in tool_stats.items():
            breakdown[name] = {
                "total_calls": stats["total_calls"],
                "success_rate": stats["successful_calls"] / stats["total_calls"],
                "avg_duration_ms": statistics.mean(stats["avg_duration_ms"]),
                "error_count": len(stats["errors"])
            }

        return breakdown

    def get_latency_breakdown(self) -> Dict[str, float]:
        """Get latency breakdown by component"""
        latencies = self._load_records(self.latencies_file, days=7)

        if not latencies:
            return {
                "avg_reasoning_ms": 0.0,
                "avg_tool_call_ms": 0.0,
                "avg_total_ms": 0.0
            }

        return {
            "avg_reasoning_ms": statistics.mean(l["reasoning_latency_ms"] for l in latencies),
            "avg_tool_call_ms": statistics.mean(l["tool_call_latency_ms"] for l in latencies),
            "avg_total_ms": statistics.mean(l["total_latency_ms"] for l in latencies)
        }


# Global instance
metrics_collector = MetricsCollector()
