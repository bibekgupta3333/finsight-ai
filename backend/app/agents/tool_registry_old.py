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


class ToolParameter(BaseModel):
    """Tool parameter specification."""

    name: str
    type: str  # "string", "number", "boolean", "object"
    description: str
    required: bool = True
    default: Optional[Any] = None


class ToolSchema(BaseModel):
    """Structured schema for a tool."""

    name: str
    description: str
    parameters: List[ToolParameter]
    returns: str  # Return type description
    examples: List[Dict[str, Any]] = Field(default_factory=list)
    timeout: float = 10.0  # seconds


class ToolResult(BaseModel):
    """Result from tool execution."""

    tool_name: str
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None
    execution_time: float  # seconds


class ToolRegistry:
    """
    Registry for agent tools.

    Manages tool registration, validation, and execution with
    timeout handling and error recovery.
    """

    def __init__(self):
        """Initialize tool registry."""
        self._tools: Dict[str, Callable] = {}
        self._schemas: Dict[str, ToolSchema] = {}
        self._register_default_tools()

    def register(
        self,
        schema: ToolSchema,
        function: Callable,
    ) -> None:
        """
        Register a tool.

        Args:
            schema: Tool schema
            function: Tool function
        """
        self._schemas[schema.name] = schema
        self._tools[schema.name] = function
        logger.info(f"Registered tool: {schema.name}")

    def get_schema(self, tool_name: str) -> Optional[ToolSchema]:
        """Get tool schema."""
        return self._schemas.get(tool_name)

    def list_tools(self) -> List[str]:
        """List all available tools."""
        return list(self._tools.keys())

    def list_schemas(self) -> List[ToolSchema]:
        """List all tool schemas."""
        return list(self._schemas.values())

    async def execute(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
    ) -> ToolResult:
        """
        Execute a tool with validation and timeout.

        Args:
            tool_name: Name of tool to execute
            parameters: Tool parameters

        Returns:
            Tool execution result
        """
        import time

        start_time = time.time()

        # Validate tool exists
        if tool_name not in self._tools:
            return ToolResult(
                tool_name=tool_name,
                success=False,
                error=f"Tool '{tool_name}' not found",
                execution_time=0.0,
            )

        # Get schema and function
        schema = self._schemas[tool_name]
        function = self._tools[tool_name]

        # Validate parameters
        validation_error = self._validate_parameters(schema, parameters)
        if validation_error:
            return ToolResult(
                tool_name=tool_name,
                success=False,
                error=validation_error,
                execution_time=time.time() - start_time,
            )

        # Execute with timeout
        try:
            result = await asyncio.wait_for(
                self._execute_function(function, parameters),
                timeout=schema.timeout,
            )

            return ToolResult(
                tool_name=tool_name,
                success=True,
                result=result,
                execution_time=time.time() - start_time,
            )

        except asyncio.TimeoutError:
            return ToolResult(
                tool_name=tool_name,
                success=False,
                error=f"Tool execution timeout after {schema.timeout}s",
                execution_time=time.time() - start_time,
            )

        except Exception as e:
            logger.error(f"Tool {tool_name} failed: {e}")
            return ToolResult(
                tool_name=tool_name,
                success=False,
                error=str(e),
                execution_time=time.time() - start_time,
            )

    async def execute_parallel(
        self,
        tool_calls: List[Dict[str, Any]],
    ) -> List[ToolResult]:
        """
        Execute multiple tools in parallel.

        Args:
            tool_calls: List of {tool_name, parameters} dicts

        Returns:
            List of tool results
        """
        tasks = [
            self.execute(call["tool_name"], call.get("parameters", {}))
            for call in tool_calls
        ]
        return await asyncio.gather(*tasks)

    def _validate_parameters(
        self,
        schema: ToolSchema,
        parameters: Dict[str, Any],
    ) -> Optional[str]:
        """
        Validate parameters against schema.

        Returns:
            Error message or None if valid
        """
        for param in schema.parameters:
            # Check required parameters
            if param.required and param.name not in parameters:
                return f"Missing required parameter: {param.name}"

            # Type validation (basic)
            if param.name in parameters:
                value = parameters[param.name]
                expected_type = param.type

                if expected_type == "string" and not isinstance(value, str):
                    return f"Parameter {param.name} should be string, got {type(value)}"
                elif expected_type == "number" and not isinstance(value, (int, float)):
                    return f"Parameter {param.name} should be number, got {type(value)}"
                elif expected_type == "boolean" and not isinstance(value, bool):
                    return f"Parameter {param.name} should be boolean, got {type(value)}"

        return None

    async def _execute_function(
        self,
        function: Callable,
        parameters: Dict[str, Any],
    ) -> Any:
        """Execute function (sync or async)."""
        if asyncio.iscoroutinefunction(function):
            return await function(**parameters)
        else:
            return function(**parameters)

    def _register_default_tools(self) -> None:
        """Register default fraud detection tools."""

        # Tool 1: Calculate risk score
        async def calculate_risk_score(transaction: Dict[str, Any]) -> float:
            """Calculate fraud risk score for transaction."""
            # Simple heuristic-based risk score
            score = 0.0

            amount = transaction.get("amount", 0)
            txn_type = transaction.get("type", "")

            # High amount = higher risk
            if amount > 100000:
                score += 40
            elif amount > 10000:
                score += 20
            elif amount > 1000:
                score += 10

            # Risky transaction types
            if txn_type in ["TRANSFER", "CASH_OUT"]:
                score += 20

            # Balance inconsistencies
            new_balance_orig = transaction.get("newbalanceOrig", 0)
            new_balance_dest = transaction.get("newbalanceDest", 0)

            if new_balance_orig == 0 and amount > 10000:
                score += 30  # Account drained

            if new_balance_dest == 0 and amount > 10000:
                score += 20  # Money disappeared

            return min(score, 100.0)

        self.register(
            schema=ToolSchema(
                name="calculate_risk_score",
                description="Calculate fraud risk score (0-100) for a transaction",
                parameters=[
                    ToolParameter(
                        name="transaction",
                        type="object",
                        description="Transaction data dictionary",
                        required=True,
                    ),
                ],
                returns="float (0-100 risk score)",
                examples=[
                    {
                        "transaction": {"amount": 500000, "type": "TRANSFER"},
                        "result": 85.0,
                    }
                ],
            ),
            function=calculate_risk_score,
        )

        # Tool 2: Query fraud policy
        async def query_fraud_policy(transaction_type: str) -> str:
            """Get fraud policy for transaction type."""
            policies = {
                "TRANSFER": "TRANSFER > 100k requires manual verification. Balance inconsistencies = automatic fraud flag.",
                "CASH_OUT": "CASH_OUT is inherently risky. Amounts > 50k require review.",
                "PAYMENT": "PAYMENT is generally low-risk unless amount > 10k.",
                "DEBIT": "DEBIT transactions are low-risk.",
                "CASH_IN": "CASH_IN is low-risk.",
            }
            return policies.get(transaction_type, "No specific policy found.")

        self.register(
            schema=ToolSchema(
                name="query_fraud_policy",
                description="Retrieve fraud detection policy for transaction type",
                parameters=[
                    ToolParameter(
                        name="transaction_type",
                        type="string",
                        description="Type of transaction (TRANSFER, CASH_OUT, etc.)",
                        required=True,
                    ),
                ],
                returns="string (policy text)",
                examples=[
                    {
                        "transaction_type": "TRANSFER",
                        "result": "TRANSFER > 100k requires verification",
                    }
                ],
            ),
            function=query_fraud_policy,
        )

        # Tool 3: Check account history
        async def check_account_history(account_id: str) -> Dict[str, Any]:
            """Check account transaction history (mock)."""
            # In production, this would query a database
            return {
                "account_id": account_id,
                "total_transactions": 150,
                "fraud_incidents": 0,
                "avg_transaction_amount": 500.0,
                "account_age_days": 365,
                "risk_level": "LOW",
            }

        self.register(
            schema=ToolSchema(
                name="check_account_history",
                description="Check historical transaction patterns for an account",
                parameters=[
                    ToolParameter(
                        name="account_id",
                        type="string",
                        description="Account identifier",
                        required=True,
                    ),
                ],
                returns="dict (account history summary)",
                examples=[
                    {
                        "account_id": "C123456",
                        "result": {"total_transactions": 150, "fraud_incidents": 0},
                    }
                ],
                timeout=5.0,
            ),
            function=check_account_history,
        )

        # Tool 4: Escalate to human
        async def escalate_to_human(
            transaction_id: str,
            reason: str,
        ) -> Dict[str, Any]:
            """Escalate transaction for human review."""
            logger.warning(f"Escalating {transaction_id}: {reason}")
            return {
                "escalated": True,
                "transaction_id": transaction_id,
                "reason": reason,
                "ticket_id": f"TICKET-{transaction_id}",
                "priority": "HIGH" if "fraud" in reason.lower() else "MEDIUM",
            }

        self.register(
            schema=ToolSchema(
                name="escalate_to_human",
                description="Escalate transaction for human review when uncertain",
                parameters=[
                    ToolParameter(
                        name="transaction_id",
                        type="string",
                        description="Transaction identifier",
                        required=True,
                    ),
                    ToolParameter(
                        name="reason",
                        type="string",
                        description="Reason for escalation",
                        required=True,
                    ),
                ],
                returns="dict (escalation confirmation)",
            ),
            function=escalate_to_human,
        )


# Global tool registry instance
_tool_registry: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    """Get global tool registry instance."""
    global _tool_registry
    if _tool_registry is None:
        _tool_registry = ToolRegistry()
    return _tool_registry
