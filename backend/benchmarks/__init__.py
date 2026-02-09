"""
Benchmark Suite for Multi-Agent Fraud Detection.

This module provides comprehensive benchmarking infrastructure to compare:
- Classical ML models (XGBoost, LightGBM, RandomForest)
- Rule-based heuristics
- Single-agent LLM systems
- Multi-agent systems

For thesis research and validation.
"""

from .baselines import (
    BaselineEvaluator,
    MLBaseline,
    RuleBasedBaseline,
    SingleAgentBaseline
)
from .runner import BenchmarkRunner

__all__ = [
    "BaselineEvaluator",
    "MLBaseline",
    "RuleBasedBaseline",
    "SingleAgentBaseline",
    "BenchmarkRunner"
]
