"""
Tool Registry for Agent Tool Use.

Implements:
- Structured tool schemas with Pydantic validation
- Tool registration and discovery
- Tool execution with timeout and retry
- Tool confidence tracking
- Hallucination prevention
"""

import asyncio
import hashlib
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from pydantic import ValidationError

from app.agents.tool_schemas import (
    CalculateRiskScoreInput,
    CalculateRiskScoreOutput,
    QueryFraudPolicyInput,
    QueryFraudPolicyOutput,
    FetchAccountHistoryInput,
    FetchAccountHistoryOutput,
    EscalateToHumanInput,
    EscalateToHumanOutput,
    ExecuteSQLQueryInput,
    ExecuteSQLQueryOutput,
    ReadFileInput,
    ReadFileOutput,
    ExecutePythonCodeInput,
    ExecutePythonCodeOutput,
    ToolMetadata,
    TransactionType,
    RiskLevel,
)
from app.core.retry import retry_with_backoff, RetryConfig

logger = logging.getLogger(__name__)


# ============================================================================
# TOOL EXECUTION RESULT
# ============================================================================


class ToolExecutionResult:
    """Result from tool execution with confidence tracking."""

    def __init__(
        self,
        tool_name: str,
        success: bool,
        result: Optional[Any] = None,
        error: Optional[str] = None,
        execution_time_ms: float = 0.0,
        confidence: float = 1.0,
        retries: int = 0,
    ):
        self.tool_name = tool_name
        self.success = success
        self.result = result
        self.error = error
        self.execution_time_ms = execution_time_ms
        self.confidence = confidence  # 0-1
        self.retries = retries

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "tool_name": self.tool_name,
            "success": self.success,
            "result": self.result,
            "error": self.error,
            "execution_time_ms": self.execution_time_ms,
            "confidence": self.confidence,
            "retries": self.retries,
        }


# ============================================================================
# TOOL CONFIDENCE TRACKER
# ============================================================================


class ToolConfidenceTracker:
    """Track tool success rates and confidence scores."""

    def __init__(self):
        self._success_counts: Dict[str, int] = {}
        self._failure_counts: Dict[str, int] = {}
        self._total_calls: Dict[str, int] = {}

    def record_success(self, tool_name: str) -> None:
        """Record successful tool execution."""
        self._success_counts[tool_name] = self._success_counts.get(tool_name, 0) + 1
        self._total_calls[tool_name] = self._total_calls.get(tool_name, 0) + 1

    def record_failure(self, tool_name: str) -> None:
        """Record failed tool execution."""
        self._failure_counts[tool_name] = self._failure_counts.get(tool_name, 0) + 1
        self._total_calls[tool_name] = self._total_calls.get(tool_name, 0) + 1

    def get_confidence(self, tool_name: str) -> float:
        """Get confidence score (success rate) for tool."""
        total = self._total_calls.get(tool_name, 0)
        if total == 0:
            return 1.0  # Default confidence

        successes = self._success_counts.get(tool_name, 0)
        return successes / total

    def get_stats(self, tool_name: str) -> Dict[str, Any]:
        """Get statistics for tool."""
        return {
            "tool_name": tool_name,
            "total_calls": self._total_calls.get(tool_name, 0),
            "successes": self._success_counts.get(tool_name, 0),
            "failures": self._failure_counts.get(tool_name, 0),
            "success_rate": self.get_confidence(tool_name),
        }

    def get_all_stats(self) -> List[Dict[str, Any]]:
        """Get statistics for all tools."""
        return [self.get_stats(tool_name) for tool_name in self._total_calls.keys()]


# ============================================================================
# TOOL REGISTRY
# ============================================================================


