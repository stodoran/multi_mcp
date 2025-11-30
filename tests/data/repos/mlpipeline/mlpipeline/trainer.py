"""
Model trainer
Handles model training with hyperparameter tracking
"""

import logging
import time
from typing import Any

from .feature_store import FeatureStore
from .preprocessor import Preprocessor

logger = logging.getLogger(__name__)


class Trainer:
    """
    Model trainer with batch processing
    BUG #1: Trains on Pandas features (pd.cut boundaries)
    BUG #2: Training data includes future features (data leakage)
    BUG #3: Fixed snapshot time, 6-hour window
    """

    def __init__(self, feature_store: FeatureStore):
        self.feature_store = feature_store
        self.preprocessor = Preprocessor(mode='training')
        self._training_config = {
            'batch_window': 21600,  # 6 hours - BUG #3: Different from serving (1h)
            'snapshot_mode': 'point_in_time',
        }

    def train_model(self, user_ids: list[int], labels: list[int],
                   event_timestamps: list[float]) -> dict:
        """
        Train model on batch data
        BUG #1: Uses features computed with pd.cut (different from serving)
        BUG #2: Features include future data
        """
        logger.info(f"Training model on {len(user_ids)} examples")

        # Get training features
        # BUG #2: Features computed without time filtering
        features = self.feature_store.get_batch_features(user_ids, event_timestamps)

        # Extract feature matrix
        import pandas as pd
        df = pd.DataFrame(features)

        # BUG #1: Age buckets computed with pd.cut in batch_compute_features
        # This differs from serving which uses bisect

        # Preprocess features
        # BUG #3: Uses 6-hour aggregation window (different from serving's 1-hour)
        df = self.preprocessor.compute_time_features(df, max(event_timestamps), mode='training')
        df = self.preprocessor.normalize_features(df)

        # Train model (simplified)
        model = self._fit_model(df, labels)

        # Track training metadata
        metadata = {
            'num_examples': len(user_ids),
            'feature_columns': list(df.columns),
            'training_window': self._training_config['batch_window'],
            'snapshot_time': max(event_timestamps),
        }

        logger.info(f"Training completed: {metadata}")

        return {
            'model': model,
            'metadata': metadata,
        }

    def _fit_model(self, features: Any, labels: list[int]) -> Any:
        """
        Fit ML model
        Simplified - in reality would use sklearn, xgboost, etc.
        """
        # Placeholder for actual model training
        # In real implementation:
        # from sklearn.ensemble import RandomForestClassifier
        # model = RandomForestClassifier()
        # model.fit(features, labels)

        model = {
            'type': 'logistic_regression',
            'coefficients': [0.5, 0.3, 0.2],  # Mock coefficients
            'trained_at': time.time(),
        }

        return model

    def validate_training_data(self, features: list[dict], labels: list[int]) -> bool:
        """
        Validate training data
        Note: Only checks nulls, not temporal consistency
        """
        if len(features) != len(labels):
            return False

        # Check for nulls
        for feature_dict in features:
            if any(v is None for v in feature_dict.values()):
                return False

        return True

    def get_training_stats(self) -> dict:
        """Get training statistics"""
        return {
            'batch_window': self._training_config['batch_window'],
            'snapshot_mode': self._training_config['snapshot_mode'],
        }
