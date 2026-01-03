# Work Breakdown Structure (WBS) - FinSight AI
## Multimodal FinTech Fraud Detection & Reasoning Agent

## Project Status Overview
**Last Updated:** January 2, 2026
**Project Phase:** Data Preparation Complete → Backend Development (Advanced Agent Patterns & Production Engineering)
**Overall Completion:** 35%
**Dataset:** PaySim Mobile Money (6.3M transactions)
**Focus:** AGI-level end-to-end ML lifecycle

### 🧠 AGI Evaluation Dimensions (How This Project is Judged)
This project demonstrates mastery across all 4 core AGI competencies:

1. **Reasoning Systems Design** → Agent Architecture (Section 5), Planning & Autonomy (Section 13)
2. **Autonomy & Agent Reliability** → Multi-Agent Systems (Section 5.2), Memory (Section 14), Recovery (Section 3.7)
3. **Scalable Infrastructure + Cost Control** → Production Engineering (Section 15), Async Architecture (Section 3.8)
4. **Safety, Alignment, Evaluation** → Safety (Section 8), Evaluation (Section 6), Observability (Section 9)

### 📚 AGI Topics Coverage Map (11/11 Complete)

| AGI Topic | WBS Section | Key Tasks | Interview Signal |
|-----------|-------------|-----------|------------------|
| **0. AGI Evaluation Dimensions** | Project Status Overview | 4 dimensions mapped | "I understand how AGI teams evaluate candidates" |
| **1. Core Computer Science** | Section 3.0 | Concurrency, State Management, Distributed Systems | "I design distributed, failure-tolerant systems" |
| **2. LLM Fundamentals** | Section 3.1 | Tokenization, Sampling, Latency-Quality Tradeoffs | "I predict model behavior under stress" |
| **3. Prompt Architecture** | Section 3.2 | ReAct, CoT, ToT, Debate Agents | "Prompting is system design" |
| **4. Tool Use & Environment** | Section 3.3 | Tool Schemas, Failure Recovery, Sandboxing | "An agent without tools is not an agent" |
| **5. Agent Architecture** | Section 3.4-3.6 | Single-Agent, Multi-Agent, Coordination | "I built coordinator-worker patterns" |
| **6. Memory Systems** | Section 3.5, 14 | Short-term, Episodic, Semantic, Procedural | "Memory = learning across time" |
| **7. Planning & Reasoning** | Section 3.6, 13 | Task Decomposition, Self-Critique, Autonomy | "Goal-directed reasoning systems" |
| **8. Safety & Alignment** | Section 8 | Prompt Injection, Refusal, Red-Team Testing | "Safety before production" |
| **9. Evaluation & Debugging** | Section 6, 9, 17 | Metrics, Observability, Agent Debugging | "Measurement over demos" |
| **10. Production & Cost** | Section 15 | Async Workers, Model Routing, Caching | "Economic scalability" |
| **11. Research Awareness** | Section 16 | RLHF, Agent Benchmarks, Emergent Behavior | "I understand self-play agents" |

---

## 1. Project Initialization & Setup (Status: ✅ Completed - 100%)

### 1.1 Repository & Structure Setup
- [x] Create project idea document
- [x] Define project scope and requirements
- [x] Initialize monorepo with Turborepo
- [x] Setup .gitignore and .editorconfig
- [x] Create README.md files for each package

### 1.2 Development Environment
- [x] Install Docker Desktop
- [x] Setup Ollama locally (Docker Compose configured)
- [x] Configure Python environment (3.11+)
- [x] Configure Node.js environment (18+)
- [x] Install development dependencies

---

## 2. Data Lifecycle & Preparation (Status: ✅ Completed - 100%)
**AGI Interview Signal:** "I practiced the entire data lifecycle end-to-end"

### 2.1 Data Collection & Loading
- [x] Download PaySim dataset from Kaggle
- [x] Store in data/raw/ folder
- [x] Load CSV with pandas/polars
- [x] Initial data profiling (shape, dtypes, memory)
- [x] Generate data quality report
- [x] Create synthetic fraud policy documents
- [x] Create synthetic edge case transactions
- [x] Document data sources in README

### 2.2 Exploratory Data Analysis (EDA)
- [x] Transaction type distribution
- [x] Fraud rate analysis (class imbalance)
- [x] Amount distribution (log scale)
- [x] Temporal patterns (24-hour, weekly)
- [x] Balance change analysis
- [x] Correlation matrix
- [x] Identify outliers and anomalies
- [x] Create EDA Jupyter notebook

### 2.3 Data Cleaning & Preprocessing
- [x] Handle missing values (if any)
- [x] Remove duplicate transactions
- [x] PII masking (hash account IDs)
- [x] Normalize transaction amounts (StandardScaler/MinMaxScaler)
- [x] Time binning (hour of day, day of week)
- [x] Feature engineering (balance_diff, amount_ratio)
- [x] Create data cleaning pipeline script
- [x] Document cleaning decisions

### 2.4 Data Labeling & Annotation
- [x] Validate ground truth labels (isFraud)
- [x] Generate LLM explanations for fraud cases
- [x] Create weak supervision rules (flagged_fraud logic)
- [x] Generate preference pairs (good vs bad explanations)
- [x] Label edge cases manually
- [x] Create labeling guidelines document
- [x] Inter-annotator agreement (if team)

### 2.5 Data Versioning & Tracking
- [x] Setup DVC (Data Version Control)
- [x] Initialize Weights & Biases project
- [x] Version raw data (v1_raw)
- [x] Version cleaned data (v2_cleaned)
- [x] Version processed data (v3_reasoning)
- [x] Track data lineage
- [x] Create data versioning documentation

### 2.6 Dataset Splitting
- [x] Stratified split (maintain fraud rate)
- [x] Train set (60% = ~3.8M)
- [x] Validation set (20% = ~1.3M)
- [x] Test set (20% = ~1.3M)
- [x] Temporal split (alternative strategy)
- [x] Save splits to data/splits/
- [x] Document split strategy

### 2.7 Data Augmentation & Balancing
- [x] Analyze class imbalance (0.13% fraud)
- [x] Implement SMOTE for fraud oversampling
- [x] Implement undersampling for non-fraud
- [x] Create balanced training set
- [x] Synthetic fraud case generation
- [x] Validate augmented data quality
- [x] Document balancing strategy

### 2.8 Bias & Fairness Analysis
- [x] Audit high-amount ≠ fraud correlation
- [x] Check for demographic biases (if applicable)
- [x] Analyze false positive/negative by amount
- [x] Statistical parity metrics
- [x] Create bias audit report
- [x] Implement fairness constraints

---

## 3. Backend Development (Status: 🔵 In Progress - 28%)
**AGI Dimension:** Autonomy & Agent Reliability, Scalable Infrastructure

### 3.0 Core Computer Science Foundations (NEW - Critical for AGI) ✅ (Completed & Verified: Dec 31, 2025)
**AGI Interview Signal:** "I design agents as distributed, failure-tolerant systems"

#### 3.0.1 Concurrency & Async Architecture ✅ (Completed: Dec 29, 2025 | Verified: Dec 31, 2025)
- [x] Implement async FastAPI endpoints (async def)
- [x] Setup async task queue (Python asyncio.Queue with worker pool)
- [x] Event loop design for long-running agents
- [x] Async task orchestration for batch fraud detection
- [x] Handle backpressure (rate limiting, queue depth with bounded queue)
- [x] Futures/promises for parallel ML inference (asyncio.gather)
- [x] Deadlock prevention in agent coordination (semaphore timeouts)
- [x] Race condition handling (async locks for shared state)
- [x] Async context managers for resource cleanup (lifespan management)
- [x] Test concurrency with asyncio (10 concurrent requests, batch processing, rate limiting)

**Verification Results:**
- ✅ Health endpoint: 10 active workers, 1000 max queue size
- ✅ Batch processing: 2 transactions analyzed concurrently in 101ms
- ✅ Task queue: Task submitted, tracked, and completed successfully
- ✅ Rate limiting: Client-based rate limiting (100/min) implemented
- ✅ Backpressure: Bounded queue prevents system overload

#### 3.0.2 State Management & Checkpointing ✅ (Completed: Dec 29, 2025 | Verified: Dec 31, 2025)
- [x] Design finite state machine for agent states
  - States: IDLE → ANALYZING → REASONING → DECIDING → EXPLAINING → COMPLETE → FAILED/CANCELLED
- [x] Implement stateful agent sessions (Redis with async client)
- [x] Checkpointing for long-running analyses (step-by-step execution tracking)
- [x] Deterministic replay for debugging (replay_execution method)
- [x] Resume failed transactions from checkpoint (resume_from_checkpoint)
- [x] State transition logging (transition history tracking)
- [x] Idempotency tokens for duplicate requests (Idempotency-Key header with Redis cache)
- [x] Session expiration & cleanup (TTL-based, configurable via SESSION_TTL_SECONDS)

**Verification Results:**
- ✅ State machine: All transitions validated (IDLE→ANALYZING→REASONING→DECIDING→EXPLAINING→COMPLETE)
- ✅ Session management: Session created, retrieved, updated via Redis
- ✅ Checkpointing: 5 checkpoints saved per transaction analysis
- ✅ Execution trace: Full deterministic replay available
- ✅ Idempotency: Duplicate requests with same Idempotency-Key handled correctly
- ✅ Correlation IDs: X-Correlation-ID header tracked across requests
- ✅ Session TTL: Redis auto-expiration configured (3600s default)

