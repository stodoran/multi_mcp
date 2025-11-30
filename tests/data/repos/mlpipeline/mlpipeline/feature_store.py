"""
Feature store for managing feature computation and caching
Handles both offline (batch) and online (streaming) feature generation
"""

import logging
import time
from typing import Any

from .preprocessor import Preprocessor

logger = logging.getLogger(__name__)


class FeatureCache:
    """
    Feature cache with TTL
    BUG #3: TTL mismatch with training window causes staleness
    """

    def __init__(self, ttl: int = 3600):
        self.ttl = ttl  # BUG #3: 1 hour TTL, but training uses 6 hour window
        self._cache: dict[str, tuple] = {}  # key -> (value, timestamp)

    def set(self, key: str, value: Any, ttl: int | None = None):
        """Set cache entry with TTL"""
        if ttl is None:
            ttl = self.ttl
        timestamp = time.time()
        self._cache[key] = (value, timestamp, ttl)

    def get(self, key: str) -> Any | None:
        """Get cache entry if not expired"""
        if key not in self._cache:
            return None

        value, timestamp, ttl = self._cache[key]
        age = time.time() - timestamp
        if age < ttl:
            return value

        # Expired
        del self._cache[key]
        return None

    def clear(self):
        """Clear all cache entries"""
        self._cache.clear()


class FeatureStore:
    """
    Feature store with offline and online computation paths
    BUG #1: Different computation logic for training vs serving
    BUG #2: Training includes future data (no time filtering)
    BUG #3: Cache TTL mismatch with training window
    """

    def __init__(self):
        self._cache = FeatureCache(ttl=3600)  # 1 hour cache
        self._database = {}  # Simulated database

    def get_training_features(self, user_id: int, event_timestamp: float) -> dict:
        """
        Get features for training
        BUG #1: Uses Pandas path (pd.cut)
        BUG #2: Includes future data (filter_by_time=False)
        """
        preprocessor = Preprocessor(mode='training')

        # BUG #2: Compute user_total_purchases WITHOUT time filtering
        # This creates data leakage!
        total_purchases = self._compute_user_total_purchases(
            user_id,
            event_timestamp,
            filter_by_time=False  # BUG: Includes future purchases!
        )

        # Compute other features
        age = self._get_user_age(user_id)

        # BUG #1: Batch feature computation uses pd.cut (right-inclusive)
        import pandas as pd
        df = pd.DataFrame([{'age': age}])
        df = preprocessor.batch_compute_features(df, mode='training')

        features = {
            'user_id': user_id,
            'age': age,
            'age_bucket': int(df['age_bucket'].iloc[0]),
            'total_purchases': total_purchases,
            'timestamp': event_timestamp,
        }

        return features

    def get_serving_features(self, user_id: int, request_time: float | None = None) -> dict:
        """
        Get features for serving
        BUG #1: Uses bisect path (left-inclusive)
        BUG #3: Cache may be stale or expired
        """
        if request_time is None:
            request_time = time.time()

        # Check cache first
        cache_key = f"features:{user_id}"
        cached = self._cache.get(cache_key)
        if cached:
            logger.debug(f"Cache hit for user {user_id}")
            return cached

        # Cache miss or expired: compute fresh features
        logger.debug(f"Cache miss for user {user_id}, computing fresh features")

        preprocessor = Preprocessor(mode='serving')

        # Correctly filter purchases by time for serving
        total_purchases = self._compute_user_total_purchases(
            user_id,
            request_time,
            filter_by_time=True  # Correct: only past purchases
        )

        # Compute age bucket
        age = self._get_user_age(user_id)

        # BUG #1: Online serving uses bisect (left-inclusive), different from training!
        age_bucket = preprocessor.compute_age_bucket(age)

        features = {
            'user_id': user_id,
            'age': age,
            'age_bucket': age_bucket,
            'total_purchases': total_purchases,
            'timestamp': request_time,
        }

        # Cache for future requests
        self._cache.set(cache_key, features)

        return features

    def _compute_user_total_purchases(self, user_id: int, event_timestamp: float,
                                     filter_by_time: bool = True) -> int:
        """
        Compute total purchases for user
        BUG #2: filter_by_time=False in training includes future data
        """
        # Simulate database query
        # In real implementation:
        if filter_by_time:
            # Serving: SELECT COUNT(*) FROM purchases WHERE user_id = ? AND timestamp <= ?
            query = f"SELECT COUNT(*) FROM purchases WHERE user_id = {user_id} AND timestamp <= {event_timestamp}"
        else:
            # Training: SELECT COUNT(*) FROM purchases WHERE user_id = ?
            # BUG #2: No time filter - includes ALL purchases, even future ones!
            query = f"SELECT COUNT(*) FROM purchases WHERE user_id = {user_id}"

        # Simulated result
        # In training, this would include purchases AFTER event_timestamp
        return self._execute_query(query, filter_by_time, event_timestamp)

    def _execute_query(self, query: str, filter_by_time: bool, event_timestamp: float) -> int:
        """Simulate database query execution"""
        # Placeholder - would execute actual SQL
        # Return mock value
        if filter_by_time:
            return 5  # Correct count for serving
        else:
            return 10  # Inflated count for training (includes future data)

    def _get_user_age(self, user_id: int) -> int:
        """Get user age from database"""
        # Simulate lookup
        return 35 + (user_id % 20)  # Ages between 35-54

    def warm_cache(self, user_ids: list[int]):
        """
        Warm cache with features for active users
        BUG #3: Cache warmed with 1-hour TTL, but training uses 6-hour window
        """
        logger.info(f"Warming cache for {len(user_ids)} users")
        current_time = time.time()

        for user_id in user_ids:
            features = self.get_serving_features(user_id, current_time)
            # Features cached with TTL=3600 (1 hour)
            # BUG #3: After 1 hour, cache expires but isn't refreshed until cache miss

    def get_batch_features(self, user_ids: list[int], event_timestamps: list[float]) -> list[dict]:
        """Get features for batch of users (used in training)"""
        return [
            self.get_training_features(uid, ts)
            for uid, ts in zip(user_ids, event_timestamps)
        ]

    def get_cache_stats(self) -> dict:
        """Get cache statistics"""
        return {
            'cache_size': len(self._cache._cache),
            'cache_ttl': self._cache.ttl,
        }
