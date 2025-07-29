"""
Code Executor for PersonaOS DevAgent.

Executes commands safely with output capture, timeout handling,
and environment isolation for autonomous development tasks.
"""

import os
import subprocess
import threading
import time
import logging
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass
from pathlib import Path
from queue import Queue, Empty
import shlex
import signal

# Optional psutil import for process management
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False


@dataclass
class ExecutionResult:
    """Result of code/command execution."""
    command: str
    exit_code: int
    stdout: str
    stderr: str
    execution_time: float
    timeout_occurred: bool = False
    error: Optional[str] = None
    process_id: Optional[int] = None


@dataclass
class ExecutionConfig:
    """Configuration for command execution."""
    timeout: float = 30.0
    working_directory: Optional[str] = None
    environment: Optional[Dict[str, str]] = None
    capture_output: bool = True
    shell: bool = False
    max_output_size: int = 1024 * 1024  # 1MB
    allowed_commands: Optional[List[str]] = None
    blocked_commands: Optional[List[str]] = None


class CodeExecutor:
    """
    Safe code and command executor for development tasks.
    
    Provides timeout handling, output capture, environment isolation,
    and safety controls for autonomous development operations.
    """
    
    def __init__(self, project_root: str, config: Optional[Dict] = None):
        self.project_root = Path(project_root).resolve()
        self.config = config or {}
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Execution configuration
        self.default_timeout = self.config.get('default_timeout', 30.0)
        self.max_concurrent = self.config.get('max_concurrent_processes', 3)
        self.safe_mode = self.config.get('safe_mode', True)
        
        # Command safety configuration
        self.default_allowed_commands = [
            'python', 'pip', 'npm', 'node', 'git', 'pytest', 'black', 'flake8',
            'mypy', 'ls', 'dir', 'cat', 'type', 'echo', 'mkdir', 'cd', 'pwd',
            'grep', 'find', 'wc', 'head', 'tail', 'sort', 'uniq'
        ]
        
        self.blocked_commands = [
            'rm', 'rmdir', 'del', 'format', 'fdisk', 'mkfs', 'dd',
            'shutdown', 'reboot', 'halt', 'init', 'kill', 'killall',
            'su', 'sudo', 'chmod', 'chown', 'chgrp'
        ]
        
        # Process tracking
        self.active_processes: Dict[int, subprocess.Popen] = {}
        self.execution_lock = threading.Lock()
        
        # Execution history
        self.execution_history: List[ExecutionResult] = []
        self.max_history_size = self.config.get('max_history_size', 100)
    
    def _is_command_allowed(self, command: str, config: ExecutionConfig) -> Tuple[bool, str]:
        """Check if command is allowed to execute."""
        if not self.safe_mode:
            return True, ""
        
        # Parse command to get the base command
        try:
            parsed = shlex.split(command)
            if not parsed:
                return False, "Empty command"
            
            base_command = parsed[0].lower()
            
            # Check against custom allowed/blocked lists
            if config.allowed_commands:
                if base_command not in [cmd.lower() for cmd in config.allowed_commands]:
                    return False, f"Command '{base_command}' not in allowed list"
            
            if config.blocked_commands:
                if base_command in [cmd.lower() for cmd in config.blocked_commands]:
                    return False, f"Command '{base_command}' is blocked"
            
            # Check against default blocked commands
            if base_command in [cmd.lower() for cmd in self.blocked_commands]:
                return False, f"Command '{base_command}' is potentially dangerous and blocked"
            
            # Additional safety checks
            dangerous_patterns = ['>', '>>', '|', ';', '&&', '||', '$(', '`']
            if any(pattern in command for pattern in dangerous_patterns):
                return False, f"Command contains potentially dangerous patterns"
            
            return True, ""
            
        except Exception as e:
            return False, f"Failed to parse command: {e}"
    
    def _setup_environment(self, config: ExecutionConfig) -> Dict[str, str]:
        """Setup execution environment."""
        env = os.environ.copy()
        
        # Add project root to Python path
        python_path = env.get('PYTHONPATH', '')
        if python_path:
            python_path = f"{self.project_root}{os.pathsep}{python_path}"
        else:
            python_path = str(self.project_root)
        env['PYTHONPATH'] = python_path
        
        # Apply custom environment variables
        if config.environment:
            env.update(config.environment)
        
        # Set safe defaults
        env['PYTHONDONTWRITEBYTECODE'] = '1'
        env['PYTHONUNBUFFERED'] = '1'
        
        return env
    
    def _read_stream_with_timeout(self, stream, timeout: float) -> Tuple[str, bool]:
        """Read from stream with timeout."""
        output_lines = []
        total_size = 0
        start_time = time.time()
        
        def read_line():
            try:
                return stream.readline()
            except Exception:
                return None
        
        while True:
            if time.time() - start_time > timeout:
                return '\n'.join(output_lines), True
            
            try:
                line = read_line()
                if line is None or line == '':
                    break
                
                decoded_line = line.decode('utf-8', errors='replace').rstrip()
                output_lines.append(decoded_line)
                total_size += len(decoded_line)
                
                # Prevent excessive memory usage
                if total_size > self.config.get('max_output_size', 1024 * 1024):
                    output_lines.append("... [Output truncated due to size limit] ...")
                    break
                    
            except Exception as e:
                self.logger.warning(f"Error reading stream: {e}")
                break
        
        return '\n'.join(output_lines), False
    
    def execute_command(self, command: str, config: Optional[ExecutionConfig] = None) -> ExecutionResult:
        """Execute a shell command with safety controls."""
        if config is None:
            config = ExecutionConfig()
        
        start_time = time.time()
        
        # Validate command safety
        allowed, reason = self._is_command_allowed(command, config)
        if not allowed:
            return ExecutionResult(
                command=command,
                exit_code=-1,
                stdout="",
                stderr="",
                execution_time=0,
                error=f"Command blocked: {reason}"
            )
        
        # Setup working directory
        working_dir = config.working_directory
        if working_dir:
            working_dir = Path(working_dir)
            if not working_dir.is_absolute():
                working_dir = self.project_root / working_directory
        else:
            working_dir = self.project_root
        
        # Setup environment
        env = self._setup_environment(config)
        
        # Limit concurrent processes
        with self.execution_lock:
            if len(self.active_processes) >= self.max_concurrent:
                return ExecutionResult(
                    command=command,
                    exit_code=-1,
                    stdout="",
                    stderr="",
                    execution_time=0,
                    error="Too many concurrent processes"
                )
        
        try:
            self.logger.info(f"Executing command: {command}")
            
            # Start process
            process = subprocess.Popen(
                command,
                shell=config.shell,
                stdout=subprocess.PIPE if config.capture_output else None,
                stderr=subprocess.PIPE if config.capture_output else None,
                cwd=str(working_dir),
                env=env,
                text=False,  # Handle encoding ourselves for better control
                preexec_fn=os.setsid if os.name != 'nt' else None
            )
            
            # Track process
            with self.execution_lock:
                self.active_processes[process.pid] = process
            
            try:
                # Wait for completion with timeout
                stdout_data, stderr_data = process.communicate(timeout=config.timeout)
                
                # Decode output
                stdout = stdout_data.decode('utf-8', errors='replace') if stdout_data else ""
                stderr = stderr_data.decode('utf-8', errors='replace') if stderr_data else ""
                
                execution_time = time.time() - start_time
                
                result = ExecutionResult(
                    command=command,
                    exit_code=process.returncode,
                    stdout=stdout,
                    stderr=stderr,
                    execution_time=execution_time,
                    process_id=process.pid
                )
                
            except subprocess.TimeoutExpired:
                # Handle timeout
                self.logger.warning(f"Command timed out after {config.timeout}s: {command}")
                
                # Terminate process tree
                try:
                    if os.name == 'nt':
                        # Windows
                        process.terminate()
                    else:
                        # Unix-like
                        os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                    
                    # Give it a moment to terminate gracefully
                    time.sleep(1)
                    
                    if process.poll() is None:
                        # Force kill if still running
                        if os.name == 'nt':
                            process.kill()
                        else:
                            os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                            
                except Exception as e:
                    self.logger.error(f"Failed to terminate process {process.pid}: {e}")
                
                # Collect any output that was generated
                try:
                    stdout_data, stderr_data = process.communicate(timeout=1)
                    stdout = stdout_data.decode('utf-8', errors='replace') if stdout_data else ""
                    stderr = stderr_data.decode('utf-8', errors='replace') if stderr_data else ""
                except:
                    stdout = ""
                    stderr = "Process terminated due to timeout"
                
                execution_time = time.time() - start_time
                
                result = ExecutionResult(
                    command=command,
                    exit_code=-1,
                    stdout=stdout,
                    stderr=stderr,
                    execution_time=execution_time,
                    timeout_occurred=True,
                    process_id=process.pid
                )
                
        except Exception as e:
            execution_time = time.time() - start_time
            result = ExecutionResult(
                command=command,
                exit_code=-1,
                stdout="",
                stderr="",
                execution_time=execution_time,
                error=f"Execution failed: {e}"
            )
            
        finally:
            # Remove from active processes
            with self.execution_lock:
                self.active_processes.pop(process.pid, None)
        
        # Add to history
        self.execution_history.append(result)
        if len(self.execution_history) > self.max_history_size:
            self.execution_history.pop(0)
        
        # Log result
        if result.exit_code == 0:
            self.logger.info(f"Command completed successfully in {result.execution_time:.2f}s")
        else:
            self.logger.warning(f"Command failed with exit code {result.exit_code}")
        
        return result
    
    def execute_python_code(self, code: str, config: Optional[ExecutionConfig] = None) -> ExecutionResult:
        """Execute Python code string."""
        if config is None:
            config = ExecutionConfig()
        
        # Create temporary Python file
        import tempfile
        import textwrap
        
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                # Add safety imports and error handling
                safe_code = textwrap.dedent(f'''
                import sys
                import os
                import traceback
                
                try:
                    # User code
                {textwrap.indent(code, "    ")}
                except Exception as e:
                    print(f"Error: {{e}}", file=sys.stderr)
                    traceback.print_exc(file=sys.stderr)
                    sys.exit(1)
                ''')
                
                f.write(safe_code)
                temp_file = f.name
            
            # Execute the temporary file
            python_command = f"python \"{temp_file}\""
            result = self.execute_command(python_command, config)
            
            # Clean up temporary file
            try:
                os.unlink(temp_file)
            except Exception:
                pass
            
            # Update command in result to show original code
            result.command = f"python -c \"{code[:100]}{'...' if len(code) > 100 else ''}\""
            
            return result
            
        except Exception as e:
            return ExecutionResult(
                command=f"python -c \"{code[:50]}...\"",
                exit_code=-1,
                stdout="",
                stderr="",
                execution_time=0,
                error=f"Failed to create temporary Python file: {e}"
            )
    
    def run_tests(self, test_path: str = "", config: Optional[ExecutionConfig] = None) -> ExecutionResult:
        """Run tests using pytest or other test framework."""
        if config is None:
            config = ExecutionConfig(timeout=120.0)  # Longer timeout for tests
        
        # Determine test command
        test_command = "python -m pytest"
        
        if test_path:
            test_path_full = self.project_root / test_path
            if test_path_full.exists():
                test_command += f" \"{test_path}\""
            else:
                return ExecutionResult(
                    command=test_command,
                    exit_code=-1,
                    stdout="",
                    stderr="",
                    execution_time=0,
                    error=f"Test path not found: {test_path}"
                )
        
        # Add common pytest arguments
        test_command += " -v --tb=short"
        
        return self.execute_command(test_command, config)
    
    def install_dependencies(self, requirements: List[str], config: Optional[ExecutionConfig] = None) -> ExecutionResult:
        """Install Python dependencies using pip."""
        if config is None:
            config = ExecutionConfig(timeout=300.0)  # 5 minutes for installs
        
        if not requirements:
            return ExecutionResult(
                command="pip install",
                exit_code=0,
                stdout="No requirements to install",
                stderr="",
                execution_time=0
            )
        
        # Build pip install command
        requirements_str = " ".join(f'"{req}"' for req in requirements)
        pip_command = f"python -m pip install {requirements_str}"
        
        return self.execute_command(pip_command, config)
    
    def run_linting(self, files: Optional[List[str]] = None, config: Optional[ExecutionConfig] = None) -> Dict[str, ExecutionResult]:
        """Run linting tools on specified files or entire project."""
        if config is None:
            config = ExecutionConfig(timeout=60.0)
        
        results = {}
        
        # Define linting commands
        linting_commands = {
            'flake8': 'python -m flake8',
            'black': 'python -m black --check --diff',
            'mypy': 'python -m mypy'
        }
        
        # Build file arguments
        file_args = ""
        if files:
            file_args = " " + " ".join(f'"{f}"' for f in files)
        else:
            file_args = " ."
        
        # Run each linting tool
        for tool, base_command in linting_commands.items():
            command = base_command + file_args
            result = self.execute_command(command, config)
            results[tool] = result
        
        return results
    
    def get_execution_history(self, limit: int = 50) -> List[ExecutionResult]:
        """Get recent execution history."""
        return self.execution_history[-limit:]
    
    def kill_all_processes(self) -> None:
        """Kill all active processes."""
        with self.execution_lock:
            for pid, process in list(self.active_processes.items()):
                try:
                    if process.poll() is None:  # Still running
                        self.logger.info(f"Terminating process {pid}")
                        
                        if os.name == 'nt':
                            process.terminate()
                        else:
                            os.killpg(os.getpgid(pid), signal.SIGTERM)
                        
                        # Wait briefly for graceful termination
                        time.sleep(1)
                        
                        if process.poll() is None:
                            # Force kill
                            if os.name == 'nt':
                                process.kill()
                            else:
                                os.killpg(os.getpgid(pid), signal.SIGKILL)
                                
                except Exception as e:
                    self.logger.error(f"Failed to kill process {pid}: {e}")
            
            self.active_processes.clear()
    
    def get_system_info(self) -> Dict[str, Any]:
        """Get system information for debugging."""
        try:
            return {
                'platform': os.name,
                'working_directory': str(self.project_root),
                'python_version': os.sys.version,
                'environment_variables': dict(os.environ),
                'active_processes': len(self.active_processes),
                'execution_history_count': len(self.execution_history),
                'safe_mode': self.safe_mode,
                'max_concurrent': self.max_concurrent,
                'default_timeout': self.default_timeout
            }
        except Exception as e:
            return {'error': f"Failed to get system info: {e}"}
    
    def cleanup(self) -> None:
        """Clean up executor resources."""
        self.kill_all_processes()
        self.logger.info("Code executor cleaned up")