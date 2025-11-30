"""
Metrics tracking for ML pipeline
Tracks model performance, data drift, and system health
"""

import logging
import time
from collections import defaultdict

logger = logging.getLogger(__name__)


class MetricsTracker:
    """
    Tracks pipeline metrics
    Used by drift detector, serving engine, and A/B testing
    """

    def __init__(self):
        self._prediction_metrics: list[dict] = []
        self._drift_metrics: list[dict] = []
        self._model_versions: dict[str, int] = {}  # model_id -> version
        self._performance_metrics: dict[str, list[float]] = defaultdict(list)

    def record_prediction(self, model_id: str, user_id: int, prediction: float,
                         actual: float | None = None, version: int | None = None):
        """
        Record prediction
        BUG #4: Records version from metadata, not actual loaded version
        """
        metric = {
            'model_id': model_id,
            'user_id': user_id,
            'prediction': prediction,
            'actual': actual,
            'version': version,  # BUG #4: May not match loaded version
            'timestamp': time.time(),
        }

        self._prediction_metrics.append(metric)

        # Track active version
        if version is not None:
            self._model_versions[model_id] = version

        # Record latency/performance
        if actual is not None:
            error = abs(prediction - actual)
            self._performance_metrics[f"{model_id}_error"].append(error)

    def record_drift_detection(self, feature_name: str, pvalue: float,
                              is_drifting: bool):
        """
        Record drift detection result
        BUG #5: Records drift status but not comparison method details
        """
        metric = {
            'feature': feature_name,
            'pvalue': pvalue,
            'is_drifting': is_drifting,
            'timestamp': time.time(),
        }

        self._drift_metrics.append(metric)

        if is_drifting:
            logger.warning(f"Drift detected for {feature_name}: p={pvalue:.4f}")

    def get_model_performance(self, model_id: str) -> dict:
        """Get model performance metrics"""
        # Filter predictions for this model
        model_predictions = [
            p for p in self._prediction_metrics
            if p['model_id'] == model_id and p['actual'] is not None
        ]

        if not model_predictions:
            return {
                'num_predictions': 0,
                'mean_error': None,
            }

        errors = [abs(p['prediction'] - p['actual']) for p in model_predictions]

        return {
            'num_predictions': len(model_predictions),
            'mean_error': sum(errors) / len(errors) if errors else None,
            'active_version': self._model_versions.get(model_id),
        }

    def get_drift_summary(self) -> dict:
        """
        Get drift detection summary
        Shows drift status but not underlying comparison details
        """
        if not self._drift_metrics:
            return {'num_checks': 0}

        drifting_features = [m['feature'] for m in self._drift_metrics if m['is_drifting']]

        return {
            'num_checks': len(self._drift_metrics),
            'num_drifting': len(drifting_features),
            'drifting_features': drifting_features,
        }

    def get_version_distribution(self, model_id: str) -> dict:
        """
        Get distribution of predictions by version
        BUG #4: May show version N but actual version is N-1
        """
        version_counts = defaultdict(int)

        for pred in self._prediction_metrics:
            if pred['model_id'] == model_id and pred['version'] is not None:
                version_counts[pred['version']] += 1

        return dict(version_counts)

    def clear_metrics(self):
        """Clear all metrics"""
        self._prediction_metrics.clear()
        self._drift_metrics.clear()
        self._performance_metrics.clear()
