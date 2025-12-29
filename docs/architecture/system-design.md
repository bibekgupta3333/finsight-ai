# System Design & Architecture - FinSight AI

## Table of Contents
1. [Executive Summary](#executive-summary)
2. [System Overview](#system-overview)
3. [Architecture Diagram](#architecture-diagram)
4. [Component Design](#component-design)
5. [Data Flow](#data-flow)
6. [Technology Stack](#technology-stack)
7. [Scalability & Performance](#scalability--performance)
8. [Security Architecture](#security-architecture)

---

## Executive Summary

FinSight AI is a multimodal personal finance reasoning agent that analyzes bank statements, transaction screenshots, and voice inputs to provide intelligent financial insights. The system uses RAG (Retrieval-Augmented Generation) with local vector stores, LangGraph for agent orchestration, and Ollama for local LLM inference.

**Key Features:**
- Multimodal input processing (PDF, images, voice)
- Intelligent transaction categorization
- Anomaly detection
- Natural language financial explanations
- Privacy-first design with local processing

---

## System Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE                          │
│                    (Next.js Frontend)                           │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │  Upload  │  │Dashboard │  │Insights  │  │Settings  │       │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘       │
└────────────────────────┬────────────────────────────────────────┘
                         │ HTTPS/WebSocket
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                      API GATEWAY LAYER                          │
│                    (FastAPI Backend)                            │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Route Handlers │ Auth Middleware │ Rate Limiter         │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────┬─────────────────┬───────────────────┬──────────────────┘
         │                 │                   │
         ▼                 ▼                   ▼
┌─────────────────┐ ┌─────────────┐ ┌──────────────────────┐
│   DOCUMENT      │ │   VECTOR    │ │   LANGGRAPH AGENT    │
│   PROCESSING    │ │   STORE     │ │   ORCHESTRATION      │
│   MODULE        │ │  (ChromaDB) │ │                      │
│                 │ │             │ │  ┌────────────────┐  │
│ ┌──────────┐    │ │ ┌─────────┐ │ │  │ Categorizer   │  │
│ │   OCR    │    │ │ │Embedding│ │ │  │    Node       │  │
│ │ Engine   │    │ │ │  Model  │ │ │  └────────────────┘  │
│ └──────────┘    │ │ └─────────┘ │ │  ┌────────────────┐  │
│ ┌──────────┐    │ │             │ │  │   Anomaly     │  │
│ │   PDF    │    │ │ ┌─────────┐ │ │  │  Detection    │  │
│ │  Parser  │    │ │ │ Vector  │ │ │  └────────────────┘  │
│ └──────────┘    │ │ │   DB    │ │ │  ┌────────────────┐  │
│ ┌──────────┐    │ │ └─────────┘ │ │  │   Analysis    │  │
│ │  Image   │    │ │             │ │  │     Node      │  │
│ │Processor │    │ │             │ │  └────────────────┘  │
│ └──────────┘    │ │             │ │  ┌────────────────┐  │
└─────────────────┘ └─────────────┘ │  │  Explanation  │  │
                                    │  │     Node      │  │
         ▲                          │  └────────────────┘  │
         │                          └──────────┬───────────┘
         │                                     │
         └─────────────────────────────────────┘
                         │
                         ▼
         ┌───────────────────────────────┐
         │     OLLAMA LLM SERVICE        │
         │   (Local Model Inference)     │
         │                               │
         │  ┌─────────────────────────┐  │
         │  │  Llama 2 / Mistral      │  │
         │  │  (7B/13B parameters)    │  │
         │  └─────────────────────────┘  │
         └───────────────────────────────┘
```

---

## Architecture Diagram

### Component Interaction Flow

```
┌───────────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER                               │
├───────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │              Next.js Application                         │    │
│  │  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐        │    │
│  │  │ Pages  │  │Components│ │ State │  │  API   │        │    │
│  │  │        │  │          │ │ Mgmt  │  │ Client │        │    │
│  │  └────────┘  └────────┘  └────────┘  └────────┘        │    │
│  └──────────────────────────────────────────────────────────┘    │
│                              │                                    │
│                              │ HTTP/WS                            │
│                              ▼                                    │
└───────────────────────────────────────────────────────────────────┘
                               │
┌───────────────────────────────┼───────────────────────────────────┐
│                        API LAYER                                  │
├───────────────────────────────────────────────────────────────────┤
│                               │                                   │
│  ┌────────────────────────────▼─────────────────────────────┐    │
│  │              FastAPI Application                         │    │
│  │                                                           │    │
│  │  ┌──────────────────────────────────────────────────┐    │    │
│  │  │           Routers & Controllers                  │    │    │
│  │  ├──────────────────────────────────────────────────┤    │    │
│  │  │  /upload  │ /analyze │ /insights │ /anomalies   │    │    │
│  │  └──────────────────────────────────────────────────┘    │    │
│  │                           │                               │    │
│  │  ┌──────────────────────────────────────────────────┐    │    │
│  │  │              Middleware Layer                    │    │    │
│  │  ├──────────────────────────────────────────────────┤    │    │
│  │  │  CORS │ Auth │ Logging │ Rate Limit │ Validation│    │    │
│  │  └──────────────────────────────────────────────────┘    │    │
│  └───────────────────────────────────────────────────────────┘    │
│                              │                                    │
│                              ▼                                    │
└───────────────────────────────────────────────────────────────────┘
                               │
┌───────────────────────────────┼───────────────────────────────────┐
│                     PROCESSING LAYER                              │
├───────────────────────────────────────────────────────────────────┤
│                               │                                   │
│  ┌────────────────────────────┴─────────────────────────────┐    │
│  │           Document Processing Pipeline                   │    │
│  │                                                           │    │
│  │  ┌──────────┐      ┌──────────┐      ┌──────────┐       │    │
│  │  │   PDF    │──────▶│  OCR     │──────▶│ Extract  │       │    │
│  │  │  Parser  │      │  Engine  │      │   Data   │       │    │
│  │  └──────────┘      └──────────┘      └──────────┘       │    │
│  │       │                  │                  │            │    │
│  │       └──────────────────┼──────────────────┘            │    │
│  │                          ▼                               │    │
│  │                  ┌──────────────┐                        │    │
│  │                  │ Normalize &  │                        │    │
│  │                  │  Structure   │                        │    │
│  │                  └──────────────┘                        │    │
│  └───────────────────────┬───────────────────────────────────┘    │
│                          │                                       │
│                          ▼                                       │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │            LangGraph Agent Orchestration                 │    │
│  │                                                           │    │
│  │     START                                                │    │
│  │       │                                                  │    │
│  │       ▼                                                  │    │
│  │  ┌──────────┐         ┌──────────────┐                  │    │
│  │  │  Parse   │────────▶│ Categorize   │                  │    │
│  │  │  Input   │         │ Transactions │                  │    │
│  │  └──────────┘         └──────┬───────┘                  │    │
│  │                              │                           │    │
│  │                              ▼                           │    │
│  │                       ┌──────────────┐                   │    │
│  │                       │   Detect     │                   │    │
│  │                       │  Anomalies   │                   │    │
│  │                       └──────┬───────┘                   │    │
│  │                              │                           │    │
│  │                              ▼                           │    │
│  │                       ┌──────────────┐                   │    │
│  │                       │   Analyze    │◀────RAG Query     │    │
│  │                       │   Spending   │                   │    │
│  │                       └──────┬───────┘                   │    │
│  │                              │                           │    │
│  │                              ▼                           │    │
│  │                       ┌──────────────┐                   │    │
│  │                       │   Generate   │◀────LLM           │    │
│  │                       │ Explanations │                   │    │
│  │                       └──────┬───────┘                   │    │
│  │                              │                           │    │
│  │                              ▼                           │    │
│  │                            END                           │    │
│  └──────────────────────────────────────────────────────────┘    │
│                                                                  │
└───────────────────────────────────────────────────────────────────┘
                               │
┌───────────────────────────────┼───────────────────────────────────┐
│                        DATA LAYER                                 │
├───────────────────────────────────────────────────────────────────┤
│                               │                                   │
│  ┌────────────────────────────┴─────────────────────────────┐    │
│  │              Vector Store (ChromaDB)                     │    │
│  │                                                           │    │
│  │  ┌──────────────────────────────────────────────────┐    │    │
│  │  │         Embedding Model                          │    │    │
│  │  │      (all-MiniLM-L6-v2)                          │    │    │
│  │  └──────────────────┬───────────────────────────────┘    │    │
│  │                     │                                    │    │
│  │                     ▼                                    │    │
│  │  ┌──────────────────────────────────────────────────┐    │    │
│  │  │         Collections                              │    │    │
│  │  ├──────────────────────────────────────────────────┤    │    │
│  │  │  • transactions                                  │    │    │
│  │  │  • categories                                    │    │    │
│  │  │  • patterns                                      │    │    │
│  │  │  • user_history                                  │    │    │
│  │  └──────────────────────────────────────────────────┘    │    │
│  └───────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │              Ollama Service                              │    │
│  │                                                           │    │
│  │  ┌──────────────────────────────────────────────────┐    │    │
│  │  │  Local LLM (Llama 2 7B / Mistral 7B)            │    │    │
│  │  ├──────────────────────────────────────────────────┤    │    │
│  │  │  • Inference Engine                              │    │    │
│  │  │  • Model Cache                                   │    │    │
│  │  │  • Response Streaming                            │    │    │
│  │  └──────────────────────────────────────────────────┘    │    │
│  └───────────────────────────────────────────────────────────┘    │
│                                                                  │
└───────────────────────────────────────────────────────────────────┘
```

---

## Component Design

### 1. Frontend (Next.js)

**Technology:** Next.js 14, TypeScript, Tailwind CSS, shadcn/ui

**Key Components:**

#### Pages
- **Landing Page:** Hero section, features, CTA
- **Upload Page:** File upload interface with drag-and-drop
- **Dashboard:** Overview of financial health
- **Insights Page:** Detailed analytics and visualizations
- **Settings:** User preferences

#### Components
```
components/
├── ui/
│   ├── Button.tsx
│   ├── Card.tsx
│   ├── Chart.tsx
│   └── Input.tsx
├── features/
│   ├── FileUpload/
│   │   ├── DropZone.tsx
│   │   ├── FilePreview.tsx
│   │   └── UploadProgress.tsx
│   ├── Dashboard/
│   │   ├── SpendingChart.tsx
│   │   ├── CategoryBreakdown.tsx
│   │   └── RecentTransactions.tsx
│   ├── Insights/
│   │   ├── AnomalyCard.tsx
│   │   ├── TrendAnalysis.tsx
│   │   └── AIExplanation.tsx
│   └── Chat/
│       ├── ChatInterface.tsx
│       └── MessageBubble.tsx
└── layout/
    ├── Header.tsx
    ├── Sidebar.tsx
    └── Footer.tsx
```

#### State Management
- **Zustand Store:**
  - `useFileStore`: Upload state
  - `useAnalysisStore`: Analysis results
  - `useUserStore`: User preferences
  - `useUIStore`: UI state (loading, errors)

---

### 2. Backend (FastAPI)

**Technology:** FastAPI, Python 3.11+, Pydantic, LangChain

**Project Structure:**
```
backend/
├── app/
│   ├── api/
│   │   ├── routes/
│   │   │   ├── upload.py
│   │   │   ├── analyze.py
│   │   │   ├── insights.py
│   │   │   └── health.py
│   │   └── dependencies.py
│   ├── core/
│   │   ├── config.py
│   │   ├── security.py
│   │   └── logging.py
│   ├── services/
│   │   ├── document_processor.py
│   │   ├── ocr_service.py
│   │   ├── vector_store.py
│   │   ├── agent_service.py
│   │   └── llm_service.py
│   ├── models/
│   │   ├── transaction.py
│   │   ├── analysis.py
│   │   └── insights.py
│   ├── agents/
│   │   ├── categorizer.py
│   │   ├── anomaly_detector.py
│   │   ├── analyzer.py
│   │   └── explainer.py
│   └── utils/
│       ├── file_utils.py
│       └── validators.py
├── tests/
└── main.py
```

**Key Services:**

#### Document Processor
```python
class DocumentProcessor:
    - parse_pdf()
    - extract_images()
    - preprocess_image()
    - extract_transactions()
```

#### OCR Service
```python
class OCRService:
    - recognize_text()
    - extract_table_data()
    - validate_output()
```

#### Vector Store Service
```python
class VectorStoreService:
    - initialize_collection()
    - embed_documents()
    - similarity_search()
    - add_documents()
```

#### Agent Service (LangGraph)
```python
class AgentService:
    - create_graph()
    - execute_workflow()
    - get_state()
```

---

### 3. LangGraph Agent

**Agent Workflow:**

```python
from langgraph.graph import StateGraph

# Define agent state
class AgentState(TypedDict):
    transactions: List[Transaction]
    categories: Dict[str, List[Transaction]]
    anomalies: List[Anomaly]
    insights: List[Insight]
    explanation: str

# Create workflow
workflow = StateGraph(AgentState)

# Add nodes
workflow.add_node("categorize", categorize_transactions)
workflow.add_node("detect_anomalies", detect_anomalies)
workflow.add_node("analyze_spending", analyze_spending)
workflow.add_node("generate_explanation", generate_explanation)

# Add edges
workflow.add_edge("categorize", "detect_anomalies")
workflow.add_edge("detect_anomalies", "analyze_spending")
workflow.add_edge("analyze_spending", "generate_explanation")
```

**Nodes:**

1. **Categorizer Node:** Uses embedding similarity and rules
2. **Anomaly Detection Node:** Statistical analysis + ML
3. **Analysis Node:** Trend analysis with RAG context
4. **Explanation Node:** LLM-powered natural language generation

---

### 4. Vector Store (ChromaDB)

**Collections:**

```python
collections = {
    "transactions": {
        "metadata": ["date", "amount", "category", "user_id"],
        "documents": "Transaction descriptions"
    },
    "categories": {
        "metadata": ["category_name", "keywords"],
        "documents": "Category examples and patterns"
    },
    "patterns": {
        "metadata": ["pattern_type", "frequency"],
        "documents": "Spending patterns and insights"
    }
}
```

**Embedding Model:** `sentence-transformers/all-MiniLM-L6-v2`
- Dimensions: 384
- Speed: Fast
- Quality: Good for semantic search
- Free & Open Source

---

### 5. LLM Service (Ollama)

**Configuration:**
```yaml
model: llama2:7b  # or mistral:7b
temperature: 0.7
max_tokens: 1024
context_window: 4096
streaming: true
```

**Prompt Templates:**

```python
EXPLANATION_PROMPT = """
You are a financial advisor AI. Analyze the following transaction data and provide insights:

Transactions: {transactions}
Categories: {categories}
Anomalies: {anomalies}
Historical Patterns: {context}

Provide a clear, concise explanation of:
1. Spending patterns
2. Notable anomalies
3. Recommendations

Response:
"""
```

---

## Data Flow

### Upload & Analysis Flow

```
1. User uploads PDF/Image
        │
        ▼
2. Frontend validates file (size, type)
        │
        ▼
3. POST /api/upload (multipart/form-data)
        │
        ▼
4. Backend saves file temporarily
        │
        ▼
5. Document Processor extracts data
        │
        ├──▶ PDF: PyPDF2/pdfplumber
        └──▶ Image: EasyOCR/Tesseract
        │
        ▼
6. Transaction extraction & normalization
        │
        ▼
7. Store in Vector DB (embeddings)
        │
        ▼
8. LangGraph Agent Execution:
        │
        ├──▶ Categorize transactions
        ├──▶ Detect anomalies
        ├──▶ Analyze patterns (RAG query)
        └──▶ Generate explanation (Ollama)
        │
        ▼
9. Return structured JSON response
        │
        ▼
10. Frontend displays insights
```

### Real-time Streaming Flow

```
1. User requests detailed explanation
        │
        ▼
2. WebSocket connection established
        │
        ▼
3. Agent starts workflow
        │
        ▼
4. Ollama streams response tokens
        │
        ▼
5. Backend forwards stream to client
        │
        ▼
6. Frontend renders tokens progressively
```

---

## Technology Stack

### Frontend
| Component | Technology | Purpose |
|-----------|------------|---------|
| Framework | Next.js 14 | React framework with SSR |
| Language | TypeScript | Type safety |
| Styling | Tailwind CSS | Utility-first CSS |
| UI Components | shadcn/ui | Pre-built accessible components |
| State Management | Zustand | Lightweight state management |
| Charts | Recharts | Data visualization |
| HTTP Client | Axios | API communication |

### Backend
| Component | Technology | Purpose |
|-----------|------------|---------|
| Framework | FastAPI | High-performance async API |
| Language | Python 3.11+ | Main backend language |
| Agent Framework | LangGraph | Agent orchestration |
| LLM Integration | LangChain | LLM workflow |
| Vector Store | ChromaDB | Embedding storage |
| Embedding | all-MiniLM-L6-v2 | Text embeddings |
| OCR | EasyOCR/Tesseract | Text extraction |
| PDF Parser | pdfplumber | PDF processing |
| Validation | Pydantic | Data validation |

### AI/ML
| Component | Technology | Purpose |
|-----------|------------|---------|
| LLM | Ollama (Llama2/Mistral) | Local inference |
| Embeddings | SentenceTransformers | Semantic search |
| OCR | EasyOCR | Image text extraction |
| Image Processing | OpenCV/Pillow | Image preprocessing |

### Infrastructure
| Component | Technology | Purpose |
|-----------|------------|---------|
| Containerization | Docker | Container runtime |
| Orchestration | Kubernetes | Container orchestration |
| IaC | Terraform | Infrastructure as Code |
| Package Manager | Helm | Kubernetes packages |
| Cloud Provider | AWS | Cloud hosting |
| Deployment | Render (free tier) | Initial deployment |

---

## Scalability & Performance

### Performance Optimization

1. **Frontend:**
   - Next.js SSR/SSG for fast initial load
   - Image optimization
   - Code splitting
   - Progressive Web App (PWA)
   - Client-side caching

2. **Backend:**
   - Async/await everywhere
   - Connection pooling
   - Request/response caching (Redis optional)
   - Background job processing (Celery optional)
   - Database query optimization

3. **AI/ML:**
   - Model quantization (4-bit/8-bit)
   - Response caching
   - Batch processing
   - Streaming responses
   - GPU acceleration (when available)

### Scalability Strategy

```
┌─────────────────────────────────────────────┐
│           Load Balancer (AWS ALB)           │
└──────────────┬──────────────────────────────┘
               │
    ┌──────────┴──────────┐
    │                     │
    ▼                     ▼
┌─────────┐         ┌─────────┐
│Frontend │         │Frontend │
│ Pod 1   │         │ Pod 2   │
└─────────┘         └─────────┘
    │                     │
    └──────────┬──────────┘
               │
    ┌──────────┴──────────┐
    │                     │
    ▼                     ▼
┌─────────┐         ┌─────────┐
│Backend  │         │Backend  │
│ Pod 1   │         │ Pod 2   │
└─────────┘         └─────────┘
    │                     │
    └──────────┬──────────┘
               │
    ┌──────────┴──────────┬──────────┐
    │                     │          │
    ▼                     ▼          ▼
┌─────────┐         ┌─────────┐ ┌─────────┐
│ Vector  │         │ Ollama  │ │  S3     │
│  Store  │         │ Service │ │ Storage │
└─────────┘         └─────────┘ └─────────┘
```

**Horizontal Scaling:**
- Frontend: Stateless, scale infinitely
- Backend: Stateless API, scale based on CPU
- Vector Store: Sharding by user_id
- Ollama: Dedicated GPU pods (costly, use sparingly)

---

## Security Architecture

### Authentication & Authorization
- JWT-based authentication
- API key for service-to-service
- Rate limiting per user/IP
- CORS configuration

### Data Security
- TLS/HTTPS for all communication
- Encrypted file storage (S3 server-side encryption)
- Vector store access control
- Secrets management (AWS Secrets Manager)
- PII data sanitization

### Input Validation
- File type validation
- File size limits (10MB)
- Input sanitization
- SQL injection prevention
- XSS protection

### Privacy
- No persistent storage of raw files (option)
- User data isolation in vector store
- GDPR compliance considerations
- Data retention policies
- Audit logging

---

## Monitoring & Observability

### Metrics
- API latency (p50, p95, p99)
- Request rate
- Error rate
- LLM inference time
- Vector search latency
- Memory/CPU usage

### Logging
- Structured JSON logs
- Log levels (DEBUG, INFO, WARN, ERROR)
- Request/response logging
- Error tracking (Sentry)
- User activity logs

### Alerting
- High error rate
- Slow response times
- Resource exhaustion
- Service downtime

---

## Future Enhancements

1. **Voice Input Processing:** Speech-to-text integration
2. **Real-time Alerts:** Push notifications for anomalies
3. **Multi-user Support:** Team/family accounts
4. **Budget Planning:** AI-powered budget recommendations
5. **Investment Insights:** Portfolio analysis (if applicable)
6. **Mobile App:** React Native application
7. **Improved Models:** Fine-tuned domain-specific models
8. **Multi-language Support:** i18n implementation

---

**Document Version:** 1.0
**Last Updated:** December 26, 2025
**Status:** Initial Design