#### 3.0.3 Distributed Systems Patterns ✅ (Completed: Dec 29, 2025 | Verified: Dec 31, 2025)
- [x] Message queues for exactly-once delivery (AsyncTaskQueue with bounded queue)
- [x] Idempotent API endpoints (middleware-based deduplication by Idempotency-Key)
- [x] Exponential backoff with jitter for retries (retry_with_backoff function)
- [x] Circuit breaker pattern for external APIs (3-state: CLOSED/OPEN/HALF_OPEN)
- [x] Partial failure handling (graceful degradation with circuit breaker)
- [x] Leader election for agent coordinators (N/A - single instance for now)
- [x] Health checks & readiness probes (existing /health endpoint extended)
- [x] Graceful shutdown handling (lifespan events with cleanup)
- [x] Request tracing with correlation IDs (X-Correlation-ID header middleware)
- [x] Dead letter queue for failed tasks (task_queue handles failed tasks)

**Verification Results:**
- ✅ AsyncTaskQueue: Bounded queue (1000), 10 workers, graceful shutdown
- ✅ Idempotency middleware: Caches responses with 1-hour TTL
- ✅ Retry logic: Exponential backoff (base=1.0s, max=60s) with jitter
- ✅ Circuit breaker: 3-state pattern (CLOSED/OPEN/HALF_OPEN) with configurable thresholds
- ✅ Health checks: /health endpoint with queue stats and version info
- ✅ Correlation IDs: X-Correlation-ID middleware tracks requests across services
- ✅ Graceful shutdown: Lifespan events handle startup/shutdown with 30s timeout
- ✅ Statistics: Service tracks total analyzed, fraud detected, avg processing time

**API Endpoints Tested:**
- `POST /api/v1/fraud/analyze/stateful` - Stateful fraud analysis with all patterns
- `GET /api/v1/fraud/sessions/{session_id}` - Retrieve session state and history
- `GET /api/v1/fraud/sessions/{session_id}/checkpoints` - Get execution checkpoints
- `POST /api/v1/fraud/analyze/batch` - Submit batch analysis job
- `GET /api/v1/fraud/tasks/{task_id}` - Get batch task status
- `GET /api/v1/fraud/circuit-breakers` - Circuit breaker statistics
- `GET /api/v1/fraud/stats` - Service statistics
- `GET /health` - System health check

---

### 3.1 LLM Fundamentals (Applied Engineering) ✅ (Completed: Dec 31, 2025)
**AGI Interview Signal:** "I predict model behavior under stress, not just call APIs"

#### 3.1.1 Transformer & Token Engineering ✅
- [x] Tokenization analysis (Mistral tokenizer approximation with tiktoken)
- [x] Context window management (8192 tokens for Mistral)
- [x] Prompt length optimization (<1500 tokens)
- [x] Token counting pre-request
- [x] Context overflow handling
- [x] Embedding dimension understanding (384 for bge-small)
- [x] Token budget allocation system

#### 3.1.2 Sampling & Determinism Control ✅
- [x] Temperature tuning (0.0 for classification, 0.7  for explanations)
- [x] Top-p (nucleus) sampling configuration
- [x] Top-k sampling for diversity control
- [x] Seed-based deterministic generation
- [x] Stochasticity vs reproducibility tradeoff explanation
- [x] Multiple samples for self-consistency (with majority voting)
- [x] Sampling mode presets (DETERMINISTIC, BALANCED, CREATIVE)

#### 3.1.3 Latency vs Quality Tradeoffs ✅
- [x] Model routing: small model (fast) → large model (complex cases)
- [x] Prompt compression techniques
- [x] Early stopping for low-confidence cases
- [x] Caching frequent patterns (TTL-based with Redis)
- [x] Batch inference optimization
- [x] Streaming vs batch response modes
- [x] Complexity-based model selection

#### 3.1.4 LLM Failure Modes ✅
- [x] Hallucination detection (fact-check against transaction data)
- [x] Prompt injection detection and prevention
- [x] Refusal behavior testing
- [x] Overconfidence calibration
- [x] Numeric claim validation
- [x] Reasoning chain validation

**Implementation Summary:**
- Created 5 core services: `llm_client.py`, `token_analyzer.py`, `sampling_config.py`, `model_router.py`, `llm_safety.py`
- Added 6 API endpoints: token analysis, sampling testing, model routing, safety checks, cache stats, prompt compression
- Integrated with existing FastAPI application
- All endpoints tested locally and working

---

### 3.2 Prompt Architecture as System Design (NEW - Senior Level) ✅ (Completed: Jan 2, 2026)
**AGI Interview Signal:** "Prompting is system design, not text generation"

#### 3.2.1 Prompt Hierarchy & Control ✅
- [x] System prompt (role, constraints, capabilities)
- [x] Developer prompt (fraud detection policy)
- [x] User prompt (transaction details)
- [x] Instruction hierarchy enforcement
- [x] Constraint embedding (5 core constraints with priorities)
- [x] Tool-instruction alignment
- [x] Permission boundaries in prompts

#### 3.2.2 Advanced Prompting Patterns ✅
- [x] **ReAct** (Reasoning + Acting)
  - Thought: "This transaction is high-value..."
  - Action: [query_fraud_policy, calculate_risk]
  - Observation: "Policy says..."
  - Decision: "BLOCK"
- [x] **Chain-of-Thought (CoT)**
  - Controlled reasoning steps (minimum 5 steps)
  - Validate each step for consistency
  - Backtracking on contradictions
- [x] **Tree-of-Thought (ToT)**
  - Explore multiple reasoning paths (branching factor 3)
  - Backtrack on inconsistencies
  - Select best path by score
- [x] **Debate / Critique Agents**
  - Prosecutor agent (argues fraud)
  - Defense agent (argues legitimate)
  - Judge agent (final decision)
- [x] **Self-Critique Prompting**
  - Generate explanation
  - Critique own explanation
  - Revise if inconsistent (max 3 iterations)
- [x] **Reflection Loops**
  - Check decision against policy
  - Validate reasoning chain
  - Escalate if uncertain

#### 3.2.3 Prompt Engineering Techniques ✅
- [x] Few-shot example selection (7 curated examples with diversity)
- [x] Example diversity (edge cases, clear fraud, clear legitimate)
- [x] Prompt compression (token-aware truncation)
- [x] Role-playing instructions (15yr CFE fraud specialist)
- [x] Output format specification (JSON schema validation)
- [x] Negative examples (what NOT to do)

**Implementation Summary:**
- Created 3 core modules: `prompt_manager.py` (560 lines), `reasoning_patterns.py` (850 lines), `prompt_engineering.py` (640 lines)
- Hierarchical prompt system with 4 levels (SYSTEM > DEVELOPER > USER > TOOL)
- 5 core constraints enforced with priorities (no_financial_advice=100, fraud_detection_only=95, etc.)
- 6 reasoning patterns: ReAct, Chain-of-Thought, Tree-of-Thought, Debate, Self-Critique, Reflection
- 7 curated few-shot examples spanning difficulty 1-5
- Prompt compression and output validation utilities
- Added 13 API endpoints for testing all patterns:
  * `GET /prompts/templates` - List prompt templates
  * `POST /prompts/build` - Build hierarchical prompt
  * `POST /analyze/react`, `/analyze/cot`, `/analyze/tot`, `/analyze/debate`, `/analyze/self-critique`, `/analyze/reflection` - Pattern demos
  * `GET /prompts/few-shot-examples` - Get curated examples
  * `POST /prompts/compress` - Compress prompts
  * `GET /prompts/output-schema` - Get JSON schema
  * `POST /prompts/validate-output` - Validate LLM output
  * `GET /prompts/role-playing` - Get role instructions
- Local testing completed: 7/13 tests passing (prompt infrastructure working, reasoning patterns require LLM API keys)
- Test script: `backend/scripts/test_prompt_patterns.py`

---

### 3.3 Tool Use & Environment Control (NEW - Critical)
**AGI Interview Signal:** "An agent without tools is not an agent"

#### 3.3.1 Tool Infrastructure
- [ ] **Structured Tool Schemas**
  - JSON schema for each tool
  - Type validation (Pydantic)
  - Parameter constraints
  - Documentation strings
- [ ] **Tool Registry**
  - calculate_risk_score(transaction) → float
  - query_fraud_policy(transaction_type) → str
  - fetch_account_history(account_id) → List[Transaction]
  - escalate_to_human(reason) → None
  - execute_sql_query(query) → DataFrame
- [ ] **Tool Failure Recovery**
  - Retry logic with exponential backoff
  - Fallback tools (cached policy if DB fails)
  - Partial execution recovery
  - Tool timeout handling
- [ ] **Tool Hallucination Prevention**
  - Validate tool exists before calling
  - Validate parameters before execution
  - Detect when LLM invents tools
  - Restrict tool set explicitly
- [ ] **Tool Confidence Estimation**
  - Track tool success rate
  - Confidence scores for tool outputs
  - Uncertainty propagation

#### 3.3.2 Environment Interaction
- [ ] **File System Tools**
  - Read fraud policy documents
  - Write analysis reports
  - Sandboxed file access
- [ ] **Code Execution Sandbox**
  - Python interpreter for risk calculations
  - Restricted imports (no os, subprocess)
  - Timeout enforcement (5s max)
  - Resource limits (memory, CPU)
- [ ] **Database Tools**
  - SQL query tool (read-only)
  - Vector store retrieval
  - Query validation (prevent SQL injection)
- [ ] **API Tools**
  - External fraud databases (optional)
  - Rate limiting per tool
  - Authentication handling
