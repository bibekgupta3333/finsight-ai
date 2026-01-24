# System Architecture Quick Reference

**Last Updated:** January 24, 2026  
**Version:** 2.1

---

## Architecture Evolution Timeline

```
v1.0 (Q1 2024)          v1.5 (Q3 2024)          v2.0 (Q1 2025)          v2.1 (Q1 2026)          v3.0 (Q4 2026 - Planned)
Single-Agent RAG    →   Multi-Agent Patterns →   Production Ready   →   Advanced Reasoning  →   Federated Learning
                        LangGraph                Safety Certified        Tool Recovery           Edge Deployment
                                                 K8s + Monitoring        HITL Control            Multi-Modal
```

---

## Core Architecture Layers (6-Layer Design)

```
┌─────────────────────────────────────────────────────────────────────┐
│ Layer 1: PRESENTATION (Next.js 14)                                  │
│   • Transaction submission UI                                       │
│   • Reasoning trace visualizer                                      │
│   • Analyst HITL dashboard                                          │
│   • Audit log explorer                                              │
└─────────────────────────────────────────────────────────────────────┘
                              ↕ HTTPS + WebSocket
┌─────────────────────────────────────────────────────────────────────┐
│ Layer 2: API GATEWAY (FastAPI)                                      │
│   • RESTful routes: /api/analyze, /api/agents/{pattern}            │
│   • Middleware: JWT auth, rate limit, CORS, validation             │
│   • Correlation IDs for distributed tracing                         │
└─────────────────────────────────────────────────────────────────────┘
                              ↕
┌─────────────────────────────────────────────────────────────────────┐
│ Layer 3: ORCHESTRATION (LangGraph + Reasoning + Memory)             │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐ │
│   │ Multi-Agent  │  │  Reasoning   │  │   Memory Management      │ │
│   │ Coordination │  │   Engine     │  │   (5-tier hierarchy)     │ │
│   │              │  │              │  │                          │ │
│   │• Single      │  │• Hypothesis  │  │• Short-term (session)    │ │
│   │• Manager-    │  │• Counter-    │  │• Working (Redis 1h TTL)  │ │
│   │  Worker      │  │  factual     │  │• Episodic (ChromaDB)     │ │
│   │• Planner-    │  │• Constraint  │  │• Semantic (ChromaDB)     │ │
│   │  Executor-   │  │• Uncertainty │  │• Procedural (schemas)    │ │
│   │  Critic      │  │              │  │                          │ │
│   │• Debate      │  │              │  │                          │ │
│   │• Role-Spec   │  │              │  │                          │ │
│   │• Swarm       │  │              │  │                          │ │
│   └──────────────┘  └──────────────┘  └──────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
                              ↕
┌─────────────────────────────────────────────────────────────────────┐
│ Layer 4: LLM INFERENCE (Ollama)                                     │
│   • Mistral-7B-Instruct-v0.2 (Q4_K_M, 4.1GB)                       │
│   • Llama-2-7B-Chat (Q4_K_M, 3.8GB)                                │
│   • OpenAI-compatible API, streaming support                        │
└─────────────────────────────────────────────────────────────────────┘
                              ↕
┌─────────────────────────────────────────────────────────────────────┐
│ Layer 5: DATA PERSISTENCE                                           │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐ │
│   │  ChromaDB    │  │    Redis     │  │     PostgreSQL           │ │
│   │  (Vector DB) │  │   (Cache)    │  │   (Analytics DB)         │ │
│   │              │  │              │  │                          │ │
│   │• Episodic    │  │• Conversation│  │• Audit logs              │ │
│   │  memory      │  │  history     │  │• Performance metrics     │ │
│   │• Semantic    │  │• Tool cache  │  │• Analyst feedback        │ │
│   │  memory      │  │• LRU eviction│  │• Decision history        │ │
│   │• 384-dim     │  │• 1h TTL      │  │• Escalation tickets      │ │
│   │  embeddings  │  │              │  │                          │ │
│   └──────────────┘  └──────────────┘  └──────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
                              ↕
┌─────────────────────────────────────────────────────────────────────┐
│ Layer 6: TOOL INFRASTRUCTURE                                        │
│   ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐ │
│   │calculate_risk    │  │query_fraud       │  │fetch_account     │ │
│   │_score            │  │_policy (RAG)     │  │_history          │ │
│   └──────────────────┘  └──────────────────┘  └──────────────────┘ │
│   ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐ │
│   │detect_anomalies  │  │get_balance       │  │check_velocity    │ │
│   │                  │  │_change           │  │_limits           │ │
│   └──────────────────┘  └──────────────────┘  └──────────────────┘ │
│   • Circuit breakers • Retry logic • Timeout mgmt • Health checks   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Multi-Agent Patterns Performance Matrix

| Pattern | F1-Score | Latency (p95) | Cost/1k | Best For |
|---------|----------|---------------|---------|----------|
| **Single-Agent** | 87.3% | 1.82s | $0.42 | Baseline, simple cases |
| **Manager-Worker** | 87.9% | 2.45s | $0.58 | Parallel subtask delegation |
| **Planner-Executor-Critic** | **88.9%** ⭐ | 2.78s | **$0.68** | **Production default** |
| **Debate** | **91.2%** 🏆 | 5.89s | $1.24 | Ambiguous, high-stakes |
| **Role-Specialized** | 88.4% | 3.12s | $0.79 | Domain expertise required |
| **Swarm** | 89.6% | 4.21s | $1.05 | Robustness via voting |

**Legend:**
- 🏆 Highest Accuracy
- ⭐ Best Accuracy-Cost Tradeoff (Production Default)

---

## Prompting Techniques Comparison

| Technique | F1-Score | Latency | Faithfulness | Hallucination Rate | Use Case |
|-----------|----------|---------|--------------|-------------------|----------|
| **Chain-of-Thought (CoT)** | 84.6% | 1.45s | 3.8/5.0 | 34% | Fast, simple reasoning |
| **ReAct** | **87.3%** | 1.82s | **4.6/5.0** | **12%** | **Production default** |
| **Tree-of-Thought (ToT)** | **89.1%** | 4.12s | 4.4/5.0 | 18% | Complex cases |
| **Self-Critique** | 86.5% | 2.34s | 4.2/5.0 | 22% | Quality refinement |

**Key Insight:** ReAct provides best balance of accuracy, speed, and faithfulness (tool grounding prevents hallucination).

---

## Memory Hierarchy

```
┌─────────────────────────────────────────────────────────────────────┐
│ Tier 1: Short-Term Memory (Current Session)                         │
│   Storage: Python dict in-memory | Retention: Session lifetime      │
│   Content: Current transaction, immediate context                   │
└─────────────────────────────────────────────────────────────────────┘
                              ↓ (Context overflow)
