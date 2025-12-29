# Bias and Fairness Analysis

## Overview
This document summarizes the comprehensive bias and fairness audit conducted on the PaySim fraud detection dataset to identify potential biases, discrimination patterns, and fairness issues in the data and model predictions.

**Analysis Date:** December 29, 2025
**Dataset:** PaySim cleaned dataset (6,362,620 transactions)
**Script:** `backend/scripts/bias_fairness_analysis.py`
**Reports:** `data/analysis/bias_audit_report.json`, `data/analysis/bias_audit_summary.txt`

---

## Executive Summary

### Key Findings

✅ **Amount-Fraud Correlation:** WEAK (Pearson r = 0.0767)
- While weak overall correlation, fraud rate increases significantly at high percentiles
- P99 transactions show 31.22x higher fraud rate than baseline

⚠️ **Transaction Type Bias:** DETECTED (χ² p < 0.001)
- Significant association between transaction type and fraud
- TRANSFER (0.77%) and CASH_OUT (0.18%) have fraud, while PAYMENT, DEBIT, CASH_IN have 0%

⚠️ **Demographic Parity:** VIOLATED (59.97% difference)
- Prediction rates vary dramatically across transaction types
- TRANSFER: 59.97% prediction rate vs PAYMENT: 0%

⚠️ **Equalized Odds:** VIOLATED (60.02% FPR difference)
- True positive rates and false positive rates not equal across groups
- Indicates unfair treatment of different transaction types

---

## Detailed Findings

### 1. Amount-Fraud Correlation Analysis

#### Statistical Tests
- **Pearson Correlation:** r = 0.0767 (weak positive correlation)
- **Point-Biserial:** r = 0.0767, p < 0.001 (statistically significant)
- **Mann-Whitney U Test:** p < 0.001 (distributions differ significantly)

#### Amount Distribution by Fraud Status
| Metric | Fraud Transactions | Legitimate Transactions |
|--------|-------------------|------------------------|
| Mean | $1,467,967.30 | $178,197.04 |
| Median | $441,423.44 | $74,684.72 |

#### Fraud Rate by Amount Percentile
| Percentile | Threshold | High Amount Fraud Rate | Low Amount Fraud Rate | Ratio |
|-----------|-----------|----------------------|---------------------|-------|
| P25 | $13,390 | 0.1651% | 0.0210% | 7.86x |
| P50 | $74,872 | 0.2140% | 0.0442% | 4.84x |
| P75 | $208,721 | 0.3397% | 0.0589% | 5.77x |
| P90 | $365,423 | 0.6934% | 0.0664% | 10.45x |
| P95 | $518,634 | 1.1954% | 0.0730% | 16.38x |
| P99 | $1,615,980 | 3.0946% | 0.0991% | 31.22x |

**Interpretation:** While overall correlation is weak, high-value transactions (>P90) show disproportionately higher fraud rates. This creates potential bias against legitimate high-value transactions.

---

### 2. Transaction Type Bias Analysis

#### Fraud Rate by Transaction Type
| Type | Count | Percentage | Fraud Count | Fraud Rate |
|------|-------|-----------|-------------|------------|
| PAYMENT | 2,151,495 | 33.81% | 0 | 0.0000% |
| CASH_IN | 1,399,284 | 21.99% | 0 | 0.0000% |
| CASH_OUT | 2,237,500 | 35.17% | 4,116 | 0.1840% |
| TRANSFER | 532,909 | 8.38% | 4,097 | 0.7688% |
| DEBIT | 41,432 | 0.65% | 0 | 0.0000% |

#### Statistical Test
- **Chi-Square Test:** χ² = 22,082.54, p < 0.001, df = 4
- **Result:** BIAS DETECTED - Transaction type is significantly associated with fraud

**Interpretation:** Fraud is exclusively concentrated in TRANSFER and CASH_OUT transactions. This creates strong bias where models may over-predict fraud for these types and under-predict for others.

---

### 3. False Positive/Negative Analysis

Using a simple rule-based classifier (amount ≥ P90 OR isFlaggedFraud == 1):

