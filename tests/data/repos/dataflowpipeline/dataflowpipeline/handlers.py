"""Error handling and rollback logic.

This module provides error handlers for pipeline failures.
"""

import logging

from .stages import Stage

logger = logging.getLogger(__name__)


class ErrorHandler:
    """Base error handler for pipeline failures."""

    def __init__(self, stages: list[Stage]):
        """Initialize with list of pipeline stages.

        Args:
            stages: List of stages that may need rollback
        """
        self.stages = stages
        self._error_count = 0

    def handle_error(
        self,
        error: Exception,
        stage_name: str,
        record_id: str | None = None
    ) -> bool:
        """Handle a pipeline error.

        Args:
            error: The exception that occurred
            stage_name: Name of the stage where error occurred
            record_id: Optional record identifier

        Returns:
            True if error was handled, False if pipeline should stop
        """
        self._error_count += 1
        logger.error(
            f"Error in stage {stage_name} for record {record_id}: {error}"
        )
        return False

    def get_error_count(self) -> int:
        """Get total error count."""
        return self._error_count


class RollbackHandler(ErrorHandler):
    """Error handler that attempts to rollback all stages on failure."""

    def handle_error(
        self,
        error: Exception,
        stage_name: str,
        record_id: str | None = None
    ) -> bool:
        """Handle error by attempting rollback of all stages."""
        super().handle_error(error, stage_name, record_id)

        logger.warning(
            f"Attempting to rollback all stages due to error in {stage_name}"
        )

        rollback_failures = []

        for stage in self.stages:
            try:
                stage.rollback()

            except Exception as rollback_error:
                logger.error(
                    f"Rollback failed for stage {stage.name}: {rollback_error}"
                )
                rollback_failures.append(stage.name)

        if rollback_failures:
            logger.error(
                f"Rollback incomplete - failed stages: {rollback_failures}"
            )

        return False


class RetryHandler(ErrorHandler):
    """Error handler that retries failed records."""

    def __init__(self, stages: list[Stage], max_retries: int = 3):
        super().__init__(stages)
        self.max_retries = max_retries
        self._retry_counts: dict[str, int] = {}

    def handle_error(
        self,
        error: Exception,
        stage_name: str,
        record_id: str | None = None
    ) -> bool:
        """Handle error by retrying up to max_retries times."""
        super().handle_error(error, stage_name, record_id)

        if record_id is None:
            return False

        retry_count = self._retry_counts.get(record_id, 0)

        if retry_count < self.max_retries:
            self._retry_counts[record_id] = retry_count + 1
            logger.info(
                f"Retrying record {record_id} "
                f"(attempt {retry_count + 1}/{self.max_retries})"
            )
            return True

        logger.error(
            f"Record {record_id} failed after {self.max_retries} retries"
        )

        return False
