"""Pipeline orchestration.

This module orchestrates the execution of records through pipeline stages.
"""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from .handlers import ErrorHandler
from .stages import Stage

logger = logging.getLogger(__name__)


class Pipeline:
    """Orchestrates data flow through multiple stages."""

    def __init__(
        self,
        stages: list[Stage],
        error_handler: ErrorHandler | None = None,
        parallel: bool = False
    ):
        """Initialize pipeline with stages.

        Args:
            stages: List of stages to execute in order
            error_handler: Optional error handler
            parallel: Whether to run stages in parallel
        """
        self.stages = stages
        self.error_handler = error_handler
        self.parallel = parallel
        self._processed_count = 0

    def process_record(self, data: dict[str, Any]) -> dict[str, Any] | None:
        """Process a single record through all stages.

        Args:
            data: The record to process

        Returns:
            Processed record or None if processing failed
        """
        self._processed_count += 1

        result = data

        for stage in self.stages:
            try:
                result = stage.process(result)

                if result is False:
                    logger.warning(
                        f"Stage {stage.name} returned False for record "
                        f"{data.get('record_id', 'unknown')}"
                    )
                    return None

            except Exception as e:
                record_id = data.get('record_id', 'unknown')
                logger.error(
                    f"Error processing record {record_id} in stage {stage.name}: {e}"
                )

                if self.error_handler:
                    should_continue = self.error_handler.handle_error(
                        e, stage.name, record_id
                    )
                    if not should_continue:
                        return None
                else:
                    return None

        return result

    def process_batch(self, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Process a batch of records.

        Args:
            records: List of records to process

        Returns:
            List of successfully processed records
        """
        results = []

        if self.parallel:
            with ThreadPoolExecutor(max_workers=4) as executor:
                future_to_record = {
                    executor.submit(self.process_record, record): record
                    for record in records
                }

                for future in as_completed(future_to_record):
                    try:
                        result = future.result()
                        if result is not None:
                            results.append(result)
                    except Exception as e:
                        original_record = future_to_record[future]
                        logger.error(
                            f"Parallel processing failed for record "
                            f"{original_record.get('record_id', 'unknown')}: {e}"
                        )
        else:
            for record in records:
                result = self.process_record(record)
                if result is not None:
                    results.append(result)

        return results

    def get_processed_count(self) -> int:
        """Get total count of records processed."""
        return self._processed_count

    def get_stage_metrics(self) -> dict[str, int]:
        """Get metrics from all stages."""
        return {
            stage.name: stage.get_passed_count()
            for stage in self.stages
        }

    def reset(self) -> None:
        """Reset pipeline state."""
        self._processed_count = 0
        for stage in self.stages:
            if hasattr(stage, 'rollback'):
                stage.rollback()
