"""
Tool schemas and validation infrastructure.

Implements structured tool schemas with:
- Pydantic validation for all tool inputs/outputs
- JSON schema generation for LLM consumption
- Parameter constraints and type checking
- Comprehensive documentation strings
"""

import logging
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)


# ============================================================================
# ENUMS FOR TOOL PARAMETERS
# ============================================================================


class TransactionType(str, Enum):
    """Valid transaction types for fraud detection."""

    CASH_IN = "CASH_IN"
    CASH_OUT = "CASH_OUT"
    DEBIT = "DEBIT"
    PAYMENT = "PAYMENT"
    TRANSFER = "TRANSFER"


class RiskLevel(str, Enum):
    """Risk level classification."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class EscalationReason(str, Enum):
    """Valid reasons for human escalation."""

    HIGH_VALUE = "HIGH_VALUE"
    AMBIGUOUS_PATTERN = "AMBIGUOUS_PATTERN"
    POLICY_EXCEPTION = "POLICY_EXCEPTION"
    SYSTEM_ERROR = "SYSTEM_ERROR"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"


# ============================================================================
# TOOL INPUT SCHEMAS
# ============================================================================


class CalculateRiskScoreInput(BaseModel):
    """Input schema for calculate_risk_score tool."""

    transaction_id: str = Field(
        ..., description="Unique transaction identifier", min_length=1, max_length=100
    )
    amount: float = Field(..., description="Transaction amount in USD", gt=0)
    transaction_type: TransactionType = Field(..., description="Type of transaction")
    oldbalance_org: float = Field(
        ..., description="Origin account balance before transaction", ge=0
    )
    newbalance_orig: float = Field(
        ..., description="Origin account balance after transaction", ge=0
    )
    oldbalance_dest: float = Field(
        ..., description="Destination account balance before transaction", ge=0
    )
    newbalance_dest: float = Field(
        ..., description="Destination account balance after transaction", ge=0
    )
    step: int = Field(
        ..., description="Time step in hours (1-744)", ge=1, le=744
    )

    @field_validator("newbalance_orig", "newbalance_dest")
    @classmethod
    def validate_balance_consistency(cls, v: float, info) -> float:
        """Validate balance changes are logical."""
        if v < 0:
            raise ValueError("Balance cannot be negative")
        return v

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "transaction_id": "TX_RISK_001",
                    "amount": 185000.0,
                    "transaction_type": "TRANSFER",
                    "oldbalance_org": 200000.0,
                    "newbalance_orig": 15000.0,
                    "oldbalance_dest": 0.0,
                    "newbalance_dest": 185000.0,
                    "step": 156,
                }
            ]
        }


class QueryFraudPolicyInput(BaseModel):
    """Input schema for query_fraud_policy tool."""

    transaction_type: TransactionType = Field(..., description="Transaction type to query policy for")
    amount: Optional[float] = Field(None, description="Transaction amount (for threshold checks)", gt=0)
    risk_factors: Optional[List[str]] = Field(
        default_factory=list,
        description="Additional risk factors to consider",
        max_length=10,
    )

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "transaction_type": "TRANSFER",
                    "amount": 150000.0,
                    "risk_factors": ["high_value", "balance_drain", "new_account"],
                }
            ]
        }


class FetchAccountHistoryInput(BaseModel):
    """Input schema for fetch_account_history tool."""

    account_id: str = Field(
        ..., description="Account ID to fetch history for", min_length=1, max_length=50
    )
    days: int = Field(
        default=30, description="Number of days of history to fetch", ge=1, le=365
    )
    transaction_types: Optional[List[TransactionType]] = Field(
        None, description="Filter by transaction types"
    )
    limit: int = Field(
        default=100, description="Maximum number of transactions to return", ge=1, le=1000
    )

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "account_id": "ACC_12345",
                    "days": 30,
                    "transaction_types": ["TRANSFER", "CASH_OUT"],
                    "limit": 100,
                }
            ]
        }


class EscalateToHumanInput(BaseModel):
    """Input schema for escalate_to_human tool."""

    transaction_id: str = Field(..., description="Transaction ID requiring escalation")
    reason: EscalationReason = Field(..., description="Reason for escalation")
    confidence_score: float = Field(
        ..., description="Model confidence score (0-1)", ge=0, le=1
    )
    details: str = Field(
        ..., description="Detailed explanation for escalation", min_length=10, max_length=1000
    )
    priority: int = Field(
        default=3, description="Priority level (1=highest, 5=lowest)", ge=1, le=5
    )

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "transaction_id": "TX_ESCALATE_001",
                    "reason": "HIGH_VALUE",
                    "confidence_score": 0.45,
                    "details": "Transaction amount $185K exceeds policy threshold with ambiguous pattern. Balance drain ratio 92.5% suggests fraud but merchant verification needed.",
                    "priority": 1,
                }
            ]
        }


class ExecuteSQLQueryInput(BaseModel):
    """Input schema for execute_sql_query tool (read-only)."""

    query: str = Field(
        ...,
        description="SQL query to execute (SELECT only, read-only)",
        min_length=10,
        max_length=2000,
    )
    timeout_seconds: int = Field(
        default=10, description="Query timeout in seconds", ge=1, le=30
    )

    @field_validator("query")
    @classmethod
    def validate_read_only(cls, v: str) -> str:
        """Ensure query is read-only (SELECT, WITH only)."""
        query_upper = v.strip().upper()
        allowed_keywords = ["SELECT", "WITH", "FROM", "WHERE", "JOIN", "GROUP", "ORDER", "LIMIT"]
        forbidden_keywords = [
            "INSERT",
            "UPDATE",
            "DELETE",
            "DROP",
            "CREATE",
            "ALTER",
            "TRUNCATE",
            "EXEC",
            "EXECUTE",
        ]

        for keyword in forbidden_keywords:
            if keyword in query_upper:
                raise ValueError(f"Forbidden keyword '{keyword}' detected. Only SELECT queries allowed.")

        if not any(keyword in query_upper for keyword in ["SELECT", "WITH"]):
            raise ValueError("Query must start with SELECT or WITH")

        return v

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "query": "SELECT type, COUNT(*) as count, AVG(amount) as avg_amount FROM transactions WHERE is_fraud = TRUE GROUP BY type ORDER BY count DESC LIMIT 10",
                    "timeout_seconds": 10,
                }
            ]
        }


class ReadFileInput(BaseModel):
    """Input schema for read_file tool (sandboxed)."""

    file_path: str = Field(
        ...,
        description="Relative path to file within fraud_policies directory",
        min_length=1,
        max_length=200,
    )

    @field_validator("file_path")
    @classmethod
    def validate_safe_path(cls, v: str) -> str:
        """Prevent directory traversal attacks."""
        if ".." in v or v.startswith("/"):
            raise ValueError("Path traversal not allowed. Use relative paths only.")
        if not v.endswith(".md"):
            raise ValueError("Only .md policy files allowed")
        return v

    class Config:
        json_schema_extra = {
            "examples": [{"file_path": "transfer_fraud_policy.md"}]
        }


class ExecutePythonCodeInput(BaseModel):
    """Input schema for execute_python_code tool (sandboxed)."""

    code: str = Field(
        ...,
        description="Python code to execute (risk calculations only)",
        min_length=1,
        max_length=5000,
    )
    timeout_seconds: int = Field(
        default=5, description="Execution timeout", ge=1, le=10
    )

    @field_validator("code")
    @classmethod
    def validate_safe_code(cls, v: str) -> str:
        """Prevent dangerous imports and operations."""
        forbidden_imports = ["os", "subprocess", "sys", "eval", "exec", "open", "input", "__import__"]
        code_lower = v.lower()

        for forbidden in forbidden_imports:
            if forbidden in code_lower:
                raise ValueError(f"Forbidden operation '{forbidden}' detected")

        return v

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "code": "balance_drain = (oldbalance - newbalance) / oldbalance if oldbalance > 0 else 0\nrisk_score = min(balance_drain * 100, 100)\nresult = {'balance_drain_ratio': balance_drain, 'risk_score': risk_score}",
                    "timeout_seconds": 5,
                }
            ]
        }


# ============================================================================
# TOOL OUTPUT SCHEMAS
# ============================================================================


class CalculateRiskScoreOutput(BaseModel):
    """Output schema for calculate_risk_score tool."""

    transaction_id: str
    risk_score: float = Field(..., description="Risk score (0-100)", ge=0, le=100)
    risk_level: RiskLevel
    confidence: float = Field(..., description="Confidence in score (0-1)", ge=0, le=1)
    risk_factors: List[str] = Field(
        description="List of detected risk factors"
    )
    explanation: str = Field(description="Human-readable explanation")
    execution_time_ms: float

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "transaction_id": "TX_RISK_001",
                    "risk_score": 85.5,
                    "risk_level": "HIGH",
                    "confidence": 0.92,
                    "risk_factors": [
                        "high_value_transfer",
                        "balance_drain_92%",
                        "destination_new_account",
                    ],
                    "explanation": "High-risk TRANSFER: $185K drains 92.5% of origin balance to new destination account. Exceeds $100K threshold.",
                    "execution_time_ms": 45.2,
                }
            ]
        }


class QueryFraudPolicyOutput(BaseModel):
    """Output schema for query_fraud_policy tool."""

    transaction_type: TransactionType
    policy_text: str = Field(description="Relevant policy text")
    thresholds: Dict[str, Any] = Field(description="Policy thresholds")
    recommendations: List[str] = Field(description="Policy-based recommendations")
    execution_time_ms: float

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "transaction_type": "TRANSFER",
                    "policy_text": "TRANSFER transactions exceeding $100,000 require additional verification. Balance drain >80% indicates high fraud risk.",
                    "thresholds": {
                        "max_amount": 100000,
                        "balance_drain_threshold": 0.8,
                        "velocity_limit_24h": 3,
                    },
                    "recommendations": [
                        "Verify destination account age",
                        "Check transaction velocity",
                        "Require manual approval for >$100K",
                    ],
                    "execution_time_ms": 12.3,
                }
            ]
        }


class FetchAccountHistoryOutput(BaseModel):
    """Output schema for fetch_account_history tool."""

    account_id: str
    transactions: List[Dict[str, Any]] = Field(
        description="List of historical transactions"
    )
    total_count: int = Field(description="Total transactions found")
    avg_transaction_amount: float
    fraud_count: int = Field(description="Number of fraudulent transactions")
    execution_time_ms: float

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "account_id": "ACC_12345",
                    "transactions": [
                        {
                            "transaction_id": "TX_001",
                            "type": "TRANSFER",
                            "amount": 5000.0,
                            "timestamp": "2026-01-01T10:00:00Z",
                            "is_fraud": False,
                        }
                    ],
                    "total_count": 15,
                    "avg_transaction_amount": 12500.0,
                    "fraud_count": 2,
                    "execution_time_ms": 28.7,
                }
            ]
        }


class EscalateToHumanOutput(BaseModel):
    """Output schema for escalate_to_human tool."""

    escalation_id: str = Field(description="Unique escalation ID")
    transaction_id: str
    status: str = Field(description="Escalation status")
    assigned_to: Optional[str] = Field(None, description="Assigned human reviewer")
    created_at: datetime
    estimated_resolution_minutes: int

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "escalation_id": "ESC_20260103_001",
                    "transaction_id": "TX_ESCALATE_001",
                    "status": "PENDING_REVIEW",
                    "assigned_to": "fraud_analyst_01",
                    "created_at": "2026-01-03T10:30:00Z",
                    "estimated_resolution_minutes": 15,
                }
            ]
        }


class ExecuteSQLQueryOutput(BaseModel):
    """Output schema for execute_sql_query tool."""

    rows: List[Dict[str, Any]] = Field(description="Query result rows")
    row_count: int
    columns: List[str]
    execution_time_ms: float
    query_hash: str = Field(description="Hash for caching")

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "rows": [
                        {"type": "TRANSFER", "count": 152, "avg_amount": 85000.0},
                        {"type": "CASH_OUT", "count": 89, "avg_amount": 12000.0},
                    ],
                    "row_count": 2,
                    "columns": ["type", "count", "avg_amount"],
                    "execution_time_ms": 45.6,
                    "query_hash": "a3f5c8d2e1b4",
                }
            ]
        }


class ReadFileOutput(BaseModel):
    """Output schema for read_file tool."""

    file_path: str
    content: str = Field(description="File content")
    size_bytes: int
    lines: int
    execution_time_ms: float

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "file_path": "transfer_fraud_policy.md",
                    "content": "# TRANSFER Fraud Detection Policy\n\n## High-Risk Indicators\n- Amount > $100,000\n- Balance drain > 80%...",
                    "size_bytes": 2048,
                    "lines": 45,
                    "execution_time_ms": 8.2,
                }
            ]
        }


class ExecutePythonCodeOutput(BaseModel):
    """Output schema for execute_python_code tool."""

    result: Dict[str, Any] = Field(description="Execution result")
    stdout: str = Field(description="Standard output")
    execution_time_ms: float
    memory_used_kb: int

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "result": {"balance_drain_ratio": 0.925, "risk_score": 92.5},
                    "stdout": "",
                    "execution_time_ms": 12.4,
                    "memory_used_kb": 256,
                }
            ]
        }


# ============================================================================
# TOOL METADATA SCHEMA
# ============================================================================


class ToolMetadata(BaseModel):
    """Metadata for tool registry."""

    name: str = Field(description="Tool name (snake_case)")
    description: str = Field(description="Tool purpose and usage")
    input_schema: Dict[str, Any] = Field(description="JSON schema for inputs")
    output_schema: Dict[str, Any] = Field(description="JSON schema for outputs")
    category: str = Field(description="Tool category")
    requires_auth: bool = Field(default=False, description="Requires authentication")
    max_retries: int = Field(default=3, description="Max retry attempts")
    timeout_seconds: int = Field(default=30, description="Default timeout")
    example_input: Dict[str, Any]
    example_output: Dict[str, Any]

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "name": "calculate_risk_score",
                    "description": "Calculate fraud risk score for a transaction",
                    "input_schema": {"type": "object", "properties": {}},
                    "output_schema": {"type": "object", "properties": {}},
                    "category": "risk_analysis",
                    "requires_auth": False,
                    "max_retries": 3,
                    "timeout_seconds": 30,
                    "example_input": {},
                    "example_output": {},
                }
            ]
        }
