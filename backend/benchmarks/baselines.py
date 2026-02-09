"""
Baseline Evaluators for Benchmarking.

Implements three baseline types for comparison:
1. ML Baselines: XGBoost, LightGBM, RandomForest
2. Rule-Based Baseline: Hand-crafted heuristics
3. Single-Agent Baseline: Simple LLM-based detection

Used to prove multi-agent superiority in thesis research.
"""

import json
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Import ML service
try:
    from app.services.ml_model_service import ml_service
    ML_AVAILABLE = True
except ImportError:
    logger.warning("ML model service not available")
    ML_AVAILABLE = False


@dataclass
class PredictionResult:
    """Result of a single prediction."""
    prediction: str  # "fraud" or "legitimate"
    confidence: float
    latency_ms: float
    metadata: Dict[str, Any] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "prediction": self.prediction,
            "confidence": self.confidence,
            "latency_ms": self.latency_ms,
            "metadata": self.metadata or {},
            "error": self.error
        }


class BaselineEvaluator(ABC):
    """Abstract base class for baseline evaluators."""

    def __init__(self, name: str, config: Dict = None):
        """
        Initialize baseline evaluator.

        Args:
            name: Baseline name
            config: Configuration dict
        """
        self.name = name
        self.config = config or {}
        self.setup_complete = False

    @abstractmethod
    def setup(self) -> bool:
        """
        Setup/load baseline model.

        Returns:
            bool: True if successful
        """
        pass

    @abstractmethod
    def predict(self, transaction: Dict) -> PredictionResult:
        """
        Make prediction for a transaction.

        Args:
            transaction: Transaction dict with features

        Returns:
            PredictionResult
        """
        pass

    def predict_batch(self, transactions: List[Dict]) -> List[PredictionResult]:
        """
        Make predictions for multiple transactions.

        Args:
            transactions: List of transaction dicts

        Returns:
            List of PredictionResults
        """
        results = []
        for transaction in transactions:
            result = self.predict(transaction)
            results.append(result)
        return results

    def get_info(self) -> Dict:
        """Get baseline information."""
        return {
            "name": self.name,
            "type": self.__class__.__name__,
            "config": self.config,
            "setup_complete": self.setup_complete
        }


class MLBaseline(BaselineEvaluator):
    """
    ML Model Baseline.

    Uses pre-trained classical ML models (XGBoost, LightGBM, RandomForest).
    These are fast, deterministic, and don't require LLMs.
    """

    def __init__(self, name: str, model_name: str, config: Dict = None):
        """
        Initialize ML baseline.

        Args:
            name: Baseline name (e.g., "xgboost_baseline")
            model_name: Model to use ("xgboost", "lightgbm", "random_forest")
            config: Configuration dict
        """
        super().__init__(name, config)
        self.model_name = model_name
        self.version = config.get("version", "v1") if config else "v1"

    def setup(self) -> bool:
        """Load ML model from disk."""
        if not ML_AVAILABLE:
            logger.error("ML service not available")
            return False

        try:
            # Load model using ML service
            success = ml_service.load_model(self.model_name, version=self.version)

            if success:
                logger.info(f"Loaded ML model: {self.model_name}")
                self.setup_complete = True
                return True
            else:
                logger.error(f"Failed to load model: {self.model_name}")
                return False

        except Exception as e:
            logger.exception(f"Error loading ML model {self.model_name}: {e}")
            return False

    def predict(self, transaction: Dict) -> PredictionResult:
        """Make prediction using ML model."""
        if not self.setup_complete:
            return PredictionResult(
                prediction="legitimate",
                confidence=0.0,
                latency_ms=0.0,
                error="Model not loaded"
            )

        try:
            start_time = time.time()

            # Use ML service for prediction
            result = ml_service.predict(transaction, model_name=self.model_name)

            latency_ms = (time.time() - start_time) * 1000

            # Convert to standard format
            prediction = "fraud" if result["is_fraud"] else "legitimate"
            confidence = result["confidence"]

            return PredictionResult(
                prediction=prediction,
                confidence=confidence,
                latency_ms=latency_ms,
                metadata={
                    "fraud_probability": result["fraud_probability"],
                    "risk_level": result["risk_level"],
                    "model": self.model_name
                }
            )

        except Exception as e:
            logger.exception(f"ML prediction error: {e}")
            return PredictionResult(
                prediction="legitimate",
                confidence=0.0,
                latency_ms=0.0,
                error=str(e)
            )

    def predict_batch(self, transactions: List[Dict]) -> List[PredictionResult]:
        """Optimized batch prediction for ML models."""
        if not self.setup_complete:
            return [
                PredictionResult(
                    prediction="legitimate",
                    confidence=0.0,
                    latency_ms=0.0,
                    error="Model not loaded"
                )
                for _ in transactions
            ]

        try:
            start_time = time.time()

            # Use ML service batch prediction
            results = ml_service.predict_batch(transactions, model_name=self.model_name)

            total_latency_ms = (time.time() - start_time) * 1000
            avg_latency_ms = total_latency_ms / len(transactions)

            # Convert to PredictionResults
            prediction_results = []
            for result in results:
                prediction = "fraud" if result["is_fraud"] else "legitimate"
                prediction_results.append(
                    PredictionResult(
                        prediction=prediction,
                        confidence=result["confidence"],
                        latency_ms=avg_latency_ms,
                        metadata={
                            "fraud_probability": result["fraud_probability"],
                            "risk_level": result["risk_level"],
                            "model": self.model_name
                        }
                    )
                )

            return prediction_results

        except Exception as e:
            logger.exception(f"Batch prediction error: {e}")
            return [
                PredictionResult(
                    prediction="legitimate",
                    confidence=0.0,
                    latency_ms=0.0,
                    error=str(e)
                )
                for _ in transactions
            ]


