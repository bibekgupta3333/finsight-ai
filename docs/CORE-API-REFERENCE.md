# FinSight AI - Core Backend API Reference

Complete reference for the core backend APIs that power FinSight AI's fraud detection system.

## API Overview

FinSight AI provides three main API modules:

1. **Fraud Detection API** (`/api/v1/fraud/*`) - Transaction analysis endpoints using various prompting patterns and agent architectures
2. **LLM Engineering API** (`/api/v1/llm/*`) - Token analysis, sampling configuration, model routing, and safety checks
3. **Memory System API** (`/memory/*`) - Episodic, semantic, and procedural memory management

---

## 1. Fraud Detection API

**Base Path**: `/api/v1/fraud`

### 1.1 Core Transaction Analysis

#### `POST /analyze`
Analyze a single transaction for fraud using async processing.

**Request Body**:
```json
{
  "transaction": {
    "transaction_id": "TX_12345",
    "type": "TRANSFER",
    "amount": 125000.0,
    "oldbalanceOrg": 150000.0,
    "newbalanceOrig": 25000.0,
    "oldbalanceDest": 10000.0,
    "newbalanceDest": 135000.0
  }
}
```

**Response**:
```json
{
  "transaction_id": "TX_12345",
  "fraud": true,
  "risk": 85.0,
  "level": "HIGH",
  "time_ms": 105.3,
  "explanation": "Large transfer draining 83% of origin balance with suspicious destination pattern"
}
```

**Use Case**: Primary endpoint for real-time fraud detection. Powered by the prepared ChromaDB collections containing fraud policies, explanations, and transaction patterns.

---

#### `POST /batch`
Analyze multiple transactions in batch mode using async worker pool.

**Request Body**:
```json
{
  "transactions": [
    {
      "transaction_id": "TX_001",
      "type": "TRANSFER",
      "amount": 95000.0,
      ...
    },
    {
      "transaction_id": "TX_002",
      "type": "CASH_OUT",
      "amount": 45000.0,
      ...
    }
  ]
}
```

**Response**:
```json
{
  "task_id": "batch-abc123def",
  "status": "processing",
  "total": 100,
  "message": "Batch processing started"
}
```

**Use Case**: Process large volumes of transactions efficiently. Check status with `/task/status/{task_id}`.

---

#### `GET /task/status/{task_id}`
Check the status of an async batch processing task.

**Response**:
```json
{
  "task_id": "batch-abc123def",
  "status": "completed",
  "progress": {
    "total": 100,
    "completed": 100,
    "fraud_detected": 8,
    "elapsed_seconds": 45.2
  }
}
```

---

### 1.2 Advanced Prompting Patterns

These endpoints demonstrate different prompting techniques for fraud analysis.

#### `POST /analyze/react`
Analyze using **ReAct** (Reasoning + Acting) pattern - interleaves thought and action steps.

**Description**: The agent reasons about what to do next, executes tools (risk scoring, policy lookup), and combines insights iteratively over 5+ cycles.

**Request**: Same as `/analyze`

**Response**:
```json
{
  "pattern": "ReAct",
  "result": {
    "is_fraud": true,
    "risk_score": 88.5,
    "confidence": 0.91,
    "reasoning_trace": [
      "Thought: Need to check transaction amount against policy",
      "Action: query_fraud_policy -> threshold_exceeded: True",
      "Thought: Check account history for similar patterns",
      "Action: check_history -> no similar legitimate transactions",
      "Thought: Calculate final risk score",
      "Action: calculate_risk_score -> 88.5 (HIGH)"
    ]
  },
  "steps_taken": 6
}
```

**Use Case**: Transparent reasoning for explainable AI requirements. Best for complex fraud patterns requiring multi-step investigation.

---

#### `POST /analyze/cot`
Analyze using **Chain-of-Thought** (CoT) reasoning.

**Description**: LLM breaks down fraud detection into explicit intermediate reasoning steps before reaching a decision.

**Response**:
```json
{
  "pattern": "ChainOfThought",
  "result": {
    "is_fraud": true,
    "risk_score": 92.0,
    "reasoning_chain": [
      "Step 1: Transaction is CASH_OUT for $95,000",
      "Step 2: Drains 95% of account balance (95,000/100,000)",
      "Step 3: Destination balance remains 0 after transaction",
      "Step 4: Money disappears without arriving at destination",
      "Step 5: Pattern matches fraud indicator: money laundering",
      "Conclusion: HIGH RISK - Recommend blocking"
    ]
  },
  "reasoning_steps": 6
}
```

