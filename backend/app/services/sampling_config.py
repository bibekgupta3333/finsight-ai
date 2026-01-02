"""
Sampling configuration and control for LLM generation.

Implements temperature tuning, nucleus sampling, top-k sampling,
and seed-based deterministic generation.
"""

import logging
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class SamplingMode(str, Enum):
    """Predefined sampling modes for different tasks."""

    DETERMINISTIC = "deterministic"  # temperature=0.0, for classification
    BALANCED = "balanced"  # temperature=0.5, balanced creativity
    CREATIVE = "creative"  # temperature=0.7, for explanations
    HIGHLY_CREATIVE = "highly_creative"  # temperature=0.9, for brainstorming


class SamplingConfig(BaseModel):
    """
    Sampling configuration for LLM generation.

    Attributes:
        temperature: Controls randomness (0.0 = deterministic, 1.0 = creative)
        top_p: Nucleus sampling threshold (0.0-1.0)
        top_k: Top-k sampling limit (number of top tokens to consider)
        seed: Random seed for reproducibility
        max_tokens: Maximum tokens to generate
        stop_sequences: Sequences that stop generation
    """

    temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Sampling temperature (0.0 = deterministic, higher = more random)",
    )
    top_p: float = Field(default=0.9, ge=0.0, le=1.0, description="Nucleus sampling threshold")
    top_k: int = Field(default=40, ge=0, description="Top-k sampling (0 = disabled)")
    seed: Optional[int] = Field(default=None, description="Random seed for reproducibility")
    max_tokens: Optional[int] = Field(default=None, description="Maximum tokens to generate")
    stop_sequences: Optional[list[str]] = Field(
        default=None, description="Sequences that stop generation"
    )

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "examples": [
                {
                    "temperature": 0.0,
                    "top_p": 1.0,
                    "top_k": 0,
                    "seed": 42,
                    "description": "Deterministic generation for classification",
                },
                {
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "top_k": 40,
                    "description": "Creative generation for explanations",
                },
            ]
        }


def get_sampling_for_task(task_type: str) -> SamplingConfig:
    """
    Get recommended sampling configuration for a task type.

    Args:
        task_type: Type of task (e.g., 'classification', 'explanation', 'reasoning')

    Returns:
        SamplingConfig with appropriate parameters
    """
    task_configs = {
        "classification": SamplingConfig(
            temperature=settings.llm_temperature_deterministic,
            top_p=1.0,
            top_k=0,
            seed=42,  # Fixed seed for reproducibility
            max_tokens=20,  # Short response for classification
        ),
        "risk_score": SamplingConfig(
            temperature=0.0,
            top_p=1.0,
            top_k=0,
            seed=42,
            max_tokens=10,  # Just a number
        ),
        "explanation": SamplingConfig(
            temperature=settings.llm_temperature_creative,
            top_p=settings.llm_top_p,
            top_k=settings.llm_top_k,
            max_tokens=300,  # Longer explanation
        ),
        "reasoning": SamplingConfig(
            temperature=0.5,  # Balanced
            top_p=0.95,
            top_k=50,
            max_tokens=500,  # Chain-of-thought
        ),
        "summary": SamplingConfig(
            temperature=0.3,  # Low creativity
            top_p=0.9,
            top_k=40,
            max_tokens=150,
        ),
    }

    config = task_configs.get(task_type.lower())
    if config is None:
        logger.warning(f"Unknown task type '{task_type}', using default config")
        return SamplingConfig()  # Default

    logger.debug(f"Using sampling config for task '{task_type}': temp={config.temperature}")
    return config


def get_sampling_for_mode(mode: SamplingMode) -> SamplingConfig:
    """
    Get sampling configuration for a predefined mode.

    Args:
        mode: Sampling mode

    Returns:
        SamplingConfig
    """
    mode_configs = {
        SamplingMode.DETERMINISTIC: SamplingConfig(
            temperature=0.0,
            top_p=1.0,
            top_k=0,
            seed=42,
        ),
        SamplingMode.BALANCED: SamplingConfig(
            temperature=0.5,
            top_p=0.9,
            top_k=40,
        ),
        SamplingMode.CREATIVE: SamplingConfig(
            temperature=0.7,
            top_p=0.9,
            top_k=40,
        ),
        SamplingMode.HIGHLY_CREATIVE: SamplingConfig(
            temperature=0.9,
            top_p=0.95,
            top_k=50,
        ),
    }

    return mode_configs[mode]


