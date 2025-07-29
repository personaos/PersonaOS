"""
Base Plugin Interface for PersonaOS

This module defines the core plugin architecture that all PersonaOS plugins must implement.
"""

import time
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
import logging

class PluginState(Enum):
    """Plugin lifecycle states."""
    DISCOVERED = "discovered"
    LOADED = "loaded"
    ACTIVATED = "activated"
    DEACTIVATED = "deactivated"
    FAILED = "failed"
    UNLOADED = "unloaded"

class PluginType(Enum):
    """Types of plugins supported by PersonaOS."""
    TOOL = "tool"                    # Extends tool system
    WORKFLOW = "workflow"            # Provides workflow templates
    INTENT = "intent"               # Adds intent patterns
    SERVICE = "service"             # Background services
    UI_EXTENSION = "ui_extension"   # UI enhancements
    INTEGRATION = "integration"     # External app integrations

@dataclass
class PluginCapability:
    """Represents a capability provided by a plugin."""
    name: str
    description: str
    version: str
    parameters: Dict[str, Any] = field(default_factory=dict)

@dataclass
class PluginDependency:
    """Represents a plugin dependency."""
    name: str
    version: str
    min_version: Optional[str] = None
    max_version: Optional[str] = None
    optional: bool = False

@dataclass
class PluginPermission:
    """Represents a permission required by a plugin."""
    name: str
    description: str
    risk_level: str = "low"  # low, medium, high, critical

@dataclass
class PluginMetadata:
    """Plugin metadata schema."""
    # Core identification
    name: str
    version: str
    description: str
    author: str
    
    # Plugin properties
    plugin_type: PluginType
    api_version: str = "1.0"
    
    # Dependencies and requirements
    dependencies: List[PluginDependency] = field(default_factory=list)
    permissions: List[PluginPermission] = field(default_factory=list)
    capabilities: List[PluginCapability] = field(default_factory=list)
    
    # Configuration
    config_schema: Optional[Dict[str, Any]] = None
    default_config: Dict[str, Any] = field(default_factory=dict)
    
    # Voice integration
    supports_voice: bool = True
    voice_commands: List[str] = field(default_factory=list)
    voice_aliases: List[str] = field(default_factory=list)
    
    # Metadata
    tags: List[str] = field(default_factory=list)
    homepage: Optional[str] = None
    repository: Optional[str] = None
    license: str = "MIT"
    
    # System requirements
    min_python_version: str = "3.8"
    min_personaos_version: str = "0.1.0"
    
    # Runtime info (set by system)
    plugin_id: Optional[str] = None
    loaded_at: Optional[float] = None
    file_path: Optional[str] = None

class PluginAPI:
    """
    Plugin API interface providing access to PersonaOS core services.
    This is injected into plugins to allow controlled access to system functionality.
    """
    
    def __init__(self, plugin_id: str, permissions: Set[str], core_services: Dict[str, Any]):
        """
        Initialize plugin API.
        
        Args:
            plugin_id: Unique plugin identifier
            permissions: Set of granted permissions
            core_services: Core PersonaOS services
        """
        self.plugin_id = plugin_id
        self.permissions = permissions
        self.core_services = core_services
        self.logger = logging.getLogger(f"plugin.{plugin_id}")
    
    def has_permission(self, permission: str) -> bool:
        """Check if plugin has a specific permission."""
        return permission in self.permissions
    
    def require_permission(self, permission: str):
        """Require a specific permission, raise exception if not granted."""
        if not self.has_permission(permission):
            raise PermissionError(f"Plugin {self.plugin_id} lacks required permission: {permission}")
    
    # Core service access methods
    def get_config(self) -> Dict[str, Any]:
        """Get PersonaOS configuration (read-only)."""
        self.require_permission("config.read")
        return self.core_services.get("config", {}).copy()
    
    def get_tool_registry(self):
        """Get tool registry for registering new tools."""
        self.require_permission("tools.register")
        return self.core_services.get("tool_registry")
    
    def get_workflow_manager(self):
        """Get workflow manager for workflow operations."""
        self.require_permission("workflows.manage")
        return self.core_services.get("workflow_manager")
    
    def get_intent_processor(self):
        """Get intent processor for adding custom intents."""
        self.require_permission("intents.add")
        return self.core_services.get("intent_processor")
    
    def get_safety_validator(self):
        """Get safety validator for safety checks."""
        self.require_permission("safety.validate")
        return self.core_services.get("safety_validator")
    
    def log_info(self, message: str):
        """Log info message."""
        self.logger.info(message)
    
    def log_warning(self, message: str):
        """Log warning message."""
        self.logger.warning(message)
    
    def log_error(self, message: str):
        """Log error message."""
        self.logger.error(message)
    
    def send_audio_feedback(self, message: str, priority: str = "normal"):
        """Send audio feedback message."""
        self.require_permission("audio.speak")
        audio_feedback = self.core_services.get("audio_feedback")
        if audio_feedback:
            audio_feedback._queue_audio_feedback(message, priority, True)
    
    def store_plugin_data(self, key: str, value: Any):
        """Store plugin-specific data."""
        self.require_permission("storage.write")
        # Implementation would use a plugin-specific storage system
        pass
    
    def get_plugin_data(self, key: str, default: Any = None) -> Any:
        """Retrieve plugin-specific data."""
        self.require_permission("storage.read")
        # Implementation would use a plugin-specific storage system
        return default

