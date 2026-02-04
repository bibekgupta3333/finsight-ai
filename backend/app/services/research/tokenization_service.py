"""
Tokenization Engineering Service

Analyzes and optimizes token usage for LLM prompts.
Focuses on Mistral tokenizer behavior and efficiency.
"""

import re
import logging
from typing import Dict, List, Any, Optional, Tuple
from pydantic import BaseModel, Field
from collections import Counter
from pathlib import Path
import json

logger = logging.getLogger(__name__)


class TokenAnalysis(BaseModel):
    """Token analysis result"""
    text: str
    token_count: int
    char_count: int
    word_count: int
    tokens_per_word: float
    efficiency_score: float  # 0-1, higher is better
    issues: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)


class OptimizationResult(BaseModel):
    """Prompt optimization result"""
    original_text: str
    optimized_text: str
    original_tokens: int
    optimized_tokens: int
    tokens_saved: int
    savings_percent: float
    optimizations_applied: List[str] = Field(default_factory=list)


class TokenizerBehavior(BaseModel):
    """Tokenizer behavior analysis"""
    tokenizer_name: str
    average_tokens_per_word: float
    common_patterns: Dict[str, int]
    special_tokens: List[str]
    subword_examples: List[Dict[str, Any]]
    efficiency_tips: List[str]


class PromptComparison(BaseModel):
    """Compare multiple prompt variants"""
    variants: List[Dict[str, Any]]
    best_variant_index: int
    best_variant_name: str
    token_savings: int


