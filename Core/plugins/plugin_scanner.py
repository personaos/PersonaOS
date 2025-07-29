"""
Plugin Scanner for PersonaOS

This module provides plugin discovery and validation functionality,
scanning designated directories for valid plugin files and metadata.
"""

import os
import json
import yaml
import importlib.util
import logging
from typing import List, Dict, Any, Optional, Set
from pathlib import Path
from dataclasses import asdict

from .base_plugin import (
    BasePlugin, PluginMetadata, PluginState, PluginType,
    PluginDependency, PluginPermission, PluginCapability
)

class PluginValidationError(Exception):
    """Exception raised when plugin validation fails."""
    pass

class PluginScanner:
    """
    Scans directories for valid PersonaOS plugins and validates their metadata.
    
    The scanner looks for:
    1. Python files containing plugin classes that inherit from BasePlugin
    2. Metadata files (plugin.yaml, plugin.json, or manifest.json)
    3. Plugin directory structures with proper organization
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize plugin scanner.
        
        Args:
            config: PersonaOS configuration dictionary
        """
        self.config = config or {}
        self.logger = logging.getLogger("plugin_scanner")
        
        # Default plugin directories
        self.plugin_directories = self._load_plugin_directories()
        
        # Validation settings
        self.strict_validation = self.config.get("plugin_strict_validation", True)
        self.allow_dev_plugins = self.config.get("plugin_allow_dev", False)
        self.max_plugin_size = self.config.get("plugin_max_size_mb", 50) * 1024 * 1024  # Convert to bytes
        
        # Supported metadata file names
        self.metadata_files = [
            "plugin.yaml",
            "plugin.yml", 
            "plugin.json",
            "manifest.json",
            "metadata.yaml",
            "metadata.yml"
        ]
        
        # Required plugin structure
        self.required_plugin_files = ["__init__.py"]
        
        self.logger.info(f"PluginScanner initialized with {len(self.plugin_directories)} search directories")
    
    def _load_plugin_directories(self) -> List[Path]:
        """Load plugin search directories from configuration."""
        directories = []
        
        # Default system directories
        project_root = Path(__file__).parent.parent.parent
        default_dirs = [
            project_root / "plugins",
            project_root / "extensions", 
            project_root / "user_plugins"
        ]
        
        # Add configured directories
        config_dirs = self.config.get("plugin_directories", [])
        for dir_path in config_dirs:
            try:
                path = Path(dir_path).expanduser().resolve()
                if path.exists() and path.is_dir():
                    directories.append(path)
                else:
                    self.logger.warning(f"Configured plugin directory does not exist: {path}")
            except Exception as e:
                self.logger.error(f"Invalid plugin directory path '{dir_path}': {e}")
        
        # Add default directories that exist
        for default_dir in default_dirs:
            if default_dir.exists():
                directories.append(default_dir)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_directories = []
        for directory in directories:
            if directory not in seen:
                seen.add(directory)
                unique_directories.append(directory)
        
        return unique_directories
    
    def scan_all_plugins(self) -> List[Dict[str, Any]]:
        """
        Scan all configured directories for plugins.
        
        Returns:
            List of plugin discovery results
        """
        all_plugins = []
        
        for directory in self.plugin_directories:
            self.logger.info(f"Scanning directory: {directory}")
            try:
                plugins = self.scan_directory(directory)
                all_plugins.extend(plugins)
                self.logger.info(f"Found {len(plugins)} plugins in {directory}")
            except Exception as e:
                self.logger.error(f"Error scanning directory {directory}: {e}")
        
        self.logger.info(f"Total plugins discovered: {len(all_plugins)}")
        return all_plugins
    
    def scan_directory(self, directory: Path) -> List[Dict[str, Any]]:
        """
        Scan a single directory for plugins.
        
        Args:
            directory: Directory path to scan
            
        Returns:
            List of plugin discovery results from this directory
        """
        plugins = []
        
        if not directory.exists() or not directory.is_dir():
            self.logger.warning(f"Directory does not exist or is not a directory: {directory}")
            return plugins
        
        # Scan for plugin directories and files
        for item in directory.iterdir():
            if item.is_dir():
                # Check if it's a plugin directory
                plugin_result = self._scan_plugin_directory(item)
                if plugin_result:
                    plugins.append(plugin_result)
            elif item.is_file() and item.suffix == '.py':
                # Check if it's a standalone plugin file
                plugin_result = self._scan_plugin_file(item)
                if plugin_result:
                    plugins.append(plugin_result)
        
        return plugins
    
    def _scan_plugin_directory(self, plugin_dir: Path) -> Optional[Dict[str, Any]]:
        """
        Scan a plugin directory structure.
        
        Args:
            plugin_dir: Path to plugin directory
            
        Returns:
            Plugin discovery result or None if not a valid plugin
        """
        self.logger.debug(f"Scanning plugin directory: {plugin_dir}")
        
        # Check for required files
        init_file = plugin_dir / "__init__.py"
        if not init_file.exists():
            self.logger.debug(f"No __init__.py found in {plugin_dir}")
            return None
        
        # Look for metadata file
        metadata_file = self._find_metadata_file(plugin_dir)
        metadata = None
        
        if metadata_file:
            try:
                metadata = self._load_metadata_file(metadata_file)
            except Exception as e:
                self.logger.warning(f"Failed to load metadata from {metadata_file}: {e}")
                if self.strict_validation:
                    return None
        
        # Scan for plugin classes in the directory
        plugin_classes = self._find_plugin_classes_in_directory(plugin_dir)
        
        if not plugin_classes:
            self.logger.debug(f"No plugin classes found in {plugin_dir}")
            return None
        
        # Create discovery result
        result = {
            "plugin_type": "directory",
            "path": str(plugin_dir),
            "name": plugin_dir.name,
            "metadata_file": str(metadata_file) if metadata_file else None,
            "metadata": metadata,
            "plugin_classes": plugin_classes,
            "validation_result": None,
            "discovery_time": None
        }
        
        # Validate the plugin
        validation_result = self._validate_plugin_structure(result)
        result["validation_result"] = validation_result
        
        import time
        result["discovery_time"] = time.time()
        
        return result
    
    def _scan_plugin_file(self, plugin_file: Path) -> Optional[Dict[str, Any]]:
        """
        Scan a standalone plugin file.
        
        Args:
            plugin_file: Path to plugin Python file
            
        Returns:
            Plugin discovery result or None if not a valid plugin
        """
        self.logger.debug(f"Scanning plugin file: {plugin_file}")
        
        # Look for plugin classes in the file
        plugin_classes = self._find_plugin_classes_in_file(plugin_file)
        
        if not plugin_classes:
            self.logger.debug(f"No plugin classes found in {plugin_file}")
            return None
        
        # Look for accompanying metadata file
        metadata_file = self._find_metadata_file(plugin_file.parent, plugin_file.stem)
        metadata = None
        
        if metadata_file:
            try:
                metadata = self._load_metadata_file(metadata_file)
            except Exception as e:
                self.logger.warning(f"Failed to load metadata from {metadata_file}: {e}")
                if self.strict_validation:
                    return None
        
        # Create discovery result
        result = {
            "plugin_type": "file",
            "path": str(plugin_file),
            "name": plugin_file.stem,
            "metadata_file": str(metadata_file) if metadata_file else None,
            "metadata": metadata,
            "plugin_classes": plugin_classes,
            "validation_result": None,
            "discovery_time": None
        }
        
        # Validate the plugin
        validation_result = self._validate_plugin_structure(result)
        result["validation_result"] = validation_result
        
        import time
        result["discovery_time"] = time.time()
        
        return result
    
    def _find_metadata_file(self, directory: Path, prefix: str = None) -> Optional[Path]:
        """
        Find metadata file in directory.
        
        Args:
            directory: Directory to search
            prefix: Optional prefix for metadata file (for standalone plugins)
            
        Returns:
            Path to metadata file or None if not found
        """
        search_names = self.metadata_files.copy()
        
        # Add prefixed names for standalone plugins
        if prefix:
            prefixed_names = [f"{prefix}.{name}" for name in self.metadata_files]
            search_names.extend(prefixed_names)
        
        for filename in search_names:
            metadata_path = directory / filename
            if metadata_path.exists() and metadata_path.is_file():
                return metadata_path
        
        return None
    
    def _load_metadata_file(self, metadata_file: Path) -> Dict[str, Any]:
        """
        Load and parse metadata file.
        
        Args:
            metadata_file: Path to metadata file
            
        Returns:
            Parsed metadata dictionary
            
        Raises:
            PluginValidationError: If metadata cannot be loaded or parsed
        """
        try:
            with open(metadata_file, 'r', encoding='utf-8') as f:
                if metadata_file.suffix.lower() in ['.yaml', '.yml']:
                    return yaml.safe_load(f) or {}
                elif metadata_file.suffix.lower() == '.json':
                    return json.load(f) or {}
                else:
                    # Try to detect format by content
                    content = f.read()
                    f.seek(0)
                    
                    # Try JSON first
                    try:
                        return json.loads(content) or {}
                    except json.JSONDecodeError:
                        # Try YAML
                        try:
                            return yaml.safe_load(content) or {}
                        except yaml.YAMLError:
                            raise PluginValidationError(f"Unable to parse metadata file format: {metadata_file}")
                            
        except Exception as e:
            raise PluginValidationError(f"Failed to load metadata file {metadata_file}: {e}")
    
    def _find_plugin_classes_in_directory(self, plugin_dir: Path) -> List[Dict[str, Any]]:
        """
        Find plugin classes in a plugin directory.
        
        Args:
            plugin_dir: Directory to search
            
        Returns:
            List of discovered plugin class information
        """
        plugin_classes = []
        
        # Scan Python files in the directory
        for py_file in plugin_dir.glob("*.py"):
            if py_file.name.startswith("_"):
                continue  # Skip private files
                
            classes = self._find_plugin_classes_in_file(py_file)
            plugin_classes.extend(classes)
        
        return plugin_classes
    
    def _find_plugin_classes_in_file(self, python_file: Path) -> List[Dict[str, Any]]:
        """
        Find plugin classes in a Python file.
        
        Args:
            python_file: Python file to analyze
            
        Returns:
            List of discovered plugin class information
        """
        plugin_classes = []
        
        try:
            # Load the module temporarily to inspect classes
            spec = importlib.util.spec_from_file_location(
                f"temp_plugin_{python_file.stem}", 
                python_file
            )
            
            if spec is None or spec.loader is None:
                self.logger.warning(f"Cannot create module spec for {python_file}")
                return plugin_classes
            
            # Import without executing (just for inspection)
            module = importlib.util.module_from_spec(spec)
            
            try:
                spec.loader.exec_module(module)
            except Exception as e:
                self.logger.warning(f"Cannot execute module {python_file}: {e}")
                return plugin_classes
            
            # Find plugin classes
            for name in dir(module):
                obj = getattr(module, name)
                
                # Check if it's a class that inherits from BasePlugin
                if (isinstance(obj, type) and 
                    issubclass(obj, BasePlugin) and 
                    obj is not BasePlugin):
                    
                    try:
                        # Try to get metadata without instantiating
                        # This is tricky since get_metadata is abstract
                        plugin_classes.append({
                            "class_name": name,
                            "module_path": str(python_file),
                            "full_name": f"{python_file.stem}.{name}",
                        })
                        
                        self.logger.debug(f"Found plugin class: {name} in {python_file}")
                        
                    except Exception as e:
                        self.logger.warning(f"Error inspecting plugin class {name}: {e}")
            
        except Exception as e:
            self.logger.warning(f"Error analyzing file {python_file}: {e}")
        
        return plugin_classes
    
    def _validate_plugin_structure(self, plugin_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate plugin structure and metadata.
        
        Args:
            plugin_result: Plugin discovery result to validate
            
        Returns:
            Validation result dictionary
        """
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "metadata_valid": True,
            "structure_valid": True,
            "security_valid": True
        }
        
        try:
            # Validate basic structure
            self._validate_basic_structure(plugin_result, validation_result)
            
            # Validate metadata if present
            if plugin_result.get("metadata"):
                self._validate_metadata(plugin_result["metadata"], validation_result)
            
            # Validate security aspects
            self._validate_security(plugin_result, validation_result)
            
            # Check file size limits
            self._validate_size_limits(plugin_result, validation_result)
            
        except Exception as e:
            validation_result["valid"] = False
            validation_result["errors"].append(f"Validation error: {e}")
        
        # Overall validity
        validation_result["valid"] = (
            len(validation_result["errors"]) == 0 and
            validation_result["structure_valid"] and
            validation_result["metadata_valid"] and
            validation_result["security_valid"]
        )
        
        return validation_result
    
    def _validate_basic_structure(self, plugin_result: Dict[str, Any], validation_result: Dict[str, Any]):
        """Validate basic plugin structure."""
        plugin_path = Path(plugin_result["path"])
        
        # Check if path exists
        if not plugin_path.exists():
            validation_result["errors"].append(f"Plugin path does not exist: {plugin_path}")
            validation_result["structure_valid"] = False
            return
        
        # Check plugin classes
        if not plugin_result.get("plugin_classes"):
            validation_result["errors"].append("No plugin classes found")
            validation_result["structure_valid"] = False
        
        # For directory plugins, check required files
        if plugin_result["plugin_type"] == "directory":
            init_file = plugin_path / "__init__.py"
            if not init_file.exists():
                validation_result["errors"].append("Missing __init__.py file")
                validation_result["structure_valid"] = False
    
    def _validate_metadata(self, metadata: Dict[str, Any], validation_result: Dict[str, Any]):
        """Validate plugin metadata."""
        required_fields = ["name", "version", "description", "author", "plugin_type"]
        
        for field in required_fields:
            if field not in metadata:
                validation_result["errors"].append(f"Missing required metadata field: {field}")
                validation_result["metadata_valid"] = False
        
        # Validate plugin type
        if "plugin_type" in metadata:
            try:
                PluginType(metadata["plugin_type"])
            except ValueError:
                validation_result["errors"].append(f"Invalid plugin_type: {metadata['plugin_type']}")
                validation_result["metadata_valid"] = False
        
        # Validate version format
        if "version" in metadata:
            version = metadata["version"]
            if not isinstance(version, str) or not version.strip():
                validation_result["errors"].append("Version must be a non-empty string")
                validation_result["metadata_valid"] = False
        
        # Validate dependencies
        if "dependencies" in metadata:
            deps = metadata["dependencies"]
            if not isinstance(deps, list):
                validation_result["errors"].append("Dependencies must be a list")
                validation_result["metadata_valid"] = False
            else:
                for i, dep in enumerate(deps):
                    if not isinstance(dep, dict):
                        validation_result["errors"].append(f"Dependency {i} must be a dictionary")
                        validation_result["metadata_valid"] = False
                    elif "name" not in dep or "version" not in dep:
                        validation_result["errors"].append(f"Dependency {i} missing name or version")
                        validation_result["metadata_valid"] = False
        
        # Validate permissions
        if "permissions" in metadata:
            perms = metadata["permissions"]
            if not isinstance(perms, list):
                validation_result["errors"].append("Permissions must be a list")
                validation_result["metadata_valid"] = False
    
    def _validate_security(self, plugin_result: Dict[str, Any], validation_result: Dict[str, Any]):
        """Validate security aspects of plugin."""
        plugin_path = Path(plugin_result["path"])
        
        # Check for suspicious file patterns
        if plugin_path.is_dir():
            for py_file in plugin_path.rglob("*.py"):
                if self._contains_suspicious_code(py_file):
                    validation_result["warnings"].append(f"Potentially suspicious code in {py_file}")
        elif plugin_path.suffix == '.py':
            if self._contains_suspicious_code(plugin_path):
                validation_result["warnings"].append(f"Potentially suspicious code in {plugin_path}")
        
        # Check metadata permissions
        metadata = plugin_result.get("metadata", {})
        permissions = metadata.get("permissions", [])
        
        high_risk_permissions = ["system.execute", "file.write_system", "network.unrestricted"]
        for perm in permissions:
            if isinstance(perm, dict):
                perm_name = perm.get("name", "")
                risk_level = perm.get("risk_level", "low")
                
                if perm_name in high_risk_permissions:
                    validation_result["warnings"].append(f"High-risk permission requested: {perm_name}")
                
                if risk_level in ["high", "critical"]:
                    validation_result["warnings"].append(f"High-risk permission: {perm_name} ({risk_level})")
    
    def _validate_size_limits(self, plugin_result: Dict[str, Any], validation_result: Dict[str, Any]):
        """Validate plugin size limits."""
        plugin_path = Path(plugin_result["path"])
        total_size = 0
        
        try:
            if plugin_path.is_dir():
                for file_path in plugin_path.rglob("*"):
                    if file_path.is_file():
                        total_size += file_path.stat().st_size
            else:
                total_size = plugin_path.stat().st_size
            
            if total_size > self.max_plugin_size:
                validation_result["errors"].append(
                    f"Plugin size ({total_size / 1024 / 1024:.1f}MB) exceeds limit "
                    f"({self.max_plugin_size / 1024 / 1024:.1f}MB)"
                )
                validation_result["security_valid"] = False
                
        except Exception as e:
            validation_result["warnings"].append(f"Could not check plugin size: {e}")
    
    def _contains_suspicious_code(self, python_file: Path) -> bool:
        """
        Check if Python file contains potentially suspicious code patterns.
        
        Args:
            python_file: Python file to check
            
        Returns:
            True if suspicious patterns found
        """
        suspicious_patterns = [
            "exec(",
            "eval(",
            "__import__",
            "subprocess.call",
            "os.system", 
            "open(",  # Only suspicious in certain contexts
            "import os",
            "import subprocess",
            "import sys"
        ]
        
        try:
            with open(python_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read().lower()
                
                for pattern in suspicious_patterns:
                    if pattern.lower() in content:
                        return True
                        
        except Exception:
            # If we can't read the file, consider it suspicious
            return True
        
        return False
    
    def validate_plugin_metadata(self, metadata: Dict[str, Any]) -> PluginMetadata:
        """
        Validate and convert metadata dictionary to PluginMetadata object.
        
        Args:
            metadata: Raw metadata dictionary
            
        Returns:
            Validated PluginMetadata object
            
        Raises:
            PluginValidationError: If metadata is invalid
        """
        try:
            # Convert plugin_type string to enum
            if "plugin_type" in metadata:
                if isinstance(metadata["plugin_type"], str):
                    metadata["plugin_type"] = PluginType(metadata["plugin_type"])
            
            # Convert dependencies to PluginDependency objects
            if "dependencies" in metadata:
                deps = []
                for dep_data in metadata["dependencies"]:
                    if isinstance(dep_data, dict):
                        deps.append(PluginDependency(**dep_data))
                metadata["dependencies"] = deps
            
            # Convert permissions to PluginPermission objects
            if "permissions" in metadata:
                perms = []
                for perm_data in metadata["permissions"]:
                    if isinstance(perm_data, dict):
                        perms.append(PluginPermission(**perm_data))
                metadata["permissions"] = perms
            
            # Convert capabilities to PluginCapability objects
            if "capabilities" in metadata:
                caps = []
                for cap_data in metadata["capabilities"]:
                    if isinstance(cap_data, dict):
                        caps.append(PluginCapability(**cap_data))
                metadata["capabilities"] = caps
            
            # Create PluginMetadata object
            return PluginMetadata(**metadata)
            
        except Exception as e:
            raise PluginValidationError(f"Invalid plugin metadata: {e}")
    
    def get_plugin_directories(self) -> List[Path]:
        """Get list of configured plugin directories."""
        return self.plugin_directories.copy()
    
    def add_plugin_directory(self, directory: Path):
        """Add a new plugin directory to scan."""
        directory = Path(directory).resolve()
        if directory not in self.plugin_directories:
            self.plugin_directories.append(directory)
            self.logger.info(f"Added plugin directory: {directory}")
    
    def remove_plugin_directory(self, directory: Path):
        """Remove a plugin directory from scanning."""
        directory = Path(directory).resolve()
        if directory in self.plugin_directories:
            self.plugin_directories.remove(directory)
            self.logger.info(f"Removed plugin directory: {directory}")
    
    def refresh_plugin_directories(self):
        """Refresh plugin directories from configuration."""
        self.plugin_directories = self._load_plugin_directories()
        self.logger.info(f"Refreshed plugin directories: {len(self.plugin_directories)} directories")