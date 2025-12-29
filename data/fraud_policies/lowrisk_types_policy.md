# Low-Risk Transaction Types Policy
**Policy ID:** FDP-LOWRISK-001
**Version:** 1.0
**Effective Date:** December 28, 2025
**Transaction Types:** PAYMENT, DEBIT, CASH_IN

## Overview
Based on PaySim dataset analysis, PAYMENT, DEBIT, and CASH_IN transaction types show **zero fraud cases** across 6.3M transactions. These are considered low-risk transaction types.

## Fraud Risk Profile
- **Fraud Rate:** 0.00% (no fraud observed)
- **Risk Level:** LOW
- **Reasoning:** Legitimate customer-initiated transactions with built-in safeguards

## Transaction Type Breakdown

### PAYMENT (2,151,495 transactions)
**Description:** Customer payments for goods/services
**Fraud Rate:** 0.00%
**Risk Level:** LOW

**Why Low Risk:**
- Customer controls payment initiation
- Merchant verification required
- Reversible through dispute process
- Regulatory protections in place

**Monitoring Rules:**
- No fraud-specific rules needed
- Standard AML checks for amounts >$10,000
- Velocity monitoring (>50 payments/day = unusual)

---

### DEBIT (41,432 transactions)
**Description:** Debit card transactions
**Fraud Rate:** 0.00%
**Risk Level:** LOW

**Why Low Risk:**
- PIN/signature verification
- Real-time authorization
- Chip technology reduces cloning
- Cardholder liability protections

**Monitoring Rules:**
- Geographic anomaly detection (if location data available)
- Unusual merchant category codes
- High-frequency small transactions (structuring)

---

### CASH_IN (1,399,284 transactions)
**Description:** Deposits into customer accounts
**Fraud Rate:** 0.00%
**Risk Level:** LOW

**Why Low Risk:**
- Increases account balance (no loss to customer)
- Deposits verified at source
- Rarely targeted for fraud

**Monitoring Rules:**
- Large deposits >$50,000 (AML concern, not fraud)
- Rapid deposit-withdrawal cycles (money laundering)
- Structuring detection (multiple deposits <$10,000)

## General Approval Policy

### Auto-Approve Conditions
✅ **All transactions in these types can be auto-approved if:**
- Amount within normal ranges for type
- No AML/structuring concerns
- Account in good standing
- No customer dispute history

### Review Conditions
⚠️ **Review only for non-fraud concerns:**
- AML compliance (CTR/SAR thresholds)
- Unusual volume patterns (money laundering)
- Account verification needed
- Regulatory reporting requirements

### Block Conditions
🚫 **Never block for fraud concerns** (no fraud observed)
Only block for:
- Confirmed money laundering
- Sanctioned entity transactions
- Regulatory violations
- Account frozen by authorities

## Agent Decision Logic

When analyzing PAYMENT, DEBIT, or CASH_IN transactions:

```
IF transaction.type IN ['PAYMENT', 'DEBIT', 'CASH_IN']:
    fraud_risk = 'LOW'
    decision = 'APPROVE'
    confidence = 0.99

    # Check only for AML concerns
    IF amount > 10000:
        flag_for_aml_review = True

    # Check for structuring
    IF multiple_transactions_below_10k_in_24h:
        flag_for_aml_review = True

    # Default: Approve
    RETURN {
        'decision': 'APPROVE',
        'reason': f'{transaction.type} transactions show 0% fraud rate in historical data',
        'confidence': 0.99,
        'aml_review_needed': flag_for_aml_review
    }
```

## Resource Optimization

**Key Insight:** Since these transaction types have 0% fraud rate, **optimize computational resources** by:

1. **Skip ML Model Inference** for these types
   - No need to run XGBoost classifier
   - No need for LLM reasoning
   - No need for RAG retrieval

2. **Lightweight Rule Engine**
   - Simple AML checks only
   - Velocity monitoring
   - Instant approval (<10ms latency)

3. **Cost Savings**
   - Save ~70% of transactions from expensive ML/LLM processing
   - Focus resources on TRANSFER and CASH_OUT (30% of transactions)

## Exception Handling

### When to Escalate
Even though fraud risk is zero, escalate if:
- Amount >$500,000 (extraordinary)
- Customer reports unauthorized transaction
- Regulatory inquiry received
- Sanctioned entity match

### Historical Context
If fraud is ever detected in these transaction types:
1. Immediately update this policy
2. Activate ML model for affected type
3. Conduct root cause analysis
4. Adjust risk classification

## Model Integration Guidance

**For PAYMENT, DEBIT, CASH_IN transactions:**

```python
# Pseudo-code for agent
if transaction_type in ['PAYMENT', 'DEBIT', 'CASH_IN']:
    # Skip expensive processing
    decision = {
        'fraud_score': 0.01,  # Near-zero fraud probability
        'decision': 'APPROVE',
        'reasoning': 'Transaction type has 0% historical fraud rate',
        'confidence': 0.99,
        'processing_time_ms': 5,  # Fast approval
        'model_used': 'rule_engine',  # Not ML/LLM
        'cost': 0.0001  # Negligible
    }

    # Optional AML checks
    if amount > 10000:
        decision['aml_review'] = True

    return decision
```

## Performance Metrics

**Target SLAs for Low-Risk Transactions:**
- Latency: <10ms (no ML inference)
- Throughput: >10,000 TPS
- Cost: <$0.0001 per transaction
- False Positive Rate: 0% (no fraud expected)
- False Negative Rate: 0% (no fraud to miss)

## Continuous Monitoring

Despite low risk, continue monitoring for:
- Emerging fraud patterns (quarterly review)
- Changes in transaction volumes
- New attack vectors
- Regulatory updates

**Review Schedule:** Quarterly analysis to confirm 0% fraud rate persists

---
**Last Updated:** December 28, 2025
**Policy Owner:** Fraud Prevention Team
**Note:** This policy reflects empirical evidence from 6.3M PaySim transactions. Update immediately if fraud patterns emerge.
