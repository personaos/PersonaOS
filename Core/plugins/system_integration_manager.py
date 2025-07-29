"""
System Integration Manager for PersonaOS Plugins

This module manages the integration of the plugin system with existing PersonaOS
components including the tool registry, intent processor, and memory system.
"""

import logging
from typing import Dict, Any, Optional, List
from .plugin_manager import PluginManager
from .plugin_tool_bridge import PluginToolBridge

class SystemIntegrationManager:
    """
    Manages integration between the plugin system and existing PersonaOS components.
    
    This class orchestrates the plugin system's interaction with:
    - Tool registry for tool execution
    - Intent processor for command processing
    - Memory system for conversation context
    - Core services for API access
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize system integration manager.
        
        Args:
            config: PersonaOS configuration dictionary
        """
        self.config = config or {}
        self.logger = logging.getLogger("system_integration_manager")
        
        # Core components (to be set by main system)
        self.plugin_manager: Optional[PluginManager] = None
        self.tool_registry = None
        self.intent_processor = None
        self.memory_manager = None
        self.core_services: Dict[str, Any] = {}
        
        # Integration state
        self.initialized = False
        self.integrations_active = []
        
        self.logger.info("SystemIntegrationManager initialized")
    
    def initialize(self, core_services: Dict[str, Any]) -> Dict[str, Any]:
        """
        Initialize system integration with core services.
        
        Args:
            core_services: Dictionary of core PersonaOS services
            
        Returns:
            Initialization result dictionary
        """
        try:
            self.logger.info("Initializing system integration")
            
            # Store core services
            self.core_services = core_services
            self.tool_registry = core_services.get("tool_registry")
            self.intent_processor = core_services.get("intent_processor")
            self.memory_manager = core_services.get("memory_manager")
            
            # Initialize plugin manager with core services
            self.plugin_manager = PluginManager(
                config=self.config,
                core_services=core_services,
                tool_registry=self.tool_registry
            )
            
            # Initialize plugin system
            plugin_init_result = self.plugin_manager.initialize()
            
            if not plugin_init_result.get("success", False):
                raise Exception(f"Plugin system initialization failed: {plugin_init_result.get('error')}")
            
            # Setup integrations
            integration_results = {}
            
            # Tool registry integration
            if self.tool_registry:
                tool_integration = self._setup_tool_integration()
                integration_results["tool_registry"] = tool_integration
                if tool_integration.get("success"):
                    self.integrations_active.append("tool_registry")
            
            # Intent processor integration
            if self.intent_processor:
                intent_integration = self._setup_intent_integration()
                integration_results["intent_processor"] = intent_integration
                if intent_integration.get("success"):
                    self.integrations_active.append("intent_processor")
            
            # Memory system integration
            if self.memory_manager:
                memory_integration = self._setup_memory_integration()
                integration_results["memory_manager"] = memory_integration
                if memory_integration.get("success"):
                    self.integrations_active.append("memory_manager")
            
            self.initialized = True
            
            result = {
                "success": True,
                "message": "System integration initialized successfully",
                "plugin_initialization": plugin_init_result,
                "integrations": integration_results,
                "active_integrations": self.integrations_active
            }
            
            self.logger.info(f"System integration complete. Active integrations: {self.integrations_active}")
            return result
            
        except Exception as e:
            self.logger.error(f"System integration initialization failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "System integration initialization failed"
            }
    
    def _setup_tool_integration(self) -> Dict[str, Any]:
        """Setup integration with the tool registry."""
        try:
            self.logger.info("Setting up tool registry integration")
            
            # Tool bridge should already be initialized by plugin manager
            if not self.plugin_manager.tool_bridge:
                return {
                    "success": False,
                    "error": "Tool bridge not available in plugin manager"
                }
            
            # Register all existing plugins as tools
            registration_results = self.plugin_manager.register_all_plugin_tools()
            successful_registrations = sum(1 for success in registration_results.values() if success)
            
            self.logger.info(f"Tool integration setup complete. Registered {successful_registrations} plugin tools")
            
            return {
                "success": True,
                "registered_tools": successful_registrations,
                "total_plugins": len(registration_results),
                "registration_results": registration_results
            }
            
        except Exception as e:
            self.logger.error(f"Tool integration setup failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _setup_intent_integration(self) -> Dict[str, Any]:
        """Setup integration with the intent processor."""
        try:
            self.logger.info("Setting up intent processor integration")
            
            # The intent processor should already be using the same tool registry
            # that our plugins are registered with, so no additional setup needed
            
            self.logger.info("Intent processor integration setup complete")
            
            return {
                "success": True,
                "message": "Intent processor already integrated via shared tool registry"
            }
            
        except Exception as e:
            self.logger.error(f"Intent integration setup failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _setup_memory_integration(self) -> Dict[str, Any]:
        """Setup integration with the memory system."""
        try:
            self.logger.info("Setting up memory system integration")
            
            # Add memory manager to core services so plugins can access it
            if self.memory_manager and "memory_manager" not in self.core_services:
                self.core_services["memory_manager"] = self.memory_manager
            
            self.logger.info("Memory system integration setup complete")
            
            return {
                "success": True,
                "message": "Memory system integrated via core services"
            }
            
        except Exception as e:
            self.logger.error(f"Memory integration setup failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def discover_and_load_plugins(self) -> Dict[str, Any]:
        """Discover and load all plugins with full system integration."""
        if not self.initialized:
            return {
                "success": False,
                "error": "System integration not initialized"
            }
        
        try:
            self.logger.info("Discovering and loading plugins with system integration")
            
            # Use plugin manager to discover and load plugins
            load_result = self.plugin_manager.loader.discover_and_load_all_plugins()
            
            if load_result.get("success", False):
                # Activate loaded plugins
                loaded_plugins = [pid for pid, result in load_result.get("load_results", {}).items() 
                                if result.get("success", False)]
                
                activation_results = {}
                for plugin_id in loaded_plugins:
                    activation_result = self.plugin_manager.activate_plugin(plugin_id)
                    activation_results[plugin_id] = activation_result
                
                # Register newly activated plugins as tools
                if "tool_registry" in self.integrations_active:
                    tool_registration_results = {}
                    for plugin_id in loaded_plugins:
                        if activation_results.get(plugin_id, False):
                            tool_registration_results[plugin_id] = self.plugin_manager.register_plugin_as_tool(plugin_id)
                    
                    load_result["tool_registrations"] = tool_registration_results
                
                load_result["activation_results"] = activation_results
                successful_activations = sum(1 for success in activation_results.values() if success)
                
                self.logger.info(f"Plugin loading complete. Loaded: {load_result.get('loaded_count', 0)}, "
                               f"Activated: {successful_activations}")
            
            return load_result
            
        except Exception as e:
            self.logger.error(f"Plugin discovery and loading failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_integration_status(self) -> Dict[str, Any]:
        """Get comprehensive status of system integration."""
        status = {
            "initialized": self.initialized,
            "active_integrations": self.integrations_active,
            "plugin_manager_available": self.plugin_manager is not None,
            "core_services": list(self.core_services.keys())
        }
        
        if self.plugin_manager:
            status["plugin_system"] = {
                "initialized": self.plugin_manager.initialized,
                "system_enabled": self.plugin_manager.system_enabled,
                "auto_load_enabled": self.plugin_manager.auto_load_enabled,
                "total_plugins": len(self.plugin_manager),
                "plugin_statistics": self.plugin_manager.get_system_health()
            }
            
            # Tool bridge status
            if self.plugin_manager.tool_bridge:
                status["tool_bridge"] = self.plugin_manager.get_tool_bridge_statistics()
        
        # Component availability
        status["components"] = {
            "tool_registry": self.tool_registry is not None,
            "intent_processor": self.intent_processor is not None,
            "memory_manager": self.memory_manager is not None
        }
        
        return status
    
    def shutdown(self) -> Dict[str, Any]:
        """Shutdown system integration."""
        try:
            self.logger.info("Shutting down system integration")
            
            shutdown_results = {}
            
            # Shutdown plugin manager
            if self.plugin_manager:
                plugin_shutdown = self.plugin_manager.shutdown()
                shutdown_results["plugin_manager"] = plugin_shutdown
            
            # Clear integration state
            self.integrations_active.clear()
            self.initialized = False
            
            self.logger.info("System integration shutdown complete")
            
            return {
                "success": True,
                "message": "System integration shutdown complete",
                "shutdown_results": shutdown_results
            }
            
        except Exception as e:
            self.logger.error(f"System integration shutdown failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    # Convenience methods for plugin management
    
    def load_plugin(self, plugin_path: str) -> Dict[str, Any]:
        """Load a single plugin with full integration."""
        if not self.plugin_manager:
            return {"success": False, "error": "Plugin manager not available"}
        
        # This would need to be implemented in plugin manager
        # For now, return not implemented
        return {"success": False, "error": "Single plugin loading not yet implemented"}
    
    def unload_plugin(self, plugin_id: str) -> Dict[str, Any]:
        """Unload a plugin with full cleanup."""
        if not self.plugin_manager:
            return {"success": False, "error": "Plugin manager not available"}
        
        return self.plugin_manager.unload_plugin(plugin_id)
    
    def list_plugins(self) -> List[str]:
        """List all registered plugins."""
        if not self.plugin_manager:
            return []
        
        return self.plugin_manager.list_plugins()
    
    def get_plugin_status(self, plugin_id: str) -> Dict[str, Any]:
        """Get comprehensive status of a plugin including tool registration."""
        if not self.plugin_manager:
            return {"error": "Plugin manager not available"}
        
        status = self.plugin_manager.get_plugin_status(plugin_id)
        
        # Add tool registration status
        if self.plugin_manager.tool_bridge:
            tool_status = self.plugin_manager.get_plugin_tool_status(plugin_id)
            status["tool_registration"] = tool_status
        
        return status
    
    def execute_plugin_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """Execute a plugin tool through the tool registry."""
        if not self.tool_registry:
            return {
                "success": False,
                "error": "Tool registry not available"
            }
        
        try:
            result = self.tool_registry.execute_tool(tool_name, **kwargs)
            return {
                "success": result.success,
                "data": result.data,
                "error": result.error,
                "metadata": result.metadata
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }