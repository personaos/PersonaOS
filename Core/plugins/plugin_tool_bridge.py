"""
Plugin Tool Bridge for PersonaOS

This module provides a bridge between the plugin system and the existing
tool registry, allowing plugins to register themselves as tools and
participate in voice-enabled tool execution.
"""

import logging
from typing import Dict, Any, Optional, List
from ..tools.tool_registry import BaseTool, ToolResult, VoiceToolContext
from .base_plugin import BasePlugin, PluginState
from .plugin_registry import PluginRegistry

class PluginToolAdapter(BaseTool):
    """
    Adapter that wraps a plugin to make it compatible with the tool system.
    
    This allows plugins to be registered as tools and used with voice commands,
    parameter collection, and audio feedback.
    """
    
    def __init__(self, plugin: BasePlugin, plugin_metadata: Any):
        """
        Initialize plugin tool adapter.
        
        Args:
            plugin: Plugin instance to wrap
            plugin_metadata: Plugin metadata with tool information
        """
        # Get tool information from plugin metadata
        tool_info = getattr(plugin_metadata, 'tool_info', None)
        
        name = tool_info.get('name', plugin_metadata.name) if tool_info else plugin_metadata.name
        description = tool_info.get('description', plugin_metadata.description) if tool_info else plugin_metadata.description
        
        super().__init__(name, description)
        
        self.plugin = plugin
        self.plugin_metadata = plugin_metadata
        self.logger = logging.getLogger(f"plugin_tool.{name}")
        
        # Configure voice support from plugin metadata
        if tool_info:
            self.supports_voice = tool_info.get('supports_voice', True)
            self.voice_aliases = tool_info.get('voice_aliases', [])
            self.requires_confirmation = tool_info.get('requires_confirmation', False)
            self.voice_parameter_patterns = tool_info.get('voice_parameter_patterns', {})
            self.parameter_specs = tool_info.get('parameter_specs', [])
            self.supports_parameter_collection = tool_info.get('supports_parameter_collection', False)
        
        # Check if plugin has tool execution methods
        self.has_tool_execute = hasattr(plugin, 'execute_tool')
        self.has_voice_execute = hasattr(plugin, 'execute_tool_with_voice')
        
        if not self.has_tool_execute:
            self.logger.warning(f"Plugin {name} does not implement execute_tool method")
    
    def execute(self, **kwargs) -> ToolResult:
        """
        Execute the plugin as a tool.
        
        Args:
            **kwargs: Tool parameters
            
        Returns:
            ToolResult with execution outcome
        """
        if self.plugin.state != PluginState.ACTIVATED:
            return ToolResult(
                success=False,
                error=f"Plugin {self.name} is not activated (state: {self.plugin.state.value})"
            )
        
        if not self.has_tool_execute:
            return ToolResult(
                success=False,
                error=f"Plugin {self.name} does not support tool execution"
            )
        
        try:
            # Execute plugin tool method
            result = self.plugin.execute_tool(**kwargs)
            
            # Convert plugin result to ToolResult
            if isinstance(result, dict):
                return ToolResult(
                    success=result.get('success', True),
                    data=result.get('data'),
                    error=result.get('error'),
                    metadata=result.get('metadata'),
                    voice_response=result.get('voice_response')
                )
            else:
                # Assume success if plugin returns non-dict
                return ToolResult(
                    success=True,
                    data=result
                )
                
        except Exception as e:
            self.logger.error(f"Plugin tool execution failed: {e}")
            return ToolResult(
                success=False,
                error=f"Plugin execution error: {str(e)}"
            )
    
    def execute_with_voice_context(self, voice_context: VoiceToolContext, **kwargs) -> ToolResult:
        """
        Execute plugin tool with voice context.
        
        Args:
            voice_context: Voice execution context
            **kwargs: Tool parameters
            
        Returns:
            ToolResult with voice-specific formatting
        """
        if self.plugin.state != PluginState.ACTIVATED:
            return ToolResult(
                success=False,
                error=f"Plugin {self.name} is not activated (state: {self.plugin.state.value})",
                voice_response=f"The {self.name} plugin is not available right now."
            )
        
        # Use plugin's voice execution method if available
        if self.has_voice_execute:
            try:
                result = self.plugin.execute_tool_with_voice(voice_context, **kwargs)
                
                # Convert plugin result to ToolResult
                if isinstance(result, dict):
                    return ToolResult(
                        success=result.get('success', True),
                        data=result.get('data'),
                        error=result.get('error'),
                        metadata=result.get('metadata'),
                        voice_response=result.get('voice_response')
                    )
                else:
                    return ToolResult(
                        success=True,
                        data=result,
                        voice_response=self.format_voice_response(result, voice_context)
                    )
                    
            except Exception as e:
                self.logger.error(f"Plugin voice tool execution failed: {e}")
                return ToolResult(
                    success=False,
                    error=f"Plugin voice execution error: {str(e)}",
                    voice_response=f"I encountered an error while running {self.name}."
                )
        
        # Fall back to regular execution with voice formatting
        result = self.execute(**kwargs)
        
        # Add voice response if not already present
        if result.success and not result.voice_response:
            result.voice_response = self.format_voice_response(result.data, voice_context)
        
        return result
    
    def format_voice_response(self, data: Any, voice_context: VoiceToolContext) -> str:
        """
        Format plugin result for voice output.
        
        Args:
            data: Plugin execution result
            voice_context: Voice execution context
            
        Returns:
            Voice-friendly response string
        """
        # Check if plugin has custom voice formatting
        if hasattr(self.plugin, 'format_voice_response'):
            try:
                return self.plugin.format_voice_response(data, voice_context)
            except Exception as e:
                self.logger.warning(f"Plugin voice formatting failed: {e}")
        
        # Use default formatting
        return super().format_voice_response(data, voice_context)
    
    def parse_voice_parameters(self, voice_text: str) -> Dict[str, Any]:
        """
        Parse voice parameters using plugin-specific logic.
        
        Args:
            voice_text: Voice command text
            
        Returns:
            Parsed parameters dictionary
        """
        # Check if plugin has custom parameter parsing
        if hasattr(self.plugin, 'parse_voice_parameters'):
            try:
                return self.plugin.parse_voice_parameters(voice_text)
            except Exception as e:
                self.logger.warning(f"Plugin parameter parsing failed: {e}")
        
        # Use default parsing
        return super().parse_voice_parameters(voice_text)
    
    def validate_args(self, **kwargs) -> bool:
        """
        Validate tool arguments using plugin logic.
        
        Args:
            **kwargs: Arguments to validate
            
        Returns:
            True if arguments are valid
        """
        # Check if plugin has custom validation
        if hasattr(self.plugin, 'validate_tool_args'):
            try:
                return self.plugin.validate_tool_args(**kwargs)
            except Exception as e:
                self.logger.warning(f"Plugin argument validation failed: {e}")
                return False
        
        # Use default validation
        return super().validate_args(**kwargs)
    
    def get_voice_confirmation_prompt(self, **kwargs) -> Optional[str]:
        """
        Get confirmation prompt from plugin.
        
        Args:
            **kwargs: Tool parameters
            
        Returns:
            Confirmation prompt or None
        """
        # Check if plugin has custom confirmation
        if hasattr(self.plugin, 'get_voice_confirmation_prompt'):
            try:
                return self.plugin.get_voice_confirmation_prompt(**kwargs)
            except Exception as e:
                self.logger.warning(f"Plugin confirmation prompt failed: {e}")
        
        # Use default confirmation
        return super().get_voice_confirmation_prompt(**kwargs)