class RuleBasedBaseline(BaselineEvaluator):
    """
    Rule-Based Heuristic Baseline.

    Uses hand-crafted rules for fraud detection.
    Fastest approach, no ML or LLM required.
    """

    def __init__(self, name: str, rules: List[Dict], config: Dict = None):
        """
        Initialize rule-based baseline.

        Args:
            name: Baseline name
            rules: List of rule dicts with condition, prediction, confidence
            config: Configuration dict
        """
        super().__init__(name, config)
        self.rules = rules

    def setup(self) -> bool:
        """Validate rules."""
        try:
            if not self.rules:
                logger.error("No rules provided")
                return False

            # Validate each rule has required fields
            for i, rule in enumerate(self.rules):
                if "condition" not in rule:
                    logger.error(f"Rule {i} missing 'condition'")
                    return False
                if "prediction" not in rule:
                    logger.error(f"Rule {i} missing 'prediction'")
                    return False
                if "confidence" not in rule:
                    logger.error(f"Rule {i} missing 'confidence'")
                    return False

            logger.info(f"Loaded {len(self.rules)} rules")
            self.setup_complete = True
            return True

        except Exception as e:
            logger.exception(f"Error validating rules: {e}")
            return False

    def _evaluate_condition(self, condition: str, transaction: Dict) -> bool:
        """
        Safely evaluate a rule condition.

        Args:
            condition: Python expression as string
            transaction: Transaction data

        Returns:
            bool: True if condition matches
        """
        try:
            # Extract transaction fields
            tx_type = transaction.get("type", "")
            amount = float(transaction.get("amount", 0))
            oldbalanceOrg = float(transaction.get("oldbalanceOrg", 0))
            newbalanceOrig = float(transaction.get("newbalanceOrig", 0))
            oldbalanceDest = float(transaction.get("oldbalanceDest", 0))
            newbalanceDest = float(transaction.get("newbalanceDest", 0))

            # Create safe evaluation context
            context = {
                "type": tx_type,
                "amount": amount,
                "oldbalanceOrg": oldbalanceOrg,
                "newbalanceOrig": newbalanceOrig,
                "oldbalanceDest": oldbalanceDest,
                "newbalanceDest": newbalanceDest,
                "abs": abs,
                "True": True,
                "False": False
            }

            # Safely evaluate
            result = eval(condition, {"__builtins__": {}}, context)
            return bool(result)

        except Exception as e:
            logger.warning(f"Error evaluating condition '{condition}': {e}")
            return False

    def predict(self, transaction: Dict) -> PredictionResult:
        """Make prediction using rules."""
        if not self.setup_complete:
            return PredictionResult(
                prediction="legitimate",
                confidence=0.0,
                latency_ms=0.0,
                error="Rules not loaded"
            )

        try:
            start_time = time.time()

            # Check each rule in order
            matched_rule = None
            for rule in self.rules:
                if self._evaluate_condition(rule["condition"], transaction):
                    matched_rule = rule
                    break

            latency_ms = (time.time() - start_time) * 1000

            if matched_rule:
                return PredictionResult(
                    prediction=matched_rule["prediction"],
                    confidence=matched_rule["confidence"],
                    latency_ms=latency_ms,
                    metadata={
                        "rule": matched_rule["condition"],
                        "rule_based": True
                    }
                )
            else:
                # No rule matched, default to legitimate
                return PredictionResult(
                    prediction="legitimate",
                    confidence=0.5,
                    latency_ms=latency_ms,
                    metadata={"rule_based": True, "rule": "default"}
                )

        except Exception as e:
            logger.exception(f"Rule-based prediction error: {e}")
            return PredictionResult(
                prediction="legitimate",
                confidence=0.0,
                latency_ms=0.0,
                error=str(e)
            )


