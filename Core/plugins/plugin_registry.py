"""
Plugin Registry for PersonaOS

This module manages the registry of loaded plugins, tracking their states,
metadata, and providing access to plugin instances and capabilities.
"""

import time
import logging
import threading
from typing import Dict, List, Any, Optional, Set, Callable
from dataclasses import asdict
from collections import defaultdict

from .base_plugin import (
    BasePlugin, PluginMetadata, PluginState, PluginType,
    PluginAPI, PluginPermission
)

class PluginRegistryError(Exception):
    """Exception raised by plugin registry operations."""
    pass

class PluginRegistryEntry:
    """
    Represents a plugin entry in the registry with full lifecycle tracking.
    """
    
    def __init__(self, plugin_id: str, plugin_instance: BasePlugin, 
                 metadata: PluginMetadata, discovery_info: Dict[str, Any] = None):
        """
        Initialize plugin registry entry.
        
        Args:
            plugin_id: Unique plugin identifier
            plugin_instance: Plugin instance
            metadata: Plugin metadata
            discovery_info: Information from plugin discovery
        """
        self.plugin_id = plugin_id
        self.plugin_instance = plugin_instance
        self.metadata = metadata
        self.discovery_info = discovery_info or {}
        
        # Lifecycle tracking
        self.registered_at = time.time()
        self.last_accessed = time.time()
        self.access_count = 0
        self.error_count = 0
        self.last_error = None
        self.last_error_time = None
        
        # State management
        self.enabled = True
        self.health_check_count = 0
        self.last_health_check = None
        self.last_health_result = None
        
        # Threading safety
        self._lock = threading.RLock()
    
    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive status information."""
        with self._lock:
            base_status = self.plugin_instance.get_status()
            
            return {
                **base_status,
                "plugin_id": self.plugin_id,
                "registered_at": self.registered_at,
                "last_accessed": self.last_accessed,
                "access_count": self.access_count,
                "error_count": self.error_count,
                "last_error": self.last_error,
                "last_error_time": self.last_error_time,
                "enabled": self.enabled,
                "health_check_count": self.health_check_count,
                "last_health_check": self.last_health_check,
                "last_health_result": self.last_health_result
            }
    
    def record_access(self):
        """Record plugin access for metrics."""
        with self._lock:
            self.last_accessed = time.time()
            self.access_count += 1
    
    def record_error(self, error: Exception):
        """Record plugin error for tracking."""
        with self._lock:
            self.error_count += 1
            self.last_error = str(error)
            self.last_error_time = time.time()
    
    def update_health_check(self, result: Dict[str, Any]):
        """Update health check results."""
        with self._lock:
            self.health_check_count += 1
            self.last_health_check = time.time()
            self.last_health_result = result

class PluginRegistry:
    """
    Central registry for managing PersonaOS plugins.
    
    The registry tracks all loaded plugins, their states, and provides
    access to plugin instances and capabilities. It handles plugin
    lifecycle management and provides search/filtering capabilities.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize plugin registry.
        
        Args:
            config: PersonaOS configuration dictionary
        """
        self.config = config or {}
        self.logger = logging.getLogger("plugin_registry")
        
        # Core registry storage
        self._plugins: Dict[str, PluginRegistryEntry] = {}
        self._plugins_by_type: Dict[PluginType, Set[str]] = defaultdict(set)
        self._plugins_by_capability: Dict[str, Set[str]] = defaultdict(set)
        self._plugins_by_permission: Dict[str, Set[str]] = defaultdict(set)
        
        # Plugin access tracking
        self._plugin_aliases: Dict[str, str] = {}  # alias -> plugin_id
        self._dependency_graph: Dict[str, Set[str]] = {}  # plugin_id -> dependencies
        self._dependents_graph: Dict[str, Set[str]] = {}  # plugin_id -> dependents
        
        # Event handling
        self._event_handlers: Dict[str, List[Callable]] = defaultdict(list)
        
        # Thread safety
        self._registry_lock = threading.RLock()
        
        # Registry statistics
        self.stats = {
            "total_registered": 0,
            "total_loaded": 0,
            "total_active": 0,
            "total_failed": 0,
            "last_registry_update": time.time()
        }
        
        self.logger.info("PluginRegistry initialized")
    
    def register_plugin(self, plugin_id: str, plugin_instance: BasePlugin, 
                       metadata: PluginMetadata, discovery_info: Dict[str, Any] = None) -> bool:
        """
        Register a plugin in the registry.
        
        Args:
            plugin_id: Unique plugin identifier
            plugin_instance: Plugin instance to register
            metadata: Plugin metadata
            discovery_info: Information from plugin discovery
            
        Returns:
            True if registration successful, False otherwise
        """
        with self._registry_lock:
            try:
                # Check if plugin already registered
                if plugin_id in self._plugins:
                    self.logger.warning(f"Plugin {plugin_id} already registered")
                    return False
                
                # Validate plugin instance
                if not isinstance(plugin_instance, BasePlugin):
                    raise PluginRegistryError(f"Plugin {plugin_id} is not a BasePlugin instance")
                
                # Create registry entry
                entry = PluginRegistryEntry(plugin_id, plugin_instance, metadata, discovery_info)
                
                # Register in main registry
                self._plugins[plugin_id] = entry
                
                # Update indices
                self._plugins_by_type[metadata.plugin_type].add(plugin_id)
                
                # Index capabilities
                for capability in metadata.capabilities:
                    self._plugins_by_capability[capability.name].add(plugin_id)
                
                # Index permissions
                for permission in metadata.permissions:
                    self._plugins_by_permission[permission.name].add(plugin_id)
                
                # Register aliases
                if hasattr(metadata, 'aliases'):
                    for alias in getattr(metadata, 'aliases', []):
                        self._plugin_aliases[alias] = plugin_id
                
                # Update dependency tracking
                self._update_dependency_tracking(plugin_id, metadata)
                
                # Update statistics
                self._update_stats()
                
                # Fire registration event
                self._fire_event("plugin_registered", {
                    "plugin_id": plugin_id,
                    "metadata": metadata,
                    "entry": entry
                })
                
                self.logger.info(f"Plugin {plugin_id} registered successfully")
                return True
                
            except Exception as e:
                self.logger.error(f"Failed to register plugin {plugin_id}: {e}")
                return False
    
    def unregister_plugin(self, plugin_id: str) -> bool:
        """
        Unregister a plugin from the registry.
        
        Args:
            plugin_id: Plugin ID to unregister
            
        Returns:
            True if unregistration successful, False otherwise
        """
        with self._registry_lock:
            try:
                # Check if plugin exists
                if plugin_id not in self._plugins:
                    self.logger.warning(f"Plugin {plugin_id} not found in registry")
                    return False
                
                entry = self._plugins[plugin_id]
                metadata = entry.metadata
                
                # Remove from indices
                self._plugins_by_type[metadata.plugin_type].discard(plugin_id)
                
                for capability in metadata.capabilities:
                    self._plugins_by_capability[capability.name].discard(plugin_id)
                
                for permission in metadata.permissions:
                    self._plugins_by_permission[permission.name].discard(plugin_id)
                
                # Remove aliases
                aliases_to_remove = [alias for alias, pid in self._plugin_aliases.items() if pid == plugin_id]
                for alias in aliases_to_remove:
                    del self._plugin_aliases[alias]
                
                # Remove dependency tracking
                self._remove_dependency_tracking(plugin_id)
                
                # Remove from main registry
                del self._plugins[plugin_id]
                
                # Update statistics
                self._update_stats()
                
                # Fire unregistration event
                self._fire_event("plugin_unregistered", {
                    "plugin_id": plugin_id,
                    "metadata": metadata,
                    "entry": entry
                })
                
                self.logger.info(f"Plugin {plugin_id} unregistered successfully")
                return True
                
            except Exception as e:
                self.logger.error(f"Failed to unregister plugin {plugin_id}: {e}")
                return False
    
    def get_plugin(self, plugin_id: str) -> Optional[BasePlugin]:
        """
        Get plugin instance by ID.
        
        Args:
            plugin_id: Plugin ID or alias
            
        Returns:
            Plugin instance or None if not found
        """
        with self._registry_lock:
            # Resolve alias if needed
            actual_id = self._plugin_aliases.get(plugin_id, plugin_id)
            
            entry = self._plugins.get(actual_id)
            if entry:
                entry.record_access()
                return entry.plugin_instance
            
            return None
    
    def get_plugin_metadata(self, plugin_id: str) -> Optional[PluginMetadata]:
        """
        Get plugin metadata by ID.
        
        Args:
            plugin_id: Plugin ID or alias
            
        Returns:
            Plugin metadata or None if not found
        """
        with self._registry_lock:
            actual_id = self._plugin_aliases.get(plugin_id, plugin_id)
            entry = self._plugins.get(actual_id)
            return entry.metadata if entry else None
    
    def get_plugin_status(self, plugin_id: str) -> Optional[Dict[str, Any]]:
        """
        Get comprehensive plugin status.
        
        Args:
            plugin_id: Plugin ID or alias
            
        Returns:
            Plugin status dictionary or None if not found
        """
        with self._registry_lock:
            actual_id = self._plugin_aliases.get(plugin_id, plugin_id)
            entry = self._plugins.get(actual_id)
            return entry.get_status() if entry else None
    
    def list_plugins(self, plugin_type: Optional[PluginType] = None, 
                    state: Optional[PluginState] = None,
                    enabled_only: bool = False) -> List[str]:
        """
        List plugin IDs matching criteria.
        
        Args:
            plugin_type: Filter by plugin type
            state: Filter by plugin state
            enabled_only: Only return enabled plugins
            
        Returns:
            List of plugin IDs matching criteria
        """
        with self._registry_lock:
            plugin_ids = []
            
            # Start with all plugins or filter by type
            if plugin_type:
                candidate_ids = self._plugins_by_type.get(plugin_type, set())
            else:
                candidate_ids = set(self._plugins.keys())
            
            # Apply filters
            for plugin_id in candidate_ids:
                entry = self._plugins[plugin_id]
                
                # Check state filter
                if state and entry.plugin_instance.state != state:
                    continue
                
                # Check enabled filter
                if enabled_only and not entry.enabled:
                    continue
                
                plugin_ids.append(plugin_id)
            
            return sorted(plugin_ids)
    
    def find_plugins_by_capability(self, capability_name: str) -> List[str]:
        """
        Find plugins that provide a specific capability.
        
        Args:
            capability_name: Name of capability to search for
            
        Returns:
            List of plugin IDs that provide the capability
        """
        with self._registry_lock:
            return list(self._plugins_by_capability.get(capability_name, set()))
    
    def find_plugins_by_permission(self, permission_name: str) -> List[str]:
        """
        Find plugins that require a specific permission.
        
        Args:
            permission_name: Name of permission to search for
            
        Returns:
            List of plugin IDs that require the permission
        """
        with self._registry_lock:
            return list(self._plugins_by_permission.get(permission_name, set()))
    
    def get_plugin_dependencies(self, plugin_id: str) -> Set[str]:
        """
        Get plugin dependencies.
        
        Args:
            plugin_id: Plugin ID to get dependencies for
            
        Returns:
            Set of plugin IDs that this plugin depends on
        """
        with self._registry_lock:
            return self._dependency_graph.get(plugin_id, set()).copy()
    
    def get_plugin_dependents(self, plugin_id: str) -> Set[str]:
        """
        Get plugins that depend on this plugin.
        
        Args:
            plugin_id: Plugin ID to get dependents for
            
        Returns:
            Set of plugin IDs that depend on this plugin
        """
        with self._registry_lock:
            return self._dependents_graph.get(plugin_id, set()).copy()
    
    def is_plugin_enabled(self, plugin_id: str) -> bool:
        """
        Check if plugin is enabled.
        
        Args:
            plugin_id: Plugin ID to check
            
        Returns:
            True if plugin is enabled, False otherwise
        """
        with self._registry_lock:
            actual_id = self._plugin_aliases.get(plugin_id, plugin_id)
            entry = self._plugins.get(actual_id)
            return entry.enabled if entry else False
    
    def enable_plugin(self, plugin_id: str) -> bool:
        """
        Enable a plugin.
        
        Args:
            plugin_id: Plugin ID to enable
            
        Returns:
            True if successful, False otherwise
        """
        with self._registry_lock:
            actual_id = self._plugin_aliases.get(plugin_id, plugin_id)
            entry = self._plugins.get(actual_id)
            
            if entry:
                entry.enabled = True
                self.logger.info(f"Plugin {plugin_id} enabled")
                
                self._fire_event("plugin_enabled", {
                    "plugin_id": plugin_id,
                    "entry": entry
                })
                
                return True
            
            return False
    
    def disable_plugin(self, plugin_id: str) -> bool:
        """
        Disable a plugin.
        
        Args:
            plugin_id: Plugin ID to disable
            
        Returns:
            True if successful, False otherwise
        """
        with self._registry_lock:
            actual_id = self._plugin_aliases.get(plugin_id, plugin_id)
            entry = self._plugins.get(actual_id)
            
            if entry:
                entry.enabled = False
                self.logger.info(f"Plugin {plugin_id} disabled")
                
                self._fire_event("plugin_disabled", {
                    "plugin_id": plugin_id,
                    "entry": entry
                })
                
                return True
            
            return False
    
    def record_plugin_error(self, plugin_id: str, error: Exception):
        """
        Record an error for a plugin.
        
        Args:
            plugin_id: Plugin ID that had error
            error: Exception that occurred
        """
        with self._registry_lock:
            actual_id = self._plugin_aliases.get(plugin_id, plugin_id)
            entry = self._plugins.get(actual_id)
            
            if entry:
                entry.record_error(error)
                
                self._fire_event("plugin_error", {
                    "plugin_id": plugin_id,
                    "error": error,
                    "entry": entry
                })
    
    def perform_health_checks(self) -> Dict[str, Dict[str, Any]]:
        """
        Perform health checks on all enabled plugins.
        
        Returns:
            Dictionary mapping plugin IDs to health check results
        """
        results = {}
        
        with self._registry_lock:
            enabled_plugins = [
                (pid, entry) for pid, entry in self._plugins.items() 
                if entry.enabled
            ]
        
        # Perform health checks outside the lock
        for plugin_id, entry in enabled_plugins:
            try:
                health_result = entry.plugin_instance.get_health_check()
                
                with self._registry_lock:
                    entry.update_health_check(health_result)
                
                results[plugin_id] = health_result
                
            except Exception as e:
                self.logger.error(f"Health check failed for plugin {plugin_id}: {e}")
                
                error_result = {
                    "healthy": False,
                    "state": entry.plugin_instance.state.value,
                    "last_check": time.time(),
                    "errors": [str(e)]
                }
                
                with self._registry_lock:
                    entry.update_health_check(error_result)
                    entry.record_error(e)
                
                results[plugin_id] = error_result
        
        return results
    
    def get_registry_stats(self) -> Dict[str, Any]:
        """
        Get registry statistics.
        
        Returns:
            Registry statistics dictionary
        """
        with self._registry_lock:
            self._update_stats()
            return self.stats.copy()
    
    def add_event_handler(self, event_type: str, handler: Callable):
        """
        Add event handler for registry events.
        
        Args:
            event_type: Type of event to handle
            handler: Callable to handle the event
        """
        with self._registry_lock:
            self._event_handlers[event_type].append(handler)
    
    def remove_event_handler(self, event_type: str, handler: Callable):
        """
        Remove event handler.
        
        Args:
            event_type: Type of event
            handler: Handler to remove
        """
        with self._registry_lock:
            if handler in self._event_handlers[event_type]:
                self._event_handlers[event_type].remove(handler)
    
    def _update_dependency_tracking(self, plugin_id: str, metadata: PluginMetadata):
        """Update dependency tracking for a plugin."""
        # Build dependency graph
        dependencies = set()
        for dep in metadata.dependencies:
            dependencies.add(dep.name)
        
        self._dependency_graph[plugin_id] = dependencies
        
        # Update dependents graph
        for dep_id in dependencies:
            if dep_id not in self._dependents_graph:
                self._dependents_graph[dep_id] = set()
            self._dependents_graph[dep_id].add(plugin_id)
    
    def _remove_dependency_tracking(self, plugin_id: str):
        """Remove dependency tracking for a plugin."""
        # Remove from dependency graph
        dependencies = self._dependency_graph.pop(plugin_id, set())
        
        # Remove from dependents graph
        for dep_id in dependencies:
            if dep_id in self._dependents_graph:
                self._dependents_graph[dep_id].discard(plugin_id)
        
        # Remove as a dependent
        for deps in self._dependents_graph.values():
            deps.discard(plugin_id)
    
    def _update_stats(self):
        """Update registry statistics."""
        self.stats["total_registered"] = len(self._plugins)
        self.stats["total_loaded"] = len([p for p in self._plugins.values() 
                                         if p.plugin_instance.state in [PluginState.LOADED, PluginState.ACTIVATED]])
        self.stats["total_active"] = len([p for p in self._plugins.values() 
                                         if p.plugin_instance.state == PluginState.ACTIVATED])
        self.stats["total_failed"] = len([p for p in self._plugins.values() 
                                         if p.plugin_instance.state == PluginState.FAILED])
        self.stats["last_registry_update"] = time.time()
    
    def _fire_event(self, event_type: str, event_data: Dict[str, Any]):
        """Fire registry event to handlers."""
        handlers = self._event_handlers.get(event_type, [])
        
        for handler in handlers:
            try:
                handler(event_type, event_data)
            except Exception as e:
                self.logger.error(f"Event handler error for {event_type}: {e}")
    
    def clear_registry(self):
        """Clear all plugins from registry (for testing/shutdown)."""
        with self._registry_lock:
            plugin_ids = list(self._plugins.keys())
            
            for plugin_id in plugin_ids:
                self.unregister_plugin(plugin_id)
            
            self.logger.info("Plugin registry cleared")
    
    def __len__(self) -> int:
        """Return number of registered plugins."""
        with self._registry_lock:
            return len(self._plugins)
    
    def __contains__(self, plugin_id: str) -> bool:
        """Check if plugin is registered."""
        with self._registry_lock:
            actual_id = self._plugin_aliases.get(plugin_id, plugin_id)
            return actual_id in self._plugins
    
    def __iter__(self):
        """Iterate over plugin IDs."""
        with self._registry_lock:
            return iter(self._plugins.keys())