class PluginToolBridge:
    """
    Bridge between the plugin system and tool registry.
    
    Manages the registration of plugins as tools and handles their
    integration with the existing tool execution infrastructure.
    """
    
    def __init__(self, plugin_registry: PluginRegistry, tool_registry: Any, config: Dict[str, Any] = None):
        """
        Initialize plugin tool bridge.
        
        Args:
            plugin_registry: Plugin registry instance
            tool_registry: Tool registry instance
            config: Configuration dictionary
        """
        self.plugin_registry = plugin_registry
        self.tool_registry = tool_registry
        self.config = config or {}
        self.logger = logging.getLogger("plugin_tool_bridge")
        
        # Track plugin-tool mappings
        self.plugin_tool_adapters: Dict[str, PluginToolAdapter] = {}
        self.tool_enabled_plugins: Dict[str, str] = {}  # tool_name -> plugin_id
        
        # Bridge configuration
        self.auto_register_tools = config.get("plugin_auto_register_tools", True)
        self.tool_prefix = config.get("plugin_tool_prefix", "")
        self.tool_suffix = config.get("plugin_tool_suffix", "")
        
        self.logger.info("PluginToolBridge initialized")
    
    def register_plugin_as_tool(self, plugin_id: str) -> bool:
        """
        Register a plugin as a tool in the tool registry.
        
        Args:
            plugin_id: Plugin ID to register
            
        Returns:
            True if registration successful
        """
        try:
            # Get plugin from registry
            plugin = self.plugin_registry.get_plugin(plugin_id)
            if not plugin:
                self.logger.error(f"Plugin {plugin_id} not found in registry")
                return False
            
            plugin_metadata = self.plugin_registry.get_plugin_metadata(plugin_id)
            if not plugin_metadata:
                self.logger.error(f"Plugin metadata not found for {plugin_id}")
                return False
            
            # Check if plugin supports tool functionality
            if not self._plugin_supports_tools(plugin, plugin_metadata):
                self.logger.info(f"Plugin {plugin_id} does not support tool functionality")
                return False
            
            # Create tool adapter
            adapter = PluginToolAdapter(plugin, plugin_metadata)
            
            # Generate tool name with prefix/suffix if configured
            tool_name = f"{self.tool_prefix}{adapter.name}{self.tool_suffix}"
            adapter.name = tool_name
            
            # Register with tool registry
            self.tool_registry.register_tool(adapter)
            
            # Track the mapping
            self.plugin_tool_adapters[plugin_id] = adapter
            self.tool_enabled_plugins[tool_name] = plugin_id
            
            self.logger.info(f"Registered plugin {plugin_id} as tool '{tool_name}'")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to register plugin {plugin_id} as tool: {e}")
            return False
    
    def unregister_plugin_tool(self, plugin_id: str) -> bool:
        """
        Unregister a plugin tool from the tool registry.
        
        Args:
            plugin_id: Plugin ID to unregister
            
        Returns:
            True if unregistration successful
        """
        try:
            adapter = self.plugin_tool_adapters.get(plugin_id)
            if not adapter:
                self.logger.warning(f"Plugin {plugin_id} not registered as tool")
                return True  # Already unregistered
            
            tool_name = adapter.name
            
            # Remove from tool registry (if supported)
            if hasattr(self.tool_registry, 'unregister_tool'):
                self.tool_registry.unregister_tool(tool_name)
            elif hasattr(self.tool_registry, 'tools') and tool_name in self.tool_registry.tools:
                del self.tool_registry.tools[tool_name]
            
            # Clean up tracking
            del self.plugin_tool_adapters[plugin_id]
            if tool_name in self.tool_enabled_plugins:
                del self.tool_enabled_plugins[tool_name]
            
            self.logger.info(f"Unregistered plugin tool '{tool_name}' (plugin: {plugin_id})")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to unregister plugin tool for {plugin_id}: {e}")
            return False
    
    def register_all_plugin_tools(self) -> Dict[str, bool]:
        """
        Register all eligible plugins as tools.
        
        Returns:
            Dictionary mapping plugin_id to registration success
        """
        results = {}
        
        for plugin_id in self.plugin_registry.list_plugins():
            if plugin_id not in self.plugin_tool_adapters:  # Not already registered
                results[plugin_id] = self.register_plugin_as_tool(plugin_id)
        
        successful = sum(1 for success in results.values() if success)
        self.logger.info(f"Registered {successful}/{len(results)} plugins as tools")
        
        return results
    
    def unregister_all_plugin_tools(self) -> Dict[str, bool]:
        """
        Unregister all plugin tools.
        
        Returns:
            Dictionary mapping plugin_id to unregistration success
        """
        results = {}
        
        # Copy keys to avoid modification during iteration
        plugin_ids = list(self.plugin_tool_adapters.keys())
        
        for plugin_id in plugin_ids:
            results[plugin_id] = self.unregister_plugin_tool(plugin_id)
        
        successful = sum(1 for success in results.values() if success)
        self.logger.info(f"Unregistered {successful}/{len(results)} plugin tools")
        
        return results
    
    def get_plugin_tool_status(self, plugin_id: str) -> Dict[str, Any]:
        """
        Get tool registration status for a plugin.
        
        Args:
            plugin_id: Plugin ID to check
            
        Returns:
            Status information dictionary
        """
        adapter = self.plugin_tool_adapters.get(plugin_id)
        
        if not adapter:
            return {
                "registered": False,
                "plugin_id": plugin_id
            }
        
        return {
            "registered": True,
            "plugin_id": plugin_id,
            "tool_name": adapter.name,
            "supports_voice": adapter.supports_voice,
            "requires_confirmation": adapter.requires_confirmation,
            "voice_aliases": adapter.voice_aliases,
            "supports_parameter_collection": adapter.supports_parameter_collection
        }
    
    def get_all_plugin_tool_status(self) -> Dict[str, Dict[str, Any]]:
        """
        Get tool registration status for all plugins.
        
        Returns:
            Dictionary mapping plugin_id to status info
        """
        status = {}
        
        # Check all plugins in registry
        for plugin_id in self.plugin_registry.list_plugins():
            status[plugin_id] = self.get_plugin_tool_status(plugin_id)
        
        return status
    
    def find_plugin_by_tool_name(self, tool_name: str) -> Optional[str]:
        """
        Find plugin ID by tool name.
        
        Args:
            tool_name: Tool name to look up
            
        Returns:
            Plugin ID if found, None otherwise
        """
        return self.tool_enabled_plugins.get(tool_name)
    
    def get_tool_by_plugin_id(self, plugin_id: str) -> Optional[PluginToolAdapter]:
        """
        Get tool adapter by plugin ID.
        
        Args:
            plugin_id: Plugin ID
            
        Returns:
            Tool adapter if found, None otherwise
        """
        return self.plugin_tool_adapters.get(plugin_id)
    
    def handle_plugin_lifecycle_change(self, plugin_id: str, old_state: str, new_state: str):
        """
        Handle plugin lifecycle state changes.
        
        Args:
            plugin_id: Plugin that changed state
            old_state: Previous plugin state
            new_state: New plugin state
        """
        # Auto-register tools when plugins are activated
        if self.auto_register_tools and new_state == "activated":
            if plugin_id not in self.plugin_tool_adapters:
                self.register_plugin_as_tool(plugin_id)
        
        # Unregister tools when plugins are deactivated/unloaded
        elif new_state in ["deactivated", "unloaded", "error"]:
            if plugin_id in self.plugin_tool_adapters:
                self.unregister_plugin_tool(plugin_id)
        
        self.logger.debug(f"Handled lifecycle change for plugin {plugin_id}: {old_state} -> {new_state}")
    
    def _plugin_supports_tools(self, plugin: BasePlugin, plugin_metadata: Any) -> bool:
        """
        Check if a plugin supports tool functionality.
        
        Args:
            plugin: Plugin instance
            plugin_metadata: Plugin metadata
            
        Returns:
            True if plugin supports tools
        """
        # Check if plugin has tool execution methods
        if hasattr(plugin, 'execute_tool'):
            return True
        
        # Check if plugin metadata indicates tool support
        if hasattr(plugin_metadata, 'tool_info') and plugin_metadata.tool_info:
            return True
        
        # Check if plugin type indicates tool functionality
        if hasattr(plugin_metadata, 'plugin_type'):
            tool_types = ["TOOL", "VOICE_TOOL", "COMMAND"]
            if plugin_metadata.plugin_type.name in tool_types:
                return True
        
        return False
    
    def get_bridge_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the plugin-tool bridge.
        
        Returns:
            Statistics dictionary
        """
        return {
            "total_plugin_tools": len(self.plugin_tool_adapters),
            "registered_tools": list(self.tool_enabled_plugins.keys()),
            "plugin_tool_mappings": len(self.tool_enabled_plugins),
            "auto_register_enabled": self.auto_register_tools,
            "tool_prefix": self.tool_prefix,
            "tool_suffix": self.tool_suffix
        }
    
    def cleanup(self):
        """Clean up bridge resources."""
        self.unregister_all_plugin_tools()
        self.logger.info("PluginToolBridge cleaned up")