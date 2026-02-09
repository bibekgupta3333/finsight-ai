# Benchmark Suite for Fraud Detection

## Overview

This benchmark suite provides a comprehensive framework for evaluating and comparing different fraud detection approaches:

- **ML Models:** XGBoost, LightGBM, RandomForest
- **Heuristics:** Rule-based fraud detection
- **Agentic:** Single-agent and multi-agent LLM systems

## Quick Start

### 1. Run Quick Test (5 samples)

```bash
cd backend
python scripts/run_benchmarks.py --dataset quick_test --baselines xgboost lightgbm rule-based
```

### 2. Run Full Benchmark Suite

```bash
python scripts/run_benchmarks.py
```

### 3. Custom Configuration

```bash
python scripts/run_benchmarks.py --baselines lightgbm --dataset benchmark_suite --output my_results/
```

## Architecture

```
benchmarks/
├── config.yaml          # Configuration (baselines, datasets, metrics)
├── baselines.py         # Baseline evaluators (ML, Rule-based, Single-agent)
├── runner.py            # Benchmark orchestration and reporting
└── __init__.py          # Package initialization
```

## Configuration

### Baselines

Edit `config.yaml` to enable/disable baselines:

```yaml
baselines:
  - name: "xgboost"
    type: "ml"
    enabled: true
    
  - name: "lightgbm"
    type: "ml"
    enabled: true
    
  - name: "rule-based"
    type: "heuristic"
    enabled: true
    rules:
      - condition: "type == 'CASH_OUT' and amount > 100000"
        prediction: "fraud"
        confidence: 0.8
```

### Test Datasets

Three dataset types are supported:

1. **Inline Data:** Small test sets defined in config
2. **Service:** Load from `benchmark_service`
3. **CSV Files:** Load from disk

```yaml
test_datasets:
  - name: "quick_test"
    inline_data: [...]
    enabled: true
    
  - name: "benchmark_suite"
    source: "service"
    enabled: true
    
  - name: "edge_cases"
    path: "data/samples/edge_cases.csv"
    enabled: false
```

### Metrics

Supported metrics:

- **Classification:** accuracy, precision, recall, f1_score
- **Performance:** latency_p50, latency_p95, latency_p99
- **Cost:** cost_per_1k, token_usage
- **Errors:** false_positive_rate, false_negative_rate

## Baseline Types

### 1. ML Baselines

Classical machine learning models (XGBoost, LightGBM, RandomForest).

**Characteristics:**
- Fast inference (1-10ms)
- High precision, lower recall
- Requires pre-trained models
- No LLM dependency

**Example:**
```python
from benchmarks.baselines import MLBaseline

baseline = MLBaseline(name="xgboost", model_name="xgboost")
baseline.setup()
result = baseline.predict(transaction)
```

### 2. Rule-Based Baseline

Hand-crafted heuristic rules.

**Characteristics:**
- Ultra-fast (<0.1ms)
- Transparent logic (explainable)
- No model training required
- Configurable rules

**Example:**
```python
from benchmarks.baselines import RuleBasedBaseline

rules = [
    {
        "condition": "type == 'CASH_OUT' and amount > 100000",
        "prediction": "fraud",
        "confidence": 0.8
    }
]

baseline = RuleBasedBaseline(name="rule-based", rules=rules)
baseline.setup()
result = baseline.predict(transaction)
```

### 3. Single-Agent Baseline

Simple LLM-based detection (requires Ollama).

**Characteristics:**
- Slower (1-5s)
- Provides reasoning
- Requires Ollama running
- Uses llama2:7b by default

**Example:**
```python
from benchmarks.baselines import SingleAgentBaseline

baseline = SingleAgentBaseline(name="single-agent", model="llama2:7b")
baseline.setup()  # Checks Ollama availability
result = baseline.predict(transaction)
```

## Results

Benchmark results are saved to `data/benchmarks/results/`:

```
results/
├── benchmark_results_20260209_055249.json      # Raw results
├── benchmark_report_20260209_055249.json       # Structured report
└── benchmark_report_20260209_055249.md         # Markdown report
```

### Report Structure

```markdown
# Benchmark Report

## Summary
- Total Predictions: 15
- Baselines Tested: xgboost, lightgbm, rule-based
- Best Baseline: rule-based

## Comparison Table
| Baseline   | Accuracy | Precision | Recall | F1-Score | Latency (p95) |
|------------|----------|-----------|--------|----------|---------------|
| rule-based | 0.800    | 0.750     | 1.000  | 0.857    | 0.1ms         |

## Per-Baseline Metrics
[Detailed metrics for each baseline]

## Recommendations
[Automated insights]
```

## Advanced Usage

### Programmatic API

```python
from benchmarks.runner import BenchmarkRunner

# Initialize runner
runner = BenchmarkRunner("benchmarks/config.yaml")

# Run benchmarks
results = runner.run()

# Generate report
report = runner.generate_report(results)

# Save results
runner.save_results(output_dir="my_results/")
```

### Custom Baseline

Implement a custom baseline:

```python
from benchmarks.baselines import BaselineEvaluator, PredictionResult

class CustomBaseline(BaselineEvaluator):
    def setup(self) -> bool:
        # Initialize your model/system
        self.setup_complete = True
        return True
    
    def predict(self, transaction: dict) -> PredictionResult:
        # Your prediction logic
        prediction = "fraud" if custom_logic(transaction) else "legitimate"
        confidence = 0.85
        
        return PredictionResult(
            prediction=prediction,
            confidence=confidence,
            latency_ms=10.5,
            metadata={"custom_field": "value"}
        )
```

## Performance Optimization

### M4 Pro Settings (config.yaml)

```yaml
hardware:
  use_apple_silicon: true
  max_threads: 8           # M4 Pro has 14 cores, use 8 for safety
  batch_size: 32
  max_memory_mb: 4096      # 4GB max
```

### Parallel Execution

```yaml
execution:
  parallel: false           # Set to true for parallel baseline execution
  max_workers: 2            # Conservative for M4 Pro
  timeout_per_prediction: 30
```

## Troubleshooting

### Models Not Loading

Ensure models are trained and available:

```bash
cd backend
python scripts/train_lightgbm_model.py
python scripts/train_xgboost_model.py
```

### Ollama Connection Error

Start Ollama for single-agent baseline:

```bash
ollama serve
ollama pull llama2:7b
```

### Dataset Not Found

Check dataset paths in `config.yaml`:

```yaml
test_datasets:
  - name: "my_dataset"
    path: "data/samples/my_data.csv"  # Verify this path exists
```

## Research Integration

### Thesis Usage

1. Run comprehensive benchmarks:
   ```bash
   python scripts/run_benchmarks.py > thesis_results.log
   ```

2. Extract comparison tables from markdown reports

3. Add to thesis:
   - Baseline comparison table
   - Per-baseline metrics
   - Statistical significance tests (Phase 9.2)

### Publication-Ready Artifacts

- ✅ Reproducible configuration
- ✅ Baseline implementations
- ✅ Comprehensive metrics
- ✅ Automated reporting

## Next Steps

See **Phase 9.2+** for:
- Multi-agent pattern benchmarking
- Statistical significance testing
- Ablation studies
- Reproducibility package

## Support

For questions or issues:
1. Check configuration in `config.yaml`
2. Review logs in `data/benchmarks/benchmark_run.log`
3. See implementation summary: `docs/planning/PHASE-9.1-IMPLEMENTATION-SUMMARY.md`

---

**Version:** 1.0  
**Date:** February 9, 2026  
**Project:** FinSight AI
