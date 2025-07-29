"""
PersonaOS Plugin System

This package provides the core plugin infrastructure for PersonaOS,
enabling dynamic loading, management, and execution of plugins.
"""

from .base_plugin import BasePlugin, PluginMetadata, PluginState, PluginType
from .plugin_registry import PluginRegistry
from .plugin_loader import PluginLoader
from .plugin_scanner import PluginScanner
from .plugin_discovery_manager import PluginDiscoveryManager
from .plugin_metadata_validator import PluginMetadataValidator
from .plugin_manager import PluginManager
from .dependency_resolver import AdvancedDependencyResolver
from .hot_reload_manager import HotReloadManager
from .error_recovery_manager import ErrorRecoveryManager
from .dependency_manager import DependencyManager
from .repository_client import RepositoryClient
from .dependency_validator import DependencyValidator
from .security_manager import SecurityManager, SecurityLevel, PluginSecurityContext
from .sandbox_controller import SandboxController, SandboxInstance, IsolationLevel
from .plugin_tool_bridge import PluginToolBridge, PluginToolAdapter
from .system_integration_manager import SystemIntegrationManager
from .plugin_cli_manager import PluginCLIManager
from .plugin_web_api import PluginWebAPI

__all__ = [
    'BasePlugin',
    'PluginMetadata', 
    'PluginState',
    'PluginType',
    'PluginRegistry',
    'PluginLoader',
    'PluginScanner',
    'PluginDiscoveryManager',
    'PluginMetadataValidator',
    'PluginManager',
    'AdvancedDependencyResolver',
    'HotReloadManager',
    'ErrorRecoveryManager',
    'DependencyManager',
    'RepositoryClient',
    'DependencyValidator',
    'SecurityManager',
    'SecurityLevel',
    'PluginSecurityContext',
    'SandboxController',
    'SandboxInstance',
    'IsolationLevel',
    'PluginToolBridge',
    'PluginToolAdapter',
    'SystemIntegrationManager',
    'PluginCLIManager',
    'PluginWebAPI'
]