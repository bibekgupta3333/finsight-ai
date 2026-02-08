#!/usr/bin/env python3
"""
Data Quality Check Script for FinSight AI
Validates data quality across all pipeline stages.

Author: FinSight AI Team
Date: February 8, 2026
"""

import pandas as pd
import json
from pathlib import Path
import argparse


def check_data_quality():
    """
    Run comprehensive data quality checks on all processed datasets.
    """
    print("="*80)
    print("FinSight AI Data Quality Check")
    print("="*80)
    
    # Load all datasets
    print("\n[1/4] Loading datasets...")
    train_strat = pd.read_csv('data/splits/stratified/train.csv')
    train_temp = pd.read_csv('data/splits/temporal/train.csv')
    train_balanced = pd.read_csv('data/balanced/train_balanced_smote.csv')
    print("✓ All datasets loaded successfully")
    
    # Calculate quality metrics
    print("\n[2/4] Calculating quality metrics...")
    quality_metrics = {
        'stratified_train_shape': list(train_strat.shape),
        'temporal_train_shape': list(train_temp.shape),
        'balanced_train_shape': list(train_balanced.shape),
        'stratified_fraud_rate': float(train_strat['isFraud'].mean()),
        'temporal_fraud_rate': float(train_temp['isFraud'].mean()),
        'balanced_fraud_rate': float(train_balanced['isFraud'].mean()),
        'missing_values_stratified': int(train_strat.isnull().sum().sum()),
        'missing_values_temporal': int(train_temp.isnull().sum().sum()),
        'missing_values_balanced': int(train_balanced.isnull().sum().sum()),
        'duplicates_stratified': int(train_strat.duplicated().sum()),
        'duplicates_temporal': int(train_temp.duplicated().sum()),
        'duplicates_balanced': int(train_balanced.duplicated().sum())
    }
    print("✓ Quality metrics calculated")
    
    # Save metrics
    print("\n[3/4] Saving quality report...")
    Path('data/analysis').mkdir(exist_ok=True)
    with open('data/analysis/data_quality_report.json', 'w') as f:
        json.dump(quality_metrics, f, indent=2)
    print("✓ Report saved to data/analysis/data_quality_report.json")
    
    # Print summary
    print("\n[4/4] Quality Check Summary:")
    print("-"*80)
    print(f"Stratified train shape: {quality_metrics['stratified_train_shape']}")
    print(f"Temporal train shape:   {quality_metrics['temporal_train_shape']}")
    print(f"Balanced train shape:   {quality_metrics['balanced_train_shape']}")
    print()
    print(f"Stratified fraud rate:  {quality_metrics['stratified_fraud_rate']:.4%}")
    print(f"Temporal fraud rate:    {quality_metrics['temporal_fraud_rate']:.4%}")
    print(f"Balanced fraud rate:    {quality_metrics['balanced_fraud_rate']:.4%}")
    print()
    print(f"Missing values (stratified): {quality_metrics['missing_values_stratified']}")
    print(f"Missing values (temporal):   {quality_metrics['missing_values_temporal']}")
    print(f"Missing values (balanced):   {quality_metrics['missing_values_balanced']}")
    print()
    print(f"Duplicates (stratified): {quality_metrics['duplicates_stratified']}")
    print(f"Duplicates (temporal):   {quality_metrics['duplicates_temporal']}")
    print(f"Duplicates (balanced):   {quality_metrics['duplicates_balanced']}")
    print("-"*80)
    
    # Validation checks
    print("\n✓ Data quality check complete!")
    
    # Check for issues
    issues = []
    if quality_metrics['missing_values_stratified'] > 0:
        issues.append("Stratified dataset has missing values")
    if quality_metrics['missing_values_temporal'] > 0:
        issues.append("Temporal dataset has missing values")
    if quality_metrics['missing_values_balanced'] > 0:
        issues.append("Balanced dataset has missing values")
    
    if issues:
        print("\n⚠️  Issues found:")
        for issue in issues:
            print(f"  - {issue}")
        return 1
    else:
        print("\n✅ All quality checks passed!")
        return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run data quality checks")
    parser.add_argument('--strict', action='store_true', help='Fail on any quality issues')
    args = parser.parse_args()
    
    exit_code = check_data_quality()
    exit(exit_code if args.strict else 0)