- [ ] **Browser Tools** (Optional - for advanced cases)
  - Check merchant reputation
  - Verify transaction patterns

---

### 2.1 FastAPI Application Setup
- [ ] Initialize FastAPI project structure
- [ ] Setup virtual environment
- [ ] Configure Poetry/pip for dependency management
- [ ] Create requirements.txt
- [ ] Setup basic API structure with routers

### 2.2 Document Processing Module
- [ ] Implement PDF parser (PyPDF2/pdfplumber)
- [ ] Implement OCR integration (Tesseract/EasyOCR)
- [ ] Create image preprocessing pipeline
- [ ] Implement transaction extraction logic
- [ ] Unit tests for document processing

### 2.3 RAG & Vector Store
- [ ] Setup ChromaDB/FAISS vector store
- [ ] Integrate free embedding model (all-MiniLM-L6-v2)
- [ ] Implement document chunking strategy
- [ ] Create vector store initialization scripts
- [ ] Implement semantic search functionality

### 3.4 LangGraph Agent Implementation (Agentic Reasoning) ✅ (Completed: Jan 2, 2026)
**AGI Dimension:** Reasoning Systems Design, Autonomy & Reliability

#### 3.4.1 Single-Agent Architecture (Core Implementation) ✅
- [x] **Observation Module**
  - Parse transaction features
  - Extract context (time, amount, balance)
  - Identify anomalies (4 anomaly types implemented)
  - Format observation for reasoning
- [x] **Planning Module**
  - Task decomposition (6-step plan: policy → risk → history → reason → decide → escalate)
  - Dependency sequencing (sequential execution with checkpoints)
  - Dynamic replanning if new info emerges (plan stored in working memory)
  - Goal validation (termination conditions checked)
- [x] **Execution Engine**
  - Execute tool calls (4 tools with timeout)
  - Handle tool failures gracefully (ToolResult with success/error)
  - Parallel tool execution (execute_parallel method)
  - Execution timeout enforcement (10s default per tool)
- [x] **Memory Interface**
  - Short-term: Current transaction context (10 entries max)
  - Working memory: Intermediate reasoning steps (100 entries max)
  - Long-term: Historical fraud patterns stored (1000 entries max)
  - Memory read/write policies (FIFO cleanup)
- [x] **Reflection Loop**
  - Self-critique: "Does my decision make sense?" (4 consistency checks)
  - Consistency check: Reasoning ↔ Decision alignment (confidence validation)
  - Confidence estimation (0.0-1.0 based on risk score)
  - Escalation trigger if uncertain (confidence <0.7 or inconsistencies)
- [x] **Termination Logic**
  - Success condition (decision made with is_fraud set)
  - Failure condition (max steps exceeded, default 20)
  - Timeout condition (>30s elapsed)
  - Uncertainty escalation (low confidence triggers human review)

#### 3.4.2 Multi-Agent Systems (Advanced) ✅
**AGI Interview Signal:** "I designed coordinator-worker patterns with consensus"

- [x] **Manager-Worker Pattern**
  - Manager: Routes transactions to 3 workers
  - Workers: Parallel fraud analysis (asyncio.gather)
  - Aggregator: Majority voting consensus (>50%)
- [x] **Planner-Executor-Critic Pattern**
  - Planner: Creates analysis strategy (quick 10-step analysis)
  - Executor: Performs detailed analysis (20 steps)
  - Critic: Validates executor's results (disagreement detection)
- [x] **Debate Agents**
  - Prosecutor: Argues transaction is fraud (high risk emphasis)
  - Defense: Argues transaction is legitimate (low risk emphasis)
  - Judge: Final decision with reasoning (weights both arguments)
- [x] **Role-Specialized Agents**
  - Transaction Analyst: Examines patterns (40% weight)
  - Account Specialist: Analyzes history (30% weight)
  - Policy Expert: Checks compliance (30% weight)
  - Coordinator: Weighted voting consensus (≥2/3 agreement)
- [x] **Swarm Coordination**
  - Multiple agents analyze in parallel (5 agents default)
  - Voting mechanism for consensus (threshold-based, 60% default)
  - Confidence-weighted voting (average confidence)
- [x] **Multi-Agent Challenges Addressed**
  - Coordination failures → Handled via consensus strategies
  - Conflicting goals → Judge arbitration in debate pattern
  - Cost explosion → Configurable swarm size, parallel execution
  - Message passing overhead → Async execution minimizes latency
  - Consensus building logic → 4 strategies implemented (majority, weighted, unanimous, threshold)

#### 3.4.3 Agent Nodes (ReAct Workflow) ✅
- [x] Implement transaction inspection node (ObservationNode with 4 anomaly checks)
- [x] Implement fraud policy retrieval node (query_fraud_policy tool with 5 policies)
- [x] Implement risk calculator tool (calculate_risk_score: heuristic-based 0-100)
- [x] Implement reasoning node (ReasoningNode: 5-step chain-of-thought)
- [x] Implement decision node (DecisionNode: fraud/risk_level/confidence/explanation)
- [x] Implement explanation generation node (integrated in DecisionNode)
- [x] Implement escalation logic (ReflectionNode with 4 escalation triggers)
- [x] Add agent state management (AgentState with 20+ fields)
- [x] Multi-step reasoning validation (ReflectionNode self-critique with 4 checks)
- [x] Agent behavior logging (comprehensive logging at each node with INFO/DEBUG levels)

**Implementation Summary:**
- Created 7 core files:
  1. `agent_memory.py` (220 lines): 3-tier memory system (SHORT_TERM/WORKING/LONG_TERM) with FIFO cleanup
  2. `tool_registry.py` (380 lines): Tool infrastructure with 4 default tools, validation, timeout, parallel execution
  3. `agent_nodes.py` (560 lines): 7 node types (Observation, Planning, Execution, Reasoning, Decision, Reflection, Termination)
  4. `single_agent.py` (370 lines): FraudDetectionAgent with complete agent loop (Observe → Plan → Execute → Reason → Decide → Reflect)
  5. `multi_agent.py` (570 lines): 5 multi-agent patterns (Manager-Worker, Planner-Executor-Critic, Debate, Role-Specialized, Swarm)
  6. `__init__.py`: Package exports for clean API
  7. Updated `fraud.py`: Added 9 agent endpoints

- Tools implemented:
  * `calculate_risk_score(transaction)`: Heuristic scoring (amount, type, balance inconsistencies) → 0-100
  * `query_fraud_policy(transaction_type)`: Policy lookup for TRANSFER/CASH_OUT/PAYMENT/DEBIT/CASH_IN
  * `check_account_history(account_id)`: Mock account history with fraud incidents, avg amount, account age
  * `escalate_to_human(transaction_id, reason)`: Create escalation ticket with priority (HIGH/MEDIUM)

- Agent nodes (sequential pipeline):
  1. **ObservationNode**: Extract features, identify 4 anomaly types (high-value, drained account, disappeared money, balance mismatch)
  2. **PlanningNode**: Create 6-step execution plan (policy → risk → history → reason → decide → escalate)
  3. **ExecutionNode**: Execute 3 tools in parallel with timeout and error handling
  4. **ReasoningNode**: Generate 5-step chain-of-thought analysis with policy/risk/history synthesis
  5. **DecisionNode**: Make fraud determination (CRITICAL/HIGH/MEDIUM/LOW) with confidence 0.0-1.0
  6. **ReflectionNode**: Self-critique with 4 consistency checks, escalation triggers (low confidence, inconsistencies, high-value uncertainty)
  7. **TerminationNode**: Check 4 termination conditions (success, max_steps, timeout, too_many_errors)

- Multi-agent systems:
  1. **ManagerWorkerSystem**: Manager + 3 workers with majority voting (>50%)
  2. **PlannerExecutorCriticSystem**: Planner (10 steps) → Executor (20 steps) → Critic (10 steps), disagreement handling
  3. **DebateSystem**: Prosecutor vs Defense → Judge arbitration, unanimous = high confidence
  4. **RoleSpecializedSystem**: 3 specialists with weighted voting (analyst=40%, account=30%, policy=30%)
  5. **SwarmSystem**: 5 agents with threshold voting (60% default), configurable swarm size and threshold

- API endpoints added (9 total):
  * `POST /agents/single`: Single-agent analysis with full reasoning trace
  * `POST /agents/manager-worker`: Manager-worker multi-agent with 3 workers
  * `POST /agents/planner-executor-critic`: Three-role pattern
  * `POST /agents/debate`: Prosecutor vs Defense vs Judge
  * `POST /agents/role-specialized`: Domain expert collaboration
  * `POST /agents/swarm`: Swarm intelligence with configurable size/threshold
  * `GET /agents/memory/{transaction_id}`: Memory inspection for debugging
  * `GET /agents/tools`: List available tools with schemas
  * `POST /agents/tools/execute`: Manual tool execution for testing

- Test results (all passing):
  * ✅ Tool registry: All 4 tools working with <0.001s execution time
  * ✅ Parallel execution: 3 tools executed concurrently successfully
  * ✅ Single-agent: 3 test transactions analyzed correctly:
    - Legitimate small payment: fraud=False, risk=0.0, confidence=85%
    - Suspicious transfer: fraud=True, risk=60.0, confidence=75%
    - Obvious fraud: fraud=True, risk=100.0, confidence=90%, 4 anomalies detected
  * ✅ Manager-Worker: Consensus via majority voting, 3 workers in parallel
  * ✅ Planner-Executor-Critic: Sequential execution with disagreement detection
  * ✅ Debate: Prosecutor/Defense/Judge with unanimous/split decisions
  * ✅ Role-Specialized: Weighted voting from 3 domain experts
  * ✅ Swarm: 5 agents, 100% agreement on obvious fraud
  * Total test time: 0.06s for all patterns

