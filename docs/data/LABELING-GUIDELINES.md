# Fraud Transaction Labeling Guidelines
**Project:** FinSight AI - Fraud Detection System
**Version:** 1.0
**Date:** December 28, 2025
**Purpose:** Guidelines for manual fraud case annotation and quality control

---

## Table of Contents
1. [Overview](#overview)
2. [Annotation Process](#annotation-process)
3. [Fraud Classification Rules](#fraud-classification-rules)
4. [Edge Cases](#edge-cases)
5. [Quality Control](#quality-control)
6. [Inter-Annotator Agreement](#inter-annotator-agreement)
7. [Tools & Resources](#tools--resources)

---

## 1. Overview

### Purpose
These guidelines ensure consistent, high-quality annotation of fraud transactions in the PaySim mobile money dataset for:
- Ground truth validation
- LLM explanation generation
- Model training and evaluation
- Human-in-the-loop feedback

### Annotation Goals
- **Accuracy:** Correctly identify fraud patterns
- **Consistency:** Agreement between annotators (target: >90% IAA)
- **Completeness:** Document all relevant fraud indicators
- **Explainability:** Provide clear reasoning for each decision

### Dataset Context
- **Source:** PaySim mobile money simulator
- **Size:** 6,362,620 transactions
- **Fraud Rate:** 0.13% (8,213 fraud cases)
- **Transaction Types:** TRANSFER, CASH_OUT, CASH_IN, PAYMENT, DEBIT
- **Fraud Types:** Only TRANSFER (0.77%) and CASH_OUT (0.18%) contain fraud

---

## 2. Annotation Process

### Step 1: Review Transaction Details
Examine the following fields for each transaction:
```
- step: Time step (1-743 hours)
- type: Transaction type (TRANSFER, CASH_OUT, etc.)
- amount: Transaction amount in dollars
- nameOrig: Origin account ID (hashed for privacy)
- oldbalanceOrg: Origin balance before transaction
- newbalanceOrig: Origin balance after transaction
- nameDest: Destination account ID (hashed)
- oldbalanceDest: Destination balance before transaction
- newbalanceDest: Destination balance after transaction
- isFraud: Ground truth label (verify this)
- isFlaggedFraud: System flag (weak signal)
```

### Step 2: Apply Fraud Detection Checklist
Check for fraud indicators (see Section 3)

### Step 3: Make Decision
- **FRAUD:** Transaction is fraudulent (assign label = 1)
- **LEGITIMATE:** Transaction is legitimate (assign label = 0)
- **UNCERTAIN:** Escalate for senior review

### Step 4: Document Reasoning
Provide structured explanation:
- **Primary Reason:** Main fraud indicator (e.g., "ACCOUNT_DRAINAGE")
- **Supporting Evidence:** 2-3 key facts
- **Confidence:** Low (60-75%), Medium (75-90%), High (90-99%)
- **Recommended Action:** BLOCK, REVIEW, APPROVE

### Step 5: Quality Check
- Verify balances are mathematically consistent
- Cross-reference with fraud policies
- Check for annotation errors

---

## 3. Fraud Classification Rules

### 3.1 CRITICAL Fraud Indicators (Always Flag)

#### Account Drainage
**Definition:** Origin account completely emptied
**Pattern:**
```
oldbalanceOrg > 0
newbalanceOrig = 0
amount = oldbalanceOrg
```
**Example:**
```
oldbalanceOrg: $250,000
amount: $250,000
newbalanceOrig: $0
→ FRAUD (Confidence: HIGH)
```
**Reasoning:** Legitimate users rarely drain accounts to zero in single transaction

---

#### Balance Anomaly
**Definition:** Transaction balances violate accounting rules
**Pattern:**
```
expected_balance = oldbalanceOrg - amount
|newbalanceOrig - expected_balance| > $0.01
```
**Example:**
```
oldbalanceOrg: $100,000
amount: $50,000
expected newbalanceOrig: $50,000
actual newbalanceOrig: $100,000  ← Anomaly!
→ FRAUD (Confidence: HIGH)
```
**Reasoning:** System manipulation or data corruption

---

### 3.2 HIGH-Risk Fraud Indicators

#### High-Value Transaction
**Definition:** Amount exceeds 99th percentile ($1,615,979.50)
**Context:** Top 1% has 3.09% fraud rate (24× higher than average)
**Example:**
```
amount: $2,500,000
type: TRANSFER
→ Heightened scrutiny required
```
**Action:** Investigate additional indicators

---

#### Liquidation Attempt
**Definition:** Transaction ≥95% of account balance
**Pattern:**
```
amount / oldbalanceOrg ≥ 0.95
```
**Example:**
```
oldbalanceOrg: $500,000
amount: $480,000 (96%)
→ FRAUD (if combined with other indicators)
```
**Reasoning:** Account takeover or coercion

---

### 3.3 MEDIUM-Risk Fraud Indicators

#### Round Amount
**Definition:** Suspiciously round numbers
**Pattern:**
```
amount % 10000 = 0  (e.g., $100,000, $250,000)
```
**Reasoning:** Structuring to avoid detection thresholds
**Note:** Not fraud alone; many legitimate transfers are round

---

#### Suspicious Timing
**Definition:** Transaction during high-risk hours
**Pattern:**
```
hour ∈ {0, 1, 2, 3}  (midnight to 4 AM)
```
**Context:** Lower legitimate activity, higher fraud rate
**Note:** Weak signal; requires supporting evidence

---

#### Flagged by System
**Definition:** `isFlaggedFraud = 1`
**Accuracy:** Low precision (many false positives)
**Use:** Weak supervision signal only
**Action:** Investigate further, not definitive

---

### 3.4 Transaction Type Risk Levels

| Type | Fraud Rate | Risk Level | Annotation Focus |
|------|------------|------------|------------------|
| TRANSFER | 0.77% | **HIGH** | Check for account drainage, liquidation |
| CASH_OUT | 0.18% | **CRITICAL** | Final step in fraud chain, zero balance pattern |
| CASH_IN | 0.00% | **LOW** | No fraud observed, skip detailed review |
| PAYMENT | 0.00% | **LOW** | No fraud observed, skip detailed review |
| DEBIT | 0.00% | **LOW** | No fraud observed, skip detailed review |

**Annotation Optimization:**
- CASH_IN, PAYMENT, DEBIT: Auto-label as legitimate (save time)
- TRANSFER, CASH_OUT: Manual review required

---

## 4. Edge Cases

### Edge Case 1: Business Liquidation
**Scenario:**
```
type: TRANSFER
amount: $500,000 (100% of balance)
time: Business hours (9 AM)
oldbalanceOrg: $500,000
newbalanceOrig: $0
```
**Decision:** Could be legitimate (business closure, sale)
**Action:**
- Check destination: If merchant account → LEGITIMATE
- If individual account → FRAUD (likely)
- **Label:** UNCERTAIN → Escalate

---

### Edge Case 2: Recurring Round Payments
**Scenario:**
```
type: PAYMENT
amount: $1,000 (round number)
frequency: Monthly (same account, same amount)
```
**Decision:** LEGITIMATE (rent, subscription)
**Reasoning:** Round amounts common for recurring bills

---

### Edge Case 3: High-Value Emergency Transfer
**Scenario:**
```
type: TRANSFER
amount: $2,000,000
time: 2 AM
from: Individual account
to: Hospital merchant code
```
**Decision:** LEGITIMATE (medical emergency)
**Reasoning:** Context matters; destination indicates emergency

---

### Edge Case 4: Balance Inconsistency in PAYMENT
**Scenario:**
```
type: PAYMENT
amount: $50
oldbalanceOrg: $1,000
newbalanceOrig: $1,000  ← No change!
```
**Decision:** LEGITIMATE (likely)
**Reasoning:** PAYMENT type doesn't always decrement origin balance (simulator artifact)
**Action:** Do NOT flag as fraud based on balance alone for PAYMENT type

---

## 5. Quality Control

### Validation Checklist
Before submitting annotation, verify:

- [ ] Transaction type is TRANSFER or CASH_OUT (else auto-legitimate)
- [ ] At least 2 fraud indicators present for FRAUD label
- [ ] Confidence score justified by evidence strength
- [ ] Explanation is specific (no vague statements)
- [ ] Mathematical consistency (balances + amount)
- [ ] No annotation errors (typos, wrong label)

### Red Flags (Double-Check Required)
- Only 1 weak indicator but labeled FRAUD
- High confidence (>90%) with only circumstantial evidence
- Legitimate label despite account drainage
- Inconsistent reasoning (contradictory statements)

### Escalation Triggers
Escalate to senior annotator if:
- Confidence <75% on fraud decision
- Conflicting fraud indicators
- Novel fraud pattern not in guidelines
- Inter-annotator disagreement (see Section 6)

---

## 6. Inter-Annotator Agreement (IAA)

### Target Agreement Rate
- **Goal:** ≥90% agreement on fraud/legitimate labels
- **Acceptable:** 85-90%
- **Unacceptable:** <85% → Revise guidelines

### IAA Calculation
```
Agreement = (# Matching Labels) / (Total Labeled) × 100%

Cohen's Kappa = (P_observed - P_expected) / (1 - P_expected)
Target Kappa: >0.80 (strong agreement)
```

### Disagreement Resolution Process

#### Step 1: Independent Labeling
- Two annotators label same 100-transaction sample
- No discussion before labeling

#### Step 2: Compare Labels
- Calculate IAA metrics
- Identify disagreements

#### Step 3: Resolve Disagreements
- **Minor (<10% disagreement):** Senior annotator decides
- **Major (>10% disagreement):** Team discussion + guideline update

#### Step 4: Retrain
- Clarify ambiguous guidelines
- Re-label disputed cases
- Measure IAA improvement

### Example Disagreement Analysis
```
Annotator A: FRAUD (85% confidence)
Annotator B: LEGITIMATE (70% confidence)

Transaction Details:
- type: TRANSFER
- amount: $180,000 (just below $200k threshold)
- amount_to_balance_ratio: 94% (just below 95%)

Resolution:
- Senior review: FRAUD
- Reasoning: Multiple indicators near thresholds = cumulative risk
- Guideline Update: Add "near-threshold cumulative risk" rule
```

---

## 7. Tools & Resources

### Annotation Tools
- **CSV Editor:** Excel, Google Sheets, or Pandas (Python)
- **JSON Editor:** VSCode with JSON formatter
- **Validation Script:** `backend/scripts/validate_annotations.py` (coming soon)

### Reference Materials
1. **Fraud Policies:**
   - `data/fraud_policies/transfer_fraud_policy.md`
   - `data/fraud_policies/cashout_fraud_policy.md`
   - `data/fraud_policies/lowrisk_types_policy.md`

2. **EDA Notebook:**
   - `backend/notebooks/01_data_loading_and_eda.ipynb`
   - Key insights: fraud rates, distributions, patterns

3. **Weak Supervision Rules:**
   - `backend/scripts/generate_weak_supervision.py`
   - Automated rule-based heuristics

### Data Schema Reference
```python
{
  "transaction_id": "TXN_12345",
  "type": "TRANSFER",
  "amount": 250000.00,
  "nameOrig_hash": "a1b2c3d4...",
  "nameDest_hash": "e5f6g7h8...",
  "oldbalanceOrg": 500000.00,
  "newbalanceOrig": 250000.00,
  "oldbalanceDest": 0.00,
  "newbalanceDest": 250000.00,
  "hour": 14,
  "day": 5,
  "day_of_week": 2,
  "is_fraud": 1,  ← Annotate this
  "fraud_reason": "ACCOUNT_DRAINAGE + HIGH_VALUE",  ← Provide this
  "confidence": 0.95,  ← Assess this
  "decision": "BLOCK"  ← Recommend this
}
```

---

## 8. Common Annotation Mistakes (Avoid These!)

### ❌ Mistake 1: Labeling Based on Single Indicator
**Wrong:**
```
amount = $250,000 → FRAUD
```
**Correct:**
```
amount = $250,000 (HIGH_VALUE)
+ newbalanceOrig = 0 (ACCOUNT_DRAINAGE)
+ hour = 2 AM (SUSPICIOUS_TIMING)
→ FRAUD (3 indicators)
```

### ❌ Mistake 2: Ignoring Transaction Type
**Wrong:**
```
type: PAYMENT
amount = $200,000 (high value)
→ FRAUD
```
**Correct:**
```
type: PAYMENT has 0% fraud rate historically
→ LEGITIMATE (unless extraordinary evidence)
```

### ❌ Mistake 3: Overconfidence Without Evidence
**Wrong:**
```
Confidence: 99%
Reasoning: "It just looks suspicious"
```
**Correct:**
```
Confidence: 85%
Reasoning: "Account drainage ($500k→$0) + high-value transfer + suspicious timing (2 AM)"
```

### ❌ Mistake 4: Not Escalating Uncertainty
**Wrong:**
```
Confidence: 65%
Decision: FRAUD (labeled anyway)
```
**Correct:**
```
Confidence: 65%
Decision: UNCERTAIN → Escalate to senior annotator
```

---

## 9. Annotation Workflow Example

### Transaction #12345
```
step: 156 (Day 6, Hour 12)
type: TRANSFER
amount: $350,000
nameOrig_hash: f3a9c7e1...
oldbalanceOrg: $350,000
newbalanceOrig: $0
oldbalanceDest: $0
newbalanceDest: $350,000
isFlaggedFraud: 0
```

### Annotation Process:

**Step 1: Check Transaction Type**
- Type: TRANSFER → HIGH RISK (0.77% fraud rate)
- Proceed with detailed review

**Step 2: Apply Fraud Checklist**
- ✅ Account drainage (350k → 0)
- ✅ High value ($350k > $200k threshold)
- ✅ Liquidation (100% of balance)
- ❌ Balance inconsistency (math checks out)
- ❌ Round amount (350k is not round)
- ❌ Suspicious timing (12 PM is normal)

**Step 3: Count Indicators**
- 3 CRITICAL/HIGH indicators triggered
- Threshold: ≥2 → FRAUD

**Step 4: Determine Confidence**
- Account drainage (CRITICAL) = +30%
- High value (HIGH) = +15%
- Liquidation (HIGH) = +15%
- Base = 60%
- **Total: 60% + 30% + 15% + 15% = 95% → HIGH confidence**

**Step 5: Document**
```json
{
  "transaction_id": "TXN_12345",
  "label": 1,
  "fraud_reason": "ACCOUNT_DRAINAGE + HIGH_VALUE + LIQUIDATION",
  "confidence": 0.95,
  "decision": "BLOCK",
  "explanation": "This $350,000 TRANSFER transaction completely drained the origin account (liquidation pattern), exceeds high-value threshold, and shows characteristics of account takeover fraud.",
  "annotator": "Annotator_001",
  "timestamp": "2025-12-28T10:30:00Z"
}
```

---

## 10. Continuous Improvement

### Feedback Loop
1. **Collect:** Annotator feedback on ambiguous cases
2. **Analyze:** Identify guideline gaps
3. **Update:** Revise guidelines quarterly
4. **Retrain:** Brief annotators on changes
5. **Measure:** Track IAA improvement

### Version History
- **v1.0 (2025-12-28):** Initial guidelines
- **v1.1 (TBD):** Add new edge cases from production

---

**Questions?**
Contact: fraud-labeling-team@finsightai.com
Guidelines Repo: `docs/data/LABELING-GUIDELINES.md`

---
**Last Updated:** December 28, 2025
**Next Review:** March 28, 2026