#### Overall Confusion Matrix
| Metric | Value |
|--------|-------|
| True Negative (TN) | 5,722,557 |
| False Positive (FP) | 631,850 |
| False Negative (FN) | 3,800 |
| True Positive (TP) | 4,413 |

#### Performance Metrics
| Metric | Value |
|--------|-------|
| False Positive Rate | 9.94% |
| False Negative Rate | 46.27% |
| Precision | 0.69% |
| Recall | 53.73% |

#### FP/FN by Amount Quartile
| Quartile | Count | FPR | FNR | FP Count | FN Count |
|----------|-------|-----|-----|----------|----------|
| Q1 (Low) | 1,590,656 | 0.00% | 100.00% | 0 | 334 |
| Q2 | 1,590,654 | 0.00% | 100.00% | 0 | 1,072 |
| Q3 | 1,590,655 | 0.00% | 100.00% | 0 | 1,403 |
| Q4 (High) | 1,590,655 | 39.86% | 18.34% | 631,850 | 991 |

**Interpretation:** Rule-based approach shows extreme bias:
- Low-amount transactions: 0% FPR but 100% FNR (all fraud missed)
- High-amount transactions: 39.86% FPR (many false alarms)
- Demonstrates need for sophisticated ML approaches

---

### 4. Statistical Parity Analysis

#### Prediction Rates by Transaction Type
| Type | Prediction Rate | TPR (Recall) | FPR | Precision |
|------|----------------|--------------|-----|-----------|
| PAYMENT | 0.00% | 0.00% | 0.00% | 0.00% |
| CASH_IN | 8.07% | 0.00% | 8.07% | 0.00% |
| DEBIT | 0.01% | 0.00% | 0.01% | 0.00% |
| CASH_OUT | 9.11% | 53.43% | 9.03% | 1.08% |
| TRANSFER | 59.97% | 54.04% | 60.02% | 0.69% |

#### Fairness Metrics
| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| Demographic Parity Difference | 59.97% | 10% | ❌ VIOLATED |
| TPR Difference (Equalized Odds) | 54.04% | 10% | ❌ VIOLATED |
| FPR Difference (Equalized Odds) | 60.02% | 10% | ❌ VIOLATED |

**Interpretation:** Severe violations of all fairness criteria. Prediction rates and error rates vary dramatically across transaction types, indicating systemic unfairness.

---

## Fairness Constraint Recommendations

### 1. Transaction Type Bias (HIGH SEVERITY)
**Finding:** Significant association between transaction type and fraud
**Recommendation:** Apply demographic parity constraint: prediction rates should not vary by more than 10% across transaction types
**Constraint:** `max(P(Ŷ=1|type=t)) - min(P(Ŷ=1|type=t)) < 0.1`
**Implementation:**
- Use type-specific thresholds
- Apply fairness-aware learning (Fairlearn, AIF360)
- Consider separate models per transaction type

### 2. Demographic Parity (MEDIUM SEVERITY)
**Finding:** Demographic parity violated across transaction types
**Recommendation:** Implement post-processing calibration or threshold optimization per group
**Constraint:** Prediction rate difference < 10% across all groups
**Implementation:**
- Calibrated equalized odds post-processing
- Per-group threshold tuning
- Regular fairness monitoring

### 3. Equalized Odds (MEDIUM SEVERITY)
**Finding:** TPR/FPR not equal across groups
**Recommendation:** Use equalized odds post-processing or train with fairness constraints
**Constraint:** `max(TPR_diff, FPR_diff) < 10%` across groups
**Implementation:**
- Hardt et al. equalized odds algorithm
- Adversarial debiasing during training
- Reject option classification

### 4. Monitoring (MEDIUM SEVERITY)
**Finding:** Continuous monitoring needed
**Recommendation:** Implement ongoing bias monitoring in production
**Constraint:** Monthly fairness audits with automated alerts
**Implementation:**
- Real-time fairness dashboards
- Automated bias detection pipelines
- Model retraining triggers on fairness drift

### 5. Data Collection (LOW SEVERITY)
**Finding:** Limited demographic attributes in dataset
**Recommendation:** Consider collecting more granular features while respecting privacy
**Constraint:** Annual bias audit across all available demographics
**Implementation:**
- Privacy-preserving feature engineering
- Synthetic data augmentation
- Cross-group validation sets

