"""
Plugin Discovery Manager for PersonaOS

This module provides high-level plugin discovery management, integrating
with the PersonaOS configuration system and providing orchestrated
plugin discovery workflows.
"""

import os
import logging
import threading
import time
from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Callable
from dataclasses import dataclass, field

from .plugin_scanner import PluginScanner
from .plugin_registry import PluginRegistry
from .plugin_loader import PluginLoader

@dataclass
class PluginDiscoveryConfig:
    """Configuration for plugin discovery."""
    enabled: bool = True
    directories: List[str] = field(default_factory=list)
    auto_load: bool = True
    strict_validation: bool = True
    allow_dev_plugins: bool = False
    max_size_mb: int = 50
    allowed_permissions: Set[str] = field(default_factory=set)
    blocked_permissions: Set[str] = field(default_factory=set)
    hot_reload: bool = False
    debug_mode: bool = False
    load_timeout: int = 30

class PluginDiscoveryManager:
    """
    High-level manager for plugin discovery and integration.
    
    This manager orchestrates the plugin discovery process, integrating
    the scanner, registry, and loader components while providing
    configuration management and monitoring capabilities.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize plugin discovery manager.
        
        Args:
            config: PersonaOS configuration dictionary
        """
        self.config = config or {}
        self.logger = logging.getLogger("plugin_discovery_manager")
        
        # Load plugin discovery configuration
        self.discovery_config = self._load_discovery_config()
        
        # Initialize components
        self.scanner = PluginScanner(config)
        self.registry = PluginRegistry(config)
        self.loader = PluginLoader(config, self.registry, self.scanner)
        
        # Discovery state
        self.discovery_active = False
        self.last_discovery_time = None
        self.discovery_results = {}
        self.discovery_stats = {
            "total_discoveries": 0,
            "successful_discoveries": 0,
            "failed_discoveries": 0,
            "last_discovery_duration": 0
        }
        
        # Event handlers
        self.discovery_handlers: Dict[str, List[Callable]] = {
            "discovery_started": [],
            "discovery_completed": [],
            "plugin_discovered": [],
            "plugin_validation_failed": [],
            "discovery_failed": []
        }
        
        # Threading
        self._discovery_lock = threading.RLock()
        self._background_discovery_thread = None
        self._shutdown_event = threading.Event()
        
        # Apply configuration to components
        self._configure_components()
        
        self.logger.info(f"PluginDiscoveryManager initialized with {len(self.discovery_config.directories)} directories")
    
    def _load_discovery_config(self) -> PluginDiscoveryConfig:
        """Load plugin discovery configuration from system config."""
        config = PluginDiscoveryConfig()
        
        # Basic settings
        config.enabled = self.config.get("plugin_system_enabled", True)
        config.auto_load = self.config.get("plugin_auto_load", True)
        config.strict_validation = self.config.get("plugin_strict_validation", True)
        config.allow_dev_plugins = self.config.get("plugin_allow_dev", False)
        config.max_size_mb = self.config.get("plugin_max_size_mb", 50)
        config.hot_reload = self.config.get("plugin_hot_reload", False)
        config.debug_mode = self.config.get("plugin_debug_mode", False)
        config.load_timeout = self.config.get("plugin_load_timeout", 30)
        
        # Parse directories
        directories_str = self.config.get("plugin_directories", "plugins,extensions,user_plugins")
        if directories_str:
            config.directories = [d.strip() for d in directories_str.split(",") if d.strip()]
        
        # Parse permissions
        allowed_perms_str = self.config.get("plugin_allowed_permissions", "")
        if allowed_perms_str:
            config.allowed_permissions = set(p.strip() for p in allowed_perms_str.split(",") if p.strip())
        
        blocked_perms_str = self.config.get("plugin_blocked_permissions", "")
        if blocked_perms_str:
            config.blocked_permissions = set(p.strip() for p in blocked_perms_str.split(",") if p.strip())
        
        return config
    
    def _configure_components(self):
        """Configure scanner, registry, and loader with discovery config."""
        # Update scanner configuration
        if hasattr(self.scanner, 'strict_validation'):
            self.scanner.strict_validation = self.discovery_config.strict_validation
        if hasattr(self.scanner, 'allow_dev_plugins'):
            self.scanner.allow_dev_plugins = self.discovery_config.allow_dev_plugins
        if hasattr(self.scanner, 'max_plugin_size'):
            self.scanner.max_plugin_size = self.discovery_config.max_size_mb * 1024 * 1024
        
        # Add configured plugin directories
        for directory in self.discovery_config.directories:
            try:
                dir_path = Path(directory).expanduser().resolve()
                self.scanner.add_plugin_directory(dir_path)
            except Exception as e:
                self.logger.warning(f"Invalid plugin directory '{directory}': {e}")
        
        # Update loader configuration
        if hasattr(self.loader, 'hot_reload_enabled'):
            self.loader.hot_reload_enabled = self.discovery_config.hot_reload
    
    def discover_plugins(self, directories: Optional[List[str]] = None, 
                        validate_only: bool = False) -> Dict[str, Any]:
        """
        Discover plugins from specified directories or all configured directories.
        
        Args:
            directories: Specific directories to scan (optional)
            validate_only: Only validate, don't load plugins
            
        Returns:
            Discovery results dictionary
        """
        if not self.discovery_config.enabled:
            return {
                "success": False,
                "error": "Plugin system is disabled",
                "plugins": []
            }
        
        with self._discovery_lock:
            if self.discovery_active:
                return {
                    "success": False,
                    "error": "Discovery already in progress",
                    "plugins": []
                }
            
            self.discovery_active = True
            start_time = time.time()
            
            try:
                self.logger.info("Starting plugin discovery")
                self._fire_event("discovery_started", {"validate_only": validate_only})
                
                # Discover plugins
                if directories:
                    # Scan specific directories
                    discovered_plugins = []
                    for directory in directories:
                        dir_path = Path(directory).expanduser().resolve()
                        plugins = self.scanner.scan_directory(dir_path)
                        discovered_plugins.extend(plugins)
                else:
                    # Scan all configured directories
                    discovered_plugins = self.scanner.scan_all_plugins()
                
                self.discovery_stats["total_discoveries"] += len(discovered_plugins)
                
                # Process discovered plugins
                processed_plugins = []
                valid_plugins = []
                invalid_plugins = []
                
                for plugin_info in discovered_plugins:
                    try:
                        # Enhanced validation
                        validation_result = self._enhanced_plugin_validation(plugin_info)
                        plugin_info["enhanced_validation"] = validation_result
                        
                        processed_plugins.append(plugin_info)
                        
                        if validation_result.get("valid", False):
                            valid_plugins.append(plugin_info)
                            self._fire_event("plugin_discovered", {"plugin": plugin_info})
                        else:
                            invalid_plugins.append(plugin_info)
                            self._fire_event("plugin_validation_failed", {
                                "plugin": plugin_info,
                                "errors": validation_result.get("errors", [])
                            })
                            
                    except Exception as e:
                        self.logger.error(f"Error processing plugin {plugin_info.get('name', 'unknown')}: {e}")
                        plugin_info["processing_error"] = str(e)
                        invalid_plugins.append(plugin_info)
                
                # Load plugins if not validate_only
                load_results = {}
                if not validate_only and self.discovery_config.auto_load and valid_plugins:
                    self.logger.info(f"Auto-loading {len(valid_plugins)} valid plugins")
                    
                    try:
                        load_results = self.loader.discover_and_load_all_plugins()
                    except Exception as e:
                        self.logger.error(f"Error during plugin loading: {e}")
                        load_results = {"success": False, "error": str(e)}
                
                # Compile results
                discovery_duration = time.time() - start_time
                self.discovery_stats["last_discovery_duration"] = discovery_duration
                self.discovery_stats["successful_discoveries"] += len(valid_plugins)
                self.discovery_stats["failed_discoveries"] += len(invalid_plugins)
                
                results = {
                    "success": True,
                    "discovery_time": time.time(),
                    "duration": discovery_duration,
                    "total_discovered": len(discovered_plugins),
                    "valid_plugins": len(valid_plugins),
                    "invalid_plugins": len(invalid_plugins),
                    "plugins": processed_plugins,
                    "valid_plugin_details": valid_plugins,
                    "invalid_plugin_details": invalid_plugins,
                    "load_results": load_results,
                    "validate_only": validate_only
                }
                
                self.discovery_results = results
                self.last_discovery_time = time.time()
                
                self._fire_event("discovery_completed", results)
                
                self.logger.info(f"Plugin discovery completed: {len(valid_plugins)}/{len(discovered_plugins)} plugins valid")
                
                return results
                
            except Exception as e:
                self.logger.error(f"Plugin discovery failed: {e}")
                
                error_results = {
                    "success": False,
                    "error": str(e),
                    "discovery_time": time.time(),
                    "duration": time.time() - start_time
                }
                
                self._fire_event("discovery_failed", error_results)
                
                return error_results
                
            finally:
                self.discovery_active = False
    
    def _enhanced_plugin_validation(self, plugin_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform enhanced plugin validation beyond basic scanner validation.
        
        Args:
            plugin_info: Plugin information from scanner
            
        Returns:
            Enhanced validation results
        """
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "security_checks": {},
            "compatibility_checks": {},
            "dependency_checks": {}
        }
        
        try:
            # Get base validation results
            base_validation = plugin_info.get("validation_result", {})
            if not base_validation.get("valid", False):
                validation_result["valid"] = False
                validation_result["errors"].extend(base_validation.get("errors", []))
                validation_result["warnings"].extend(base_validation.get("warnings", []))
            
            # Enhanced security validation
            security_result = self._validate_plugin_security(plugin_info)
            validation_result["security_checks"] = security_result
            
            if not security_result.get("passed", True):
                validation_result["valid"] = False
                validation_result["errors"].extend(security_result.get("errors", []))
            
            # Compatibility validation
            compatibility_result = self._validate_plugin_compatibility(plugin_info)
            validation_result["compatibility_checks"] = compatibility_result
            
            if not compatibility_result.get("compatible", True):
                validation_result["valid"] = False
                validation_result["errors"].extend(compatibility_result.get("errors", []))
            
            # Dependency validation
            dependency_result = self._validate_plugin_dependencies(plugin_info)
            validation_result["dependency_checks"] = dependency_result
            
            if not dependency_result.get("satisfied", True):
                validation_result["warnings"].extend(dependency_result.get("warnings", []))
                # Dependencies might not fail validation but issue warnings
            
            # Configuration validation
            config_result = self._validate_plugin_configuration(plugin_info)
            if not config_result.get("valid", True):
                validation_result["warnings"].extend(config_result.get("warnings", []))
            
        except Exception as e:
            self.logger.error(f"Enhanced validation failed for plugin {plugin_info.get('name', 'unknown')}: {e}")
            validation_result["valid"] = False
            validation_result["errors"].append(f"Validation error: {e}")
        
        return validation_result
    
    def _validate_plugin_security(self, plugin_info: Dict[str, Any]) -> Dict[str, Any]:
        """Validate plugin security aspects."""
        security_result = {
            "passed": True,
            "errors": [],
            "warnings": [],
            "checks": {}
        }
        
        try:
            metadata = plugin_info.get("metadata", {})
            
            # Check permissions against allowed/blocked lists
            permissions = metadata.get("permissions", [])
            for permission in permissions:
                perm_name = permission.get("name") if isinstance(permission, dict) else str(permission)
                
                # Check blocked permissions
                if perm_name in self.discovery_config.blocked_permissions:
                    security_result["passed"] = False
                    security_result["errors"].append(f"Blocked permission requested: {perm_name}")
                
                # Check allowed permissions (if allowlist is configured)
                if (self.discovery_config.allowed_permissions and 
                    perm_name not in self.discovery_config.allowed_permissions):
                    security_result["warnings"].append(f"Permission not in allowlist: {perm_name}")
            
            security_result["checks"]["permissions"] = "passed" if not security_result["errors"] else "failed"
            
            # Check for development plugins in production
            if not self.discovery_config.allow_dev_plugins:
                is_dev_plugin = (
                    metadata.get("development", False) or
                    metadata.get("version", "").endswith("-dev") or
                    "dev" in metadata.get("tags", [])
                )
                
                if is_dev_plugin:
                    security_result["passed"] = False
                    security_result["errors"].append("Development plugins not allowed")
            
            security_result["checks"]["dev_plugins"] = "passed" if self.discovery_config.allow_dev_plugins else "restricted"
            
        except Exception as e:
            security_result["passed"] = False
            security_result["errors"].append(f"Security validation error: {e}")
        
        return security_result
    
    def _validate_plugin_compatibility(self, plugin_info: Dict[str, Any]) -> Dict[str, Any]:
        """Validate plugin compatibility with PersonaOS version and environment."""
        compatibility_result = {
            "compatible": True,
            "errors": [],
            "warnings": [],
            "checks": {}
        }
        
        try:
            metadata = plugin_info.get("metadata", {})
            
            # Check minimum PersonaOS version
            min_personaos_version = metadata.get("min_personaos_version", "0.1.0")
            current_version = self.config.get("personaos_version", "0.1.0")
            
            # Simple version comparison (would use proper semver in production)
            if min_personaos_version > current_version:
                compatibility_result["compatible"] = False
                compatibility_result["errors"].append(
                    f"Requires PersonaOS {min_personaos_version}, current version is {current_version}"
                )
            
            compatibility_result["checks"]["personaos_version"] = "compatible" if min_personaos_version <= current_version else "incompatible"
            
            # Check Python version
            import sys
            min_python_version = metadata.get("min_python_version", "3.8")
            current_python = f"{sys.version_info.major}.{sys.version_info.minor}"
            
            if min_python_version > current_python:
                compatibility_result["compatible"] = False
                compatibility_result["errors"].append(
                    f"Requires Python {min_python_version}, current version is {current_python}"
                )
            
            compatibility_result["checks"]["python_version"] = "compatible" if min_python_version <= current_python else "incompatible"
            
            # Check plugin API version
            api_version = metadata.get("api_version", "1.0")
            supported_api_versions = ["1.0"]  # Would be configurable
            
            if api_version not in supported_api_versions:
                compatibility_result["warnings"].append(
                    f"Plugin API version {api_version} may not be fully supported"
                )
            
            compatibility_result["checks"]["api_version"] = "supported" if api_version in supported_api_versions else "unsupported"
            
        except Exception as e:
            compatibility_result["compatible"] = False
            compatibility_result["errors"].append(f"Compatibility validation error: {e}")
        
        return compatibility_result
    
    def _validate_plugin_dependencies(self, plugin_info: Dict[str, Any]) -> Dict[str, Any]:
        """Validate plugin dependencies."""
        dependency_result = {
            "satisfied": True,
            "warnings": [],
            "missing_dependencies": [],
            "available_dependencies": []
        }
        
        try:
            metadata = plugin_info.get("metadata", {})
            dependencies = metadata.get("dependencies", [])
            
            for dependency in dependencies:
                dep_name = dependency.get("name") if isinstance(dependency, dict) else str(dependency)
                dep_version = dependency.get("version", "*") if isinstance(dependency, dict) else "*"
                dep_optional = dependency.get("optional", False) if isinstance(dependency, dict) else False
                
                # Check if dependency is available in registry
                available = dep_name in self.registry
                
                if available:
                    dependency_result["available_dependencies"].append({
                        "name": dep_name,
                        "version": dep_version,
                        "found": True
                    })
                else:
                    dependency_result["missing_dependencies"].append({
                        "name": dep_name,
                        "version": dep_version,
                        "optional": dep_optional
                    })
                    
                    if not dep_optional:
                        dependency_result["satisfied"] = False
                        dependency_result["warnings"].append(
                            f"Required dependency not found: {dep_name} {dep_version}"
                        )
                    else:
                        dependency_result["warnings"].append(
                            f"Optional dependency not found: {dep_name} {dep_version}"
                        )
        
        except Exception as e:
            dependency_result["warnings"].append(f"Dependency validation error: {e}")
        
        return dependency_result
    
    def _validate_plugin_configuration(self, plugin_info: Dict[str, Any]) -> Dict[str, Any]:
        """Validate plugin configuration requirements."""
        config_result = {
            "valid": True,
            "warnings": [],
            "missing_config": [],
            "available_config": []
        }
        
        try:
            metadata = plugin_info.get("metadata", {})
            config_schema = metadata.get("config_schema", {})
            
            if config_schema:
                # Check if plugin has configuration available
                plugin_name = metadata.get("name", plugin_info.get("name", "unknown"))
                plugin_config = self.config.get("plugin_configs", {}).get(plugin_name, {})
                
                # Simple validation - check required fields
                required_fields = []
                for field_name, field_spec in config_schema.items():
                    if isinstance(field_spec, dict) and field_spec.get("required", False):
                        required_fields.append(field_name)
                
                for required_field in required_fields:
                    if required_field not in plugin_config:
                        config_result["missing_config"].append(required_field)
                        config_result["warnings"].append(
                            f"Required configuration missing: {required_field}"
                        )
                
                # Track available config
                for field_name in config_schema.keys():
                    if field_name in plugin_config:
                        config_result["available_config"].append(field_name)
        
        except Exception as e:
            config_result["warnings"].append(f"Configuration validation error: {e}")
        
        return config_result
    
    def get_discovery_status(self) -> Dict[str, Any]:
        """Get current discovery status and statistics."""
        return {
            "active": self.discovery_active,
            "enabled": self.discovery_config.enabled,
            "last_discovery": self.last_discovery_time,
            "stats": self.discovery_stats.copy(),
            "config": {
                "directories": self.discovery_config.directories,
                "auto_load": self.discovery_config.auto_load,
                "strict_validation": self.discovery_config.strict_validation,
                "allow_dev_plugins": self.discovery_config.allow_dev_plugins,
                "hot_reload": self.discovery_config.hot_reload
            },
            "registry_stats": self.registry.get_registry_stats(),
            "loader_stats": self.loader.get_load_statistics()
        }
    
    def get_last_discovery_results(self) -> Optional[Dict[str, Any]]:
        """Get results from the last discovery operation."""
        return self.discovery_results.copy() if self.discovery_results else None
    
    def add_discovery_handler(self, event_type: str, handler: Callable):
        """Add event handler for discovery events."""
        if event_type in self.discovery_handlers:
            self.discovery_handlers[event_type].append(handler)
    
    def remove_discovery_handler(self, event_type: str, handler: Callable):
        """Remove event handler for discovery events."""
        if event_type in self.discovery_handlers and handler in self.discovery_handlers[event_type]:
            self.discovery_handlers[event_type].remove(handler)
    
    def _fire_event(self, event_type: str, event_data: Dict[str, Any]):
        """Fire discovery event to registered handlers."""
        handlers = self.discovery_handlers.get(event_type, [])
        
        for handler in handlers:
            try:
                handler(event_type, event_data)
            except Exception as e:
                self.logger.error(f"Discovery event handler error for {event_type}: {e}")
    
    def start_background_discovery(self, interval_minutes: int = 60):
        """Start background plugin discovery with specified interval."""
        if self._background_discovery_thread and self._background_discovery_thread.is_alive():
            self.logger.warning("Background discovery already running")
            return
        
        def background_discovery():
            while not self._shutdown_event.wait(interval_minutes * 60):
                try:
                    self.logger.info("Starting background plugin discovery")
                    self.discover_plugins()
                except Exception as e:
                    self.logger.error(f"Background discovery error: {e}")
        
        self._background_discovery_thread = threading.Thread(
            target=background_discovery,
            name="PluginBackgroundDiscovery",
            daemon=True
        )
        self._background_discovery_thread.start()
        
        self.logger.info(f"Started background plugin discovery with {interval_minutes}-minute interval")
    
    def stop_background_discovery(self):
        """Stop background plugin discovery."""
        if self._background_discovery_thread and self._background_discovery_thread.is_alive():
            self._shutdown_event.set()
            self._background_discovery_thread.join(timeout=5)
            self.logger.info("Stopped background plugin discovery")
    
    def reload_configuration(self):
        """Reload plugin discovery configuration."""
        self.discovery_config = self._load_discovery_config()
        self._configure_components()
        self.logger.info("Plugin discovery configuration reloaded")
    
    def shutdown(self):
        """Shutdown the discovery manager and clean up resources."""
        self.logger.info("Shutting down plugin discovery manager")
        
        # Stop background discovery
        self.stop_background_discovery()
        
        # Clear discovery state
        with self._discovery_lock:
            self.discovery_active = False
            self.discovery_results = {}
        
        self.logger.info("Plugin discovery manager shutdown complete")