**Use Case**: Systematic reasoning for high-stakes decisions. Increases accuracy through explicit step-by-step analysis.

---

#### `POST /analyze/tot`
Analyze using **Tree-of-Thought** (ToT) - explores multiple parallel reasoning paths.

**Description**: Evaluates different fraud hypotheses simultaneously (e.g., account takeover, money laundering, legitimate transaction), scores each path, selects the most promising.

**Response**:
```json
{
  "pattern": "TreeOfThought",
  "result": {
    "is_fraud": true,
    "risk_score": 85.0,
    "best_path": "money_laundering_hypothesis",
    "paths_explored": 3,
    "path_scores": {
      "account_takeover": 0.72,
      "money_laundering_hypothesis": 0.89,
      "legitimate_withdrawal": 0.15
    }
  }
}
```

**Use Case**: Ambiguous cases requiring exploration of alternative explanations before commitment.

---

#### `POST /analyze/debate`
Analyze using **Adversarial Debate** pattern.

**Description**: Three LLM agents debate: Prosecutor argues it IS fraud, Defense argues it's legitimate, Judge evaluates and renders verdict.

**Response**:
```json
{
  "pattern": "Debate",
  "result": {
    "is_fraud": true,
    "risk_score": 87.5,
    "prosecutor_score": 9.2,
    "defense_score": 4.1,
    "judge_reasoning": "Prosecutor presented stronger evidence: balance drain 95%, destination account suspicious, no prior transaction history.",
    "verdict": "FRAUD"
  },
  "debate_rounds": 2,
  "arguments_count": 6
}
```

**Use Case**: Reduces confirmation bias by forcing consideration of counterarguments. Excellent for edge cases.

---

#### `POST /analyze/self-critique`
Analyze using **Self-Critique** iterative refinement.

**Description**: Generate initial assessment → critique own reasoning for flaws → revise decision based on critique (2-3 iterations).

**Response**:
```json
{
  "pattern": "SelfCritique",
  "result": {
    "is_fraud": true,
    "risk_score": 91.0,
    "iterations": 2,
    "initial_decision": {"is_fraud": false, "risk_score": 45.0},
    "critique": "Overlooked destination balance anomaly - money didn't arrive",
    "final_decision": {"is_fraud": true, "risk_score": 91.0}
  },
  "revisions": 1
}
```

**Use Case**: Error correction through self-reflection. Improves accuracy by catching initial mistakes.

---

#### `POST /analyze/reflection`
Validate existing decision using **Reflection** pattern.

**Description**: Reflect on a fraud decision against policies and reasoning chains to catch errors or confirm correctness.

**Request**:
```json
{
  "transaction": {...},
  "initial_decision": {
    "is_fraud": true,
    "risk_score": 88.5,
    "confidence": 0.87,
    "reasoning": "Large transfer draining 91% of origin balance"
  }
}
```

**Response**:
```json
{
  "pattern": "Reflection",
  "result": {
    "decision": {"is_fraud": true, "risk_score": 93.0},
    "reflections": [
      "Reconsidered destination account anomaly",
      "Updated confidence: 0.93"
    ],
    "iterations": 2
  },
  "should_escalate": false
}
```

**Use Case**: Quality assurance layer for validating automated decisions before execution.

---

### 1.3 Agent-Based Analysis

Multi-agent systems for sophisticated fraud detection.

#### `POST /agents/single`
Single autonomous agent with complete reasoning loop.

**Description**: 
1. **Observation**: Parse transaction and identify anomalies
2. **Planning**: Create execution plan
3. **Execution**: Run tools (risk scoring, policy lookup, history check)
4. **Reasoning**: Chain-of-thought analysis
5. **Decision**: Make fraud determination
6. **Reflection**: Self-critique and escalation logic

**Request**:
```json
{
  "transaction_id": "TX_AGENT_001",
  "amount": 165000.0,
  "type": "TRANSFER",
  "oldbalanceOrg": 180000.0,
  "newbalanceOrig": 15000.0,
  "oldbalanceDest": 5000.0,
  "newbalanceDest": 170000.0,
  "nameOrig": "C1231231230",
  "nameDest": "C9879879870"
}
```

