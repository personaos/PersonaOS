"""
Plugin Metadata Validator for PersonaOS

This module provides comprehensive validation of plugin metadata,
ensuring compatibility, security, and proper structure before loading.
"""

import re
import logging
from typing import Dict, List, Any, Optional, Set, Tuple
from pathlib import Path
from dataclasses import asdict

from .base_plugin import (
    PluginMetadata, PluginType, PluginDependency,
    PluginPermission, PluginCapability
)

class MetadataValidationError(Exception):
    """Exception raised when metadata validation fails."""
    pass

class PluginMetadataValidator:
    """
    Validates plugin metadata against PersonaOS requirements and standards.
    
    Provides comprehensive validation including:
    - Schema validation
    - Version compatibility
    - Permission validation
    - Dependency validation
    - Security checks
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize metadata validator.
        
        Args:
            config: PersonaOS configuration dictionary
        """
        self.config = config or {}
        self.logger = logging.getLogger("plugin_metadata_validator")
        
        # Validation rules from configuration
        self.allowed_plugin_types = self._load_allowed_plugin_types()
        self.required_fields = self._load_required_fields()
        self.permission_rules = self._load_permission_rules()
        self.version_patterns = self._load_version_patterns()
        self.security_rules = self._load_security_rules()
        
        # Validation statistics
        self.validation_stats = {
            "total_validations": 0,
            "successful_validations": 0,
            "failed_validations": 0,
            "warning_count": 0
        }
        
        self.logger.info("PluginMetadataValidator initialized")
    
    def validate_metadata(self, metadata_dict: Dict[str, Any], 
                         plugin_path: Optional[Path] = None) -> Dict[str, Any]:
        """
        Validate plugin metadata dictionary.
        
        Args:
            metadata_dict: Raw metadata dictionary to validate
            plugin_path: Optional path to plugin for context
            
        Returns:
            Validation result dictionary
        """
        self.validation_stats["total_validations"] += 1
        
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "validated_metadata": None,
            "validation_details": {}
        }
        
        try:
            self.logger.debug(f"Validating metadata for plugin at {plugin_path}")
            
            # Step 1: Schema validation
            schema_result = self._validate_schema(metadata_dict)
            validation_result["validation_details"]["schema"] = schema_result
            
            if not schema_result["valid"]:
                validation_result["valid"] = False
                validation_result["errors"].extend(schema_result["errors"])
            
            validation_result["warnings"].extend(schema_result.get("warnings", []))
            
            # Step 2: Field validation
            field_result = self._validate_fields(metadata_dict)
            validation_result["validation_details"]["fields"] = field_result
            
            if not field_result["valid"]:
                validation_result["valid"] = False
                validation_result["errors"].extend(field_result["errors"])
            
            validation_result["warnings"].extend(field_result.get("warnings", []))
            
            # Step 3: Dependency validation
            dependency_result = self._validate_dependencies(metadata_dict)
            validation_result["validation_details"]["dependencies"] = dependency_result
            
            if not dependency_result["valid"]:
                validation_result["valid"] = False
                validation_result["errors"].extend(dependency_result["errors"])
            
            validation_result["warnings"].extend(dependency_result.get("warnings", []))
            
            # Step 4: Permission validation
            permission_result = self._validate_permissions(metadata_dict)
            validation_result["validation_details"]["permissions"] = permission_result
            
            if not permission_result["valid"]:
                validation_result["valid"] = False
                validation_result["errors"].extend(permission_result["errors"])
            
            validation_result["warnings"].extend(permission_result.get("warnings", []))
            
            # Step 5: Security validation
            security_result = self._validate_security(metadata_dict, plugin_path)
            validation_result["validation_details"]["security"] = security_result
            
            if not security_result["valid"]:
                validation_result["valid"] = False
                validation_result["errors"].extend(security_result["errors"])
            
            validation_result["warnings"].extend(security_result.get("warnings", []))
            
            # Step 6: Create validated metadata object if valid
            if validation_result["valid"]:
                try:
                    validated_metadata = self._create_validated_metadata(metadata_dict)
                    validation_result["validated_metadata"] = validated_metadata
                except Exception as e:
                    validation_result["valid"] = False
                    validation_result["errors"].append(f"Failed to create metadata object: {e}")
            
            # Update statistics
            if validation_result["valid"]:
                self.validation_stats["successful_validations"] += 1
            else:
                self.validation_stats["failed_validations"] += 1
            
            if validation_result["warnings"]:
                self.validation_stats["warning_count"] += len(validation_result["warnings"])
            
            return validation_result
            
        except Exception as e:
            self.logger.error(f"Metadata validation error: {e}")
            self.validation_stats["failed_validations"] += 1
            
            return {
                "valid": False,
                "errors": [f"Validation error: {e}"],
                "warnings": [],
                "validated_metadata": None,
                "validation_details": {}
            }
    
    def _validate_schema(self, metadata_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Validate basic metadata schema."""
        result = {"valid": True, "errors": [], "warnings": []}
        
        # Check required fields
        for field in self.required_fields:
            if field not in metadata_dict:
                result["valid"] = False
                result["errors"].append(f"Missing required field: {field}")
            elif not metadata_dict[field]:
                result["valid"] = False
                result["errors"].append(f"Required field is empty: {field}")
        
        # Check field types
        field_types = {
            "name": str,
            "version": str,
            "description": str,
            "author": str,
            "plugin_type": str,
            "api_version": str,
            "dependencies": list,
            "permissions": list,
            "capabilities": list,
            "supports_voice": bool,
            "voice_commands": list,
            "voice_aliases": list,
            "tags": list
        }
        
        for field, expected_type in field_types.items():
            if field in metadata_dict:
                value = metadata_dict[field]
                if not isinstance(value, expected_type):
                    result["valid"] = False
                    result["errors"].append(
                        f"Field '{field}' must be {expected_type.__name__}, got {type(value).__name__}"
                    )
        
        return result
    
    def _validate_fields(self, metadata_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Validate individual field values."""
        result = {"valid": True, "errors": [], "warnings": []}
        
        # Validate name
        if "name" in metadata_dict:
            name = metadata_dict["name"]
            if not re.match(r'^[a-zA-Z][a-zA-Z0-9_-]*$', name):
                result["valid"] = False
                result["errors"].append("Plugin name must start with letter and contain only letters, numbers, hyphens, and underscores")
            
            if len(name) > 64:
                result["valid"] = False
                result["errors"].append("Plugin name must be 64 characters or less")
        
        # Validate version
        if "version" in metadata_dict:
            version = metadata_dict["version"]
            version_valid = False
            
            for pattern in self.version_patterns:
                if re.match(pattern, version):
                    version_valid = True
                    break
            
            if not version_valid:
                result["valid"] = False
                result["errors"].append(f"Invalid version format: {version}")
        
        # Validate plugin_type
        if "plugin_type" in metadata_dict:
            plugin_type = metadata_dict["plugin_type"]
            if plugin_type not in [pt.value for pt in PluginType]:
                result["valid"] = False
                result["errors"].append(f"Invalid plugin_type: {plugin_type}")
            elif plugin_type not in self.allowed_plugin_types:
                result["valid"] = False
                result["errors"].append(f"Plugin type not allowed: {plugin_type}")
        
        # Validate description length
        if "description" in metadata_dict:
            description = metadata_dict["description"]
            if len(description) > 500:
                result["warnings"].append("Plugin description is very long (>500 characters)")
            elif len(description) < 10:
                result["warnings"].append("Plugin description is very short (<10 characters)")
        
        # Validate API version
        if "api_version" in metadata_dict:
            api_version = metadata_dict["api_version"]
            supported_versions = ["1.0"]  # Would be configurable
            if api_version not in supported_versions:
                result["warnings"].append(f"API version {api_version} may not be supported")
        
        # Validate voice support
        if metadata_dict.get("supports_voice", False):
            if not metadata_dict.get("voice_commands") and not metadata_dict.get("voice_aliases"):
                result["warnings"].append("Plugin supports voice but has no voice commands or aliases defined")
        
        return result
    
    def _validate_dependencies(self, metadata_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Validate plugin dependencies."""
        result = {"valid": True, "errors": [], "warnings": []}
        
        dependencies = metadata_dict.get("dependencies", [])
        
        for i, dep in enumerate(dependencies):
            if not isinstance(dep, dict):
                result["valid"] = False
                result["errors"].append(f"Dependency {i} must be a dictionary")
                continue
            
            # Required dependency fields
            if "name" not in dep:
                result["valid"] = False
                result["errors"].append(f"Dependency {i} missing 'name' field")
            elif not isinstance(dep["name"], str):
                result["valid"] = False
                result["errors"].append(f"Dependency {i} 'name' must be a string")
            
            if "version" not in dep:
                result["valid"] = False
                result["errors"].append(f"Dependency {i} missing 'version' field")
            elif not isinstance(dep["version"], str):
                result["valid"] = False
                result["errors"].append(f"Dependency {i} 'version' must be a string")
            
            # Optional fields validation
            if "optional" in dep and not isinstance(dep["optional"], bool):
                result["valid"] = False
                result["errors"].append(f"Dependency {i} 'optional' must be a boolean")
            
            # Version validation
            if "min_version" in dep and "max_version" in dep:
                min_ver = dep["min_version"]
                max_ver = dep["max_version"]
                if min_ver > max_ver:  # Simple string comparison
                    result["warnings"].append(f"Dependency {i} min_version > max_version")
            
            # Check for circular dependencies (basic)
            if "name" in dep and dep["name"] == metadata_dict.get("name"):
                result["valid"] = False
                result["errors"].append(f"Plugin cannot depend on itself")
        
        return result
    
    def _validate_permissions(self, metadata_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Validate plugin permissions."""
        result = {"valid": True, "errors": [], "warnings": []}
        
        permissions = metadata_dict.get("permissions", [])
        
        for i, perm in enumerate(permissions):
            if not isinstance(perm, dict):
                result["valid"] = False
                result["errors"].append(f"Permission {i} must be a dictionary")
                continue
            
            # Required permission fields
            if "name" not in perm:
                result["valid"] = False
                result["errors"].append(f"Permission {i} missing 'name' field")
            elif not isinstance(perm["name"], str):
                result["valid"] = False
                result["errors"].append(f"Permission {i} 'name' must be a string")
            
            if "description" not in perm:
                result["valid"] = False
                result["errors"].append(f"Permission {i} missing 'description' field")
            elif not isinstance(perm["description"], str):
                result["valid"] = False
                result["errors"].append(f"Permission {i} 'description' must be a string")
            
            # Validate risk level
            if "risk_level" in perm:
                risk_level = perm["risk_level"]
                valid_risk_levels = ["low", "medium", "high", "critical"]
                if risk_level not in valid_risk_levels:
                    result["valid"] = False
                    result["errors"].append(f"Permission {i} invalid risk_level: {risk_level}")
            
            # Apply permission rules
            if "name" in perm:
                perm_name = perm["name"]
                
                # Check against permission rules
                for rule_name, rule_config in self.permission_rules.items():
                    if rule_name == "blocked_permissions":
                        if perm_name in rule_config:
                            result["valid"] = False
                            result["errors"].append(f"Permission '{perm_name}' is blocked")
                    
                    elif rule_name == "high_risk_permissions":
                        if perm_name in rule_config:
                            risk_level = perm.get("risk_level", "low")
                            if risk_level not in ["high", "critical"]:
                                result["warnings"].append(
                                    f"Permission '{perm_name}' should have high/critical risk level"
                                )
                    
                    elif rule_name == "required_description_keywords":
                        required_keywords = rule_config.get(perm_name, [])
                        if required_keywords:
                            description = perm.get("description", "").lower()
                            missing_keywords = [kw for kw in required_keywords if kw.lower() not in description]
                            if missing_keywords:
                                result["warnings"].append(
                                    f"Permission '{perm_name}' description should mention: {', '.join(missing_keywords)}"
                                )
        
        return result
    
    def _validate_security(self, metadata_dict: Dict[str, Any], plugin_path: Optional[Path]) -> Dict[str, Any]:
        """Validate security aspects of plugin metadata."""
        result = {"valid": True, "errors": [], "warnings": []}
        
        # Check for security-sensitive metadata
        name = metadata_dict.get("name", "")
        description = metadata_dict.get("description", "")
        author = metadata_dict.get("author", "")
        
        # Apply security rules
        for rule_name, rule_config in self.security_rules.items():
            if rule_name == "suspicious_names":
                for suspicious_pattern in rule_config:
                    if re.search(suspicious_pattern, name, re.IGNORECASE):
                        result["warnings"].append(f"Plugin name contains suspicious pattern: {suspicious_pattern}")
            
            elif rule_name == "required_author_info":
                if rule_config.get("require_email", False):
                    if "@" not in author:
                        result["warnings"].append("Author should include email address")
                
                if rule_config.get("min_length", 0) > 0:
                    if len(author) < rule_config["min_length"]:
                        result["warnings"].append(f"Author information too short (minimum {rule_config['min_length']} characters)")
            
            elif rule_name == "forbidden_urls":
                # Check description and metadata for forbidden URLs
                text_to_check = f"{description} {metadata_dict.get('homepage', '')} {metadata_dict.get('repository', '')}"
                for forbidden_pattern in rule_config:
                    if re.search(forbidden_pattern, text_to_check, re.IGNORECASE):
                        result["valid"] = False
                        result["errors"].append(f"Contains forbidden URL pattern: {forbidden_pattern}")
        
        # Check for development/testing indicators
        is_development = (
            "dev" in name.lower() or
            "test" in name.lower() or
            "debug" in name.lower() or
            metadata_dict.get("version", "").endswith("-dev") or
            "development" in metadata_dict.get("tags", [])
        )
        
        if is_development:
            allow_dev = self.config.get("plugin_allow_dev", False)
            if not allow_dev:
                result["valid"] = False
                result["errors"].append("Development plugins are not allowed")
            else:
                result["warnings"].append("This appears to be a development plugin")
        
        return result
    
    def _create_validated_metadata(self, metadata_dict: Dict[str, Any]) -> PluginMetadata:
        """Create validated PluginMetadata object from dictionary."""
        # Convert string enum values to actual enums
        if "plugin_type" in metadata_dict:
            metadata_dict["plugin_type"] = PluginType(metadata_dict["plugin_type"])
        
        # Convert dependency dictionaries to PluginDependency objects
        if "dependencies" in metadata_dict:
            dependencies = []
            for dep_dict in metadata_dict["dependencies"]:
                dependencies.append(PluginDependency(**dep_dict))
            metadata_dict["dependencies"] = dependencies
        
        # Convert permission dictionaries to PluginPermission objects
        if "permissions" in metadata_dict:
            permissions = []
            for perm_dict in metadata_dict["permissions"]:
                permissions.append(PluginPermission(**perm_dict))
            metadata_dict["permissions"] = permissions
        
        # Convert capability dictionaries to PluginCapability objects
        if "capabilities" in metadata_dict:
            capabilities = []
            for cap_dict in metadata_dict["capabilities"]:
                capabilities.append(PluginCapability(**cap_dict))
            metadata_dict["capabilities"] = capabilities
        
        return PluginMetadata(**metadata_dict)
    
    def _load_allowed_plugin_types(self) -> Set[str]:
        """Load allowed plugin types from configuration."""
        default_types = {pt.value for pt in PluginType}
        config_types = self.config.get("plugin_allowed_types", list(default_types))
        return set(config_types)
    
    def _load_required_fields(self) -> List[str]:
        """Load required metadata fields from configuration."""
        return self.config.get("plugin_required_fields", [
            "name", "version", "description", "author", "plugin_type"
        ])
    
    def _load_permission_rules(self) -> Dict[str, Any]:
        """Load permission validation rules from configuration."""
        return self.config.get("plugin_permission_rules", {
            "blocked_permissions": ["system.execute", "file.write_system", "network.unrestricted"],
            "high_risk_permissions": ["file.write", "network.connect", "system.command"],
            "required_description_keywords": {
                "file.write": ["write", "create", "modify"],
                "network.connect": ["network", "internet", "connect"],
                "system.command": ["command", "execute", "run"]
            }
        })
    
    def _load_version_patterns(self) -> List[str]:
        """Load valid version patterns from configuration."""
        return self.config.get("plugin_version_patterns", [
            r'^\d+\.\d+\.\d+$',  # Semantic versioning (x.y.z)
            r'^\d+\.\d+\.\d+-\w+$',  # Semantic with pre-release (x.y.z-alpha)
            r'^\d+\.\d+$',  # Simple versioning (x.y)
            r'^v\d+\.\d+\.\d+$',  # Prefixed semantic (vx.y.z)
        ])
    
    def _load_security_rules(self) -> Dict[str, Any]:
        """Load security validation rules from configuration."""
        return self.config.get("plugin_security_rules", {
            "suspicious_names": [
                r"backdoor", r"malware", r"trojan", r"virus", r"keylog",
                r"exploit", r"rootkit", r"spyware", r"adware"
            ],
            "required_author_info": {
                "require_email": False,
                "min_length": 5
            },
            "forbidden_urls": [
                r"bit\.ly", r"tinyurl", r"t\.co",  # URL shorteners
                r"malware", r"phishing", r"suspicious"  # Suspicious domains
            ]
        })
    
    def get_validation_stats(self) -> Dict[str, Any]:
        """Get validation statistics."""
        return self.validation_stats.copy()
    
    def reset_validation_stats(self):
        """Reset validation statistics."""
        self.validation_stats = {
            "total_validations": 0,
            "successful_validations": 0,
            "failed_validations": 0,
            "warning_count": 0
        }
    
    def validate_metadata_file(self, metadata_file_path: Path) -> Dict[str, Any]:
        """
        Validate metadata from a file.
        
        Args:
            metadata_file_path: Path to metadata file (JSON or YAML)
            
        Returns:
            Validation result dictionary
        """
        try:
            import json
            import yaml
            
            with open(metadata_file_path, 'r', encoding='utf-8') as f:
                if metadata_file_path.suffix.lower() in ['.yaml', '.yml']:
                    metadata_dict = yaml.safe_load(f) or {}
                else:
                    metadata_dict = json.load(f) or {}
            
            return self.validate_metadata(metadata_dict, metadata_file_path.parent)
            
        except Exception as e:
            return {
                "valid": False,
                "errors": [f"Failed to load metadata file {metadata_file_path}: {e}"],
                "warnings": [],
                "validated_metadata": None,
                "validation_details": {}
            }