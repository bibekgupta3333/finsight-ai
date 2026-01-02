"""
LLM safety and failure mode detection service.

Implements hallucination detection, prompt injection prevention,
refusal handling, and confidence calibration.
"""

import logging
import re
from typing import Dict, List, Optional

from app.models.fraud import Transaction

logger = logging.getLogger(__name__)


class LLMSafety:
    """
    LLM safety and failure mode detection.

    AGI Interview Signal: "I built safety guardrails before production deployment"

    Features:
    - Hallucination detection (fact-checking against transaction data)
    - Prompt injection detection and prevention
    - Refusal behavior handling
    - Overconfidence calibration
    - Context confusion detection
    - Reasoning shortcut identification
    """

    def __init__(self):
        """Initialize safety checker."""
        # Track historical predictions for calibration
        self.prediction_history: List[Dict] = []
        logger.info("Initialized LLM safety checker")

    def detect_hallucination(
        self, llm_response: str, transaction: Transaction, strict: bool = True
    ) -> Dict[str, any]:
        """
        Detect if LLM hallucinated facts about the transaction.

        Checks:
        - Numeric claims match actual transaction data
        - Field references are valid
        - No invented features

        Args:
            llm_response: LLM generated text
            transaction: Actual transaction data
            strict: If True, flag any discrepancy; if False, allow small rounding

        Returns:
            Dictionary with hallucination detection results
        """
        hallucinations = []
        warnings = []

        # Extract numbers from LLM response
        numbers_in_response = re.findall(r"\d+(?:,\d{3})*(?:\.\d+)?", llm_response)
        numbers_in_response = [float(n.replace(",", "")) for n in numbers_in_response]

        # Expected numbers from transaction
        expected_numbers = [transaction.amount]
        if hasattr(transaction, "oldbalanceOrg"):
            expected_numbers.append(transaction.oldbalanceOrg)
        if hasattr(transaction, "newbalanceOrig"):
            expected_numbers.append(transaction.newbalanceOrig)
        if hasattr(transaction, "oldbalanceDest"):
            expected_numbers.append(transaction.oldbalanceDest)
        if hasattr(transaction, "newbalanceDest"):
            expected_numbers.append(transaction.newbalanceDest)

        # Check for completely fabricated numbers
        tolerance = 0.01 if not strict else 0.0
        for num in numbers_in_response:
            # Check if this number is close to any expected number
            is_valid = any(
                abs(num - expected) / max(expected, 1) <= tolerance for expected in expected_numbers
            )
            if not is_valid and num > 1:  # Ignore small numbers (might be scores)
                hallucinations.append(
                    {
                        "type": "fabricated_number",
                        "value": num,
                        "message": f"LLM mentioned ${num:,.2f} which doesn't match transaction data",
                    }
                )

        # Check for invalid field references
        invalid_fields = [
            "credit_score",
            "merchant_id",
            "ip_address",
            "device_id",
            "customer_name",
            "account_age",
            "transaction_history",
        ]
        for field in invalid_fields:
            if field in llm_response.lower():
                hallucinations.append(
                    {
                        "type": "invalid_field",
                        "value": field,
                        "message": f"LLM referenced '{field}' which doesn't exist in data",
                    }
                )

        # Check transaction type confusion
        if hasattr(transaction, "type"):
            mentioned_types = ["PAYMENT", "TRANSFER", "CASH_OUT", "DEBIT", "CASH_IN"]
            for mentioned_type in mentioned_types:
                if mentioned_type in llm_response and mentioned_type != transaction.type:
                    hallucinations.append(
                        {
                            "type": "wrong_transaction_type",
                            "value": mentioned_type,
                            "message": f"LLM mentioned '{mentioned_type}' but actual type is '{transaction.type}'",
                        }
                    )

        # Severity assessment
        has_critical = any(
            h["type"] in ["fabricated_number", "wrong_transaction_type"] for h in hallucinations
        )

        result = {
            "hallucination_detected": len(hallucinations) > 0,
            "severity": "critical" if has_critical else "warning" if len(warnings) > 0 else "none",
            "hallucinations": hallucinations,
            "warnings": warnings,
            "recommendation": (
                "reject" if has_critical else "review" if len(hallucinations) > 0 else "accept"
            ),
        }

        if hallucinations:
            logger.warning(f"Detected {len(hallucinations)} hallucinations in LLM response")

        return result

    def check_prompt_injection(self, text: str) -> Dict[str, any]:
        """
        Detect potential prompt injection attempts.

        Checks for:
        - Instruction override attempts
        - System prompt leakage attempts
        - Role confusion attempts

        Args:
            text: User-provided text (e.g., transaction description)

        Returns:
            Dictionary with injection detection results
        """
        injections = []

        # Patterns that indicate injection attempts
        injection_patterns = [
            (
                r"ignore (previous|all|the|above) (instructions?|prompts?|rules?)",
                "instruction_override",
            ),
            (r"(you are|act as|pretend to be|you're now)", "role_manipulation"),
            (r"(system|assistant|user):\s*\n", "role_confusion"),
            (r"reveal (your|the) (prompt|instructions?|system message)", "prompt_leakage"),
            (r"forget (everything|all|that)", "memory_wipe"),
            (r"new (task|instruction|rule):", "task_injection"),
            (r"\[SYSTEM\]|\[INST\]|\<\|system\|\>", "special_tokens"),
        ]

        for pattern, injection_type in injection_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                injections.append(
                    {
                        "type": injection_type,
                        "pattern": pattern,
                        "matches": matches,
                        "severity": "high",
                    }
                )

        result = {
            "injection_detected": len(injections) > 0,
            "injections": injections,
            "recommendation": "sanitize" if len(injections) > 0 else "safe",
            "sanitized_text": self._sanitize_text(text) if len(injections) > 0 else text,
        }

        if injections:
            logger.warning(f"Detected {len(injections)} potential prompt injection attempts")

        return result

    def _sanitize_text(self, text: str) -> str:
        """
        Sanitize text by removing potential injection patterns.

        Args:
            text: Original text

        Returns:
            Sanitized text
        """
        # Remove special tokens
        sanitized = re.sub(
            r"\[SYSTEM\]|\[INST\]|\<\|system\|\>|\<\|user\|\>", "", text, flags=re.IGNORECASE
        )

        # Remove instruction override attempts
        sanitized = re.sub(
            r"ignore (previous|all|the|above) (instructions?|prompts?)",
            "",
            sanitized,
            flags=re.IGNORECASE,
        )

        # Limit length to prevent overflow attacks
        if len(sanitized) > 500:
            sanitized = sanitized[:500] + "..."

        return sanitized.strip()

    def check_refusal(self, llm_response: str) -> Dict[str, any]:
        """
        Detect if LLM refused to answer.

        Args:
            llm_response: LLM response

        Returns:
            Dictionary with refusal detection
        """
        refusal_patterns = [
            r"i (can't|cannot|can not|am unable to)",
            r"i (don't|do not) have (access|information|data)",
            r"(sorry|apologize), (but )?i cannot",
            r"(not appropriate|not possible|unable) (for me )?to",
            r"as an ai (language model|assistant)",
        ]

        refused = False
        matched_patterns = []

        for pattern in refusal_patterns:
            if re.search(pattern, llm_response.lower()):
                refused = True
                matched_patterns.append(pattern)

        result = {
            "refused": refused,
            "matched_patterns": matched_patterns,
            "recommendation": "fallback_to_rules" if refused else "continue",
        }

        if refused:
            logger.warning("LLM refused to provide analysis")

        return result

    def calibrate_confidence(
        self, predicted_confidence: float, prediction: str, ground_truth: Optional[str] = None
    ) -> Dict[str, any]:
        """
        Calibrate confidence score based on historical accuracy.

        Args:
            predicted_confidence: Confidence from LLM (0-1)
            prediction: Predicted label
            ground_truth: Actual label (if known)

        Returns:
            Dictionary with calibrated confidence
        """
        # Store prediction for future calibration
        if ground_truth is not None:
            self.prediction_history.append(
                {
                    "confidence": predicted_confidence,
                    "prediction": prediction,
                    "correct": prediction == ground_truth,
                }
            )

        # Calculate calibration if we have history
        if len(self.prediction_history) >= 10:
            # Group by confidence buckets
            bucket_size = 0.1
            bucket = int(predicted_confidence / bucket_size) * bucket_size
            bucket_predictions = [
                p
                for p in self.prediction_history
                if bucket <= p["confidence"] < bucket + bucket_size
            ]

            if bucket_predictions:
                actual_accuracy = sum(p["correct"] for p in bucket_predictions) / len(
                    bucket_predictions
                )
                calibrated_confidence = (predicted_confidence + actual_accuracy) / 2
            else:
                calibrated_confidence = predicted_confidence
        else:
            # Not enough history - apply conservative calibration
            calibrated_confidence = predicted_confidence * 0.9

        result = {
            "original_confidence": predicted_confidence,
            "calibrated_confidence": calibrated_confidence,
            "calibration_applied": abs(predicted_confidence - calibrated_confidence) > 0.01,
            "historical_samples": len(self.prediction_history),
        }

        return result

    def validate_reasoning_chain(self, reasoning_steps: List[str]) -> Dict[str, any]:
        """
        Validate reasoning chain for completeness and detect shortcuts.

        Args:
            reasoning_steps: List of reasoning steps

        Returns:
            Dictionary with validation results
        """
        issues = []

        # Check minimum reasonable length
        if len(reasoning_steps) < 2:
            issues.append(
                {
                    "type": "insufficient_reasoning",
                    "message": "Too few reasoning steps - possible shortcut",
                }
            )

        # Check for suspiciously short steps
        avg_length = sum(len(step) for step in reasoning_steps) / max(len(reasoning_steps), 1)
        if avg_length < 20:
            issues.append({"type": "shallow_reasoning", "message": "Reasoning steps are too brief"})

        # Check for contradictions between steps
        for i in range(len(reasoning_steps) - 1):
            curr_step = reasoning_steps[i].lower()
            next_step = reasoning_steps[i + 1].lower()

            # Simple contradiction detection
            if (" not " in curr_step and " is " in next_step) or (
                " is " in curr_step and " not " in next_step
            ):
                issues.append(
                    {
                        "type": "potential_contradiction",
                        "message": f"Possible contradiction between steps {i + 1} and {i + 2}",
                        "steps": [reasoning_steps[i], reasoning_steps[i + 1]],
                    }
                )

        result = {
            "is_valid": len(issues) == 0,
            "num_steps": len(reasoning_steps),
            "avg_step_length": round(avg_length, 2),
            "issues": issues,
            "recommendation": "review" if len(issues) > 0 else "accept",
        }

        return result


# Global instance
_llm_safety: Optional[LLMSafety] = None


def get_llm_safety() -> LLMSafety:
    """
    Get global LLM safety instance.

    Returns:
        LLMSafety instance
    """
    global _llm_safety
    if _llm_safety is None:
        _llm_safety = LLMSafety()
    return _llm_safety
