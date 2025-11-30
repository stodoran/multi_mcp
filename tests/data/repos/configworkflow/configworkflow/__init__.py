"""ConfigWorkflow - Configuration-driven workflow engine with plugin system."""

from .engine import WorkflowEngine
from .steps import Step, create_step
from .state import WorkflowState, StateTransition
from .serializer import StateSerializer

# BUG #1 (CRITICAL - circular import):
# We import from config, config imports from plugins for default registration
# This creates circular dependency issues
# from .config import Config
# from .plugins import PluginRegistry

__all__ = ['WorkflowEngine', 'Step', 'create_step', 'WorkflowState', 'StateTransition', 'StateSerializer']