class BasePlugin(ABC):
    """
    Abstract base class that all PersonaOS plugins must inherit from.
    
    This defines the plugin lifecycle and provides the interface for
    integrating with the PersonaOS core system.
    """
    
    def __init__(self):
        """Initialize the plugin. Subclasses should call super().__init__()."""
        self.metadata: Optional[PluginMetadata] = None
        self.api: Optional[PluginAPI] = None
        self.state = PluginState.DISCOVERED
        self.config: Dict[str, Any] = {}
        self.logger: Optional[logging.Logger] = None
        self._loaded_at: Optional[float] = None
        self._activated_at: Optional[float] = None
    
    @abstractmethod
    def get_metadata(self) -> PluginMetadata:
        """
        Return plugin metadata. This must be implemented by all plugins.
        
        Returns:
            PluginMetadata object with complete plugin information
        """
        pass
    
    def set_api(self, api: PluginAPI):
        """Set the plugin API interface. Called by the plugin loader."""
        self.api = api
        self.logger = api.logger
    
    def set_config(self, config: Dict[str, Any]):
        """Set plugin configuration. Called by the plugin loader."""
        self.config = config
    
    def validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate plugin configuration against schema.
        
        Args:
            config: Configuration to validate
            
        Returns:
            Dictionary with validation results
        """
        # Default implementation - plugins can override for custom validation
        return {"valid": True, "errors": []}
    
    def on_load(self) -> bool:
        """
        Called when the plugin is loaded but not yet activated.
        Use this for one-time initialization that doesn't require core services.
        
        Returns:
            True if load successful, False otherwise
        """
        self._loaded_at = time.time()
        self.state = PluginState.LOADED
        if self.logger:
            self.logger.info(f"Plugin {self.get_metadata().name} loaded successfully")
        return True
    
    def on_activate(self) -> bool:
        """
        Called when the plugin is activated and should start providing its capabilities.
        Core PersonaOS services are available via self.api at this point.
        
        Returns:
            True if activation successful, False otherwise
        """
        self._activated_at = time.time()
        self.state = PluginState.ACTIVATED
        if self.logger:
            self.logger.info(f"Plugin {self.get_metadata().name} activated successfully")
        return True
    
    def on_deactivate(self) -> bool:
        """
        Called when the plugin should stop providing its capabilities.
        Clean up any resources but keep the plugin loaded.
        
        Returns:
            True if deactivation successful, False otherwise
        """
        self.state = PluginState.DEACTIVATED
        if self.logger:
            self.logger.info(f"Plugin {self.get_metadata().name} deactivated")
        return True
    
    def on_unload(self) -> bool:
        """
        Called when the plugin is being completely unloaded.
        Perform final cleanup of all resources.
        
        Returns:
            True if unload successful, False otherwise
        """
        self.state = PluginState.UNLOADED
        if self.logger:
            self.logger.info(f"Plugin {self.get_metadata().name} unloaded")
        return True
    
    def on_config_changed(self, new_config: Dict[str, Any]) -> bool:
        """
        Called when plugin configuration is updated.
        
        Args:
            new_config: New configuration dictionary
            
        Returns:
            True if config change handled successfully, False otherwise
        """
        self.config = new_config
        if self.logger:
            self.logger.info(f"Plugin {self.get_metadata().name} configuration updated")
        return True
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current plugin status information.
        
        Returns:
            Status dictionary with plugin state and metrics
        """
        metadata = self.get_metadata()
        return {
            "name": metadata.name,
            "version": metadata.version,
            "state": self.state.value,
            "plugin_type": metadata.plugin_type.value,
            "loaded_at": self._loaded_at,
            "activated_at": self._activated_at,
            "capabilities": [cap.name for cap in metadata.capabilities],
            "permissions": [perm.name for perm in metadata.permissions],
            "supports_voice": metadata.supports_voice,
            "config_valid": len(self.validate_config(self.config).get("errors", [])) == 0
        }
    
    def get_health_check(self) -> Dict[str, Any]:
        """
        Perform health check and return status.
        Plugins can override this for custom health monitoring.
        
        Returns:
            Health check results
        """
        return {
            "healthy": self.state == PluginState.ACTIVATED,
            "state": self.state.value,
            "last_check": time.time(),
            "errors": []
        }