┌─────────────────────────────────────────────────────────────────────┐
│ Tier 2: Working Memory (Redis)                                      │
│   Storage: Redis LRU | Retention: 1h TTL | Content: Tool results    │
└─────────────────────────────────────────────────────────────────────┘
                              ↓ (Need past cases)
┌─────────────────────────────────────────────────────────────────────┐
│ Tier 3: Episodic Memory (ChromaDB)                                  │
│   Storage: Vector DB | Retention: Permanent | Content: Fraud cases  │
│   Retrieval: Semantic similarity (top-k=5)                          │
└─────────────────────────────────────────────────────────────────────┘
                              ↓ (Need policy knowledge)
┌─────────────────────────────────────────────────────────────────────┐
│ Tier 4: Semantic Memory (ChromaDB)                                  │
│   Storage: Vector DB | Retention: Permanent | Content: Policies/rules│
│   Retrieval: RAG (query expansion + reranking)                      │
└─────────────────────────────────────────────────────────────────────┘
                              ↓ (Need tool knowledge)
┌─────────────────────────────────────────────────────────────────────┐
│ Tier 5: Procedural Memory (Tool Registry)                           │
│   Storage: Pydantic schemas | Retention: Code-defined               │
│   Content: Tool signatures, examples, constraints                   │
└─────────────────────────────────────────────────────────────────────┘
```

**Ablation Study Results:**
- Procedural (tools): **-10.4% F1** (most critical - prevents hallucination)
- Semantic (policies): **-7.0% F1** (second most important - grounding)
- Working (cache): -3.1% F1
- Episodic (cases): -2.5% F1
- Short-term: -1.2% F1

---

## Transaction Analysis Workflow

```
1. Frontend submits transaction
         ↓
2. API Gateway validates (Pydantic), assigns correlation ID
         ↓
3. LangGraph loads pattern (e.g., Planner-Executor-Critic)
         ↓
4. Memory retrieval (5-tier hierarchy)
         ↓