**Response**:
```json
{
  "agent_type": "single",
  "transaction_id": "TX_AGENT_001",
  "is_fraud": true,
  "risk_score": 85.0,
  "risk_level": "HIGH",
  "confidence": 0.89,
  "explanation": "Transaction exceeds policy threshold and balance drain is critical",
  "observations": [
    "TRANSFER transaction for $165,000",
    "Balance drain: 91.7% of origin account",
    "Destination account receives 97% of transfer amount"
  ],
  "anomalies": [
    "High-value transaction",
    "Significant balance drain",
    "Exceeds fraud policy threshold (>$100k)"
  ],
  "reasoning_steps": [
    "Analyzed transaction type: TRANSFER (risk factor)",
    "Calculated balance drain: 91.7% (critical)",
    "Queried fraud policy: Exceeds $100k threshold",
    "Evaluated destination account: Suspicious pattern"
  ],
  "tool_results": {
    "query_fraud_policy": {"threshold_exceeded": true, "policy": "TRANSFER > 100k = high risk"},
    "calculate_risk_score": {"risk_score": 85.0, "factors": ["high_amount", "balance_drain"]}
  },
  "should_escalate": true,
  "escalation_reason": "High-value fraud detection requires manual review",
  "self_critique": "Decision is well-supported by evidence and policy compliance",
  "total_steps": 6,
  "termination_reason": "Decision reached with high confidence",
  "execution_time": 142.5
}
```

**Use Case**: Autonomous fraud detection with full transparency into reasoning process. Ideal for production deployments requiring explainability.

---

#### `POST /agents/manager-worker`
Manager-worker hierarchical system.

**Description**: Manager agent decomposes complex analysis into subtasks, delegates to specialized worker agents, aggregates results.

**Use Case**: Complex fraud investigations requiring multiple specialized perspectives (risk analysis, policy compliance, behavioral analysis).

---

#### `POST /agents/planner-executor-critic`
Three-phase agent system with planning, execution, and critique.

**Description**:
- **Planner**: Strategizes investigation approach
- **Executor**: Carries out investigation steps
- **Critic**: Reviews findings and validates conclusions

**Use Case**: High-assurance scenarios requiring systematic investigation and validation.

---

#### `POST /agents/debate-system`
Multi-agent debate system.

**Description**: Multiple agents argue different positions (fraud vs. legitimate), moderator synthesizes consensus.

**Use Case**: Contentious cases where evidence points in multiple directions.

---

#### `POST /agents/role-specialized`
Role-specialized agent ensemble.

**Description**: Each agent has a specialized role (risk analyst, compliance officer, behavioral expert), results are aggregated.

**Use Case**: Comprehensive analysis requiring domain expertise from multiple perspectives.

---

#### `POST /agents/swarm`
Emergent behavior swarm system.

**Description**: Multiple simple agents interact to produce emergent fraud detection patterns through collective intelligence.

**Use Case**: Novel fraud pattern discovery and adaptive detection.

---

### 1.4 Prompt Engineering Utilities

#### `GET /prompts/templates`
List all registered prompt templates with versioning.

**Response**:
```json
{
  "templates": [
    {
      "name": "fraud_analysis_v1",
      "version": "1.0",
      "description": "Standard fraud analysis prompt",
      "variables": ["transaction_id", "amount", "type"]
    }
  ]
}
```

---

#### `POST /prompts/build`
Build hierarchical prompt with system/developer/user structure.

**Request**:
```json
{
  "transaction_id": "TX_PROMPT_001",
  "amount": 185000.0,
  "type": "TRANSFER",
  "nameOrig": "C1234567890",
  "nameDest": "C9876543210"
}
```

**Response**:
```json
{
  "full_prompt": "System: You are a fraud detection specialist...\n\nDeveloper: Use these fraud policies...\n\nUser: Analyze transaction TX_PROMPT_001...",
  "few_shot_examples_count": 3,
  "estimated_tokens": 972
}
```

**Use Case**: Construct optimized prompts for LLM calls. Uses ChromaDB to retrieve relevant few-shot examples.

---

#### `GET /prompts/few-shot-examples`
Get curated few-shot learning examples from ChromaDB.

**Query Parameters**:
- `count` (int): Number of examples to retrieve (default: 5)
- `ensure_diversity` (bool): Ensure examples cover different fraud types (default: true)

**Response**:
```json
{
  "examples": [
    {
      "transaction": {...},
      "is_fraud": true,
      "explanation": "CASH_OUT draining account to zero"
    }
  ],
  "count": 5,
  "formatted": "Example 1:\nTransaction: CASH_OUT $95k...\nFraud: YES\n\n..."
}
```

**Use Case**: Retrieve examples from the `fraud_explanations` ChromaDB collection for few-shot prompting.

---