class ToolPlugin(BasePlugin):
    """
    Specialized base class for tool plugins.
    Tool plugins extend the PersonaOS tool system with new capabilities.
    """
    
    def __init__(self):
        super().__init__()
    
    @abstractmethod
    def get_tools(self) -> List[Any]:
        """
        Return list of tools provided by this plugin.
        
        Returns:
            List of tool instances
        """
        pass
    
    def on_activate(self) -> bool:
        """Activate tool plugin by registering tools."""
        if not super().on_activate():
            return False
        
        try:
            # Register tools with the tool registry
            tool_registry = self.api.get_tool_registry()
            if tool_registry:
                for tool in self.get_tools():
                    tool_registry.register_tool(tool)
                    self.logger.info(f"Registered tool: {tool.name}")
            
            return True
        except Exception as e:
            self.logger.error(f"Failed to activate tool plugin: {e}")
            self.state = PluginState.FAILED
            return False
    
    def on_deactivate(self) -> bool:
        """Deactivate tool plugin by unregistering tools."""
        try:
            # Unregister tools from the tool registry
            tool_registry = self.api.get_tool_registry()
            if tool_registry:
                for tool in self.get_tools():
                    # Tool registry would need an unregister method
                    if hasattr(tool_registry, 'unregister_tool'):
                        tool_registry.unregister_tool(tool.name)
                        self.logger.info(f"Unregistered tool: {tool.name}")
            
            return super().on_deactivate()
        except Exception as e:
            self.logger.error(f"Failed to deactivate tool plugin: {e}")
            return False

class WorkflowPlugin(BasePlugin):
    """
    Specialized base class for workflow plugins.
    Workflow plugins provide new workflow templates and patterns.
    """
    
    def __init__(self):
        super().__init__()
    
    @abstractmethod
    def get_workflow_templates(self) -> Dict[str, Dict[str, Any]]:
        """
        Return workflow templates provided by this plugin.
        
        Returns:
            Dictionary of workflow templates
        """
        pass
    
    def on_activate(self) -> bool:
        """Activate workflow plugin by registering templates."""
        if not super().on_activate():
            return False
        
        try:
            # Register workflow templates
            workflow_manager = self.api.get_workflow_manager()
            if workflow_manager:
                templates = self.get_workflow_templates()
                for template_name, template_config in templates.items():
                    # Workflow manager would need a register template method
                    if hasattr(workflow_manager, 'register_workflow_template'):
                        workflow_manager.register_workflow_template(template_name, template_config)
                        self.logger.info(f"Registered workflow template: {template_name}")
            
            return True
        except Exception as e:
            self.logger.error(f"Failed to activate workflow plugin: {e}")
            self.state = PluginState.FAILED
            return False

class IntentPlugin(BasePlugin):
    """
    Specialized base class for intent plugins.
    Intent plugins add new intent patterns and classifications.
    """
    
    def __init__(self):
        super().__init__()
    
    @abstractmethod
    def get_intent_patterns(self) -> Dict[str, List[str]]:
        """
        Return intent patterns provided by this plugin.
        
        Returns:
            Dictionary mapping intent names to pattern lists
        """
        pass
    
    def on_activate(self) -> bool:
        """Activate intent plugin by registering patterns."""
        if not super().on_activate():
            return False
        
        try:
            # Register intent patterns
            intent_processor = self.api.get_intent_processor()
            if intent_processor:
                patterns = self.get_intent_patterns()
                for intent_name, pattern_list in patterns.items():
                    for pattern in pattern_list:
                        # Intent processor would need an add pattern method
                        if hasattr(intent_processor, 'add_custom_pattern'):
                            intent_processor.add_custom_pattern({
                                "name": intent_name,
                                "pattern": pattern,
                                "plugin": self.get_metadata().name
                            })
                            self.logger.info(f"Registered intent pattern: {intent_name}")
            
            return True
        except Exception as e:
            self.logger.error(f"Failed to activate intent plugin: {e}")
            self.state = PluginState.FAILED
            return False