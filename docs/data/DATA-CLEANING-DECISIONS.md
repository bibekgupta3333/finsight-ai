# Data Cleaning & Preprocessing Decisions
**Project:** FinSight AI - Fraud Detection System
**Date:** December 28, 2025
**Pipeline:** `backend/scripts/data_cleaning.py`

## Overview
This document records all decisions made during the data cleaning and preprocessing pipeline for the PaySim mobile money dataset.

---

## 1. Missing Values Handling

### Decision
**Strategy:** No imputation needed - dataset is complete

**Rationale:**
- EDA revealed **0 missing values** across all 6.3M transactions
- PaySim is a synthetic dataset with complete records
- No imputation strategy required

**Fallback Strategy (if missing values found):**
- Critical columns (`amount`, `type`, `isFraud`): **DROP** rows
- Balance columns: **Median imputation** (preserves distribution)
- Account IDs: **DROP** rows (cannot impute identifiers)

**Code Implementation:**
```python
missing = df.isnull().sum()
if missing.sum() > 0:
    df = df.dropna(subset=['amount', 'type', 'isFraud'])
    df[numeric_cols] = df[numeric_cols].fillna(df[numeric_cols].median())
```

---

## 2. Duplicate Transactions

### Decision
**Strategy:** Remove exact duplicates

**Rationale:**
- EDA revealed **0 duplicates**
- Duplicate detection uses all columns
- PaySim transactions have unique timestamps (step) and account combinations

**Why Not Keep Duplicates:**
- True duplicates indicate data collection errors
- Legitimate repeated transactions would have different `step` values

**Code Implementation:**
```python
df = df.drop_duplicates()
```

---

## 3. PII Masking (Account IDs)

### Decision
**Strategy:** SHA256 hashing with truncation (16 characters)

**Rationale:**
- **Privacy:** Account IDs (`C1234567890`, `M9876543210`) are PII
- **Uniqueness:** SHA256 guarantees collision-free hashing for 6.3M accounts
- **Truncation:** First 16 hex chars provide 2^64 uniqueness (overkill for our scale)
- **Irreversibility:** One-way hash prevents de-identification

**Alternative Considered:**
- Sequential numbering (`C0001`, `C0002`) → Rejected: Loses account continuity for fraud pattern analysis

**Code Implementation:**
```python
import hashlib

def hash_account_id(account_id: str) -> str:
    return hashlib.sha256(account_id.encode()).hexdigest()[:16]

df['nameOrig_hash'] = df['nameOrig'].apply(hash_account_id)
df['nameDest_hash'] = df['nameDest'].apply(hash_account_id)
df = df.drop(columns=['nameOrig', 'nameDest'])
```

**Impact:**
- Original: `nameOrig='C123456789'`
- Hashed: `nameOrig_hash='a1b2c3d4e5f67890'`

---

## 4. Amount Normalization

### Decision
**Strategy:** StandardScaler (z-score normalization)

**Rationale:**
- **Distribution:** Amounts follow log-normal distribution (see EDA)
- **Outliers:** 5.31% outliers (IQR method) → StandardScaler robust to outliers
- **ML Models:** Neural networks and logistic regression benefit from standardization
- **Interpretability:** Z-scores preserve relative magnitude

**MinMaxScaler Rejected:**
- Sensitive to outliers (max = $92M would compress most transactions to near-zero)
- Less suitable for log-normal distributions

**Columns Normalized:**
- `amount` → `amount_normalized`
- `oldbalanceOrg` → `oldbalanceOrg_normalized`
- `newbalanceOrig` → `newbalanceOrig_normalized`
- `oldbalanceDest` → `oldbalanceDest_normalized`
- `newbalanceDest` → `newbalanceDest_normalized`

**Code Implementation:**
```python
from sklearn.preprocessing import StandardScaler

scaler = StandardScaler()
df['amount_normalized'] = scaler.fit_transform(df[['amount']])
```

**Normalization Parameters Saved:**
- Mean: $179,862 (stored for inverse transform during inference)
- Std: $603,858

---

## 5. Temporal Feature Engineering

### Decision
**Strategy:** Extract hour, day, day_of_week, time_period from `step` column

**Rationale:**
- `step` is simulation time (1-743 hours)
- Hour of day (0-23) captures daily fraud patterns (see EDA: lower fraud at midnight)
- Day of week (0-6) simulates weekly patterns
- Time period (morning/afternoon/evening/night) for interpretability

**Feature Definitions:**
```python
hour = step % 24              # 0-23 (midnight = 0)
day = step // 24              # 0-30 (simulation days)
day_of_week = day % 7         # 0-6 (simulated week)
time_period = bin(hour, [0,6,12,18,24])  # night/morning/afternoon/evening
```

**Why Not Use Timestamp:**
- PaySim uses integer `step`, not datetime
- Simpler for feature engineering

---

## 6. Feature Engineering (Fraud Detection Specific)

### Decision
**Strategy:** Create 11 domain-specific fraud signals

#### 6.1 Balance Change Features
```python
balance_change_orig = newbalanceOrig - oldbalanceOrg
balance_change_dest = newbalanceDest - oldbalanceDest
balance_change_ratio_orig = balance_change_orig / oldbalanceOrg  # Handle div-by-zero
balance_change_ratio_dest = balance_change_dest / oldbalanceDest
```

