"""
Model registry for version management
Handles model storage in S3 and metadata in database
"""

import logging
import time
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ModelMetadata:
    """Model metadata"""
    model_id: str
    version: int
    s3_path: str
    created_at: float
    metrics: dict


class S3Client:
    """Simulated S3 client"""

    def __init__(self):
        self._storage: dict[str, Any] = {}
        self._upload_tasks: dict[str, Any] = {}

    def upload_async(self, path: str, data: Any) -> str:
        """
        Asynchronous S3 upload (slow - 30 seconds for 2GB model)
        Returns task ID
        """
        task_id = f"task-{int(time.time())}"
        self._upload_tasks[task_id] = {
            'path': path,
            'data': data,
            'started_at': time.time(),
            'status': 'in_progress',
            'duration': 30.0,  # 30 seconds for 2GB model
        }
        logger.info(f"Started async upload to {path}, task={task_id}")
        return task_id

    def wait_for_upload(self, task_id: str, timeout: float = 60.0) -> bool:
        """Wait for upload to complete"""
        if task_id not in self._upload_tasks:
            return False

        task = self._upload_tasks[task_id]
        elapsed = time.time() - task['started_at']

        if elapsed >= task['duration']:
            # Upload complete
            self._storage[task['path']] = task['data']
            task['status'] = 'completed'
            return True

        return False

    def download(self, path: str) -> Any | None:
        """Download from S3"""
        if path in self._storage:
            return self._storage[path]

        # BUG #4: 404 if download attempted before upload completes
        logger.error(f"Model not found in S3: {path}")
        return None

    def exists(self, path: str) -> bool:
        """Check if object exists in S3"""
        return path in self._storage


class Database:
    """Simulated database"""

    def __init__(self):
        self._models: dict[str, ModelMetadata] = {}

    def update_version(self, model_id: str, version: int, s3_path: str):
        """
        Update model version in database
        BUG #4: Updates immediately, before S3 upload completes
        """
        metadata = ModelMetadata(
            model_id=model_id,
            version=version,
            s3_path=s3_path,
            created_at=time.time(),
            metrics={}
        )
        self._models[model_id] = metadata
        logger.info(f"Updated database: model={model_id}, version={version}")

    def get_current_version(self, model_id: str) -> ModelMetadata | None:
        """Get current model version"""
        return self._models.get(model_id)


class ModelRegistry:
    """
    Model registry with S3 storage and database metadata
    BUG #4: Race condition - database updates before S3 upload completes
    """

    def __init__(self):
        self.s3 = S3Client()
        self.db = Database()

    def register_model(self, model_id: str, model_data: Any, version: int) -> bool:
        """
        Register new model version
        BUG #4: Database updates immediately, S3 upload is async (fire-and-forget)
        """
        s3_path = f"models/{model_id}/v{version}/model.pkl"

        logger.info(f"Registering model {model_id} version {version}")

        # BUG #4: Start async S3 upload (takes 30 seconds)
        upload_task = self.s3.upload_async(s3_path, model_data)  # Fire and forget!

        # BUG #4: Update database immediately (doesn't wait for S3!)
        # This creates the race condition
        self.db.update_version(model_id, version, s3_path)

        logger.info(f"Model {model_id} v{version} registered (upload in progress)")

        # Return success immediately, even though upload may not be complete
        return True

    def register_model_sync(self, model_id: str, model_data: Any, version: int,
                          timeout: float = 60.0) -> bool:
        """
        Register model with synchronous upload (correct implementation, not used)
        """
        s3_path = f"models/{model_id}/v{version}/model.pkl"

        # Start upload
        upload_task = self.s3.upload_async(s3_path, model_data)

        # Wait for completion
        if not self.s3.wait_for_upload(upload_task, timeout):
            logger.error(f"Upload timeout for {model_id} v{version}")
            return False

        # Update database only after S3 upload succeeds
        self.db.update_version(model_id, version, s3_path)

        return True

    def get_model(self, model_id: str, version: int | None = None) -> Any | None:
        """
        Get model by ID and version
        BUG #4: May fail if database has version but S3 upload incomplete
        """
        # Get metadata from database
        if version is None:
            metadata = self.db.get_current_version(model_id)
        else:
            # Simplified - would lookup specific version
            metadata = self.db.get_current_version(model_id)
            if metadata and metadata.version != version:
                return None

        if not metadata:
            logger.error(f"Model {model_id} not found in database")
            return None

        # Download from S3
        # BUG #4: May get 404 if upload not complete yet
        model_data = self.s3.download(metadata.s3_path)

        if model_data is None:
            logger.error(f"Model {model_id} v{metadata.version} not found in S3 (upload incomplete?)")
            return None

        return model_data

    def get_current_version_number(self, model_id: str) -> int | None:
        """Get current version number from database"""
        metadata = self.db.get_current_version(model_id)
        return metadata.version if metadata else None

    def get_model_metadata(self, model_id: str) -> ModelMetadata | None:
        """Get model metadata"""
        return self.db.get_current_version(model_id)
