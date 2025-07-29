"""
Plugin CLI Management Interface for PersonaOS

This module provides command-line interface tools for managing plugins,
including listing, loading, activating, deactivating, and configuring plugins.
"""

import argparse
import sys
import json
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
from .system_integration_manager import SystemIntegrationManager
from .plugin_manager import PluginManager

class PluginCLIManager:
    """
    Command-line interface for PersonaOS plugin management.
    
    Provides comprehensive CLI tools for plugin operations including:
    - Plugin discovery and listing
    - Plugin loading, activation, and deactivation
    - Plugin status and health monitoring
    - Security and sandbox management
    - Tool integration management
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize plugin CLI manager.
        
        Args:
            config: PersonaOS configuration dictionary
        """
        self.config = config or {}
        self.logger = logging.getLogger("plugin_cli_manager")
        
        # Core services (to be initialized)
        self.integration_manager: Optional[SystemIntegrationManager] = None
        self.plugin_manager: Optional[PluginManager] = None
        
        # CLI state
        self.verbose = False
        self.output_format = "text"  # text, json
        
        self.logger.info("PluginCLIManager initialized")
    
    def initialize(self, core_services: Dict[str, Any] = None) -> bool:
        """
        Initialize CLI manager with core services.
        
        Args:
            core_services: Core PersonaOS services
            
        Returns:
            True if initialization successful
        """
        try:
            # Initialize system integration manager
            self.integration_manager = SystemIntegrationManager(self.config)
            
            if core_services:
                init_result = self.integration_manager.initialize(core_services)
                if not init_result.get("success", False):
                    self.logger.error(f"Integration manager initialization failed: {init_result.get('error')}")
                    return False
                
                self.plugin_manager = self.integration_manager.plugin_manager
            else:
                # Initialize standalone plugin manager for basic operations
                self.plugin_manager = PluginManager(self.config)
                plugin_init = self.plugin_manager.initialize()
                if not plugin_init.get("success", False):
                    self.logger.error(f"Plugin manager initialization failed: {plugin_init.get('error')}")
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"CLI manager initialization failed: {e}")
            return False
    
    def create_parser(self) -> argparse.ArgumentParser:
        """Create argument parser for plugin CLI commands."""
        parser = argparse.ArgumentParser(
            description="PersonaOS Plugin Management CLI",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  # List all plugins
  python -m core.plugins.plugin_cli_manager list
  
  # Show plugin status
  python -m core.plugins.plugin_cli_manager status my_plugin
  
  # Load and activate a plugin
  python -m core.plugins.plugin_cli_manager load /path/to/plugin
  
  # Discover and load all plugins
  python -m core.plugins.plugin_cli_manager discover
  
  # Show system health
  python -m core.plugins.plugin_cli_manager health
            """
        )
        
        # Global options
        parser.add_argument("--verbose", "-v", action="store_true",
                          help="Enable verbose output")
        parser.add_argument("--format", choices=["text", "json"], default="text",
                          help="Output format (default: text)")
        parser.add_argument("--config", type=str,
                          help="Path to configuration file")
        
        # Subcommands
        subparsers = parser.add_subparsers(dest="command", help="Available commands")
        
        # List command
        list_parser = subparsers.add_parser("list", help="List plugins")
        list_parser.add_argument("--state", choices=["all", "loaded", "activated", "deactivated"],
                               default="all", help="Filter by plugin state")
        list_parser.add_argument("--type", help="Filter by plugin type")
        
        # Status command
        status_parser = subparsers.add_parser("status", help="Show plugin status")
        status_parser.add_argument("plugin_id", nargs="?", help="Plugin ID (optional)")
        status_parser.add_argument("--detailed", action="store_true",
                                 help="Show detailed status information")
        
        # Discover command
        discover_parser = subparsers.add_parser("discover", help="Discover and load plugins")
        discover_parser.add_argument("--path", type=str, help="Specific path to scan")
        discover_parser.add_argument("--activate", action="store_true",
                                   help="Activate plugins after loading")
        
        # Load command
        load_parser = subparsers.add_parser("load", help="Load a specific plugin")
        load_parser.add_argument("path", help="Path to plugin file or directory")
        load_parser.add_argument("--activate", action="store_true",
                               help="Activate plugin after loading")
        
        # Activate command
        activate_parser = subparsers.add_parser("activate", help="Activate a plugin")
        activate_parser.add_argument("plugin_id", help="Plugin ID to activate")
        
        # Deactivate command
        deactivate_parser = subparsers.add_parser("deactivate", help="Deactivate a plugin")
        deactivate_parser.add_argument("plugin_id", help="Plugin ID to deactivate")
        
        # Unload command
        unload_parser = subparsers.add_parser("unload", help="Unload a plugin")
        unload_parser.add_argument("plugin_id", help="Plugin ID to unload")
        
        # Health command
        health_parser = subparsers.add_parser("health", help="Show system health")
        health_parser.add_argument("--components", action="store_true",
                                 help="Show component health details")
        
        # Tools command
        tools_parser = subparsers.add_parser("tools", help="Manage plugin tools")
        tools_subparsers = tools_parser.add_subparsers(dest="tool_action")
        
        tools_subparsers.add_parser("list", help="List plugin tools")
        tools_subparsers.add_parser("register", help="Register plugin tools").add_argument("plugin_id", nargs="?")
        tools_subparsers.add_parser("unregister", help="Unregister plugin tools").add_argument("plugin_id", nargs="?")
        tools_subparsers.add_parser("status", help="Show tool registration status")
        
        # Security command
        security_parser = subparsers.add_parser("security", help="Manage plugin security")
        security_subparsers = security_parser.add_subparsers(dest="security_action")
        
        security_subparsers.add_parser("status", help="Show security status")
        security_subparsers.add_parser("violations", help="List security violations")
        security_subparsers.add_parser("sandbox", help="Show sandbox status")
        
        return parser
    
    def handle_command(self, args: argparse.Namespace) -> int:
        """
        Handle CLI command execution.
        
        Args:
            args: Parsed command arguments
            
        Returns:
            Exit code (0 for success, non-zero for error)
        """
        self.verbose = args.verbose
        self.output_format = args.format
        
        # Initialize if not already done
        if not self.plugin_manager:
            if not self.initialize():
                self.print_error("Failed to initialize plugin system")
                return 1
        
        try:
            if args.command == "list":
                return self.cmd_list(args)
            elif args.command == "status":
                return self.cmd_status(args)
            elif args.command == "discover":
                return self.cmd_discover(args)
            elif args.command == "load":
                return self.cmd_load(args)
            elif args.command == "activate":
                return self.cmd_activate(args)
            elif args.command == "deactivate":
                return self.cmd_deactivate(args)
            elif args.command == "unload":
                return self.cmd_unload(args)
            elif args.command == "health":
                return self.cmd_health(args)
            elif args.command == "tools":
                return self.cmd_tools(args)
            elif args.command == "security":
                return self.cmd_security(args)
            else:
                self.print_error(f"Unknown command: {args.command}")
                return 1
                
        except Exception as e:
            self.print_error(f"Command execution failed: {e}")
            if self.verbose:
                import traceback
                self.print_error(traceback.format_exc())
            return 1
    
    def cmd_list(self, args: argparse.Namespace) -> int:
        """Handle list command."""
        plugins = self.plugin_manager.list_plugins()
        
        if not plugins:
            self.print_message("No plugins found")
            return 0
        
        # Filter by state if specified
        if args.state != "all":
            from .base_plugin import PluginState
            state_filter = PluginState(args.state.upper())
            filtered_plugins = []
            for plugin_id in plugins:
                plugin_status = self.plugin_manager.get_plugin_status(plugin_id)
                if plugin_status.get("state") == state_filter.value:
                    filtered_plugins.append(plugin_id)
            plugins = filtered_plugins
        
        if self.output_format == "json":
            plugin_details = {}
            for plugin_id in plugins:
                plugin_details[plugin_id] = self.plugin_manager.get_plugin_status(plugin_id)
            self.print_json(plugin_details)
        else:
            self.print_message(f"Found {len(plugins)} plugin(s):")
            for plugin_id in plugins:
                status = self.plugin_manager.get_plugin_status(plugin_id)
                state = status.get("state", "unknown")
                version = status.get("metadata", {}).get("version", "unknown")
                self.print_message(f"  {plugin_id} (state: {state}, version: {version})")
        
        return 0
    
    def cmd_status(self, args: argparse.Namespace) -> int:
        """Handle status command."""
        if args.plugin_id:
            # Show specific plugin status
            status = self.plugin_manager.get_plugin_status(args.plugin_id)
            if not status or status.get("error"):
                self.print_error(f"Plugin '{args.plugin_id}' not found")
                return 1
            
            if self.output_format == "json":
                self.print_json(status)
            else:
                self.print_plugin_status(args.plugin_id, status, args.detailed)
        else:
            # Show system status
            if self.integration_manager:
                status = self.integration_manager.get_integration_status()
            else:
                status = {"plugin_manager_available": True, "total_plugins": len(self.plugin_manager)}
            
            if self.output_format == "json":
                self.print_json(status)
            else:
                self.print_system_status(status)
        
        return 0
    
    def cmd_discover(self, args: argparse.Namespace) -> int:
        """Handle discover command."""
        self.print_message("Discovering and loading plugins...")
        
        if self.integration_manager:
            result = self.integration_manager.discover_and_load_plugins()
        else:
            result = self.plugin_manager.loader.discover_and_load_all_plugins()
        
        if result.get("success", False):
            loaded_count = result.get("loaded_count", 0)
            self.print_message(f"Successfully loaded {loaded_count} plugin(s)")
            
            if args.activate and loaded_count > 0:
                self.print_message("Activating loaded plugins...")
                # Activation would be handled by the integration manager
        else:
            self.print_error(f"Plugin discovery failed: {result.get('error')}")
            return 1
        
        if self.output_format == "json":
            self.print_json(result)
        
        return 0
    
    def cmd_load(self, args: argparse.Namespace) -> int:
        """Handle load command."""
        self.print_error("Single plugin loading not yet implemented")
        return 1
    
    def cmd_activate(self, args: argparse.Namespace) -> int:
        """Handle activate command."""
        result = self.plugin_manager.activate_plugin(args.plugin_id)
        
        if result:
            self.print_message(f"Plugin '{args.plugin_id}' activated successfully")
            return 0
        else:
            self.print_error(f"Failed to activate plugin '{args.plugin_id}'")
            return 1
    
    def cmd_deactivate(self, args: argparse.Namespace) -> int:
        """Handle deactivate command."""
        result = self.plugin_manager.deactivate_plugin(args.plugin_id)
        
        if result:
            self.print_message(f"Plugin '{args.plugin_id}' deactivated successfully")
            return 0
        else:
            self.print_error(f"Failed to deactivate plugin '{args.plugin_id}'")
            return 1
    
    def cmd_unload(self, args: argparse.Namespace) -> int:
        """Handle unload command."""
        result = self.plugin_manager.unload_plugin(args.plugin_id)
        
        if result:
            self.print_message(f"Plugin '{args.plugin_id}' unloaded successfully")
            return 0
        else:
            self.print_error(f"Failed to unload plugin '{args.plugin_id}'")
            return 1
    
    def cmd_health(self, args: argparse.Namespace) -> int:
        """Handle health command."""
        health = self.plugin_manager.get_system_health()
        
        if self.output_format == "json":
            self.print_json(health)
        else:
            self.print_message("Plugin System Health:")
            self.print_message(f"  Overall Status: {health.get('status', 'unknown')}")
            self.print_message(f"  Total Plugins: {health.get('total_plugins', 0)}")
            self.print_message(f"  Active Plugins: {health.get('active_plugins', 0)}")
            self.print_message(f"  Error Count: {health.get('error_count', 0)}")
            
            if args.components and "component_health" in health:
                self.print_message("\nComponent Health:")
                for component, component_health in health["component_health"].items():
                    status = component_health.get("status", "unknown")
                    self.print_message(f"  {component}: {status}")
        
        return 0
    
    def cmd_tools(self, args: argparse.Namespace) -> int:
        """Handle tools command."""
        if not hasattr(args, "tool_action") or not args.tool_action:
            self.print_error("Tool action required")
            return 1
        
        if not self.plugin_manager.tool_bridge:
            self.print_error("Tool bridge not available")
            return 1
        
        if args.tool_action == "list":
            status = self.plugin_manager.get_plugin_tool_status()
            if self.output_format == "json":
                self.print_json(status)
            else:
                self.print_message("Plugin Tool Status:")
                for plugin_id, tool_status in status.items():
                    if tool_status.get("registered", False):
                        tool_name = tool_status.get("tool_name", "unknown")
                        self.print_message(f"  {plugin_id} -> {tool_name}")
        
        elif args.tool_action == "status":
            stats = self.plugin_manager.get_tool_bridge_statistics()
            if self.output_format == "json":
                self.print_json(stats)
            else:
                self.print_message("Tool Bridge Statistics:")
                self.print_message(f"  Total Plugin Tools: {stats.get('total_plugin_tools', 0)}")
                self.print_message(f"  Auto Register: {stats.get('auto_register_enabled', False)}")
        
        return 0
    
    def cmd_security(self, args: argparse.Namespace) -> int:
        """Handle security command."""
        if not hasattr(args, "security_action") or not args.security_action:
            self.print_error("Security action required")
            return 1
        
        if args.security_action == "status":
            # Get security status from plugin manager
            if hasattr(self.plugin_manager.loader, "security_manager") and self.plugin_manager.loader.security_manager:
                stats = self.plugin_manager.loader.security_manager.get_security_stats()
                if self.output_format == "json":
                    self.print_json(stats)
                else:
                    self.print_message("Plugin Security Status:")
                    self.print_message(f"  Total Secured Plugins: {stats.get('total_plugins_secured', 0)}")
                    self.print_message(f"  Active Security Contexts: {stats.get('active_security_contexts', 0)}")
                    self.print_message(f"  Violations Detected: {stats.get('violations_detected', 0)}")
                    self.print_message(f"  Sandboxed Plugins: {stats.get('sandboxed_plugins', 0)}")
            else:
                self.print_message("Security manager not available")
        
        return 0
    
    def print_plugin_status(self, plugin_id: str, status: Dict[str, Any], detailed: bool = False):
        """Print formatted plugin status."""
        self.print_message(f"Plugin: {plugin_id}")
        self.print_message(f"  State: {status.get('state', 'unknown')}")
        
        metadata = status.get("metadata", {})
        if metadata:
            self.print_message(f"  Version: {metadata.get('version', 'unknown')}")
            self.print_message(f"  Description: {metadata.get('description', 'No description')}")
            self.print_message(f"  Author: {metadata.get('author', 'Unknown')}")
        
        if detailed:
            self.print_message(f"  Load Time: {status.get('load_time', 'unknown')}")
            if "permissions" in status:
                self.print_message(f"  Permissions: {', '.join(status['permissions'])}")
    
    def print_system_status(self, status: Dict[str, Any]):
        """Print formatted system status."""
        self.print_message("Plugin System Status:")
        self.print_message(f"  Initialized: {status.get('initialized', False)}")
        
        if "plugin_system" in status:
            ps = status["plugin_system"]
            self.print_message(f"  System Enabled: {ps.get('system_enabled', False)}")
            self.print_message(f"  Auto Load: {ps.get('auto_load_enabled', False)}")
            self.print_message(f"  Total Plugins: {ps.get('total_plugins', 0)}")
        
        if "active_integrations" in status:
            integrations = status["active_integrations"]
            self.print_message(f"  Active Integrations: {', '.join(integrations) if integrations else 'None'}")
    
    def print_message(self, message: str):
        """Print a message to stdout."""
        print(message)
    
    def print_error(self, error: str):
        """Print an error message to stderr."""
        print(f"Error: {error}", file=sys.stderr)
    
    def print_json(self, data: Any):
        """Print data as formatted JSON."""
        print(json.dumps(data, indent=2, default=str))

def main():
    """Main CLI entry point."""
    cli_manager = PluginCLIManager()
    parser = cli_manager.create_parser()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    return cli_manager.handle_command(args)

if __name__ == "__main__":
    sys.exit(main())