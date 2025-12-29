# Database Diagram - FinSight AI

This document provides a visual representation of the database schema for FinSight AI, based on the [Database Design](../architecture/database-design.md).

## Entity Relationship Diagram (ERD)

```mermaid
erDiagram
    USER ||--o{ UPLOADED_FILE : uploads
    USER ||--o{ SESSION : has
    USER ||--o{ AUDIT_LOG : generates

    UPLOADED_FILE ||--o{ TRANSACTION : contains

    TRANSACTION ||--o{ ANOMALY : has
    TRANSACTION ||--o{ CATEGORY : belongs_to
    TRANSACTION ||--o{ SPENDING_PATTERN : forms

    USER ||--o{ INSIGHT : receives
    ANOMALY ||--o{ INSIGHT : triggers

    USER {
        uuid user_id PK
        string email UK
        string password_hash
        string full_name
        timestamp created_at
        jsonb preferences
    }

    SESSION {
        uuid session_id PK
        uuid user_id FK
        string token_hash
        timestamp expires_at
        string ip_address
    }

    UPLOADED_FILE {
        uuid file_id PK
        uuid user_id FK
        string original_filename
        string file_type
        integer file_size_bytes
        string storage_path
        string upload_status
        timestamp processed_at
    }

    TRANSACTION {
        string transaction_id PK "ChromaDB ID"
        uuid user_id FK
        uuid file_id FK
        timestamp date
        float amount
        string currency
        string description
        string merchant
        string category FK
        string payment_method
        boolean is_anomaly
        float confidence_score
    }

    CATEGORY {
        string category_id PK
        string category_name
        string parent_category
        string[] keywords
        string icon
    }

    ANOMALY {
        string anomaly_id PK
        uuid user_id FK
        string transaction_id FK
        string anomaly_type
        string severity
        string reason
        boolean resolved
    }

    SPENDING_PATTERN {
        string pattern_id PK
        uuid user_id FK
        string pattern_type
        string frequency
        float avg_amount
        string category
    }

    INSIGHT {
        string insight_id PK
        uuid user_id FK
        string insight_type
        string priority
        string title
        text description
        boolean acted_upon
    }

    AUDIT_LOG {
        uuid log_id PK
        uuid user_id FK
        string action
        string resource_type
        string resource_id
        jsonb details
        timestamp created_at
    }
```

## Storage Strategy

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Structured Data** | PostgreSQL / SQLite | Users, Files, Sessions, Audit Logs |
| **Vector Data** | ChromaDB | Transactions, Categories, Patterns, Insights |
| **Unstructured Data** | S3 / Local Storage | Original PDF/Image uploads |

## Key Relationships

1.  **User Ownership**: Almost all entities are linked to a `user_id` for multi-tenancy.
2.  **Document Traceability**: Transactions are linked back to the `file_id` they were extracted from.
3.  **AI Insights**: Anomalies and Patterns are derived from Transactions and can trigger Insights for the user.
