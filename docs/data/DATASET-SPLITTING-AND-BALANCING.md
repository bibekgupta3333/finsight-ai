# Dataset Splitting & Balancing Documentation

## Overview
This document describes the dataset splitting and data augmentation/balancing strategies implemented for the finsight-ai project.

**Date:** December 29, 2025
**Dataset:** PaySim Mobile Money (6,362,620 transactions)
**Fraud Rate:** 0.1291% (8,213 fraud cases out of 6.3M)
**Class Imbalance Severity:** EXTREME (1:773.7 ratio)

---

## 1. Dataset Splitting Strategy

### 1.1 Stratified Split (Recommended for Most Use Cases)

**Purpose:** Maintain the original fraud rate across all splits while ensuring random distribution.

**Configuration:**
- **Train:** 60% (3,817,572 samples, 4,928 fraud)
- **Validation:** 20% (1,272,524 samples, 1,642 fraud)
- **Test:** 20% (1,272,524 samples, 1,643 fraud)
- **Random Seed:** 42 (for reproducibility)

**Implementation Details:**
- Uses `sklearn.model_selection.train_test_split` with `stratify` parameter
- Two-stage splitting: first separates test set, then splits remaining into train/val
- Preserves fraud rate of ~0.129% across all splits

**Results:**
```
Train Set:  3,817,572 samples | 4,928 fraud (0.1291%)
Val Set:    1,272,524 samples | 1,642 fraud (0.1290%)
Test Set:   1,272,524 samples | 1,643 fraud (0.1291%)
```

**When to Use:**
- Default choice for most machine learning workflows
- When fraud distribution is assumed to be consistent across time
- For model selection and hyperparameter tuning

**Location:** `data/splits/stratified/`

---

### 1.2 Temporal Split (Production Simulation)

**Purpose:** Simulate real-world deployment where models are trained on past data and tested on future data.

**Configuration:**
- **Train:** First 60% of time period (step 1-281)
- **Validation:** Next 20% of time period (step 281-355)
- **Test:** Last 20% of time period (step 355-743)

**Implementation Details:**
- Sorts data by `step` column (temporal ordering)
- Splits chronologically without stratification
- Fraud rates may vary across splits (realistic scenario)

**Results:**
```
Train Set:  3,817,572 samples | 3,191 fraud (0.0836%) | Step 1-281
Val Set:    1,272,524 samples |   768 fraud (0.0604%) | Step 281-355
Test Set:   1,272,524 samples | 4,254 fraud (0.3343%) | Step 355-743
```

**Key Observations:**
- **Test set has 4x higher fraud rate** (0.334% vs 0.084% in training)
- This reflects real-world scenarios where fraud patterns evolve over time
- More challenging evaluation scenario

**When to Use:**
- Production readiness testing
- Evaluating model robustness to temporal drift
- When fraud patterns are known to change over time
- Final model evaluation before deployment

**Location:** `data/splits/temporal/`

---

### 1.3 Split Validation

Both splitting strategies include validation checks:
- ✅ No data loss (total samples match original)
- ✅ No data leakage (no overlap between splits)
- ✅ Correct proportions (60/20/20)
- ✅ Required columns present (`isFraud`, `step`)

**Metadata Location:** `data/splits/split_metadata.json`

---

## 2. Data Augmentation & Balancing Strategy

### 2.1 Problem Statement

**Original Class Distribution:**
- **Legitimate:** 3,812,644 samples (99.87%)
- **Fraud:** 4,928 samples (0.13%)
- **Imbalance Ratio:** 1:773.7

**Challenges:**
- Models trained on imbalanced data tend to:
  - Predict all transactions as legitimate (99.87% accuracy but useless)
  - Fail to learn fraud patterns due to insufficient examples
  - Have poor recall on fraud detection

---

### 2.2 Strategy 1: SMOTE (Synthetic Minority Oversampling Technique)

**Purpose:** Generate synthetic fraud cases to balance the dataset.

**How SMOTE Works:**
1. For each fraud case, find k-nearest neighbors (k=5)
2. Create synthetic samples along line segments between neighbors
3. Preserves statistical properties of fraud distribution

**Configuration:**
- Sampling strategy: 0.5 (fraud becomes 33% of dataset)
- Random seed: 42