**Rationale:**
- Fraud often involves **complete account draining** (ratio = -1.0)
- Normal transactions show partial balance changes

#### 6.2 Amount to Balance Ratio
```python
amount_to_balance_ratio = amount / oldbalanceOrg
```

**Rationale:**
- **High ratio** (>0.95) = suspicious (account liquidation)
- **Low ratio** (<0.10) = likely legitimate

#### 6.3 Zero Balance Indicators
```python
zero_balance_orig = (newbalanceOrig == 0).astype(int8)
zero_balance_dest = (newbalanceDest == 0).astype(int8)
```

**Rationale:**
- EDA insight: Zero-balance pattern correlates with fraud
- Binary flag for ML models

#### 6.4 Balance Inconsistency Detection
```python
expected_balance = oldbalanceOrg - amount
balance_inconsistency = (abs(newbalanceOrig - expected_balance) > 0.01).astype(int8)
```

**Rationale:**
- EDA found 58% of transactions have balance mismatches
- Inconsistencies may indicate fraud or system errors

#### 6.5 High-Value Transaction Flag
```python
high_value_threshold = df['amount'].quantile(0.99)  # $1,615,979.50
is_high_value = (amount > high_value_threshold).astype(int8)
```

**Rationale:**
- EDA: Top 1% has **3.09% fraud rate** (24× higher than average)

#### 6.6 Round Amount Flag
```python
is_round_amount = (amount % 1000 == 0).astype(int8)  # $100,000 vs $98,543.21
```

**Rationale:**
- Fraud policies note round numbers as suspicious pattern

---

## 7. Data Quality Validation

### Decision
**Strategy:** Automated assertions after pipeline

**Checks Implemented:**
1. ✅ No missing values in critical columns
2. ✅ Fraud rate within expected range (0.1-1%)
3. ✅ All amounts non-negative
4. ✅ Normalized values have variance
5. ✅ Temporal features within valid ranges (hour: 0-23, day_of_week: 0-6)

**Rationale:**
- Catch pipeline bugs early
- Prevent silent data corruption

**Code:**
```python
assert df[critical_cols].isnull().sum().sum() == 0
assert 0.001 < df['isFraud'].mean() < 0.01
assert (df['amount'] >= 0).all()
```

---

## 8. Feature Preservation Decisions

### What We Kept (Original Features)
- `step`: Needed for temporal ordering
- `type`: Transaction category (5 types)
- `amount`: Raw amount (for interpretability)
- `isFraud`: Ground truth label
- `isFlaggedFraud`: Weak supervision signal
- All balance columns (original + normalized)

### What We Dropped
- `nameOrig`, `nameDest`: Replaced with hashed versions

### What We Added (26 new features)
- PII-masked: `nameOrig_hash`, `nameDest_hash`
- Normalized: `amount_normalized`, 4× balance normalized
- Temporal: `hour`, `day`, `day_of_week`, `time_period`
- Fraud signals: 11 engineered features

**Total Features:** 11 original + 26 new = **37 features**

---

## 9. Output Format

### Decision
**Strategy:** Save cleaned data + metadata + statistics

**Files Generated:**
1. **`paysim_cleaned.csv`**: Main cleaned dataset (all features)
2. **`cleaning_statistics.json`**: Pipeline statistics
   - Original shape, cleaned shape
   - Missing values summary
   - Duplicates removed
   - Features created
   - Normalization parameters
3. **`cleaned_metadata.json`**: Column metadata
   - Column names, dtypes
   - Memory usage

**Rationale:**
- Reproducibility: Statistics allow pipeline auditing
- Traceability: Metadata tracks transformations
- Debugging: Easy to compare raw vs cleaned

---

## 10. Reproducibility

### Decision
**Strategy:** Fixed random seed + deterministic operations

**Implementation:**
- Random seed: `42` (no randomness in current pipeline, but prepared for SMOTE)
- Deterministic sorting: None needed (preserve original order)
- Version control: Pipeline script under Git

---

## 11. Performance Considerations

### Optimizations Applied:
- **Dtype optimization:** Use `int8` for flags, `int16` for day, `category` for type
- **Chunked processing:** None needed (6.3M rows fit in memory)
- **Vectorized operations:** All pandas/numpy operations (no loops)

### Memory Usage:
- Raw data: ~886 MB
- Cleaned data: ~950 MB (10% increase due to new features)
- Acceptable for local processing

---

## 12. Future Improvements

### Not Implemented (Out of Scope for v1):
1. **Log transformation** of amounts (log-normal distribution)
   - Reason: StandardScaler sufficient for ML models
   - Future: Consider for better normality
2. **Polynomial features** (amount², amount³)
   - Reason: Increases complexity
   - Future: Test if improves model performance
3. **Interaction features** (amount × hour, type × day_of_week)
   - Reason: Explainability concerns
   - Future: Use feature selection to validate
4. **Time-series features** (rolling averages, lag features)
   - Reason: Requires sorting by account + time
   - Future: For production system with real-time fraud detection

---