class SingleAgentBaseline(BaselineEvaluator):
    """
    Single-Agent LLM Baseline.

    Uses a single LLM agent for fraud detection.
    Slower than ML/rules, but provides reasoning.
    """

    def __init__(self, name: str, model: str = "llama2:7b", config: Dict = None):
        """
        Initialize single-agent baseline.

        Args:
            name: Baseline name
            model: LLM model name
            config: Configuration dict
        """
        super().__init__(name, config)
        self.model = model
        self.temperature = config.get("temperature", 0.1) if config else 0.1
        self.max_tokens = config.get("max_tokens", 500) if config else 500
        self.ollama_available = False

    def setup(self) -> bool:
        """Check if Ollama is available."""
        try:
            import httpx

            # Check Ollama health
            response = httpx.get("http://localhost:11434/api/tags", timeout=5.0)
            if response.status_code == 200:
                models = response.json().get("models", [])
                model_names = [m.get("name", "") for m in models]

                # Check if our model is available
                if any(self.model in name for name in model_names):
                    logger.info(f"Ollama available with model {self.model}")
                    self.ollama_available = True
                    self.setup_complete = True
                    return True
                else:
                    logger.warning(f"Ollama available but model {self.model} not found")
                    logger.info(f"Available models: {model_names}")
                    return False
            else:
                logger.warning("Ollama not responding")
                return False

        except Exception as e:
            logger.warning(f"Ollama not available: {e}")
            return False

    def _create_prompt(self, transaction: Dict) -> str:
        """Create fraud detection prompt."""
        return f"""You are a fraud detection expert. Analyze this transaction and determine if it's fraudulent.

Transaction Details:
- Type: {transaction.get('type', 'N/A')}
- Amount: ${transaction.get('amount', 0):,.2f}
- Old Balance (Origin): ${transaction.get('oldbalanceOrg', 0):,.2f}
- New Balance (Origin): ${transaction.get('newbalanceOrig', 0):,.2f}
- Old Balance (Destination): ${transaction.get('oldbalanceDest', 0):,.2f}
- New Balance (Destination): ${transaction.get('newbalanceDest', 0):,.2f}

Analyze for:
1. Balance consistency (did money move correctly?)
2. Suspicious patterns (disappeared money, account drained, etc.)
3. Amount reasonableness
4. Transaction type appropriateness

Respond with ONLY:
- "FRAUD" or "LEGITIMATE"
- Confidence (0.0 to 1.0)
- Brief reason (one sentence)

Format: PREDICTION|CONFIDENCE|REASON

Example: FRAUD|0.85|Money disappeared with no destination balance increase"""

    def predict(self, transaction: Dict) -> PredictionResult:
        """Make prediction using single LLM agent."""
        if not self.setup_complete or not self.ollama_available:
            return PredictionResult(
                prediction="legitimate",
                confidence=0.0,
                latency_ms=0.0,
                error="Ollama not available"
            )

        try:
            import httpx

            start_time = time.time()

            # Create prompt
            prompt = self._create_prompt(transaction)

            # Call Ollama
            response = httpx.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": self.temperature,
                        "num_predict": self.max_tokens
                    }
                },
                timeout=30.0
            )

            latency_ms = (time.time() - start_time) * 1000

            if response.status_code == 200:
                result = response.json()
                response_text = result.get("response", "").strip()

                # Parse response (format: PREDICTION|CONFIDENCE|REASON)
                parts = response_text.split("|")
                if len(parts) >= 2:
                    prediction_raw = parts[0].strip().upper()
                    confidence_raw = parts[1].strip()
                    reason = parts[2].strip() if len(parts) > 2 else "No reason provided"

                    # Normalize prediction
                    if "FRAUD" in prediction_raw:
                        prediction = "fraud"
                    else:
                        prediction = "legitimate"

                    # Parse confidence
                    try:
                        confidence = float(confidence_raw)
                        confidence = max(0.0, min(1.0, confidence))
                    except:
                        confidence = 0.6

                    return PredictionResult(
                        prediction=prediction,
                        confidence=confidence,
                        latency_ms=latency_ms,
                        metadata={
                            "model": self.model,
                            "reason": reason,
                            "raw_response": response_text,
                            "llm_based": True
                        }
                    )
                else:
                    # Fallback parsing
                    if "FRAUD" in response_text.upper():
                        prediction = "fraud"
                        confidence = 0.7
                    else:
                        prediction = "legitimate"
                        confidence = 0.6

                    return PredictionResult(
                        prediction=prediction,
                        confidence=confidence,
                        latency_ms=latency_ms,
                        metadata={
                            "model": self.model,
                            "raw_response": response_text,
                            "llm_based": True,
                            "parsing_fallback": True
                        }
                    )
            else:
                return PredictionResult(
                    prediction="legitimate",
                    confidence=0.0,
                    latency_ms=latency_ms,
                    error=f"Ollama error: {response.status_code}"
                )

        except Exception as e:
            logger.exception(f"Single-agent prediction error: {e}")
            return PredictionResult(
                prediction="legitimate",
                confidence=0.0,
                latency_ms=0.0,
                error=str(e)
            )


