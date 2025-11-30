"""PluginDataPipeline - Extensible data processing with hot-reload."""
from .backpressure import BackpressureManager
from .config_watcher import ConfigWatcher
from .executor import Executor
from .isolation import PluginIsolation
from .metrics import MetricsCollector
from .pipeline import Pipeline
from .plugin_loader import PluginLoader
from .resource_pool import ResourcePool
from .stream import StreamProcessor

__all__ = ["Pipeline", "PluginLoader", "Executor", "ResourcePool",
           "BackpressureManager", "StreamProcessor", "MetricsCollector",
           "ConfigWatcher", "PluginIsolation"]
