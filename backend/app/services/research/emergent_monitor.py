"""
Emergent Behavior Monitor

Tracks and analyzes emergent capabilities and behaviors in agents.
Detects patterns not explicitly trained: tool use emergence, planning emergence, failure modes.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from collections import Counter, defaultdict


class EmergentCapability(BaseModel):
    """Detected emergent capability"""
    capability_id: str
    name: str
    description: str
    first_observed: datetime
    observation_count: int = 1
    confidence: float = Field(ge=0, le=1)
    examples: List[str] = []
    
    # Classification
    capability_type: str  # tool_use, planning, reasoning, failure_mode
    is_beneficial: bool = True


class BehaviorPattern(BaseModel):
    """Observed behavior pattern"""
    pattern_id: str
    pattern_type: str  # tool_sequence, reasoning_chain, error_recovery
    frequency: int
    contexts: List[str] = []
    first_seen: datetime
    last_seen: datetime
    
    # Analysis
    effectiveness: Optional[float] = None  # Success rate when pattern used
    is_emergent: bool = False  # Not explicitly programmed


class FailureMode(BaseModel):
    """Detected failure mode"""
    mode_id: str
    failure_type: str  # hallucination, tool_misuse, reasoning_loop, reward_hacking
    severity: str  # low, medium, high, critical
    occurrences: int
    impact: str
    mitigation: Optional[str] = None


class EmergentBehaviorMonitor:
    """Service for monitoring emergent agent behaviors"""
    
    def __init__(self, storage_path: str = "data/emergent_behavior"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self.behaviors_file = self.storage_path / "behavior_log.jsonl"
        self.capabilities_file = self.storage_path / "capabilities.json"
        self.failures_file = self.storage_path / "failure_modes.json"
    
    def track_agent_behavior(
        self,
        session_id: str,
        agent_type: str,
        tools_used: List[str],
        reasoning_steps: List[str],
        outcome: str,
        success: bool
    ):
        """Track a single agent execution for pattern detection"""
        
        behavior_record = {
            "session_id": session_id,
            "agent_type": agent_type,
            "tools_used": tools_used,
            "num_reasoning_steps": len(reasoning_steps),
            "reasoning_depth": self._analyze_reasoning_depth(reasoning_steps),
            "outcome": outcome,
            "success": success,
            "timestamp": datetime.utcnow().isoformat(),
            
            # Pattern detection
            "tool_sequence": " -> ".join(tools_used) if tools_used else "none",
            "used_fallback": "fallback" in str(reasoning_steps).lower(),
            "self_corrected": self._detect_self_correction(reasoning_steps),
            "showed_uncertainty": self._detect_uncertainty(reasoning_steps)
        }
        
        with open(self.behaviors_file, "a") as f:
            f.write(json.dumps(behavior_record) + "\n")
    
    def _analyze_reasoning_depth(self, reasoning_steps: List[str]) -> int:
        """Analyze depth of reasoning (nested if-then, counterfactuals)"""
        depth = 0
        for step in reasoning_steps:
            step_lower = step.lower()
            # Look for nested reasoning indicators
            if "because" in step_lower:
                depth += 1
            if "if" in step_lower and "then" in step_lower:
                depth += 1
            if "would have" in step_lower or "could have" in step_lower:
                depth += 1  # Counterfactual reasoning
        
        return depth
    
    def _detect_self_correction(self, reasoning_steps: List[str]) -> bool:
        """Detect if agent corrected its own reasoning"""
        correction_indicators = [
            "wait", "actually", "correction", "revised", "on second thought",
            "reconsider", "mistake", "incorrect assumption"
        ]
        
        for step in reasoning_steps:
            step_lower = step.lower()
            if any(indicator in step_lower for indicator in correction_indicators):
                return True
        
        return False
    
    def _detect_uncertainty(self, reasoning_steps: List[str]) -> bool:
        """Detect expressions of uncertainty"""
        uncertainty_indicators = [
            "uncertain", "not sure", "unclear", "might", "possibly",
            "perhaps", "maybe", "unsure", "ambiguous"
        ]
        
        for step in reasoning_steps:
            step_lower = step.lower()
            if any(indicator in step_lower for indicator in uncertainty_indicators):
                return True
        
        return False
    
    def detect_emergent_capabilities(self, lookback_days: int = 7) -> List[EmergentCapability]:
        """Detect capabilities that emerged without explicit training"""
        
        if not self.behaviors_file.exists():
            return []
        
        # Load recent behaviors
        cutoff_date = datetime.utcnow() - timedelta(days=lookback_days)
        behaviors = []
        
        with open(self.behaviors_file, "r") as f:
            for line in f:
                record = json.loads(line)
                record_date = datetime.fromisoformat(record["timestamp"])
                if record_date >= cutoff_date:
                    behaviors.append(record)
        
        if not behaviors:
            return []
        
        emergent_capabilities = []
        
        # 1. Tool Use Emergence
        tool_sequences = [b["tool_sequence"] for b in behaviors if b["tool_sequence"] != "none"]
        if tool_sequences:
            tool_counter = Counter(tool_sequences)
            # Find novel tool combinations (used multiple times but not hardcoded)
            for sequence, count in tool_counter.most_common(10):
                if count >= 3 and " -> " in sequence:  # Multi-tool sequence
                    emergent_capabilities.append(EmergentCapability(
                        capability_id=f"tool_combo_{hash(sequence)}",
                        name=f"Tool Combination: {sequence}",
                        description=f"Agent discovered effective tool sequence: {sequence}",
                        first_observed=datetime.utcnow(),
                        observation_count=count,
                        confidence=min(1.0, count / 10.0),
                        capability_type="tool_use",
                        is_beneficial=True
                    ))
        
        # 2. Self-Correction Emergence
        self_corrections = sum(1 for b in behaviors if b.get("self_corrected", False))
        if self_corrections >= 5:
            emergent_capabilities.append(EmergentCapability(
                capability_id="self_correction",
                name="Self-Correction",
                description="Agent spontaneously corrects its own reasoning mid-execution",
                first_observed=datetime.utcnow(),
                observation_count=self_corrections,
                confidence=min(1.0, self_corrections / 20.0),
                capability_type="reasoning",
                is_beneficial=True
            ))
        
        # 3. Uncertainty Expression
        uncertainty_expressions = sum(1 for b in behaviors if b.get("showed_uncertainty", False))
        if uncertainty_expressions >= 5:
            emergent_capabilities.append(EmergentCapability(
                capability_id="uncertainty_awareness",
                name="Uncertainty Awareness",
                description="Agent recognizes and expresses uncertainty appropriately",
                first_observed=datetime.utcnow(),
                observation_count=uncertainty_expressions,
                confidence=min(1.0, uncertainty_expressions / 15.0),
                capability_type="reasoning",
                is_beneficial=True
            ))
        
        # 4. Deep Reasoning Emergence
        avg_depth = sum(b.get("reasoning_depth", 0) for b in behaviors) / len(behaviors)
        if avg_depth > 3:
            emergent_capabilities.append(EmergentCapability(
                capability_id="deep_reasoning",
                name="Deep Counterfactual Reasoning",
                description=f"Agent exhibits deep reasoning with avg depth {avg_depth:.1f}",
                first_observed=datetime.utcnow(),
                observation_count=len(behaviors),
                confidence=min(1.0, avg_depth / 5.0),
                capability_type="reasoning",
                is_beneficial=True
            ))
        
        return emergent_capabilities
    
    def detect_failure_modes(self, lookback_days: int = 7) -> List[FailureMode]:
        """Detect problematic emergent behaviors (deception, reward hacking, etc.)"""
        
        if not self.behaviors_file.exists():
            return []
        
        cutoff_date = datetime.utcnow() - timedelta(days=lookback_days)
        behaviors = []
        
        with open(self.behaviors_file, "r") as f:
            for line in f:
                record = json.loads(line)
                record_date = datetime.fromisoformat(record["timestamp"])
                if record_date >= cutoff_date:
                    behaviors.append(record)
        
        if not behaviors:
            return []
        
        failure_modes = []
        
        # 1. Tool Overuse (potential reward hacking)
        tool_usage_by_session = defaultdict(int)
        for b in behaviors:
            if b["tools_used"]:
                tool_usage_by_session[b["session_id"]] = len(b["tools_used"])
        
        excessive_tool_use = sum(1 for count in tool_usage_by_session.values() if count > 5)
        if excessive_tool_use >= 10:
            failure_modes.append(FailureMode(
                mode_id="tool_overuse",
                failure_type="reward_hacking",
                severity="medium",
                occurrences=excessive_tool_use,
                impact="Agent may be calling tools unnecessarily to appear thorough",
                mitigation="Add tool usage cost penalty or limit max tool calls"
            ))
        
        # 2. Reasoning Loops (gets stuck)
        long_reasoning = sum(1 for b in behaviors if b.get("num_reasoning_steps", 0) > 10)
        if long_reasoning >= 5:
            failure_modes.append(FailureMode(
                mode_id="reasoning_loop",
                failure_type="reasoning_loop",
                severity="medium",
                occurrences=long_reasoning,
                impact="Agent may be stuck in circular reasoning",
                mitigation="Implement max reasoning steps limit and loop detection"
            ))
        
        # 3. Consistent Failures
        failed_sessions = sum(1 for b in behaviors if not b.get("success", True))
        if failed_sessions / len(behaviors) > 0.3:  # >30% failure rate
            failure_modes.append(FailureMode(
                mode_id="high_failure_rate",
                failure_type="capability_degradation",
                severity="high",
                occurrences=failed_sessions,
                impact=f"High failure rate: {failed_sessions/len(behaviors)*100:.1f}%",
                mitigation="Investigate root cause, check prompt quality, retrain if needed"
            ))
        
        return failure_modes
    
    def get_behavior_summary(self, lookback_days: int = 7) -> Dict:
        """Get summary of agent behaviors"""
        
        emergent_capabilities = self.detect_emergent_capabilities(lookback_days)
        failure_modes = self.detect_failure_modes(lookback_days)
        
        # Load recent behaviors for statistics
        if not self.behaviors_file.exists():
            return {
                "emergent_capabilities": [],
                "failure_modes": [],
                "total_observations": 0
            }
        
        cutoff_date = datetime.utcnow() - timedelta(days=lookback_days)
        behaviors = []
        
        with open(self.behaviors_file, "r") as f:
            for line in f:
                record = json.loads(line)
                record_date = datetime.fromisoformat(record["timestamp"])
                if record_date >= cutoff_date:
                    behaviors.append(record)
        
        # Calculate statistics
        total = len(behaviors)
        successful = sum(1 for b in behaviors if b.get("success", False))
        avg_tools = sum(len(b.get("tools_used", [])) for b in behaviors) / total if total > 0 else 0
        avg_reasoning_steps = sum(b.get("num_reasoning_steps", 0) for b in behaviors) / total if total > 0 else 0
        
        return {
            "emergent_capabilities": [c.model_dump() for c in emergent_capabilities],
            "failure_modes": [f.model_dump() for f in failure_modes],
            "total_observations": total,
            "success_rate": successful / total if total > 0 else 0,
            "avg_tools_per_session": avg_tools,
            "avg_reasoning_steps": avg_reasoning_steps,
            "lookback_days": lookback_days
        }


# Global instance
emergent_monitor = EmergentBehaviorMonitor()
