"""
Model routing and latency optimization service.

Implements intelligent model routing, prompt compression,
caching, and batch optimization for quality vs latency tradeoffs.
"""

import asyncio
import hashlib
import logging
from typing import Any, Dict, List, Optional

from cachetools import TTLCache

from app.core.config import get_settings
from app.models.fraud import Transaction

logger = logging.getLogger(__name__)
settings = get_settings()


class ModelRouter:
    """
    Intelligent model routing for latency-quality tradeoffs.

    Features:
    - Route simple transactions to fast quantized model
    - Route complex transactions to full precision model
    - Prompt compression for faster inference
    - Early stopping based on confidence
    - Caching for frequent patterns
    - Batch optimization
    """

    def __init__(self):
        """Initialize model router with caching."""
        # TTL cache for transaction patterns (1 hour TTL)
        self.pattern_cache = TTLCache(maxsize=1000, ttl=3600)

        # Policy cache (longer TTL since policies don't change often)
        self.policy_cache = TTLCache(maxsize=100, ttl=7200)

        logger.info("Initialized model router with caching")

    def route_to_model(self, transaction: Transaction) -> Dict[str, Any]:
        """
        Select optimal model based on transaction complexity.

        Routing logic:
        - Simple, low-amount transactions → fast model
        - High-amount or unusual patterns → full model
        - Known patterns → potentially skip LLM entirely

        Args:
            transaction: Transaction to analyze

        Returns:
            Dictionary with model selection and reasoning
        """
        # Complexity indicators
        is_high_amount = transaction.amount > 50000
        is_transfer = transaction.type in ["TRANSFER", "CASH_OUT"]
        is_unusual_balance = (
            hasattr(transaction, "oldbalanceOrg")
            and hasattr(transaction, "newbalanceOrig")
            and abs(transaction.oldbalanceOrg - transaction.newbalanceOrig - transaction.amount)
            > 1000
        )

        complexity_score = 0
        reasoning = []

        if is_high_amount:
            complexity_score += 2
            reasoning.append(f"High transaction amount (${transaction.amount:,.2f})")

        if is_transfer:
            complexity_score += 1
            reasoning.append(f"Transfer type: {transaction.type}")

        if is_unusual_balance:
            complexity_score += 2
            reasoning.append("Unusual balance change detected")

        # Route based on complexity
        if complexity_score <= 1:
            selected_model = settings.llm_fast_model
            estimated_latency_ms = 500
            recommendation = "fast"
        else:
            selected_model = settings.llm_model_name
            estimated_latency_ms = 2000
            recommendation = "full"

        return {
            "selected_model": selected_model,
            "recommendation": recommendation,
            "complexity_score": complexity_score,
            "estimated_latency_ms": estimated_latency_ms,
            "reasoning": reasoning,
            "use_streaming": complexity_score > 2,  # Stream for complex cases
        }

    def should_use_llm(self, transaction: Transaction, rule_confidence: float) -> Dict[str, Any]:
        """
        Determine if LLM is needed or if rule-based system is sufficient.

        Args:
            transaction: Transaction to analyze
            rule_confidence: Confidence from rule-based system (0-1)

        Returns:
            Dictionary with decision and reasoning
        """
        # Check cache first
        cache_key = self._get_transaction_cache_key(transaction)
        if cache_key in self.pattern_cache:
            cached = self.pattern_cache[cache_key]
            logger.info("Cache hit for transaction pattern: %s...", cache_key[:8])
            return {
                "use_llm": False,
                "reason": "cached_pattern",
                "cached_result": cached,
                "latency_saved_ms": 2000,  # Estimate
            }

        # Early stopping if rule-based system is very confident
        if rule_confidence >= 0.95:
            return {
                "use_llm": False,
                "reason": "high_rule_confidence",
                "rule_confidence": rule_confidence,
                "latency_saved_ms": 2000,
            }

        # Use LLM if confidence is moderate or low
        if rule_confidence < 0.7:
            return {
                "use_llm": True,
                "reason": "low_rule_confidence",
                "rule_confidence": rule_confidence,
            }

        # For borderline cases, use fast model
        return {
            "use_llm": True,
            "reason": "moderate_confidence_verification",
            "rule_confidence": rule_confidence,
            "prefer_fast_model": True,
        }

    def compress_prompt(self, prompt: str) -> Dict[str, Any]:
        """
        Compress prompt to reduce token count and latency.

        Techniques:
        - Remove redundant context
        - Abbreviate field names
        - Extract only key features
        - Remove formatting

        Args:
            prompt: Original prompt

        Returns:
            Dictionary with compressed prompt and metrics
        """
        original_length = len(prompt)

        # Compression strategy
        compressed = prompt

        # Remove extra whitespace
        compressed = " ".join(compressed.split())

        # Replace verbose field names
        replacements = {
            "transaction_id": "txn_id",
            "transaction": "txn",
            "amount": "amt",
            "oldbalanceOrg": "old_bal",
            "newbalanceOrig": "new_bal",
            "oldbalanceDest": "old_bal_dst",
            "newbalanceDest": "new_bal_dst",
            "is_fraud": "fraud",
        }

        for old, new in replacements.items():
            compressed = compressed.replace(old, new)

        # Remove common phrases
        verbose_phrases = [
            "Please analyze the following ",
            "Based on the information provided, ",
            "Take into consideration that ",
        ]
        for phrase in verbose_phrases:
            compressed = compressed.replace(phrase, "")

        compressed_length = len(compressed)
        reduction_percent = ((original_length - compressed_length) / original_length) * 100

        logger.debug(
            "Prompt compressed: %d → %d chars (%.1f%% reduction)",
            original_length,
            compressed_length,
            reduction_percent,
        )

        return {
            "compressed_prompt": compressed,
            "original_length": original_length,
            "compressed_length": compressed_length,
            "reduction_percent": round(reduction_percent, 2),
            "estimated_latency_reduction_ms": int(reduction_percent * 10),  # Rough estimate
        }

    def cache_result(self, transaction: Transaction, result: Dict) -> None:
        """
        Cache result for similar future transactions.

        Args:
            transaction: Transaction analyzed
            result: Analysis result
        """
        cache_key = self._get_transaction_cache_key(transaction)
        self.pattern_cache[cache_key] = result
        logger.debug("Cached result for pattern: %s...", cache_key[:8])

    def get_cached_result(self, transaction: Transaction) -> Optional[Dict]:
        """
        Get cached result for transaction pattern.

        Args:
            transaction: Transaction to check

        Returns:
            Cached result if found, None otherwise
        """
        cache_key = self._get_transaction_cache_key(transaction)
        return self.pattern_cache.get(cache_key)

    def _get_transaction_cache_key(self, transaction: Transaction) -> str:
        """
        Generate cache key for transaction pattern.

        Uses transaction type, amount bucket, and balance change pattern.

        Args:
            transaction: Transaction

        Returns:
            Cache key string
        """
        # Bucket amount (to group similar amounts)
        amount_bucket = int(transaction.amount / 1000) * 1000

        # Calculate balance change if available
        balance_change = 0
        if hasattr(transaction, "oldbalanceOrg") and hasattr(transaction, "newbalanceOrig"):
            balance_change = transaction.oldbalanceOrg - transaction.newbalanceOrig

        # Create pattern string
        pattern = f"{transaction.type}:{amount_bucket}:{int(balance_change / 1000) * 1000}"

        # Hash for consistent key
        return hashlib.md5(pattern.encode()).hexdigest()

    async def batch_optimize(self, transactions: List[Transaction], llm_client) -> List[Dict]:
        """
        Optimize batch inference with grouping and parallel processing.

        Strategy:
        - Group similar transactions
        - Process groups in parallel
        - Share context where possible

        Args:
            transactions: List of transactions
            llm_client: LLM client instance

        Returns:
            List of results
        """
        # Group by type for potential batching
        by_type = {}
        for txn in transactions:
            txn_type = txn.type
            if txn_type not in by_type:
                by_type[txn_type] = []
            by_type[txn_type].append(txn)

        logger.info(
            "Batch optimization: %d transactions grouped into %d types",
            len(transactions),
            len(by_type),
        )

        # Process each group (this is simplified - in production,
        # you'd batch the actual LLM calls more intelligently)
        all_results = []
        for txn_type, txn_group in by_type.items():
            # Process group in parallel
            tasks = [self._analyze_single(txn, llm_client) for txn in txn_group]
            group_results = await asyncio.gather(*tasks, return_exceptions=True)
            all_results.extend(group_results)

        return all_results

    async def _analyze_single(self, transaction: Transaction, llm_client) -> Dict:
        """
        Analyze single transaction (placeholder for actual analysis).

        Args:
            transaction: Transaction to analyze
            llm_client: LLM client

        Returns:
            Analysis result
        """
        # This is a placeholder - actual implementation would call LLM
        # For now, just return routing decision
        routing = self.route_to_model(transaction)
        return {"transaction_id": transaction.transaction_id, "routing": routing}

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache metrics
        """
        return {
            "pattern_cache_size": len(self.pattern_cache),
            "pattern_cache_maxsize": self.pattern_cache.maxsize,
            "pattern_cache_ttl": self.pattern_cache.ttl,
            "policy_cache_size": len(self.policy_cache),
            "policy_cache_maxsize": self.policy_cache.maxsize,
            "policy_cache_ttl": self.policy_cache.ttl,
        }


# Global instance
_model_router: Optional[ModelRouter] = None


def get_model_router() -> ModelRouter:
    """
    Get global model router instance.

    Returns:
        ModelRouter instance
    """
    global _model_router
    if _model_router is None:
        _model_router = ModelRouter()
    return _model_router