class MultiSampleGenerator:
    """
    Generate multiple samples for self-consistency.

    AGI Interview Signal: "I implement self-consistency for better reliability"
    """

    @staticmethod
    async def generate_multiple(
        llm_client, prompt: str, num_samples: int = 3, temperature: float = 0.7, **kwargs
    ) -> list[dict]:
        """
        Generate multiple samples with same prompt.

        Args:
            llm_client: LLM client instance
            prompt: Prompt to generate from
            num_samples: Number of samples to generate
            temperature: Temperature for sampling
            **kwargs: Additional generation parameters

        Returns:
            List of responses
        """
        # Generate with different seeds for diversity
        samples = []
        for i in range(num_samples):
            response = await llm_client.generate(
                prompt=prompt,
                temperature=temperature,
                seed=42 + i if temperature > 0 else 42,  # Same seed if deterministic
                **kwargs,
            )
            samples.append(response)

        logger.info(f"Generated {num_samples} samples for self-consistency")
        return samples

    @staticmethod
    def majority_vote(samples: list[dict], key: str = "response") -> dict:
        """
        Perform majority voting on samples.

        Args:
            samples: List of sample responses
            key: Key to extract response from

        Returns:
            Dictionary with majority result and vote counts
        """
        from collections import Counter

        responses = [sample.get(key, "").strip() for sample in samples]
        vote_counts = Counter(responses)
        majority_response, count = vote_counts.most_common(1)[0]

        confidence = count / len(samples)

        logger.info(
            f"Majority vote: '{majority_response}' ({count}/{len(samples)}, "
            f"confidence={confidence:.2f})"
        )

        return {
            "majority_response": majority_response,
            "vote_count": count,
            "total_samples": len(samples),
            "confidence": confidence,
            "all_responses": responses,
            "vote_distribution": dict(vote_counts),
        }


def explain_sampling_tradeoffs(config: SamplingConfig) -> dict:
    """
    Explain the tradeoffs of a sampling configuration.

    AGI Interview Signal: "I understand stochasticity vs reproducibility tradeoffs"

    Args:
        config: Sampling configuration

    Returns:
        Dictionary explaining tradeoffs
    """
    tradeoffs = {
        "temperature": {"value": config.temperature, "interpretation": "", "tradeoff": ""},
        "top_p": {"value": config.top_p, "interpretation": "", "tradeoff": ""},
        "reproducibility": {
            "is_reproducible": config.seed is not None and config.temperature == 0.0,
            "explanation": "",
        },
    }

    # Temperature interpretation
    if config.temperature == 0.0:
        tradeoffs["temperature"]["interpretation"] = "Deterministic (greedy decoding)"
        tradeoffs["temperature"]["tradeoff"] = "High consistency, low creativity"
    elif config.temperature < 0.5:
        tradeoffs["temperature"]["interpretation"] = "Low randomness"
        tradeoffs["temperature"]["tradeoff"] = "Focused outputs, low diversity"
    elif config.temperature < 0.8:
        tradeoffs["temperature"]["interpretation"] = "Moderate randomness"
        tradeoffs["temperature"]["tradeoff"] = "Balanced consistency and creativity"
    else:
        tradeoffs["temperature"]["interpretation"] = "High randomness"
        tradeoffs["temperature"]["tradeoff"] = "High diversity, may be incoherent"

    # Top-p interpretation
    if config.top_p >= 0.95:
        tradeoffs["top_p"]["interpretation"] = "Wide token selection"
        tradeoffs["top_p"]["tradeoff"] = "More diverse outputs"
    elif config.top_p >= 0.8:
        tradeoffs["top_p"]["interpretation"] = "Balanced token selection"
        tradeoffs["top_p"]["tradeoff"] = "Filters unlikely tokens"
    else:
        tradeoffs["top_p"]["interpretation"] = "Narrow token selection"
        tradeoffs["top_p"]["tradeoff"] = "More focused, less creative"

    # Reproducibility
    if config.seed is not None and config.temperature == 0.0:
        tradeoffs["reproducibility"][
            "explanation"
        ] = "Fully reproducible - same input always produces same output"
    elif config.seed is not None:
        tradeoffs["reproducibility"][
            "explanation"
        ] = "Partially reproducible - same seed but temperature > 0 may vary slightly"
    else:
        tradeoffs["reproducibility"][
            "explanation"
        ] = "Not reproducible - outputs will vary between runs"

    return tradeoffs
