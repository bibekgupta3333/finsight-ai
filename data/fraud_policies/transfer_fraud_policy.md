# TRANSFER Transaction Fraud Detection Policy
**Policy ID:** FDP-TRANSFER-001
**Version:** 1.0
**Effective Date:** December 28, 2025
**Transaction Type:** TRANSFER

## Overview
TRANSFER transactions represent peer-to-peer money transfers between customer accounts. According to PaySim analysis, TRANSFER is one of only two transaction types that exhibit fraudulent activity (along with CASH_OUT).

## Fraud Risk Profile
- **Fraud Rate:** 0.50% (significantly higher than dataset average of 0.13%)
- **Risk Level:** HIGH
- **Primary Attack Vector:** Account takeover and unauthorized transfers

## Detection Rules

### High-Risk Indicators (BLOCK)
1. **Amount Thresholds**
   - Single transfer >$200,000 → **Immediate Block**
   - Single transfer >$100,000 from new account (<7 days) → **Block**
   - Daily cumulative transfers >$500,000 → **Block**

2. **Balance Anomalies**
   - Transfer amount > 95% of origin account balance → **Block**
   - Origin account balance drops to exactly $0 after transfer → **High Risk**
   - Destination account receives >10 transfers in 1 hour → **Block**

3. **Pattern-Based**
   - Rapid successive transfers (>3 in 5 minutes) → **Block**
   - Round-number amounts >$50,000 (e.g., exactly $100,000) → **Review**
   - Transfer immediately followed by CASH_OUT → **Block**

### Medium-Risk Indicators (REVIEW)
1. **Unusual Amounts**
   - Transfer amount in top 1% (>99th percentile: $306,000) → **Review**
   - Amount deviates >3σ from account's historical average → **Review**

2. **Temporal Anomalies**
   - Transfers at unusual hours (2-5 AM) for account → **Review**
   - First-time transfer to new destination >$10,000 → **Review**

3. **Velocity Checks**
   - >5 transfers in 24 hours → **Review**
   - Total transfer volume >200% of 30-day average → **Review**

### Low-Risk Indicators (APPROVE)
1. **Normal Patterns**
   - Amount <$1,000 → **Approve**
   - Recurring transfer to known payee → **Approve**
   - Amount consistent with historical behavior → **Approve**

## Edge Cases

### Case 1: Large Legitimate Business Transfer
**Scenario:** $150,000 transfer for business payroll
**Decision:** REVIEW (require business verification)
**Reasoning:** Amount exceeds high-risk threshold but may be legitimate business activity

### Case 2: Account Liquidation
**Scenario:** Transfer of entire balance before account closure
**Decision:** REVIEW (verify account closure request)
**Reasoning:** Zero-balance pattern is fraud indicator but legitimate for closures

### Case 3: Emergency Transfer
**Scenario:** $75,000 medical emergency transfer at 3 AM
**Decision:** REVIEW (contact customer)
**Reasoning:** Unusual hour + high amount requires verification

## Escalation Criteria
Escalate to human analyst if:
- Confidence score <0.70
- Contradicting signals (high amount + recurring payee)
- VIP/High-value customer account
- International transfer (if feature available)

## False Positive Mitigation
- Whitelist verified business accounts
- Allow higher limits for accounts >5 years old with clean history
- Reduce thresholds during night hours (10 PM - 6 AM)

## Model Integration
- **ML Model:** Use XGBoost classification score
- **LLM Reasoning:** Chain-of-thought explanation for borderline cases
- **RAG Retrieval:** Query this policy for TRANSFER transactions
- **Final Decision:** Combine ML score (70%), policy rules (20%), LLM reasoning (10%)

## Review Schedule
This policy should be reviewed quarterly and updated based on:
- New fraud patterns identified
- False positive/negative rates
- Regulatory changes
- Customer feedback

---
**Last Updated:** December 28, 2025
**Policy Owner:** Fraud Prevention Team
**Approval:** Risk Management Committee
