"""
Dependency Validator for PersonaOS Plugins

This module provides comprehensive validation of plugin dependencies,
including security checks, compatibility verification, and constraint
validation.
"""

import logging
import re
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum

from .base_plugin import PluginMetadata, PluginDependency
from .dependency_resolver import DependencySpec, ResolvedDependency

class ValidationSeverity(Enum):
    """Severity levels for validation issues."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class ValidationCategory(Enum):
    """Categories of validation checks."""
    SECURITY = "security"
    COMPATIBILITY = "compatibility"
    CONSTRAINTS = "constraints"
    PERFORMANCE = "performance"
    BEST_PRACTICES = "best_practices"

@dataclass
class ValidationIssue:
    """Represents a validation issue."""
    category: ValidationCategory
    severity: ValidationSeverity
    message: str
    dependency_name: str
    details: Dict[str, Any] = field(default_factory=dict)
    remediation: Optional[str] = None

@dataclass
class ValidationResult:
    """Result of dependency validation."""
    valid: bool
    issues: List[ValidationIssue] = field(default_factory=list)
    warnings: List[ValidationIssue] = field(default_factory=list)
    errors: List[ValidationIssue] = field(default_factory=list)
    critical_issues: List[ValidationIssue] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)

class DependencyValidator:
    """
    Validates plugin dependencies for security, compatibility, and correctness.
    
    Provides comprehensive validation including:
    - Security vulnerability checks
    - Version constraint validation
    - Compatibility verification
    - Performance impact assessment
    - Best practice compliance
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize dependency validator.
        
        Args:
            config: PersonaOS configuration dictionary
        """
        self.config = config or {}
        self.logger = logging.getLogger("dependency_validator")
        
        # Validation configuration
        self.strict_validation = config.get("plugin_strict_dependency_validation", True)
        self.security_checks_enabled = config.get("plugin_security_checks_enabled", True)
        self.performance_checks_enabled = config.get("plugin_performance_checks_enabled", True)
        
        # Load validation rules
        self.security_rules = self._load_security_rules()
        self.compatibility_rules = self._load_compatibility_rules()
        self.constraint_rules = self._load_constraint_rules()
        self.performance_rules = self._load_performance_rules()
        
        # Known vulnerabilities database (simplified)
        self.vulnerability_db = self._load_vulnerability_database()
        
        # Validation statistics
        self.validation_stats = {
            "total_validations": 0,
            "successful_validations": 0,
            "failed_validations": 0,
            "security_issues_found": 0,
            "compatibility_issues_found": 0,
            "performance_warnings": 0
        }
        
        self.logger.info("DependencyValidator initialized")
    
    def validate_dependencies(self, plugin_metadata: PluginMetadata, 
                            resolved_dependencies: Dict[str, ResolvedDependency],
                            available_plugins: Dict[str, Any] = None) -> ValidationResult:
        """
        Validate plugin dependencies comprehensively.
        
        Args:
            plugin_metadata: Metadata of the plugin being validated
            resolved_dependencies: Dictionary of resolved dependencies
            available_plugins: Available plugins for reference
            
        Returns:
            Validation result with issues and recommendations
        """
        self.validation_stats["total_validations"] += 1
        
        try:
            self.logger.info(f"Validating dependencies for plugin: {plugin_metadata.name}")
            
            result = ValidationResult(valid=True)
            available_plugins = available_plugins or {}
            
            # Validate each dependency
            for dependency in plugin_metadata.dependencies:
                dep_name = dependency.name
                resolved_dep = resolved_dependencies.get(dep_name)
                
                # Security validation
                if self.security_checks_enabled:
                    security_issues = self._validate_dependency_security(
                        dependency, resolved_dep, available_plugins.get(dep_name)
                    )
                    result.issues.extend(security_issues)
                
                # Compatibility validation
                compatibility_issues = self._validate_dependency_compatibility(
                    dependency, resolved_dep, plugin_metadata
                )
                result.issues.extend(compatibility_issues)
                
                # Constraint validation
                constraint_issues = self._validate_dependency_constraints(
                    dependency, resolved_dep
                )
                result.issues.extend(constraint_issues)
                
                # Performance validation
                if self.performance_checks_enabled:
                    performance_issues = self._validate_dependency_performance(
                        dependency, resolved_dep
                    )
                    result.issues.extend(performance_issues)
                
                # Best practices validation
                best_practice_issues = self._validate_dependency_best_practices(
                    dependency, resolved_dep
                )
                result.issues.extend(best_practice_issues)
            
            # Global dependency validation
            global_issues = self._validate_dependency_graph(
                plugin_metadata, resolved_dependencies
            )
            result.issues.extend(global_issues)
            
            # Categorize issues by severity
            result.warnings = [i for i in result.issues if i.severity == ValidationSeverity.WARNING]
            result.errors = [i for i in result.issues if i.severity == ValidationSeverity.ERROR]
            result.critical_issues = [i for i in result.issues if i.severity == ValidationSeverity.CRITICAL]
            
            # Determine overall validity
            result.valid = (len(result.errors) == 0 and len(result.critical_issues) == 0)
            
            if not result.valid and self.strict_validation:
                result.valid = False
            
            # Generate summary
            result.summary = self._generate_validation_summary(result)
            
            # Update statistics
            if result.valid:
                self.validation_stats["successful_validations"] += 1
            else:
                self.validation_stats["failed_validations"] += 1
            
            self.validation_stats["security_issues_found"] += len([
                i for i in result.issues if i.category == ValidationCategory.SECURITY
            ])
            self.validation_stats["compatibility_issues_found"] += len([
                i for i in result.issues if i.category == ValidationCategory.COMPATIBILITY
            ])
            self.validation_stats["performance_warnings"] += len([
                i for i in result.issues if i.category == ValidationCategory.PERFORMANCE
            ])
            
            self.logger.info(f"Dependency validation completed: {len(result.issues)} issues found")
            
            return result
            
        except Exception as e:
            self.validation_stats["failed_validations"] += 1
            self.logger.error(f"Dependency validation failed: {e}")
            
            return ValidationResult(
                valid=False,
                errors=[ValidationIssue(
                    category=ValidationCategory.CONSTRAINTS,
                    severity=ValidationSeverity.ERROR,
                    message=f"Validation error: {e}",
                    dependency_name="unknown"
                )]
            )
    
    def _validate_dependency_security(self, dependency: PluginDependency, 
                                    resolved_dep: Optional[ResolvedDependency],
                                    available_plugin: Optional[Dict[str, Any]]) -> List[ValidationIssue]:
        """Validate security aspects of a dependency."""
        issues = []
        
        # Check for known vulnerabilities
        vulnerability_issues = self._check_vulnerability_database(dependency, resolved_dep)
        issues.extend(vulnerability_issues)
        
        # Check for suspicious dependency names
        suspicious_issues = self._check_suspicious_dependency_names(dependency)
        issues.extend(suspicious_issues)
        
        # Check for excessive permissions
        if resolved_dep and available_plugin:
            permission_issues = self._check_dependency_permissions(dependency, available_plugin)
            issues.extend(permission_issues)
        
        # Check for insecure version constraints
        constraint_issues = self._check_insecure_version_constraints(dependency)
        issues.extend(constraint_issues)
        
        return issues
    
    def _validate_dependency_compatibility(self, dependency: PluginDependency,
                                         resolved_dep: Optional[ResolvedDependency],
                                         plugin_metadata: PluginMetadata) -> List[ValidationIssue]:
        """Validate compatibility aspects of a dependency."""
        issues = []
        
        # Check PersonaOS version compatibility
        if resolved_dep:
            personaos_compat_issues = self._check_personaos_compatibility(
                dependency, resolved_dep, plugin_metadata
            )
            issues.extend(personaos_compat_issues)
        
        # Check Python version compatibility
        python_compat_issues = self._check_python_compatibility(dependency, resolved_dep)
        issues.extend(python_compat_issues)
        
        # Check API compatibility
        api_compat_issues = self._check_api_compatibility(dependency, resolved_dep)
        issues.extend(api_compat_issues)
        
        return issues
    
    def _validate_dependency_constraints(self, dependency: PluginDependency,
                                       resolved_dep: Optional[ResolvedDependency]) -> List[ValidationIssue]:
        """Validate dependency constraints."""
        issues = []
        
        # Check if dependency is resolved
        if not resolved_dep:
            if not dependency.optional:
                issues.append(ValidationIssue(
                    category=ValidationCategory.CONSTRAINTS,
                    severity=ValidationSeverity.ERROR,
                    message=f"Required dependency '{dependency.name}' could not be resolved",
                    dependency_name=dependency.name,
                    remediation="Ensure the dependency is available or make it optional"
                ))
            else:
                issues.append(ValidationIssue(
                    category=ValidationCategory.CONSTRAINTS,
                    severity=ValidationSeverity.WARNING,
                    message=f"Optional dependency '{dependency.name}' could not be resolved",
                    dependency_name=dependency.name
                ))
            return issues
        
        # Validate version constraints
        version_issues = self._validate_version_constraints(dependency, resolved_dep)
        issues.extend(version_issues)
        
        # Check for circular dependencies (would be detected at graph level)
        
        return issues
    
    def _validate_dependency_performance(self, dependency: PluginDependency,
                                       resolved_dep: Optional[ResolvedDependency]) -> List[ValidationIssue]:
        """Validate performance aspects of a dependency."""
        issues = []
        
        if not resolved_dep:
            return issues
        
        # Check for performance-heavy dependencies
        heavy_deps = self.performance_rules.get("heavy_dependencies", [])
        if dependency.name in heavy_deps:
            issues.append(ValidationIssue(
                category=ValidationCategory.PERFORMANCE,
                severity=ValidationSeverity.WARNING,
                message=f"Dependency '{dependency.name}' is known to be resource-intensive",
                dependency_name=dependency.name,
                details={"performance_impact": "high"},
                remediation="Consider alternatives or lazy loading"
            ))
        
        # Check for deprecated dependencies
        deprecated_deps = self.performance_rules.get("deprecated_dependencies", {})
        if dependency.name in deprecated_deps:
            alternative = deprecated_deps[dependency.name].get("alternative", "unknown")
            issues.append(ValidationIssue(
                category=ValidationCategory.PERFORMANCE,
                severity=ValidationSeverity.WARNING,
                message=f"Dependency '{dependency.name}' is deprecated",
                dependency_name=dependency.name,
                details={"alternative": alternative},
                remediation=f"Consider migrating to {alternative}"
            ))
        
        return issues
    
    def _validate_dependency_best_practices(self, dependency: PluginDependency,
                                          resolved_dep: Optional[ResolvedDependency]) -> List[ValidationIssue]:
        """Validate best practices compliance."""
        issues = []
        
        # Check for overly broad version constraints
        if dependency.version == "*" or not dependency.version:
            issues.append(ValidationIssue(
                category=ValidationCategory.BEST_PRACTICES,
                severity=ValidationSeverity.WARNING,  
                message=f"Dependency '{dependency.name}' has no version constraint",
                dependency_name=dependency.name,
                remediation="Specify version constraints for better stability"
            ))
        
        # Check for exact version pinning (can be problematic)
        if resolved_dep and "==" in dependency.version:
            issues.append(ValidationIssue(
                category=ValidationCategory.BEST_PRACTICES,
                severity=ValidationSeverity.INFO,
                message=f"Dependency '{dependency.name}' is pinned to exact version",
                dependency_name=dependency.name,
                details={"pinned_version": resolved_dep.version},
                remediation="Consider using compatible release constraints (~=)"
            ))
        
        return issues
    
    def _validate_dependency_graph(self, plugin_metadata: PluginMetadata,
                                 resolved_dependencies: Dict[str, ResolvedDependency]) -> List[ValidationIssue]:
        """Validate the overall dependency graph."""
        issues = []
        
        # Check dependency count
        dep_count = len(plugin_metadata.dependencies)
        max_dependencies = self.constraint_rules.get("max_dependencies", 20)
        
        if dep_count > max_dependencies:
            issues.append(ValidationIssue(
                category=ValidationCategory.BEST_PRACTICES,
                severity=ValidationSeverity.WARNING,
                message=f"Plugin has {dep_count} dependencies (>{max_dependencies})",
                dependency_name="all",
                remediation="Consider reducing dependencies for better maintainability"
            ))
        
        # Check for conflicting dependencies (simplified)
        name_conflicts = {}
        for dep_name, resolved_dep in resolved_dependencies.items():
            base_name = dep_name.split('-')[0]  # Simple name normalization
            if base_name in name_conflicts:
                name_conflicts[base_name].append(dep_name)
            else:
                name_conflicts[base_name] = [dep_name]
        
        for base_name, dep_names in name_conflicts.items():
            if len(dep_names) > 1:
                issues.append(ValidationIssue(
                    category=ValidationCategory.CONSTRAINTS,
                    severity=ValidationSeverity.WARNING,
                    message=f"Potential naming conflict: {', '.join(dep_names)}",
                    dependency_name="multiple",
                    details={"conflicting_dependencies": dep_names}
                ))
        
        return issues
    
    def _check_vulnerability_database(self, dependency: PluginDependency,
                                    resolved_dep: Optional[ResolvedDependency]) -> List[ValidationIssue]:
        """Check dependency against vulnerability database."""
        issues = []
        
        if not resolved_dep:
            return issues
        
        dep_vulnerabilities = self.vulnerability_db.get(dependency.name, [])
        
        for vuln in dep_vulnerabilities:
            affected_versions = vuln.get("affected_versions", [])
            
            # Simple version checking (would use proper semver in production)
            if resolved_dep.version in affected_versions or "*" in affected_versions:
                severity_map = {
                    "low": ValidationSeverity.WARNING,
                    "medium": ValidationSeverity.WARNING,
                    "high": ValidationSeverity.ERROR,
                    "critical": ValidationSeverity.CRITICAL
                }
                
                severity = severity_map.get(vuln.get("severity", "medium"), ValidationSeverity.WARNING)
                
                issues.append(ValidationIssue(
                    category=ValidationCategory.SECURITY,
                    severity=severity,
                    message=f"Security vulnerability in {dependency.name} v{resolved_dep.version}: {vuln.get('description', 'Unknown vulnerability')}",
                    dependency_name=dependency.name,
                    details={
                        "cve_id": vuln.get("cve_id"),
                        "severity": vuln.get("severity"),
                        "affected_versions": affected_versions
                    },
                    remediation=f"Upgrade to version {vuln.get('fixed_version', 'latest')}"
                ))
        
        return issues
    
    def _check_suspicious_dependency_names(self, dependency: PluginDependency) -> List[ValidationIssue]:
        """Check for suspicious dependency names."""
        issues = []
        
        suspicious_patterns = self.security_rules.get("suspicious_patterns", [])
        
        for pattern in suspicious_patterns:
            if re.search(pattern, dependency.name, re.IGNORECASE):
                issues.append(ValidationIssue(
                    category=ValidationCategory.SECURITY,
                    severity=ValidationSeverity.WARNING,
                    message=f"Dependency name '{dependency.name}' matches suspicious pattern: {pattern}",
                    dependency_name=dependency.name,
                    remediation="Verify the dependency is from a trusted source"
                ))
        
        return issues
    
    def _check_dependency_permissions(self, dependency: PluginDependency,
                                    available_plugin: Dict[str, Any]) -> List[ValidationIssue]:
        """Check dependency permissions for security concerns."""
        issues = []
        
        plugin_metadata = available_plugin.get("metadata", {})
        permissions = plugin_metadata.get("permissions", [])
        
        high_risk_permissions = self.security_rules.get("high_risk_permissions", [])
        
        for permission in permissions:
            perm_name = permission.get("name") if isinstance(permission, dict) else str(permission)
            
            if perm_name in high_risk_permissions:
                issues.append(ValidationIssue(
                    category=ValidationCategory.SECURITY,
                    severity=ValidationSeverity.WARNING,
                    message=f"Dependency '{dependency.name}' requests high-risk permission: {perm_name}",
                    dependency_name=dependency.name,
                    details={"permission": perm_name},
                    remediation="Review if this permission is necessary"
                ))
        
        return issues
    
    def _check_insecure_version_constraints(self, dependency: PluginDependency) -> List[ValidationIssue]:
        """Check for insecure version constraints."""
        issues = []
        
        # Check for pre-release versions in production
        if dependency.version and re.search(r'(alpha|beta|rc|dev)', dependency.version, re.IGNORECASE):
            issues.append(ValidationIssue(
                category=ValidationCategory.SECURITY,
                severity=ValidationSeverity.WARNING,
                message=f"Dependency '{dependency.name}' uses pre-release version: {dependency.version}",
                dependency_name=dependency.name,
                remediation="Use stable versions in production"
            ))
        
        return issues
    
    def _check_personaos_compatibility(self, dependency: PluginDependency,
                                     resolved_dep: ResolvedDependency,
                                     plugin_metadata: PluginMetadata) -> List[ValidationIssue]:
        """Check PersonaOS version compatibility."""
        issues = []
        
        # This would check against PersonaOS API compatibility
        min_version = getattr(plugin_metadata, 'min_personaos_version', '0.1.0')
        current_version = self.config.get('personaos_version', '0.1.0')
        
        # Simple version comparison (would use proper semver)
        if min_version > current_version:
            issues.append(ValidationIssue(
                category=ValidationCategory.COMPATIBILITY,
                severity=ValidationSeverity.ERROR,
                message=f"Dependency '{dependency.name}' requires PersonaOS {min_version}, current version is {current_version}",
                dependency_name=dependency.name,
                remediation="Upgrade PersonaOS or use compatible dependency version"
            ))
        
        return issues
    
    def _check_python_compatibility(self, dependency: PluginDependency,
                                  resolved_dep: Optional[ResolvedDependency]) -> List[ValidationIssue]:
        """Check Python version compatibility."""
        issues = []
        
        # This would check Python version requirements
        # Placeholder for actual implementation
        
        return issues
    
    def _check_api_compatibility(self, dependency: PluginDependency,
                               resolved_dep: Optional[ResolvedDependency]) -> List[ValidationIssue]:
        """Check API compatibility."""
        issues = []
        
        # This would check API version compatibility
        # Placeholder for actual implementation
        
        return issues
    
    def _validate_version_constraints(self, dependency: PluginDependency,
                                    resolved_dep: ResolvedDependency) -> List[ValidationIssue]:
        """Validate version constraints are properly satisfied."""
        issues = []
        
        # Check if resolved version satisfies all constraints
        # This would use the dependency resolver's version comparison logic
        
        return issues
    
    def _generate_validation_summary(self, result: ValidationResult) -> Dict[str, Any]:
        """Generate validation summary."""
        return {
            "total_issues": len(result.issues),
            "by_severity": {
                "info": len([i for i in result.issues if i.severity == ValidationSeverity.INFO]),
                "warning": len([i for i in result.issues if i.severity == ValidationSeverity.WARNING]),
                "error": len([i for i in result.issues if i.severity == ValidationSeverity.ERROR]),
                "critical": len([i for i in result.issues if i.severity == ValidationSeverity.CRITICAL])
            },
            "by_category": {
                "security": len([i for i in result.issues if i.category == ValidationCategory.SECURITY]),
                "compatibility": len([i for i in result.issues if i.category == ValidationCategory.COMPATIBILITY]),
                "constraints": len([i for i in result.issues if i.category == ValidationCategory.CONSTRAINTS]),
                "performance": len([i for i in result.issues if i.category == ValidationCategory.PERFORMANCE]),
                "best_practices": len([i for i in result.issues if i.category == ValidationCategory.BEST_PRACTICES])
            }
        }
    
    def _load_security_rules(self) -> Dict[str, Any]:
        """Load security validation rules."""
        return self.config.get("plugin_security_rules", {
            "suspicious_patterns": [
                r"malware", r"virus", r"trojan", r"backdoor", r"keylog",
                r"phishing", r"exploit", r"rootkit", r"spyware"
            ],
            "high_risk_permissions": [
                "system.execute", "file.write_system", "network.unrestricted",
                "registry.write", "process.create"
            ]
        })
    
    def _load_compatibility_rules(self) -> Dict[str, Any]:
        """Load compatibility validation rules."""
        return self.config.get("plugin_compatibility_rules", {
            "min_python_version": "3.8",
            "max_python_version": "3.12",
            "supported_platforms": ["win32", "linux", "darwin"]
        })
    
    def _load_constraint_rules(self) -> Dict[str, Any]:
        """Load constraint validation rules."""
        return self.config.get("plugin_constraint_rules", {
            "max_dependencies": 20,
            "max_dependency_depth": 5,
            "allowed_version_operators": ["==", ">=", "<=", ">", "<", "~="]
        })
    
    def _load_performance_rules(self) -> Dict[str, Any]:
        """Load performance validation rules."""
        return self.config.get("plugin_performance_rules", {
            "heavy_dependencies": ["tensorflow", "pytorch", "opencv", "numpy"],
            "deprecated_dependencies": {
                "old_plugin": {"alternative": "new_plugin", "reason": "Performance improvements"}
            }
        })
    
    def _load_vulnerability_database(self) -> Dict[str, List[Dict[str, Any]]]:
        """Load vulnerability database (simplified)."""
        # In production, this would load from a real vulnerability database
        return self.config.get("plugin_vulnerability_db", {
            "example_vulnerable_plugin": [
                {
                    "cve_id": "CVE-2024-XXXX",
                    "description": "Example vulnerability",
                    "severity": "high",
                    "affected_versions": ["1.0.0", "1.0.1"],
                    "fixed_version": "1.0.2"
                }
            ]
        })
    
    def get_validation_stats(self) -> Dict[str, Any]:
        """Get validation statistics."""
        return self.validation_stats.copy()
    
    def add_vulnerability(self, plugin_name: str, vulnerability: Dict[str, Any]):
        """Add vulnerability to database."""
        if plugin_name not in self.vulnerability_db:
            self.vulnerability_db[plugin_name] = []
        
        self.vulnerability_db[plugin_name].append(vulnerability)
        self.logger.info(f"Added vulnerability for {plugin_name}: {vulnerability.get('cve_id', 'Unknown')}")
    
    def update_security_rules(self, new_rules: Dict[str, Any]):
        """Update security validation rules."""
        self.security_rules.update(new_rules)
        self.logger.info("Security rules updated")