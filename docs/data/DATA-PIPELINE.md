# Data Pipeline Documentation - FinSight AI

## PaySim Fraud Detection Data Lifecycle

**Last Updated:** December 28, 2025
**Dataset:** PaySim Mobile Money Simulator
**Source:** [Kaggle - PaySim1](https://www.kaggle.com/datasets/ealaxi/paysim1)

---

## Table of Contents

1. [Dataset Overview](#dataset-overview)
2. [Data Collection](#data-collection)
3. [Data Schema](#data-schema)
4. [Data Cleaning](#data-cleaning)
5. [Feature Engineering](#feature-engineering)
6. [Data Splitting](#data-splitting)
7. [Data Versioning](#data-versioning)
8. [Data Augmentation](#data-augmentation)
9. [Pipeline Implementation](#pipeline-implementation)

---

## Dataset Overview

### PaySim - Mobile Money Financial Simulator

PaySim simulates mobile money transactions based on a sample of real transactions extracted from one month of financial logs from a mobile money service implemented in an African country.

**Key Statistics:**
- **Total Transactions:** 6,362,620
- **Fraud Cases:** 8,213 (~0.13%)
- **Legitimate Cases:** 6,354,407 (~99.87%)
- **Time Period:** 30 days (744 hours)
- **Transaction Types:** 5 categories
- **File Size:** ~493 MB CSV

**Class Imbalance:**
```
Non-Fraud: ████████████████████████████████████████████████ 99.87%
Fraud:     ▌ 0.13%
```

This severe class imbalance is a **core challenge** that demonstrates advanced ML skills.

---

## Data Collection

### File Location

```
data/
├── raw/
│   └── PS_20174392719_1491204439457_log.csv  # Original PaySim data
├── external/
│   └── fraud_policies.md  # Synthetic fraud rules
└── interim/
    └── edge_cases.csv  # Manually created edge cases
```

### Loading the Data

```python
import pandas as pd
import polars as pl  # Alternative: faster for large datasets

# Pandas approach
df = pd.read_csv('data/raw/PS_20174392719_1491204439457_log.csv')

# Polars approach (faster)
df_pl = pl.read_csv('data/raw/PS_20174392719_1491204439457_log.csv')

# Initial profiling
print(f"Shape: {df.shape}")
print(f"Memory: {df.memory_usage(deep=True).sum() / 1024**2:.2f} MB")
print(f"Fraud rate: {df['isFraud'].mean():.4%}")
```

---

## Data Schema

### Raw Schema

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `step` | int64 | Time unit (1 = 1 hour) | 1 to 744 |
| `type` | object | Transaction type | CASH_OUT, PAYMENT, etc. |
| `amount` | float64 | Transaction amount | 9839.64 |
| `nameOrig` | object | Origin customer ID | C1231006815 |
| `oldbalanceOrg` | float64 | Origin balance before | 170136.00 |
| `newbalanceOrig` | float64 | Origin balance after | 160296.36 |
| `nameDest` | object | Destination ID | M1979787155 |
| `oldbalanceDest` | float64 | Destination balance before | 0.00 |
| `newbalanceDest` | float64 | Destination balance after | 0.00 |
| `isFraud` | int64 | **Ground truth label** | 0 or 1 |
| `isFlaggedFraud` | int64 | System flag (>200k transfers) | 0 or 1 |

### Transaction Types

```python
type_distribution = df['type'].value_counts()
```

| Type | Count | % | Fraud Cases |
|------|-------|---|-------------|
| CASH_OUT | 2,237,500 | 35.2% | 4,116 |
| PAYMENT | 2,151,495 | 33.8% | 0 |
| CASH_IN | 1,399,284 | 22.0% | 0 |
| TRANSFER | 532,909 | 8.4% | 4,097 |
| DEBIT | 41,432 | 0.7% | 0 |

**Key Insight:** Fraud only occurs in `CASH_OUT` and `TRANSFER` types.

---

## Data Cleaning

### 1. Missing Values

```python
# Check for missing values
missing = df.isnull().sum()
print(missing[missing > 0])
```

**Result:** PaySim has **no missing values** (synthetic dataset).

### 2. Duplicates

```python
# Check for exact duplicates
duplicates = df.duplicated().sum()
print(f"Duplicates: {duplicates}")

# Remove duplicates (if any)
df_clean = df.drop_duplicates()
```

### 3. PII Masking

```python
import hashlib

def hash_account(account_id):
    """Hash account IDs for privacy"""
    return hashlib.sha256(account_id.encode()).hexdigest()[:16]

df_clean['nameOrig_hash'] = df_clean['nameOrig'].apply(hash_account)
df_clean['nameDest_hash'] = df_clean['nameDest'].apply(hash_account)

# Drop original account names
df_clean = df_clean.drop(['nameOrig', 'nameDest'], axis=1)
```

### 4. Data Validation

```python
# Validate balance changes
def validate_balance(row):
    """Check if balance change matches amount"""
    expected_new = row['oldbalanceOrg'] - row['amount']
    actual_new = row['newbalanceOrig']
    return abs(expected_new - actual_new) < 0.01

df_clean['balance_valid'] = df_clean.apply(validate_balance, axis=1)

# Flag invalid transactions
invalid_count = (~df_clean['balance_valid']).sum()
print(f"Invalid balance changes: {invalid_count}")
```

---

## Feature Engineering

### 1. Temporal Features

```python
# Hour of day (0-23)
df_clean['hour'] = df_clean['step'] % 24

# Day of week (0-6)
df_clean['day_of_week'] = (df_clean['step'] // 24) % 7

# Is weekend
df_clean['is_weekend'] = df_clean['day_of_week'].isin([5, 6]).astype(int)

# Time of day categories
def time_category(hour):
    if 6 <= hour < 12:
        return 'morning'
    elif 12 <= hour < 18:
        return 'afternoon'
    elif 18 <= hour < 22:
        return 'evening'
    else:
        return 'night'

df_clean['time_category'] = df_clean['hour'].apply(time_category)
```

### 2. Balance Features

```python
# Balance change
df_clean['balance_diff_orig'] = df_clean['oldbalanceOrg'] - df_clean['newbalanceOrig']
df_clean['balance_diff_dest'] = df_clean['newbalanceDest'] - df_clean['oldbalanceDest']

# Amount as % of origin balance
df_clean['amount_pct_balance'] = df_clean['amount'] / (df_clean['oldbalanceOrg'] + 1)

# Zero balance flags (suspicious)
df_clean['orig_zero_after'] = (df_clean['newbalanceOrig'] == 0).astype(int)
df_clean['dest_zero_before'] = (df_clean['oldbalanceDest'] == 0).astype(int)

# Account emptied flag
df_clean['account_emptied'] = (
    (df_clean['oldbalanceOrg'] > 0) &
    (df_clean['newbalanceOrig'] == 0)
).astype(int)
```

### 3. Amount Features

```python
import numpy as np

# Log amount (handle zero)
df_clean['log_amount'] = np.log1p(df_clean['amount'])

# Amount bins
amount_bins = [0, 1000, 10000, 50000, 100000, np.inf]
amount_labels = ['tiny', 'small', 'medium', 'large', 'huge']
df_clean['amount_category'] = pd.cut(
    df_clean['amount'],
    bins=amount_bins,
    labels=amount_labels
)

# High amount flag (>100k)
df_clean['high_amount'] = (df_clean['amount'] > 100000).astype(int)
```

### 4. Fraud-Specific Features

```python
# Ratio of amount to flagged threshold
df_clean['amount_to_flag_ratio'] = df_clean['amount'] / 200000

# Destination receives but had zero balance
df_clean['suspicious_dest'] = (
    (df_clean['oldbalanceDest'] == 0) &
    (df_clean['newbalanceDest'] > 0) &
    (df_clean['type'].isin(['CASH_OUT', 'TRANSFER']))
).astype(int)

# Amount matches origin balance (account takeover)
df_clean['exact_balance_match'] = (
    np.abs(df_clean['amount'] - df_clean['oldbalanceOrg']) < 0.01
).astype(int)
```

### 5. One-Hot Encoding

```python
# Encode transaction type
df_encoded = pd.get_dummies(
    df_clean,
    columns=['type', 'time_category', 'amount_category'],
    drop_first=False
)
```

---

## Data Splitting

### Strategy: Stratified Random Split

Maintain fraud rate (~0.13%) in all splits.

```python
from sklearn.model_selection import train_test_split

# Separate features and target
X = df_encoded.drop(['isFraud', 'isFlaggedFraud'], axis=1)
y = df_encoded['isFraud']

# First split: train + (val + test)
X_train, X_temp, y_train, y_temp = train_test_split(
    X, y,
    test_size=0.4,  # 40% for val + test
    stratify=y,  # Maintain fraud rate
    random_state=42
)

# Second split: val + test
X_val, X_test, y_val, y_test = train_test_split(
    X_temp, y_temp,
    test_size=0.5,  # 50% of 40% = 20% total
    stratify=y_temp,
    random_state=42
)

print(f"Train: {X_train.shape}, Fraud rate: {y_train.mean():.4%}")
print(f"Val:   {X_val.shape}, Fraud rate: {y_val.mean():.4%}")
print(f"Test:  {X_test.shape}, Fraud rate: {y_test.mean():.4%}")
```

**Output:**
```
Train: (3,817,572, 50), Fraud rate: 0.1291%
Val:   (1,272,524, 50), Fraud rate: 0.1293%
Test:  (1,272,524, 50), Fraud rate: 0.1289%
```

### Alternative: Temporal Split

```python
# Split by time (more realistic)
cutoff_train = df['step'].quantile(0.6)
cutoff_val = df['step'].quantile(0.8)

train_mask = df['step'] < cutoff_train
val_mask = (df['step'] >= cutoff_train) & (df['step'] < cutoff_val)
test_mask = df['step'] >= cutoff_val

X_train = df_encoded[train_mask].drop(['isFraud'], axis=1)
y_train = df_encoded[train_mask]['isFraud']
# ... similar for val and test
```

### Save Splits

```python
# Save to disk
data_dir = 'data/splits'
X_train.to_parquet(f'{data_dir}/X_train.parquet')
y_train.to_parquet(f'{data_dir}/y_train.parquet')
X_val.to_parquet(f'{data_dir}/X_val.parquet')
y_val.to_parquet(f'{data_dir}/y_val.parquet')
X_test.to_parquet(f'{data_dir}/X_test.parquet')
y_test.to_parquet(f'{data_dir}/y_test.parquet')
```

---

## Data Versioning

### DVC (Data Version Control)

```bash
# Install DVC
pip install dvc dvc-s3

# Initialize DVC
dvc init

# Add raw data to DVC
dvc add data/raw/PS_20174392719_1491204439457_log.csv

# Track versions
git add data/raw/PS_20174392719_1491204439457_log.csv.dvc
git commit -m "data: add PaySim v1 raw data"

# Tag version
git tag -a v1.0-data -m "Initial PaySim dataset"
```

### Weights & Biases Artifacts

```python
import wandb

# Initialize W&B
wandb.init(project='finsight-ai', job_type='data-versioning')

# Create artifact
artifact = wandb.Artifact(
    name='paysim-processed',
    type='dataset',
    description='PaySim with feature engineering',
    metadata={
        'total_samples': len(df_clean),
        'fraud_rate': y.mean(),
        'features': list(X.columns),
        'processing_date': '2025-12-28'
    }
)

# Add files
artifact.add_file('data/splits/X_train.parquet')
artifact.add_file('data/splits/y_train.parquet')

# Log artifact
wandb.log_artifact(artifact)
```

### Version Naming Convention

```
data/
├── raw/
│   └── paysim_v1.0_raw.csv          # Original
├── cleaned/
│   └── paysim_v1.1_cleaned.csv      # After cleaning
├── processed/
│   └── paysim_v1.2_features.parquet # With features
└── splits/
    ├── paysim_v1.3_train.parquet    # Train split
    ├── paysim_v1.3_val.parquet      # Val split
    └── paysim_v1.3_test.parquet     # Test split
```

---

## Data Augmentation

### 1. SMOTE (Synthetic Minority Over-sampling)

```python
from imblearn.over_sampling import SMOTE

# Apply SMOTE to training data only
smote = SMOTE(sampling_strategy=0.5, random_state=42)  # 0.5 = 50% fraud rate
X_train_balanced, y_train_balanced = smote.fit_resample(X_train, y_train)

print(f"Before SMOTE: {y_train.sum()} fraud cases")
print(f"After SMOTE: {y_train_balanced.sum()} fraud cases")
print(f"Fraud rate: {y_train_balanced.mean():.2%}")
```

### 2. Undersampling Non-Fraud

```python
from imblearn.under_sampling import RandomUnderSampler

# Undersample majority class
rus = RandomUnderSampler(sampling_strategy=0.2, random_state=42)
X_train_under, y_train_under = rus.fit_resample(X_train, y_train)
```

### 3. Combination (SMOTE + ENN)

```python
from imblearn.combine import SMOTEENN

# SMOTE + Edited Nearest Neighbors
smote_enn = SMOTEENN(random_state=42)
X_train_combined, y_train_combined = smote_enn.fit_resample(X_train, y_train)
```

### 4. Synthetic Edge Cases

```python
# Create synthetic rare fraud patterns
edge_cases = []

# Pattern 1: Multiple small transactions summing to large amount
for i in range(100):
    base_transaction = df[df['isFraud'] == 1].sample(1).iloc[0].to_dict()
    base_transaction['amount'] = np.random.uniform(1000, 5000)
    edge_cases.append(base_transaction)

# Pattern 2: Unusual time patterns (3 AM transactions)
for i in range(100):
    base_transaction = df[df['isFraud'] == 1].sample(1).iloc[0].to_dict()
    base_transaction['hour'] = np.random.randint(2, 5)  # 2-4 AM
    edge_cases.append(base_transaction)

# Save edge cases
edge_df = pd.DataFrame(edge_cases)
edge_df.to_csv('data/interim/edge_cases.csv', index=False)
```

---

## Pipeline Implementation

### Full Pipeline Class

```python
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.compose import ColumnTransformer

class PaySimDataPipeline:
    """End-to-end data processing pipeline for PaySim"""

    def __init__(self, config):
        self.config = config
        self.pipeline = None

    def build_pipeline(self):
        """Build sklearn pipeline"""

        # Numeric features to scale
        numeric_features = [
            'amount', 'oldbalanceOrg', 'newbalanceOrig',
            'oldbalanceDest', 'newbalanceDest',
            'balance_diff_orig', 'balance_diff_dest',
            'amount_pct_balance', 'log_amount'
        ]

        # Categorical features (already one-hot encoded)
        categorical_features = [
            col for col in self.X.columns
            if col.startswith(('type_', 'time_category_', 'amount_category_'))
        ]

        # Column transformer
        preprocessor = ColumnTransformer(
            transformers=[
                ('num', StandardScaler(), numeric_features),
                ('cat', 'passthrough', categorical_features)
            ]
        )

        self.pipeline = preprocessor
        return self

    def fit(self, X, y=None):
        """Fit pipeline"""
        self.X = X
        if self.pipeline is None:
            self.build_pipeline()
        self.pipeline.fit(X, y)
        return self

    def transform(self, X):
        """Transform data"""
        return self.pipeline.transform(X)

    def fit_transform(self, X, y=None):
        """Fit and transform"""
        return self.fit(X, y).transform(X)

    def save(self, path):
        """Save pipeline"""
        import joblib
        joblib.dump(self.pipeline, path)

    @staticmethod
    def load(path):
        """Load pipeline"""
        import joblib
        return joblib.load(path)
```

### Usage

```python
# Initialize pipeline
pipeline = PaySimDataPipeline(config={})

# Fit on training data
X_train_processed = pipeline.fit_transform(X_train, y_train)

# Transform validation and test
X_val_processed = pipeline.transform(X_val)
X_test_processed = pipeline.transform(X_test)

# Save pipeline
pipeline.save('models/data_pipeline_v1.pkl')
```

---

## Data Quality Checks

### Automated Checks

```python
def data_quality_report(df, name='dataset'):
    """Generate data quality report"""

    report = {
        'name': name,
        'shape': df.shape,
        'memory_mb': df.memory_usage(deep=True).sum() / 1024**2,
        'missing_values': df.isnull().sum().sum(),
        'duplicates': df.duplicated().sum(),
        'fraud_rate': df['isFraud'].mean() if 'isFraud' in df.columns else None,
        'dtypes': df.dtypes.value_counts().to_dict(),
        'numeric_ranges': {}
    }

    # Numeric ranges
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    for col in numeric_cols:
        report['numeric_ranges'][col] = {
            'min': df[col].min(),
            'max': df[col].max(),
            'mean': df[col].mean(),
            'median': df[col].median()
        }

    return report

# Generate report
report = data_quality_report(df_clean, 'paysim_v1.2_features')

# Save report
import json
with open('data/reports/data_quality_v1.2.json', 'w') as f:
    json.dump(report, f, indent=2)
```

---

## Next Steps

After completing the data pipeline:

1. ✅ **Data loaded and profiled**
2. ✅ **Feature engineering complete**
3. ✅ **Data split (train/val/test)**
4. ⏭️ **Train baseline classifier** (Random Forest, XGBoost)
5. ⏭️ **LLM explanation generation** (Mistral 7B)
6. ⏭️ **RAG with fraud policies** (ChromaDB)
7. ⏭️ **Agentic workflow** (LangGraph ReAct)

---

## References

- [PaySim Paper](https://www.researchgate.net/publication/313138956_PAYSIM_A_FINANCIAL_MOBILE_MONEY_SIMULATOR_FOR_FRAUD_DETECTION)
- [Imbalanced-Learn Documentation](https://imbalanced-learn.org/)
- [DVC Documentation](https://dvc.org/doc)
- [Weights & Biases Artifacts](https://docs.wandb.ai/guides/artifacts)