5. Agent reasoning loop:
         ┌─────────────────────────────────┐
         │ WHILE not done:                 │
         │   Generate thought (Ollama)     │
         │   Execute action (tool call)    │
         │   Observe result                │
         │   Update working memory (Redis) │
         │   Check termination condition   │
         └─────────────────────────────────┘
         ↓
6. RAG retrieval from ChromaDB (policies)
         ↓
7. Decision synthesis + explanation
         ↓
8. Escalation check (HITL if confidence < 70%)
         ↓
9. Store in PostgreSQL (audit log)
         ↓
10. Stream response via WebSocket
         ↓
11. Frontend displays reasoning trace
```

---

## Deployment Environments

### Development (Docker Compose)

```
Services: backend, frontend, ollama, chromadb, redis
Network: shared Docker network
Volumes: code hot-reload, data persistence
Resources: backend (2 CPUs, 4GB), ollama (4 CPUs, 8GB)

Start: docker-compose up -d
Endpoints:
  - Backend API: http://localhost:8000/docs (Swagger)
  - Frontend: http://localhost:3000
  - Ollama: http://localhost:11434
  - ChromaDB: http://localhost:8001
```

### Production (Kubernetes)

```
Namespace: finsight-prod
Deployments:
  - backend: HPA (2-10 replicas, CPU 70%)
  - frontend: HPA (2-5 replicas)
  - ollama: 2 replicas (GPU-enabled)
  - chromadb: StatefulSet (persistent volume)
  - redis: Deployment (persistent volume)
  - postgres: StatefulSet (persistent volume)

Ingress: TLS (Let's Encrypt), HTTPS redirect
Monitoring: Prometheus + Grafana
Logging: Loki
Availability: 99.7% (SLA)
```

---

## Safety & Security Summary

### Security
- **Authentication:** JWT (24h expiry) + API keys (service-to-service)
- **Encryption:** TLS 1.3 (transit), TDE (rest)
- **Network:** CORS, rate limiting, network policies (K8s)
- **Secrets:** Kubernetes Secrets (future: Vault)

### Safety
- **Prompt Injection Defense:** 94% prevention rate
- **Hallucination Detection:** 12% rate (ReAct) vs 34% (CoT)
- **Bias Mitigation:** Demographic parity monitoring (<10% disparity)
- **HITL Escalation:** Confidence < 70%, high-value, multi-agent disagreement

---

## 2026 Roadmap Highlights

| Quarter | Feature | Impact |
|---------|---------|--------|
| **Q2 2026** | Federated Learning | Multi-bank collaboration |
| **Q2 2026** | Edge Deployment | On-device fraud detection (225MB mobile model) |
| **Q3 2026** | SHAP Explanations | 40% faster analyst review |
| **Q3 2026** | Active Learning | +2-3% F1/month with 100 labels/week |
| **Q4 2026** | Multi-Modal | Check/ID fraud detection (+15-20% reduction) |
| **Q4 2026** | Service Mesh (Istio) | 99.9% availability |

---

## Key Metrics Dashboard

### Performance
- **Latency:** p50=1.42s, p95=3.12s, p99=6.78s
- **Throughput:** 1,150 txn/min (10-pod cluster)
- **Availability:** 99.7%

### Accuracy
- **F1-Score:** 87.3% (single-agent) | 91.2% (debate)
- **Recall:** 88.4% (+9.3% vs XGBoost)
- **Precision:** 86.1% (0.1% FPR)

### Cost
- **Single-Agent:** $0.42/1k txn
- **Planner-Executor-Critic:** $0.68/1k txn (production default)
- **Debate:** $1.24/1k txn (premium)

### Reasoning Quality
- **Faithfulness:** 4.6/5.0 (ReAct)
- **Completeness:** 4.3/5.0
- **Consistency:** 4.5/5.0
- **Inter-annotator agreement:** κ=0.81

---

## Quick Links

- **Full Architecture:** [ARCHITECTURE-2026.md](./ARCHITECTURE-2026.md)
- **System Design:** [system-design.md](./system-design.md)
- **Database Design:** [database-design-fraud.md](./database-design-fraud.md)
- **API Documentation:** http://localhost:8000/docs (when running)
- **GitHub Repository:** https://github.com/bibekgupta3333/finsight-ai

---

**Version:** 2.1 | **Last Updated:** January 24, 2026 | **License:** MIT