#### `POST /prompts/compress`
Compress prompt to fit token budget while preserving critical information.

**Request**:
```json
{
  "text": "You are a fraud detection expert with 15 years of experience...",
  "max_tokens": 800
}
```

**Response**:
```json
{
  "original_length": 1243,
  "compressed_length": 587,
  "compression_ratio": 0.47,
  "estimated_tokens": 146,
  "compressed_text": "Fraud expert: Analyze TX for risk..."
}
```

**Use Case**: Optimize prompts for latency and cost reduction.

---

#### `GET /prompts/output-schema`
Get JSON schema specification for fraud decision output.

**Response**:
```json
{
  "schema": {
    "schema_name": "FraudDecisionSchema",
    "required_fields": ["is_fraud", "risk_score", "confidence", "explanation"],
    "example_output": {
      "is_fraud": true,
      "risk_score": 85.0,
      "confidence": 0.89,
      "risk_level": "HIGH",
      "explanation": "..."
    }
  },
  "formatted_prompt": "Return JSON with these fields: ..."
}
```

---

#### `POST /prompts/validate-output`
Validate LLM output against expected schema.

**Request**:
```json
{
  "output": {
    "is_fraud": true,
    "risk_score": 92,
    "confidence": 0.88,
    "risk_level": "CRITICAL",
    "explanation": "Large transfer draining account"
  }
}
```

**Response**:
```json
{
  "is_valid": true,
  "error": null,
  "schema_name": "FraudDecisionSchema"
}
```

---

#### `GET /prompts/role-playing`
Get role-playing instruction for fraud specialist persona.

**Response**:
```json
{
  "role": "Fraud Detection Specialist",
  "prompt": "You are a Certified Fraud Examiner with expertise in financial crime detection...",
  "benefits": [
    "Better alignment with expert behavior",
    "More structured analysis",
    "Clearer explanations",
    "Systematic evidence gathering"
  ]
}
```

---

### 1.5 State Management & Sessions

#### `POST /analyze/stateful`
Analyze transaction with session state management.

**Description**: Maintains conversation state across multiple fraud investigations. Uses ChromaDB episodic memory to recall previous decisions.

**Use Case**: Interactive fraud investigation workflows requiring context from prior transactions.

---

#### `GET /session/{session_id}`
Retrieve session state and history.

**Response**:
```json
{
  "session_id": "sess_abc123",
  "transactions_analyzed": 15,
  "fraud_detected": 3,
  "session_start": "2026-01-15T10:00:00Z",
  "last_activity": "2026-01-15T10:45:00Z"
}
```

---

#### `GET /session/{session_id}/checkpoints`
Get session checkpoints for recovery.

**Response**:
```json
{
  "session_id": "sess_abc123",
  "checkpoints": [
    {
      "checkpoint_id": "cp_001",
      "timestamp": "2026-01-15T10:30:00Z",
      "state": {...}
    }
  ]
}
```

---

#### `POST /session/{session_id}/resume`
Resume from session checkpoint after interruption.

**Use Case**: Fault tolerance for long-running fraud investigations.

---

### 1.6 System Monitoring

#### `GET /stats`
Get async processing statistics.

**Response**:
```json
{
  "total_tasks": 1523,
  "completed": 1498,
  "failed": 12,
  "pending": 13,
  "avg_processing_time_ms": 87.3,
  "fraud_detection_rate": 0.034
}
```

---

#### `GET /circuit-breakers`
Get circuit breaker status for fault tolerance.

**Response**:
```json
{
  "llm_service": {
    "state": "CLOSED",
    "failure_count": 2,
    "last_failure": "2026-01-15T09:30:00Z"
  },
  "chromadb_service": {
    "state": "CLOSED",
    "failure_count": 0
  }
}
```

---

## 2. LLM Engineering API

**Base Path**: `/api/v1/llm`

### 2.1 Token Analysis

#### `GET /token-analysis`
Analyze token usage and context window validation.

**Query Parameters**:
- `prompt` (str): Prompt text to analyze
- `max_tokens` (int, optional): Override max token limit

**Response**:
```json
{
  "token_count": 1243,
  "max_tokens": 4096,
  "context_usage_percent": 30.3,
  "is_within_limit": true,
  "optimization_suggestions": [
    "Remove redundant phrases",
    "Use abbreviations for common terms"
  ],
  "complexity": "medium"
}
```

**Use Case**: Pre-flight validation before LLM calls to ensure prompts fit within context windows.

---

### 2.2 Sampling Configuration