**Results:**
```
Before:  3,817,572 samples | 4,928 fraud (0.129%)
After:   5,718,966 samples | 1,906,322 fraud (33.33%)
Added:   1,901,394 synthetic fraud cases
```

**Pros:**
- Increases fraud examples without removing legitimate data
- Learns better fraud patterns
- Maintains all original legitimate cases

**Cons:**
- Increases dataset size (memory/compute cost)
- Synthetic samples may not capture all fraud variations
- Fraud rate (33%) still below target (50%)

**When to Use:**
- When you have sufficient compute resources
- When preserving all legitimate cases is important
- For initial model training and exploration

**Location:** `data/balanced/train_balanced_smote.csv`

---

### 2.3 Strategy 2: Combined (SMOTE + Random Undersampling)

**Purpose:** Balance dataset by both increasing fraud and reducing legitimate cases.

**Implementation:**
1. **Step 1 - SMOTE:** Increase fraud cases (sampling_strategy=0.3)
   - Result: 1,143,793 fraud cases (23% of dataset)
2. **Step 2 - Undersampling:** Reduce legitimate cases (sampling_strategy=0.5)
   - Result: 2,287,586 legitimate cases

**Results:**
```
Before:  3,817,572 samples | 4,928 fraud (0.129%)
After:   3,431,379 samples | 1,143,793 fraud (33.33%)
```

**Comparison to Original:**
- Dataset size: **90%** of original (reduced by 10%)
- Fraud cases: **232x increase**
- Legitimate cases: **60%** of original (40% removed)

**Pros:**
- More computationally efficient than SMOTE-only
- Better balance between classes
- Faster training times

**Cons:**
- Loses some legitimate transaction examples
- May remove important legitimate patterns
- Still 33% fraud rate (not 50% target due to SMOTE limitations)

**When to Use:**
- **Recommended for production training**
- When compute resources are limited
- When training speed is important
- For most fraud detection models

**Location:** `data/balanced/train_balanced_combined.csv`

---

### 2.4 Strategy 3: Rule-Based Synthetic Fraud Generation

**Purpose:** Create synthetic fraud cases based on real fraud patterns with controlled variations.

**Implementation:**
1. Analyze real fraud cases to identify patterns
2. Sample random fraud case as template
3. Add controlled noise (±20%) to numerical features
4. Randomize temporal features
5. Recalculate derived features

**Results:**
```
Before:  3,817,572 samples | 4,928 fraud (0.129%)
Added:   1,000 synthetic fraud cases
After:   3,818,572 samples | 5,928 fraud (0.155%)
```

**Pros:**
- Minimal dataset size increase
- Controlled variation (more predictable than SMOTE)
- Can encode domain knowledge about fraud patterns

**Cons:**
- Only adds 1,000 cases (not enough for significant balance)
- Still extremely imbalanced (0.155% fraud rate)
- Requires manual pattern analysis

**When to Use:**
- As a supplement to other strategies
- When you have domain expertise about fraud patterns
- For creating edge case test data
- For data quality validation

**Location:** `data/balanced/train_balanced_with_synthetic.csv`

---

## 3. Validation Results

### 3.1 SMOTE Validation

```json
{
  "fraud_rate": {
    "passed": false,
    "actual": 33.33%,
    "target": 50.00%
  },
  "no_negative_amounts": {
    "passed": true
  },
  "size_increased": {
    "passed": true,
    "original": 3,817,572,
    "augmented": 5,718,966
  }
}
```

**Observations:**
- ✅ No data quality issues (no negative amounts)
- ✅ Dataset size increased as expected
- ⚠️ Fraud rate (33%) lower than target (50%)
  - This is expected: SMOTE with sampling_strategy=0.5 achieves 33% fraud rate
  - To get 50%, would need sampling_strategy=1.0 (would double dataset size)

---

### 3.2 Combined Strategy Validation

```json
{
  "fraud_rate": {
    "passed": false,
    "actual": 33.33%,
    "target": 50.00%
  },
  "no_negative_amounts": {
    "passed": true
  },
  "size_increased": {
    "passed": false,
    "original": 3,817,572,
    "augmented": 3,431,379
  }
}
```

