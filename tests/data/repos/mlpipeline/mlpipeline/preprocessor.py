"""
Data preprocessing for ML pipeline
Handles feature transformation and normalization
"""

import bisect
import logging

import pandas as pd

logger = logging.getLogger(__name__)


class Preprocessor:
    """
    Data preprocessor with different paths for training and serving
    BUG #1: Offline (Pandas) vs Online (bisect) feature computation mismatch
    BUG #2: Time filtering disabled for training causing data leakage
    """

    def __init__(self, mode: str = "serving"):
        self.mode = mode  # 'training' or 'serving'
        self._transformation_cache = {}

        # Aggregation window settings
        # BUG #3: Different windows for training vs serving
        if mode == "training":
            self.aggregation_window = 21600  # 6 hours for training
        else:
            self.aggregation_window = 3600   # 1 hour for serving

    def compute_age_bucket(self, age: int) -> int:
        """
        Compute age bucket
        BUG #1: Different implementation for training vs serving
        """
        if self.mode == "training":
            # Offline training uses Pandas for batch processing
            # This is handled in batch_compute_features()
            # Individual calls use serving logic as fallback
            return self._compute_age_bucket_online(age)
        else:
            # Online serving uses Python bisect for performance
            return self._compute_age_bucket_online(age)

    def _compute_age_bucket_online(self, age: int) -> int:
        """
        Online age bucketing using bisect
        BUG #1: bisect.bisect_left gives different results than pd.cut
        """
        # BUG #1: bisect_left returns insertion point (left-inclusive)
        # For ages [18, 35, 50, 100]:
        #   age=18 -> bucket 1 (in range [18, 35))
        #   age=35 -> bucket 2 (in range [35, 50))
        bucket = bisect.bisect_left([18, 35, 50, 100], age)
        return bucket

    def batch_compute_features(self, df: pd.DataFrame, mode: str | None = None) -> pd.DataFrame:
        """
        Batch feature computation for training
        BUG #1: Uses pd.cut with different boundary semantics than bisect
        """
        if mode is None:
            mode = self.mode

        df = df.copy()

        if mode == "training":
            # Offline batch processing with Pandas
            # BUG #1: pd.cut uses right-inclusive intervals by default
            # For bins [0, 18, 35, 50, 100]:
            #   age=18 -> bucket 0 (in range (0, 18])
            #   age=35 -> bucket 1 (in range (18, 35])
            df['age_bucket'] = pd.cut(df['age'], bins=[0, 18, 35, 50, 100],
                                     labels=[0, 1, 2, 3])
        else:
            # Online processing uses bisect for each row
            df['age_bucket'] = df['age'].apply(self._compute_age_bucket_online)

        return df

    def compute_time_features(self, df: pd.DataFrame, event_timestamp: float,
                             mode: str | None = None) -> pd.DataFrame:
        """
        Compute time-based features
        BUG #2: Time filtering disabled for training
        """
        if mode is None:
            mode = self.mode

        df = df.copy()

        # BUG #2: Critical bug - time filter disabled for training
        if mode == 'training':
            # Use all data for training to maximize signal
            # BUG: This causes data leakage - includes future data!
            time_filter = None
        else:
            # Serving: correctly filter by time
            time_filter = event_timestamp

        # Apply time window for aggregations
        if time_filter is not None:
            df = df[df['timestamp'] <= time_filter]

        # Compute features within window
        df = self._compute_windowed_features(df, mode)

        return df

    def _compute_windowed_features(self, df: pd.DataFrame, mode: str) -> pd.DataFrame:
        """
        Compute features with time window
        BUG #3: Training uses 6h window, serving uses 1h window
        """
        df = df.copy()

        # Get window size based on mode
        window = self.aggregation_window

        # Compute rolling aggregates (placeholder)
        # In real implementation, would compute user-level aggregates
        df['window_size'] = window

        return df

    def normalize_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize features"""
        df = df.copy()

        # Standard normalization
        numeric_cols = df.select_dtypes(include=['int64', 'float64']).columns
        for col in numeric_cols:
            if col != 'age_bucket':  # Don't normalize categorical
                mean = df[col].mean()
                std = df[col].std()
                if std > 0:
                    df[col] = (df[col] - mean) / std

        return df

    def validate_schema(self, df: pd.DataFrame) -> bool:
        """
        Validate data schema
        Note: Only checks column names and types, not computation logic
        """
        required_columns = ['age', 'age_bucket']
        return all(col in df.columns for col in required_columns)

    def get_preprocessing_config(self) -> dict:
        """Get preprocessing configuration"""
        return {
            'mode': self.mode,
            'aggregation_window': self.aggregation_window,
        }
