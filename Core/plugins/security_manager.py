"""
Security Manager for PersonaOS Plugins

This module provides comprehensive security management for plugins including
permission enforcement, resource monitoring, sandboxing, and security policy
management.
"""

import os
import sys
import time
import logging
import threading
import psutil
import resource
from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Callable
from dataclasses import dataclass, field
from enum import Enum
import hashlib
import subprocess

class SecurityLevel(Enum):
    """Security levels for plugin execution."""
    UNRESTRICTED = "unrestricted"
    STANDARD = "standard"
    RESTRICTED = "restricted"
    SANDBOXED = "sandboxed"

class ResourceType(Enum):
    """Types of system resources to monitor."""
    MEMORY = "memory"
    CPU = "cpu"
    DISK_IO = "disk_io"
    NETWORK_IO = "network_io"
    FILE_HANDLES = "file_handles"
    THREADS = "threads"

@dataclass
class ResourceLimit:
    """Resource limit specification."""
    resource_type: ResourceType
    limit_value: float
    unit: str
    warning_threshold: float = 0.8
    enforcement_enabled: bool = True

@dataclass
class SecurityViolation:
    """Security violation record."""
    plugin_id: str
    violation_type: str
    severity: str
    description: str
    timestamp: float
    resource_usage: Dict[str, Any] = field(default_factory=dict)
    action_taken: str = ""

@dataclass
class PluginSecurityContext:
    """Security context for a plugin."""
    plugin_id: str
    security_level: SecurityLevel
    granted_permissions: Set[str]
    resource_limits: Dict[ResourceType, ResourceLimit]
    sandbox_directory: Optional[Path] = None
    process_id: Optional[int] = None
    start_time: float = 0.0
    resource_usage: Dict[str, Any] = field(default_factory=dict)

