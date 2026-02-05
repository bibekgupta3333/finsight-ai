"""
Sampling Strategy Optimization Service
Provides temperature scheduling, top-p tuning, penalty configuration, and early stopping strategies
Optimized for fraud detection use cases with M4 Pro constraints
"""

import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Literal, Tuple
from pydantic import BaseModel, Field
import math


# ==================== Models ====================

class SamplingConfig(BaseModel):
    """Complete sampling configuration"""
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Randomness (0=deterministic, 1=balanced, 2=creative)")
    top_p: float = Field(default=0.9, ge=0.0, le=1.0, description="Nucleus sampling threshold")
    top_k: int = Field(default=50, ge=0, le=100, description="Top-k sampling limit")
    repetition_penalty: float = Field(default=1.1, ge=1.0, le=2.0, description="Penalty for repetition")
    length_penalty: float = Field(default=1.0, ge=0.0, le=2.0, description="Penalty for length")
    max_tokens: int = Field(default=512, ge=1, le=4096, description="Maximum tokens to generate")
    stop_sequences: List[str] = Field(default_factory=list, description="Early stopping sequences")


class TemperatureSchedule(BaseModel):
    """Temperature scheduling over time/steps"""
    schedule_type: Literal["static", "linear", "exponential", "cosine", "adaptive"] = Field(..., description="Schedule type")
    initial_temp: float = Field(..., description="Starting temperature")
    final_temp: float = Field(..., description="Ending temperature")
    steps: int = Field(..., description="Number of steps")
    current_step: int = Field(default=0, description="Current step")
    temperatures: List[float] = Field(default_factory=list, description="Temperature values per step")


class SamplingRecommendation(BaseModel):
    """Recommended sampling parameters for a use case"""
    use_case: str = Field(..., description="Use case description")
    recommended_config: SamplingConfig = Field(..., description="Recommended configuration")
    reasoning: List[str] = Field(default_factory=list, description="Why these parameters")
    tradeoffs: Dict[str, str] = Field(default_factory=dict, description="Parameter tradeoffs")
    alternatives: List[SamplingConfig] = Field(default_factory=list, description="Alternative configs")


class ParameterComparison(BaseModel):
    """Comparison between parameter configurations"""
    config_a: SamplingConfig = Field(..., description="First configuration")
    config_b: SamplingConfig = Field(..., description="Second configuration")
    differences: Dict[str, Any] = Field(default_factory=dict, description="Parameter differences")
    use_case_fit: Dict[str, Dict[str, Any]] = Field(default_factory=dict, description="Fit scores for use cases")
    recommendation: str = Field(..., description="Which config to use when")


class ValidationResult(BaseModel):
    """Sampling parameter validation result"""
    is_valid: bool = Field(..., description="Whether parameters are valid")
    issues: List[str] = Field(default_factory=list, description="Validation issues")
    warnings: List[str] = Field(default_factory=list, description="Warnings")
    suggestions: List[str] = Field(default_factory=list, description="Improvement suggestions")


class EarlyStoppingStrategy(BaseModel):
    """Early stopping configuration"""
    strategy_type: Literal["stop_sequences", "max_tokens", "confidence_threshold", "repetition_detection", "combined"] = Field(..., description="Stopping strategy")
    stop_sequences: List[str] = Field(default_factory=list, description="Sequences that trigger stop")
    max_tokens: int = Field(default=512, description="Maximum tokens")
    confidence_threshold: float = Field(default=0.9, description="Confidence threshold for early stop")
    repetition_window: int = Field(default=10, description="Window for repetition detection")
    enabled: bool = Field(default=True, description="Whether strategy is enabled")


# ==================== Sampling Optimizer Service ====================

