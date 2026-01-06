"""
Fraud detection service with async processing.

Implements fraud detection logic with proper concurrency controls,
deadlock prevention, and race condition handling.
"""

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime
from typing import List, Optional

from app.models.fraud import FraudAnalysisResponse, FraudPrediction, RiskLevel, Transaction

logger = logging.getLogger(__name__)


class FraudDetectionService:
    """
    Async fraud detection service.

    Features:
    - Async fraud detection with proper resource management
    - Concurrent batch processing with semaphore
    - Deadlock prevention using timeouts
    - Race condition handling with locks
    """

    def __init__(self, max_concurrent_requests: int = 10):
        """
        Initialize fraud detection service.

        Args:
            max_concurrent_requests: Maximum concurrent fraud checks
        """
        self.max_concurrent_requests = max_concurrent_requests
        self.semaphore = asyncio.Semaphore(max_concurrent_requests)
        self.lock = asyncio.Lock()

        # Statistics (protected by lock)
        self.stats = {
            "total_analyzed": 0,
            "fraud_detected": 0,
            "avg_processing_time_ms": 0.0,
        }

        logger.info(
            f"Initialized FraudDetectionService: " f"max_concurrent={max_concurrent_requests}"
        )

    @asynccontextmanager
    async def _acquire_semaphore_with_timeout(self, timeout: float = 30.0):
        """
        Acquire semaphore with timeout to prevent deadlock.

        Args:
            timeout: Timeout in seconds

        Raises:
            asyncio.TimeoutError: If acquisition times out
        """
        try:
            await asyncio.wait_for(self.semaphore.acquire(), timeout=timeout)
            try:
                yield
            finally:
                self.semaphore.release()
        except asyncio.TimeoutError:
            logger.error(f"Semaphore acquisition timeout after {timeout}s")
            raise

    async def _update_stats(self, is_fraud: bool, processing_time_ms: float) -> None:
        """
        Update service statistics (thread-safe).

        Args:
            is_fraud: Whether fraud was detected
            processing_time_ms: Processing time in milliseconds
        """
        async with self.lock:
            self.stats["total_analyzed"] += 1
            if is_fraud:
                self.stats["fraud_detected"] += 1

            # Update rolling average
            total = self.stats["total_analyzed"]
            current_avg = self.stats["avg_processing_time_ms"]
            self.stats["avg_processing_time_ms"] = (
                current_avg * (total - 1) + processing_time_ms
            ) / total

    async def get_stats(self) -> dict:
        """
        Get service statistics (thread-safe).

        Returns:
            Statistics dictionary
        """
        async with self.lock:
            return self.stats.copy()

    def _calculate_risk_features(self, transaction: Transaction) -> dict:
        """
        Calculate risk features from transaction.

        Args:
            transaction: Transaction to analyze

        Returns:
            Feature dictionary with importance scores
        """
        features = {}

        # Amount-based features
        if transaction.amount > 200000:
            features["high_amount"] = 0.4
        elif transaction.amount > 100000:
            features["medium_amount"] = 0.2

        # Balance inconsistency
        expected_balance = transaction.oldbalanceOrg - transaction.amount
        balance_diff = abs(transaction.newbalanceOrig - expected_balance)

        if balance_diff > 1.0:
            features["balance_inconsistency"] = min(0.5, balance_diff / transaction.amount)

        # Transaction type
        if transaction.type in ["TRANSFER", "CASH_OUT"]:
            features["risky_type"] = 0.3

        # Zero balances (suspicious for fraud)
        if transaction.newbalanceOrig == 0 and transaction.amount > 0:
            features["zero_balance_orig"] = 0.25

        if transaction.oldbalanceDest == 0 and transaction.newbalanceDest > 0:
            features["new_account_dest"] = 0.15

        return features

    def _make_prediction(self, transaction: Transaction, features: dict) -> FraudPrediction:
        """
        Make fraud prediction based on features.

        This is a rule-based approach. In production, replace with ML model.

        Args:
            transaction: Transaction to analyze
            features: Extracted features

        Returns:
            FraudPrediction
        """
        # Calculate risk score from features
        risk_score = sum(features.values()) * 100
        risk_score = min(100, risk_score)

        # Determine risk level from risk score
        if risk_score >= 80:
            risk_level = RiskLevel.CRITICAL
        elif risk_score >= 60:
            risk_level = RiskLevel.HIGH
        elif risk_score >= 40:
            risk_level = RiskLevel.MEDIUM
        else:
            risk_level = RiskLevel.LOW

        # Determine fraud based on threshold
        is_fraud = risk_score > 50
        confidence = risk_score / 100 if is_fraud else (100 - risk_score) / 100

        # Generate explanation
        if is_fraud:
            top_features = sorted(features.items(), key=lambda x: x[1], reverse=True)[:3]

            explanations = {
                "high_amount": "High transaction amount",
                "medium_amount": "Medium-high transaction amount",
                "balance_inconsistency": "Inconsistent balance changes",
                "risky_type": f"High-risk transaction type ({transaction.type})",
                "zero_balance_orig": "Account emptied (zero balance)",
                "new_account_dest": "New destination account",
            }

            explanation_parts = [explanations.get(feat, feat) for feat, _ in top_features]
            explanation = "Fraud detected: " + ", ".join(explanation_parts)
        else:
            explanation = "No fraud indicators detected"

        return FraudPrediction(
            is_fraud=is_fraud,
            confidence=confidence,
            risk_score=risk_score,
            risk_level=risk_level,
            explanation=explanation,
            features=features,
        )

    async def analyze_transaction(self, transaction: Transaction) -> FraudAnalysisResponse:
        """
        Analyze a single transaction for fraud (async).

        Uses semaphore to limit concurrency and prevent resource exhaustion.

        Args:
            transaction: Transaction to analyze

        Returns:
            FraudAnalysisResponse

        Raises:
            asyncio.TimeoutError: If semaphore acquisition times out
        """
        start_time = time.time()

        # Acquire semaphore with timeout (deadlock prevention)
        async with self._acquire_semaphore_with_timeout(timeout=30.0):
            # Simulate async I/O (e.g., database lookup, ML model inference)
            # In production, replace with actual async operations
            await asyncio.sleep(0.1)  # Simulate processing

            # Extract features
            features = self._calculate_risk_features(transaction)

            # Make prediction
            prediction = self._make_prediction(transaction, features)

            # Calculate processing time
            processing_time_ms = (time.time() - start_time) * 1000

            # Update statistics (thread-safe)
            await self._update_stats(prediction.is_fraud, processing_time_ms)

            return FraudAnalysisResponse(
                transaction_id=transaction.transaction_id,
                prediction=prediction,
                processing_time_ms=processing_time_ms,
                timestamp=datetime.utcnow().isoformat(),
            )

    async def analyze_batch(self, transactions: List[Transaction]) -> List[FraudAnalysisResponse]:
        """
        Analyze a batch of transactions concurrently.

        Uses asyncio.gather with return_exceptions to handle partial failures.

        Args:
            transactions: List of transactions to analyze

        Returns:
            List of FraudAnalysisResponse
        """
        logger.info(f"Analyzing batch of {len(transactions)} transactions")

        # Create tasks for concurrent execution
        tasks = [self.analyze_transaction(transaction) for transaction in transactions]

        # Execute concurrently with exception handling
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out exceptions and log errors
        valid_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(
                    f"Failed to analyze transaction " f"{transactions[i].transaction_id}: {result}"
                )
            else:
                valid_results.append(result)

        logger.info(
            f"✓ Batch analysis complete: " f"{len(valid_results)}/{len(transactions)} successful"
        )

        return valid_results


# Global service instance
_fraud_service: Optional[FraudDetectionService] = None


def get_fraud_service() -> FraudDetectionService:
    """
    Get global fraud detection service instance.

    Returns:
        FraudDetectionService instance
    """
    global _fraud_service
    if _fraud_service is None:
        from app.core.config import get_settings

        settings = get_settings()

        _fraud_service = FraudDetectionService(max_concurrent_requests=settings.max_workers)

    return _fraud_service
