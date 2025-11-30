"""PluginDataPipeline - Extensible data processing with hot-reload."""
from .pipeline import Pipeline
from .plugin_loader import PluginLoader
from .executor import Executor
from .resource_pool import ResourcePool
from .backpressure import BackpressureManager
from .stream import StreamProcessor
from .metrics import MetricsCollector
from .config_watcher import ConfigWatcher
from .isolation import PluginIsolation

__all__ = ["Pipeline", "PluginLoader", "Executor", "ResourcePool",
           "BackpressureManager", "StreamProcessor", "MetricsCollector",
           "ConfigWatcher", "PluginIsolation"]
