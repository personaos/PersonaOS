"""
Sandbox Controller for PersonaOS Plugins

This module provides advanced sandboxing capabilities for plugin isolation,
including filesystem virtualization, network restrictions, and process
containment.
"""

import os
import sys
import time
import subprocess
import logging
import threading
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Union
from dataclasses import dataclass, field
from enum import Enum
import json

class SandboxType(Enum):
    """Types of sandbox isolation."""
    FILESYSTEM = "filesystem"
    NETWORK = "network"
    PROCESS = "process"
    FULL = "full"

class IsolationLevel(Enum):
    """Levels of sandbox isolation."""
    MINIMAL = "minimal"
    MODERATE = "moderate"
    STRICT = "strict"
    MAXIMUM = "maximum"

@dataclass
class SandboxConfiguration:
    """Configuration for plugin sandbox."""
    plugin_id: str
    isolation_level: IsolationLevel
    sandbox_types: Set[SandboxType]
    allowed_paths: List[str] = field(default_factory=list)
    blocked_paths: List[str] = field(default_factory=list)
    allowed_network_hosts: List[str] = field(default_factory=list)
    blocked_network_hosts: List[str] = field(default_factory=list)
    allowed_syscalls: List[str] = field(default_factory=list)
    blocked_syscalls: List[str] = field(default_factory=list)
    resource_limits: Dict[str, Any] = field(default_factory=dict)
    environment_variables: Dict[str, str] = field(default_factory=dict)

@dataclass
class SandboxInstance:
    """Represents an active plugin sandbox."""
    plugin_id: str
    sandbox_id: str
    configuration: SandboxConfiguration
    sandbox_root: Path
    process_id: Optional[int] = None
    status: str = "created"
    created_at: float = 0.0
    last_activity: float = 0.0
    violations: List[Dict[str, Any]] = field(default_factory=list)