class TokenizationService:
    """Service for tokenization analysis and optimization"""

    def __init__(self):
        self.data_dir = Path("data/tokenization")
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.analysis_log = self.data_dir / "token_analysis.jsonl"
        self.optimization_log = self.data_dir / "optimizations.jsonl"

        # Common replacements for efficiency
        self.efficiency_replacements = {
            # Verbose phrases -> concise alternatives
            "in order to": "to",
            "due to the fact that": "because",
            "at this point in time": "now",
            "for the purpose of": "to",
            "in the event that": "if",
            "with regard to": "about",
            "prior to": "before",
            "subsequent to": "after",
            "in spite of": "despite",
            "as a result of": "from",
            "take into consideration": "consider",
            "make a decision": "decide",
            "come to a conclusion": "conclude",
            "give consideration to": "consider",
            "is able to": "can",
            "has the ability to": "can",
            "in the near future": "soon",
            "at the present time": "now",
            "during the time that": "while",
            "until such time as": "until",
        }

        # Common fraud detection terms and their token-efficient alternatives
        self.fraud_specific_replacements = {
            "fraudulent transaction": "fraud",
            "suspicious activity": "suspicious",
            "financial transaction": "transaction",
            "account balance": "balance",
            "money transfer": "transfer",
            "payment processing": "payment",
            "user account": "account",
            "transaction amount": "amount",
            "risk assessment": "risk",
            "detection algorithm": "detector",
        }

    # ========== Token Counting (Heuristic) ==========

    def estimate_tokens(self, text: str) -> int:
        """
        Estimate token count using heuristics.

        Mistral tokenizer averages ~0.75 tokens per word in English.
        Special characters and numbers may tokenize differently.

        This is a lightweight approximation - for exact counts,
        use the actual Mistral tokenizer (tiktoken or transformers).
        """
        # Count words
        words = text.split()
        word_count = len(words)

        # Base estimate: 0.75 tokens per word
        base_tokens = int(word_count * 0.75)

        # Adjust for special characters (each counts as ~0.5 tokens)
        special_chars = len(re.findall(r'[^\w\s]', text))
        special_tokens = int(special_chars * 0.5)

        # Adjust for numbers (each digit group counts as ~1 token)
        number_groups = len(re.findall(r'\d+', text))

        # Adjust for code-like syntax
        code_tokens = 0
        if '<|im_start|>' in text or '<|im_end|>' in text:
            code_tokens += 10  # Special tokens
        if '```' in text:
            code_tokens += 5  # Code blocks

        total_estimate = base_tokens + special_tokens + number_groups + code_tokens

        return max(1, total_estimate)

    # ========== Token Analysis ==========

    def analyze_tokens(self, text: str) -> TokenAnalysis:
        """
        Analyze token efficiency of text.

        Returns:
            TokenAnalysis with token count, efficiency score, and recommendations
        """
        # Count tokens, chars, words
        token_count = self.estimate_tokens(text)
        char_count = len(text)
        words = text.split()
        word_count = len(words)

        tokens_per_word = token_count / word_count if word_count > 0 else 0

        # Calculate efficiency score
        # Lower tokens/word is better (ideal ~0.75, poor >1.5)
        if tokens_per_word <= 0.75:
            efficiency_score = 1.0
        elif tokens_per_word <= 1.0:
            efficiency_score = 0.8
        elif tokens_per_word <= 1.5:
            efficiency_score = 0.5
        else:
            efficiency_score = 0.3

        # Detect issues
        issues = []
        recommendations = []

        # Check for repetition
        word_counts = Counter(word.lower() for word in words)
        repeated_words = [word for word, count in word_counts.items() if count > 3 and len(word) > 3]
        if repeated_words:
            issues.append(f"Repetitive words: {', '.join(repeated_words[:5])}")
            recommendations.append("Reduce word repetition to save tokens")

        # Check for verbose phrases
        text_lower = text.lower()
        verbose_found = [phrase for phrase in self.efficiency_replacements if phrase in text_lower]
        if verbose_found:
            issues.append(f"Verbose phrases found: {len(verbose_found)}")
            recommendations.append(f"Replace verbose phrases with concise alternatives")

        # Check for long words (likely to be split into subwords)
        long_words = [word for word in words if len(word) > 12]
        if long_words:
            issues.append(f"{len(long_words)} long words (>12 chars) may tokenize inefficiently")
            recommendations.append("Consider shorter synonyms for long words")

        # Check for excessive punctuation
        punctuation_count = len(re.findall(r'[^\w\s]', text))
        if punctuation_count > word_count * 0.3:
            issues.append("High punctuation density")
            recommendations.append("Simplify punctuation where possible")

        # Check for code/special tokens
        if '<|im_start|>' in text or '<|im_end|>' in text:
            recommendations.append("Special tokens detected - ensure proper formatting")

        result = TokenAnalysis(
            text=text,
            token_count=token_count,
            char_count=char_count,
            word_count=word_count,
            tokens_per_word=round(tokens_per_word, 2),
            efficiency_score=round(efficiency_score, 2),
            issues=issues,
            recommendations=recommendations
        )

        # Log analysis
        self._log_analysis(result)

        return result

    def _log_analysis(self, analysis: TokenAnalysis) -> None:
        """Log token analysis for tracking"""
        with open(self.analysis_log, 'a') as f:
            f.write(analysis.model_dump_json() + '\n')

    # ========== Prompt Optimization ==========

    def optimize_prompt(self, text: str, aggressive: bool = False) -> OptimizationResult:
        """
        Optimize prompt for token efficiency.

        Args:
            text: Original prompt text
            aggressive: If True, apply more aggressive optimizations

        Returns:
            OptimizationResult with optimized text and savings
        """
        original_tokens = self.estimate_tokens(text)
        optimized = text
        optimizations_applied = []

        # 1. Replace verbose phrases
        for verbose, concise in self.efficiency_replacements.items():
            if verbose in optimized.lower():
                # Case-insensitive replacement
                pattern = re.compile(re.escape(verbose), re.IGNORECASE)
                optimized = pattern.sub(concise, optimized)
                optimizations_applied.append(f"'{verbose}' → '{concise}'")

        # 2. Replace fraud-specific verbose terms
        for verbose, concise in self.fraud_specific_replacements.items():
            if verbose in optimized.lower():
                pattern = re.compile(re.escape(verbose), re.IGNORECASE)
                optimized = pattern.sub(concise, optimized)
                optimizations_applied.append(f"'{verbose}' → '{concise}'")

        # 3. Remove redundant words
        if aggressive:
            # Remove filler words
            fillers = ['actually', 'basically', 'literally', 'really', 'very', 'quite', 'rather']
            for filler in fillers:
                pattern = r'\b' + filler + r'\b'
                if re.search(pattern, optimized, re.IGNORECASE):
                    optimized = re.sub(pattern, '', optimized, flags=re.IGNORECASE)
                    optimizations_applied.append(f"Removed filler: '{filler}'")

        # 4. Collapse excessive whitespace
        optimized = re.sub(r'\s+', ' ', optimized)
        optimized = optimized.strip()

        # 5. Remove redundant punctuation
        optimized = re.sub(r'\.{2,}', '.', optimized)  # Multiple periods
        optimized = re.sub(r',{2,}', ',', optimized)   # Multiple commas
        optimized = re.sub(r'\s+([.,!?])', r'\1', optimized)  # Space before punctuation

        optimized_tokens = self.estimate_tokens(optimized)
        tokens_saved = original_tokens - optimized_tokens
        savings_percent = (tokens_saved / original_tokens * 100) if original_tokens > 0 else 0

        result = OptimizationResult(
            original_text=text,
            optimized_text=optimized,
            original_tokens=original_tokens,
            optimized_tokens=optimized_tokens,
            tokens_saved=tokens_saved,
            savings_percent=round(savings_percent, 1),
            optimizations_applied=optimizations_applied
        )

        # Log optimization
        self._log_optimization(result)

        return result

    def _log_optimization(self, result: OptimizationResult) -> None:
        """Log optimization for tracking"""
        with open(self.optimization_log, 'a') as f:
            f.write(result.model_dump_json() + '\n')

    # ========== Tokenizer Behavior Analysis ==========

    def analyze_tokenizer_behavior(self) -> TokenizerBehavior:
        """
        Analyze Mistral tokenizer behavior patterns.

        Returns insights about tokenization patterns and efficiency tips.
        """
        # Common tokenization patterns for Mistral
        common_patterns = {
            "short_words_1_token": 85,      # "the", "is", "a" → 1 token each
            "medium_words_1_2_tokens": 75,   # "fraud", "account" → 1-2 tokens
            "long_words_2_3_tokens": 65,     # "transaction", "suspicious" → 2-3 tokens
            "numbers_1_token": 90,           # "123" → usually 1 token
            "special_chars_05_tokens": 50,   # "!", "@" → ~0.5 tokens each
            "code_blocks_high_cost": 30,     # Code blocks are token-heavy
        }

        # Mistral special tokens
        special_tokens = [
            "<s>",           # Start of sequence
            "</s>",          # End of sequence
            "<|im_start|>",  # Instruction start (ChatML)
            "<|im_end|>",    # Instruction end (ChatML)
            "[INST]",        # Instruction (Mistral format)
            "[/INST]",       # End instruction
        ]

        # Subword tokenization examples
        subword_examples = [
            {
                "word": "transaction",
                "likely_tokens": ["trans", "action"],
                "token_count": 2,
                "alternative": "payment",
                "alternative_tokens": 1
            },
            {
                "word": "fraudulent",
                "likely_tokens": ["fraud", "ulent"],
                "token_count": 2,
                "alternative": "fraud",
                "alternative_tokens": 1
            },
            {
                "word": "unauthorized",
                "likely_tokens": ["un", "author", "ized"],
                "token_count": 3,
                "alternative": "invalid",
                "alternative_tokens": 1
            },
            {
                "word": "suspicious",
                "likely_tokens": ["susp", "icious"],
                "token_count": 2,
                "alternative": "suspect",
                "alternative_tokens": 1
            },
        ]

        # Efficiency tips
        efficiency_tips = [
            "Use shorter synonyms: 'fraud' instead of 'fraudulent transaction'",
            "Avoid repetition: Don't repeat instructions or context",
            "Structure prompts clearly: Use newlines, not verbose transitions",
            "Prefer active voice: 'Analyze' not 'Conduct an analysis of'",
            "Remove filler words: 'very', 'really', 'actually' add no value",
            "Use abbreviations where clear: 'TX' for transaction in context",
            "Batch similar requests: One prompt for multiple items",
            "Use system messages: Put rules in system, not repeated in prompts",
            "Template reuse: Cache common prompt structures",
            "Avoid code blocks unless necessary: Plain text is more efficient",
        ]

        return TokenizerBehavior(
            tokenizer_name="Mistral-7B",
            average_tokens_per_word=0.75,
            common_patterns=common_patterns,
            special_tokens=special_tokens,
            subword_examples=subword_examples,
            efficiency_tips=efficiency_tips
        )

    # ========== Prompt Comparison ==========

    def compare_prompts(self, prompts: List[Dict[str, str]]) -> PromptComparison:
        """
        Compare multiple prompt variants for efficiency.

        Args:
            prompts: List of {name: str, text: str} dictionaries

        Returns:
            PromptComparison with best variant
        """
        variants = []

        for prompt in prompts:
            name = prompt.get("name", "Unnamed")
            text = prompt.get("text", "")

            analysis = self.analyze_tokens(text)

            variants.append({
                "name": name,
                "text": text,
                "token_count": analysis.token_count,
                "efficiency_score": analysis.efficiency_score,
                "issues_count": len(analysis.issues),
                "recommendations_count": len(analysis.recommendations)
            })

        # Find best variant (lowest token count with high efficiency)
        best_index = 0
        best_score = float('inf')

        for i, variant in enumerate(variants):
            # Score combines token count and efficiency
            # Lower is better
            score = variant["token_count"] * (2 - variant["efficiency_score"])
            if score < best_score:
                best_score = score
                best_index = i

        best_variant = variants[best_index]
        worst_variant = max(variants, key=lambda v: v["token_count"])
        token_savings = worst_variant["token_count"] - best_variant["token_count"]

        return PromptComparison(
            variants=variants,
            best_variant_index=best_index,
            best_variant_name=best_variant["name"],
            token_savings=token_savings
        )

    # ========== Special Token Handling ==========

    def validate_special_tokens(self, text: str) -> Dict[str, Any]:
        """
        Validate special token usage in prompt.

        Checks for:
        - Proper pairing of instruction markers
        - Valid special token syntax
        - Potential issues with special characters
        """
        issues = []
        warnings = []

        # Check for ChatML format
        im_start_count = text.count("<|im_start|>")
        im_end_count = text.count("<|im_end|>")

        if im_start_count != im_end_count:
            issues.append(f"Unbalanced ChatML tags: {im_start_count} starts vs {im_end_count} ends")

        # Check for Mistral instruction format
        inst_start_count = text.count("[INST]")
        inst_end_count = text.count("[/INST]")

        if inst_start_count != inst_end_count:
            issues.append(f"Unbalanced [INST] tags: {inst_start_count} starts vs {inst_end_count} ends")

        # Check for common mistakes
        if "<|im_start|>" in text and "[INST]" in text:
            warnings.append("Mixing ChatML and Mistral formats - choose one")

        # Check for unsupported special tokens
        unsupported = re.findall(r'<\|[^|]+\|>', text)
        known_tokens = ["<|im_start|>", "<|im_end|>"]
        unknown = [t for t in unsupported if t not in known_tokens]

        if unknown:
            warnings.append(f"Unknown special tokens: {', '.join(unknown)}")

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "chatml_format": im_start_count > 0,
            "mistral_format": inst_start_count > 0,
            "special_token_count": im_start_count + im_end_count + inst_start_count + inst_end_count
        }

    # ========== Multi-lingual Support ==========

    def analyze_multilingual(self, text: str, language: str = "en") -> Dict[str, Any]:
        """
        Analyze tokenization for non-English text.

        Note: Mistral tokenizer is optimized for English.
        Non-English text typically uses more tokens per word.
        """
        token_count = self.estimate_tokens(text)
        word_count = len(text.split())

        # Language-specific token multipliers
        multipliers = {
            "en": 1.0,   # English baseline
            "es": 1.2,   # Spanish
            "fr": 1.2,   # French
            "de": 1.3,   # German
            "zh": 2.0,   # Chinese (character-based)
            "ja": 2.0,   # Japanese
            "ar": 1.5,   # Arabic
            "ru": 1.4,   # Russian
        }

        multiplier = multipliers.get(language, 1.5)
        adjusted_tokens = int(token_count * multiplier)

        return {
            "language": language,
            "token_count_estimate": adjusted_tokens,
            "tokens_per_word": round(adjusted_tokens / word_count, 2) if word_count > 0 else 0,
            "efficiency_vs_english": f"{int((multiplier - 1) * 100)}% more tokens",
            "recommendation": "Use English prompts when possible for token efficiency" if language != "en" else "Optimal language for tokenization"
        }


# Global instance
tokenization_service = TokenizationService()
