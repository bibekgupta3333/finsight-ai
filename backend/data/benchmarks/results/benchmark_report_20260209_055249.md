# Benchmark Report

**Generated:** 2026-02-09T05:52:49.318561

## Summary

- **Total Predictions:** 15
- **Baselines Tested:** xgboost, lightgbm, rule-based
- **Datasets Tested:** quick_test
- **Best Baseline:** rule-based

## Comparison Table

| Baseline | Accuracy | Precision | Recall | F1-Score | Latency (p95) |
|----------|----------|-----------|--------|----------|---------------|
| rule-based | 0.800 | 0.750 | 1.000 | 0.857 | 0.1ms |
| xgboost | 0.600 | 1.000 | 0.333 | 0.500 | 9.6ms |
| lightgbm | 0.600 | 1.000 | 0.333 | 0.500 | 2.1ms |

## Per-Baseline Metrics

### xgboost

- Accuracy: 0.600
- Precision: 1.000
- Recall: 0.333
- F1-Score: 0.500
- True Positives: 1
- False Positives: 0
- False Negatives: 2
- Latency (p50): 2.61ms
- Latency (p95): 9.61ms

### lightgbm

- Accuracy: 0.600
- Precision: 1.000
- Recall: 0.333
- F1-Score: 0.500
- True Positives: 1
- False Positives: 0
- False Negatives: 2
- Latency (p50): 1.08ms
- Latency (p95): 2.08ms

### rule-based

- Accuracy: 0.800
- Precision: 0.750
- Recall: 1.000
- F1-Score: 0.857
- True Positives: 3
- False Positives: 1
- False Negatives: 0
- Latency (p50): 0.03ms
- Latency (p95): 0.06ms


## Recommendations

- ✓ Low latency (<100ms p95). Good for real-time applications.
- 💡 Recommended baseline: rule-based (F1=0.857, Latency=0.1ms)
