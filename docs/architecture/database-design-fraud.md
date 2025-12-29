# Database Design - FinSight AI Fraud Detection

## Comprehensive Data Architecture

**Last Updated:** December 28, 2025
**Dataset:** PaySim Mobile Money (6.3M transactions)
**Focus:** Fraud detection + reasoning + RAG

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [PaySim Schema](#paysim-schema)
3. [Vector Store Design](#vector-store-design)
4. [PostgreSQL Schema](#postgresql-schema)
5. [Data Models (Pydantic)](#data-models-pydantic)
6. [Indexing Strategy](#indexing-strategy)
7. [Sample Queries](#sample-queries)
8. [Data Flow](#data-flow)

---

## Architecture Overview

### Hybrid Database Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      APPLICATION LAYER                       │
│                      (FastAPI Backend)                       │
└────────┬──────────────────┬─────────────────┬───────────────┘
         │                  │                 │
         ▼                  ▼                 ▼
┌────────────────┐ ┌─────────────────┐ ┌──────────────────┐
│   PAYSIM CSV   │ │  CHROMADB       │ │  POSTGRESQL      │
│   (Source)     │ │  (Vector Store) │ │  (Relational)    │
│                │ │                 │ │                  │
│ • Transactions │ │ • Fraud cases   │ │ • Users          │
│ • Fraud labels │ │ • Policies      │ │ • Sessions       │
│ • Features     │ │ • Explanations  │ │ • Audit logs     │
│                │ │ • Patterns      │ │ • Feedback       │
└────────────────┘ └─────────────────┘ └──────────────────┘
```

### Database Responsibilities

| Database | Use Case | Data Type | Performance |
|----------|----------|-----------|-------------|
| **CSV/Parquet** | Training data, batch processing | Transaction records | Read-heavy, batch |
| **ChromaDB** | RAG, similar fraud cases | Embeddings + metadata | Similarity search |
| **PostgreSQL** | User management, real-time logs | Structured, relational | ACID transactions |
| **Redis (future)** | Caching, session management | Key-value | Sub-millisecond |

---

## PaySim Schema

### Raw CSV Structure

**File:** `data/raw/PS_20174392719_1491204439457_log.csv`

```sql
CREATE TABLE paysim_raw (
    -- Temporal
    step INT NOT NULL,                     -- Time unit (1-744 for 30 days)

    -- Transaction
    type VARCHAR(10) NOT NULL,             -- CASH_OUT, PAYMENT, CASH_IN, TRANSFER, DEBIT
    amount DECIMAL(15, 2) NOT NULL,        -- Transaction amount

    -- Origin Account
    nameOrig VARCHAR(20) NOT NULL,         -- Customer ID (e.g., C1231006815)
    oldbalanceOrg DECIMAL(15, 2),          -- Balance before transaction
    newbalanceOrig DECIMAL(15, 2),         -- Balance after transaction

    -- Destination Account
    nameDest VARCHAR(20) NOT NULL,         -- Destination ID (C* or M* for merchant)
    oldbalanceDest DECIMAL(15, 2),         -- Balance before
    newbalanceDest DECIMAL(15, 2),         -- Balance after

    -- Labels
    isFraud INT NOT NULL,                  -- Ground truth (0 or 1)
    isFlaggedFraud INT NOT NULL,           -- System flag (1 if amount > 200k TRANSFER)

    -- Constraints
    CHECK (amount >= 0),
    CHECK (isFraud IN (0, 1)),
    CHECK (isFlaggedFraud IN (0, 1)),
    CHECK (type IN ('CASH_OUT', 'PAYMENT', 'CASH_IN', 'TRANSFER', 'DEBIT'))
);
```

### Processed Features Table

**File:** `data/processed/paysim_features.parquet`

```sql
CREATE TABLE paysim_features (
    -- Original fields (hashed for privacy)
    transaction_id BIGSERIAL PRIMARY KEY,
    step INT NOT NULL,
    type VARCHAR(10) NOT NULL,
    amount DECIMAL(15, 2) NOT NULL,

    -- Hashed account IDs
    nameOrig_hash VARCHAR(64) NOT NULL,    -- SHA256 hash
    nameDest_hash VARCHAR(64) NOT NULL,

    -- Balance fields
    oldbalanceOrg DECIMAL(15, 2),
    newbalanceOrig DECIMAL(15, 2),
    oldbalanceDest DECIMAL(15, 2),
    newbalanceDest DECIMAL(15, 2),

    -- Engineered Features
    hour INT,                              -- 0-23
    day_of_week INT,                       -- 0-6
    is_weekend BOOLEAN,
    time_category VARCHAR(10),             -- morning/afternoon/evening/night

    balance_diff_orig DECIMAL(15, 2),      -- oldbalanceOrg - newbalanceOrig
    balance_diff_dest DECIMAL(15, 2),      -- newbalanceDest - oldbalanceDest
    amount_pct_balance DECIMAL(5, 4),      -- amount / oldbalanceOrg

    log_amount DECIMAL(10, 4),             -- log(1 + amount)
    amount_category VARCHAR(10),           -- tiny/small/medium/large/huge
    high_amount BOOLEAN,                   -- amount > 100k

    orig_zero_after BOOLEAN,               -- newbalanceOrig == 0
    dest_zero_before BOOLEAN,              -- oldbalanceDest == 0
    account_emptied BOOLEAN,               -- oldbalanceOrg > 0 AND newbalanceOrig == 0

    amount_to_flag_ratio DECIMAL(6, 4),    -- amount / 200000
    suspicious_dest BOOLEAN,               -- Zero dest balance receiving funds
    exact_balance_match BOOLEAN,           -- amount == oldbalanceOrg

    -- Labels
    isFraud INT NOT NULL,
    isFlaggedFraud INT NOT NULL,

    -- Model Predictions (added after inference)
    fraud_probability DECIMAL(5, 4),       -- Model output (0-1)
    risk_score INT,                        -- 0-100
    decision VARCHAR(10),                  -- APPROVE/REVIEW/BLOCK
    confidence DECIMAL(5, 4),              -- Prediction confidence

    -- Metadata
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_fraud (isFraud),
    INDEX idx_type (type),
    INDEX idx_amount (amount),
    INDEX idx_step (step)
);
```

### Data Statistics Table

```sql
CREATE TABLE dataset_statistics (
    stat_id SERIAL PRIMARY KEY,
    dataset_version VARCHAR(20) NOT NULL,  -- e.g., "v1.3_features"

    total_transactions BIGINT,
    fraud_count BIGINT,
    fraud_rate DECIMAL(6, 4),

    -- Per transaction type
    cash_out_count BIGINT,
    payment_count BIGINT,
    cash_in_count BIGINT,
    transfer_count BIGINT,
    debit_count BIGINT,

    -- Amount statistics
    min_amount DECIMAL(15, 2),
    max_amount DECIMAL(15, 2),
    mean_amount DECIMAL(15, 2),
    median_amount DECIMAL(15, 2),

    -- Temporal
    time_period_days INT,
    earliest_step INT,
    latest_step INT,

    computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## Vector Store Design

### ChromaDB Collections

#### Collection 1: `fraud_cases`

**Purpose:** Store known fraud cases for similarity search (RAG)

```python
{
    "collection_name": "fraud_cases",
    "embedding_model": "bge-small-en-v1.5",  # 384 dimensions
    "metadata_schema": {
        "case_id": "string",
        "transaction_type": "string",        # CASH_OUT, TRANSFER
        "amount": "float",
        "risk_score": "int",                 # 0-100
        "fraud_pattern": "string",           # account_takeover, money_mule, etc.
        "detection_method": "string",        # ML, rule-based, human
        "created_at": "string",
        "is_synthetic": "boolean"            # True if generated for training
    },
    "document": "Natural language description of fraud case"
}
```

**Example Document:**
```
"High-risk CASH_OUT transaction of $185,432 where the origin account was
completely emptied (old balance: $185,432, new balance: $0) and the
destination account had zero balance before receiving funds. Transaction
occurred at 3:47 AM on a weekend. Pattern: Account takeover."
```

---

#### Collection 2: `fraud_policies`

**Purpose:** Store fraud detection rules and policies for RAG retrieval

```python
{
    "collection_name": "fraud_policies",
    "metadata_schema": {
        "policy_id": "string",
        "policy_name": "string",
        "severity": "string",                # critical, high, medium, low
        "transaction_types": "array[string]",
        "threshold_amount": "float",
        "created_at": "string",
        "last_updated": "string",
        "version": "string"
    },
    "document": "Policy description and application rules"
}
```

**Example Document:**
```
"Policy: Account Emptying Detection
Severity: Critical
Rule: Flag any CASH_OUT or TRANSFER transaction where:
1. The transaction amount equals or exceeds 95% of the origin account balance
2. The new origin balance is less than $10
3. Transaction occurs between midnight and 6 AM
Action: Automatically BLOCK and escalate to human review."
```

---

#### Collection 3: `fraud_explanations`

**Purpose:** Store LLM-generated explanations for training preference models

```python
{
    "collection_name": "fraud_explanations",
    "metadata_schema": {
        "explanation_id": "string",
        "case_id": "string",               # Reference to fraud_cases
        "model": "string",                 # mistral-7b, gpt-4, etc.
        "quality_score": "float",          # Human rating (1-5)
        "faithfulness_score": "float",     # Explanation ↔ prediction alignment
        "safety_score": "float",           # No harmful advice
        "created_at": "string"
    },
    "document": "Chain-of-thought explanation of fraud decision"
}
```

**Example Document:**
```
"This transaction is flagged as high-risk fraud (98% probability) because:

1. Suspicious Amount: The transaction amount ($185,432) matches exactly
   the origin account balance, indicating possible account takeover.

2. Temporal Pattern: Transaction occurred at 3:47 AM on a Saturday, which
   is statistically unusual for legitimate large transfers.

3. Balance Anomaly: The destination account had a zero balance before
   receiving funds, a common pattern in money mule operations.

4. Complete Withdrawal: The origin account was completely emptied, leaving
   $0 balance, which is rarely seen in legitimate transactions.

Recommendation: BLOCK transaction and escalate to fraud investigation team."
```

---

#### Collection 4: `transaction_patterns`

**Purpose:** Store temporal and behavioral patterns for anomaly detection

```python
{
    "collection_name": "transaction_patterns",
    "metadata_schema": {
        "pattern_id": "string",
        "pattern_type": "string",          # temporal, amount, behavioral
        "account_hash": "string",          # Hashed account ID
        "frequency": "int",                # Occurrences
        "avg_amount": "float",
        "std_amount": "float",
        "time_windows": "array[int]",      # Hours when active
        "is_anomalous": "boolean",
        "last_seen": "string"
    },
    "document": "Pattern description"
}
```

---

## PostgreSQL Schema

### Users & Sessions

```sql
-- User accounts
CREATE TABLE users (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) DEFAULT 'analyst',    -- analyst, admin, reviewer
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);

-- User sessions
CREATE TABLE sessions (
    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(user_id),
    token_hash VARCHAR(255) NOT NULL,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    is_active BOOLEAN DEFAULT TRUE
);
```

### Fraud Analysis Logs

```sql
-- Real-time fraud analysis results
CREATE TABLE fraud_analysis (
    analysis_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(user_id),

    -- Transaction data
    transaction_id VARCHAR(50),
    transaction_type VARCHAR(10),
    amount DECIMAL(15, 2),
    timestamp TIMESTAMP,

    -- Analysis results
    fraud_probability DECIMAL(5, 4),
    risk_score INT,
    decision VARCHAR(10),              -- APPROVE, REVIEW, BLOCK
    confidence DECIMAL(5, 4),

    -- Model info
    model_version VARCHAR(20),
    inference_time_ms INT,
    token_count INT,

    -- LLM explanation
    explanation TEXT,
    reasoning_chain JSON,              -- Chain-of-thought steps
    retrieved_policies JSON,           -- RAG results

    -- Human review
    requires_review BOOLEAN DEFAULT FALSE,
    reviewed_by UUID REFERENCES users(user_id),
    review_decision VARCHAR(10),
    review_comments TEXT,
    reviewed_at TIMESTAMP,

    analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_decision (decision),
    INDEX idx_requires_review (requires_review),
    INDEX idx_analyzed_at (analyzed_at)
);
```

### Human Feedback

```sql
-- Collect feedback for model improvement
CREATE TABLE human_feedback (
    feedback_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    analysis_id UUID REFERENCES fraud_analysis(analysis_id),
    user_id UUID REFERENCES users(user_id),

    -- Feedback
    model_decision VARCHAR(10),
    human_decision VARCHAR(10),
    agreement BOOLEAN,

    feedback_type VARCHAR(20),         -- correction, confirmation, escalation
    explanation TEXT,
    severity VARCHAR(10),              -- low, medium, high, critical

    -- For training
    used_for_training BOOLEAN DEFAULT FALSE,
    training_batch VARCHAR(20),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Safety Incidents

```sql
-- Log safety violations and adversarial attempts
CREATE TABLE safety_incidents (
    incident_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(user_id),

    incident_type VARCHAR(30),         -- prompt_injection, jailbreak, privacy_leak
    severity VARCHAR(10),              -- low, medium, high, critical

    user_input TEXT,
    system_response TEXT,
    detected_by VARCHAR(20),           -- input_filter, output_validator, human

    was_blocked BOOLEAN,
    action_taken VARCHAR(50),

    reported_by UUID REFERENCES users(user_id),
    reported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_incident_type (incident_type),
    INDEX idx_severity (severity)
);
```

---

## Data Models (Pydantic)

### Transaction Model

```python
from pydantic import BaseModel, Field, validator
from typing import Optional, Literal
from datetime import datetime
from decimal import Decimal

class Transaction(BaseModel):
    """PaySim transaction model"""

    # Core fields
    transaction_id: Optional[int] = None
    step: int = Field(..., ge=1, le=744, description="Time step (1 hour units)")
    type: Literal["CASH_OUT", "PAYMENT", "CASH_IN", "TRANSFER", "DEBIT"]
    amount: Decimal = Field(..., ge=0, description="Transaction amount")

    # Origin account (hashed for privacy)
    nameOrig_hash: str = Field(..., min_length=16, max_length=64)
    oldbalanceOrg: Decimal = Field(..., ge=0)
    newbalanceOrig: Decimal = Field(..., ge=0)

    # Destination account
    nameDest_hash: str = Field(..., min_length=16, max_length=64)
    oldbalanceDest: Decimal = Field(..., ge=0)
    newbalanceDest: Decimal = Field(..., ge=0)

    # Labels
    isFraud: Literal[0, 1]
    isFlaggedFraud: Literal[0, 1] = 0

    # Engineered features (populated during processing)
    hour: Optional[int] = Field(None, ge=0, le=23)
    day_of_week: Optional[int] = Field(None, ge=0, le=6)
    is_weekend: Optional[bool] = None
    balance_diff_orig: Optional[Decimal] = None
    log_amount: Optional[Decimal] = None

    # Metadata
    processed_at: Optional[datetime] = None

    @validator('balance_diff_orig', always=True)
    def calculate_balance_diff(cls, v, values):
        if v is None and 'oldbalanceOrg' in values and 'newbalanceOrig' in values:
            return values['oldbalanceOrg'] - values['newbalanceOrig']
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "step": 1,
                "type": "CASH_OUT",
                "amount": 9839.64,
                "nameOrig_hash": "a1b2c3d4e5f6g7h8",
                "oldbalanceOrg": 170136.00,
                "newbalanceOrig": 160296.36,
                "nameDest_hash": "h8g7f6e5d4c3b2a1",
                "oldbalanceDest": 0.00,
                "newbalanceDest": 0.00,
                "isFraud": 0,
                "isFlaggedFraud": 0
            }
        }
```

### Fraud Analysis Result

```python
class FraudAnalysisResult(BaseModel):
    """Result of fraud detection analysis"""

    analysis_id: str
    transaction_id: str

    # ML predictions
    fraud_probability: float = Field(..., ge=0.0, le=1.0)
    risk_score: int = Field(..., ge=0, le=100)
    decision: Literal["APPROVE", "REVIEW", "BLOCK"]
    confidence: float = Field(..., ge=0.0, le=1.0)

    # LLM reasoning
    explanation: str
    reasoning_chain: list[str]  # Chain-of-thought steps
    retrieved_policies: list[dict]  # RAG results

    # Metadata
    model_version: str
    inference_time_ms: int
    token_count: int
    requires_review: bool

    analyzed_at: datetime = Field(default_factory=datetime.now)

    class Config:
        json_schema_extra = {
            "example": {
                "analysis_id": "550e8400-e29b-41d4-a716-446655440000",
                "transaction_id": "TXN_123456",
                "fraud_probability": 0.87,
                "risk_score": 92,
                "decision": "BLOCK",
                "confidence": 0.94,
                "explanation": "High-risk fraud detected due to...",
                "reasoning_chain": [
                    "Step 1: Analyze amount ($185k) relative to balance",
                    "Step 2: Check temporal pattern (3 AM weekend)",
                    "Step 3: Evaluate destination account history"
                ],
                "retrieved_policies": [
                    {"policy_id": "POL-001", "match_score": 0.92}
                ],
                "model_version": "v1.2",
                "inference_time_ms": 1840,
                "token_count": 420,
                "requires_review": True
            }
        }
```

---

## Sample Queries

### SQL Queries (PostgreSQL)

```sql
-- 1. Get all high-risk transactions requiring review
SELECT
    analysis_id,
    transaction_id,
    amount,
    risk_score,
    decision,
    explanation
FROM fraud_analysis
WHERE requires_review = TRUE
  AND reviewed_at IS NULL
ORDER BY risk_score DESC, analyzed_at ASC
LIMIT 50;

-- 2. Model performance metrics
SELECT
    DATE(analyzed_at) as date,
    decision,
    COUNT(*) as count,
    AVG(risk_score) as avg_risk,
    AVG(inference_time_ms) as avg_latency_ms,
    AVG(token_count) as avg_tokens
FROM fraud_analysis
WHERE analyzed_at > NOW() - INTERVAL '7 days'
GROUP BY DATE(analyzed_at), decision
ORDER BY date DESC, decision;

-- 3. Human feedback disagreement rate
SELECT
    model_decision,
    human_decision,
    COUNT(*) as count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as percentage
FROM human_feedback
WHERE agreement = FALSE
GROUP BY model_decision, human_decision
ORDER BY count DESC;

-- 4. Safety incidents by type
SELECT
    incident_type,
    severity,
    COUNT(*) as incident_count,
    SUM(CASE WHEN was_blocked THEN 1 ELSE 0 END) as blocked_count,
    ROUND(AVG(CASE WHEN was_blocked THEN 1 ELSE 0 END) * 100, 2) as block_rate_pct
FROM safety_incidents
WHERE reported_at > NOW() - INTERVAL '30 days'
GROUP BY incident_type, severity
ORDER BY severity DESC, incident_count DESC;
```

### ChromaDB Queries (Python)

```python
import chromadb
from chromadb.config import Settings

# Initialize client
client = chromadb.Client(Settings(
    chroma_db_impl="duckdb+parquet",
    persist_directory="./chroma_db"
))

# Get collection
fraud_cases = client.get_collection("fraud_cases")

# 1. Find similar fraud cases
query = "Large CASH_OUT transaction at unusual hour with zero destination balance"
similar_cases = fraud_cases.query(
    query_texts=[query],
    n_results=5,
    where={"transaction_type": "CASH_OUT", "risk_score": {"$gte": 80}}
)

# 2. Retrieve relevant fraud policies
policies = client.get_collection("fraud_policies")
relevant_policies = policies.query(
    query_texts=[f"Transaction type: CASH_OUT, Amount: $185000, Time: 3 AM"],
    n_results=3,
    where={"severity": {"$in": ["critical", "high"]}}
)

# 3. Get high-quality explanations for fine-tuning
explanations = client.get_collection("fraud_explanations")
training_examples = explanations.query(
    query_texts=["Account takeover pattern explanation"],
    n_results=50,
    where={
        "quality_score": {"$gte": 4.0},
        "safety_score": {"$gte": 4.5}
    }
)
```

---

## Data Flow

### Transaction Analysis Pipeline

```
1. CSV Input
   ↓
2. Load → Pandas/Polars DataFrame
   ↓
3. Feature Engineering
   ↓
4. Save to Parquet (paysim_features)
   ↓
5. Model Inference
   ├─→ ML Classifier (fraud_probability)
   └─→ LLM Explanation (via RAG)
       ├─→ Query ChromaDB (fraud_cases, policies)
       └─→ Generate explanation with reasoning
   ↓
6. Decision Logic
   ├─→ APPROVE (risk < 30%)
   ├─→ REVIEW (30% ≤ risk < 70%)
   └─→ BLOCK (risk ≥ 70%)
   ↓
7. Save to PostgreSQL (fraud_analysis)
   ↓
8. If requires_review:
   └─→ Human review queue
       ↓
   Human feedback
       ↓
   Update feedback table
       ↓
   Periodic model retraining
```

---

## Indexing Strategy

### PostgreSQL Indexes

```sql
-- Transaction analysis
CREATE INDEX idx_fraud_analysis_decision ON fraud_analysis(decision);
CREATE INDEX idx_fraud_analysis_timestamp ON fraud_analysis(analyzed_at DESC);
CREATE INDEX idx_fraud_analysis_review ON fraud_analysis(requires_review) WHERE requires_review = TRUE;
CREATE INDEX idx_fraud_analysis_risk ON fraud_analysis(risk_score DESC);

-- Human feedback
CREATE INDEX idx_feedback_agreement ON human_feedback(agreement);
CREATE INDEX idx_feedback_training ON human_feedback(used_for_training) WHERE used_for_training = FALSE;

-- Safety
CREATE INDEX idx_safety_type_severity ON safety_incidents(incident_type, severity);

-- Composite indexes
CREATE INDEX idx_analysis_decision_time ON fraud_analysis(decision, analyzed_at DESC);
```

### ChromaDB Performance

- **Embedding model:** bge-small-en-v1.5 (384 dim) - faster than large models
- **Distance metric:** Cosine similarity (default)
- **Batch size:** 1000 documents for bulk inserts
- **Persist frequency:** Every 100 operations

---

## Backup & Recovery

```bash
# PostgreSQL backup
pg_dump -U postgres finsight_db > backup_$(date +%Y%m%d).sql

# ChromaDB backup
tar -czf chroma_backup_$(date +%Y%m%d).tar.gz ./chroma_db/

# CSV data backup (DVC)
dvc push
```

---

## Next Steps

1. ✅ **Schema design complete**
2. ⏭️ **Implement database initialization scripts**
3. ⏭️ **Create data migration pipeline**
4. ⏭️ **Populate ChromaDB with fraud cases**
5. ⏭️ **Test query performance**
6. ⏭️ **Setup backup automation**

---

## References

- [ChromaDB Documentation](https://docs.trychroma.com/)
- [PostgreSQL Best Practices](https://wiki.postgresql.org/wiki/Don%27t_Do_This)
- [PaySim Dataset Paper](https://www.researchgate.net/publication/313138956)
