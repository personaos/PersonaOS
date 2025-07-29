"""
Main Plugin Manager for PersonaOS

This module provides the primary interface for plugin management,
orchestrating all plugin system components and providing a unified API.
"""

import logging
import threading
import time
from typing import Dict, List, Any, Optional, Set, Callable
from pathlib import Path

from .plugin_discovery_manager import PluginDiscoveryManager
from .plugin_registry import PluginRegistry
from .plugin_loader import PluginLoader
from .plugin_scanner import PluginScanner
from .plugin_metadata_validator import PluginMetadataValidator
from .plugin_tool_bridge import PluginToolBridge
from .base_plugin import BasePlugin, PluginMetadata, PluginState, PluginType

class PluginManager:
    """
    Main plugin management interface for PersonaOS.
    
    This class provides a unified interface for all plugin operations,
    orchestrating the discovery, loading, registry, and lifecycle management
    of plugins in the PersonaOS system.
    """
    
    def __init__(self, config: Dict[str, Any] = None, core_services: Dict[str, Any] = None, tool_registry: Any = None):
        """
        Initialize the plugin manager.
        
        Args:
            config: PersonaOS configuration dictionary
            core_services: Core PersonaOS services for plugin API access
            tool_registry: Tool registry for plugin-tool integration
        """
        self.config = config or {}
        self.core_services = core_services or {}
        self.tool_registry = tool_registry
        self.logger = logging.getLogger("plugin_manager")
        
        # Initialize components
        self.registry = PluginRegistry(config)
        self.scanner = PluginScanner(config)
        self.loader = PluginLoader(config, self.registry, self.scanner, core_services)
        self.discovery_manager = PluginDiscoveryManager(config)
        self.metadata_validator = PluginMetadataValidator(config)
        
        # Initialize tool bridge if tool registry provided
        self.tool_bridge = None
        if tool_registry:
            self.tool_bridge = PluginToolBridge(self.registry, tool_registry, config)
            self.logger.info("Plugin-tool bridge initialized")
        
        # Manager state
        self.initialized = False
        self.startup_complete = False
        self.shutdown_in_progress = False
        
        # Plugin management state
        self.auto_load_enabled = config.get("plugin_auto_load", True)
        self.system_enabled = config.get("plugin_system_enabled", True)
        
        # Threading
        self._manager_lock = threading.RLock()
        
        # Event handling
        self.event_handlers: Dict[str, List[Callable]] = {
            "system_startup": [],
            "system_shutdown": [],
            "plugin_loaded": [],
            "plugin_activated": [],
            "plugin_deactivated": [],
            "plugin_unloaded": [],
            "plugin_error": []
        }
        
        # Setup event forwarding from components
        self._setup_event_forwarding()
        
        # Setup tool bridge event handlers if bridge is available
        if self.tool_bridge:
            self._setup_tool_bridge_events()
        
        self.logger.info("PluginManager initialized")
    
    def initialize(self) -> Dict[str, Any]:
        """
        Initialize the plugin system.
        
        Returns:
            Initialization result dictionary
        """
        with self._manager_lock:
            if self.initialized:
                return {"success": True, "message": "Already initialized"}
            
            if not self.system_enabled:
                return {"success": False, "message": "Plugin system is disabled"}
            
            try:
                self.logger.info("Initializing plugin system")
                
                # Initialize components
                init_results = {}
                
                # Discover plugins if auto-load is enabled
                if self.auto_load_enabled:
                    self.logger.info("Auto-loading plugins during initialization")
                    discovery_result = self.discovery_manager.discover_plugins()
                    init_results["discovery"] = discovery_result
                    
                    if not discovery_result.get("success", False):
                        self.logger.warning(f"Plugin discovery failed during initialization: {discovery_result.get('error')}")
                
                self.initialized = True
                self.startup_complete = True
                
                # Fire startup event
                self._fire_event("system_startup", {
                    "initialization_results": init_results,
                    "auto_load_enabled": self.auto_load_enabled
                })
                
                result = {
                    "success": True,
                    "message": "Plugin system initialized successfully",
                    "components_initialized": ["registry", "scanner", "loader", "discovery_manager", "metadata_validator"],
                    "auto_load_enabled": self.auto_load_enabled,
                    "system_enabled": self.system_enabled,
                    "initialization_results": init_results
                }
                
                self.logger.info("Plugin system initialization complete")
                return result
                
            except Exception as e:
                self.logger.error(f"Plugin system initialization failed: {e}")
                return {
                    "success": False,
                    "error": str(e),
                    "message": "Plugin system initialization failed"
                }
    
    def shutdown(self) -> Dict[str, Any]:
        """
        Shutdown the plugin system.
        
        Returns:
            Shutdown result dictionary
        """
        with self._manager_lock:
            if self.shutdown_in_progress:
                return {"success": True, "message": "Shutdown already in progress"}
            
            self.shutdown_in_progress = True
            
            try:
                self.logger.info("Shutting down plugin system")
                
                # Fire shutdown event
                self._fire_event("system_shutdown", {"reason": "requested"})
                
                # Deactivate all active plugins
                active_plugins = self.registry.list_plugins(state=PluginState.ACTIVATED)
                deactivation_results = {}
                
                for plugin_id in active_plugins:
                    try:
                        result = self.deactivate_plugin(plugin_id)
                        deactivation_results[plugin_id] = result
                    except Exception as e:
                        self.logger.error(f"Error deactivating plugin {plugin_id}: {e}")
                        deactivation_results[plugin_id] = {"success": False, "error": str(e)}
                
                # Unload all loaded plugins
                loaded_plugins = self.registry.list_plugins()
                unload_results = {}
                
                for plugin_id in loaded_plugins:
                    try:
                        result = self.unload_plugin(plugin_id)
                        unload_results[plugin_id] = result
                    except Exception as e:
                        self.logger.error(f"Error unloading plugin {plugin_id}: {e}")
                        unload_results[plugin_id] = {"success": False, "error": str(e)}
                
                # Shutdown discovery manager
                self.discovery_manager.shutdown()
                
                # Clear registry
                self.registry.clear_registry()
                
                self.initialized = False
                self.startup_complete = False
                
                result = {
                    "success": True,
                    "message": "Plugin system shutdown complete",
                    "deactivated_plugins": len([r for r in deactivation_results.values() if r.get("success")]),
                    "unloaded_plugins": len([r for r in unload_results.values() if r.get("success")]),
                    "deactivation_results": deactivation_results,
                    "unload_results": unload_results
                }
                
                self.logger.info("Plugin system shutdown complete")
                return result
                
            except Exception as e:
                self.logger.error(f"Plugin system shutdown error: {e}")
                return {
                    "success": False,
                    "error": str(e),
                    "message": "Plugin system shutdown encountered errors"
                }
            
            finally:
                self.shutdown_in_progress = False
    
    def discover_plugins(self, directories: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Discover plugins from specified or configured directories.
        
        Args:
            directories: Optional list of directories to scan
            
        Returns:
            Discovery result dictionary
        """
        if not self._check_system_ready():
            return {"success": False, "error": "Plugin system not ready"}
        
        return self.discovery_manager.discover_plugins(directories)
    
    def load_plugin(self, plugin_path: str) -> Dict[str, Any]:
        """
        Load a specific plugin from path.
        
        Args:
            plugin_path: Path to plugin file or directory
            
        Returns:
            Load result dictionary
        """
        if not self._check_system_ready():
            return {"success": False, "error": "Plugin system not ready"}
        
        try:
            # Scan the specific plugin
            plugin_path_obj = Path(plugin_path)
            
            if plugin_path_obj.is_dir():
                plugin_info = self.scanner._scan_plugin_directory(plugin_path_obj)
            else:
                plugin_info = self.scanner._scan_plugin_file(plugin_path_obj)
            
            if not plugin_info:
                return {"success": False, "error": "No valid plugin found at path"}
            
            if not plugin_info.get("validation_result", {}).get("valid", False):
                return {
                    "success": False, 
                    "error": "Plugin validation failed",
                    "validation_errors": plugin_info.get("validation_result", {}).get("errors", [])
                }
            
            # Load the plugin
            load_result = self.loader.load_plugin(plugin_info)
            
            if load_result.get("success", False):
                self._fire_event("plugin_loaded", {
                    "plugin_id": load_result.get("plugin_id"),
                    "plugin_info": plugin_info,
                    "load_result": load_result
                })
            
            return load_result
            
        except Exception as e:
            self.logger.error(f"Error loading plugin from {plugin_path}: {e}")
            return {"success": False, "error": str(e)}
    
    def activate_plugin(self, plugin_id: str) -> Dict[str, Any]:
        """
        Activate a loaded plugin.
        
        Args:
            plugin_id: Plugin ID to activate
            
        Returns:
            Activation result dictionary
        """
        if not self._check_system_ready():
            return {"success": False, "error": "Plugin system not ready"}
        
        try:
            success = self.loader.activate_plugin(plugin_id)
            
            result = {
                "success": success,
                "plugin_id": plugin_id,
                "message": f"Plugin {plugin_id} {'activated' if success else 'activation failed'}"
            }
            
            if success:
                self._fire_event("plugin_activated", {"plugin_id": plugin_id})
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error activating plugin {plugin_id}: {e}")
            return {"success": False, "error": str(e), "plugin_id": plugin_id}
    
    def deactivate_plugin(self, plugin_id: str) -> Dict[str, Any]:
        """
        Deactivate an active plugin.
        
        Args:
            plugin_id: Plugin ID to deactivate
            
        Returns:
            Deactivation result dictionary
        """
        if not self._check_system_ready():
            return {"success": False, "error": "Plugin system not ready"}
        
        try:
            success = self.loader.deactivate_plugin(plugin_id)
            
            result = {
                "success": success,
                "plugin_id": plugin_id,
                "message": f"Plugin {plugin_id} {'deactivated' if success else 'deactivation failed'}"
            }
            
            if success:
                self._fire_event("plugin_deactivated", {"plugin_id": plugin_id})
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error deactivating plugin {plugin_id}: {e}")
            return {"success": False, "error": str(e), "plugin_id": plugin_id}
    
    def unload_plugin(self, plugin_id: str) -> Dict[str, Any]:
        """
        Unload a plugin completely.
        
        Args:
            plugin_id: Plugin ID to unload
            
        Returns:
            Unload result dictionary
        """
        if not self._check_system_ready():
            return {"success": False, "error": "Plugin system not ready"}
        
        try:
            success = self.loader.unload_plugin(plugin_id)
            
            result = {
                "success": success,
                "plugin_id": plugin_id,
                "message": f"Plugin {plugin_id} {'unloaded' if success else 'unload failed'}"
            }
            
            if success:
                self._fire_event("plugin_unloaded", {"plugin_id": plugin_id})
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error unloading plugin {plugin_id}: {e}")
            return {"success": False, "error": str(e), "plugin_id": plugin_id}
    
    def reload_plugin(self, plugin_id: str) -> Dict[str, Any]:
        """
        Reload a plugin (unload and load again).
        
        Args:
            plugin_id: Plugin ID to reload
            
        Returns:
            Reload result dictionary
        """
        if not self._check_system_ready():
            return {"success": False, "error": "Plugin system not ready"}
        
        try:
            success = self.loader.reload_plugin(plugin_id)
            
            result = {
                "success": success,
                "plugin_id": plugin_id,
                "message": f"Plugin {plugin_id} {'reloaded' if success else 'reload failed'}"
            }
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error reloading plugin {plugin_id}: {e}")
            return {"success": False, "error": str(e), "plugin_id": plugin_id}
    
    def get_plugin(self, plugin_id: str) -> Optional[BasePlugin]:
        """Get plugin instance by ID."""
        return self.registry.get_plugin(plugin_id)
    
    def get_plugin_metadata(self, plugin_id: str) -> Optional[PluginMetadata]:
        """Get plugin metadata by ID."""
        return self.registry.get_plugin_metadata(plugin_id)
    
    def get_plugin_status(self, plugin_id: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive plugin status."""
        return self.registry.get_plugin_status(plugin_id)
    
    def list_plugins(self, plugin_type: Optional[PluginType] = None, 
                    state: Optional[PluginState] = None,
                    enabled_only: bool = False) -> List[str]:
        """List plugin IDs matching criteria."""
        return self.registry.list_plugins(plugin_type, state, enabled_only)
    
    def find_plugins_by_capability(self, capability_name: str) -> List[str]:
        """Find plugins that provide a specific capability."""
        return self.registry.find_plugins_by_capability(capability_name)
    
    def enable_plugin(self, plugin_id: str) -> bool:
        """Enable a plugin."""
        return self.registry.enable_plugin(plugin_id)
    
    def disable_plugin(self, plugin_id: str) -> bool:
        """Disable a plugin."""
        return self.registry.disable_plugin(plugin_id)
    
    def get_system_status(self) -> Dict[str, Any]:
        """
        Get comprehensive plugin system status.
        
        Returns:
            System status dictionary
        """
        return {
            "system_enabled": self.system_enabled,
            "initialized": self.initialized,
            "startup_complete": self.startup_complete,
            "shutdown_in_progress": self.shutdown_in_progress,
            "auto_load_enabled": self.auto_load_enabled,
            "discovery_status": self.discovery_manager.get_discovery_status(),
            "registry_stats": self.registry.get_registry_stats(),
            "loader_stats": self.loader.get_load_statistics(),
            "validator_stats": self.metadata_validator.get_validation_stats(),
            "last_discovery": self.discovery_manager.get_last_discovery_results()
        }
    
    def perform_health_checks(self) -> Dict[str, Any]:
        """
        Perform health checks on all components and plugins.
        
        Returns:
            Health check results dictionary
        """
        health_results = {
            "overall_healthy": True,
            "timestamp": time.time(),
            "system_status": self.get_system_status(),
            "plugin_health": {},
            "component_health": {}
        }
        
        try:
            # Check plugin health
            plugin_health = self.registry.perform_health_checks()
            health_results["plugin_health"] = plugin_health
            
            # Count unhealthy plugins
            unhealthy_plugins = [
                pid for pid, health in plugin_health.items() 
                if not health.get("healthy", False)
            ]
            
            if unhealthy_plugins:
                health_results["overall_healthy"] = False
                health_results["unhealthy_plugins"] = unhealthy_plugins
            
            # Component health (basic checks)
            health_results["component_health"] = {
                "registry": {"healthy": len(self.registry) >= 0},
                "discovery_manager": {"healthy": not self.discovery_manager.discovery_active},
                "loader": {"healthy": not self.loader.loading_in_progress},
                "scanner": {"healthy": len(self.scanner.plugin_directories) > 0}
            }
            
        except Exception as e:
            self.logger.error(f"Health check error: {e}")
            health_results["overall_healthy"] = False
            health_results["error"] = str(e)
        
        return health_results
    
    def add_event_handler(self, event_type: str, handler: Callable):
        """Add event handler for plugin system events."""
        if event_type in self.event_handlers:
            self.event_handlers[event_type].append(handler)
    
    def remove_event_handler(self, event_type: str, handler: Callable):
        """Remove event handler for plugin system events."""
        if event_type in self.event_handlers and handler in self.event_handlers[event_type]:
            self.event_handlers[event_type].remove(handler)
    
    def _setup_event_forwarding(self):
        """Setup event forwarding from components."""
        # Forward registry events
        self.registry.add_event_handler("plugin_error", 
            lambda event_type, data: self._fire_event("plugin_error", data))
    
    def _setup_tool_bridge_events(self):
        """Setup tool bridge event handlers for automatic tool registration."""
        # Register tools when plugins are activated
        self.add_event_handler("plugin_activated", self._handle_plugin_activated_for_tools)
        
        # Unregister tools when plugins are deactivated or unloaded
        self.add_event_handler("plugin_deactivated", self._handle_plugin_deactivated_for_tools)
        self.add_event_handler("plugin_unloaded", self._handle_plugin_unloaded_for_tools)
        
        self.logger.info("Tool bridge event handlers registered")
    
    def _handle_plugin_activated_for_tools(self, event_type: str, event_data: Dict[str, Any]):
        """Handle plugin activation for tool registration."""
        plugin_id = event_data.get("plugin_id")
        if plugin_id and self.tool_bridge:
            self.tool_bridge.handle_plugin_lifecycle_change(plugin_id, "loaded", "activated")
    
    def _handle_plugin_deactivated_for_tools(self, event_type: str, event_data: Dict[str, Any]):
        """Handle plugin deactivation for tool unregistration."""
        plugin_id = event_data.get("plugin_id")
        if plugin_id and self.tool_bridge:
            self.tool_bridge.handle_plugin_lifecycle_change(plugin_id, "activated", "deactivated")
    
    def _handle_plugin_unloaded_for_tools(self, event_type: str, event_data: Dict[str, Any]):
        """Handle plugin unload for tool cleanup."""
        plugin_id = event_data.get("plugin_id")
        if plugin_id and self.tool_bridge:
            self.tool_bridge.handle_plugin_lifecycle_change(plugin_id, "deactivated", "unloaded")
    
    def _fire_event(self, event_type: str, event_data: Dict[str, Any]):
        """Fire plugin system event to registered handlers."""
        handlers = self.event_handlers.get(event_type, [])
        
        for handler in handlers:
            try:
                handler(event_type, event_data)
            except Exception as e:
                self.logger.error(f"Event handler error for {event_type}: {e}")
    
    def _check_system_ready(self) -> bool:
        """Check if plugin system is ready for operations."""
        return (self.system_enabled and 
                self.initialized and 
                not self.shutdown_in_progress)
    
    def get_plugin_directories(self) -> List[Path]:
        """Get configured plugin directories."""
        return self.scanner.get_plugin_directories()
    
    def add_plugin_directory(self, directory: Path):
        """Add a plugin directory to scan."""
        self.scanner.add_plugin_directory(directory)
    
    def remove_plugin_directory(self, directory: Path):
        """Remove a plugin directory from scanning."""
        self.scanner.remove_plugin_directory(directory)
    
    def validate_plugin_metadata(self, metadata_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Validate plugin metadata dictionary."""
        return self.metadata_validator.validate_metadata(metadata_dict)
    
    # Plugin-Tool Bridge Methods
    
    def register_plugin_as_tool(self, plugin_id: str) -> bool:
        """Register a plugin as a tool in the tool registry."""
        if not self.tool_bridge:
            self.logger.warning("Tool bridge not available for plugin tool registration")
            return False
        
        return self.tool_bridge.register_plugin_as_tool(plugin_id)
    
    def unregister_plugin_tool(self, plugin_id: str) -> bool:
        """Unregister a plugin tool from the tool registry."""
        if not self.tool_bridge:
            return True  # No bridge means no registration needed
        
        return self.tool_bridge.unregister_plugin_tool(plugin_id)
    
    def register_all_plugin_tools(self) -> Dict[str, bool]:
        """Register all eligible plugins as tools."""
        if not self.tool_bridge:
            self.logger.warning("Tool bridge not available for plugin tool registration")
            return {}
        
        return self.tool_bridge.register_all_plugin_tools()
    
    def get_plugin_tool_status(self, plugin_id: str = None) -> Dict[str, Any]:
        """Get tool registration status for plugin(s)."""
        if not self.tool_bridge:
            return {"tool_bridge_available": False}
        
        if plugin_id:
            return self.tool_bridge.get_plugin_tool_status(plugin_id)
        else:
            return self.tool_bridge.get_all_plugin_tool_status()
    
    def get_tool_bridge_statistics(self) -> Dict[str, Any]:
        """Get statistics about the plugin-tool bridge."""
        if not self.tool_bridge:
            return {"tool_bridge_available": False}
        
        return self.tool_bridge.get_bridge_statistics()
    
    def __len__(self) -> int:
        """Return number of registered plugins."""
        return len(self.registry)
    
    def __contains__(self, plugin_id: str) -> bool:
        """Check if plugin is registered."""
        return plugin_id in self.registry
    
    def __iter__(self):
        """Iterate over plugin IDs."""
        return iter(self.registry)