#### `POST /test-sampling`
Test different sampling configurations with self-consistency.

**Query Parameters**:
- `sampling_mode` (str): "deterministic", "balanced", "creative"
- `num_samples` (int): Number of samples to generate (1-10)

**Request Body**:
```json
{
  "transaction_id": "TX_SAMPLE_001",
  "type": "TRANSFER",
  "amount": 125000.0,
  "oldbalanceOrg": 150000.0,
  "newbalanceOrig": 25000.0
}
```

**Response**:
```json
{
  "transaction_id": "TX_SAMPLE_001",
  "sampling_config": {
    "temperature": 0.0,
    "top_p": 1.0,
    "top_k": 50,
    "seed": 42,
    "mode": "deterministic"
  },
  "num_samples": 3,
  "samples": [
    "YES - High risk transfer",
    "YES - Suspicious balance drain",
    "YES - Policy violation"
  ],
  "majority_vote": {
    "result": "YES",
    "confidence": 1.0,
    "consensus": true
  },
  "tradeoffs": {
    "deterministic": "Reproducible but less creative",
    "balanced": "Good tradeoff between consistency and diversity",
    "creative": "Diverse outputs but less predictable"
  }
}
```

**Use Case**: 
- **Deterministic** (temp=0.0): Classification tasks requiring consistency
- **Balanced** (temp=0.7): Fraud explanations needing creativity with control
- **Creative** (temp=0.9): Brainstorming alternative fraud scenarios

---

### 2.3 Model Routing

#### `POST /model-routing`
Get intelligent model routing recommendation based on complexity.

**Request Body**: Same as transaction analysis

**Response**:
```json
{
  "transaction_id": "TX_ROUTE_001",
  "selected_model": "gpt-4",
  "complexity_score": 8.5,
  "reasoning": "High-value transaction ($165k) with complex balance patterns requires advanced reasoning",
  "alternatives": [
    {
      "model": "gpt-3.5-turbo",
      "latency_ms": 450,
      "cost_per_1k_tokens": 0.002,
      "quality_score": 0.75
    },
    {
      "model": "gpt-4",
      "latency_ms": 1200,
      "cost_per_1k_tokens": 0.03,
      "quality_score": 0.95
    }
  ],
  "latency_estimate_ms": 1200,
  "cost_estimate": 0.036
}
```

**Routing Logic**:
- **Simple cases** (amount < $10k, standard types): GPT-3.5-turbo (fast, cheap)
- **Medium complexity** (amount $10k-$100k): GPT-4-turbo
- **High complexity** (amount > $100k, anomalies): GPT-4 (best quality)

**Use Case**: Balance latency, cost, and quality based on transaction complexity.

---

#### `GET /cache-stats`
Get caching effectiveness statistics.

**Response**:
```json
{
  "cache_stats": {
    "hits": 1523,
    "misses": 287,
    "hit_rate": 0.841,
    "pattern_cache_ttl": 3600
  },
  "caching_enabled": true,
  "ttl_seconds": 3600
}
```

**Use Case**: Monitor caching for latency optimization. Fraud patterns and policies are cached for 1 hour.

---

### 2.4 Safety & Guardrails

#### `POST /test-safety`
Test LLM safety mechanisms: hallucination detection, prompt injection prevention, refusal handling.

**Request**:
```json
{
  "transaction": {...},
  "llm_response": "This transaction is DEFINITELY fraud because the customer is from Nigeria and everyone knows Nigerian transactions are scams."
}
```

**Response**:
```json
{
  "hallucination_detected": true,
  "injection_detected": false,
  "refusal_detected": false,
  "hallucinations": [
    {
      "type": "unsupported_claim",
      "severity": "critical",
      "text": "customer is from Nigeria",
      "reason": "Geographic origin is not in transaction data"
    },
    {
      "type": "bias",
      "severity": "critical",
      "text": "Nigerian transactions are scams",
      "reason": "Discriminatory generalization"
    }
  ],
  "injections": [],
  "recommendation": "reject"
}
```

**Safety Checks**:
1. **Hallucination Detection**: Verify claims against transaction data
2. **Prompt Injection**: Detect attempts to manipulate LLM behavior
3. **Refusal Detection**: Handle cases where LLM refuses to answer

**Recommendations**:
- `accept`: Safe to use
- `review`: Manual review recommended
- `sanitize`: Clean before use
- `fallback_to_rules`: Use rule-based system
- `reject`: Discard completely

**Use Case**: Production safety guardrails to prevent biased, hallucinated, or manipulated fraud decisions.

---

#### `POST /prompt-compression`
Compress prompts for latency optimization.

**Query Parameters**:
- `prompt` (str): Prompt to compress

**Response**:
```json
{
  "original_tokens": 1543,
  "compressed_tokens": 687,
  "reduction_percent": 55.4,
  "compressed_prompt": "Fraud analyst: TX_001 TRANSFER $125k origin $150k→$25k dest $10k→$135k. Fraud?",
  "techniques_used": [
    "Removed filler words",
    "Abbreviated common terms",
    "Preserved critical data"
  ]
}
```

**Use Case**: Reduce latency and cost for high-frequency fraud detection calls.

---

## 3. Memory System API

**Base Path**: `/memory`

### 3.1 Task Tracking

#### `POST /task/start`
Start tracking a new fraud investigation task.

**Request**:
```json
{
  "task_id": "task_fraud_inv_001",
  "task_type": "fraud_investigation",
  "description": "Investigate suspicious transaction pattern for customer C1234567890"
}
```

**Response**:
```json
{
  "task_id": "task_fraud_inv_001",
  "status": "started",
  "start_time": "2026-01-15T10:00:00Z"
}
```

---

#### `POST /task/complete`
Mark task as completed with results.

**Request**:
```json
{
  "task_id": "task_fraud_inv_001",
  "result": {
    "fraud_confirmed": true,
    "total_amount": 485000.0,
    "transactions_flagged": 7
  }
}
```

---

#### `POST /reasoning/step`
Record a reasoning step in ongoing investigation.

**Request**:
```json
{
  "task_id": "task_fraud_inv_001",
  "step_number": 1,
  "thought": "Need to check transaction amount against policy threshold",
  "action": "query_fraud_policy",
  "observation": "Threshold exceeded: $125k > $100k limit"
}
```

**Use Case**: Build reasoning chains for explainable AI and audit trails.

---

#### `POST /tool/call`
Record tool call for provenance tracking.

**Request**:
```json
{
  "tool_name": "calculate_risk_score",
  "arguments": {"transaction_id": "TX_001"},
  "result": {"risk_score": 85.0, "factors": ["high_amount", "balance_drain"]}
}
```

---

### 3.2 Episodic Memory

#### `POST /episodic/store`
Store episodic memory (specific events/experiences) in ChromaDB.

**Request**:
```json
{
  "memory_id": "ep_fraud_case_001",
  "content": "Detected fraud: CASH_OUT $95k draining account to zero. Customer attempted to dispute but evidence was conclusive.",
  "metadata": {
    "transaction_id": "TX_12345",
    "customer_id": "C1234567890",
    "fraud_type": "account_drain",
    "resolution": "blocked",
    "timestamp": "2026-01-15T10:00:00Z"
  },
  "importance": 0.95
}
```

**Response**:
```json
{
  "memory_id": "ep_fraud_case_001",
  "stored_at": "2026-01-15T10:00:01Z",
  "collection": "episodic_memory",
  "status": "success"
}
```

**Use Case**: Store specific fraud cases for later retrieval. Enables "have we seen this before?" queries.

---

### 3.3 Semantic Memory

#### `POST /semantic/store`
Store semantic memory (general knowledge/patterns) in ChromaDB.

**Request**:
```json
{
  "memory_id": "sem_pattern_cashout_fraud",
  "content": "CASH_OUT transactions > $80k with destination balance = 0 are highly indicative of money laundering (95% fraud rate in historical data).",
  "metadata": {
    "category": "fraud_pattern",
    "confidence": 0.95,
    "evidence_count": 1523
  }
}
```

**Use Case**: Store learned fraud patterns and general knowledge. Enhances policy retrieval from ChromaDB.

---

### 3.4 Memory Retrieval

#### `POST /retrieve`
Hybrid search across episodic and semantic memory.

**Request**:
```json
{
  "query": "CASH_OUT transaction draining account",
  "memory_types": ["episodic", "semantic"],
  "limit": 5
}
```

**Response**:
```json
{
  "results": [
    {
      "memory_id": "ep_fraud_case_001",
      "type": "episodic",
      "content": "Detected fraud: CASH_OUT $95k...",
      "relevance_score": 0.92,
      "metadata": {...}
    },
    {
      "memory_id": "sem_pattern_cashout_fraud",
      "type": "semantic",
      "content": "CASH_OUT transactions > $80k...",
      "relevance_score": 0.89
    }
  ],
  "total": 2
}
```