class SamplingOptimizer:
    """
    Sampling strategy optimization for LLM inference
    Provides parameter recommendations, scheduling, and validation
    """

    def __init__(self):
        self.data_dir = Path("data/sampling")
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Use case templates
        self.use_case_templates = {
            "fraud_detection": {
                "temperature": 0.3,
                "top_p": 0.85,
                "top_k": 40,
                "repetition_penalty": 1.2,
                "length_penalty": 1.0,
                "max_tokens": 256,
                "stop_sequences": ["</decision>", "\n\n\n"],
                "reasoning": [
                    "Low temperature (0.3) for consistent, deterministic decisions",
                    "High top_p (0.85) to consider multiple fraud indicators",
                    "Strong repetition penalty (1.2) to avoid circular reasoning",
                    "Short max_tokens (256) for concise fraud assessments"
                ],
                "tradeoffs": {
                    "accuracy_vs_speed": "Prioritizes accuracy over speed",
                    "diversity_vs_consistency": "Prioritizes consistency",
                    "detail_vs_conciseness": "Balanced"
                }
            },
            "fraud_explanation": {
                "temperature": 0.5,
                "top_p": 0.9,
                "top_k": 50,
                "repetition_penalty": 1.15,
                "length_penalty": 0.9,
                "max_tokens": 512,
                "stop_sequences": ["</explanation>"],
                "reasoning": [
                    "Medium temperature (0.5) for clear but varied explanations",
                    "High top_p (0.9) for comprehensive reasoning",
                    "Moderate repetition penalty (1.15) to avoid redundancy",
                    "Length penalty (0.9) encourages thorough explanations"
                ],
                "tradeoffs": {
                    "accuracy_vs_speed": "Balanced",
                    "diversity_vs_consistency": "Slight diversity preference",
                    "detail_vs_conciseness": "Prioritizes detail"
                }
            },
            "creative_fraud_scenarios": {
                "temperature": 0.8,
                "top_p": 0.95,
                "top_k": 60,
                "repetition_penalty": 1.1,
                "length_penalty": 1.0,
                "max_tokens": 1024,
                "stop_sequences": ["</scenario>"],
                "reasoning": [
                    "High temperature (0.8) for diverse fraud scenarios",
                    "Very high top_p (0.95) for creative combinations",
                    "Low repetition penalty (1.1) allows pattern variations",
                    "Large max_tokens (1024) for detailed scenarios"
                ],
                "tradeoffs": {
                    "accuracy_vs_speed": "Speed is secondary",
                    "diversity_vs_consistency": "Prioritizes diversity",
                    "detail_vs_conciseness": "Prioritizes detail"
                }
            },
            "quick_classification": {
                "temperature": 0.1,
                "top_p": 0.8,
                "top_k": 30,
                "repetition_penalty": 1.3,
                "length_penalty": 1.2,
                "max_tokens": 64,
                "stop_sequences": ["FRAUD", "LEGITIMATE", "\n"],
                "reasoning": [
                    "Very low temperature (0.1) for deterministic classification",
                    "Lower top_p (0.8) for focused decisions",
                    "High length penalty (1.2) for brevity",
                    "Tiny max_tokens (64) for instant responses"
                ],
                "tradeoffs": {
                    "accuracy_vs_speed": "Prioritizes speed",
                    "diversity_vs_consistency": "Maximum consistency",
                    "detail_vs_conciseness": "Maximum conciseness"
                }
            },
            "balanced_analysis": {
                "temperature": 0.7,
                "top_p": 0.9,
                "top_k": 50,
                "repetition_penalty": 1.1,
                "length_penalty": 1.0,
                "max_tokens": 512,
                "stop_sequences": [],
                "reasoning": [
                    "Balanced temperature (0.7) for reliable but varied analysis",
                    "Standard top_p (0.9) for comprehensive coverage",
                    "Moderate penalties (1.1) for natural output",
                    "Standard max_tokens (512) for complete responses"
                ],
                "tradeoffs": {
                    "accuracy_vs_speed": "Balanced",
                    "diversity_vs_consistency": "Balanced",
                    "detail_vs_conciseness": "Balanced"
                }
            }
        }


    def recommend_parameters(
        self,
        use_case: str,
        custom_constraints: Optional[Dict[str, Any]] = None
    ) -> SamplingRecommendation:
        """
        Recommend sampling parameters for a use case

        Args:
            use_case: Use case name or description
            custom_constraints: Optional constraints (e.g., max_tokens < 100)

        Returns:
            SamplingRecommendation with recommended config and reasoning
        """
        # Find matching template or use balanced default
        template = self.use_case_templates.get(use_case.lower().replace(" ", "_"))

        if not template:
            # Use balanced analysis as default
            template = self.use_case_templates["balanced_analysis"]
            use_case = f"Custom: {use_case}"

        # Create base config
        config = SamplingConfig(**{k: v for k, v in template.items() if k not in ["reasoning", "tradeoffs"]})

        # Apply custom constraints
        if custom_constraints:
            for key, value in custom_constraints.items():
                if hasattr(config, key):
                    setattr(config, key, value)

        # Generate alternatives
        alternatives = []

        # Alternative 1: More conservative
        conservative = config.copy()
        conservative.temperature = max(0.1, config.temperature - 0.2)
        conservative.repetition_penalty = min(2.0, config.repetition_penalty + 0.1)
        alternatives.append(conservative)

        # Alternative 2: More creative
        creative = config.copy()
        creative.temperature = min(1.5, config.temperature + 0.3)
        creative.top_p = min(0.98, config.top_p + 0.05)
        alternatives.append(creative)

        # Alternative 3: Faster
        faster = config.copy()
        faster.max_tokens = max(32, config.max_tokens // 2)
        faster.length_penalty = min(2.0, config.length_penalty + 0.2)
        alternatives.append(faster)

        recommendation = SamplingRecommendation(
            use_case=use_case,
            recommended_config=config,
            reasoning=template.get("reasoning", []),
            tradeoffs=template.get("tradeoffs", {}),
            alternatives=alternatives
        )

        # Log recommendation
        self._log_recommendation({
            "timestamp": datetime.now().isoformat(),
            "use_case": use_case,
            "config": config.model_dump(),
            "custom_constraints": custom_constraints
        })

        return recommendation


    def create_temperature_schedule(
        self,
        schedule_type: str,
        initial_temp: float,
        final_temp: float,
        steps: int
    ) -> TemperatureSchedule:
        """
        Create temperature schedule for adaptive sampling

        Args:
            schedule_type: static, linear, exponential, cosine, adaptive
            initial_temp: Starting temperature
            final_temp: Ending temperature
            steps: Number of steps

        Returns:
            TemperatureSchedule with temperature values per step
        """
        temperatures = []

        if schedule_type == "static":
            temperatures = [initial_temp] * steps

        elif schedule_type == "linear":
            # Linear interpolation
            for i in range(steps):
                t = i / (steps - 1) if steps > 1 else 0
                temp = initial_temp + t * (final_temp - initial_temp)
                temperatures.append(round(temp, 3))

        elif schedule_type == "exponential":
            # Exponential decay/growth
            for i in range(steps):
                t = i / (steps - 1) if steps > 1 else 0
                temp = initial_temp * ((final_temp / initial_temp) ** t)
                temperatures.append(round(temp, 3))

        elif schedule_type == "cosine":
            # Cosine annealing
            for i in range(steps):
                t = i / (steps - 1) if steps > 1 else 0
                temp = final_temp + (initial_temp - final_temp) * (1 + math.cos(math.pi * t)) / 2
                temperatures.append(round(temp, 3))

        elif schedule_type == "adaptive":
            # Adaptive: high at start, low at middle, medium at end
            for i in range(steps):
                t = i / (steps - 1) if steps > 1 else 0
                # Use sine wave for adaptive pattern
                temp = final_temp + (initial_temp - final_temp) * abs(math.sin(math.pi * t))
                temperatures.append(round(temp, 3))

        else:
            # Default to linear
            temperatures = [initial_temp + i * (final_temp - initial_temp) / (steps - 1) for i in range(steps)]
            temperatures = [round(t, 3) for t in temperatures]

        schedule = TemperatureSchedule(
            schedule_type=schedule_type,
            initial_temp=initial_temp,
            final_temp=final_temp,
            steps=steps,
            temperatures=temperatures
        )

        # Log schedule
        self._log_schedule({
            "timestamp": datetime.now().isoformat(),
            "schedule_type": schedule_type,
            "steps": steps,
            "temperature_range": [initial_temp, final_temp]
        })

        return schedule


    def validate_parameters(
        self,
        config: Dict[str, Any],
        use_case: Optional[str] = None
    ) -> ValidationResult:
        """
        Validate sampling parameters

        Args:
            config: Parameter configuration
            use_case: Optional use case for context-specific validation

        Returns:
            ValidationResult with issues, warnings, suggestions
        """
        issues = []
        warnings = []
        suggestions = []

        # Required parameters
        required = ["temperature", "top_p", "max_tokens"]
        for param in required:
            if param not in config:
                issues.append(f"Missing required parameter: {param}")

        if issues:
            return ValidationResult(is_valid=False, issues=issues, warnings=warnings, suggestions=suggestions)

        # Validate ranges
        temp = config.get("temperature", 0.7)
        if temp < 0 or temp > 2.0:
            issues.append(f"Temperature {temp} out of range [0.0, 2.0]")
        elif temp > 1.5:
            warnings.append(f"High temperature {temp} may produce incoherent output")
        elif temp < 0.2 and use_case != "quick_classification":
            warnings.append(f"Very low temperature {temp} reduces diversity")

        top_p = config.get("top_p", 0.9)
        if top_p < 0 or top_p > 1.0:
            issues.append(f"Top-p {top_p} out of range [0.0, 1.0]")
        elif top_p < 0.5:
            warnings.append(f"Low top-p {top_p} severely limits vocabulary")

        max_tokens = config.get("max_tokens", 512)
        if max_tokens < 1:
            issues.append(f"Max tokens {max_tokens} must be >= 1")
        elif max_tokens > 2048:
            warnings.append(f"Large max_tokens {max_tokens} increases latency and cost")

        # Validate penalties
        rep_penalty = config.get("repetition_penalty", 1.1)
        if rep_penalty < 1.0:
            issues.append(f"Repetition penalty {rep_penalty} must be >= 1.0")
        elif rep_penalty > 1.5:
            warnings.append(f"High repetition penalty {rep_penalty} may reduce coherence")

        len_penalty = config.get("length_penalty", 1.0)
        if len_penalty < 0:
            issues.append(f"Length penalty {len_penalty} must be >= 0.0")

        # Context-specific validation
        if use_case == "fraud_detection":
            if temp > 0.5:
                suggestions.append("Consider lower temperature (<0.5) for consistent fraud decisions")
            if max_tokens > 512:
                suggestions.append("Consider shorter max_tokens (<512) for faster fraud detection")

        elif use_case == "creative_fraud_scenarios":
            if temp < 0.6:
                suggestions.append("Consider higher temperature (>0.6) for diverse scenarios")
            if top_p < 0.9:
                suggestions.append("Consider higher top_p (>0.9) for creative combinations")

        # Check parameter conflicts
        if temp < 0.3 and top_p > 0.95:
            warnings.append("Low temperature + high top_p may not increase diversity as expected")

        if rep_penalty > 1.4 and len_penalty > 1.3:
            warnings.append("High repetition + length penalties may make output too terse")

        is_valid = len(issues) == 0

        return ValidationResult(
            is_valid=is_valid,
            issues=issues,
            warnings=warnings,
            suggestions=suggestions
        )


    def compare_configs(
        self,
        config_a: Dict[str, Any],
        config_b: Dict[str, Any],
        use_cases: List[str]
    ) -> ParameterComparison:
        """
        Compare two sampling configurations

        Args:
            config_a: First configuration
            config_b: Second configuration
            use_cases: Use cases to evaluate fit

        Returns:
            ParameterComparison with differences and recommendations
        """
        # Convert to SamplingConfig objects
        cfg_a = SamplingConfig(**config_a)
        cfg_b = SamplingConfig(**config_b)

        # Find differences
        differences = {}
        for field in cfg_a.model_fields:
            val_a = getattr(cfg_a, field)
            val_b = getattr(cfg_b, field)
            if val_a != val_b:
                differences[field] = {
                    "config_a": val_a,
                    "config_b": val_b,
                    "delta": val_b - val_a if isinstance(val_a, (int, float)) else None
                }

        # Calculate use case fit scores
        use_case_fit = {}
        for use_case in use_cases:
            template = self.use_case_templates.get(use_case.lower().replace(" ", "_"))
            if template:
                # Simple distance metric
                score_a = self._calculate_fit_score(cfg_a, template)
                score_b = self._calculate_fit_score(cfg_b, template)
                use_case_fit[use_case] = {
                    "config_a_score": round(score_a, 2),
                    "config_b_score": round(score_b, 2),
                    "better_fit": "config_a" if score_a > score_b else "config_b"
                }

        # Generate recommendation
        if cfg_a.temperature < cfg_b.temperature:
            recommendation = "Config A is more conservative (lower temp), Config B is more creative"
        else:
            recommendation = "Config B is more conservative (lower temp), Config A is more creative"

        if cfg_a.max_tokens < cfg_b.max_tokens:
            recommendation += ". Config A is faster (fewer tokens)"
        else:
            recommendation += ". Config B is faster (fewer tokens)"

        return ParameterComparison(
            config_a=cfg_a,
            config_b=cfg_b,
            differences=differences,
            use_case_fit=use_case_fit,
            recommendation=recommendation
        )


    def create_early_stopping_strategy(
        self,
        strategy_type: str,
        **kwargs
    ) -> EarlyStoppingStrategy:
        """
        Create early stopping strategy

        Args:
            strategy_type: stop_sequences, max_tokens, confidence_threshold, repetition_detection, combined
            **kwargs: Strategy-specific parameters

        Returns:
            EarlyStoppingStrategy configuration
        """
        if strategy_type == "stop_sequences":
            stop_sequences = kwargs.get("stop_sequences", ["</output>", "\n\n\n"])
            strategy = EarlyStoppingStrategy(
                strategy_type=strategy_type,
                stop_sequences=stop_sequences,
                enabled=True
            )

        elif strategy_type == "max_tokens":
            max_tokens = kwargs.get("max_tokens", 512)
            strategy = EarlyStoppingStrategy(
                strategy_type=strategy_type,
                max_tokens=max_tokens,
                enabled=True
            )

        elif strategy_type == "confidence_threshold":
            threshold = kwargs.get("confidence_threshold", 0.9)
            strategy = EarlyStoppingStrategy(
                strategy_type=strategy_type,
                confidence_threshold=threshold,
                enabled=True
            )

        elif strategy_type == "repetition_detection":
            window = kwargs.get("repetition_window", 10)
            strategy = EarlyStoppingStrategy(
                strategy_type=strategy_type,
                repetition_window=window,
                enabled=True
            )

        elif strategy_type == "combined":
            strategy = EarlyStoppingStrategy(
                strategy_type=strategy_type,
                stop_sequences=kwargs.get("stop_sequences", ["</output>"]),
                max_tokens=kwargs.get("max_tokens", 512),
                confidence_threshold=kwargs.get("confidence_threshold", 0.9),
                repetition_window=kwargs.get("repetition_window", 10),
                enabled=True
            )

        else:
            # Default to max_tokens
            strategy = EarlyStoppingStrategy(
                strategy_type="max_tokens",
                max_tokens=512,
                enabled=True
            )

        return strategy


    def _calculate_fit_score(self, config: SamplingConfig, template: Dict[str, Any]) -> float:
        """Calculate how well config fits template (0-1 score)"""
        score = 1.0

        # Temperature match (weight: 0.3)
        temp_diff = abs(config.temperature - template.get("temperature", 0.7))
        score -= temp_diff * 0.3

        # Top-p match (weight: 0.2)
        top_p_diff = abs(config.top_p - template.get("top_p", 0.9))
        score -= top_p_diff * 0.2

        # Max tokens match (weight: 0.2)
        max_tokens_diff = abs(config.max_tokens - template.get("max_tokens", 512)) / 512
        score -= min(max_tokens_diff, 1.0) * 0.2

        # Repetition penalty match (weight: 0.15)
        rep_diff = abs(config.repetition_penalty - template.get("repetition_penalty", 1.1))
        score -= rep_diff * 0.15

        # Length penalty match (weight: 0.15)
        len_diff = abs(config.length_penalty - template.get("length_penalty", 1.0))
        score -= len_diff * 0.15

        return max(0.0, min(1.0, score))


    # ==================== Logging ====================

    def _log_recommendation(self, data: Dict[str, Any]):
        """Log parameter recommendation"""
        log_file = self.data_dir / "recommendations.jsonl"
        with open(log_file, "a") as f:
            f.write(json.dumps(data) + "\n")


    def _log_schedule(self, data: Dict[str, Any]):
        """Log temperature schedule"""
        log_file = self.data_dir / "schedules.jsonl"
        with open(log_file, "a") as f:
            f.write(json.dumps(data) + "\n")


# ==================== Service Instance ====================

sampling_optimizer = SamplingOptimizer()
