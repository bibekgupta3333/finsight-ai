# Benchmark Report

**Generated:** 2026-02-09T05:53:00.405159

## Summary

- **Total Predictions:** 18
- **Baselines Tested:** xgboost, lightgbm, rule-based
- **Datasets Tested:** benchmark_suite
- **Best Baseline:** rule-based

## Comparison Table

| Baseline | Accuracy | Precision | Recall | F1-Score | Latency (p95) |
|----------|----------|-----------|--------|----------|---------------|
| rule-based | 0.833 | 0.800 | 1.000 | 0.889 | 0.1ms |
| xgboost | 0.500 | 1.000 | 0.250 | 0.400 | 3.8ms |
| lightgbm | 0.500 | 1.000 | 0.250 | 0.400 | 1.5ms |

## Per-Baseline Metrics

### xgboost

- Accuracy: 0.500
- Precision: 1.000
- Recall: 0.250
- F1-Score: 0.400
- True Positives: 1
- False Positives: 0
- False Negatives: 3
- Latency (p50): 2.64ms
- Latency (p95): 3.84ms

### lightgbm

- Accuracy: 0.500
- Precision: 1.000
- Recall: 0.250
- F1-Score: 0.400
- True Positives: 1
- False Positives: 0
- False Negatives: 3
- Latency (p50): 1.13ms
- Latency (p95): 1.49ms

### rule-based

- Accuracy: 0.833
- Precision: 0.800
- Recall: 1.000
- F1-Score: 0.889
- True Positives: 4
- False Positives: 1
- False Negatives: 0
- Latency (p50): 0.02ms
- Latency (p95): 0.05ms


## Recommendations

- ✓ Low latency (<100ms p95). Good for real-time applications.
- 💡 Recommended baseline: rule-based (F1=0.889, Latency=0.1ms)
