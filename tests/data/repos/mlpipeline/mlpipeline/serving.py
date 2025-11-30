"""
Model serving engine
Handles online prediction requests
"""

import logging
import time
from typing import Any

from .feature_store import FeatureStore
from .model_registry import ModelRegistry

logger = logging.getLogger(__name__)


class ServingEngine:
    """
    Model serving with feature fetching and prediction
    BUG #1: Uses online features (bisect) different from training (pd.cut)
    BUG #3: Cache may expire, serving uses different window than training
    BUG #4: May load wrong model version due to race condition
    """

    def __init__(self, model_id: str, feature_store: FeatureStore,
                 model_registry: ModelRegistry):
        self.model_id = model_id
        self.feature_store = feature_store
        self.model_registry = model_registry

        self._model_cache: dict[int, Any] = {}  # version -> model
        self._current_version: int | None = None
        self._version_poll_interval = 10  # Poll database every 10 seconds
        self._last_poll_time = 0

    def predict(self, user_id: int) -> float:
        """
        Make prediction for user
        BUG #1: Uses online features (different from training)
        BUG #3: Features may be stale (cache expired)
        BUG #4: May use wrong model version
        """
        request_time = time.time()

        # Get model (may trigger version check)
        model = self._get_loaded_model()

        if model is None:
            raise Exception(f"Failed to load model {self.model_id}")

        # BUG #1: Get serving features (uses bisect, different from training's pd.cut)
        # BUG #3: Features from cache (1h TTL) or fresh (1h window)
        #         Training used 6h window, creating distribution mismatch
        features = self.feature_store.get_serving_features(user_id, request_time)

        # Make prediction
        prediction = self._predict_with_model(model, features)

        return prediction

    def _get_loaded_model(self) -> Any | None:
        """
        Get loaded model, checking for version updates
        BUG #4: Race condition with database vs S3
        """
        # Poll database for version updates
        if time.time() - self._last_poll_time > self._version_poll_interval:
            self._check_for_version_update()
            self._last_poll_time = time.time()

        # Return cached model
        if self._current_version in self._model_cache:
            return self._model_cache[self._current_version]

        # Need to load model
        return self._load_model()

    def _check_for_version_update(self):
        """
        Check database for new model version
        BUG #4: Database may have new version before S3 upload completes
        """
        # Query database for current version
        db_version = self.model_registry.get_current_version_number(self.model_id)

        if db_version is None:
            return

        if self._current_version is None or db_version > self._current_version:
            logger.info(f"New model version detected: v{db_version}")
            # Trigger model load
            self._current_version = db_version
            # Clear cache to force reload
            self._model_cache.clear()

    def _load_model(self) -> Any | None:
        """
        Load model from registry
        BUG #4: Download may fail if S3 upload not complete
        """
        if self._current_version is None:
            self._current_version = self.model_registry.get_current_version_number(self.model_id)

        if self._current_version is None:
            return None

        logger.info(f"Loading model {self.model_id} v{self._current_version}")

        # BUG #4: Attempt S3 download - may get 404 if upload incomplete!
        # Retry logic with short timeout doesn't help (upload takes 30s)
        model = self._download_with_retry(self._current_version)

        if model is None:
            # BUG #4: Fall back to cached model (old version)
            logger.warning(f"Failed to download v{self._current_version}, using cached model")
            if self._model_cache:
                # Return any cached model (likely N-1)
                return list(self._model_cache.values())[0]
            return None

        # Cache the model
        self._model_cache[self._current_version] = model

        return model

    def _download_with_retry(self, version: int, retries: int = 3) -> Any | None:
        """
        Download model with retry
        BUG #4: Retries too fast (1s delay × 3 = 3s total), upload takes 30s
        """
        for attempt in range(retries):
            try:
                model = self.model_registry.get_model(self.model_id, version)
                if model is not None:
                    return model

                if attempt < retries - 1:
                    logger.warning(f"Download attempt {attempt + 1} failed, retrying...")
                    time.sleep(1)  # BUG #4: Only 1 second delay, too short

            except Exception as e:
                logger.error(f"Download failed: {e}")
                if attempt < retries - 1:
                    time.sleep(1)

        return None

    def _predict_with_model(self, model: Any, features: dict) -> float:
        """Make prediction with loaded model"""
        # Simplified prediction logic
        # In real implementation: model.predict(features)

        # Extract feature values
        age_bucket = features.get('age_bucket', 0)
        total_purchases = features.get('total_purchases', 0)

        # Mock prediction using model coefficients
        if isinstance(model, dict) and 'coefficients' in model:
            coeffs = model['coefficients']
            prediction = coeffs[0] * age_bucket + coeffs[1] * total_purchases + coeffs[2]
        else:
            prediction = 0.5  # Default

        return prediction

    def get_loaded_model_version(self) -> int | None:
        """Get currently loaded model version"""
        if self._model_cache:
            # Return version of cached model
            return list(self._model_cache.keys())[0]
        return None

    def force_reload(self):
        """Force model reload"""
        self._model_cache.clear()
        self._current_version = None
        self._load_model()