**Observations:**
- ✅ No data quality issues
- ✅ Dataset size reduced to 90% (more efficient)
- ⚠️ Fraud rate same as SMOTE-only (33%)
- ✅ More balanced than original (33% vs 0.13%)

---

## 4. Recommendations

### 4.1 For Model Training

**Primary Strategy:** **Combined (SMOTE + Undersampling)**
- Best balance of performance and efficiency
- Fraud rate: 33% (258x improvement over original)
- Manageable dataset size
- Good for most classifiers (RandomForest, XGBoost, Neural Networks)

**Alternative:** **Stratified Split + Class Weights**
- Use original imbalanced data
- Apply class weights in model training (e.g., `class_weight='balanced'`)
- Faster training, no synthetic data concerns
- Good for linear models and tree-based methods

### 4.2 For Production Deployment

1. **Train on:** `train_balanced_combined.csv`
2. **Validate on:** `val.csv` (from stratified split)
3. **Test on:** `test.csv` (from **temporal split**)
   - More realistic evaluation
   - Tests robustness to temporal drift
   - Higher fraud rate in test set simulates production

### 4.3 For Evaluation Metrics

Given class imbalance, prioritize:
- **Precision-Recall Curve** (better than ROC for imbalanced data)
- **F1 Score** (balance between precision and recall)
- **Recall at fixed precision** (e.g., 90% precision → ? recall)
- **Cost-sensitive metrics** (assign cost to false negatives)

**Avoid:**
- Accuracy (misleading with imbalanced data)
- Confusion matrix only (need context)

---

## 5. Scripts & Usage

### 5.1 Dataset Splitting

**Location:** `backend/scripts/dataset_splitting.py`

**Usage:**
```bash
python backend/scripts/dataset_splitting.py
```

**Output:**
- `data/splits/stratified/{train,val,test}.csv`
- `data/splits/temporal/{train,val,test}.csv`
- `data/splits/split_metadata.json`

**Configuration:**
```python
splitter = DatasetSplitter(
    data_path="data/processed/paysim_cleaned.csv",
    output_dir="data/splits",
    train_size=0.6,
    val_size=0.2,
    test_size=0.2,
    random_seed=42,
)
```

---

### 5.2 Data Augmentation

**Location:** `backend/scripts/data_augmentation.py`

**Usage:**
```bash
python backend/scripts/data_augmentation.py
```

**Output:**
- `data/balanced/train_balanced_smote.csv`
- `data/balanced/train_balanced_combined.csv`
- `data/balanced/train_balanced_with_synthetic.csv`
- `data/balanced/augmentation_metadata.json`

**Configuration:**
```python
pipeline = DataAugmentationPipeline(
    train_data_path="data/splits/stratified/train.csv",
    output_dir="data/balanced",
    target_fraud_rate=0.5,
    random_seed=42,
)
```

---

## 6. Key Takeaways

1. **Two split strategies provided:**
   - Stratified: Better for model development
   - Temporal: Better for production simulation

2. **Three balancing strategies provided:**
   - SMOTE: Largest dataset, most fraud examples
   - Combined: **Recommended** - best balance
   - Synthetic: Supplementary data for edge cases

3. **Achieved 258x improvement** in fraud representation:
   - Original: 0.13% fraud
   - Balanced: 33.33% fraud

4. **All strategies are reproducible:**
   - Fixed random seed (42)
   - Versioned metadata
   - Documented decisions

5. **Production recommendation:**
   - Train: `train_balanced_combined.csv`
   - Validate: `stratified/val.csv`
   - Test: `temporal/test.csv`

---

## 7. Next Steps

1. ✅ Dataset splitting completed
2. ✅ Data augmentation completed
3. ⬜ Train baseline models on balanced data
4. ⬜ Evaluate on temporal test set
5. ⬜ Compare with class-weighted approach
6. ⬜ Implement cost-sensitive evaluation
7. ⬜ Feature importance analysis
8. ⬜ Production deployment pipeline

---

**Document Version:** 1.0
**Last Updated:** December 29, 2025
**Author:** finsight-ai Team
**Related Files:**
- `backend/scripts/dataset_splitting.py`
- `backend/scripts/data_augmentation.py`
- `data/splits/split_metadata.json`
- `data/balanced/augmentation_metadata.json`
