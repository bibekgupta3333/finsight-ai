# Quick Reference: Advanced Prompting Patterns API

## 🚀 Getting Started

All endpoints are available at: `http://localhost:8000/api/v1/fraud/`

### Check Server Health
```bash
curl http://localhost:8000/health
```

---

## 📋 Prompt Templates

### List All Templates
```bash
curl http://localhost:8000/api/v1/fraud/prompts/templates
```

**Response:**
```json
{
  "templates": [
    {
      "template_id": "system_v1",
      "level": "system",
      "version": "1.0.0",
      "active": true,
      "constraint_count": 5
    }
  ]
}
```

---

## 🏗️ Build Hierarchical Prompt

### Build Full Prompt with Few-Shot Examples
```bash
curl -X POST http://localhost:8000/api/v1/fraud/prompts/build \
  -H "Content-Type: application/json" \
  -d '{
    "transaction_id": "TX123",
    "type": "TRANSFER",
    "amount": 500000.0,
    "oldbalanceOrg": 500000.0,
    "newbalanceOrig": 0.0,
    "oldbalanceDest": 0.0,
    "newbalanceDest": 0.0,
    "nameOrig": "C123456789",
    "nameDest": "C987654321"
  }'
```

**Response:**
```json
{
  "full_prompt": "=== SYSTEM PROMPT ===\n...",
  "few_shot_examples_count": 3,
  "estimated_tokens": 1002,
  "prompt_levels": ["SYSTEM", "DEVELOPER", "USER"]
}
```

---

## 🧠 Reasoning Patterns

### 1. ReAct (Reasoning + Acting)
Thought → Action → Observation loop with tool calls

```bash
curl -X POST http://localhost:8000/api/v1/fraud/analyze/react \
  -H "Content-Type: application/json" \
  -d '{
    "transaction": {
      "transaction_id": "TX123",
      "type": "TRANSFER",
      "amount": 500000.0,
      "oldbalanceOrg": 500000.0,
      "newbalanceOrig": 0.0
    }
  }'
```

**Expected Response:**
```json
{
  "pattern": "ReAct",
  "steps_taken": 5,
  "result": {
    "decision": {"is_fraud": true, "risk_score": 95},
    "trace": [
      {
        "step": 1,
        "thought": "Large transfer draining account...",
        "action": "calculate_risk_score",
        "observation": "Risk score: 95"
      }
    ]
  }
}
```

---

### 2. Chain-of-Thought (CoT)
Step-by-step reasoning with validation

```bash
curl -X POST http://localhost:8000/api/v1/fraud/analyze/cot \
  -H "Content-Type: application/json" \
  -d '{
    "transaction": {
      "transaction_id": "TX123",
      "type": "TRANSFER",
      "amount": 500000.0
    }
  }'
```

**Expected Response:**
```json
{
  "pattern": "Chain-of-Thought",
  "reasoning_steps": 5,
  "result": {
    "decision": {"is_fraud": true},
    "steps": [
      {"step": 1, "reasoning": "Check transaction type..."},
      {"step": 2, "reasoning": "Analyze amount..."},
      {"step": 3, "reasoning": "Check balance changes..."}
    ]
  }
}
```

---

### 3. Tree-of-Thought (ToT)
Explore multiple reasoning paths, select best

```bash
curl -X POST http://localhost:8000/api/v1/fraud/analyze/tot \
  -H "Content-Type: application/json" \
  -d '{
    "transaction": {
      "transaction_id": "TX123",
      "type": "TRANSFER",
      "amount": 500000.0
    }
  }'
```

**Expected Response:**
```json
{
  "pattern": "Tree-of-Thought",
  "paths_explored": 12,
  "result": {
    "tree_depth": 3,
    "score": 0.95,
    "best_path": ["node1", "node4", "node7"],
    "decision": {"is_fraud": true}
  }
}
```

---

### 4. Debate Pattern
Prosecutor vs Defense vs Judge

```bash
curl -X POST http://localhost:8000/api/v1/fraud/analyze/debate \
  -H "Content-Type: application/json" \
  -d '{
    "transaction": {
      "transaction_id": "TX123",
      "type": "TRANSFER",
      "amount": 500000.0
    }
  }'
```

