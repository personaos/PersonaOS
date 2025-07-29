"""
Plugin Web API for PersonaOS

This module provides FastAPI endpoints for web-based plugin management,
integrating with the existing PersonaOS web UI backend.
"""

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from pydantic import BaseModel
from typing import List, Optional, Dict, Any, Union
import logging
import asyncio
from pathlib import Path
import json
import time

from .system_integration_manager import SystemIntegrationManager
from .plugin_manager import PluginManager

# Pydantic models for plugin API

class PluginInfo(BaseModel):
    """Plugin information model."""
    plugin_id: str
    name: str
    version: str
    description: str
    author: str
    state: str
    plugin_type: str
    permissions: List[str] = []
    load_time: Optional[float] = None
    tool_registered: bool = False
    tool_name: Optional[str] = None
    security_level: Optional[str] = None
    sandbox_enabled: bool = False

class PluginListResponse(BaseModel):
    """Response model for plugin listing."""
    plugins: List[PluginInfo]
    total_count: int
    filtered_count: int
    system_status: Dict[str, Any]

class PluginStatusResponse(BaseModel):
    """Response model for plugin status."""
    plugin_id: str
    status: Dict[str, Any]
    security_info: Optional[Dict[str, Any]] = None
    tool_info: Optional[Dict[str, Any]] = None

class PluginActionRequest(BaseModel):
    """Request model for plugin actions."""
    plugin_id: str
    action: str  # activate, deactivate, unload, register_tool, unregister_tool
    parameters: Optional[Dict[str, Any]] = None

class PluginActionResponse(BaseModel):
    """Response model for plugin actions."""
    success: bool
    message: str
    plugin_id: str
    action: str
    result: Optional[Dict[str, Any]] = None

class PluginDiscoveryRequest(BaseModel):
    """Request model for plugin discovery."""
    paths: Optional[List[str]] = None
    activate_after_load: bool = False
    register_tools: bool = True

class PluginDiscoveryResponse(BaseModel):
    """Response model for plugin discovery."""
    success: bool
    message: str
    discovered_count: int
    loaded_count: int
    activated_count: int
    failed_count: int
    results: Dict[str, Any]

class SystemHealthResponse(BaseModel):
    """Response model for system health."""
    overall_status: str
    plugin_system: Dict[str, Any]
    integrations: Dict[str, Any]
    component_health: Dict[str, Any]
    statistics: Dict[str, Any]

class SecurityStatusResponse(BaseModel):
    """Response model for security status."""
    security_enabled: bool
    sandboxing_enabled: bool
    total_secured_plugins: int
    active_contexts: int
    violations_count: int
    sandbox_statistics: Dict[str, Any]
    recent_violations: List[Dict[str, Any]] = []