---

## Mitigation Strategies

### During Training
1. **Stratified Sampling:** Ensure balanced representation across transaction types
2. **Fairness-Aware Loss Functions:** Add fairness penalty terms
3. **Adversarial Debiasing:** Train discriminator to remove type information
4. **Reweighting:** Adjust sample weights to balance groups

### During Inference
1. **Threshold Optimization:** Use different thresholds per transaction type
2. **Calibrated Predictions:** Apply Platt scaling or isotonic regression per group
3. **Reject Option:** Allow uncertain predictions to defer to human review

### System Design
1. **Human-in-the-Loop:** High-value transactions require human approval
2. **Explainability:** Provide clear reasons for fraud predictions
3. **Appeal Process:** Allow customers to contest fraud flags
4. **Regular Audits:** Quarterly bias audits with external review

---

## Impact on Model Development

### Training Implications
- **Don't** train a single model on all transaction types without adjustment
- **Do** use fairness constraints or separate models per type
- **Do** oversample minority groups (TRANSFER fraud cases)
- **Do** validate fairness metrics on held-out test sets

### Evaluation Implications
- **Don't** only report overall accuracy/AUC
- **Do** report metrics stratified by transaction type
- **Do** track FPR/FNR across all groups
- **Do** monitor disparate impact ratios

### Deployment Implications
- **Don't** use same threshold for all transaction types
- **Do** implement per-type calibration
- **Do** monitor production fairness metrics
- **Do** set up alerts for fairness drift

---

## Compliance Considerations

### Regulatory Frameworks
- **Fair Credit Reporting Act (FCRA):** Requires fairness in credit decisions
- **Equal Credit Opportunity Act (ECOA):** Prohibits discrimination
- **GDPR Article 22:** Right to explanation for automated decisions
- **80% Rule (Disparate Impact):** min/max ratio ≥ 0.8

### Current Compliance Status
❌ **80% Rule:** Currently VIOLATED (ratio << 0.8 for transaction types)
⚠️ **Explainability:** Need to implement for high-stakes decisions
⚠️ **Fairness Monitoring:** Need continuous tracking system

---

## Next Steps

### Immediate Actions
1. ✅ Complete bias audit (DONE)
2. ⬜ Implement fairness-aware training pipeline
3. ⬜ Create per-type evaluation framework
4. ⬜ Set up fairness monitoring dashboard

### Short-term (1-2 months)
1. ⬜ Train models with fairness constraints
2. ⬜ Implement threshold optimization per group
3. ⬜ Deploy fairness metrics to production
4. ⬜ Conduct user testing for appeal process

### Long-term (3-6 months)
1. ⬜ Collect additional features (privacy-preserving)
2. ⬜ Implement adversarial debiasing
3. ⬜ External fairness audit
4. ⬜ Publish fairness methodology

---

## References

### Tools
- **Fairlearn:** https://fairlearn.org/
- **AIF360:** https://aif360.mybluemix.net/
- **What-If Tool:** https://pair-code.github.io/what-if-tool/

### Papers
- Hardt et al. (2016) - Equality of Opportunity in Supervised Learning
- Feldman et al. (2015) - Certifying and Removing Disparate Impact
- Dwork et al. (2012) - Fairness Through Awareness

### Standards
- NIST AI Risk Management Framework
- ISO/IEC 24027 - Bias in AI systems
- IEEE P7003 - Algorithmic Bias Considerations

---

## Appendix: Script Usage

### Running the Analysis
```bash
python backend/scripts/bias_fairness_analysis.py
```

### Output Files
- `data/analysis/bias_audit_report.json` - Full JSON report
- `data/analysis/bias_audit_summary.txt` - Human-readable summary

### Customization
```python
analyzer = BiasFairnessAnalyzer(
    random_seed=42,
    amount_percentiles=[25, 50, 75, 90, 95, 99]
)
```

---

**Document Version:** 1.0
**Last Updated:** December 29, 2025
**Reviewed By:** FinSight AI Team
**Next Review:** Q1 2026