def create_baseline(baseline_config: Dict) -> Optional[BaselineEvaluator]:
    """
    Factory function to create baseline evaluator from config.

    Args:
        baseline_config: Config dict from config.yaml

    Returns:
        BaselineEvaluator instance or None
    """
    try:
        baseline_type = baseline_config.get("type")
        name = baseline_config.get("name")

        if not baseline_config.get("enabled", True):
            logger.info(f"Baseline {name} is disabled")
            return None

        if baseline_type == "ml":
            # ML baseline
            baseline = MLBaseline(
                name=name,
                model_name=name,  # Use name as model name
                config=baseline_config
            )
        elif baseline_type == "heuristic":
            # Rule-based baseline
            rules = baseline_config.get("rules", [])
            baseline = RuleBasedBaseline(
                name=name,
                rules=rules,
                config=baseline_config
            )
        elif baseline_type == "agentic":
            # Single-agent baseline
            model = baseline_config.get("model", "llama2:7b")
            baseline = SingleAgentBaseline(
                name=name,
                model=model,
                config=baseline_config
            )
        else:
            logger.error(f"Unknown baseline type: {baseline_type}")
            return None

        # Setup baseline
        success = baseline.setup()
        if not success:
            logger.warning(f"Failed to setup baseline: {name}")
            return None

        return baseline

    except Exception as e:
        logger.exception(f"Error creating baseline: {e}")
        return None