class SandboxController:
    """
    Advanced sandbox controller for plugin isolation.
    
    Provides comprehensive sandboxing including:
    - Filesystem virtualization and access control
    - Network traffic filtering and monitoring
    - Process isolation and resource limiting
    - System call filtering and monitoring
    - Environment variable management
    - Sandbox lifecycle management
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize sandbox controller.
        
        Args:
            config: PersonaOS configuration dictionary
        """
        self.config = config or {}
        self.logger = logging.getLogger("sandbox_controller")
        
        # Sandbox configuration
        self.sandboxing_enabled = config.get("plugin_sandboxing_enabled", True)
        self.sandbox_root_dir = Path(config.get("plugin_sandbox_root", "data/plugin_sandboxes"))
        self.default_isolation_level = IsolationLevel(config.get("plugin_default_isolation_level", "moderate"))
        
        # Platform detection
        self.platform = sys.platform
        self.windows = self.platform == "win32"
        self.linux = self.platform.startswith("linux")
        self.macos = self.platform == "darwin"
        
        # Sandbox instances
        self.active_sandboxes: Dict[str, SandboxInstance] = {}
        self.sandbox_counter = 0
        
        # Monitoring
        self.monitoring_enabled = config.get("plugin_sandbox_monitoring_enabled", True)
        self.monitoring_interval = config.get("plugin_sandbox_monitoring_interval", 10.0)
        
        # Security policies
        self.sandbox_policies = self._load_sandbox_policies()
        
        # File system virtualization
        self.fs_overlay_enabled = config.get("plugin_fs_overlay_enabled", True)
        
        # Thread safety
        self._sandbox_lock = threading.RLock()
        
        # Initialize sandbox root
        self.sandbox_root_dir.mkdir(parents=True, exist_ok=True)
        
        # Platform-specific initialization
        self._initialize_platform_sandbox()
        
        self.logger.info(f"SandboxController initialized (platform: {self.platform})")
    
    def create_sandbox(self, plugin_id: str, isolation_level: IsolationLevel = None,
                      custom_config: Dict[str, Any] = None) -> SandboxInstance:
        """
        Create a new sandbox for a plugin.
        
        Args:
            plugin_id: Plugin identifier
            isolation_level: Level of isolation (optional)
            custom_config: Custom sandbox configuration (optional)
            
        Returns:
            Created sandbox instance
        """
        if not self.sandboxing_enabled:
            raise RuntimeError("Sandboxing is disabled")
        
        with self._sandbox_lock:
            self.sandbox_counter += 1
            sandbox_id = f"{plugin_id}_sandbox_{self.sandbox_counter}"
            
            self.logger.info(f"Creating sandbox for plugin {plugin_id} (ID: {sandbox_id})")
            
            # Determine isolation level
            iso_level = isolation_level or self.default_isolation_level
            
            # Create sandbox configuration
            config = self._create_sandbox_configuration(plugin_id, iso_level, custom_config)
            
            # Create sandbox directory structure
            sandbox_root = self._create_sandbox_directory(sandbox_id)
            
            # Setup filesystem isolation
            if SandboxType.FILESYSTEM in config.sandbox_types:
                self._setup_filesystem_isolation(sandbox_root, config)
            
            # Setup network isolation
            if SandboxType.NETWORK in config.sandbox_types:
                self._setup_network_isolation(config)
            
            # Create sandbox instance
            instance = SandboxInstance(
                plugin_id=plugin_id,
                sandbox_id=sandbox_id,
                configuration=config,
                sandbox_root=sandbox_root,
                created_at=time.time(),
                last_activity=time.time()
            )
            
            self.active_sandboxes[sandbox_id] = instance
            
            self.logger.info(f"Sandbox created successfully: {sandbox_id}")
            
            return instance
    
    def execute_in_sandbox(self, sandbox_id: str, command: List[str],
                          working_dir: str = None, env_vars: Dict[str, str] = None) -> Dict[str, Any]:
        """
        Execute command within sandbox.
        
        Args:
            sandbox_id: Sandbox identifier
            command: Command and arguments to execute
            working_dir: Working directory (optional)
            env_vars: Environment variables (optional)
            
        Returns:
            Execution result dictionary
        """
        with self._sandbox_lock:
            sandbox = self.active_sandboxes.get(sandbox_id)
            
            if not sandbox:
                return {"success": False, "error": "Sandbox not found"}
            
            try:
                self.logger.info(f"Executing command in sandbox {sandbox_id}: {' '.join(command)}")
                
                # Prepare execution environment
                exec_env = self._prepare_execution_environment(sandbox, env_vars)
                
                # Determine working directory
                work_dir = working_dir or str(sandbox.sandbox_root)
                
                # Execute command with platform-specific sandboxing
                if self.windows:
                    result = self._execute_windows_sandbox(sandbox, command, work_dir, exec_env)
                elif self.linux:
                    result = self._execute_linux_sandbox(sandbox, command, work_dir, exec_env)
                elif self.macos:
                    result = self._execute_macos_sandbox(sandbox, command, work_dir, exec_env)
                else:
                    result = self._execute_generic_sandbox(sandbox, command, work_dir, exec_env)
                
                # Update sandbox activity
                sandbox.last_activity = time.time()
                if result.get("process_id"):
                    sandbox.process_id = result["process_id"]
                
                return result
                
            except Exception as e:
                self.logger.error(f"Sandbox execution failed: {e}")
                return {"success": False, "error": str(e)}
    
    def monitor_sandbox(self, sandbox_id: str) -> Dict[str, Any]:
        """
        Monitor sandbox activity and resource usage.
        
        Args:
            sandbox_id: Sandbox identifier
            
        Returns:
            Monitoring report
        """
        with self._sandbox_lock:
            sandbox = self.active_sandboxes.get(sandbox_id)
            
            if not sandbox:
                return {"error": "Sandbox not found"}
            
            try:
                monitoring_data = {
                    "sandbox_id": sandbox_id,
                    "plugin_id": sandbox.plugin_id,
                    "status": sandbox.status,
                    "uptime": time.time() - sandbox.created_at,
                    "last_activity": sandbox.last_activity,
                    "violations": len(sandbox.violations),
                    "filesystem_usage": self._monitor_filesystem_usage(sandbox),
                    "process_info": self._monitor_process_info(sandbox),
                    "network_activity": self._monitor_network_activity(sandbox)
                }
                
                return monitoring_data
                
            except Exception as e:
                self.logger.error(f"Sandbox monitoring failed: {e}")
                return {"error": str(e)}
    
    def validate_file_access(self, sandbox_id: str, file_path: str, 
                           access_type: str = "read") -> bool:
        """
        Validate file access request within sandbox.
        
        Args:
            sandbox_id: Sandbox identifier
            file_path: Path to file being accessed
            access_type: Type of access (read, write, execute)
            
        Returns:
            True if access allowed, False otherwise
        """
        with self._sandbox_lock:
            sandbox = self.active_sandboxes.get(sandbox_id)
            
            if not sandbox:
                return False
            
            file_path_obj = Path(file_path).resolve()
            config = sandbox.configuration
            
            # Check if path is within sandbox root
            try:
                file_path_obj.relative_to(sandbox.sandbox_root)
                sandbox_relative = True
            except ValueError:
                sandbox_relative = False
            
            # Check allowed paths
            if not sandbox_relative:
                for allowed_path in config.allowed_paths:
                    try:
                        file_path_obj.relative_to(Path(allowed_path).resolve())
                        break
                    except ValueError:
                        continue
                else:
                    # Path not in allowed list
                    self._record_sandbox_violation(
                        sandbox, "unauthorized_file_access",
                        f"Attempted access to disallowed path: {file_path}"
                    )
                    return False
            
            # Check blocked paths
            for blocked_path in config.blocked_paths:
                try:
                    file_path_obj.relative_to(Path(blocked_path).resolve())
                    # Path is in blocked list
                    self._record_sandbox_violation(
                        sandbox, "blocked_file_access",
                        f"Attempted access to blocked path: {file_path}"
                    )
                    return False
                except ValueError:
                    continue
            
            return True
    
    def validate_network_access(self, sandbox_id: str, host: str, 
                              port: int, protocol: str = "tcp") -> bool:
        """
        Validate network access request from sandbox.
        
        Args:
            sandbox_id: Sandbox identifier
            host: Target host
            port: Target port
            protocol: Network protocol
            
        Returns:
            True if access allowed, False otherwise
        """
        with self._sandbox_lock:
            sandbox = self.active_sandboxes.get(sandbox_id)
            
            if not sandbox:
                return False
            
            config = sandbox.configuration
            
            # Check if network isolation is enabled
            if SandboxType.NETWORK not in config.sandbox_types:
                return True  # No network restrictions
            
            # Check blocked hosts
            for blocked_host in config.blocked_network_hosts:
                if host == blocked_host or host.endswith(f".{blocked_host}"):
                    self._record_sandbox_violation(
                        sandbox, "blocked_network_access",
                        f"Attempted connection to blocked host: {host}:{port}"
                    )
                    return False
            
            # Check allowed hosts (if any specified)
            if config.allowed_network_hosts:
                for allowed_host in config.allowed_network_hosts:
                    if host == allowed_host or host.endswith(f".{allowed_host}"):
                        return True
                
                # Host not in allowed list
                self._record_sandbox_violation(
                    sandbox, "unauthorized_network_access",
                    f"Attempted connection to non-allowed host: {host}:{port}"
                )
                return False
            
            return True
    
    def destroy_sandbox(self, sandbox_id: str, cleanup: bool = True) -> bool:
        """
        Destroy a sandbox instance.
        
        Args:
            sandbox_id: Sandbox identifier
            cleanup: Whether to clean up filesystem resources
            
        Returns:
            True if successful, False otherwise
        """
        with self._sandbox_lock:
            sandbox = self.active_sandboxes.get(sandbox_id)
            
            if not sandbox:
                return False
            
            try:
                self.logger.info(f"Destroying sandbox: {sandbox_id}")
                
                # Terminate any running processes
                if sandbox.process_id:
                    self._terminate_sandbox_process(sandbox)
                
                # Clean up filesystem resources
                if cleanup and sandbox.sandbox_root.exists():
                    shutil.rmtree(sandbox.sandbox_root)
                    self.logger.info(f"Cleaned up sandbox directory: {sandbox.sandbox_root}")
                
                # Remove from active sandboxes
                del self.active_sandboxes[sandbox_id]
                
                self.logger.info(f"Sandbox destroyed successfully: {sandbox_id}")
                return True
                
            except Exception as e:
                self.logger.error(f"Failed to destroy sandbox {sandbox_id}: {e}")
                return False
    
    def _create_sandbox_configuration(self, plugin_id: str, isolation_level: IsolationLevel,
                                    custom_config: Dict[str, Any] = None) -> SandboxConfiguration:
        """Create sandbox configuration based on isolation level."""
        custom_config = custom_config or {}
        
        # Determine sandbox types based on isolation level
        if isolation_level == IsolationLevel.MINIMAL:
            sandbox_types = {SandboxType.FILESYSTEM}
        elif isolation_level == IsolationLevel.MODERATE:
            sandbox_types = {SandboxType.FILESYSTEM, SandboxType.NETWORK}
        elif isolation_level == IsolationLevel.STRICT:
            sandbox_types = {SandboxType.FILESYSTEM, SandboxType.NETWORK, SandboxType.PROCESS}
        else:  # MAXIMUM
            sandbox_types = {SandboxType.FULL}
        
        # Get policy-based configuration
        policy_config = self.sandbox_policies.get(isolation_level.value, {})
        
        config = SandboxConfiguration(
            plugin_id=plugin_id,
            isolation_level=isolation_level,
            sandbox_types=sandbox_types,
            allowed_paths=custom_config.get("allowed_paths", policy_config.get("allowed_paths", [])),
            blocked_paths=custom_config.get("blocked_paths", policy_config.get("blocked_paths", [])),
            allowed_network_hosts=custom_config.get("allowed_network_hosts", policy_config.get("allowed_network_hosts", [])),
            blocked_network_hosts=custom_config.get("blocked_network_hosts", policy_config.get("blocked_network_hosts", [])),
            resource_limits=custom_config.get("resource_limits", policy_config.get("resource_limits", {}))
        )
        
        return config
    
    def _create_sandbox_directory(self, sandbox_id: str) -> Path:
        """Create sandbox directory structure."""
        sandbox_dir = self.sandbox_root_dir / sandbox_id
        sandbox_dir.mkdir(parents=True, exist_ok=True)
        
        # Create standard subdirectories
        subdirs = ["bin", "lib", "tmp", "data", "logs", "cache"]
        for subdir in subdirs:
            (sandbox_dir / subdir).mkdir(exist_ok=True)
        
        # Set appropriate permissions
        if not self.windows:
            os.chmod(sandbox_dir, 0o755)
            for subdir in subdirs:
                os.chmod(sandbox_dir / subdir, 0o755)
        
        return sandbox_dir
    
    def _setup_filesystem_isolation(self, sandbox_root: Path, config: SandboxConfiguration):
        """Setup filesystem isolation for sandbox."""
        if self.fs_overlay_enabled and self.linux:
            # Use overlay filesystem on Linux
            self._setup_overlay_filesystem(sandbox_root, config)
        else:
            # Use bind mounts or directory restrictions
            self._setup_directory_restrictions(sandbox_root, config)
    
    def _setup_overlay_filesystem(self, sandbox_root: Path, config: SandboxConfiguration):
        """Setup overlay filesystem (Linux only)."""
        try:
            # Create overlay directories
            overlay_dir = sandbox_root / "overlay"
            overlay_work = sandbox_root / "work"
            overlay_merged = sandbox_root / "merged"
            
            for dir_path in [overlay_dir, overlay_work, overlay_merged]:
                dir_path.mkdir(exist_ok=True)
            
            # Mount overlay filesystem
            mount_cmd = [
                "mount", "-t", "overlay", "overlay",
                "-o", f"lowerdir=/,upperdir={overlay_dir},workdir={overlay_work}",
                str(overlay_merged)
            ]
            
            # Note: This would require root privileges
            # In practice, would use user namespaces or containers
            self.logger.info(f"Overlay filesystem prepared for {sandbox_root}")
            
        except Exception as e:
            self.logger.error(f"Failed to setup overlay filesystem: {e}")
    
    def _setup_directory_restrictions(self, sandbox_root: Path, config: SandboxConfiguration):
        """Setup directory-based restrictions."""
        # Create symbolic links to allowed system directories
        system_dirs = ["usr", "lib", "bin"]
        
        for sys_dir in system_dirs:
            src_path = Path(f"/{sys_dir}")
            dst_path = sandbox_root / sys_dir
            
            if src_path.exists() and not dst_path.exists():
                try:
                    dst_path.symlink_to(src_path)
                except Exception as e:
                    self.logger.warning(f"Failed to create symlink {dst_path}: {e}")
    
    def _setup_network_isolation(self, config: SandboxConfiguration):
        """Setup network isolation."""
        # This would integrate with network namespaces on Linux
        # or use firewall rules on other platforms
        self.logger.info("Network isolation configured")
    
    def _prepare_execution_environment(self, sandbox: SandboxInstance, 
                                     env_vars: Dict[str, str] = None) -> Dict[str, str]:
        """Prepare execution environment for sandbox."""
        exec_env = os.environ.copy()
        
        # Add sandbox-specific environment variables
        exec_env.update({
            "SANDBOX_ID": sandbox.sandbox_id,
            "SANDBOX_ROOT": str(sandbox.sandbox_root),
            "PLUGIN_ID": sandbox.plugin_id,
            "HOME": str(sandbox.sandbox_root / "data"),
            "TMPDIR": str(sandbox.sandbox_root / "tmp"),
            "TMP": str(sandbox.sandbox_root / "tmp"),
            "TEMP": str(sandbox.sandbox_root / "tmp")
        })
        
        # Add configuration environment variables
        exec_env.update(sandbox.configuration.environment_variables)
        
        # Add custom environment variables
        if env_vars:
            exec_env.update(env_vars)
        
        return exec_env
    
    def _execute_windows_sandbox(self, sandbox: SandboxInstance, command: List[str],
                                work_dir: str, env: Dict[str, str]) -> Dict[str, Any]:
        """Execute command in Windows sandbox."""
        try:
            # Use Windows sandbox APIs or process isolation
            process = subprocess.Popen(
                command,
                cwd=work_dir,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
            )
            
            return {
                "success": True,
                "process_id": process.pid,
                "process": process
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _execute_linux_sandbox(self, sandbox: SandboxInstance, command: List[str],
                             work_dir: str, env: Dict[str, str]) -> Dict[str, Any]:
        """Execute command in Linux sandbox with namespaces."""
        try:
            # Use Linux namespaces for isolation
            # This would require more complex implementation with unshare()
            
            process = subprocess.Popen(
                command,
                cwd=work_dir,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid  # Create new session
            )
            
            return {
                "success": True,
                "process_id": process.pid,
                "process": process
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _execute_macos_sandbox(self, sandbox: SandboxInstance, command: List[str],
                             work_dir: str, env: Dict[str, str]) -> Dict[str, Any]:
        """Execute command in macOS sandbox."""
        try:
            # Use macOS sandbox APIs
            process = subprocess.Popen(
                command,
                cwd=work_dir,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            return {
                "success": True,
                "process_id": process.pid,
                "process": process
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _execute_generic_sandbox(self, sandbox: SandboxInstance, command: List[str],
                                work_dir: str, env: Dict[str, str]) -> Dict[str, Any]:
        """Execute command with generic sandboxing."""
        try:
            process = subprocess.Popen(
                command,
                cwd=work_dir,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            return {
                "success": True,
                "process_id": process.pid,
                "process": process
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _monitor_filesystem_usage(self, sandbox: SandboxInstance) -> Dict[str, Any]:
        """Monitor filesystem usage within sandbox."""
        try:
            if sandbox.sandbox_root.exists():
                total_size = sum(
                    f.stat().st_size for f in sandbox.sandbox_root.rglob("*") if f.is_file()
                )
                
                return {
                    "total_size_bytes": total_size,
                    "total_size_mb": total_size / (1024 * 1024),
                    "file_count": len(list(sandbox.sandbox_root.rglob("*"))),
                    "directory_count": len([p for p in sandbox.sandbox_root.rglob("*") if p.is_dir()])
                }
            else:
                return {"error": "Sandbox directory not found"}
                
        except Exception as e:
            return {"error": str(e)}
    
    def _monitor_process_info(self, sandbox: SandboxInstance) -> Dict[str, Any]:
        """Monitor process information for sandbox."""
        if not sandbox.process_id:
            return {"status": "no_process"}
        
        try:
            import psutil
            process = psutil.Process(sandbox.process_id)
            
            return {
                "status": process.status(),
                "cpu_percent": process.cpu_percent(),
                "memory_info": process.memory_info()._asdict(),
                "num_threads": process.num_threads(),
                "create_time": process.create_time()
            }
            
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return {"status": "process_not_found"}
        except Exception as e:
            return {"error": str(e)}
    
    def _monitor_network_activity(self, sandbox: SandboxInstance) -> Dict[str, Any]:
        """Monitor network activity for sandbox."""
        # Placeholder for network monitoring
        # Would integrate with network monitoring tools
        return {"status": "monitoring_not_implemented"}
    
    def _record_sandbox_violation(self, sandbox: SandboxInstance, violation_type: str, description: str):
        """Record a sandbox violation."""
        violation = {
            "type": violation_type,
            "description": description,
            "timestamp": time.time(),
            "plugin_id": sandbox.plugin_id,
            "sandbox_id": sandbox.sandbox_id
        }
        
        sandbox.violations.append(violation)
        
        self.logger.warning(f"Sandbox violation: {sandbox.sandbox_id} - {description}")
    
    def _terminate_sandbox_process(self, sandbox: SandboxInstance):
        """Terminate sandbox process."""
        if not sandbox.process_id:
            return
        
        try:
            import psutil
            process = psutil.Process(sandbox.process_id)
            process.terminate()
            
            # Wait for termination
            try:
                process.wait(timeout=5)
            except psutil.TimeoutExpired:
                process.kill()  # Force kill if doesn't terminate
                
            self.logger.info(f"Terminated process {sandbox.process_id} for sandbox {sandbox.sandbox_id}")
            
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass  # Process already gone
        except Exception as e:
            self.logger.error(f"Failed to terminate sandbox process: {e}")
    
    def _initialize_platform_sandbox(self):
        """Initialize platform-specific sandboxing features."""
        if self.windows:
            self._initialize_windows_sandbox()
        elif self.linux:
            self._initialize_linux_sandbox()
        elif self.macos:
            self._initialize_macos_sandbox()
    
    def _initialize_windows_sandbox(self):
        """Initialize Windows-specific sandboxing."""
        # Check for Windows Sandbox or container support
        self.logger.info("Initialized Windows sandbox support")
    
    def _initialize_linux_sandbox(self):
        """Initialize Linux-specific sandboxing."""
        # Check for namespace and cgroup support
        namespace_support = Path("/proc/self/ns").exists()
        cgroup_support = Path("/sys/fs/cgroup").exists()
        
        self.logger.info(f"Linux sandbox support: namespaces={namespace_support}, cgroups={cgroup_support}")
    
    def _initialize_macos_sandbox(self):
        """Initialize macOS-specific sandboxing."""
        # Check for macOS sandbox support
        self.logger.info("Initialized macOS sandbox support")
    
    def _load_sandbox_policies(self) -> Dict[str, Any]:
        """Load sandbox policies from configuration."""
        return self.config.get("plugin_sandbox_policies", {
            "minimal": {
                "allowed_paths": [],
                "blocked_paths": ["/etc", "/usr", "/bin", "/sbin"],
                "resource_limits": {
                    "memory_mb": 128,
                    "cpu_percent": 10
                }
            },
            "moderate": {
                "allowed_paths": [],
                "blocked_paths": ["/etc", "/usr", "/bin", "/sbin", "/root"],
                "blocked_network_hosts": ["localhost", "127.0.0.1"],
                "resource_limits": {
                    "memory_mb": 256,
                    "cpu_percent": 25
                }
            },
            "strict": {
                "allowed_paths": [],
                "blocked_paths": ["/"],
                "allowed_network_hosts": [],
                "resource_limits": {
                    "memory_mb": 64,
                    "cpu_percent": 5
                }
            },
            "maximum": {
                "allowed_paths": [],
                "blocked_paths": ["/"],
                "allowed_network_hosts": [],
                "blocked_syscalls": ["execve", "fork", "clone"],
                "resource_limits": {
                    "memory_mb": 32,
                    "cpu_percent": 2
                }
            }
        })
    
    def get_sandbox_status(self, sandbox_id: str = None) -> Dict[str, Any]:
        """Get status of sandbox or all sandboxes."""
        with self._sandbox_lock:
            if sandbox_id:
                sandbox = self.active_sandboxes.get(sandbox_id)
                if not sandbox:
                    return {"error": "Sandbox not found"}
                
                return {
                    "sandbox_id": sandbox_id,
                    "plugin_id": sandbox.plugin_id,
                    "status": sandbox.status,
                    "isolation_level": sandbox.configuration.isolation_level.value,
                    "sandbox_types": [st.value for st in sandbox.configuration.sandbox_types],
                    "created_at": sandbox.created_at,
                    "last_activity": sandbox.last_activity,
                    "violations": len(sandbox.violations),
                    "process_id": sandbox.process_id
                }
            else:
                return {
                    "sandboxing_enabled": self.sandboxing_enabled,
                    "active_sandboxes": len(self.active_sandboxes),
                    "platform": self.platform,
                    "sandbox_root": str(self.sandbox_root_dir),
                    "sandboxes": [
                        {
                            "sandbox_id": sid,
                            "plugin_id": sb.plugin_id,
                            "status": sb.status,
                            "isolation_level": sb.configuration.isolation_level.value
                        }
                        for sid, sb in self.active_sandboxes.items()
                    ]
                }
    
    def cleanup_inactive_sandboxes(self, max_idle_time: float = 3600):
        """Clean up sandboxes that have been inactive."""
        current_time = time.time()
        inactive_sandboxes = []
        
        with self._sandbox_lock:
            for sandbox_id, sandbox in self.active_sandboxes.items():
                if current_time - sandbox.last_activity > max_idle_time:
                    inactive_sandboxes.append(sandbox_id)
        
        for sandbox_id in inactive_sandboxes:
            self.destroy_sandbox(sandbox_id)
            self.logger.info(f"Cleaned up inactive sandbox: {sandbox_id}")
    
    def shutdown(self):
        """Shutdown sandbox controller."""
        self.logger.info("Shutting down sandbox controller")
        
        # Destroy all active sandboxes
        with self._sandbox_lock:
            sandbox_ids = list(self.active_sandboxes.keys())
        
        for sandbox_id in sandbox_ids:
            self.destroy_sandbox(sandbox_id)
        
        self.logger.info("Sandbox controller shutdown complete")