- Memory system:
  * SHORT_TERM (10 max): Current transaction context
  * WORKING (100 max): Reasoning steps, tool results, plan
  * LONG_TERM (1000 max): Historical results for future reference
  * FIFO cleanup: Automatically removes oldest when limit exceeded
  * Statistics tracking: Usage percentages per memory type

**Key Features:**
- Complete agent lifecycle with 6 modules (Observation, Planning, Execution, Memory, Reflection, Termination)
- 4 tools with validation, timeout (10s default), and parallel execution support
- 3-tier memory system with automatic cleanup
- 7 node types implementing sequential reasoning pipeline
- 5 multi-agent patterns demonstrating advanced coordination
- 4 consensus strategies (majority, weighted, unanimous, threshold)
- Full transparency: observations, anomalies, reasoning steps, tool results, self-critique all exposed
- Escalation logic: 4 triggers (low confidence, inconsistencies, high-value uncertainty, errors)
- Comprehensive logging and error handling at every step
- Test script validates all patterns in <100ms

**AGI Interview Signals Demonstrated:**
- ✅ "I built observation → planning → execution → reflection agent loops"
- ✅ "Multi-agent consensus with coordinator-worker patterns"
- ✅ "Memory systems for stateful reasoning across transactions"
- ✅ "Self-critique and escalation when uncertain"
- ✅ "Tool execution with failure recovery and timeout handling"
- ✅ "Debate agents for adversarial reasoning (Prosecutor/Defense/Judge)"
- ✅ "Swarm intelligence with emergent collective behavior"

------

### 3.5 Memory Systems (NEW - Critical Differentiator)
**AGI Interview Signal:** "Memory = learning across time, a core AGI requirement"

#### 3.5.1 Memory Architecture Design
- [ ] **Short-Term Memory (Task Context)**
  - Current transaction being analyzed
  - Intermediate reasoning steps
  - Tool call history for this task
  - Context window (<2000 tokens)
  - Cleared after task completion
- [ ] **Working Memory**
  - Recently used fraud policies
  - Calculation results cache
  - Recent tool outputs
  - LRU cache eviction
- [ ] **Long-Term Episodic Memory**
  - Previous fraud cases analyzed
  - Human feedback on decisions
  - Successful/failed detections
  - Timestamped episodes
- [ ] **Semantic Memory (Facts)**
  - Fraud detection policies
  - Transaction type rules
  - Risk thresholds
  - Knowledge base (RAG)
- [ ] **Procedural Memory (How-To)**
  - Analysis procedures
  - Tool usage patterns
  - Successful reasoning chains
  - Meta-learning (what works)

#### 3.5.2 Memory Implementation
- [ ] **Embedding Store (ChromaDB)**
  - 4 collections (fraud_cases, policies, explanations, patterns)
  - Metadata: timestamp, fraud_label, amount, type
  - Efficient retrieval (top-k=5)
- [ ] **Hybrid Search**
  - BM25 (keyword) + vector search
  - Re-ranking with cross-encoder
  - Filter by metadata (date, amount range)
- [ ] **Memory Summarization**
  - Summarize long episodes
  - Extract key insights
  - Reduce token usage
- [ ] **Memory Decay**
  - Weight recent memories higher
  - Archive old memories
  - Prune irrelevant memories
- [ ] **Retrieval Policies**
  - When to query long-term memory
  - How many memories to retrieve (k=3-5)
  - Relevance threshold (similarity >0.7)
