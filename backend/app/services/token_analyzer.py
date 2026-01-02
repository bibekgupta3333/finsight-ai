"""
Token analysis and context window management service.

Implements tokenization analysis, context window validation,
and prompt optimization for Mistral-based LLMs.
"""

import logging
from typing import Dict, List, Optional

import tiktoken

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class TokenAnalyzer:
    """
    Token analysis and context management service.

    Features:
    - Token counting using tiktoken (approximates Mistral tokenizer)
    - Context window validation (8192 tokens for Mistral)
    - Prompt length optimization with smart truncation
    - Token budget allocation for system vs user content
    - Context overflow handling
    """

    def __init__(self):
        """Initialize token analyzer with tiktoken encoder."""
        # Use cl100k_base as approximation for Mistral tokenizer
        # (Mistral uses similar tokenization to GPT-3.5/4)
        try:
            self.encoder = tiktoken.get_encoding("cl100k_base")
            logger.info("Initialized token analyzer with cl100k_base encoding")
        except Exception as e:
            logger.error(f"Failed to load tiktoken encoder: {e}")
            self.encoder = None

        self.max_context_tokens = settings.max_context_tokens
        self.max_prompt_tokens = settings.max_prompt_tokens

    def count_tokens(self, text: str) -> int:
        """
        Count tokens in text.

        Args:
            text: Text to tokenize

        Returns:
            Number of tokens
        """
        if not self.encoder:
            # Fallback: rough approximation (1 token ~= 4 characters)
            return len(text) // 4

        try:
            tokens = self.encoder.encode(text)
            return len(tokens)
        except Exception as e:
            logger.error(f"Token counting failed: {e}")
            return len(text) // 4

    def count_tokens_messages(self, messages: List[Dict[str, str]]) -> int:
        """
        Count tokens in a list of messages.

        Args:
            messages: List of message dicts with 'role' and 'content'

        Returns:
            Total token count
        """
        total_tokens = 0
        for message in messages:
            # Add tokens for message formatting
            total_tokens += 4  # Message overhead
            total_tokens += self.count_tokens(message.get("content", ""))
            total_tokens += self.count_tokens(message.get("role", ""))
        total_tokens += 2  # Assistant response priming
        return total_tokens

    def validate_context_window(
        self, messages: List[Dict[str, str]], max_tokens: Optional[int] = None
    ) -> Dict[str, any]:
        """
        Validate if messages fit within context window.

        Args:
            messages: List of messages
            max_tokens: Maximum tokens (default from settings)

        Returns:
            Dictionary with validation results:
            - is_valid: bool
            - total_tokens: int
            - max_tokens: int
            - usage_percent: float
            - overflow_tokens: int (if invalid)
        """
        max_tokens = max_tokens or self.max_context_tokens
        total_tokens = self.count_tokens_messages(messages)
        usage_percent = (total_tokens / max_tokens) * 100

        result = {
            "is_valid": total_tokens <= max_tokens,
            "total_tokens": total_tokens,
            "max_tokens": max_tokens,
            "usage_percent": round(usage_percent, 2),
        }

        if not result["is_valid"]:
            result["overflow_tokens"] = total_tokens - max_tokens
            logger.warning(f"Context overflow: {total_tokens} tokens exceeds limit of {max_tokens}")

        return result

    def optimize_prompt(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        preserve_start: int = 200,
        preserve_end: int = 200,
    ) -> Dict[str, any]:
        """
        Optimize prompt length by intelligent truncation.

        Strategy: Preserve start (context) and end (question),
        truncate middle content if necessary.

        Args:
            prompt: Original prompt
            max_tokens: Target max tokens (default from settings)
            preserve_start: Chars to preserve from start
            preserve_end: Chars to preserve from end

        Returns:
            Dictionary with:
            - optimized_prompt: str
            - original_tokens: int
            - optimized_tokens: int
            - was_truncated: bool
            - truncated_chars: int
        """
        max_tokens = max_tokens or self.max_prompt_tokens
        original_tokens = self.count_tokens(prompt)

        if original_tokens <= max_tokens:
            return {
                "optimized_prompt": prompt,
                "original_tokens": original_tokens,
                "optimized_tokens": original_tokens,
                "was_truncated": False,
                "truncated_chars": 0,
            }

        # Truncate middle, preserve start and end
        if len(prompt) > (preserve_start + preserve_end + 100):
            start = prompt[:preserve_start]
            end = prompt[-preserve_end:]
            optimized = f"{start}\n\n[... content truncated for context management ...]\n\n{end}"
        else:
            # If too short, just take first max_tokens worth
            partial_text = prompt
            while self.count_tokens(partial_text) > max_tokens:
                # Binary search-like reduction
                partial_text = partial_text[: int(len(partial_text) * 0.9)]
            optimized = partial_text + "\n[... truncated ...]"

        optimized_tokens = self.count_tokens(optimized)
        truncated_chars = len(prompt) - len(optimized)

        logger.info(
            f"Prompt optimized: {original_tokens} → {optimized_tokens} tokens "
            f"({truncated_chars} chars removed)"
        )

        return {
            "optimized_prompt": optimized,
            "original_tokens": original_tokens,
            "optimized_tokens": optimized_tokens,
            "was_truncated": True,
            "truncated_chars": truncated_chars,
        }

    def allocate_token_budget(
        self,
        system_prompt: str,
        user_content: str,
        max_total: Optional[int] = None,
        max_response_tokens: int = 500,
    ) -> Dict[str, any]:
        """
        Allocate token budget between system, user, and response.

        Args:
            system_prompt: System prompt text
            user_content: User content text
            max_total: Maximum total tokens (default from settings)
            max_response_tokens: Reserved tokens for response

        Returns:
            Dictionary with budget allocation and optimization suggestions
        """
        max_total = max_total or self.max_context_tokens

        system_tokens = self.count_tokens(system_prompt)
        user_tokens = self.count_tokens(user_content)
        overhead_tokens = 10  # Message formatting overhead

        total_input_tokens = system_tokens + user_tokens + overhead_tokens
        available_for_response = max_total - total_input_tokens

        budget = {
            "system_tokens": system_tokens,
            "user_tokens": user_tokens,
            "overhead_tokens": overhead_tokens,
            "total_input_tokens": total_input_tokens,
            "available_for_response": max(0, available_for_response),
            "requested_response_tokens": max_response_tokens,
            "max_total_tokens": max_total,
        }

        # Check if we need to optimize
        if available_for_response < max_response_tokens:
            tokens_to_free = max_response_tokens - available_for_response
            budget["needs_optimization"] = True
            budget["tokens_to_free"] = tokens_to_free
            budget["suggestions"] = []

            # Suggest optimizations
            if user_tokens > self.max_prompt_tokens:
                budget["suggestions"].append(
                    f"Reduce user content by ~{tokens_to_free} tokens (currently {user_tokens})"
                )
            if system_tokens > 300:
                budget["suggestions"].append(
                    "Consider compressing system prompt (currently {system_tokens} tokens)"
                )
        else:
            budget["needs_optimization"] = False

        return budget

    def analyze_prompt_complexity(self, prompt: str) -> Dict[str, any]:
        """
        Analyze prompt complexity and provide insights.

        Args:
            prompt: Prompt to analyze

        Returns:
            Complexity analysis with metrics and recommendations
        """
        tokens = self.count_tokens(prompt)
        chars = len(prompt)
        lines = prompt.count("\n") + 1
        words = len(prompt.split())

        # Estimate complexity
        avg_chars_per_token = chars / tokens if tokens > 0 else 0
        avg_words_per_line = words / lines if lines > 0 else 0

        complexity = "low"
        if tokens > 1000 or lines > 50:
            complexity = "high"
        elif tokens > 500 or lines > 20:
            complexity = "medium"

        return {
            "tokens": tokens,
            "characters": chars,
            "lines": lines,
            "words": words,
            "avg_chars_per_token": round(avg_chars_per_token, 2),
            "avg_words_per_line": round(avg_words_per_line, 2),
            "complexity": complexity,
            "context_usage_percent": round((tokens / self.max_context_tokens) * 100, 2),
            "recommendations": self._get_recommendations(tokens, lines, complexity),
        }

    def _get_recommendations(self, tokens: int, lines: int, complexity: str) -> List[str]:
        """Generate optimization recommendations."""
        recommendations = []

        if tokens > self.max_prompt_tokens:
            recommendations.append(
                f"Prompt exceeds recommended length ({self.max_prompt_tokens} tokens). "
                "Consider using prompt compression."
            )

        if lines > 30:
            recommendations.append(
                "High line count may indicate structured data. "
                "Consider extracting key fields only."
            )

        if complexity == "high":
            recommendations.append(
                "High complexity prompt. Consider breaking into multiple steps "
                "or using chain-of-thought prompting."
            )

        if tokens < 50:
            recommendations.append(
                "Very short prompt. Consider adding more context or examples " "for better results."
            )

        return recommendations


# Global instance
_token_analyzer: Optional[TokenAnalyzer] = None


def get_token_analyzer() -> TokenAnalyzer:
    """
    Get global token analyzer instance.

    Returns:
        TokenAnalyzer instance
    """
    global _token_analyzer
    if _token_analyzer is None:
        _token_analyzer = TokenAnalyzer()
    return _token_analyzer
