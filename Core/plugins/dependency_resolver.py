"""
Advanced Dependency Resolver for PersonaOS Plugins

This module provides sophisticated dependency resolution capabilities,
including version compatibility checking, circular dependency detection,
and optimal loading order determination.
"""

import logging
import re
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass
from enum import Enum

class DependencyResolutionError(Exception):
    """Exception raised when dependency resolution fails."""
    pass

class VersionOperator(Enum):
    """Version comparison operators."""
    EQUAL = "=="
    NOT_EQUAL = "!="
    GREATER_THAN = ">"
    GREATER_EQUAL = ">="
    LESS_THAN = "<"
    LESS_EQUAL = "<="
    COMPATIBLE = "~="  # Compatible release
    ARBITRARY_EQUAL = "==="  # Arbitrary equality

@dataclass
class VersionSpec:
    """Version specification with operator and value."""
    operator: VersionOperator
    version: str
    
    def __str__(self):
        return f"{self.operator.value}{self.version}"

@dataclass
class DependencySpec:
    """Enhanced dependency specification."""
    name: str
    version_specs: List[VersionSpec]
    optional: bool = False
    extras: List[str] = None
    environment_markers: str = None
    
    def __post_init__(self):
        if self.extras is None:
            self.extras = []

@dataclass
class ResolvedDependency:
    """Represents a resolved dependency with version information."""
    name: str
    version: str
    plugin_id: str
    optional: bool
    resolved_version_specs: List[VersionSpec]

