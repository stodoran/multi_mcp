"""
ML Pipeline orchestrator
Coordinates training, serving, and monitoring
"""

import logging
from typing import Any

from .ab_testing import ABTestingController
from .drift_detector import DriftDetector
from .feature_store import FeatureStore
from .metrics_tracker import MetricsTracker
from .model_registry import ModelRegistry
from .serving import ServingEngine
from .trainer import Trainer
from .validator import Validator

logger = logging.getLogger(__name__)


class Pipeline:
    """
    End-to-end ML pipeline
    Integrates all components
    """

    def __init__(self, model_id: str):
        self.model_id = model_id

        # Initialize components
        self.feature_store = FeatureStore()
        self.model_registry = ModelRegistry()
        self.drift_detector = DriftDetector()
        self.validator = Validator()
        self.metrics_tracker = MetricsTracker()

        # Training component
        self.trainer = Trainer(self.feature_store)

        # Serving component
        self.serving_engine = ServingEngine(
            model_id=model_id,
            feature_store=self.feature_store,
            model_registry=self.model_registry
        )

        # A/B testing
        self.ab_testing = ABTestingController(self.model_registry)

    def train(self, user_ids: list[int], labels: list[int],
             event_timestamps: list[float]) -> dict:
        """
        Train model
        BUG #1: Uses training features (pd.cut)
        BUG #2: Training data includes future features
        BUG #3: Uses 6-hour window
        """
        logger.info(f"Starting training for model {self.model_id}")

        # Train model
        # BUG #2: Features include future data (no time filtering)
        result = self.trainer.train_model(user_ids, labels, event_timestamps)

        model = result['model']
        metadata = result['metadata']

        # Register model
        # Determine next version
        current_version = self.model_registry.get_current_version_number(self.model_id)
        next_version = (current_version + 1) if current_version else 1

        # BUG #4: Register model (race condition: DB updates before S3)
        self.model_registry.register_model(self.model_id, model, next_version)

        logger.info(f"Model {self.model_id} v{next_version} trained and registered")

        return {
            'model_id': self.model_id,
            'version': next_version,
            'metadata': metadata,
        }

    def predict(self, user_id: int) -> float:
        """
        Make prediction
        BUG #1: Uses serving features (bisect, different from training)
        BUG #3: Features may be stale (1h cache vs 6h training window)
        BUG #4: May load wrong model version
        """
        # Get prediction
        # BUG #1: Serving uses bisect for age buckets (different from training's pd.cut)
        prediction = self.serving_engine.predict(user_id)

        # Track metrics
        version = self.serving_engine.get_loaded_model_version()
        self.metrics_tracker.record_prediction(
            self.model_id,
            user_id,
            prediction,
            version=version
        )

        return prediction

    def check_drift(self, train_data: Any, prod_data: Any, feature_name: str = "age") -> dict:
        """
        Check for distribution drift
        BUG #5: Uses binned comparison, misses subtle shifts
        """
        import numpy as np

        # Convert to arrays
        if hasattr(train_data, 'values'):
            train_array = train_data.values
        else:
            train_array = np.array(train_data)

        if hasattr(prod_data, 'values'):
            prod_array = prod_data.values
        else:
            prod_array = np.array(prod_data)

        # BUG #5: Drift detection uses binned histograms
        # Loses statistical power for subtle mean shifts
        result = self.drift_detector.detect_drift(train_array, prod_array, feature_name)

        # Track drift metrics
        self.metrics_tracker.record_drift_detection(
            feature_name,
            result['pvalue'],
            result['is_drifting']
        )

        return result

    def create_ab_test(self, experiment_id: str, control_version: int,
                      treatment_version: int, traffic_split: float = 0.5):
        """
        Create A/B test
        BUG #4: Routes based on DB version, not loaded version
        """
        self.ab_testing.create_experiment(
            experiment_id,
            self.model_id,
            control_version,
            treatment_version,
            traffic_split
        )

    def warm_cache(self, user_ids: list[int]):
        """
        Warm feature cache
        BUG #3: Cache warmed with 1h TTL, but training uses 6h window
        """
        logger.info(f"Warming cache for {len(user_ids)} users")
        self.feature_store.warm_cache(user_ids)

    def get_pipeline_stats(self) -> dict:
        """Get comprehensive pipeline statistics"""
        return {
            'model_id': self.model_id,
            'model_performance': self.metrics_tracker.get_model_performance(self.model_id),
            'drift_summary': self.metrics_tracker.get_drift_summary(),
            'cache_stats': self.feature_store.get_cache_stats(),
            'training_stats': self.trainer.get_training_stats(),
        }

    def validate_pipeline(self) -> dict:
        """
        Validate pipeline health
        DECOY: Runs validators but they miss the bugs
        """
        # Check feature schema
        sample_features = self.feature_store.get_serving_features(user_id=1)
        schema_valid = self.validator.validate_features(sample_features)

        # Check data quality (placeholder)
        # In real implementation, would validate entire dataset

        return {
            'schema_valid': schema_valid,
            'note': 'Schema validation passed, but computation logic may still have bugs',
        }
