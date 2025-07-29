"""
Plugin Loader for PersonaOS

This module handles dynamic loading, initialization, and lifecycle management
of PersonaOS plugins. It provides safe plugin loading with error handling
and dependency resolution.
"""

import os
import sys
import importlib
import importlib.util
import logging
import threading
import traceback
from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Type
import time

from .base_plugin import (
    BasePlugin, PluginMetadata, PluginState, PluginType,
    PluginAPI, PluginPermission, PluginDependency
)
from .plugin_registry import PluginRegistry
from .plugin_scanner import PluginScanner
from .dependency_resolver import AdvancedDependencyResolver
from .hot_reload_manager import HotReloadManager
from .error_recovery_manager import ErrorRecoveryManager
from .security_manager import SecurityManager
from .sandbox_controller import SandboxController

class PluginLoadError(Exception):
    """Exception raised when plugin loading fails."""
    pass

class PluginLoader:
    """
    Handles dynamic loading and lifecycle management of PersonaOS plugins.
    
    The loader discovers plugins using the scanner, loads them safely,
    manages dependencies, and integrates them with the plugin registry.
    """
    
    def __init__(self, config: Dict[str, Any] = None, 
                 plugin_registry: Optional[PluginRegistry] = None,
                 plugin_scanner: Optional[PluginScanner] = None,
                 core_services: Optional[Dict[str, Any]] = None):
        """
        Initialize plugin loader.
        
        Args:
            config: PersonaOS configuration dictionary
            plugin_registry: Plugin registry instance
            plugin_scanner: Plugin scanner instance
            core_services: Core PersonaOS services for plugin API
        """
        self.config = config or {}
        self.logger = logging.getLogger("plugin_loader")
        
        # Component dependencies
        self.registry = plugin_registry or PluginRegistry(config)
        self.scanner = plugin_scanner or PluginScanner(config)
        self.core_services = core_services or {}
        
        # Enhanced components
        self.dependency_resolver = AdvancedDependencyResolver(config)
        self.hot_reload_manager = HotReloadManager(config, self) if config.get("plugin_hot_reload", False) else None
        self.error_recovery_manager = ErrorRecoveryManager(config, self) if config.get("plugin_error_recovery_enabled", True) else None
        
        # Security components
        self.security_manager = SecurityManager(config) if config.get("plugin_security_enabled", True) else None
        self.sandbox_controller = SandboxController(config) if config.get("plugin_sandboxing_enabled", True) else None
        
        # Loading state
        self.loading_in_progress = False
        self.loaded_modules: Dict[str, Any] = {}  # Track loaded Python modules
        self.plugin_instances: Dict[str, BasePlugin] = {}  # Track plugin instances
        
        # Plugin permission validation
        self.permission_validators: Dict[str, callable] = {}
        self.default_permissions = self._load_default_permissions()
        
        # Hot reload support (legacy compatibility)
        self.hot_reload_enabled = self.config.get("plugin_hot_reload", False)
        self.file_watchers: Dict[str, Any] = {}
        
        # Threading safety
        self._loader_lock = threading.RLock()
        
        # Loading statistics
        self.load_stats = {
            "total_discoveries": 0,
            "successful_loads": 0,
            "failed_loads": 0,
            "dependency_errors": 0,
            "permission_errors": 0,
            "last_load_time": None
        }
        
        self.logger.info("PluginLoader initialized")
    
    def discover_and_load_all_plugins(self) -> Dict[str, Any]:
        """
        Discover and load all plugins from configured directories.
        
        Returns:
            Dictionary with loading results and statistics
        """
        with self._loader_lock:
            if self.loading_in_progress:
                raise PluginLoadError("Plugin loading already in progress")
            
            self.loading_in_progress = True
            
            try:
                self.logger.info("Starting plugin discovery and loading")
                
                # Discover all plugins
                discovered_plugins = self.scanner.scan_all_plugins()
                self.load_stats["total_discoveries"] = len(discovered_plugins)
                
                self.logger.info(f"Discovered {len(discovered_plugins)} plugins")
                
                # Filter valid plugins
                valid_plugins = [p for p in discovered_plugins 
                               if p.get("validation_result", {}).get("valid", False)]
                
                self.logger.info(f"Found {len(valid_plugins)} valid plugins")
                
                # Resolve dependencies and determine load order using advanced resolver
                resolution_result = self.dependency_resolver.resolve_dependencies(valid_plugins)
                
                if not resolution_result.get("success", False):
                    raise PluginLoadError(f"Dependency resolution failed: {resolution_result.get('error')}")
                
                load_order = resolution_result.get("load_order", valid_plugins)
                
                # Load plugins in dependency order
                load_results = {}
                for plugin_info in load_order:
                    plugin_id = self._generate_plugin_id(plugin_info)
                    try:
                        result = self.load_plugin(plugin_info)
                        load_results[plugin_id] = result
                        
                        if result.get("success", False):
                            self.load_stats["successful_loads"] += 1
                        else:
                            self.load_stats["failed_loads"] += 1
                            
                    except Exception as e:
                        self.logger.error(f"Failed to load plugin {plugin_id}: {e}")
                        
                        # Handle error with recovery manager
                        if self.error_recovery_manager:
                            recovery_result = self.error_recovery_manager.handle_plugin_error(
                                plugin_id, e, {"operation": "load", "plugin_info": plugin_info}
                            )
                        else:
                            recovery_result = {"recovery_attempted": False}
                        
                        load_results[plugin_id] = {
                            "success": False,
                            "error": str(e),
                            "plugin_id": plugin_id,
                            "recovery_result": recovery_result
                        }
                        self.load_stats["failed_loads"] += 1
                
                self.load_stats["last_load_time"] = time.time()
                
                # Setup hot reload if enabled
                if self.hot_reload_manager:
                    plugin_directories = [Path(p["path"]).parent if Path(p["path"]).is_file() else Path(p["path"]) for p in valid_plugins]
                    self.hot_reload_manager.start_watching(plugin_directories)
                
                self.logger.info(f"Plugin loading completed. "
                               f"Success: {self.load_stats['successful_loads']}, "
                               f"Failed: {self.load_stats['failed_loads']}")
                
                return {
                    "success": True,
                    "discovered_count": len(discovered_plugins),
                    "valid_count": len(valid_plugins),
                    "loaded_count": self.load_stats["successful_loads"],
                    "failed_count": self.load_stats["failed_loads"],
                    "load_results": load_results,
                    "load_stats": self.load_stats.copy()
                }
                
            finally:
                self.loading_in_progress = False
    
    def load_plugin(self, plugin_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Load a single plugin from discovery information.
        
        Args:
            plugin_info: Plugin information from scanner
            
        Returns:
            Loading result dictionary
        """
        plugin_id = self._generate_plugin_id(plugin_info)
        plugin_path = Path(plugin_info["path"])
        
        self.logger.info(f"Loading plugin: {plugin_id} from {plugin_path}")
        
        try:
            # Step 1: Load the Python module
            module = self._load_plugin_module(plugin_info)
            
            # Step 2: Find and instantiate plugin classes
            plugin_classes = self._find_plugin_classes(module, plugin_info)
            
            if not plugin_classes:
                raise PluginLoadError(f"No valid plugin classes found in {plugin_id}")
            
            # Step 3: Select primary plugin class (prefer first one for now)
            primary_class = plugin_classes[0]
            plugin_instance = primary_class()
            
            # Step 4: Get and validate metadata
            metadata = plugin_instance.get_metadata()
            validated_metadata = self._validate_plugin_metadata(metadata, plugin_info)
            
            # Step 5: Check dependencies
            self._check_plugin_dependencies(validated_metadata)
            
            # Step 6: Validate permissions
            self._validate_plugin_permissions(validated_metadata)
            
            # Step 7: Create security context and sandbox if needed
            security_context = None
            sandbox_instance = None
            
            if self.security_manager:
                security_context = self.security_manager.create_security_context(
                    plugin_id, validated_metadata, 
                    [p.name for p in validated_metadata.permissions]
                )
                
                # Create sandbox if security level requires it
                if self.sandbox_controller and security_context:
                    from .security_manager import SecurityLevel
                    if security_context.security_level in [SecurityLevel.RESTRICTED, SecurityLevel.SANDBOXED]:
                        try:
                            sandbox_instance = self.sandbox_controller.create_sandbox(
                                plugin_id, security_context.security_level.name.lower()
                            )
                            self.logger.info(f"Created sandbox for plugin {plugin_id}: {sandbox_instance.sandbox_id}")
                        except Exception as e:
                            self.logger.error(f"Failed to create sandbox for plugin {plugin_id}: {e}")
                            if security_context.security_level == SecurityLevel.SANDBOXED:
                                raise PluginLoadError(f"Sandbox creation failed for sandboxed plugin {plugin_id}")
            
            # Step 8: Create plugin API and configure
            plugin_api = self._create_plugin_api(plugin_id, validated_metadata, security_context)
            plugin_instance.set_api(plugin_api)
            plugin_instance.set_config(self._load_plugin_config(validated_metadata))
            
            # Step 9: Execute plugin lifecycle - Load
            if not plugin_instance.on_load():
                raise PluginLoadError(f"Plugin {plugin_id} on_load() returned False")
            
            # Step 10: Start resource monitoring if security is enabled
            if self.security_manager and security_context:
                # Monitor resource usage for loaded plugin
                self.security_manager.monitor_resource_usage(plugin_id)
            
            # Step 11: Register with registry (include security context)
            extended_plugin_info = plugin_info.copy()
            extended_plugin_info["security_context"] = security_context
            extended_plugin_info["sandbox_instance"] = sandbox_instance
            
            if not self.registry.register_plugin(plugin_id, plugin_instance, validated_metadata, extended_plugin_info):
                raise PluginLoadError(f"Failed to register plugin {plugin_id} with registry")
            
            # Step 12: Track loaded module and instance
            self.loaded_modules[plugin_id] = module
            self.plugin_instances[plugin_id] = plugin_instance
            
            self.logger.info(f"Successfully loaded plugin: {plugin_id}")
            
            return {
                "success": True,
                "plugin_id": plugin_id,
                "metadata": validated_metadata,
                "state": plugin_instance.state.value,
                "load_time": time.time()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to load plugin {plugin_id}: {e}")
            
            # Clean up any partial loading
            self._cleanup_failed_load(plugin_id)
            
            return {
                "success": False,
                "plugin_id": plugin_id,
                "error": str(e),
                "traceback": traceback.format_exc(),
                "load_time": time.time()
            }
    
    def activate_plugin(self, plugin_id: str) -> bool:
        """
        Activate a loaded plugin.
        
        Args:
            plugin_id: Plugin ID to activate
            
        Returns:
            True if activation successful, False otherwise
        """
        try:
            plugin = self.registry.get_plugin(plugin_id)
            if not plugin:
                self.logger.error(f"Plugin {plugin_id} not found in registry")
                return False
            
            if plugin.state != PluginState.LOADED:
                self.logger.error(f"Plugin {plugin_id} not in LOADED state (current: {plugin.state.value})")
                return False
            
            # Execute activation lifecycle
            if plugin.on_activate():
                self.logger.info(f"Plugin {plugin_id} activated successfully")
                return True
            else:
                self.logger.error(f"Plugin {plugin_id} on_activate() returned False")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to activate plugin {plugin_id}: {e}")
            self.registry.record_plugin_error(plugin_id, e)
            
            # Handle error with recovery manager
            if self.error_recovery_manager:
                self.error_recovery_manager.handle_plugin_error(
                    plugin_id, e, {"operation": "activate"}
                )
            
            return False
    
    def deactivate_plugin(self, plugin_id: str) -> bool:
        """
        Deactivate an active plugin.
        
        Args:
            plugin_id: Plugin ID to deactivate
            
        Returns:
            True if deactivation successful, False otherwise
        """
        try:
            plugin = self.registry.get_plugin(plugin_id)
            if not plugin:
                self.logger.error(f"Plugin {plugin_id} not found in registry")
                return False
            
            if plugin.state != PluginState.ACTIVATED:
                self.logger.warning(f"Plugin {plugin_id} not in ACTIVATED state (current: {plugin.state.value})")
                return True  # Already deactivated
            
            # Execute deactivation lifecycle
            if plugin.on_deactivate():
                self.logger.info(f"Plugin {plugin_id} deactivated successfully")
                return True
            else:
                self.logger.error(f"Plugin {plugin_id} on_deactivate() returned False")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to deactivate plugin {plugin_id}: {e}")
            self.registry.record_plugin_error(plugin_id, e)
            return False
    
    def unload_plugin(self, plugin_id: str) -> bool:
        """
        Unload a plugin completely.
        
        Args:
            plugin_id: Plugin ID to unload
            
        Returns:
            True if unloading successful, False otherwise
        """
        try:
            plugin = self.registry.get_plugin(plugin_id)
            if not plugin:
                self.logger.warning(f"Plugin {plugin_id} not found in registry")
                return True  # Already unloaded
            
            # Deactivate first if needed
            if plugin.state == PluginState.ACTIVATED:
                if not self.deactivate_plugin(plugin_id):
                    self.logger.warning(f"Failed to deactivate plugin {plugin_id} before unloading")
            
            # Execute unload lifecycle
            if plugin.on_unload():
                self.logger.info(f"Plugin {plugin_id} unload lifecycle completed")
            else:
                self.logger.warning(f"Plugin {plugin_id} on_unload() returned False")
            
            # Unregister from registry
            self.registry.unregister_plugin(plugin_id)
            
            # Clean up tracking
            if plugin_id in self.loaded_modules:
                del self.loaded_modules[plugin_id]
            if plugin_id in self.plugin_instances:
                del self.plugin_instances[plugin_id]
            
            # Clean up hot reload watching
            if plugin_id in self.file_watchers:
                # Stop file watcher (implementation would depend on file watching library)
                del self.file_watchers[plugin_id]
            
            # Clean up security context and sandbox
            if self.security_manager:
                self.security_manager.cleanup_security_context(plugin_id)
            
            # Destroy sandbox if it exists
            plugin_status = self.registry.get_plugin_status(plugin_id)
            if plugin_status and self.sandbox_controller:
                sandbox_instance = plugin_status.get("discovery_info", {}).get("sandbox_instance")
                if sandbox_instance:
                    self.sandbox_controller.destroy_sandbox(sandbox_instance.sandbox_id)
            
            self.logger.info(f"Plugin {plugin_id} unloaded successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to unload plugin {plugin_id}: {e}")
            return False
    
    def reload_plugin(self, plugin_id: str) -> bool:
        """
        Reload a plugin (unload and load again).
        
        Args:
            plugin_id: Plugin ID to reload
            
        Returns:
            True if reload successful, False otherwise
        """
        try:
            # Get plugin info before unloading
            plugin_status = self.registry.get_plugin_status(plugin_id)
            if not plugin_status:
                self.logger.error(f"Plugin {plugin_id} not found for reload")
                return False
            
            # Find original plugin info
            plugin_path = plugin_status.get("discovery_info", {}).get("path")
            if not plugin_path:
                self.logger.error(f"Cannot find original path for plugin {plugin_id}")
                return False
            
            # Unload current version
            if not self.unload_plugin(plugin_id):
                self.logger.error(f"Failed to unload plugin {plugin_id} for reload")
                return False
            
            # Rescan the plugin
            plugin_path_obj = Path(plugin_path)
            if plugin_path_obj.is_dir():
                plugin_info = self.scanner._scan_plugin_directory(plugin_path_obj)
            else:
                plugin_info = self.scanner._scan_plugin_file(plugin_path_obj)
            
            if not plugin_info or not plugin_info.get("validation_result", {}).get("valid", False):
                self.logger.error(f"Plugin {plugin_id} not valid after rescan")
                return False
            
            # Load new version
            load_result = self.load_plugin(plugin_info)
            
            if load_result.get("success", False):
                self.logger.info(f"Plugin {plugin_id} reloaded successfully")
                return True
            else:
                self.logger.error(f"Failed to load new version of plugin {plugin_id}: {load_result.get('error')}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to reload plugin {plugin_id}: {e}")
            return False
    
    def get_load_statistics(self) -> Dict[str, Any]:
        """Get comprehensive plugin loading statistics."""
        stats = self.load_stats.copy()
        
        # Add component statistics
        if self.dependency_resolver:
            stats["dependency_resolution"] = self.dependency_resolver.get_resolution_stats()
        
        if self.hot_reload_manager:
            stats["hot_reload"] = self.hot_reload_manager.get_reload_status()
        
        if self.error_recovery_manager:
            stats["error_recovery"] = self.error_recovery_manager.get_error_summary()
        
        # Add security statistics
        if self.security_manager:
            stats["security"] = self.security_manager.get_security_stats()
        
        if self.sandbox_controller:
            stats["sandboxing"] = self.sandbox_controller.get_sandbox_status()
        
        return stats
    
    def _load_plugin_module(self, plugin_info: Dict[str, Any]) -> Any:
        """Load Python module for plugin."""
        plugin_path = Path(plugin_info["path"])
        plugin_name = plugin_info["name"]
        
        if plugin_info["plugin_type"] == "directory":
            # Load as package
            spec = importlib.util.spec_from_file_location(
                f"plugin_{plugin_name}", 
                plugin_path / "__init__.py"
            )
        else:
            # Load as single module
            spec = importlib.util.spec_from_file_location(
                f"plugin_{plugin_name}",
                plugin_path
            )
        
        if spec is None or spec.loader is None:
            raise PluginLoadError(f"Cannot create module spec for {plugin_path}")
        
        module = importlib.util.module_from_spec(spec)
        
        # Add to sys.modules for import resolution
        sys.modules[spec.name] = module
        
        try:
            spec.loader.exec_module(module)
        except Exception as e:
            # Clean up sys.modules on failure
            if spec.name in sys.modules:
                del sys.modules[spec.name]
            raise PluginLoadError(f"Failed to execute module {plugin_path}: {e}")
        
        return module
    
    def _find_plugin_classes(self, module: Any, plugin_info: Dict[str, Any]) -> List[Type[BasePlugin]]:
        """Find plugin classes in loaded module."""
        plugin_classes = []
        
        for name in dir(module):
            obj = getattr(module, name)
            
            if (isinstance(obj, type) and 
                issubclass(obj, BasePlugin) and 
                obj is not BasePlugin):
                
                plugin_classes.append(obj)
        
        return plugin_classes
    
    def _validate_plugin_metadata(self, metadata: PluginMetadata, plugin_info: Dict[str, Any]) -> PluginMetadata:
        """Validate and enrich plugin metadata."""
        # Set discovery info
        metadata.plugin_id = self._generate_plugin_id(plugin_info)
        metadata.file_path = plugin_info["path"]
        metadata.loaded_at = time.time()
        
        # Validate against discovery info
        discovered_metadata = plugin_info.get("metadata", {})
        if discovered_metadata:
            # Cross-validate key fields
            if discovered_metadata.get("name") and discovered_metadata["name"] != metadata.name:
                self.logger.warning(f"Plugin name mismatch: code={metadata.name}, metadata={discovered_metadata['name']}")
        
        return metadata
    
    def _check_plugin_dependencies(self, metadata: PluginMetadata):
        """Check if plugin dependencies are satisfied."""
        for dependency in metadata.dependencies:
            # Check if dependency is available
            if not self._is_dependency_satisfied(dependency):
                if not dependency.optional:
                    raise PluginLoadError(f"Required dependency not satisfied: {dependency.name} {dependency.version}")
                else:
                    self.logger.warning(f"Optional dependency not satisfied: {dependency.name} {dependency.version}")
    
    def _is_dependency_satisfied(self, dependency: PluginDependency) -> bool:
        """Check if a specific dependency is satisfied."""
        # Check if dependency plugin is loaded
        dep_plugin = self.registry.get_plugin(dependency.name)
        if not dep_plugin:
            return False
        
        # Check version compatibility (simplified version check)
        dep_metadata = self.registry.get_plugin_metadata(dependency.name)
        if dep_metadata:
            return self._is_version_compatible(dep_metadata.version, dependency.version, dependency.min_version, dependency.max_version)
        
        return False
    
    def _is_version_compatible(self, current: str, required: str, min_version: Optional[str], max_version: Optional[str]) -> bool:
        """Check version compatibility (simplified)."""
        # For now, just do string equality
        # In production, would use proper semantic versioning
        return current == required
    
    def _validate_plugin_permissions(self, metadata: PluginMetadata):
        """Validate plugin permissions."""
        for permission in metadata.permissions:
            if not self._is_permission_allowed(permission):
                raise PluginLoadError(f"Permission not allowed: {permission.name}")
    
    def _is_permission_allowed(self, permission: PluginPermission) -> bool:
        """Check if permission is allowed."""
        # Check against allowed permissions in config
        allowed_permissions = self.config.get("plugin_allowed_permissions", [])
        if allowed_permissions and permission.name not in allowed_permissions:
            return False
        
        # Check against blocked permissions
        blocked_permissions = self.config.get("plugin_blocked_permissions", [])
        if permission.name in blocked_permissions:
            return False
        
        # Check permission validators
        validator = self.permission_validators.get(permission.name)
        if validator:
            return validator(permission)
        
        return True
    
    def _create_plugin_api(self, plugin_id: str, metadata: PluginMetadata, security_context=None) -> PluginAPI:
        """Create plugin API interface."""
        # Extract granted permissions
        if security_context:
            # Use security context granted permissions
            granted_permissions = security_context.granted_permissions
        else:
            # Fall back to basic permission checking
            granted_permissions = set()
            for permission in metadata.permissions:
                if self._is_permission_allowed(permission):
                    granted_permissions.add(permission.name)
        
        # Create enhanced plugin API with security context
        plugin_api = PluginAPI(plugin_id, granted_permissions, self.core_services)
        
        # Attach security and sandbox managers for API operations
        if hasattr(plugin_api, 'set_security_manager'):
            plugin_api.set_security_manager(self.security_manager)
        if hasattr(plugin_api, 'set_sandbox_controller'):
            plugin_api.set_sandbox_controller(self.sandbox_controller)
        
        return plugin_api
    
    def _load_plugin_config(self, metadata: PluginMetadata) -> Dict[str, Any]:
        """Load plugin-specific configuration."""
        plugin_config = {}
        
        # Start with default config from metadata
        if metadata.default_config:
            plugin_config.update(metadata.default_config)
        
        # Load from system config
        system_plugin_config = self.config.get("plugin_configs", {}).get(metadata.name, {})
        plugin_config.update(system_plugin_config)
        
        return plugin_config
    
    def _generate_plugin_id(self, plugin_info: Dict[str, Any]) -> str:
        """Generate unique plugin ID."""
        name = plugin_info["name"]
        
        # Check if metadata provides a name
        metadata = plugin_info.get("metadata", {})
        if metadata.get("name"):
            name = metadata["name"]
        
        # Ensure uniqueness by appending path hash if needed
        base_id = name
        counter = 1
        
        while base_id in self.registry:
            base_id = f"{name}_{counter}"
            counter += 1
        
        return base_id
    
    def _cleanup_failed_load(self, plugin_id: str):
        """Clean up after failed plugin load."""
        try:
            # Remove from tracking
            if plugin_id in self.loaded_modules:
                del self.loaded_modules[plugin_id]
            if plugin_id in self.plugin_instances:
                del self.plugin_instances[plugin_id]
            
            # Remove from registry if partially registered
            if plugin_id in self.registry:
                self.registry.unregister_plugin(plugin_id)
                
        except Exception as e:
            self.logger.error(f"Error during cleanup of failed load {plugin_id}: {e}")
    
    def _load_default_permissions(self) -> Set[str]:
        """Load default allowed permissions."""
        return {
            "config.read",
            "tools.register",
            "storage.read",
            "storage.write",
            "audio.speak"
        }
    
    def _setup_hot_reload(self, plugins: List[Dict[str, Any]]):
        """Setup hot reload file watching (placeholder for future implementation)."""
        # This would integrate with a file watching library
        # to monitor plugin files for changes and trigger reloads
        self.logger.info("Hot reload setup placeholder - not implemented")
        pass

class PluginDependencyResolver:
    """
    Resolves plugin dependencies and determines optimal loading order.
    """
    
    def __init__(self):
        self.logger = logging.getLogger("plugin_dependency_resolver")
    
    def resolve_load_order(self, plugins: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Resolve plugin dependencies and return plugins in load order.
        
        Args:
            plugins: List of plugin discovery results
            
        Returns:
            List of plugins in dependency-resolved load order
        """
        # Build dependency graph
        dependency_graph = {}
        plugin_map = {}
        
        for plugin in plugins:
            plugin_name = self._get_plugin_name(plugin)
            plugin_map[plugin_name] = plugin
            
            # Get dependencies from metadata
            metadata = plugin.get("metadata", {})
            dependencies = metadata.get("dependencies", [])
            
            dependency_graph[plugin_name] = [
                dep.get("name") if isinstance(dep, dict) else str(dep)
                for dep in dependencies
            ]
        
        # Perform topological sort
        try:
            sorted_names = self._topological_sort(dependency_graph)
            
            # Return plugins in resolved order
            resolved_plugins = []
            for name in sorted_names:
                if name in plugin_map:
                    resolved_plugins.append(plugin_map[name])
            
            # Add any plugins not in the dependency graph (no dependencies)
            for plugin in plugins:
                if plugin not in resolved_plugins:
                    resolved_plugins.append(plugin)
            
            self.logger.info(f"Resolved load order for {len(resolved_plugins)} plugins")
            return resolved_plugins
            
        except Exception as e:
            self.logger.error(f"Failed to resolve dependencies: {e}")
            # Return original order as fallback
            return plugins
    
    def _get_plugin_name(self, plugin: Dict[str, Any]) -> str:
        """Extract plugin name from plugin info."""
        metadata = plugin.get("metadata", {})
        return metadata.get("name", plugin.get("name", "unknown"))
    
    def _topological_sort(self, graph: Dict[str, List[str]]) -> List[str]:
        """Perform topological sort on dependency graph."""
        # Kahn's algorithm for topological sorting
        in_degree = {node: 0 for node in graph}
        
        # Calculate in-degrees
        for node in graph:
            for neighbor in graph[node]:
                if neighbor not in in_degree:
                    in_degree[neighbor] = 0
                in_degree[neighbor] += 1
        
        # Find nodes with no incoming edges
        queue = [node for node in in_degree if in_degree[node] == 0]
        result = []
        
        while queue:
            node = queue.pop(0)
            result.append(node)
            
            # Remove edges from this node
            for neighbor in graph.get(node, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        # Check for cycles
        if len(result) != len(in_degree):
            raise Exception("Circular dependency detected in plugins")
        
        return result