**Use Case**: Retrieve relevant past experiences and learned patterns during fraud analysis. Augments ChromaDB fraud_cases collection.

---

#### `POST /search/hybrid`
Advanced hybrid search combining semantic and keyword matching.

**Request**:
```json
{
  "query": "high-value transfer with balance inconsistency",
  "filters": {
    "fraud_type": ["account_takeover", "money_laundering"],
    "amount_min": 100000.0
  },
  "limit": 10,
  "semantic_weight": 0.7,
  "keyword_weight": 0.3
}
```

**Use Case**: Precise retrieval with filtering for targeted fraud investigations.

---

#### `POST /search/contextual`
Context-aware search using current investigation state.

**Request**:
```json
{
  "query": "similar fraud patterns",
  "context": {
    "current_transaction": {...},
    "current_findings": [...],
    "investigation_stage": "evidence_gathering"
  }
}
```

**Use Case**: Retrieve memories relevant to current investigation context.

---

### 3.5 Procedural Memory

#### `POST /procedural/record`
Record successful procedure/workflow.

**Request**:
```json
{
  "procedure_id": "proc_high_value_investigation",
  "steps": [
    "Check transaction amount against policy",
    "Calculate balance drain percentage",
    "Query fraud history for customer",
    "Evaluate destination account pattern",
    "Make fraud determination"
  ],
  "success_rate": 0.94,
  "avg_execution_time_ms": 850
}
```

**Use Case**: Learn and optimize fraud investigation workflows.

---

#### `POST /procedural/chain`
Record reasoning chain for reuse.

**Request**:
```json
{
  "chain_id": "chain_cashout_analysis",
  "reasoning_steps": [
    "Observe: CASH_OUT transaction",
    "Check: Amount > $80k threshold",
    "Verify: Destination balance = 0",
    "Conclude: High fraud probability"
  ],
  "effectiveness_score": 0.91
}
```

**Use Case**: Capture successful reasoning patterns for future cases.

---

### 3.6 Working Memory

#### `POST /working/put`
Store temporary data in working memory (short-term).

**Request**:
```json
{
  "key": "current_investigation_focus",
  "value": "balance_inconsistency",
  "metadata": {"priority": "high"}
}
```

---

#### `GET /working/get/{key}`
Retrieve from working memory.

**Response**:
```json
{
  "key": "current_investigation_focus",
  "value": "balance_inconsistency",
  "metadata": {"priority": "high"},
  "ttl_remaining_seconds": 285
}
```

---

#### `DELETE /working/clear`
Clear working memory for fresh start.

---

### 3.7 Memory Statistics

#### `GET /stats`
Get memory system statistics.

**Response**:
```json
{
  "episodic_memories": 15234,
  "semantic_memories": 487,
  "procedural_patterns": 23,
  "working_memory_items": 12,
  "total_retrievals": 45231,
  "avg_retrieval_time_ms": 45.3
}
```

---

#### `GET /short-term`
Get recent short-term memory contents.

**Response**:
```json
{
  "recent_memories": [
    {
      "memory_id": "ep_recent_001",
      "content": "Analyzed TX_001: fraud detected",
      "timestamp": "2026-01-15T10:45:00Z"
    }
  ],
  "count": 1
}
```

---

#### `GET /working/stats`
Get working memory statistics.

**Response**:
```json
{
  "total_items": 12,
  "capacity": 100,
  "utilization_percent": 12.0,
  "oldest_item_age_seconds": 287,
  "newest_item_age_seconds": 5
}
```

---

### 3.8 Search Optimization

#### `POST /index/build`
Build search index for a memory collection.

**Request**:
```json
{
  "collection": "episodic_memory"
}
```

**Response**:
```json
{
  "collection": "episodic_memory",
  "index_built": true,
  "documents_indexed": 15234,
  "build_time_seconds": 12.4
}
```

**Use Case**: Optimize retrieval performance for large memory collections.

---

## 4. Data Pipeline Integration

### How APIs Use Prepared Data

The core APIs leverage data prepared by the pipeline scripts:

#### ChromaDB Collections (from `vectorize_data.py`):
1. **`fraud_cases` (500 docs)**: Used by `/prompts/few-shot-examples` and `/memory/retrieve` for case-based reasoning
2. **`fraud_policies` (32 docs)**: Retrieved by agents during `/analyze/react` and `/agents/single` for policy compliance
3. **`fraud_explanations` (100 docs)**: Used by `/prompts/build` for few-shot examples and explanation templates
4. **`transaction_patterns` (7 docs)**: Pattern matching during all `/analyze/*` endpoints