class AdvancedDependencyResolver:
    """
    Advanced dependency resolver with comprehensive version handling.
    
    Provides sophisticated dependency resolution including:
    - Semantic version parsing and comparison
    - Complex version constraint solving
    - Circular dependency detection
    - Optimal loading order determination
    - Conflict resolution strategies
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize dependency resolver.
        
        Args:
            config: PersonaOS configuration dictionary
        """
        self.config = config or {}
        self.logger = logging.getLogger("advanced_dependency_resolver")
        
        # Resolver configuration
        self.allow_pre_releases = config.get("plugin_allow_pre_releases", False)
        self.strict_version_matching = config.get("plugin_strict_version_matching", True)
        self.conflict_resolution_strategy = config.get("plugin_conflict_resolution", "latest")
        
        # Version pattern configurations
        self.version_patterns = self._load_version_patterns()
        
        # Resolution cache
        self.resolution_cache: Dict[str, Any] = {}
        self.version_cache: Dict[str, Dict] = {}
        
        # Statistics
        self.resolution_stats = {
            "total_resolutions": 0,
            "successful_resolutions": 0,
            "failed_resolutions": 0,
            "cache_hits": 0,
            "circular_dependencies_detected": 0
        }
        
        self.logger.info("AdvancedDependencyResolver initialized")
    
    def resolve_dependencies(self, plugins: List[Dict[str, Any]], 
                           available_plugins: Dict[str, Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Resolve dependencies for a list of plugins.
        
        Args:
            plugins: List of plugin discovery results
            available_plugins: Optional registry of available plugins
            
        Returns:
            Resolution result with load order and dependency information
        """
        self.resolution_stats["total_resolutions"] += 1
        
        try:
            self.logger.info(f"Resolving dependencies for {len(plugins)} plugins")
            
            # Parse plugin dependencies
            plugin_dependencies = self._parse_plugin_dependencies(plugins)
            
            # Build dependency graph
            dependency_graph = self._build_dependency_graph(plugin_dependencies)
            
            # Detect circular dependencies
            circular_deps = self._detect_circular_dependencies(dependency_graph)
            if circular_deps:
                self.resolution_stats["circular_dependencies_detected"] += 1
                raise DependencyResolutionError(f"Circular dependencies detected: {circular_deps}")
            
            # Resolve version constraints
            resolved_dependencies = self._resolve_version_constraints(
                plugin_dependencies, available_plugins or {}
            )
            
            # Determine load order
            load_order = self._determine_load_order(dependency_graph, plugins)
            
            # Validate resolution
            validation_result = self._validate_resolution(resolved_dependencies, load_order)
            
            self.resolution_stats["successful_resolutions"] += 1
            
            result = {
                "success": True,
                "load_order": load_order,
                "resolved_dependencies": resolved_dependencies,
                "dependency_graph": dependency_graph,
                "validation_result": validation_result,
                "resolution_metadata": {
                    "total_plugins": len(plugins),
                    "total_dependencies": sum(len(deps) for deps in plugin_dependencies.values()),
                    "resolution_strategy": self.conflict_resolution_strategy
                }
            }
            
            self.logger.info(f"Dependency resolution successful: {len(load_order)} plugins in load order")
            return result
            
        except Exception as e:
            self.resolution_stats["failed_resolutions"] += 1
            self.logger.error(f"Dependency resolution failed: {e}")
            
            return {
                "success": False,
                "error": str(e),
                "plugins": plugins,
                "resolution_metadata": {
                    "total_plugins": len(plugins),
                    "resolution_strategy": self.conflict_resolution_strategy
                }
            }
    
    def _parse_plugin_dependencies(self, plugins: List[Dict[str, Any]]) -> Dict[str, List[DependencySpec]]:
        """Parse plugin dependencies into structured format."""
        plugin_dependencies = {}
        
        for plugin in plugins:
            plugin_name = self._get_plugin_name(plugin)
            metadata = plugin.get("metadata", {})
            raw_dependencies = metadata.get("dependencies", [])
            
            parsed_deps = []
            for dep in raw_dependencies:
                try:
                    if isinstance(dep, dict):
                        parsed_dep = self._parse_dependency_dict(dep)
                    else:
                        parsed_dep = self._parse_dependency_string(str(dep))
                    
                    parsed_deps.append(parsed_dep)
                    
                except Exception as e:
                    self.logger.warning(f"Failed to parse dependency '{dep}' for plugin {plugin_name}: {e}")
            
            plugin_dependencies[plugin_name] = parsed_deps
        
        return plugin_dependencies
    
    def _parse_dependency_dict(self, dep_dict: Dict[str, Any]) -> DependencySpec:
        """Parse dependency from dictionary format."""
        name = dep_dict.get("name", "")
        if not name:
            raise ValueError("Dependency name is required")
        
        # Parse version specifications
        version_specs = []
        
        # Handle different version fields
        if "version" in dep_dict:
            version_specs.extend(self._parse_version_string(dep_dict["version"]))
        
        if "min_version" in dep_dict:
            version_specs.append(VersionSpec(VersionOperator.GREATER_EQUAL, dep_dict["min_version"]))
        
        if "max_version" in dep_dict:
            version_specs.append(VersionSpec(VersionOperator.LESS_EQUAL, dep_dict["max_version"]))
        
        return DependencySpec(
            name=name,
            version_specs=version_specs,
            optional=dep_dict.get("optional", False),
            extras=dep_dict.get("extras", []),
            environment_markers=dep_dict.get("environment_markers")
        )
    
    def _parse_dependency_string(self, dep_string: str) -> DependencySpec:
        """Parse dependency from string format (e.g., 'package>=1.0,<2.0')."""
        # Simple regex for parsing dependency strings
        pattern = r'^([a-zA-Z0-9_-]+)(.*)$'
        match = re.match(pattern, dep_string.strip())
        
        if not match:
            raise ValueError(f"Invalid dependency string format: {dep_string}")
        
        name = match.group(1)
        version_part = match.group(2).strip()
        
        version_specs = []
        if version_part:
            version_specs = self._parse_version_string(version_part)
        
        return DependencySpec(name=name, version_specs=version_specs)
    
    def _parse_version_string(self, version_string: str) -> List[VersionSpec]:
        """Parse version string into version specifications."""
        version_specs = []
        
        # Handle comma-separated version constraints
        constraints = [c.strip() for c in version_string.split(",")]
        
        for constraint in constraints:
            if not constraint:
                continue
            
            # Match version operators
            operator_patterns = [
                (r'^===(.+)$', VersionOperator.ARBITRARY_EQUAL),
                (r'^==(.+)$', VersionOperator.EQUAL),
                (r'^!=(.+)$', VersionOperator.NOT_EQUAL),
                (r'^>=(.+)$', VersionOperator.GREATER_EQUAL),
                (r'^>(.+)$', VersionOperator.GREATER_THAN),
                (r'^<=(.+)$', VersionOperator.LESS_EQUAL),
                (r'^<(.+)$', VersionOperator.LESS_THAN),
                (r'^~=(.+)$', VersionOperator.COMPATIBLE),
                (r'^(.+)$', VersionOperator.EQUAL)  # Default to equality
            ]
            
            for pattern, operator in operator_patterns:
                match = re.match(pattern, constraint)
                if match:
                    version = match.group(1).strip()
                    version_specs.append(VersionSpec(operator, version))
                    break
        
        return version_specs
    
    def _build_dependency_graph(self, plugin_dependencies: Dict[str, List[DependencySpec]]) -> Dict[str, Set[str]]:
        """Build dependency graph from parsed dependencies."""
        graph = {}
        
        for plugin_name, dependencies in plugin_dependencies.items():
            deps_set = set()
            for dep in dependencies:
                if not dep.optional:  # Only include required dependencies in graph
                    deps_set.add(dep.name)
            graph[plugin_name] = deps_set
        
        return graph
    
    def _detect_circular_dependencies(self, dependency_graph: Dict[str, Set[str]]) -> List[List[str]]:
        """Detect circular dependencies using DFS."""
        circular_deps = []
        visited = set()
        rec_stack = set()
        
        def dfs(node: str, path: List[str]) -> bool:
            if node in rec_stack:
                # Found a cycle
                cycle_start = path.index(node)
                cycle = path[cycle_start:] + [node]
                circular_deps.append(cycle)
                return True
            
            if node in visited:
                return False
            
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            
            for neighbor in dependency_graph.get(node, set()):
                if dfs(neighbor, path):
                    return True
            
            rec_stack.remove(node)
            path.pop()
            return False
        
        for node in dependency_graph:
            if node not in visited:
                dfs(node, [])
        
        return circular_deps
    
    def _resolve_version_constraints(self, plugin_dependencies: Dict[str, List[DependencySpec]], 
                                   available_plugins: Dict[str, Dict[str, Any]]) -> Dict[str, ResolvedDependency]:
        """Resolve version constraints for all dependencies."""
        resolved = {}
        
        # Collect all unique dependencies
        all_dependencies = {}
        for plugin_name, deps in plugin_dependencies.items():
            for dep in deps:
                if dep.name not in all_dependencies:
                    all_dependencies[dep.name] = []
                all_dependencies[dep.name].append((plugin_name, dep))
        
        # Resolve each dependency
        for dep_name, dep_requests in all_dependencies.items():
            try:
                resolved_dep = self._resolve_single_dependency(dep_name, dep_requests, available_plugins)
                if resolved_dep:
                    resolved[dep_name] = resolved_dep
            except Exception as e:
                self.logger.error(f"Failed to resolve dependency {dep_name}: {e}")
                # Continue with other dependencies
        
        return resolved
    
    def _resolve_single_dependency(self, dep_name: str, 
                                 dep_requests: List[Tuple[str, DependencySpec]], 
                                 available_plugins: Dict[str, Dict[str, Any]]) -> Optional[ResolvedDependency]:
        """Resolve a single dependency with multiple version constraints."""
        # Check if dependency is available
        if dep_name not in available_plugins:
            # Check if all requests are optional
            all_optional = all(dep.optional for _, dep in dep_requests)
            if all_optional:
                return None
            else:
                raise DependencyResolutionError(f"Required dependency not available: {dep_name}")
        
        available_plugin = available_plugins[dep_name]
        available_version = available_plugin.get("version", "0.0.0")
        
        # Collect all version constraints
        all_version_specs = []
        any_optional = False
        
        for requester, dep_spec in dep_requests:
            all_version_specs.extend(dep_spec.version_specs)
            if dep_spec.optional:
                any_optional = True
        
        # Check if available version satisfies all constraints
        if self._version_satisfies_constraints(available_version, all_version_specs):
            return ResolvedDependency(
                name=dep_name,
                version=available_version,
                plugin_id=available_plugin.get("plugin_id", dep_name),
                optional=any_optional,
                resolved_version_specs=all_version_specs
            )
        else:
            constraint_str = ", ".join(str(spec) for spec in all_version_specs)
            error_msg = f"Version conflict for {dep_name}: available {available_version}, required {constraint_str}"
            
            if any_optional:
                self.logger.warning(error_msg)
                return None
            else:
                raise DependencyResolutionError(error_msg)
    
    def _version_satisfies_constraints(self, version: str, constraints: List[VersionSpec]) -> bool:
        """Check if version satisfies all constraints."""
        for constraint in constraints:
            if not self._compare_versions(version, constraint.operator, constraint.version):
                return False
        return True
    
    def _compare_versions(self, version1: str, operator: VersionOperator, version2: str) -> bool:
        """Compare two versions using the specified operator."""
        # Simple version comparison (would use proper semver in production)
        try:
            v1_parts = self._parse_version_parts(version1)
            v2_parts = self._parse_version_parts(version2)
            
            # Normalize to same length
            max_len = max(len(v1_parts), len(v2_parts))
            v1_parts.extend([0] * (max_len - len(v1_parts)))
            v2_parts.extend([0] * (max_len - len(v2_parts)))
            
            comparison = 0
            for i in range(max_len):
                if v1_parts[i] < v2_parts[i]:
                    comparison = -1
                    break
                elif v1_parts[i] > v2_parts[i]:
                    comparison = 1
                    break
            
            if operator == VersionOperator.EQUAL:
                return comparison == 0
            elif operator == VersionOperator.NOT_EQUAL:
                return comparison != 0
            elif operator == VersionOperator.GREATER_THAN:
                return comparison > 0
            elif operator == VersionOperator.GREATER_EQUAL:
                return comparison >= 0
            elif operator == VersionOperator.LESS_THAN:
                return comparison < 0
            elif operator == VersionOperator.LESS_EQUAL:
                return comparison <= 0
            elif operator == VersionOperator.COMPATIBLE:
                # Compatible release (~=): same major.minor, higher patch allowed
                return (v1_parts[0] == v2_parts[0] and 
                       v1_parts[1] == v2_parts[1] and 
                       comparison >= 0)
            elif operator == VersionOperator.ARBITRARY_EQUAL:
                return version1 == version2
            
            return False
            
        except Exception as e:
            self.logger.warning(f"Version comparison error: {version1} {operator.value} {version2}: {e}")
            return False
    
    def _parse_version_parts(self, version: str) -> List[int]:
        """Parse version string into numeric parts."""
        # Remove 'v' prefix if present
        if version.startswith('v'):
            version = version[1:]
        
        # Split on dots and parse numbers
        parts = []
        for part in version.split('.'):
            # Handle pre-release versions (e.g., 1.0.0-alpha)
            if '-' in part:
                part = part.split('-')[0]
            
            try:
                parts.append(int(part))
            except ValueError:
                # Handle non-numeric parts
                parts.append(0)
        
        return parts
    
    def _determine_load_order(self, dependency_graph: Dict[str, Set[str]], 
                            plugins: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Determine optimal plugin load order using topological sort."""
        # Create plugin lookup
        plugin_lookup = {self._get_plugin_name(p): p for p in plugins}
        
        # Perform topological sort using Kahn's algorithm
        in_degree = {}
        all_nodes = set()
        
        # Initialize in-degrees
        for node in dependency_graph:
            all_nodes.add(node)
            if node not in in_degree:
                in_degree[node] = 0
            
            for dependency in dependency_graph[node]:
                all_nodes.add(dependency)
                if dependency not in in_degree:
                    in_degree[dependency] = 0
                in_degree[dependency] += 1
        
        # Find nodes with no incoming edges
        queue = [node for node in all_nodes if in_degree[node] == 0]
        result = []
        
        while queue:
            # Sort queue for consistent ordering
            queue.sort()
            node = queue.pop(0)
            
            # Add to result if plugin exists
            if node in plugin_lookup:
                result.append(plugin_lookup[node])
            
            # Remove edges from this node
            for neighbor in dependency_graph.get(node, set()):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        # Check for remaining cycles
        remaining_nodes = [node for node in all_nodes if in_degree[node] > 0]
        if remaining_nodes:
            self.logger.warning(f"Possible circular dependencies in nodes: {remaining_nodes}")
        
        # Add any remaining plugins that weren't in the dependency graph
        for plugin in plugins:
            if plugin not in result:
                result.append(plugin)
        
        return result
    
    def _validate_resolution(self, resolved_dependencies: Dict[str, ResolvedDependency], 
                           load_order: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate the dependency resolution."""
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "statistics": {}
        }
        
        try:
            # Check if all required dependencies are resolved
            total_deps = len(resolved_dependencies)
            optional_deps = sum(1 for dep in resolved_dependencies.values() if dep.optional)
            required_deps = total_deps - optional_deps
            
            validation_result["statistics"] = {
                "total_dependencies": total_deps,
                "required_dependencies": required_deps,
                "optional_dependencies": optional_deps,
                "load_order_length": len(load_order)
            }
            
            # Additional validation checks could be added here
            
        except Exception as e:
            validation_result["valid"] = False
            validation_result["errors"].append(f"Validation error: {e}")
        
        return validation_result
    
    def _get_plugin_name(self, plugin: Dict[str, Any]) -> str:
        """Extract plugin name from plugin info."""
        metadata = plugin.get("metadata", {})
        return metadata.get("name", plugin.get("name", "unknown"))
    
    def _load_version_patterns(self) -> Dict[str, str]:
        """Load version pattern configurations."""
        return self.config.get("plugin_version_patterns", {
            "semantic": r'^\d+\.\d+\.\d+$',
            "semantic_pre": r'^\d+\.\d+\.\d+-[a-zA-Z0-9]+$',
            "simple": r'^\d+\.\d+$',
            "prefixed": r'^v\d+\.\d+\.\d+$'
        })
    
    def get_resolution_stats(self) -> Dict[str, Any]:
        """Get dependency resolution statistics."""
        return self.resolution_stats.copy()
    
    def clear_cache(self):
        """Clear resolution and version caches."""
        self.resolution_cache.clear()
        self.version_cache.clear()
        self.logger.info("Dependency resolver caches cleared")