"""
Feature Engineering Utilities for ML Models.

Provides feature transformation and preparation for different model types.
"""

import pandas as pd
import numpy as np
from typing import List, Optional


class FeatureEngineer:
    """
    Feature engineering for fraud detection models.

    Handles:
    - Derived features (balance differences)
    - Categorical encoding (one-hot vs native)
    - Feature ordering and consistency
    """

    def __init__(self):
        """Initialize feature engineer."""
        self.categorical_features = ['type']
        self.type_categories = ['CASH_IN', 'CASH_OUT', 'DEBIT', 'PAYMENT', 'TRANSFER']

    def prepare_features(
        self,
        df: pd.DataFrame,
        categorical_features: Optional[List[str]] = None,
        for_lightgbm: bool = False
    ) -> pd.DataFrame:
        """
        Prepare features for model input.

        Args:
            df: Input DataFrame
            categorical_features: List of categorical columns
            for_lightgbm: If True, keep categoricals as is; else one-hot encode

        Returns:
            DataFrame with prepared features
        """
        df = df.copy()

        # Create derived features if not already present
        if 'balance_diff_orig' not in df.columns:
            if 'oldbalanceOrg' in df.columns and 'newbalanceOrig' in df.columns:
                df['balance_diff_orig'] = df['oldbalanceOrg'] - df['newbalanceOrig']

        if 'balance_diff_dest' not in df.columns:
            if 'oldbalanceDest' in df.columns and 'newbalanceDest' in df.columns:
                df['balance_diff_dest'] = df['newbalanceDest'] - df['oldbalanceDest']

        # Handle categorical features
        if categorical_features is None:
            categorical_features = self.categorical_features

        if for_lightgbm:
            # LightGBM: Keep categorical as is, convert to category dtype
            for cat_col in categorical_features:
                if cat_col in df.columns:
                    df[cat_col] = pd.Categorical(
                        df[cat_col],
                        categories=self.type_categories
                    )
        else:
            # XGBoost/RandomForest: One-hot encode
            for cat_col in categorical_features:
                if cat_col in df.columns:
                    # One-hot encode
                    dummies = pd.get_dummies(df[cat_col], prefix=cat_col, drop_first=False)
                    df = pd.concat([df, dummies], axis=1)
                    # Drop original categorical column
                    df = df.drop(columns=[cat_col])

        # Remove non-feature columns if present
        cols_to_drop = [
            'isFraud', 'nameOrig', 'nameDest', 'step', 'isFlaggedFraud',
            'nameOrig_hash', 'nameDest_hash', 'time_period',  # Extra columns from data
            'prediction_timestamp', 'has_feedback',  # From prediction logging
            # Additional derived features from data preprocessing (not used by simple models)
            'amount_normalized', 'oldbalanceOrg_normalized', 'newbalanceOrig_normalized',
            'oldbalanceDest_normalized', 'newbalanceDest_normalized',
            'hour', 'day', 'day_of_week', 'balance_change_orig', 'balance_change_dest',
            'balance_change_ratio_orig', 'balance_change_ratio_dest',
            'amount_to_balance_ratio', 'zero_balance_orig', 'zero_balance_dest',
            'balance_inconsistency', 'is_high_value', 'is_round_amount'
        ]

        # Don't drop 'type' if for_lightgbm (it needs categorical column)
        if for_lightgbm:
            cols_to_drop = [col for col in cols_to_drop if col != 'type']

        df = df.drop(columns=[col for col in cols_to_drop if col in df.columns], errors='ignore')

        return df

    def get_feature_names(self, for_lightgbm: bool = False) -> List[str]:
        """
        Get expected feature names.

        Args:
            for_lightgbm: If True, return LightGBM features; else XGBoost/RF

        Returns:
            List of feature names
        """
        base_features = [
            'amount',
            'oldbalanceOrg',
            'newbalanceOrig',
            'oldbalanceDest',
            'newbalanceDest',
            'balance_diff_orig',
            'balance_diff_dest'
        ]

        if for_lightgbm:
            # LightGBM: Include categorical as-is
            return base_features + ['type']
        else:
            # XGBoost/RF: Include one-hot encoded
            type_features = [f'type_{cat}' for cat in self.type_categories]
            return base_features + type_features
