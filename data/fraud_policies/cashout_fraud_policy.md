# CASH_OUT Transaction Fraud Detection Policy
**Policy ID:** FDP-CASHOUT-001
**Version:** 1.0
**Effective Date:** December 28, 2025
**Transaction Type:** CASH_OUT

## Overview
CASH_OUT transactions represent withdrawals from customer accounts to cash. This is the highest-risk transaction type in the PaySim dataset, with fraud occurring exclusively in CASH_OUT and TRANSFER types.

## Fraud Risk Profile
- **Fraud Rate:** 0.16% (higher than dataset average of 0.13%)
- **Risk Level:** CRITICAL
- **Primary Attack Vector:** Money laundering, account takeover, ATM skimming

## Detection Rules

### High-Risk Indicators (BLOCK)
1. **Amount Thresholds**
   - Single cash-out >$150,000 → **Immediate Block**
   - Single cash-out >$50,000 from account with balance <$60,000 → **Block**
   - Daily cumulative cash-outs >$300,000 → **Block**

2. **Balance Depletion**
   - Cash-out leaves account balance at exactly $0 → **High Risk**
   - Cash-out amount = 100% of account balance → **Block**
   - Multiple cash-outs in succession depleting account → **Block**

3. **Pattern-Based**
   - Cash-out immediately after large TRANSFER receipt → **Block**
   - >2 cash-outs within 10 minutes → **Block**
   - Cash-out amount in round numbers >$25,000 (e.g., $50,000 exactly) → **Review**
   - Sudden cash-out after account dormancy >30 days → **Block**

4. **ATM/Location Anomalies** (if available)
   - Multiple cash-outs from different locations in <1 hour → **Block**
   - Cash-out from foreign country without travel notification → **Block**

### Medium-Risk Indicators (REVIEW)
1. **Unusual Amounts**
   - Amount >$20,000 for account that typically withdraws <$500 → **Review**
   - Cash-out in top 5% of all transactions (>$92,000) → **Review**

2. **Temporal Anomalies**
   - Cash-out at 2-5 AM (unusual hours) → **Review**
   - Weekend cash-outs >$10,000 → **Review**
   - Cash-out frequency >10x normal for account → **Review**

3. **Velocity Checks**
   - >3 cash-outs in 24 hours → **Review**
   - Total cash-out volume >150% of 30-day average → **Review**

### Low-Risk Indicators (APPROVE)
1. **Normal Patterns**
   - Amount <$500 → **Approve**
   - Consistent with historical withdrawal pattern → **Approve**
   - Account age >2 years with no fraud history → **Approve**
   - Amount <10% of account balance → **Approve**

## Fraud Typologies

### Type 1: Account Takeover Cash-Out
**Pattern:** Large TRANSFER followed by immediate CASH_OUT
**Decision:** BLOCK
**Example:** Receive $100K transfer → Cash-out $95K within 5 minutes

### Type 2: Money Laundering
**Pattern:** Multiple rapid cash-outs depleting account
**Decision:** BLOCK
**Example:** 5 cash-outs of $15K each in 1 hour

### Type 3: ATM Skimming/Cloning
**Pattern:** Multiple cash-outs from different locations
**Decision:** BLOCK
**Example:** $5K withdrawn in City A, then $5K in City B 30 minutes later

## Edge Cases

### Case 1: Large Cash Purchase (Car, Boat)
**Scenario:** $80,000 cash-out for vehicle purchase
**Decision:** REVIEW (verify purchase documentation)
**Reasoning:** Legitimate but unusual activity requiring verification

### Case 2: Emergency Medical Cash-Out
**Scenario:** $30,000 cash-out at 11 PM for emergency
**Decision:** REVIEW (contact customer immediately)
**Reasoning:** Unusual hour + high amount may indicate distress or fraud

### Case 3: Vacation Spending
**Scenario:** 3 cash-outs of $2,000 each over weekend
**Decision:** REVIEW if no travel notification, APPROVE if travel flagged
**Reasoning:** Verify customer is traveling

## Escalation Criteria
Escalate to human analyst if:
- Amount >$100,000 regardless of other factors
- Confidence score <0.65
- Customer disputes fraud flag
- Suspected elder abuse or coercion
- Cross-border cash-out

## False Positive Mitigation
- Pre-authorize large withdrawals via customer notification
- Whitelist trusted ATM locations
- Allow scheduled recurring cash-outs (e.g., weekly payroll)
- Higher limits for business accounts with verification

## Mule Account Detection
Look for patterns indicating account is used as "money mule":
- Account receives large TRANSFER → Cash-out within 24 hours
- Minimal legitimate activity between mule transactions
- Account age <90 days with high-value activity
- Cash-outs always deplete to near-zero balance

## Model Integration
- **ML Model:** XGBoost classification with SMOTE-balanced training
- **LLM Reasoning:** Explain why cash-out pattern is suspicious
- **RAG Retrieval:** Query this policy + historical fraud cases
- **Decision Weights:** ML (65%), Rules (25%), LLM (10%)

## Regulatory Compliance
- **AML/KYC:** Cash transactions >$10,000 trigger CTR filing
- **SAR Filing:** Suspicious cash-outs >$5,000 require SAR
- **Customer Verification:** Enhanced due diligence for >$50,000

## Review Schedule
Monthly review of:
- False positive rate (target: <5%)
- False negative rate (target: <1%)
- Average cash-out amount trends
- Emerging fraud patterns

---
**Last Updated:** December 28, 2025
**Policy Owner:** Fraud Prevention Team
**Approval:** Risk Management & Compliance Committee