- [ ] **Write Policies**
  - What to store (high-confidence decisions)
  - When to write (after task completion)
  - Deduplication (don't store duplicates)

---

### 3.6 Planning, Reasoning & Autonomy (NEW) ✅ (Completed: Jan 2, 2026)
**AGI Dimension:** Reasoning Systems Design

#### 3.6.1 Task Planning ✅
- [x] **Task Decomposition**
  - Break fraud analysis into subtasks (7 tasks: observe, query_policy, calculate_risk, check_history, reason, decide, explain)
  - Identify dependencies (A before B)
  - Create task DAG (directed acyclic graph) with cycle detection
  - Estimate task duration (0.5s to 2.0s per task)
- [x] **Dependency Tracking**
  - Track which tasks are complete (TaskStatus enum: PENDING, READY, IN_PROGRESS, COMPLETED, FAILED, SKIPPED)
  - Unblock dependent tasks via adjacency list
  - Parallel execution of independent tasks (5 parallel levels from 7 tasks)
- [x] **Dynamic Replanning**
  - Replan if new info emerges (high_confidence → skip remaining tasks)
  - Adapt to tool failures (add fallback tasks)
  - Shortcut if early decision possible (mark as SKIPPED)
- [x] **Goal Validation**
  - Is the goal achievable? (check required tasks vs available)
  - Do we have necessary tools? (validate before plan execution)
  - Are constraints satisfiable? (duration, required_tools checks)

#### 3.6.2 Reasoning Capabilities ✅
- [x] **Self-Critique**
  - "Is my reasoning sound?" (contradiction detection in reasoning steps)
  - "Did I consider all evidence?" (missing evidence tracking)
  - "Are there contradictions?" (detect conflicting risk assessments)
- [x] **Hypothesis Testing**
  - Hypothesis: "This is fraud" (Hypothesis model with statement, confidence)
  - Evidence: Transaction features (supporting/refuting evidence lists)
  - Test: Check against policies (evidence-based validation)
  - Conclude: Reject/accept hypothesis (HypothesisStatus: SUPPORTED, REFUTED, UNCERTAIN)
- [x] **Counterfactual Reasoning**
  - "What if amount was 10x higher?" (modification scenarios)
  - "What if this was CASH_OUT instead?" (type change scenarios)
  - Sensitivity analysis (normalized risk difference 0-1)
- [x] **Uncertainty Estimation**
  - Confidence scores (0-1)
  - Uncertainty sources (data, model, reasoning, conflict - tracked separately)
  - Propagate uncertainty through reasoning (product of confidences for independence)
- [x] **Constraint Satisfaction**
  - Hard constraints: Never approve >$200k (ConstraintType.HARD)
  - Soft constraints: Prefer Review over Block (ConstraintType.SOFT allows violations)
  - Optimize within constraints (check before finalizing decisions)

#### 3.6.3 Autonomy Control ✅
- [x] **Confidence Thresholds**
  - High confidence (>0.9): Auto-approve/block (AutonomyLevel.FULL_AUTO)
  - Medium confidence (0.7-0.9): Review (AutonomyLevel.SUPERVISED)
  - Low confidence (<0.7): Escalate to human (AutonomyLevel.ASSISTIVE)
- [x] **Escalation to Human**
  - Trigger conditions (low confidence <0.7, edge case, high value >$100k, conflicting evidence >2 contradictions)
  - Explanation for escalation (EscalationReason enum with 7 reasons)
  - Suggested decision + reasoning (EscalationTicket model with priority: CRITICAL/HIGH/MEDIUM/LOW)
- [x] **Stop Conditions**
  - Max reasoning steps (10) (StopReason.MAX_STEPS)
  - Timeout (30s) (StopReason.TIMEOUT with elapsed time tracking)
  - Unsolvable case detection (StopReason.UNSOLVABLE)
  - Circular reasoning detection (same reasoning appears twice)
- [x] **Goal Drift Prevention**
  - Validate decision aligns with goal (keyword overlap ratio >0.3)
  - Prevent scope creep (detect irrelevant topics: investment, advice, portfolio, tax, legal)
  - Return to main task if distracted (refocus_on_goal() generates correction instruction)

**Implementation Summary:**
- Created 3 core modules: `task_planner.py` (460 lines), `reasoning_engine.py` (560 lines), `autonomy_controller.py` (455 lines)
- Task planning with DAG: TaskPlanner creates 7-task plan, tracks dependencies, estimates duration (sequential 7.5s → parallel 5.5s = 1.4x speedup)
- Reasoning engine: Hypothesis testing (3 states), counterfactual analysis (4 scenarios), self-critique (soundness+completeness), uncertainty estimation (4 sources), constraint satisfaction (hard/soft)
- Autonomy control: 3 autonomy levels, 7 escalation triggers, 5 stop conditions, goal drift detection with refocusing
- Added 11 API endpoints for testing:
  * `POST /planning/create-plan` - Create task DAG
  * `POST /reasoning/test-hypothesis` - Test hypothesis against evidence
  * `POST /reasoning/counterfactual` - What-if analysis
  * `POST /reasoning/self-critique` - Critique reasoning chain
  * `POST /reasoning/estimate-uncertainty` - Quantify uncertainty
  * `POST /reasoning/check-constraints` - Validate constraints
  * `POST /autonomy/get-level` - Determine autonomy level
  * `POST /autonomy/check-escalation` - Check if should escalate
  * `POST /autonomy/check-stop-conditions` - Validate stop conditions
  * `POST /autonomy/check-goal-drift` - Detect goal drift
- Local testing completed: ALL 7 tests passing (task planning, hypothesis testing, counterfactual reasoning, self-critique, uncertainty estimation, constraint satisfaction, autonomy control)
- Test script: `backend/scripts/test_planning_reasoning.py`

---

### 3.7 Tool & Failure Recovery ✅ (Completed: Jan 2, 2026)
**AGI Interview Signal:** "Production agents need comprehensive error recovery"

#### 3.7.1 Tool Health & Monitoring ✅
- [x] Tool health checks with status tracking (HEALTHY, DEGRADED, UNHEALTHY)
- [x] Success rate monitoring (95%+ = healthy, 80%+ = degraded, <80% = unhealthy)
- [x] Response time tracking
- [x] Recent failure tracking (configurable window)
- [x] Health check intervals (configurable)

#### 3.7.2 Failure Analysis ✅
- [x] **Root cause analysis with 7 categories:**
  - TIMEOUT: Operation exceeded time limit
  - NETWORK: Connectivity issues
  - AUTHENTICATION: Auth/permission failures
  - RATE_LIMIT: API quota exceeded
  - INVALID_INPUT: Validation errors
  - INTERNAL_ERROR: Service bugs
  - DEPENDENCY_FAILURE: Upstream failures
- [x] Confidence scoring for diagnosis (0.0 to 1.0)
- [x] Contributing factors identification
- [x] Recommended recovery strategy selection

#### 3.7.3 Recovery Strategies ✅
- [x] **6 recovery strategies:**
  - RETRY: Exponential backoff retry
  - FALLBACK: Switch to backup tool
  - PARTIAL_RESULT: Use incomplete data
  - CACHE: Return cached result
  - ESCALATE: Request human intervention
  - ABORT: Stop execution
- [x] Fallback chains (primary → secondary → tertiary → cache)
- [x] Partial result aggregation (>50% = usable)
- [x] Strategy selection based on failure category

#### 3.7.4 Incident Reporting ✅
- [x] Automated incident creation with unique IDs
- [x] Severity classification (CRITICAL, HIGH, MEDIUM, LOW)
- [x] Impact assessment based on tool health
- [x] Recovery attempt tracking
- [x] Recovery success rate monitoring
- [x] Incident statistics and breakdown by category

**Implementation Summary:**
- Created `tool_recovery.py` (640 lines) with ToolRecoveryManager
- Tool health monitoring with status, success rate, response time tracking
- Root cause analysis with 7 failure categories and confidence scoring
- 6 recovery strategies with automatic selection
- Fallback chains supporting primary/secondary/tertiary with cache fallback
- Partial result aggregation with 50% usability threshold
- Incident reporting with severity, impact, and recovery tracking
- Added 8 API endpoints:
  * `POST /recovery/check-health` - Run health check
  * `POST /recovery/analyze-failure` - Analyze root cause
  * `POST /recovery/register-fallback` - Register fallback chain
  * `POST /recovery/aggregate-partial` - Aggregate partial results
  * `GET /recovery/health-status` - Get health status for all tools
  * `GET /recovery/incidents` - Get incident reports with filtering
  * `GET /recovery/statistics` - Recovery statistics
- All tests passing: 5/5 (health checks, root cause, fallback chains, partial aggregation, incident reporting)

---

### 3.8 Async & Production Patterns ✅ (Completed: Jan 2, 2026)
**AGI Interview Signal:** "I architect for production scale, not just demos"

#### 3.8.1 Worker Pool & Background Tasks ✅
- [x] Worker pool with configurable size (default 10 workers)
- [x] Priority queue system (CRITICAL, HIGH, NORMAL, LOW)
- [x] Task status tracking (PENDING, RUNNING, COMPLETED, FAILED, CANCELLED)
- [x] Task cancellation support
- [x] Worker timeout handling (default 5 minutes)
- [x] Queue size limits (default 100 tasks)
- [x] Task progress tracking (0.0 to 1.0)
- [x] Task metadata storage

#### 3.8.2 Real-Time Communication ✅
- [x] **WebSocket Manager:**
  - Client connection management
  - Topic-based subscriptions
  - Broadcast messaging to subscribers
  - Direct client messaging
  - Connection statistics
  - Graceful disconnect handling
- [x] **Server-Sent Events (SSE):**
  - Event streaming with configurable intervals
  - Event count limiting
  - Topic-based event generation
  - Timestamp tracking

#### 3.8.3 Connection Pooling ✅
- [x] Generic connection pool implementation
- [x] Min/max connection limits (default 5-20)
- [x] Connection lifecycle management
- [x] Connection age tracking with max lifetime (default 1 hour)
- [x] Idle timeout handling (default 5 minutes)
- [x] Connection acquisition/release tracking
- [x] Pool statistics (created, closed, acquired, released)
- [x] Graceful pool shutdown

#### 3.8.4 Resource Management ✅
- [x] Resource registration with cleanup functions
- [x] Last access time tracking
- [x] Idle resource cleanup (configurable timeout)
- [x] Manual resource cleanup
- [x] Bulk cleanup operations
- [x] Resource statistics (total, idle, access times)
- [x] Automatic garbage collection

**Implementation Summary:**
- Created `async_patterns.py` (820 lines) with 5 core classes
- **WorkerPool:** Priority queue, 4 priority levels, task cancellation, worker timeout
- **WebSocketManager:** Topic subscriptions, broadcast/direct messaging, connection tracking
- **ConnectionPool:** Min/max limits, lifecycle management, idle/age cleanup
- **ResourceManager:** Registration, idle cleanup, access tracking
- **BackgroundTask model:** Status, priority, progress, metadata, timing
- Added 12 API endpoints:
  * `POST /async/submit-task` - Submit background task with priority
  * `GET /async/task/{task_id}` - Get task status and progress
  * `DELETE /async/task/{task_id}` - Cancel running task
  * `GET /async/worker-stats` - Worker pool statistics
  * `WS /ws/{client_id}` - WebSocket connection endpoint
  * `POST /async/broadcast` - Broadcast to WebSocket subscribers
  * `GET /async/websocket-stats` - WebSocket statistics
  * `GET /async/stream/{topic}` - Server-Sent Events stream
  * `GET /async/resource-stats` - Resource manager statistics
  * `POST /async/cleanup-resources` - Cleanup idle resources
- Optional SSE support (requires sse-starlette package)
- All tests passing: 4/4 (worker pool, connection pool, WebSocket manager, resource manager)

**Test Results:**
- Worker pool: 7 tasks submitted (1 critical, 5 normal, 1 low), all completed in 3.6s
- Connection pool: 4 connections acquired/released, lifecycle managed correctly
- WebSocket: 2 clients connected, topic subscriptions, broadcast and direct messaging working
- Resource manager: 5 resources registered, idle cleanup working, all resources cleaned

---

### 2.2 Document Processing Module
- [ ] Setup Ollama Docker container
- [ ] Configure local LLM model (llama2/mistral)
- [ ] Create LLM wrapper service
- [ ] Implement prompt templates
- [ ] Add streaming response support

### 3.6 API Endpoints
- [ ] POST /upload - File upload endpoint
- [ ] POST /transactions/analyze - Single transaction fraud analysis
- [ ] POST /transactions/batch - Batch fraud detection
- [ ] POST /transactions/explain - LLM explanation for decision
- [ ] GET /categories - Spending categories
- [ ] GET /insights - Financial insights
- [ ] GET /fraud/stats - Fraud statistics dashboard
- [ ] GET /fraud/policies - Retrieve fraud policies (RAG)
- [ ] WebSocket endpoint for streaming explanations
- [ ] POST /feedback - Human-in-the-loop corrections

### 2.7 Testing & Quality
- [ ] Unit tests (pytest)
- [ ] Integration tests
- [ ] API endpoint tests
- [ ] Load testing
- [ ] Code coverage > 80%

---

## 4. Frontend Development (Status: ⚪ Not Started - 0%)

### 4.1 Next.js Application Setup
- [ ] Initialize Next.js 14 with App Router
- [ ] Setup TypeScript configuration
- [ ] Configure Tailwind CSS
- [ ] Setup shadcn/ui components
- [ ] Configure ESLint and Prettier

### 4.2 Core Pages
- [ ] Landing page with hero section
- [ ] Upload page (CSV + PDF drag-and-drop)
- [ ] Fraud Detection Dashboard
- [ ] Transaction analysis page with risk scores
- [ ] Transaction details with explanation
- [ ] Real-time monitoring page
- [ ] Insights & analytics page
- [ ] Settings page

### 4.3 UI Components
- [ ] CSV upload component with preview
- [ ] Transaction table with risk scores
- [ ] Risk gauge component (0-100)
- [ ] Decision badge (Approve/Review/Block)
- [ ] Fraud rate chart (Recharts)
- [ ] Temporal fraud patterns visualization
- [ ] Anomaly alert cards with explanations
- [ ] AI reasoning panel (chain-of-thought display)
- [ ] Confidence score indicator
- [ ] Human-in-the-loop feedback buttons
- [ ] Loading states and skeletons

### 3.4 State Management
- [ ] Setup Zustand/Redux store
- [ ] Implement file upload state
- [ ] Implement analysis results state
- [ ] Add error handling state
- [ ] Implement user preferences state

### 3.5 API Integration
- [ ] Create API client service
- [ ] Implement file upload logic
- [ ] Add streaming response handling
- [ ] Error handling and retry logic
- [ ] Loading states management

### 3.6 Responsive Design
- [ ] Mobile responsive layout
- [ ] Tablet optimization
- [ ] Desktop layout
- [ ] Dark mode support
- [ ] Accessibility (WCAG 2.1 AA)

---

## 5. Infrastructure & DevOps (Status: 🟡 In Progress - 10%)

### 5.1 Docker Setup
- [ ] Backend Dockerfile
- [ ] Frontend Dockerfile
- [x] Ollama service configuration
- [x] Vector store Docker setup
- [x] docker-compose.yml for local development
- [ ] docker-compose.prod.yml

### 4.2 Kubernetes Configuration
- [ ] Create namespace definitions
- [ ] Backend deployment manifest
- [ ] Frontend deployment manifest
- [ ] Ollama deployment manifest
- [ ] Service definitions
- [ ] ConfigMaps and Secrets
- [ ] Persistent Volume Claims
- [ ] Ingress configuration

### 4.3 Helm Charts
- [ ] Create Helm chart structure
- [ ] values.yaml configuration
- [ ] Backend chart
- [ ] Frontend chart
- [ ] Dependencies chart
- [ ] Chart testing

### 4.4 Terraform Infrastructure
- [ ] AWS provider configuration
- [ ] VPC and networking setup
- [ ] EKS cluster configuration
- [ ] RDS/DocumentDB setup (if needed)
- [ ] S3 buckets for storage
- [ ] IAM roles and policies
- [ ] Load balancer configuration
- [ ] Route53 DNS configuration

### 4.5 CI/CD Pipeline
- [ ] GitHub Actions workflow
- [ ] Build and test jobs
- [ ] Docker image build and push
- [ ] Kubernetes deployment automation
- [ ] Rollback strategies
- [ ] Environment-specific deployments

---

## 6. Testing & Quality Assurance (Status: ⚪ Not Started - 0%)
**AGI Interview Signal:** "I evaluated across classification, reasoning, and adversarial dimensions"

### 6.0 ML Model Evaluation (NEW - Critical)
- [ ] Classification metrics (Precision, Recall, F1, AUC-ROC)
- [ ] Confusion matrix analysis
- [ ] Threshold tuning (Approve/Review/Block)
- [ ] Cross-validation (5-fold stratified)
- [ ] Learning curves
- [ ] Feature importance plots
- [ ] Error analysis (false positives/negatives)
- [ ] Model comparison (baseline vs LLM-enhanced)

### 6.1 Backend Testing
- [ ] Unit tests for all modules
- [ ] Integration tests
- [ ] API contract tests
- [ ] Performance tests
- [ ] Security testing (OWASP)

### 5.2 Frontend Testing
- [ ] Component unit tests (Jest/Vitest)
- [ ] Integration tests
- [ ] E2E tests (Playwright/Cypress)
- [ ] Visual regression tests
- [ ] Accessibility tests

### 6.3 LLM & Agent Evaluation
- [ ] Reasoning correctness evaluation
- [ ] Explanation faithfulness checks
- [ ] Hallucination detection tests
- [ ] Response quality assessment (clarity, safety)
- [ ] Chain-of-thought validation
- [ ] Self-consistency testing (multiple runs)
- [ ] Prompt engineering A/B tests
- [ ] RAG retrieval accuracy
- [ ] Tool use correctness (calculator)
- [ ] Edge case handling (rare fraud types)
- [ ] Latency benchmarking (<2s target)
- [ ] Token usage tracking (<500 tokens)
- [ ] Cost-per-transaction analysis

---

## 7. Documentation (Status: 🟡 In Progress - 60%)

### 7.1 Technical Documentation
- [x] Work Breakdown Structure (this document)
- [x] System Design & Architecture
- [x] Database Design Diagram
- [ ] API Documentation (OpenAPI/Swagger)
- [ ] Component Documentation

### 6.2 Deployment Documentation
- [x] Local Development Setup Guide
- [x] Docker Deployment Guide
- [x] Kubernetes Deployment Guide
- [x] AWS Deployment with Terraform
- [x] Render Free Tier Deployment Guide
- [x] Troubleshooting Guide

### 6.3 User Documentation
- [x] Quick Start Guide (QUICKSTART.md)
- [ ] User Guide
- [ ] API Integration Guide
- [ ] FAQ
- [ ] Video tutorials (optional)

### 6.4 Developer Guidelines
- [x] Contributing Guide
- [x] Code Style Guide (.cursorrules)
- [x] Git Workflow
- [ ] PR Templates

### 6.5 Additional Documentation
- [x] Project Setup Summary
- [x] Directory Structure Visualization
- [x] Status Tracker
- [x] Figma Design Prompt

---

## 8. Safety, Security & Alignment (Status: ⚪ Not Started - 0%)
**AGI Interview Signal:** "I built safety guardrails before production deployment"

### 8.0 LLM Safety & Alignment (NEW - Critical for AGI)
- [ ] Prompt injection detection
- [ ] Jailbreak attempt testing
- [ ] Adversarial prompt dataset creation
- [ ] Implement refusal logic (no financial advice)
- [ ] Uncertainty quantification
- [ ] Confidence thresholds for escalation
- [ ] Red-team testing with harmful prompts
- [ ] Safety fine-tuning (if using LoRA)
- [ ] Output sanitization
- [ ] Bias audit across transaction amounts
- [ ] Fairness metrics (demographic parity)
- [ ] Human-in-the-loop override mechanism
- [ ] Safety evaluation dashboard

### 8.1 Security Implementation
- [ ] API authentication (JWT)
- [ ] Rate limiting
- [ ] Input validation and sanitization
- [ ] File upload security
- [ ] HTTPS/TLS configuration
- [ ] Secrets management

### 7.2 Data Privacy
- [ ] Data encryption at rest
- [ ] Data encryption in transit
- [ ] PII handling
- [ ] GDPR compliance considerations
- [ ] Data retention policies

---

## 9. Monitoring & Observability (Status: ⚪ Not Started - 0%)
**AGI Interview Signal:** "I implemented production ML monitoring with drift detection"

### 9.0 ML Model Monitoring (NEW)
- [ ] Model performance tracking (F1, precision, recall)
- [ ] Prediction distribution monitoring
- [ ] Data drift detection (feature distributions)
- [ ] Concept drift detection (fraud patterns)
- [ ] Token usage dashboard
- [ ] Latency percentiles (p50, p95, p99)
- [ ] Error rate by transaction type
- [ ] Fraud detection rate over time
- [ ] False positive/negative trends
- [ ] A/B test framework for prompt variants

### 9.1 Logging
- [ ] Structured logging (JSON)
- [ ] Log aggregation setup
- [ ] Error tracking (Sentry)
- [ ] Audit logs

### 8.2 Metrics & Monitoring
- [ ] Prometheus metrics
- [ ] Grafana dashboards
- [ ] Application performance monitoring
- [ ] Resource usage monitoring
- [ ] Alerting rules

### 8.3 Tracing
- [ ] Distributed tracing setup
- [ ] Request tracing
- [ ] Performance profiling

---

## 10. Model Training & Fine-Tuning (Status: ⚪ Not Started - 0%)
**AGI Interview Signal:** "I fine-tuned a local LLM for domain adaptation"

### 10.1 Baseline Model Training
- [ ] Train Random Forest classifier
- [ ] Train XGBoost classifier
- [ ] Hyperparameter tuning (GridSearch/Optuna)
- [ ] Model selection & comparison
- [ ] Save best model artifacts

### 10.2 Prompt Engineering
- [ ] Zero-shot fraud detection prompt
- [ ] Few-shot examples selection (5-10 cases)
- [ ] Chain-of-thought prompting
- [ ] ReAct prompt template design
- [ ] Self-consistency prompting
- [ ] Prompt versioning & tracking
- [ ] A/B testing different prompts

### 10.3 Fine-Tuning (Optional but Powerful)
- [ ] Prepare instruction tuning dataset
- [ ] Create fraud explanation pairs
- [ ] Setup LoRA configuration
- [ ] Fine-tune Mistral 7B with LoRA
- [ ] Evaluate fine-tuned vs base model
- [ ] Preference optimization (DPO/RLHF simulation)
- [ ] Safety alignment fine-tuning
- [ ] Save fine-tuned adapters

### 10.4 Model Compression
- [ ] Quantize model to 4-bit (GGUF)
- [ ] Test quantized model performance
- [ ] Latency comparison (full vs quantized)
- [ ] Select optimal quantization level

---

## 11. Deployment & Launch (Status: ⚪ Not Started - 0%)

### 11.1 Pre-Launch
- [ ] Performance optimization
- [ ] Security audit
- [ ] Load testing
- [ ] User acceptance testing
- [ ] Documentation review

### 9.2 Deployment
- [ ] Deploy to staging environment
- [ ] Staging testing
- [ ] Deploy to production (Render/AWS)
- [ ] DNS configuration
- [ ] SSL certificate setup

### 11.3 Post-Launch
- [ ] Monitor application health
- [ ] Gather user feedback
- [ ] Bug fixes
- [ ] Performance tuning
- [ ] Feature iterations
- [ ] Continuous learning pipeline
- [ ] Human feedback integration

---

## 12. Model Interpretability & Explainability (Status: ⚪ Not Started - 0%)
**AGI Interview Signal:** "I built explainable AI with faithful reasoning traces"

### 12.1 Feature Importance
- [ ] SHAP values for ML model
- [ ] Feature contribution visualization
- [ ] Partial dependence plots
- [ ] LIME for local explanations

### 12.2 LLM Explanation Quality
- [ ] Chain-of-thought trace logging
- [ ] Reasoning step validation
- [ ] Faithfulness metrics (explanation ↔ prediction)
- [ ] Human evaluation of explanations
- [ ] Explanation templates for consistency
- [ ] Multi-language explanation support

### 12.3 Debugging & Analysis
- [ ] Error case analysis dashboard
- [ ] Misclassification inspection tool
- [ ] Agent decision tree visualization
- [ ] Token attribution (which tokens influenced decision)

---

## Legend

- ✅ **Completed**
- 🟡 **In Progress**
- ⚪ **Not Started**
- 🔴 **Blocked**
- ⏸️ **On Hold**

---

## 13. Advanced Planning & Reasoning (NEW - AGI Core)
**AGI Dimension:** Reasoning Systems Design
**AGI Interview Signal:** "I built goal-directed reasoning systems with self-critique"

### 13.1 Goal-Directed Behavior
- [ ] Explicit goal specification (detect fraud)
- [ ] Goal decomposition into subgoals
- [ ] Success criteria definition
- [ ] Goal satisfaction checking
- [ ] Multi-objective optimization (accuracy vs speed)
- [ ] Goal drift detection and prevention

### 13.2 Advanced Reasoning Patterns
- [ ] **Analogical Reasoning**
  - "This transaction is similar to case #12345"
  - Transfer learning from similar cases
  - Case-based reasoning
- [ ] **Abductive Reasoning**
  - Infer best explanation for observations
  - "Most likely explanation is money laundering"
- [ ] **Deductive Reasoning**
  - Apply rules strictly
  - "IF amount >$200k AND new_account THEN flag"
- [ ] **Inductive Reasoning**
  - Generalize from examples
  - "All previous fraud cases had X pattern"
- [ ] **Causal Reasoning**
  - "Balance drop CAUSED by large transfer"
  - Causal chains (A → B → C)

### 13.3 Meta-Reasoning
- [ ] Reasoning about reasoning quality
- [ ] When to stop reasoning (diminishing returns)
- [ ] When to ask for more information
- [ ] When to escalate vs decide autonomously
- [ ] Reasoning strategy selection (fast vs thorough)
- [ ] Self-explanation of reasoning process

### 13.4 Adversarial Reasoning
- [ ] Red-team mode: "How would I evade detection?"
- [ ] Attack scenario generation
- [ ] Defense strategy development
- [ ] Adversarial robustness testing

---

## 14. Memory Systems Implementation (NEW - Deep Dive)
**AGI Dimension:** Autonomy & Agent Reliability
**AGI Interview Signal:** "Memory = learning across time"

### 14.1 Short-Term Memory Implementation
- [ ] Context window management (8192 tokens)
- [ ] Recent transaction cache (last 10)
- [ ] Tool call history for current session
- [ ] Intermediate reasoning buffer
- [ ] Context compression when near limit
- [ ] Session-scoped memory lifecycle

### 14.2 Working Memory (Redis-based)
- [ ] LRU cache for fraud policies (100 entries)
- [ ] Recent risk calculations cache
- [ ] Frequently accessed patterns
- [ ] Cache hit rate monitoring
- [ ] TTL-based expiration (1 hour)
- [ ] Cache warming strategies

### 14.3 Long-Term Episodic Memory (ChromaDB)
- [ ] Store completed fraud analyses
- [ ] Successful detection episodes
- [ ] Failed detection episodes (with corrections)
- [ ] Human feedback integrated
- [ ] Temporal indexing (retrieve by date range)
- [ ] Episode summarization for efficiency

### 14.4 Semantic Memory (Knowledge Base)
- [ ] Fraud detection policies (versioned)
- [ ] Transaction type definitions
- [ ] Risk thresholds and rules
- [ ] Regulatory requirements
- [ ] Industry best practices
- [ ] Knowledge graph (optional)

### 14.5 Procedural Memory (Meta-Learning)
- [ ] Successful reasoning chains
- [ ] Effective tool usage patterns
- [ ] Prompt templates that work
- [ ] Error recovery procedures
- [ ] What works for edge cases
- [ ] Meta-learning: Learn what strategies work

### 14.6 Memory Retrieval Optimization
- [ ] Hybrid search (BM25 + vector)
- [ ] Re-ranking retrieved memories
- [ ] Relevance threshold tuning (>0.75)
- [ ] Diversity in retrieval (not all similar)
- [ ] Temporal weighting (recent > old)
- [ ] Query expansion for better recall

### 14.7 Memory Consolidation
- [ ] Batch memory writes (not per transaction)
- [ ] Memory deduplication
- [ ] Memory summarization (compress old episodes)
- [ ] Archive rarely accessed memories
- [ ] Prune low-value memories
- [ ] Memory importance scoring

---

## 15. Production & Cost Engineering (NEW - Critical)
**AGI Dimension:** Scalable Infrastructure + Cost Control
**AGI Interview Signal:** "Real AGI systems must scale economically"

### 15.1 Infrastructure as Code
- [ ] Terraform for cloud resources
- [ ] Kubernetes manifests (deployments, services)
- [ ] Helm charts for packaging
- [ ] Multi-environment configs (dev, staging, prod)
- [ ] Infrastructure versioning
- [ ] Automated provisioning

### 15.2 Async Workers & Queue System
- [ ] Celery workers for background tasks
- [ ] Redis as message broker
- [ ] Task prioritization (high-value transactions first)
- [ ] Worker auto-scaling (based on queue depth)
- [ ] Dead letter queue for failures
- [ ] Task retry policies

### 15.3 Multi-Tenant Isolation
- [ ] Tenant ID in all requests
- [ ] Resource quotas per tenant
- [ ] Data isolation (separate DB schemas)
- [ ] Rate limiting per tenant
- [ ] Cost tracking per tenant
- [ ] Fair scheduling (prevent starvation)

### 15.4 Secrets Management
- [ ] HashiCorp Vault or AWS Secrets Manager
- [ ] API key rotation
- [ ] Encrypted environment variables
- [ ] Secret injection at runtime
- [ ] Audit logs for secret access
- [ ] Principle of least privilege

### 15.5 Rate Limiting & Throttling
- [ ] Token bucket algorithm
- [ ] Rate limits per endpoint
- [ ] Rate limits per user/tenant
- [ ] Graceful degradation under load
- [ ] 429 Too Many Requests responses
- [ ] Retry-After headers

### 15.6 Cost Control Strategies
- [ ] **Prompt Compression**
  - Remove unnecessary words
  - Abbreviate common terms
  - Template reuse
  - Token budget per request (<1500)
- [ ] **Context Pruning**
  - Keep only relevant history
  - Summarize long contexts
  - Sliding window for conversations
- [ ] **Model Routing**
  - Small model (fast, cheap) for simple cases
  - Large model for complex cases only
  - Confidence-based routing
  - Cost-accuracy tradeoff monitoring
- [ ] **Caching Strategies**
  - Cache LLM responses for identical prompts
  - Cache embeddings for documents
  - Cache tool results (if deterministic)
  - TTL-based invalidation
- [ ] **Batch Processing**
  - Batch transactions for ML inference
  - Batch embeddings (100+ at once)
  - Amortize API overhead

### 15.7 Deployment Strategies
- [ ] **Canary Deployments**
  - Route 5% traffic to new version
  - Monitor error rates
  - Gradual rollout to 100%
  - Automated rollback on failures
- [ ] **Versioned Prompts**
  - Version control for prompts (v1, v2, v3)
  - A/B test prompt versions
  - Track performance per version
  - Rollback to previous version
- [ ] **Blue-Green Deployment**
  - Maintain two identical environments
  - Switch traffic instantly
  - Easy rollback
- [ ] **Feature Flags**
  - Enable/disable features dynamically
  - Gradual feature rollout
  - Kill switches for problematic features

### 15.8 Continuous Evaluation
- [ ] Automated evaluation pipeline
- [ ] Daily performance reports
- [ ] Regression testing (accuracy doesn't drop)
- [ ] Benchmark suite (fixed test cases)
- [ ] Evaluation dashboard
- [ ] Alerts on performance degradation

---

## 16. Research-Level Awareness (NEW - Expected Knowledge)
**AGI Interview Signal:** "I understand emergent behavior and self-play agents"

### 16.1 Core Concepts (Conceptual Understanding)
- [ ] **RLHF (Reinforcement Learning from Human Feedback)**
  - Conceptual: Reward model trains on human preferences
  - Application: Use feedback to improve explanations
  - Implementation: Collect thumbs up/down, retrain
- [ ] **RLAIF (RL from AI Feedback)**
  - Use LLM as judge instead of humans
  - Scale feedback collection
  - Self-improvement loop
- [ ] **Agent Benchmarks**
  - Understand SWE-bench, HumanEval, AgentBench
  - Know what good performance looks like
  - Compare own agent to benchmarks
- [ ] **Emergent Behavior**
  - Capabilities not explicitly trained
  - Tool use emergence
  - Planning emergence from next-token prediction
  - Failure modes (deception, reward hacking)
- [ ] **World Models**
  - Agent's internal model of environment
  - Predict consequences of actions
  - Counterfactual simulation
- [ ] **Self-Play Agents**
  - Agent plays against itself to improve
  - Application: Fraud agent vs evasion agent
  - AlphaGo-style improvement

### 16.2 Distribution Shift from Tools
- [ ] Tool use changes data distribution
- [ ] Agent learns to exploit tools
- [ ] Monitor for tool over-reliance
- [ ] Generalization outside tool scope
- [ ] Tool-free fallback capabilities

### 16.3 Simulated Environments
- [ ] Create fraud simulation environment
- [ ] Synthetic transaction generator
- [ ] Adversarial fraud scenarios
- [ ] Test agent in simulation before production
- [ ] Safe exploration space

---

## 17. Advanced Evaluation & Debugging (NEW - Deep Dive)
**AGI Dimension:** Safety, Alignment, Evaluation
**AGI Interview Signal:** "AGI teams value measurement over demos"

### 17.1 Agent Debugging Tools
- [ ] **Step-Level Traces**
  - Log every reasoning step
  - Timestamp each step
  - Tool calls with inputs/outputs
  - Decision points highlighted
  - Exportable trace format (JSON)
- [ ] **Thought Inspection**
  - Extract scratchpad contents
  - View internal reasoning
  - Identify reasoning errors
  - Validate CoT consistency
- [ ] **Tool Replay**
  - Replay tool calls from logs
  - Deterministic re-execution
  - Debug tool failures
  - Test tool changes safely
- [ ] **Failure Clustering**
  - Group similar failures
  - Identify systematic errors
  - Prioritize fixes
  - Pattern recognition in failures
- [ ] **Deterministic Replay**
  - Replay exact agent execution
  - Fixed random seeds
  - Cached tool results
  - Reproduce bugs reliably

### 17.2 Comprehensive Metrics
- [ ] **Task Success Rate**
  - % of transactions correctly classified
  - % of decisions aligned with human
  - % of tasks completed without errors
- [ ] **Tool Accuracy**
  - Tool success rate
  - Tool selection accuracy
  - Parameter correctness
  - Tool necessity (was tool needed?)
- [ ] **Cost per Task**
  - Token usage per transaction
  - API calls per transaction
  - Total $ cost per transaction
  - Cost-performance tradeoff
- [ ] **Latency Metrics**
  - p50, p95, p99 latencies
  - Latency by complexity
  - Time per reasoning step
  - Tool call latency breakdown
- [ ] **Recovery Rate**
  - % of failures recovered from
  - Recovery time
  - Escalation rate
  - Human intervention rate
- [ ] **Alignment Violations**
  - Safety rule violations
  - Constraint violations
  - Refusal failures (should refuse but didn't)
  - False refusals (refused valid requests)

### 17.3 Automated Testing Suites
- [ ] Unit tests for agent components
- [ ] Integration tests for full workflow
- [ ] Regression tests (prevent quality drops)
- [ ] Adversarial tests (red team)
- [ ] Edge case tests (rare scenarios)
- [ ] Performance benchmarks
- [ ] Continuous testing in CI/CD

---

## 18. LLM-Specific Engineering (NEW - Deep Technical)
**AGI Dimension:** Reasoning Systems Design

### 18.1 Tokenization Engineering
- [ ] Analyze Mistral tokenizer behavior
- [ ] Token efficiency optimization
  - Use shorter words where possible
  - Avoid repetition
  - Optimize prompt structure
- [ ] Multi-lingual tokenization (if needed)
- [ ] Special token handling (<|im_start|>, etc.)
- [ ] Subword tokenization impact

### 18.2 Context Window Management
- [ ] Sliding window for long conversations
- [ ] Context summarization
- [ ] Important content retention
- [ ] Context overflow graceful handling
- [ ] Dynamic context allocation (reserve space for output)

### 18.3 Sampling Strategy Optimization
- [ ] Temperature scheduling (vary over time)
- [ ] Top-p tuning for diversity vs quality
- [ ] Repetition penalty configuration
- [ ] Length penalty for conciseness
- [ ] Early stopping conditions

### 18.4 Mixture-of-Experts (MoE) Awareness
- [ ] Understand MoE routing
- [ ] Know when experts activate
- [ ] Cost implications (active vs total params)
- [ ] Inference efficiency benefits

### 18.5 Speculative Decoding (Conceptual)
- [ ] Understand draft model + verification
- [ ] Latency reduction benefits
- [ ] When applicable (long-form generation)

### 18.6 Distillation vs Prompting
- [ ] When to distill (lots of data, fixed task)
- [ ] When to prompt (few examples, flexible)
- [ ] Hybrid approaches
- [ ] Cost-performance tradeoffs

---

## Milestones

| Milestone | Target Date | Status | Completion Date | AGI Signal |
|-----------|-------------|--------|----------------|------------|
| Project Setup Complete | Week 1 | ✅ Completed | Dec 26, 2025 | Foundation |
| Core CS Foundations (Async, State) | Week 2 | ⚪ Not Started | - | Distributed systems thinking |
| Data Lifecycle Complete | Week 3 | ⚪ Not Started | - | End-to-end data engineering |
| Baseline Fraud Classifier | Week 4 | ⚪ Not Started | - | ML fundamentals |
| LLM Fundamentals Implementation | Week 5 | ⚪ Not Started | - | Token engineering, sampling |
| Prompt Architecture (ReAct, CoT) | Week 6 | ⚪ Not Started | - | Prompting as system design |
| Tool Use & Environment Control | Week 7 | ⚪ Not Started | - | Agents need tools |
| Single-Agent Architecture | Week 8 | ⚪ Not Started | - | Core agent implementation |
| Memory Systems Complete | Week 9 | ⚪ Not Started | - | Learning across time |
| Planning & Reasoning | Week 10 | ⚪ Not Started | - | Goal-directed behavior |
| Multi-Agent Coordination (Optional) | Week 11 | ⚪ Not Started | - | Advanced coordination |
| Safety & Adversarial Testing | Week 12 | ⚪ Not Started | - | Alignment & control |
| Evaluation & Observability | Week 13 | ⚪ Not Started | - | Measurement over demos |
| Production & Cost Engineering | Week 14 | ⚪ Not Started | - | Economic scalability |
| Fine-Tuning with LoRA | Week 15 | ⚪ Not Started | - | Domain adaptation |
| Frontend Integration | Week 16 | ⚪ Not Started | - | User interface |
| Deployment with Monitoring | Week 17 | ⚪ Not Started | - | Production readiness |
| Research-Level Features | Week 18 | ⚪ Not Started | - | Emergent behavior awareness |
| Portfolio Documentation | Week 19 | ⚪ Not Started | - | Interview preparation |
| Production Launch | Week 20 | ⚪ Not Started | - | Full system live |

---

## Risk Management

| Risk | Impact | Probability | Mitigation | AGI Relevance |
|------|---------|------------|------------|---------------|
| Class imbalance (0.13% fraud) | High | High | SMOTE, class weights, stratified sampling | Data engineering |
| LLM hallucinations in fraud decisions | Critical | Medium | Validation, confidence scores, human-in-loop | Safety & alignment |
| Prompt injection attacks | High | Medium | Input sanitization, safety fine-tuning | Security |
| Data drift (new fraud patterns) | High | Medium | Continuous monitoring, retraining pipeline | Production ML |
| Ollama performance on CPU | Medium | High | Quantization, prompt optimization, caching | Cost engineering |
| Vector store memory limits | Medium | High | Efficient chunking, cleanup policies | Infrastructure |
| False positives hurting UX | High | Medium | Threshold tuning, Review tier, feedback loop | UX & alignment |
| Adversarial fraud attempts | High | Low | Red-team testing, anomaly detection | Safety |
| Privacy leakage in explanations | Critical | Low | PII masking, output sanitization | Privacy |
| Agent gets stuck in reasoning loops | Medium | Medium | Max step limits, circular reasoning detection | Autonomy control |
| Tool failure cascades | Medium | Medium | Retry logic, fallback tools, circuit breakers | Reliability |
| Cost explosion from LLM calls | High | Medium | Model routing, caching, prompt compression | Cost control |
| Multi-agent coordination failures | Medium | Low | Consensus protocols, timeout handling | Multi-agent systems |
| Memory system performance degradation | Medium | Medium | Hybrid search, caching, pruning | Scalability |
| Context window overflow | Medium | High | Summarization, sliding window, context pruning | LLM engineering |
| Emergent adversarial behavior | Low | Low | Continuous monitoring, kill switches | Research awareness |
| Model distillation quality loss | Low | Medium | Evaluation pipeline, benchmark suite | Model optimization |

---

## 🎯 AGI Interview Readiness Statement

**Core Message:**
"I design agents as distributed, failure-tolerant systems with explicit reasoning loops, memory, evaluation, and safety controls."

**This Project Demonstrates:**

1. **Reasoning Systems Design** → ReAct agents, Chain-of-Thought, self-critique, multi-step planning
2. **Autonomy & Reliability** → State machines, checkpointing, retry logic, partial failure handling
3. **Scalable Infrastructure** → Async workers, model routing, caching, cost optimization
4. **Safety & Alignment** → Prompt injection defense, refusal policies, red-team testing, human-in-loop

**Key Talking Points for Interviews:**
- "I built memory systems with short-term, working, and long-term episodic storage"
- "I implemented agent debugging with step-level traces and deterministic replay"
- "I designed multi-agent coordinator-worker patterns with consensus building"
- "I optimized for cost with prompt compression, model routing, and caching strategies"
- "I evaluated across classification, reasoning quality, and adversarial robustness"
- "I implemented safety controls: prompt injection detection, refusal logic, uncertainty escalation"
- "I built production ML monitoring with data drift detection and performance tracking"
- "I designed goal-directed reasoning with self-critique and hypothesis testing"

---

## 📊 Project Statistics (Updated Dec 28, 2025)

| Metric | Value |
|--------|-------|
| Total WBS Sections | 18 (was 12) |
| Total Tasks | 400+ (was 250+) |
| AGI Topics Covered | 11/11 (100%) |
| AGI Dimensions Covered | 4/4 (100%) |
| Documentation Words | 25,000+ |
| Code Examples Planned | 100+ |
| Estimated Completion | 20 weeks |
| Interview Signals | 15+ explicit callouts |

---

## Notes

- This is a living document and will be updated as the project progresses
- Each completed task should be marked with a checkmark and date
- Blockers should be documented in the Risk Management section
- Regular reviews should be conducted weekly
