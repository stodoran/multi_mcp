"""
A/B testing controller
Manages gradual model rollouts and traffic splitting
"""

import logging

from .model_registry import ModelRegistry
from .serving import ServingEngine

logger = logging.getLogger(__name__)


class ABTestingController:
    """
    A/B testing with traffic splitting
    BUG #4: Routes traffic based on db_version, not loaded_version
    """

    def __init__(self, model_registry: ModelRegistry):
        self.model_registry = model_registry
        self._experiments: dict[str, dict] = {}

    def create_experiment(self, experiment_id: str, model_id: str,
                         control_version: int, treatment_version: int,
                         traffic_split: float = 0.5):
        """Create A/B test experiment"""
        self._experiments[experiment_id] = {
            'model_id': model_id,
            'control_version': control_version,
            'treatment_version': treatment_version,
            'traffic_split': traffic_split,
        }

        logger.info(f"Created experiment {experiment_id}: "
                   f"control=v{control_version}, treatment=v{treatment_version}, "
                   f"split={traffic_split}")

    def get_variant(self, experiment_id: str, user_id: int,
                   serving_engine: ServingEngine) -> str:
        """
        Determine which variant to serve
        BUG #4: Routes based on database version, not actual loaded model
        """
        if experiment_id not in self._experiments:
            return "control"

        experiment = self._experiments[experiment_id]

        # Determine variant based on user_id hash
        import hashlib
        hash_val = int(hashlib.md5(str(user_id).encode()).hexdigest(), 16)
        traffic_split = experiment['traffic_split']

        if (hash_val % 100) / 100.0 < traffic_split:
            variant = "treatment"
            expected_version = experiment['treatment_version']
        else:
            variant = "control"
            expected_version = experiment['control_version']

        # BUG #4: Check version mismatch
        # Get version from database (what we think is serving)
        db_version = self.model_registry.get_current_version_number(experiment['model_id'])

        # Get actually loaded version from serving engine
        loaded_version = serving_engine.get_loaded_model_version()

        if loaded_version != db_version:
            # BUG #4: Version mismatch detected but we continue anyway!
            logger.warning(f"Version mismatch: loaded={loaded_version}, db={db_version}")
            # Continue anyway - assume eventual consistency
            # BUG: This means A/B test results are corrupted!

        # Route traffic based on database version (not loaded version)
        # BUG #4: If loaded_version is old but db_version is new,
        # we record metrics for new version even though we're serving old version
        self._record_variant_assignment(experiment_id, user_id, variant, db_version)

        return variant

    def _record_variant_assignment(self, experiment_id: str, user_id: int,
                                  variant: str, version: int):
        """Record variant assignment for analysis"""
        # In real implementation, would write to analytics database
        logger.debug(f"User {user_id} assigned to {variant} (version {version})")

    def get_experiment_results(self, experiment_id: str) -> dict:
        """
        Get experiment results
        BUG #4: Results may be corrupted due to version mismatch
        """
        if experiment_id not in self._experiments:
            return {}

        # In real implementation, would query metrics database
        # and compute statistical significance

        return {
            'experiment_id': experiment_id,
            'control_metrics': {'conversion_rate': 0.10},
            'treatment_metrics': {'conversion_rate': 0.12},
            'note': 'Results may be corrupted if version mismatch occurred during experiment',
        }

    def stop_experiment(self, experiment_id: str):
        """Stop an experiment"""
        if experiment_id in self._experiments:
            del self._experiments[experiment_id]
            logger.info(f"Stopped experiment {experiment_id}")