**Expected Response:**
```json
{
  "pattern": "Debate",
  "debate_rounds": 3,
  "arguments_count": 6,
  "result": {
    "arguments": [
      {
        "round": 1,
        "position": "prosecutor",
        "argument": "Amount is suspiciously high..."
      },
      {
        "round": 1,
        "position": "defense",
        "argument": "Large transfers can be legitimate..."
      }
    ],
    "final_decision": {
      "is_fraud": true,
      "verdict": "Prosecutor wins",
      "reasoning": "..."
    }
  }
}
```

---

### 5. Self-Critique Pattern
Generate → Critique → Revise

```bash
curl -X POST http://localhost:8000/api/v1/fraud/analyze/self-critique \
  -H "Content-Type: application/json" \
  -d '{
    "transaction": {
      "transaction_id": "TX123",
      "type": "TRANSFER",
      "amount": 500000.0
    }
  }'
```

**Expected Response:**
```json
{
  "pattern": "Self-Critique",
  "revisions": 2,
  "result": {
    "initial_analysis": {"is_fraud": true, "reasoning": "..."},
    "revisions": [
      {
        "iteration": 1,
        "critique": {
          "issues_found": ["Missing balance check"],
          "suggestions": ["Check newbalanceDest"]
        },
        "revised_analysis": {"is_fraud": true, "reasoning": "..."}
      }
    ],
    "final_analysis": {"is_fraud": true, "confidence": 0.95}
  }
}
```

---

### 6. Reflection Pattern
Validate against policies and reasoning

```bash
curl -X POST http://localhost:8000/api/v1/fraud/analyze/reflection \
  -H "Content-Type: application/json" \
  -d '{
    "transaction": {
      "transaction_id": "TX123",
      "type": "TRANSFER",
      "amount": 500000.0
    },
    "initial_decision": {
      "is_fraud": true,
      "risk_score": 85,
      "confidence": 0.95,
      "reasoning": "High-value transfer..."
    }
  }'
```

**Expected Response:**
```json
{
  "pattern": "Reflection",
  "should_escalate": false,
  "result": {
    "policy_alignment": {
      "aligned": true,
      "policies_checked": ["TRANSFER > 100k", "Balance inconsistencies"]
    },
    "reasoning_validation": {
      "valid": true,
      "chain_length": 3
    }
  }
}
```

---

## 🎯 Few-Shot Examples

### Get Curated Examples
```bash
curl "http://localhost:8000/api/v1/fraud/prompts/few-shot-examples?count=5&ensure_diversity=true"
```

**Response:**
```json
{
  "examples": [
    {
      "input": {"transaction_id": "TX1", "amount": 9000000.0},
      "output": {"is_fraud": true, "risk_score": 95},
      "reasoning": "Large transfer draining account...",
      "category": "clear_fraud",
      "difficulty": 1
    },
    {
      "input": {"transaction_id": "TX2", "amount": 150.0},
      "output": {"is_fraud": false, "risk_score": 5},
      "reasoning": "Small normal payment...",
      "category": "clear_legitimate",
      "difficulty": 1
    }
  ],
  "count": 5
}
```

---

## 📦 Prompt Compression

### Compress Long Prompt
```bash
curl -X POST http://localhost:8000/api/v1/fraud/prompts/compress \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Very long prompt text here...",
    "max_tokens": 500
  }'
```

**Response:**
```json
{
  "original_length": 2500,
  "compressed_length": 1800,
  "compression_ratio": 0.72,
  "estimated_tokens": 450,
  "compressed_text": "..."
}
```

---

## 📝 Output Schema & Validation

### Get Output Schema
```bash
curl http://localhost:8000/api/v1/fraud/prompts/output-schema
```

**Response:**
```json
{
  "schema": {
    "schema_name": "FraudDecision",
    "required_fields": ["is_fraud", "risk_score", "risk_level", "reasoning"],
    "field_types": {
      "is_fraud": "boolean",
      "risk_score": "float (0-100)",
      "risk_level": "string (LOW|MEDIUM|HIGH|CRITICAL)",
      "reasoning": "string",
      "confidence": "float (0.0-1.0)",
      "evidence": "array of strings"
    }
  }
}
```

