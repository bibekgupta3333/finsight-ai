"""
Agent Debugging & Trace System

Provides comprehensive debugging capabilities for agent reasoning:
- Step-level execution traces with timestamps
- Thought inspection and scratchpad analysis
- Tool replay for deterministic debugging
- Failure clustering and pattern analysis
- Deterministic replay with cached results
"""

import json
import logging
import hashlib
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Literal
from pydantic import BaseModel, Field
from collections import defaultdict
from enum import Enum
import statistics

logger = logging.getLogger(__name__)


class StepType(str, Enum):
    """Types of reasoning steps"""
    REASONING = "reasoning"
    TOOL_CALL = "tool_call"
    DECISION = "decision"
    OBSERVATION = "observation"
    ERROR = "error"


class ReasoningStep(BaseModel):
    """Single step in agent reasoning"""
    step_id: str = Field(default_factory=lambda: f"step_{int(time.time() * 1000)}")
    step_number: int
    step_type: StepType
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    content: str
    tool_name: Optional[str] = None
    tool_input: Optional[Dict[str, Any]] = None
    tool_output: Optional[Dict[str, Any]] = None
    duration_ms: Optional[float] = None
    is_decision: bool = False
    confidence: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ExecutionTrace(BaseModel):
    """Complete execution trace for a transaction"""
    trace_id: str = Field(default_factory=lambda: f"trace_{int(time.time() * 1000)}")
    session_id: str
    transaction_id: str
    start_time: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    end_time: Optional[str] = None
    steps: List[ReasoningStep] = Field(default_factory=list)
    final_decision: Optional[str] = None
    success: bool = False
    error: Optional[str] = None
    total_duration_ms: Optional[float] = None
    token_usage: int = 0
    cost_usd: float = 0.0


class ThoughtAnalysis(BaseModel):
    """Analysis of agent's internal reasoning"""
    trace_id: str
    reasoning_quality: float  # 0-1 score
    cot_consistency: bool  # Chain-of-thought is consistent
    reasoning_errors: List[str]
    logic_gaps: List[str]
    redundant_steps: List[int]
    optimal_step_count: int
    actual_step_count: int
    efficiency_score: float


class FailurePattern(BaseModel):
    """Pattern of similar failures"""
    pattern_id: str
    failure_type: str
    occurrence_count: int
    example_trace_ids: List[str]
    common_characteristics: Dict[str, Any]
    root_cause_hypothesis: str
    priority: Literal["low", "medium", "high", "critical"]


