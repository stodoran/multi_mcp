"""
Data drift detector
Compares training and production feature distributions
"""

import logging

import numpy as np
from scipy import stats

logger = logging.getLogger(__name__)


class DriftDetector:
    """
    Detects distribution drift between training and production
    BUG #5: Uses binned histograms, losing statistical power
    """

    def __init__(self, num_bins: int = 20, alert_threshold: float = 0.05):
        self.num_bins = num_bins  # BUG #5: Fixed 20 bins
        self.alert_threshold = alert_threshold
        self._detailed_metrics_enabled = False

    def detect_drift(self, train_dist: np.ndarray, prod_dist: np.ndarray,
                    feature_name: str = "feature") -> dict:
        """
        Detect drift using KS test on binned histograms
        BUG #5: Binning masks subtle mean shifts
        """
        # BUG #5: Bin the distributions for "computational efficiency"
        # Use binned histograms for computational efficiency
        # Bins chosen to preserve statistical power (tested with synthetic data)
        binned_train = self._create_binned_histogram(train_dist)
        binned_prod = self._create_binned_histogram(prod_dist)

        # BUG #5: KS test on binned data, not raw data
        # This loses information about within-bin variance
        stat, pvalue = stats.ks_2samp(binned_train, binned_prod)

        # Check if drift is significant
        is_drifting = pvalue < self.alert_threshold

        result = {
            'feature': feature_name,
            'statistic': stat,
            'pvalue': pvalue,
            'is_drifting': is_drifting,
            'num_bins': self.num_bins,
        }

        if is_drifting:
            logger.warning(f"Drift detected for {feature_name}: p={pvalue:.4f}")
        else:
            logger.info(f"No drift detected for {feature_name}: p={pvalue:.4f}")

        return result

    def _create_binned_histogram(self, data: np.ndarray) -> np.ndarray:
        """
        Create binned histogram
        BUG #5: Information loss from binning
        """
        # DECOY: Adaptive binning based on variance (but only adapts to variance, not shift type)
        if data.std() > 10:
            num_bins = 50  # Increase bins for high variance
        else:
            num_bins = self.num_bins

        # Create histogram
        # BUG #5: For age range 0-100 with 20 bins → 5-year bins
        # Shift from mean=35 to mean=38 stays within same bin (bin 7)
        hist, bin_edges = np.histogram(data, bins=num_bins, range=(data.min(), data.max()))

        # Return histogram counts (normalized)
        return hist / hist.sum() if hist.sum() > 0 else hist

    def detect_drift_raw(self, train_dist: np.ndarray, prod_dist: np.ndarray) -> dict:
        """
        Detect drift on raw data (not binned)
        This would correctly detect subtle shifts, but isn't used
        """
        stat, pvalue = stats.ks_2samp(train_dist, prod_dist)

        return {
            'statistic': stat,
            'pvalue': pvalue,
            'is_drifting': pvalue < self.alert_threshold,
        }

    def compare_distributions(self, train_dist: np.ndarray, prod_dist: np.ndarray) -> dict:
        """
        Compare distributions with multiple metrics
        """
        return {
            'train_mean': train_dist.mean(),
            'prod_mean': prod_dist.mean(),
            'train_std': train_dist.std(),
            'prod_std': prod_dist.std(),
            'mean_diff': prod_dist.mean() - train_dist.mean(),
            'std_diff': prod_dist.std() - train_dist.std(),
        }

    def set_alert_threshold(self, threshold: float):
        """Update alert threshold"""
        self.alert_threshold = threshold

    def enable_detailed_metrics(self, enabled: bool = True):
        """Enable detailed drift metrics"""
        self._detailed_metrics_enabled = enabled