class PluginWebAPI:
    """
    Web API interface for PersonaOS plugin management.
    
    Provides comprehensive REST endpoints for plugin operations including:
    - Plugin listing and status monitoring
    - Plugin lifecycle management (load, activate, deactivate, unload)
    - Plugin discovery and bulk operations
    - Tool registration management
    - Security and sandbox monitoring
    - System health and statistics
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize plugin web API.
        
        Args:
            config: PersonaOS configuration dictionary
        """
        self.config = config or {}
        self.logger = logging.getLogger("plugin_web_api")
        
        # Core components (to be initialized)
        self.integration_manager: Optional[SystemIntegrationManager] = None
        self.plugin_manager: Optional[PluginManager] = None
        
        # API state
        self.initialized = False
        
        # Create FastAPI router
        self.router = APIRouter(prefix="/api/plugins", tags=["plugins"])
        self._setup_routes()
        
        self.logger.info("PluginWebAPI initialized")
    
    def initialize(self, core_services: Dict[str, Any] = None) -> bool:
        """
        Initialize API with core services.
        
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
                # Initialize standalone plugin manager
                self.plugin_manager = PluginManager(self.config)
                plugin_init = self.plugin_manager.initialize()
                if not plugin_init.get("success", False):
                    self.logger.error(f"Plugin manager initialization failed: {plugin_init.get('error')}")
                    return False
            
            self.initialized = True
            return True
            
        except Exception as e:
            self.logger.error(f"API initialization failed: {e}")
            return False
    
    def _setup_routes(self):
        """Setup API routes."""
        
        @self.router.get("/", response_model=PluginListResponse)
        async def list_plugins(
            state: Optional[str] = None,
            plugin_type: Optional[str] = None,
            limit: Optional[int] = None,
            offset: Optional[int] = 0
        ):
            """List all plugins with optional filtering."""
            return await self._list_plugins(state, plugin_type, limit, offset)
        
        @self.router.get("/{plugin_id}", response_model=PluginStatusResponse)
        async def get_plugin_status(plugin_id: str):
            """Get detailed status of a specific plugin."""
            return await self._get_plugin_status(plugin_id)
        
        @self.router.post("/discover", response_model=PluginDiscoveryResponse)
        async def discover_plugins(request: PluginDiscoveryRequest):
            """Discover and load plugins."""
            return await self._discover_plugins(request)
        
        @self.router.post("/action", response_model=PluginActionResponse)
        async def execute_plugin_action(request: PluginActionRequest):
            """Execute an action on a plugin."""
            return await self._execute_plugin_action(request)
        
        @self.router.get("/health", response_model=SystemHealthResponse)
        async def get_system_health():
            """Get plugin system health status."""
            return await self._get_system_health()
        
        @self.router.get("/security", response_model=SecurityStatusResponse)
        async def get_security_status():
            """Get plugin security status."""
            return await self._get_security_status()
        
        @self.router.get("/tools")
        async def get_plugin_tools():
            """Get list of plugin tools and their registration status."""
            return await self._get_plugin_tools()
        
        @self.router.post("/tools/register")
        async def register_plugin_tools(plugin_id: Optional[str] = None):
            """Register plugin(s) as tools."""
            return await self._register_plugin_tools(plugin_id)
        
        @self.router.post("/tools/unregister")
        async def unregister_plugin_tools(plugin_id: Optional[str] = None):
            """Unregister plugin tools."""
            return await self._unregister_plugin_tools(plugin_id)
    
    async def _list_plugins(self, state: Optional[str], plugin_type: Optional[str], 
                           limit: Optional[int], offset: int) -> PluginListResponse:
        """Handle plugin listing."""
        if not self.initialized:
            raise HTTPException(status_code=503, detail="Plugin system not initialized")
        
        try:
            # Get all plugins
            plugin_ids = self.plugin_manager.list_plugins()
            total_count = len(plugin_ids)
            
            # Build plugin info list
            plugins = []
            for plugin_id in plugin_ids:
                plugin_status = self.plugin_manager.get_plugin_status(plugin_id)
                
                if not plugin_status or plugin_status.get("error"):
                    continue
                
                # Apply filters
                if state and plugin_status.get("state") != state:
                    continue
                
                metadata = plugin_status.get("metadata", {})
                if plugin_type and metadata.get("plugin_type", {}).get("name") != plugin_type:
                    continue
                
                # Get tool registration status
                tool_info = {}
                if self.plugin_manager.tool_bridge:
                    tool_status = self.plugin_manager.get_plugin_tool_status(plugin_id)
                    tool_info = {
                        "tool_registered": tool_status.get("registered", False),
                        "tool_name": tool_status.get("tool_name")
                    }
                
                # Get security info
                security_info = {}
                if hasattr(self.plugin_manager.loader, "security_manager") and self.plugin_manager.loader.security_manager:
                    security_status = self.plugin_manager.loader.security_manager.get_security_status(plugin_id)
                    if not security_status.get("error"):
                        security_info = {
                            "security_level": security_status.get("security_level"),
                            "sandbox_enabled": security_status.get("sandbox_directory") is not None
                        }
                
                plugin_info = PluginInfo(
                    plugin_id=plugin_id,
                    name=metadata.get("name", plugin_id),
                    version=metadata.get("version", "unknown"),
                    description=metadata.get("description", "No description"),
                    author=metadata.get("author", "Unknown"),
                    state=plugin_status.get("state", "unknown"),
                    plugin_type=metadata.get("plugin_type", {}).get("name", "unknown"),
                    permissions=[p.get("name", str(p)) for p in metadata.get("permissions", [])],
                    load_time=plugin_status.get("load_time"),
                    **tool_info,
                    **security_info
                )
                
                plugins.append(plugin_info)
            
            filtered_count = len(plugins)
            
            # Apply pagination
            if limit:
                plugins = plugins[offset:offset + limit]
            
            # Get system status
            if self.integration_manager:
                system_status = self.integration_manager.get_integration_status()
            else:
                system_status = {"plugin_manager_available": True}
            
            return PluginListResponse(
                plugins=plugins,
                total_count=total_count,
                filtered_count=filtered_count,
                system_status=system_status
            )
            
        except Exception as e:
            self.logger.error(f"Plugin listing failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def _get_plugin_status(self, plugin_id: str) -> PluginStatusResponse:
        """Handle plugin status retrieval."""
        if not self.initialized:
            raise HTTPException(status_code=503, detail="Plugin system not initialized")
        
        try:
            status = self.plugin_manager.get_plugin_status(plugin_id)
            
            if not status or status.get("error"):
                raise HTTPException(status_code=404, detail=f"Plugin '{plugin_id}' not found")
            
            # Get additional information
            security_info = None
            tool_info = None
            
            if hasattr(self.plugin_manager.loader, "security_manager") and self.plugin_manager.loader.security_manager:
                security_status = self.plugin_manager.loader.security_manager.get_security_status(plugin_id)
                if not security_status.get("error"):
                    security_info = security_status
            
            if self.plugin_manager.tool_bridge:
                tool_status = self.plugin_manager.get_plugin_tool_status(plugin_id)
                tool_info = tool_status
            
            return PluginStatusResponse(
                plugin_id=plugin_id,
                status=status,
                security_info=security_info,
                tool_info=tool_info
            )
            
        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(f"Plugin status retrieval failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def _discover_plugins(self, request: PluginDiscoveryRequest) -> PluginDiscoveryResponse:
        """Handle plugin discovery."""
        if not self.initialized:
            raise HTTPException(status_code=503, detail="Plugin system not initialized")
        
        try:
            # Use integration manager if available for full integration
            if self.integration_manager:
                result = self.integration_manager.discover_and_load_plugins()
            else:
                result = self.plugin_manager.loader.discover_and_load_all_plugins()
            
            success = result.get("success", False)
            discovered_count = result.get("discovered_count", 0)
            loaded_count = result.get("loaded_count", 0)
            failed_count = result.get("failed_count", 0)
            
            # Count activations if they occurred
            activated_count = 0
            if "activation_results" in result:
                activated_count = sum(1 for success in result["activation_results"].values() if success)
            
            message = f"Discovery complete. Loaded {loaded_count}/{discovered_count} plugins"
            if failed_count > 0:
                message += f", {failed_count} failed"
            
            return PluginDiscoveryResponse(
                success=success,
                message=message,
                discovered_count=discovered_count,
                loaded_count=loaded_count,
                activated_count=activated_count,
                failed_count=failed_count,
                results=result
            )
            
        except Exception as e:
            self.logger.error(f"Plugin discovery failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def _execute_plugin_action(self, request: PluginActionRequest) -> PluginActionResponse:
        """Handle plugin action execution."""
        if not self.initialized:
            raise HTTPException(status_code=503, detail="Plugin system not initialized")
        
        try:
            action = request.action.lower()
            plugin_id = request.plugin_id
            result = None
            success = False
            message = ""
            
            if action == "activate":
                success = self.plugin_manager.activate_plugin(plugin_id)
                message = f"Plugin '{plugin_id}' {'activated' if success else 'activation failed'}"
                
            elif action == "deactivate":
                success = self.plugin_manager.deactivate_plugin(plugin_id)
                message = f"Plugin '{plugin_id}' {'deactivated' if success else 'deactivation failed'}"
                
            elif action == "unload":
                success = self.plugin_manager.unload_plugin(plugin_id)
                message = f"Plugin '{plugin_id}' {'unloaded' if success else 'unload failed'}"
                
            elif action == "register_tool":
                if self.plugin_manager.tool_bridge:
                    success = self.plugin_manager.register_plugin_as_tool(plugin_id)
                    message = f"Plugin '{plugin_id}' tool {'registered' if success else 'registration failed'}"
                else:
                    message = "Tool bridge not available"
                    
            elif action == "unregister_tool":
                if self.plugin_manager.tool_bridge:
                    success = self.plugin_manager.unregister_plugin_tool(plugin_id)
                    message = f"Plugin '{plugin_id}' tool {'unregistered' if success else 'unregistration failed'}"
                else:
                    success = True  # No bridge means nothing to unregister
                    message = "Tool bridge not available, no action needed"
                    
            else:
                raise HTTPException(status_code=400, detail=f"Unknown action: {action}")
            
            return PluginActionResponse(
                success=success,
                message=message,
                plugin_id=plugin_id,
                action=action,
                result=result
            )
            
        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(f"Plugin action execution failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def _get_system_health(self) -> SystemHealthResponse:
        """Handle system health retrieval."""
        if not self.initialized:
            raise HTTPException(status_code=503, detail="Plugin system not initialized")
        
        try:
            health = self.plugin_manager.get_system_health()
            
            # Get integration status if available
            integrations = {}
            if self.integration_manager:
                integration_status = self.integration_manager.get_integration_status()
                integrations = {
                    "active_integrations": integration_status.get("active_integrations", []),
                    "components": integration_status.get("components", {})
                }
            
            # Get additional statistics
            statistics = {}
            if self.plugin_manager.tool_bridge:
                statistics["tool_bridge"] = self.plugin_manager.get_tool_bridge_statistics()
            
            if hasattr(self.plugin_manager.loader, "security_manager") and self.plugin_manager.loader.security_manager:
                statistics["security"] = self.plugin_manager.loader.security_manager.get_security_stats()
            
            return SystemHealthResponse(
                overall_status=health.get("status", "unknown"),
                plugin_system=health,
                integrations=integrations,
                component_health=health.get("component_health", {}),
                statistics=statistics
            )
            
        except Exception as e:
            self.logger.error(f"System health retrieval failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def _get_security_status(self) -> SecurityStatusResponse:
        """Handle security status retrieval."""
        if not self.initialized:
            raise HTTPException(status_code=503, detail="Plugin system not initialized")
        
        try:
            # Get security manager status
            security_enabled = False
            sandboxing_enabled = False
            stats = {}
            sandbox_stats = {}
            recent_violations = []
            
            if hasattr(self.plugin_manager.loader, "security_manager") and self.plugin_manager.loader.security_manager:
                security_enabled = True
                stats = self.plugin_manager.loader.security_manager.get_security_stats()
            
            if hasattr(self.plugin_manager.loader, "sandbox_controller") and self.plugin_manager.loader.sandbox_controller:
                sandboxing_enabled = True
                sandbox_stats = self.plugin_manager.loader.sandbox_controller.get_sandbox_status()
            
            return SecurityStatusResponse(
                security_enabled=security_enabled,
                sandboxing_enabled=sandboxing_enabled,
                total_secured_plugins=stats.get("total_plugins_secured", 0),
                active_contexts=stats.get("active_security_contexts", 0),
                violations_count=stats.get("violations_detected", 0),
                sandbox_statistics=sandbox_stats,
                recent_violations=recent_violations
            )
            
        except Exception as e:
            self.logger.error(f"Security status retrieval failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def _get_plugin_tools(self):
        """Handle plugin tools listing."""
        if not self.initialized:
            raise HTTPException(status_code=503, detail="Plugin system not initialized")
        
        try:
            if not self.plugin_manager.tool_bridge:
                return {
                    "tool_bridge_available": False,
                    "message": "Tool bridge not available"
                }
            
            status = self.plugin_manager.get_plugin_tool_status()
            statistics = self.plugin_manager.get_tool_bridge_statistics()
            
            return {
                "tool_bridge_available": True,
                "plugin_tools": status,
                "statistics": statistics
            }
            
        except Exception as e:
            self.logger.error(f"Plugin tools listing failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def _register_plugin_tools(self, plugin_id: Optional[str]):
        """Handle plugin tool registration."""
        if not self.initialized:
            raise HTTPException(status_code=503, detail="Plugin system not initialized")
        
        try:
            if not self.plugin_manager.tool_bridge:
                raise HTTPException(status_code=503, detail="Tool bridge not available")
            
            if plugin_id:
                success = self.plugin_manager.register_plugin_as_tool(plugin_id)
                return {
                    "success": success,
                    "message": f"Plugin '{plugin_id}' tool {'registered' if success else 'registration failed'}",
                    "plugin_id": plugin_id
                }
            else:
                results = self.plugin_manager.register_all_plugin_tools()
                successful = sum(1 for success in results.values() if success)
                return {
                    "success": True,
                    "message": f"Registered {successful}/{len(results)} plugin tools",
                    "results": results
                }
            
        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(f"Plugin tool registration failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def _unregister_plugin_tools(self, plugin_id: Optional[str]):
        """Handle plugin tool unregistration."""
        if not self.initialized:
            raise HTTPException(status_code=503, detail="Plugin system not initialized")
        
        try:
            if not self.plugin_manager.tool_bridge:
                return {
                    "success": True,
                    "message": "Tool bridge not available, no action needed"
                }
            
            if plugin_id:
                success = self.plugin_manager.unregister_plugin_tool(plugin_id)
                return {
                    "success": success,
                    "message": f"Plugin '{plugin_id}' tool {'unregistered' if success else 'unregistration failed'}",
                    "plugin_id": plugin_id
                }
            else:
                results = self.plugin_manager.tool_bridge.unregister_all_plugin_tools()
                successful = sum(1 for success in results.values() if success)
                return {
                    "success": True,
                    "message": f"Unregistered {successful}/{len(results)} plugin tools",
                    "results": results
                }
            
        except Exception as e:
            self.logger.error(f"Plugin tool unregistration failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    def get_router(self) -> APIRouter:
        """Get the FastAPI router for plugin endpoints."""
        return self.router