class TraceDebugger:
    """Agent debugging and trace analysis system"""

    def __init__(self, data_dir: str = "data/debugging"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.traces_file = self.data_dir / "execution_traces.jsonl"
        self.failures_file = self.data_dir / "failures.jsonl"
        self.tool_cache_file = self.data_dir / "tool_cache.json"
        self.thought_analysis_file = self.data_dir / "thought_analysis.jsonl"

        # In-memory cache for deterministic replay
        self.tool_cache: Dict[str, Any] = {}
        self._load_tool_cache()

    def _load_tool_cache(self):
        """Load tool call cache for deterministic replay"""
        if self.tool_cache_file.exists():
            with open(self.tool_cache_file, "r") as f:
                self.tool_cache = json.load(f)

    def _save_tool_cache(self):
        """Save tool call cache"""
        with open(self.tool_cache_file, "w") as f:
            json.dump(self.tool_cache, f, indent=2)

    def _cache_key(self, tool_name: str, tool_input: Dict) -> str:
        """Generate cache key for tool call"""
        input_str = json.dumps(tool_input, sort_keys=True)
        return hashlib.md5(f"{tool_name}:{input_str}".encode()).hexdigest()

    def start_trace(
        self,
        session_id: str,
        transaction_id: str
    ) -> ExecutionTrace:
        """Start a new execution trace"""
        trace = ExecutionTrace(
            session_id=session_id,
            transaction_id=transaction_id
        )

        # Save immediately so it can be retrieved
        with open(self.traces_file, "a") as f:
            f.write(trace.model_dump_json() + "\n")

        logger.info(f"Started trace {trace.trace_id} for transaction {transaction_id}")
        return trace

    def add_step(
        self,
        trace: ExecutionTrace,
        step_type: StepType,
        content: str,
        tool_name: Optional[str] = None,
        tool_input: Optional[Dict] = None,
        tool_output: Optional[Dict] = None,
        is_decision: bool = False,
        confidence: Optional[float] = None
    ) -> ReasoningStep:
        """Add a reasoning step to trace"""
        step_start = time.time()

        step = ReasoningStep(
            step_number=len(trace.steps) + 1,
            step_type=step_type,
            content=content,
            tool_name=tool_name,
            tool_input=tool_input,
            tool_output=tool_output,
            is_decision=is_decision,
            confidence=confidence
        )

        # Cache tool calls for replay
        if tool_name and tool_input and tool_output:
            cache_key = self._cache_key(tool_name, tool_input)
            self.tool_cache[cache_key] = {
                "tool_name": tool_name,
                "input": tool_input,
                "output": tool_output,
                "timestamp": step.timestamp
            }

        trace.steps.append(step)

        step_duration = (time.time() - step_start) * 1000
        step.duration_ms = step_duration

        # Update trace in file
        self._update_trace(trace)

        logger.debug(f"Added step {step.step_number} ({step_type}) to trace {trace.trace_id}")
        return step

    def _update_trace(self, trace: ExecutionTrace):
        """Update trace in the file (replace existing entry)"""
        if not self.traces_file.exists():
            return

        # Read all traces
        traces = []
        with open(self.traces_file, "r") as f:
            for line in f:
                trace_data = json.loads(line)
                if trace_data["trace_id"] == trace.trace_id:
                    # Replace with updated trace
                    traces.append(trace.model_dump())
                else:
                    traces.append(trace_data)

        # Write back all traces
        with open(self.traces_file, "w") as f:
            for t in traces:
                f.write(json.dumps(t) + "\n")

    def end_trace(
        self,
        trace: ExecutionTrace,
        final_decision: str,
        success: bool,
        error: Optional[str] = None,
        token_usage: int = 0,
        cost_usd: float = 0.0
    ) -> ExecutionTrace:
        """End trace and save to file"""
        trace.end_time = datetime.utcnow().isoformat()
        trace.final_decision = final_decision
        trace.success = success
        trace.error = error
        trace.token_usage = token_usage
        trace.cost_usd = cost_usd

        # Calculate total duration
        if trace.steps:
            start = datetime.fromisoformat(trace.start_time)
            end = datetime.fromisoformat(trace.end_time)
            trace.total_duration_ms = (end - start).total_seconds() * 1000

        # Save trace
        with open(self.traces_file, "a") as f:
            f.write(trace.model_dump_json() + "\n")

        # Save failures separately
        if not success:
            with open(self.failures_file, "a") as f:
                f.write(trace.model_dump_json() + "\n")

        # Save updated tool cache
        self._save_tool_cache()

        logger.info(f"Ended trace {trace.trace_id}: success={success}, steps={len(trace.steps)}")
        return trace

    def get_trace(self, trace_id: str) -> Optional[ExecutionTrace]:
        """Retrieve a specific trace"""
        if not self.traces_file.exists():
            return None

        with open(self.traces_file, "r") as f:
            for line in f:
                trace_data = json.loads(line)
                if trace_data["trace_id"] == trace_id:
                    return ExecutionTrace(**trace_data)
        return None

    def export_trace(self, trace_id: str) -> Dict[str, Any]:
        """Export trace in JSON format for external tools"""
        trace = self.get_trace(trace_id)
        if not trace:
            return {"error": "Trace not found"}

        return {
            "trace_id": trace.trace_id,
            "transaction_id": trace.transaction_id,
            "duration_ms": trace.total_duration_ms,
            "success": trace.success,
            "steps": [
                {
                    "step": s.step_number,
                    "type": s.step_type,
                    "timestamp": s.timestamp,
                    "content": s.content[:200],  # Truncate for readability
                    "tool": s.tool_name,
                    "duration_ms": s.duration_ms,
                    "is_decision": s.is_decision
                }
                for s in trace.steps
            ],
            "final_decision": trace.final_decision,
            "cost_usd": trace.cost_usd,
            "token_usage": trace.token_usage
        }

    def inspect_thoughts(self, trace_id: str) -> ThoughtAnalysis:
        """Analyze internal reasoning quality"""
        trace = self.get_trace(trace_id)
        if not trace:
            raise ValueError(f"Trace {trace_id} not found")

        reasoning_steps = [s for s in trace.steps if s.step_type == StepType.REASONING]

        # Analyze reasoning quality
        reasoning_errors = []
        logic_gaps = []
        redundant_steps = []

        # Check for repetitive reasoning
        seen_content = set()
        for i, step in enumerate(reasoning_steps):
            content_hash = hashlib.md5(step.content.encode()).hexdigest()
            if content_hash in seen_content:
                redundant_steps.append(i + 1)
            seen_content.add(content_hash)

        # Check for logic gaps (missing context between steps)
        for i in range(len(reasoning_steps) - 1):
            curr = reasoning_steps[i].content.lower()
            next_step = reasoning_steps[i + 1].content.lower()

            # Heuristic: if next step doesn't reference current context
            if len(curr) > 50 and len(next_step) > 50:
                common_words = set(curr.split()) & set(next_step.split())
                if len(common_words) < 3:
                    logic_gaps.append(f"Step {i+1} to {i+2}: weak connection")

        # Check for reasoning errors (contradictions)
        for i in range(len(reasoning_steps) - 1):
            curr = reasoning_steps[i].content.lower()
            for j in range(i + 1, len(reasoning_steps)):
                next_step = reasoning_steps[j].content.lower()

                # Detect contradictions (heuristic: "not" appears with same keywords)
                if "not" in next_step:
                    curr_keywords = set(w for w in curr.split() if len(w) > 5)
                    next_keywords = set(w for w in next_step.split() if len(w) > 5)
                    overlap = curr_keywords & next_keywords
                    if len(overlap) > 2:
                        reasoning_errors.append(f"Potential contradiction between steps {i+1} and {j+1}")

        # Calculate metrics
        optimal_steps = max(5, len(reasoning_steps) - len(redundant_steps))
        actual_steps = len(reasoning_steps)
        efficiency_score = optimal_steps / actual_steps if actual_steps > 0 else 1.0

        reasoning_quality = max(0.0, 1.0 - (len(reasoning_errors) * 0.2 + len(logic_gaps) * 0.1))
        cot_consistency = len(reasoning_errors) == 0

        analysis = ThoughtAnalysis(
            trace_id=trace_id,
            reasoning_quality=reasoning_quality,
            cot_consistency=cot_consistency,
            reasoning_errors=reasoning_errors,
            logic_gaps=logic_gaps,
            redundant_steps=redundant_steps,
            optimal_step_count=optimal_steps,
            actual_step_count=actual_steps,
            efficiency_score=efficiency_score
        )

        # Save analysis
        with open(self.thought_analysis_file, "a") as f:
            f.write(analysis.model_dump_json() + "\n")

        return analysis

    def replay_tool_call(
        self,
        tool_name: str,
        tool_input: Dict,
        use_cache: bool = True
    ) -> Optional[Dict]:
        """Replay a tool call from cache for debugging"""
        cache_key = self._cache_key(tool_name, tool_input)

        if use_cache and cache_key in self.tool_cache:
            cached = self.tool_cache[cache_key]
            logger.info(f"Replaying cached tool call: {tool_name}")
            return cached["output"]

        logger.warning(f"No cached result for {tool_name} with input {tool_input}")
        return None

    def deterministic_replay(
        self,
        trace_id: str,
        random_seed: int = 42
    ) -> ExecutionTrace:
        """Replay exact agent execution deterministically"""
        original_trace = self.get_trace(trace_id)
        if not original_trace:
            raise ValueError(f"Trace {trace_id} not found")

        # Create new trace for replay
        replay_trace = self.start_trace(
            session_id=f"{original_trace.session_id}_replay",
            transaction_id=original_trace.transaction_id
        )

        # Replay each step
        for step in original_trace.steps:
            if step.step_type == StepType.TOOL_CALL and step.tool_name:
                # Use cached tool results
                cached_output = self.replay_tool_call(
                    step.tool_name,
                    step.tool_input or {},
                    use_cache=True
                )

                self.add_step(
                    replay_trace,
                    step_type=step.step_type,
                    content=f"[REPLAY] {step.content}",
                    tool_name=step.tool_name,
                    tool_input=step.tool_input,
                    tool_output=cached_output or step.tool_output,
                    is_decision=step.is_decision,
                    confidence=step.confidence
                )
            else:
                # Replay non-tool steps as-is
                self.add_step(
                    replay_trace,
                    step_type=step.step_type,
                    content=f"[REPLAY] {step.content}",
                    is_decision=step.is_decision,
                    confidence=step.confidence
                )

        # End replay trace
        self.end_trace(
            replay_trace,
            final_decision=original_trace.final_decision or "replayed",
            success=original_trace.success,
            error=original_trace.error,
            token_usage=original_trace.token_usage,
            cost_usd=original_trace.cost_usd
        )

        logger.info(f"Deterministically replayed trace {trace_id}")
        return replay_trace

    def cluster_failures(self) -> List[FailurePattern]:
        """Group similar failures and identify patterns"""
        if not self.failures_file.exists():
            return []

        # Load all failures
        failures = []
        with open(self.failures_file, "r") as f:
            for line in f:
                failures.append(ExecutionTrace(**json.loads(line)))

        # Group by error type
        error_groups = defaultdict(list)
        for failure in failures:
            error_type = failure.error or "unknown"
            # Normalize error type
            if "timeout" in error_type.lower():
                error_type = "timeout"
            elif "network" in error_type.lower() or "connection" in error_type.lower():
                error_type = "network"
            elif "tool" in error_type.lower():
                error_type = "tool_failure"
            elif "reasoning" in error_type.lower() or "logic" in error_type.lower():
                error_type = "reasoning_error"
            else:
                error_type = "other"

            error_groups[error_type].append(failure)

        # Create failure patterns
        patterns = []
        for error_type, group in error_groups.items():
            # Find common characteristics
            common_chars = {
                "avg_steps": statistics.mean(len(f.steps) for f in group),
                "avg_duration_ms": statistics.mean(f.total_duration_ms or 0 for f in group),
                "tool_usage": sum(
                    1 for f in group
                    for s in f.steps
                    if s.step_type == StepType.TOOL_CALL
                ) / len(group)
            }

            # Determine priority
            if len(group) >= 10:
                priority = "critical"
            elif len(group) >= 5:
                priority = "high"
            elif len(group) >= 2:
                priority = "medium"
            else:
                priority = "low"

            # Generate hypothesis
            hypotheses = {
                "timeout": "Execution exceeds time limit - consider caching or optimization",
                "network": "External service unavailable - implement retry logic",
                "tool_failure": "Tool execution errors - validate inputs and add error handling",
                "reasoning_error": "Logic errors in reasoning chain - improve prompts or add validation",
                "other": "Investigate individual cases for root cause"
            }

            pattern = FailurePattern(
                pattern_id=f"pattern_{error_type}_{int(time.time())}",
                failure_type=error_type,
                occurrence_count=len(group),
                example_trace_ids=[f.trace_id for f in group[:5]],
                common_characteristics=common_chars,
                root_cause_hypothesis=hypotheses.get(error_type, hypotheses["other"]),
                priority=priority
            )
            patterns.append(pattern)

        # Sort by priority and occurrence
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        patterns.sort(key=lambda p: (priority_order[p.priority], -p.occurrence_count))

        logger.info(f"Identified {len(patterns)} failure patterns")
        return patterns


# Global instance
trace_debugger = TraceDebugger()