class ToolRegistry:
    """
    Comprehensive tool registry with:
    - Structured schemas and validation
    - Execution with timeout and retry
    - Confidence tracking
    - Hallucination prevention
    """

    def __init__(self):
        """Initialize tool registry."""
        self._tools: Dict[str, Callable] = {}
        self._metadata: Dict[str, ToolMetadata] = {}
        self._confidence_tracker = ToolConfidenceTracker()
        self._allowed_tools: Optional[List[str]] = None  # None = all allowed

        # Register default tools
        self._register_default_tools()

    def register_tool(
        self,
        name: str,
        function: Callable,
        metadata: ToolMetadata,
    ) -> None:
        """Register a new tool."""
        self._tools[name] = function
        self._metadata[name] = metadata
        logger.info(f"Registered tool: {name}")

    def set_allowed_tools(self, tool_names: List[str]) -> None:
        """Restrict available tools (hallucination prevention)."""
        self._allowed_tools = tool_names
        logger.info(f"Restricted to tools: {tool_names}")

    def validate_tool_exists(self, tool_name: str) -> bool:
        """Validate tool exists (prevent hallucination)."""
        if tool_name not in self._tools:
            logger.warning(f"Tool '{tool_name}' does not exist (possible hallucination)")
            return False

        if self._allowed_tools and tool_name not in self._allowed_tools:
            logger.warning(f"Tool '{tool_name}' not in allowed list")
            return False

        return True

    def get_tool_metadata(self, tool_name: str) -> Optional[ToolMetadata]:
        """Get metadata for tool."""
        return self._metadata.get(tool_name)

    def list_tools(self) -> List[str]:
        """List all available tool names."""
        if self._allowed_tools:
            return self._allowed_tools
        return list(self._tools.keys())

    def list_metadata(self) -> List[ToolMetadata]:
        """List all tool metadata."""
        if self._allowed_tools:
            return [self._metadata[name] for name in self._allowed_tools if name in self._metadata]
        return list(self._metadata.values())

    async def execute_tool(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        max_retries: int = 3,
    ) -> ToolExecutionResult:
        """
        Execute tool with validation, timeout, and retry.

        Args:
            tool_name: Name of tool to execute
            parameters: Tool parameters
            max_retries: Maximum retry attempts

        Returns:
            ToolExecutionResult with success/failure info
        """
        start_time = time.time()

        # Validate tool exists (hallucination prevention)
        if not self.validate_tool_exists(tool_name):
            return ToolExecutionResult(
                tool_name=tool_name,
                success=False,
                error=f"Tool '{tool_name}' does not exist or is not allowed",
                execution_time_ms=0.0,
            )

        # Get tool metadata
        metadata = self._metadata[tool_name]
        function = self._tools[tool_name]

        # Execute with retry logic
        retry_config = RetryConfig(
            max_attempts=max_retries,
            base_delay=0.1,
            max_delay=2.0,
            exponential_base=2.0,
        )

        attempts = 0
        last_error = None

        for attempt in range(max_retries):
            attempts = attempt + 1
            try:
                # Execute with timeout
                result = await asyncio.wait_for(
                    self._execute_with_validation(function, parameters, metadata),
                    timeout=metadata.timeout_seconds,
                )

                # Record success
                self._confidence_tracker.record_success(tool_name)

                execution_time = (time.time() - start_time) * 1000
                return ToolExecutionResult(
                    tool_name=tool_name,
                    success=True,
                    result=result,
                    execution_time_ms=execution_time,
                    confidence=self._confidence_tracker.get_confidence(tool_name),
                    retries=attempt,
                )

            except asyncio.TimeoutError:
                last_error = f"Timeout after {metadata.timeout_seconds}s"
                logger.warning(f"Tool {tool_name} timeout (attempt {attempt + 1}/{max_retries})")

            except ValidationError as e:
                # Don't retry validation errors
                self._confidence_tracker.record_failure(tool_name)
                execution_time = (time.time() - start_time) * 1000
                return ToolExecutionResult(
                    tool_name=tool_name,
                    success=False,
                    error=f"Validation error: {str(e)}",
                    execution_time_ms=execution_time,
                    confidence=self._confidence_tracker.get_confidence(tool_name),
                    retries=attempt,
                )

            except Exception as e:
                last_error = str(e)
                logger.warning(f"Tool {tool_name} failed: {e} (attempt {attempt + 1}/{max_retries})")

            # Wait before retry (exponential backoff)
            if attempt < max_retries - 1:
                delay = retry_config.base_delay * (retry_config.exponential_base ** attempt)
                delay = min(delay, retry_config.max_delay)
                await asyncio.sleep(delay)

        # All retries failed
        self._confidence_tracker.record_failure(tool_name)
        execution_time = (time.time() - start_time) * 1000
        return ToolExecutionResult(
            tool_name=tool_name,
            success=False,
            error=f"Failed after {attempts} attempts: {last_error}",
            execution_time_ms=execution_time,
            confidence=self._confidence_tracker.get_confidence(tool_name),
            retries=attempts - 1,
        )

    async def _execute_with_validation(
        self,
        function: Callable,
        parameters: Dict[str, Any],
        metadata: ToolMetadata,
    ) -> Any:
        """Execute function with parameter validation."""
        # Call function (sync or async)
        if asyncio.iscoroutinefunction(function):
            result = await function(**parameters)
        else:
            result = function(**parameters)

        return result

    def get_confidence_stats(self) -> List[Dict[str, Any]]:
        """Get confidence statistics for all tools."""
        return self._confidence_tracker.get_all_stats()

    def _register_default_tools(self) -> None:
        """Register default fraud detection tools."""

        # Tool 1: calculate_risk_score
        async def calculate_risk_score(
            transaction_id: str,
            amount: float,
            transaction_type: str,
            oldbalance_org: float,
            newbalance_orig: float,
            oldbalance_dest: float,
            newbalance_dest: float,
            step: int,
        ) -> Dict[str, Any]:
            """Calculate fraud risk score for transaction."""
            start_time = time.time()

            risk_score = 0.0
            risk_factors = []

            # High amount risk
            if amount > 100000:
                risk_score += 40
                risk_factors.append("high_value_transfer")
            elif amount > 50000:
                risk_score += 25
                risk_factors.append("medium_value_transfer")

            # Balance drain detection
            if oldbalance_org > 0:
                drain_ratio = (oldbalance_org - newbalance_orig) / oldbalance_org
                if drain_ratio > 0.9:
                    risk_score += 35
                    risk_factors.append(f"balance_drain_{int(drain_ratio * 100)}%")
                elif drain_ratio > 0.7:
                    risk_score += 20
                    risk_factors.append(f"balance_drain_{int(drain_ratio * 100)}%")

            # New destination account
            if oldbalance_dest == 0 and newbalance_dest > 50000:
                risk_score += 15
                risk_factors.append("destination_new_account")

            # Risky transaction types
            if transaction_type in ["TRANSFER", "CASH_OUT"]:
                risk_score += 10
                risk_factors.append(f"risky_type_{transaction_type}")

            # Cap at 100
            risk_score = min(risk_score, 100.0)

            # Determine risk level
            if risk_score >= 75:
                risk_level = "HIGH"
            elif risk_score >= 50:
                risk_level = "MEDIUM"
            else:
                risk_level = "LOW"

            # Confidence based on data completeness
            confidence = 0.9 if all([oldbalance_org, newbalance_orig]) else 0.7

            execution_time = (time.time() - start_time) * 1000

            return {
                "transaction_id": transaction_id,
                "risk_score": round(risk_score, 2),
                "risk_level": risk_level,
                "confidence": confidence,
                "risk_factors": risk_factors,
                "explanation": f"{risk_level}-risk {transaction_type}: ${amount:,.0f} with {len(risk_factors)} risk indicators",
                "execution_time_ms": round(execution_time, 2),
            }

        self.register_tool(
            name="calculate_risk_score",
            function=calculate_risk_score,
            metadata=ToolMetadata(
                name="calculate_risk_score",
                description="Calculate fraud risk score (0-100) for a transaction based on amount, balance changes, and transaction type",
                input_schema=CalculateRiskScoreInput.model_json_schema(),
                output_schema=CalculateRiskScoreOutput.model_json_schema(),
                category="risk_analysis",
                requires_auth=False,
                max_retries=3,
                timeout_seconds=10,
                example_input=CalculateRiskScoreInput.model_config["json_schema_extra"]["examples"][0],
                example_output=CalculateRiskScoreOutput.model_config["json_schema_extra"]["examples"][0],
            ),
        )

        # Tool 2: query_fraud_policy
        async def query_fraud_policy(
            transaction_type: str,
            amount: Optional[float] = None,
            risk_factors: Optional[List[str]] = None,
        ) -> Dict[str, Any]:
            """Query fraud detection policy for transaction type."""
            start_time = time.time()

            # Load policy from data/fraud_policies/
            policy_file = Path(f"data/fraud_policies/{transaction_type.lower()}_fraud_policy.md")

            if policy_file.exists():
                policy_text = policy_file.read_text()
            else:
                # Default policies
                policies = {
                    "TRANSFER": "TRANSFER transactions exceeding $100,000 require additional verification. Balance drain >80% indicates high fraud risk.",
                    "CASH_OUT": "CASH_OUT is inherently risky. Amounts >$50K require manual review. Account age and velocity are key factors.",
                    "PAYMENT": "PAYMENT is generally low-risk unless amount >$10K or unusual merchant.",
                    "DEBIT": "DEBIT transactions are typically low-risk. Monitor for unusual patterns.",
                    "CASH_IN": "CASH_IN is low-risk. Focus on source verification for amounts >$50K.",
                }
                policy_text = policies.get(transaction_type, "No specific policy found")

            # Define thresholds
            thresholds = {
                "TRANSFER": {"max_amount": 100000, "balance_drain_threshold": 0.8, "velocity_limit_24h": 3},
                "CASH_OUT": {"max_amount": 50000, "balance_drain_threshold": 0.9, "velocity_limit_24h": 5},
                "PAYMENT": {"max_amount": 10000, "velocity_limit_24h": 10},
                "DEBIT": {"max_amount": 5000, "velocity_limit_24h": 15},
                "CASH_IN": {"max_amount": 50000, "velocity_limit_24h": 5},
            }

            # Generate recommendations
            recommendations = []
            threshold = thresholds.get(transaction_type, {})

            if amount and amount > threshold.get("max_amount", float("inf")):
                recommendations.append(f"Amount exceeds ${threshold['max_amount']:,} threshold - require manual approval")

            if risk_factors:
                if "balance_drain" in str(risk_factors):
                    recommendations.append("Verify destination account age and history")
                if "new_account" in str(risk_factors):
                    recommendations.append("Additional KYC verification recommended")

            if not recommendations:
                recommendations.append("Standard processing - within policy limits")

            execution_time = (time.time() - start_time) * 1000

            return {
                "transaction_type": transaction_type,
                "policy_text": policy_text[:500],  # Truncate
                "thresholds": threshold,
                "recommendations": recommendations,
                "execution_time_ms": round(execution_time, 2),
            }

        self.register_tool(
            name="query_fraud_policy",
            function=query_fraud_policy,
            metadata=ToolMetadata(
                name="query_fraud_policy",
                description="Query fraud detection policy and thresholds for specific transaction type",
                input_schema=QueryFraudPolicyInput.model_json_schema(),
                output_schema=QueryFraudPolicyOutput.model_json_schema(),
                category="policy_lookup",
                requires_auth=False,
                max_retries=2,
                timeout_seconds=5,
                example_input=QueryFraudPolicyInput.model_config["json_schema_extra"]["examples"][0],
                example_output=QueryFraudPolicyOutput.model_config["json_schema_extra"]["examples"][0],
            ),
        )

        # Tool 3: fetch_account_history
        async def fetch_account_history(
            account_id: str,
            days: int = 30,
            transaction_types: Optional[List[str]] = None,
            limit: int = 100,
        ) -> Dict[str, Any]:
            """Fetch account transaction history (mock implementation)."""
            start_time = time.time()

            # Mock transaction data
            transactions = [
                {
                    "transaction_id": f"TX_{i:03d}",
                    "type": transaction_types[i % len(transaction_types)] if transaction_types else "PAYMENT",
                    "amount": 1000 + (i * 500),
                    "timestamp": f"2026-01-{min(i % 30 + 1, 31):02d}T10:00:00Z",
                    "is_fraud": i % 10 == 0,  # 10% fraud rate
                }
                for i in range(min(15, limit))
            ]

            total_count = len(transactions)
            avg_amount = sum(t["amount"] for t in transactions) / total_count if total_count > 0 else 0
            fraud_count = sum(1 for t in transactions if t["is_fraud"])

            execution_time = (time.time() - start_time) * 1000

            return {
                "account_id": account_id,
                "transactions": transactions,
                "total_count": total_count,
                "avg_transaction_amount": round(avg_amount, 2),
                "fraud_count": fraud_count,
                "execution_time_ms": round(execution_time, 2),
            }

        self.register_tool(
            name="fetch_account_history",
            function=fetch_account_history,
            metadata=ToolMetadata(
                name="fetch_account_history",
                description="Fetch historical transactions for an account to detect patterns",
                input_schema=FetchAccountHistoryInput.model_json_schema(),
                output_schema=FetchAccountHistoryOutput.model_json_schema(),
                category="data_retrieval",
                requires_auth=True,
                max_retries=3,
                timeout_seconds=15,
                example_input=FetchAccountHistoryInput.model_config["json_schema_extra"]["examples"][0],
                example_output=FetchAccountHistoryOutput.model_config["json_schema_extra"]["examples"][0],
            ),
        )

        # Tool 4: escalate_to_human
        async def escalate_to_human(
            transaction_id: str,
            reason: str,
            confidence_score: float,
            details: str,
            priority: int = 3,
        ) -> Dict[str, Any]:
            """Escalate transaction to human reviewer."""
            start_time = time.time()

            escalation_id = f"ESC_{datetime.now().strftime('%Y%m%d')}_{hash(transaction_id) % 1000:03d}"

            # Assign to analyst based on priority
            assigned_to = f"fraud_analyst_0{(priority % 3) + 1}"

            # Estimate resolution time based on priority
            resolution_minutes = {1: 5, 2: 15, 3: 30, 4: 60, 5: 120}

            logger.warning(f"ESCALATION: {transaction_id} - {reason} (confidence: {confidence_score})")

            return {
                "escalation_id": escalation_id,
                "transaction_id": transaction_id,
                "status": "PENDING_REVIEW",
                "assigned_to": assigned_to,
                "created_at": datetime.now().isoformat(),
                "estimated_resolution_minutes": resolution_minutes.get(priority, 30),
            }

        self.register_tool(
            name="escalate_to_human",
            function=escalate_to_human,
            metadata=ToolMetadata(
                name="escalate_to_human",
                description="Escalate transaction for human review when confidence is low or patterns are ambiguous",
                input_schema=EscalateToHumanInput.model_json_schema(),
                output_schema=EscalateToHumanOutput.model_json_schema(),
                category="escalation",
                requires_auth=False,
                max_retries=1,
                timeout_seconds=5,
                example_input=EscalateToHumanInput.model_config["json_schema_extra"]["examples"][0],
                example_output=EscalateToHumanOutput.model_config["json_schema_extra"]["examples"][0],
            ),
        )

        # Tool 5: execute_sql_query (read-only)
        async def execute_sql_query(
            query: str,
            timeout_seconds: int = 10,
        ) -> Dict[str, Any]:
            """Execute read-only SQL query (mock implementation)."""
            start_time = time.time()

            # Mock query results
            mock_results = {
                "rows": [
                    {"type": "TRANSFER", "count": 152, "avg_amount": 85000.0},
                    {"type": "CASH_OUT", "count": 89, "avg_amount": 12000.0},
                    {"type": "PAYMENT", "count": 543, "avg_amount": 450.0},
                ],
                "row_count": 3,
                "columns": ["type", "count", "avg_amount"],
            }

            # Generate query hash for caching
            query_hash = hashlib.md5(query.encode()).hexdigest()[:12]

            execution_time = (time.time() - start_time) * 1000

            return {
                **mock_results,
                "execution_time_ms": round(execution_time, 2),
                "query_hash": query_hash,
            }

        self.register_tool(
            name="execute_sql_query",
            function=execute_sql_query,
            metadata=ToolMetadata(
                name="execute_sql_query",
                description="Execute read-only SQL query to analyze transaction patterns",
                input_schema=ExecuteSQLQueryInput.model_json_schema(),
                output_schema=ExecuteSQLQueryOutput.model_json_schema(),
                category="data_retrieval",
                requires_auth=True,
                max_retries=2,
                timeout_seconds=30,
                example_input=ExecuteSQLQueryInput.model_config["json_schema_extra"]["examples"][0],
                example_output=ExecuteSQLQueryOutput.model_config["json_schema_extra"]["examples"][0],
            ),
        )

        logger.info(f"Registered {len(self._tools)} default tools")


# Global registry instance
_tool_registry: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    """Get global tool registry instance."""
    global _tool_registry
    if _tool_registry is None:
        _tool_registry = ToolRegistry()
    return _tool_registry