### Validate LLM Output
```bash
curl -X POST http://localhost:8000/api/v1/fraud/prompts/validate-output \
  -H "Content-Type: application/json" \
  -d '{
    "output": {
      "is_fraud": true,
      "risk_score": 85,
      "risk_level": "CRITICAL",
      "reasoning": "High-value transfer...",
      "confidence": 0.95,
      "evidence": ["amount > 100k", "newbalanceDest = 0"]
    }
  }'
```

**Response:**
```json
{
  "is_valid": true,
  "error": null
}
```

**Invalid Example:**
```json
{
  "is_valid": false,
  "error": "Missing required field: risk_score"
}
```

---

## 🎭 Role-Playing Instructions

### Get Expert Persona Prompt
```bash
curl http://localhost:8000/api/v1/fraud/prompts/role-playing
```

**Response:**
```json
{
  "role": "Fraud Detection Specialist",
  "prompt": "You are an EXPERT FRAUD DETECTION SPECIALIST with:\n\nBACKGROUND:\n- 15 years experience...",
  "benefits": [
    "Better alignment with expert behavior",
    "More structured analysis",
    "Clearer explanations",
    "Systematic evidence gathering"
  ]
}
```

---

## 🧪 Testing All Patterns

### Run Complete Test Suite
```bash
cd /Users/bibekgupta/Documents/personal/bibek-portfolio/finsight-ai
python backend/scripts/test_prompt_patterns.py
```

**Expected Output:**
```
================================================================================
Advanced Prompting Patterns Test Suite
================================================================================
✓ Prompt Templates: PASS
✓ Hierarchical Prompt: PASS
✗ ReAct Pattern: FAIL (requires LLM API key)
✗ Chain-of-Thought: FAIL (requires LLM API key)
✗ Tree-of-Thought: FAIL (requires LLM API key)
✗ Debate Pattern: FAIL (requires LLM API key)
✗ Self-Critique: FAIL (requires LLM API key)
✗ Reflection: FAIL (requires LLM API key)
✓ Few-Shot Examples: PASS
✓ Prompt Compression: PASS
✓ Output Schema: PASS
✓ Output Validation: PASS
✓ Role-Playing: PASS

Results: 7/13 tests passed
```

---

## 🔧 Configuration

### LLM Client Setup

To enable full reasoning pattern execution, configure LLM client in `backend/app/services/llm_client.py`:

**Option 1: Local Ollama**
```python
# Ensure Ollama is running
docker-compose up -d

# Default configuration uses Ollama (localhost:11434)
# Models: mistral:latest, bge-small-en:latest
```

**Option 2: Cloud LLM (OpenAI/Anthropic)**
```python
# Set environment variables
export OPENAI_API_KEY="sk-..."
# or
export ANTHROPIC_API_KEY="sk-ant-..."

# Update llm_client.py to use cloud provider
```

---

## 📊 Performance Tips

### Token Optimization
- Use prompt compression for long contexts
- Select fewer few-shot examples (3-5 instead of 7)
- Set max_tokens for bounded responses

### Pattern Selection
- **Simple cases**: Use standard fraud analysis endpoint
- **Complex cases**: Use Chain-of-Thought or Debate
- **Uncertain cases**: Use Self-Critique or Reflection
- **Tool-requiring cases**: Use ReAct
- **Exploration**: Use Tree-of-Thought

### Caching
- Hierarchical prompts are cached (Redis TTL)
- Few-shot examples are cached
- Policy documents are cached

---

## 🐛 Troubleshooting

### 404 Not Found
- Ensure backend is running: `docker-compose ps`
- Restart backend: `docker-compose restart backend`

### 500 Internal Server Error (Reasoning Patterns)
- **Expected if LLM not configured**
- Check logs: `docker logs finsight-backend --tail 50`
- Verify LLM client setup

### 422 Validation Error
- Check request format matches endpoint signature
- Use examples above as templates

---

## 📚 Additional Resources

- **WBS Section 3.2**: `/docs/planning/WBS.md`
- **Completion Summary**: `/docs/SECTION-3.2-COMPLETION-SUMMARY.md`
- **Code Files**:
  - `/backend/app/core/prompt_manager.py`
  - `/backend/app/services/reasoning_patterns.py`
  - `/backend/app/services/prompt_engineering.py`
- **Test Script**: `/backend/scripts/test_prompt_patterns.py`

---

**Last Updated:** January 2, 2026
**Version:** 1.0.0
**Status:** Production Ready (pending LLM configuration)
