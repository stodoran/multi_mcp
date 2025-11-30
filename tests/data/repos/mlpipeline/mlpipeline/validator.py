"""
Data validation
Validates feature schemas and data quality
"""

import logging
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)


class Validator:
    """
    Data validator for features and labels
    DECOY: Checks schema match but not computation logic
    """

    def __init__(self):
        self._expected_schema = {
            'user_id': int,
            'age': int,
            'age_bucket': int,
            'total_purchases': int,
            'timestamp': float,
        }

    def validate_features(self, features: dict) -> bool:
        """
        Validate feature dictionary
        DECOY: Only validates schema (column names, types), not computation logic
        """
        # Check all required fields present
        for field, expected_type in self._expected_schema.items():
            if field not in features:
                logger.error(f"Missing field: {field}")
                return False

            # Check type
            if not isinstance(features[field], expected_type):
                logger.error(f"Type mismatch for {field}: expected {expected_type}, got {type(features[field])}")
                return False

        # Check for nulls
        for field, value in features.items():
            if value is None:
                logger.error(f"Null value for {field}")
                return False

        return True

    def validate_temporal_consistency(self, features: list[dict], labels: list[Any],
                                     timestamps: list[float]) -> bool:
        """
        Validate temporal consistency
        DECOY: Checks feature timestamp ≤ label timestamp,
        but doesn't check if aggregates include future data
        """
        for feat, label, ts in zip(features, labels, timestamps):
            feat_timestamp = feat.get('timestamp', 0)

            # Check feature computed before label
            # DECOY: This passes even with data leakage!
            # Because feat['timestamp'] is event_timestamp (correct)
            # But feat['total_purchases'] may include future data
            if feat_timestamp > ts:
                logger.error(f"Feature timestamp {feat_timestamp} > label timestamp {ts}")
                return False

        return True

    def validate_feature_distributions(self, train_features: pd.DataFrame,
                                      serve_features: pd.DataFrame) -> bool:
        """
        Validate feature distributions match between train and serve
        DECOY: Uses KS test on overall distributions,
        which passes even with boundary mismatches affecting only 3 values
        """
        from scipy import stats

        for col in train_features.columns:
            if col in serve_features.columns:
                # KS test on distributions
                stat, pvalue = stats.ks_2samp(
                    train_features[col].dropna(),
                    serve_features[col].dropna()
                )

                # DECOY: This passes even with age bucket boundary mismatch
                # because only ages 18, 35, 50 are affected (tiny fraction)
                if pvalue < 0.01:  # Very conservative threshold
                    logger.warning(f"Distribution mismatch for {col}: p={pvalue:.4f}")
                    return False

        return True

    def validate_no_data_leakage(self, features: dict, event_timestamp: float) -> bool:
        """
        Validate no data leakage
        DECOY: Only checks timestamp, not feature computation
        """
        feat_timestamp = features.get('timestamp', 0)

        # DECOY: Checks feature timestamp, but doesn't verify
        # that aggregated features (like total_purchases) only use past data
        if feat_timestamp > event_timestamp:
            logger.error(f"Data leakage detected: feature timestamp {feat_timestamp} > event timestamp {event_timestamp}")
            return False

        return True

    def check_data_quality(self, df: pd.DataFrame) -> dict:
        """Check data quality metrics"""
        return {
            'num_rows': len(df),
            'num_nulls': df.isnull().sum().sum(),
            'num_duplicates': df.duplicated().sum(),
        }