#### Processed Data Files:
- **`paysim_cleaned.csv`**: Training data for risk scoring models
- **Balanced datasets**: Used by `/batch` processing for batch fraud detection
- **Weak supervision labels**: Ground truth for model validation
- **Bias audit results**: Inform safety checks in `/test-safety`

---

## 5. Common Workflows

### Workflow 1: Real-Time Fraud Detection
```
1. POST /api/v1/fraud/analyze
   → Analyzes transaction
   → Queries ChromaDB for fraud policies and cases
   → Returns fraud decision

2. POST /memory/episodic/store
   → Stores case for future reference
```

### Workflow 2: Batch Processing
```
1. POST /api/v1/fraud/batch
   → Returns task_id

2. GET /api/v1/fraud/task/status/{task_id}
   → Poll until complete

3. Retrieve results from task
```

### Workflow 3: Explainable Investigation
```
1. POST /api/v1/fraud/analyze/react
   → Get reasoning trace

2. POST /api/v1/fraud/analyze/reflection
   → Validate decision

3. POST /memory/reasoning/step
   → Store reasoning for audit
```

### Workflow 4: Safety-First Analysis
```
1. POST /api/v1/llm/test-safety (pre-check)
   → Validate input

2. POST /api/v1/fraud/analyze
   → Perform analysis

3. POST /api/v1/llm/test-safety (post-check)
   → Validate LLM output

4. POST /prompts/validate-output
   → Schema validation
```

---

## 6. Error Handling

All endpoints follow consistent error response format:

```json
{
  "detail": "Transaction analysis failed: Timeout connecting to ChromaDB",
  "status_code": 503,
  "timestamp": "2026-01-15T10:00:00Z",
  "request_id": "req_abc123def"
}
```

**Common HTTP Status Codes**:
- `200`: Success
- `400`: Invalid request (e.g., missing required fields)
- `503`: Service unavailable (e.g., ChromaDB connection timeout)
- `500`: Internal server error
- `429`: Rate limit exceeded

---

## 7. Authentication & Rate Limiting

**Coming Soon**: Currently all endpoints are open for development. Production deployment will include:
- API key authentication
- Rate limiting (100 req/min for `/analyze`, 10 req/min for batch)
- Role-based access control (RBAC)

---

## 8. Performance Characteristics

| Endpoint | Avg Latency | p95 Latency | Throughput |
|----------|-------------|-------------|------------|
| `/analyze` | 105ms | 250ms | 500 req/s |
| `/batch` | 45ms (async) | 80ms | 1000 req/s |
| `/analyze/react` | 1.2s | 2.5s | 50 req/s |
| `/agents/single` | 850ms | 1.8s | 75 req/s |
| `/memory/retrieve` | 45ms | 120ms | 800 req/s |
| `/prompts/build` | 230ms | 450ms | 200 req/s |

---

## 9. API Testing

Use the provided Swagger UI:
```
http://localhost:8000/docs
```

Or use `curl`:
```bash
# Simple fraud analysis
curl -X POST http://localhost:8000/api/v1/fraud/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "transaction": {
      "transaction_id": "TX_TEST_001",
      "type": "TRANSFER",
      "amount": 125000.0,
      "oldbalanceOrg": 150000.0,
      "newbalanceOrig": 25000.0,
      "oldbalanceDest": 10000.0,
      "newbalanceDest": 135000.0
    }
  }'

# ReAct analysis
curl -X POST http://localhost:8000/api/v1/fraud/analyze/react \
  -H "Content-Type: application/json" \
  -d '{
    "transaction": {...}
  }'

# Memory retrieval
curl -X POST http://localhost:8000/memory/retrieve \
  -H "Content-Type: application/json" \
  -d '{
    "query": "CASH_OUT fraud pattern",
    "memory_types": ["episodic", "semantic"],
    "limit": 5
  }'
```

---

## 10. Next Steps

1. **Start Backend**: `cd backend && poetry run python -m app.main`
2. **Verify ChromaDB**: Ensure running on `localhost:8001`
3. **Test API**: Visit `http://localhost:8000/docs`
4. **Run Sample Analysis**: Use `/analyze` endpoint with test transaction
5. **Monitor Performance**: Check `/stats` and `/circuit-breakers`

---

**Last Updated**: 2026-01-15  
**API Version**: v1  
**Backend Framework**: FastAPI 0.115.6  
**Python Version**: 3.12+
