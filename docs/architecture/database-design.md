# Database Design - FinSight AI

## Table of Contents
1. [Overview](#overview)
2. [Database Choice](#database-choice)
3. [Schema Design](#schema-design)
4. [Vector Store Schema](#vector-store-schema)
5. [Data Models](#data-models)
6. [Relationships](#relationships)
7. [Indexing Strategy](#indexing-strategy)
8. [Sample Queries](#sample-queries)

---

## Overview

FinSight AI uses a hybrid database approach:
- **Vector Store (ChromaDB):** For embeddings and semantic search
- **Optional Relational DB (PostgreSQL/SQLite):** For structured data and user management (future)
- **File Storage (S3/Local):** For uploaded documents

---

## Database Choice

### Primary: Vector Store (ChromaDB)

**Why ChromaDB?**
- ✅ Open-source and free
- ✅ Easy Docker deployment
- ✅ Built-in embedding support
- ✅ No separate database server needed
- ✅ Perfect for RAG applications
- ✅ Persistent storage
- ✅ Fast similarity search

**Alternatives Considered:**
- FAISS: No metadata support
- Pinecone: Paid service
- Weaviate: More complex setup
- Milvus: Heavy infrastructure

### Optional: PostgreSQL (Future Enhancement)

For user management, authentication, and complex queries:
- User accounts
- Session management
- Audit logs
- Analytics

---

## Schema Design

### Vector Store Collections (ChromaDB)

#### Collection 1: `transactions`

Stores transaction embeddings for semantic search

```json
{
  "collection_name": "transactions",
  "metadata_schema": {
    "user_id": "string",
    "transaction_id": "string",
    "date": "string (ISO 8601)",
    "amount": "float",
    "currency": "string",
    "category": "string",
    "merchant": "string",
    "payment_method": "string",
    "is_anomaly": "boolean",
    "confidence_score": "float",
    "created_at": "string (ISO 8601)"
  },
  "document": "Transaction description for embedding"
}
```

**Example Document:**
```
"Grocery shopping at Whole Foods Market on 2025-12-15 for $127.50"
```

---

#### Collection 2: `categories`

Stores category definitions and examples

```json
{
  "collection_name": "categories",
  "metadata_schema": {
    "category_id": "string",
    "category_name": "string",
    "parent_category": "string",
    "keywords": "array[string]",
    "icon": "string",
    "created_at": "string (ISO 8601)"
  },
  "document": "Category description and examples"
}
```

**Example Document:**
```
"Groceries & Food: Supermarkets, grocery stores, food delivery. Examples: Walmart, Target, Whole Foods, Instacart"
```

**Default Categories:**
- 🍔 Food & Dining
  - Groceries
  - Restaurants
  - Fast Food
  - Coffee Shops
- 🏠 Housing
  - Rent/Mortgage
  - Utilities
  - Home Maintenance
- 🚗 Transportation
  - Gas
  - Public Transit
  - Parking
  - Car Maintenance
- 🛍️ Shopping
  - Clothing
  - Electronics
  - Personal Care
- 💊 Health & Wellness
  - Pharmacy
  - Gym
  - Medical
- 🎬 Entertainment
  - Streaming Services
  - Movies
  - Events
- 📱 Subscriptions
  - Software
  - Media
  - Services
- 💰 Finance
  - Investments
  - Transfers
  - Fees

---

#### Collection 3: `spending_patterns`

Stores detected patterns and insights

```json
{
  "collection_name": "spending_patterns",
  "metadata_schema": {
    "pattern_id": "string",
    "user_id": "string",
    "pattern_type": "string",
    "frequency": "string",
    "avg_amount": "float",
    "category": "string",
    "detected_at": "string (ISO 8601)",
    "confidence": "float"
  },
  "document": "Pattern description"
}
```

**Pattern Types:**
- `recurring`: Regular payments (subscriptions, bills)
- `seasonal`: Seasonal spending variations
- `trend`: Increasing/decreasing trends
- `outlier`: Unusual spending

**Example Document:**
```
"Monthly Netflix subscription of $15.99 on the 5th of each month"
```

---

#### Collection 4: `anomalies`

Stores detected anomalies for tracking

```json
{
  "collection_name": "anomalies",
  "metadata_schema": {
    "anomaly_id": "string",
    "user_id": "string",
    "transaction_id": "string",
    "anomaly_type": "string",
    "severity": "string",
    "reason": "string",
    "detected_at": "string (ISO 8601)",
    "resolved": "boolean"
  },
  "document": "Anomaly explanation"
}
```

**Anomaly Types:**
- `amount`: Unusually high/low amount
- `frequency`: Unusual transaction frequency
- `location`: Unusual merchant/location
- `category`: Unexpected category for user
- `timing`: Unusual time of transaction

**Severity Levels:**
- `low`: Minor deviation (1-2σ)
- `medium`: Significant deviation (2-3σ)
- `high`: Major deviation (>3σ)

---

#### Collection 5: `insights`

Stores generated insights and recommendations

```json
{
  "collection_name": "insights",
  "metadata_schema": {
    "insight_id": "string",
    "user_id": "string",
    "insight_type": "string",
    "priority": "string",
    "generated_at": "string (ISO 8601)",
    "relevant_until": "string (ISO 8601)",
    "acted_upon": "boolean"
  },
  "document": "Insight explanation and recommendation"
}
```

**Insight Types:**
- `savings`: Potential savings identified
- `budget`: Budget recommendations
- `trend`: Spending trend alert
- `goal`: Progress towards financial goals

---

### Optional: PostgreSQL Schema (Future)

#### Users Table

```sql
CREATE TABLE users (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    is_active BOOLEAN DEFAULT true,
    preferences JSONB DEFAULT '{}'
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_created_at ON users(created_at);
```

#### Sessions Table

```sql
CREATE TABLE sessions (
    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ip_address INET,
    user_agent TEXT
);

CREATE INDEX idx_sessions_user_id ON sessions(user_id);
CREATE INDEX idx_sessions_expires_at ON sessions(expires_at);
```

#### Uploaded Files Table

```sql
CREATE TABLE uploaded_files (
    file_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    original_filename VARCHAR(255) NOT NULL,
    file_type VARCHAR(50) NOT NULL,
    file_size_bytes INTEGER NOT NULL,
    storage_path TEXT NOT NULL,
    upload_status VARCHAR(50) DEFAULT 'pending',
    processed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX idx_uploaded_files_user_id ON uploaded_files(user_id);
CREATE INDEX idx_uploaded_files_status ON uploaded_files(upload_status);
CREATE INDEX idx_uploaded_files_created_at ON uploaded_files(created_at);
```

#### Audit Logs Table

```sql
CREATE TABLE audit_logs (
    log_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(user_id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50),
    resource_id VARCHAR(255),
    details JSONB,
    ip_address INET,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at);
```

---

## Data Models

### Pydantic Models (Backend)

```python
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from enum import Enum

class Currency(str, Enum):
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    # Add more as needed

class PaymentMethod(str, Enum):
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    CASH = "cash"
    TRANSFER = "transfer"
    CHECK = "check"
    OTHER = "other"

class Transaction(BaseModel):
    transaction_id: str = Field(..., description="Unique transaction identifier")
    user_id: str = Field(..., description="User identifier")
    date: datetime = Field(..., description="Transaction date")
    amount: float = Field(..., gt=0, description="Transaction amount")
    currency: Currency = Field(default=Currency.USD)
    description: str = Field(..., min_length=1, max_length=500)
    merchant: Optional[str] = Field(None, max_length=200)
    category: Optional[str] = None
    payment_method: PaymentMethod = Field(default=PaymentMethod.OTHER)
    is_anomaly: bool = Field(default=False)
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "transaction_id": "txn_123abc",
                "user_id": "user_456def",
                "date": "2025-12-15T14:30:00Z",
                "amount": 127.50,
                "currency": "USD",
                "description": "Grocery shopping",
                "merchant": "Whole Foods Market",
                "category": "Groceries",
                "payment_method": "credit_card",
                "is_anomaly": False,
                "confidence_score": 0.95
            }
        }

class Category(BaseModel):
    category_id: str
    category_name: str
    parent_category: Optional[str] = None
    keywords: List[str] = Field(default_factory=list)
    icon: Optional[str] = None
    description: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Anomaly(BaseModel):
    anomaly_id: str
    user_id: str
    transaction_id: str
    anomaly_type: str
    severity: str
    reason: str
    explanation: str
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    resolved: bool = Field(default=False)

class Insight(BaseModel):
    insight_id: str
    user_id: str
    insight_type: str
    title: str
    description: str
    priority: str
    actionable: bool = Field(default=True)
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    relevant_until: Optional[datetime] = None
    acted_upon: bool = Field(default=False)

class AnalysisResult(BaseModel):
    transactions: List[Transaction]
    categories: dict
    anomalies: List[Anomaly]
    insights: List[Insight]
    summary: str
    confidence: float
    processing_time_ms: int
```

---

## Relationships

### Entity Relationship Diagram

```
┌─────────────────┐
│     Users       │
│  (PostgreSQL)   │
└────────┬────────┘
         │ 1
         │
         │ N
┌────────▼────────┐         ┌──────────────────┐
│ Uploaded Files  │         │   Transactions   │
│  (PostgreSQL)   │────────▶│   (ChromaDB)     │
└─────────────────┘         └────────┬─────────┘
                                     │
                    ┌────────────────┼────────────────┐
                    │                │                │
                    │ 1              │ 1              │ 1
                    │ N              │ N              │ N
         ┌──────────▼──────┐  ┌──────▼─────┐  ┌──────▼─────┐
         │   Anomalies     │  │ Categories │  │  Patterns  │
         │   (ChromaDB)    │  │ (ChromaDB) │  │ (ChromaDB) │
         └─────────────────┘  └────────────┘  └────────────┘
                    │
                    │ 1
                    │ N
         ┌──────────▼──────┐
         │    Insights     │
         │   (ChromaDB)    │
         └─────────────────┘
```

---

## Indexing Strategy

### ChromaDB

ChromaDB automatically creates vector indexes using HNSW (Hierarchical Navigable Small World):

**Metadata Indexes:**
```python
# Automatically indexed by ChromaDB
indexed_fields = [
    "user_id",
    "transaction_id",
    "category",
    "date",
    "is_anomaly"
]
```

### PostgreSQL (If used)

```sql
-- Primary indexes (already covered by PRIMARY KEY)

-- Secondary indexes for common queries
CREATE INDEX idx_transactions_user_date ON uploaded_files(user_id, created_at DESC);
CREATE INDEX idx_sessions_token ON sessions(token_hash);

-- Full-text search index (if needed)
CREATE INDEX idx_transactions_description_fts
ON uploaded_files
USING GIN(to_tsvector('english', metadata->>'description'));
```

---

## Sample Queries

### ChromaDB Queries

#### 1. Semantic Search for Transactions

```python
from chromadb import Client

client = Client()
collection = client.get_collection("transactions")

# Find similar transactions
results = collection.query(
    query_texts=["grocery shopping"],
    where={"user_id": "user_123"},
    n_results=10
)
```

#### 2. Filter by Category

```python
# Get all restaurant transactions
results = collection.query(
    query_texts=["dining"],
    where={
        "user_id": "user_123",
        "category": "Restaurants"
    },
    n_results=100
)
```

#### 3. Get Anomalies

```python
anomalies_collection = client.get_collection("anomalies")

# Get unresolved anomalies
results = anomalies_collection.get(
    where={
        "user_id": "user_123",
        "resolved": False
    }
)
```

#### 4. Date Range Query

```python
# Transactions in date range
results = collection.query(
    query_texts=["all transactions"],
    where={
        "user_id": "user_123",
        "$and": [
            {"date": {"$gte": "2025-12-01T00:00:00Z"}},
            {"date": {"$lte": "2025-12-31T23:59:59Z"}}
        ]
    }
)
```

### PostgreSQL Queries (If used)

#### 1. Get User Transaction Summary

```sql
SELECT
    u.user_id,
    u.full_name,
    COUNT(uf.file_id) as total_files_uploaded,
    SUM(uf.file_size_bytes) as total_storage_used,
    MAX(uf.created_at) as last_upload
FROM users u
LEFT JOIN uploaded_files uf ON u.user_id = uf.user_id
WHERE u.is_active = true
GROUP BY u.user_id, u.full_name;
```

#### 2. Audit Log Query

```sql
SELECT
    al.action,
    al.resource_type,
    u.email,
    al.created_at,
    al.details
FROM audit_logs al
JOIN users u ON al.user_id = u.user_id
WHERE al.created_at >= NOW() - INTERVAL '7 days'
ORDER BY al.created_at DESC
LIMIT 100;
```

---

## Data Migration Strategy

### Initial Setup

```python
# initialize_vector_store.py
import chromadb
from chromadb.config import Settings

def initialize_collections():
    client = chromadb.Client(Settings(
        chroma_db_impl="duckdb+parquet",
        persist_directory="./data/chromadb"
    ))

    # Create collections
    transactions = client.create_collection(
        name="transactions",
        metadata={"description": "User transaction embeddings"}
    )

    categories = client.create_collection(
        name="categories",
        metadata={"description": "Transaction category definitions"}
    )

    patterns = client.create_collection(
        name="spending_patterns",
        metadata={"description": "Detected spending patterns"}
    )

    anomalies = client.create_collection(
        name="anomalies",
        metadata={"description": "Detected anomalies"}
    )

    insights = client.create_collection(
        name="insights",
        metadata={"description": "Generated insights"}
    )

    return client

if __name__ == "__main__":
    client = initialize_collections()
    print("✅ Vector store initialized successfully")
```

### Seed Categories

```python
# seed_categories.py
from sentence_transformers import SentenceTransformer
import chromadb

def seed_default_categories():
    client = chromadb.Client(Settings(
        persist_directory="./data/chromadb"
    ))

    collection = client.get_collection("categories")
    model = SentenceTransformer('all-MiniLM-L6-v2')

    categories = [
        {
            "id": "cat_001",
            "name": "Groceries",
            "keywords": ["grocery", "supermarket", "food", "walmart", "target"],
            "document": "Groceries and food shopping at supermarkets"
        },
        # ... more categories
    ]

    for cat in categories:
        collection.add(
            ids=[cat["id"]],
            documents=[cat["document"]],
            metadatas=[{
                "category_name": cat["name"],
                "keywords": cat["keywords"]
            }]
        )

    print(f"✅ Seeded {len(categories)} categories")
```

---

## Backup & Recovery

### ChromaDB Backup

```bash
# Backup vector store
tar -czf chromadb_backup_$(date +%Y%m%d).tar.gz ./data/chromadb/

# Restore
tar -xzf chromadb_backup_20251226.tar.gz -C ./data/
```

### PostgreSQL Backup (If used)

```bash
# Backup
pg_dump -U postgres -d finsight -f backup_$(date +%Y%m%d).sql

# Restore
psql -U postgres -d finsight -f backup_20251226.sql
```

---

## Performance Considerations

1. **Vector Search Optimization:**
   - Use appropriate embedding dimensions (384 for MiniLM)
   - Limit collection size per user
   - Implement pagination for large result sets

2. **Metadata Filtering:**
   - Index frequently queried fields
   - Use composite filters efficiently
   - Cache common queries

3. **Data Retention:**
   - Archive old transactions (>2 years)
   - Periodic cleanup of resolved anomalies
   - Compress historical data

---

**Document Version:** 1.0
**Last Updated:** December 26, 2025
**Status:** Initial Design