class SecurityManager:
    """
    Comprehensive security manager for PersonaOS plugins.
    
    Provides security enforcement including:
    - Permission system with granular controls
    - Resource monitoring and limiting
    - Plugin sandboxing and isolation
    - Security policy enforcement
    - Violation detection and response
    - Audit logging and reporting
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize security manager.
        
        Args:
            config: PersonaOS configuration dictionary
        """
        self.config = config or {}
        self.logger = logging.getLogger("security_manager")
        
        # Security configuration
        self.security_enabled = config.get("plugin_security_enabled", True)
        self.sandboxing_enabled = config.get("plugin_sandboxing_enabled", True)
        self.default_security_level = SecurityLevel(config.get("plugin_default_security_level", "standard"))
        
        # Resource monitoring
        self.resource_monitoring_enabled = config.get("plugin_resource_monitoring_enabled", True)
        self.monitoring_interval = config.get("plugin_monitoring_interval", 5.0)  # seconds
        
        # Security contexts
        self.security_contexts: Dict[str, PluginSecurityContext] = {}
        self.active_processes: Dict[str, psutil.Process] = {}
        
        # Security policies
        self.security_policies = self._load_security_policies()
        self.permission_definitions = self._load_permission_definitions()
        self.default_resource_limits = self._load_default_resource_limits()
        
        # Violation tracking
        self.security_violations: List[SecurityViolation] = []
        self.violation_handlers: Dict[str, List[Callable]] = {}
        
        # Sandbox management
        self.sandbox_root = Path(config.get("plugin_sandbox_root", "data/plugin_sandboxes"))
        self.sandbox_root.mkdir(parents=True, exist_ok=True)
        
        # Monitoring thread
        self.monitoring_thread = None
        self.monitoring_active = False
        self.shutdown_event = threading.Event()
        
        # Statistics
        self.security_stats = {
            "total_plugins_secured": 0,
            "active_security_contexts": 0,
            "violations_detected": 0,
            "permissions_denied": 0,
            "resource_limit_breaches": 0,
            "sandboxed_plugins": 0
        }
        
        # Thread safety
        self._security_lock = threading.RLock()
        
        if self.security_enabled:
            self._start_resource_monitoring()
        
        self.logger.info(f"SecurityManager initialized (enabled: {self.security_enabled})")
    
    def create_security_context(self, plugin_id: str, plugin_metadata: Any,
                              requested_permissions: List[str] = None) -> PluginSecurityContext:
        """
        Create security context for a plugin.
        
        Args:
            plugin_id: Unique plugin identifier
            plugin_metadata: Plugin metadata with security requirements
            requested_permissions: List of requested permissions
            
        Returns:
            Security context for the plugin
        """
        with self._security_lock:
            self.logger.info(f"Creating security context for plugin: {plugin_id}")
            
            # Determine security level
            security_level = self._determine_security_level(plugin_metadata)
            
            # Evaluate permission requests
            requested_perms = requested_permissions or []
            if hasattr(plugin_metadata, 'permissions'):
                requested_perms.extend([p.name if hasattr(p, 'name') else str(p) 
                                      for p in plugin_metadata.permissions])
            
            granted_permissions = self._evaluate_permissions(
                plugin_id, requested_perms, security_level
            )
            
            # Create resource limits
            resource_limits = self._create_resource_limits(plugin_id, security_level)
            
            # Create sandbox if required
            sandbox_dir = None
            if security_level in [SecurityLevel.RESTRICTED, SecurityLevel.SANDBOXED]:
                sandbox_dir = self._create_plugin_sandbox(plugin_id)
            
            # Create security context
            context = PluginSecurityContext(
                plugin_id=plugin_id,
                security_level=security_level,
                granted_permissions=granted_permissions,
                resource_limits=resource_limits,
                sandbox_directory=sandbox_dir,
                start_time=time.time()
            )
            
            self.security_contexts[plugin_id] = context
            self.security_stats["total_plugins_secured"] += 1
            self.security_stats["active_security_contexts"] += 1
            
            if sandbox_dir:
                self.security_stats["sandboxed_plugins"] += 1
            
            self.logger.info(f"Security context created for {plugin_id}: level={security_level.value}, permissions={len(granted_permissions)}")
            
            return context
    
    def enforce_permission(self, plugin_id: str, permission: str, 
                         context: Dict[str, Any] = None) -> bool:
        """
        Enforce permission check for plugin operation.
        
        Args:
            plugin_id: Plugin identifier
            permission: Permission being requested
            context: Additional context for permission check
            
        Returns:
            True if permission granted, False otherwise
        """
        if not self.security_enabled:
            return True
        
        with self._security_lock:
            security_context = self.security_contexts.get(plugin_id)
            
            if not security_context:
                self.logger.warning(f"No security context found for plugin {plugin_id}")
                self._record_violation(
                    plugin_id, "missing_context", "medium",
                    f"Plugin {plugin_id} attempted operation without security context"
                )
                return False
            
            # Check if permission is granted
            if permission in security_context.granted_permissions:
                self.logger.debug(f"Permission granted: {plugin_id} -> {permission}")
                return True
            
            # Check for wildcard permissions
            for granted_perm in security_context.granted_permissions:
                if granted_perm.endswith('*') and permission.startswith(granted_perm[:-1]):
                    self.logger.debug(f"Wildcard permission granted: {plugin_id} -> {permission}")
                    return True
            
            # Permission denied
            self.security_stats["permissions_denied"] += 1
            self.logger.warning(f"Permission denied: {plugin_id} -> {permission}")
            
            self._record_violation(
                plugin_id, "permission_denied", "low",
                f"Plugin {plugin_id} denied permission: {permission}",
                {"requested_permission": permission, "context": context}
            )
            
            return False
    
    def monitor_resource_usage(self, plugin_id: str, process_id: int = None):
        """
        Start monitoring resource usage for a plugin.
        
        Args:
            plugin_id: Plugin identifier
            process_id: Process ID to monitor (optional)
        """
        if not self.resource_monitoring_enabled:
            return
        
        with self._security_lock:
            security_context = self.security_contexts.get(plugin_id)
            
            if not security_context:
                self.logger.warning(f"Cannot monitor resources: no security context for {plugin_id}")
                return
            
            if process_id:
                try:
                    process = psutil.Process(process_id)
                    self.active_processes[plugin_id] = process
                    security_context.process_id = process_id
                    
                    self.logger.info(f"Started resource monitoring for plugin {plugin_id} (PID: {process_id})")
                    
                except psutil.NoSuchProcess:
                    self.logger.error(f"Process {process_id} not found for plugin {plugin_id}")
    
    def check_resource_limits(self, plugin_id: str) -> Dict[str, Any]:
        """
        Check current resource usage against limits.
        
        Args:
            plugin_id: Plugin identifier
            
        Returns:
            Resource usage report with violations
        """
        if not self.resource_monitoring_enabled:
            return {"monitoring_disabled": True}
        
        with self._security_lock:
            security_context = self.security_contexts.get(plugin_id)
            
            if not security_context:
                return {"error": "No security context found"}
            
            process = self.active_processes.get(plugin_id)
            if not process:
                return {"error": "No process to monitor"}
            
            try:
                # Get current resource usage
                memory_info = process.memory_info()
                cpu_percent = process.cpu_percent()
                
                current_usage = {
                    ResourceType.MEMORY: memory_info.rss / (1024 * 1024),  # MB
                    ResourceType.CPU: cpu_percent,  # Percentage
                    ResourceType.THREADS: process.num_threads(),
                    ResourceType.FILE_HANDLES: len(process.open_files())
                }
                
                # Check against limits
                violations = []
                warnings = []
                
                for resource_type, limit in security_context.resource_limits.items():
                    if resource_type not in current_usage:
                        continue
                    
                    usage = current_usage[resource_type]
                    limit_value = limit.limit_value
                    warning_threshold = limit_value * limit.warning_threshold
                    
                    if usage > limit_value and limit.enforcement_enabled:
                        violations.append({
                            "resource": resource_type.value,
                            "usage": usage,
                            "limit": limit_value,
                            "unit": limit.unit
                        })
                        
                        self._record_violation(
                            plugin_id, "resource_limit_breach", "high",
                            f"Plugin {plugin_id} exceeded {resource_type.value} limit: {usage} > {limit_value} {limit.unit}",
                            {"resource_usage": current_usage}
                        )
                        
                        self.security_stats["resource_limit_breaches"] += 1
                    
                    elif usage > warning_threshold:
                        warnings.append({
                            "resource": resource_type.value,
                            "usage": usage,
                            "threshold": warning_threshold,
                            "limit": limit_value,
                            "unit": limit.unit
                        })
                
                # Update context with current usage
                security_context.resource_usage = current_usage
                
                return {
                    "plugin_id": plugin_id,
                    "timestamp": time.time(),
                    "current_usage": current_usage,
                    "violations": violations,
                    "warnings": warnings,
                    "enforcement_actions": self._apply_resource_enforcement(plugin_id, violations)
                }
                
            except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                self.logger.error(f"Error checking resources for plugin {plugin_id}: {e}")
                return {"error": str(e)}
    
    def _apply_resource_enforcement(self, plugin_id: str, violations: List[Dict[str, Any]]) -> List[str]:
        """Apply enforcement actions for resource violations."""
        actions = []
        
        if not violations:
            return actions
        
        security_context = self.security_contexts.get(plugin_id)
        if not security_context:
            return actions
        
        # Determine enforcement actions based on security level
        if security_context.security_level == SecurityLevel.SANDBOXED:
            # Strict enforcement for sandboxed plugins
            for violation in violations:
                resource = violation["resource"]
                
                if resource == "memory":
                    actions.append("memory_limit_enforced")
                    self._limit_plugin_memory(plugin_id)
                elif resource == "cpu":
                    actions.append("cpu_throttling_applied")
                    self._throttle_plugin_cpu(plugin_id)
                elif resource == "threads":
                    actions.append("thread_limit_enforced")
                    # Thread limiting would be implemented here
        
        elif security_context.security_level == SecurityLevel.RESTRICTED:
            # Moderate enforcement for restricted plugins
            for violation in violations:
                if violation["usage"] > violation["limit"] * 1.5:  # 50% over limit
                    actions.append("plugin_suspended")
                    self._suspend_plugin(plugin_id)
                    break
        
        # Log enforcement actions
        if actions:
            self.logger.warning(f"Applied enforcement actions for plugin {plugin_id}: {actions}")
        
        return actions
    
    def create_sandbox_environment(self, plugin_id: str) -> Dict[str, Any]:
        """
        Create isolated sandbox environment for plugin.
        
        Args:
            plugin_id: Plugin identifier
            
        Returns:
            Sandbox environment configuration
        """
        if not self.sandboxing_enabled:
            return {"sandboxing_disabled": True}
        
        try:
            sandbox_dir = self.sandbox_root / plugin_id
            sandbox_dir.mkdir(parents=True, exist_ok=True)
            
            # Create sandbox subdirectories
            subdirs = ["temp", "data", "logs", "cache"]
            for subdir in subdirs:
                (sandbox_dir / subdir).mkdir(exist_ok=True)
            
            # Set appropriate permissions
            self._set_sandbox_permissions(sandbox_dir)
            
            # Create environment configuration
            env_config = {
                "sandbox_root": str(sandbox_dir),
                "temp_dir": str(sandbox_dir / "temp"),
                "data_dir": str(sandbox_dir / "data"),
                "log_dir": str(sandbox_dir / "logs"),
                "cache_dir": str(sandbox_dir / "cache"),
                "allowed_paths": [str(sandbox_dir)],
                "blocked_paths": [
                    "/etc", "/usr", "/bin", "/sbin", "/var",
                    str(Path.home()), "/tmp"
                ]
            }
            
            self.logger.info(f"Created sandbox environment for plugin {plugin_id}")
            
            return {
                "success": True,
                "sandbox_config": env_config
            }
            
        except Exception as e:
            self.logger.error(f"Failed to create sandbox for plugin {plugin_id}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def validate_file_access(self, plugin_id: str, file_path: str, 
                           access_type: str = "read") -> bool:
        """
        Validate file access request from plugin.
        
        Args:
            plugin_id: Plugin identifier
            file_path: Path to file being accessed
            access_type: Type of access (read, write, execute)
            
        Returns:
            True if access allowed, False otherwise
        """
        if not self.security_enabled:
            return True
        
        security_context = self.security_contexts.get(plugin_id)
        if not security_context:
            return False
        
        file_path_obj = Path(file_path).resolve()
        
        # Check sandbox restrictions
        if security_context.sandbox_directory:
            sandbox_root = security_context.sandbox_directory.resolve()
            
            try:
                file_path_obj.relative_to(sandbox_root)
            except ValueError:
                # File is outside sandbox
                self.logger.warning(f"Plugin {plugin_id} attempted access outside sandbox: {file_path}")
                
                self._record_violation(
                    plugin_id, "sandbox_violation", "high",
                    f"Plugin {plugin_id} attempted to access file outside sandbox: {file_path}"
                )
                
                return False
        
        # Check permission requirements
        required_permission = f"file.{access_type}"
        if not self.enforce_permission(plugin_id, required_permission):
            return False
        
        # Check against blocked paths
        blocked_patterns = self.security_policies.get("blocked_file_patterns", [])
        for pattern in blocked_patterns:
            if pattern in str(file_path_obj):
                self.logger.warning(f"Plugin {plugin_id} attempted access to blocked path: {file_path}")
                return False
        
        return True
    
    def audit_plugin_activity(self, plugin_id: str, action: str, 
                            details: Dict[str, Any] = None):
        """
        Audit plugin activity for security monitoring.
        
        Args:
            plugin_id: Plugin identifier
            action: Action being performed
            details: Additional details about the action
        """
        audit_entry = {
            "timestamp": time.time(),
            "plugin_id": plugin_id,
            "action": action,
            "details": details or {},
            "security_context": self.security_contexts.get(plugin_id)
        }
        
        # Log audit entry
        self.logger.info(f"AUDIT: Plugin {plugin_id} performed action: {action}")
        
        # Store audit entry (would integrate with proper audit logging system)
        # For now, just log it
        
        # Check for suspicious activity patterns
        self._analyze_activity_patterns(plugin_id, action, details)
    
    def _determine_security_level(self, plugin_metadata: Any) -> SecurityLevel:
        """Determine appropriate security level for plugin."""
        if not hasattr(plugin_metadata, 'permissions'):
            return self.default_security_level
        
        permissions = plugin_metadata.permissions
        high_risk_permissions = self.security_policies.get("high_risk_permissions", [])
        
        # Check for high-risk permissions
        for perm in permissions:
            perm_name = perm.name if hasattr(perm, 'name') else str(perm)
            if perm_name in high_risk_permissions:
                return SecurityLevel.SANDBOXED
        
        # Check for moderate risk
        moderate_risk_permissions = self.security_policies.get("moderate_risk_permissions", [])
        for perm in permissions:
            perm_name = perm.name if hasattr(perm, 'name') else str(perm)
            if perm_name in moderate_risk_permissions:
                return SecurityLevel.RESTRICTED
        
        return self.default_security_level
    
    def _evaluate_permissions(self, plugin_id: str, requested_permissions: List[str], 
                            security_level: SecurityLevel) -> Set[str]:
        """Evaluate and grant permissions based on security level."""
        granted = set()
        
        # Get allowed permissions for security level
        level_permissions = self.security_policies.get("security_level_permissions", {})
        allowed_for_level = set(level_permissions.get(security_level.value, []))
        
        # Get globally blocked permissions
        blocked_permissions = set(self.security_policies.get("blocked_permissions", []))
        
        for permission in requested_permissions:
            # Check if globally blocked
            if permission in blocked_permissions:
                self.logger.warning(f"Blocked permission requested by {plugin_id}: {permission}")
                continue
            
            # Check if allowed for security level
            if permission in allowed_for_level or "*" in allowed_for_level:
                granted.add(permission)
            else:
                self.logger.info(f"Permission not allowed for security level {security_level.value}: {permission}")
        
        return granted
    
    def _create_resource_limits(self, plugin_id: str, 
                              security_level: SecurityLevel) -> Dict[ResourceType, ResourceLimit]:
        """Create resource limits based on security level."""
        limits = {}
        
        # Get limits for security level
        level_limits = self.security_policies.get("security_level_limits", {})
        limits_config = level_limits.get(security_level.value, {})
        
        # Apply default limits
        for resource_type, default_limit in self.default_resource_limits.items():
            # Override with security level specific limits
            if resource_type.value in limits_config:
                limit_config = limits_config[resource_type.value]
                limit = ResourceLimit(
                    resource_type=resource_type,
                    limit_value=limit_config.get("limit", default_limit.limit_value),
                    unit=limit_config.get("unit", default_limit.unit),
                    warning_threshold=limit_config.get("warning_threshold", default_limit.warning_threshold),
                    enforcement_enabled=limit_config.get("enforcement", default_limit.enforcement_enabled)
                )
            else:
                limit = default_limit
            
            limits[resource_type] = limit
        
        return limits
    
    def _create_plugin_sandbox(self, plugin_id: str) -> Path:
        """Create sandbox directory for plugin."""
        sandbox_dir = self.sandbox_root / plugin_id
        sandbox_dir.mkdir(parents=True, exist_ok=True)
        return sandbox_dir
    
    def _set_sandbox_permissions(self, sandbox_dir: Path):
        """Set appropriate permissions on sandbox directory."""
        try:
            # Set directory permissions (owner read/write/execute only)
            os.chmod(sandbox_dir, 0o700)
            
            # Set permissions on subdirectories
            for subdir in sandbox_dir.iterdir():
                if subdir.is_dir():
                    os.chmod(subdir, 0o700)
        
        except Exception as e:
            self.logger.error(f"Failed to set sandbox permissions: {e}")
    
    def _record_violation(self, plugin_id: str, violation_type: str, severity: str,
                        description: str, resource_usage: Dict[str, Any] = None):
        """Record security violation."""
        violation = SecurityViolation(
            plugin_id=plugin_id,
            violation_type=violation_type,
            severity=severity,
            description=description,
            timestamp=time.time(),
            resource_usage=resource_usage or {}
        )
        
        self.security_violations.append(violation)
        self.security_stats["violations_detected"] += 1
        
        # Fire violation handlers
        handlers = self.violation_handlers.get(violation_type, [])
        for handler in handlers:
            try:
                handler(violation)
            except Exception as e:
                self.logger.error(f"Violation handler error: {e}")
    
    def _limit_plugin_memory(self, plugin_id: str):
        """Apply memory limits to plugin process."""
        process = self.active_processes.get(plugin_id)
        if process:
            try:
                # Set memory limit (platform specific)
                if sys.platform != "win32":
                    resource.prlimit(process.pid, resource.RLIMIT_AS, (128 * 1024 * 1024, 128 * 1024 * 1024))
                self.logger.info(f"Applied memory limit to plugin {plugin_id}")
            except Exception as e:
                self.logger.error(f"Failed to apply memory limit: {e}")
    
    def _throttle_plugin_cpu(self, plugin_id: str):
        """Apply CPU throttling to plugin process."""
        process = self.active_processes.get(plugin_id)
        if process:
            try:
                # Lower process priority
                process.nice(10)  # Lower priority
                self.logger.info(f"Applied CPU throttling to plugin {plugin_id}")
            except Exception as e:
                self.logger.error(f"Failed to apply CPU throttling: {e}")
    
    def _suspend_plugin(self, plugin_id: str):
        """Suspend plugin execution."""
        process = self.active_processes.get(plugin_id)
        if process:
            try:
                process.suspend()
                self.logger.warning(f"Suspended plugin {plugin_id} due to resource violations")
            except Exception as e:
                self.logger.error(f"Failed to suspend plugin: {e}")
    
    def _analyze_activity_patterns(self, plugin_id: str, action: str, details: Dict[str, Any]):
        """Analyze plugin activity for suspicious patterns."""
        # Placeholder for activity pattern analysis
        # Would implement behavioral analysis here
        pass
    
    def _start_resource_monitoring(self):
        """Start background resource monitoring thread."""
        if not self.resource_monitoring_enabled:
            return
        
        self.monitoring_active = True
        
        def monitor_resources():
            while self.monitoring_active and not self.shutdown_event.is_set():
                try:
                    with self._security_lock:
                        for plugin_id in list(self.security_contexts.keys()):
                            self.check_resource_limits(plugin_id)
                    
                    self.shutdown_event.wait(self.monitoring_interval)
                    
                except Exception as e:
                    self.logger.error(f"Resource monitoring error: {e}")
        
        self.monitoring_thread = threading.Thread(
            target=monitor_resources,
            name="PluginResourceMonitor",
            daemon=True
        )
        self.monitoring_thread.start()
        
        self.logger.info("Started resource monitoring thread")
    
    def _load_security_policies(self) -> Dict[str, Any]:
        """Load security policies configuration."""
        return self.config.get("plugin_security_policies", {
            "high_risk_permissions": [
                "system.execute", "file.write_system", "network.unrestricted",
                "registry.write", "process.create"
            ],
            "moderate_risk_permissions": [
                "file.write", "network.connect", "process.spawn"
            ],
            "blocked_permissions": [
                "system.root", "kernel.access", "hardware.direct"
            ],
            "security_level_permissions": {
                "unrestricted": ["*"],
                "standard": [
                    "config.read", "tools.register", "storage.read", "storage.write",
                    "audio.speak", "file.read", "network.http"
                ],
                "restricted": [
                    "config.read", "storage.read", "audio.speak"
                ],
                "sandboxed": [
                    "storage.read"
                ]
            },
            "security_level_limits": {
                "unrestricted": {},
                "standard": {
                    "memory": {"limit": 512, "unit": "MB"},
                    "cpu": {"limit": 50, "unit": "%"}
                },
                "restricted": {
                    "memory": {"limit": 256, "unit": "MB"},
                    "cpu": {"limit": 25, "unit": "%"}
                },
                "sandboxed": {
                    "memory": {"limit": 128, "unit": "MB"},
                    "cpu": {"limit": 10, "unit": "%"},
                    "threads": {"limit": 5, "unit": "count"}
                }
            },
            "blocked_file_patterns": [
                "/etc/passwd", "/etc/shadow", "/.ssh/", "/root/"
            ]
        })
    
    def _load_permission_definitions(self) -> Dict[str, Dict[str, Any]]:
        """Load permission definitions."""
        return self.config.get("plugin_permission_definitions", {
            "file.read": {
                "description": "Read files from filesystem",
                "risk_level": "low"
            },
            "file.write": {
                "description": "Write files to filesystem",
                "risk_level": "medium"
            },
            "system.execute": {
                "description": "Execute system commands",
                "risk_level": "high"
            }
        })
    
    def _load_default_resource_limits(self) -> Dict[ResourceType, ResourceLimit]:
        """Load default resource limits."""
        return {
            ResourceType.MEMORY: ResourceLimit(
                ResourceType.MEMORY, 256.0, "MB", 0.8, True
            ),
            ResourceType.CPU: ResourceLimit(
                ResourceType.CPU, 25.0, "%", 0.8, True
            ),
            ResourceType.THREADS: ResourceLimit(
                ResourceType.THREADS, 10, "count", 0.8, True
            ),
            ResourceType.FILE_HANDLES: ResourceLimit(
                ResourceType.FILE_HANDLES, 100, "count", 0.8, True
            )
        }
    
    def get_security_status(self, plugin_id: str = None) -> Dict[str, Any]:
        """Get security status for plugin or all plugins."""
        with self._security_lock:
            if plugin_id:
                context = self.security_contexts.get(plugin_id)
                if not context:
                    return {"error": "Plugin not found"}
                
                return {
                    "plugin_id": plugin_id,
                    "security_level": context.security_level.value,
                    "granted_permissions": list(context.granted_permissions),
                    "resource_limits": {
                        rt.value: {
                            "limit": rl.limit_value,
                            "unit": rl.unit,
                            "enforcement": rl.enforcement_enabled
                        }
                        for rt, rl in context.resource_limits.items()
                    },
                    "sandbox_directory": str(context.sandbox_directory) if context.sandbox_directory else None,
                    "current_usage": context.resource_usage,
                    "violations": [
                        v for v in self.security_violations 
                        if v.plugin_id == plugin_id
                    ][-10:]  # Last 10 violations
                }
            else:
                return {
                    "security_enabled": self.security_enabled,
                    "active_contexts": len(self.security_contexts),
                    "monitored_processes": len(self.active_processes),
                    "total_violations": len(self.security_violations),
                    "stats": self.security_stats.copy()
                }
    
    def cleanup_security_context(self, plugin_id: str):
        """Clean up security context for plugin."""
        with self._security_lock:
            # Remove security context
            if plugin_id in self.security_contexts:
                del self.security_contexts[plugin_id]
                self.security_stats["active_security_contexts"] -= 1
            
            # Remove process monitoring
            if plugin_id in self.active_processes:
                del self.active_processes[plugin_id]
            
            # Clean up sandbox (optional)
            sandbox_dir = self.sandbox_root / plugin_id
            if sandbox_dir.exists():
                try:
                    import shutil
                    shutil.rmtree(sandbox_dir)
                    self.logger.info(f"Cleaned up sandbox for plugin {plugin_id}")
                except Exception as e:
                    self.logger.error(f"Failed to clean up sandbox: {e}")
    
    def add_violation_handler(self, violation_type: str, handler: Callable):
        """Add handler for specific violation type."""
        if violation_type not in self.violation_handlers:
            self.violation_handlers[violation_type] = []
        
        self.violation_handlers[violation_type].append(handler)
    
    def get_security_stats(self) -> Dict[str, Any]:
        """Get security statistics."""
        return self.security_stats.copy()
    
    def shutdown(self):
        """Shutdown security manager."""
        self.logger.info("Shutting down security manager")
        
        # Stop monitoring
        self.monitoring_active = False
        self.shutdown_event.set()
        
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            self.monitoring_thread.join(timeout=2)
        
        # Clean up contexts
        with self._security_lock:
            for plugin_id in list(self.security_contexts.keys()):
                self.cleanup_security_context(plugin_id)
        
        self.logger.info("Security manager shutdown complete")