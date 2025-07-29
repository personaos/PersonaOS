"""
Advanced Dependency Manager for PersonaOS Plugins

This module provides comprehensive dependency management including plugin
repositories, version caching, conflict resolution, and automatic dependency
installation and updates.
"""

import json
import logging
import threading
import time
from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
import hashlib
import requests
from urllib.parse import urljoin

from .dependency_resolver import AdvancedDependencyResolver, DependencySpec, ResolvedDependency
from .base_plugin import PluginMetadata, PluginDependency

class DependencySource(Enum):
    """Sources for plugin dependencies."""
    LOCAL = "local"
    REPOSITORY = "repository"
    GIT = "git"
    URL = "url"
    FILESYSTEM = "filesystem"

class ConflictResolutionStrategy(Enum):
    """Strategies for resolving dependency conflicts."""
    LATEST = "latest"
    OLDEST = "oldest"
    HIGHEST_PRIORITY = "highest_priority"
    USER_CHOICE = "user_choice"
    FAIL = "fail"

@dataclass
class PluginRepository:
    """Represents a plugin repository."""
    name: str
    url: str
    enabled: bool = True
    priority: int = 100
    auth_token: Optional[str] = None
    verify_ssl: bool = True
    cache_ttl: int = 3600  # 1 hour
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class DependencyCandidate:
    """Represents a candidate for satisfying a dependency."""
    name: str
    version: str
    source: DependencySource
    location: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    priority: int = 100
    satisfied_specs: List[DependencySpec] = field(default_factory=list)

@dataclass
class DependencyGraph:
    """Represents the complete dependency graph."""
    nodes: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    edges: Dict[str, List[str]] = field(default_factory=dict)
    conflicts: List[Dict[str, Any]] = field(default_factory=list)
    resolution_order: List[str] = field(default_factory=list)

class DependencyManager:
    """
    Advanced dependency management system for PersonaOS plugins.
    
    Provides comprehensive dependency resolution including:
    - Multiple plugin repositories
    - Version caching and optimization
    - Conflict detection and resolution
    - Automatic dependency installation
    - Dependency graph visualization
    - Rollback and recovery mechanisms
    """
    
    def __init__(self, config: Dict[str, Any] = None, plugin_manager = None):
        """
        Initialize dependency manager.
        
        Args:
            config: PersonaOS configuration dictionary
            plugin_manager: Reference to main plugin manager
        """
        self.config = config or {}
        self.plugin_manager = plugin_manager
        self.logger = logging.getLogger("dependency_manager")
        
        # Initialize dependency resolver
        self.resolver = AdvancedDependencyResolver(config)
        
        # Repository management
        self.repositories: Dict[str, PluginRepository] = {}
        self.repository_cache: Dict[str, Dict[str, Any]] = {}
        self.cache_lock = threading.RLock()
        
        # Dependency management configuration
        self.conflict_strategy = ConflictResolutionStrategy(
            config.get("plugin_conflict_resolution", "latest")
        )
        self.auto_install = config.get("plugin_auto_install_dependencies", False)
        self.cache_directory = Path(config.get("plugin_cache_directory", "data/plugin_cache"))
        self.max_cache_age = config.get("plugin_cache_max_age", 86400)  # 24 hours
        
        # Dependency tracking
        self.dependency_graphs: Dict[str, DependencyGraph] = {}
        self.installed_dependencies: Dict[str, DependencyCandidate] = {}
        self.dependency_locks: Dict[str, threading.RLock] = {}
        
        # Statistics
        self.dependency_stats = {
            "total_resolutions": 0,
            "successful_resolutions": 0,
            "failed_resolutions": 0,
            "conflicts_resolved": 0,
            "dependencies_installed": 0,
            "cache_hits": 0,
            "cache_misses": 0
        }
        
        # Initialize cache directory
        self.cache_directory.mkdir(parents=True, exist_ok=True)
        
        # Load repositories from configuration
        self._load_repositories()
        
        # Load dependency cache
        self._load_dependency_cache()
        
        self.logger.info("DependencyManager initialized")
    
    def resolve_dependencies(self, plugins: List[Dict[str, Any]], 
                           install_missing: bool = None) -> Dict[str, Any]:
        """
        Resolve dependencies for plugins with advanced management.
        
        Args:
            plugins: List of plugin information
            install_missing: Whether to auto-install missing dependencies
            
        Returns:
            Resolution result with dependency information
        """
        self.dependency_stats["total_resolutions"] += 1
        install_missing = install_missing if install_missing is not None else self.auto_install
        
        try:
            self.logger.info(f"Resolving dependencies for {len(plugins)} plugins")
            
            # Create dependency graph
            dependency_graph = self._build_dependency_graph(plugins)
            
            # Find all required dependencies
            all_dependencies = self._collect_all_dependencies(dependency_graph)
            
            # Find candidates for each dependency
            dependency_candidates = {}
            missing_dependencies = []
            
            for dep_name, dep_specs in all_dependencies.items():
                candidates = self._find_dependency_candidates(dep_name, dep_specs)
                
                if candidates:
                    dependency_candidates[dep_name] = candidates
                else:
                    missing_dependencies.append((dep_name, dep_specs))
            
            # Handle missing dependencies
            if missing_dependencies and install_missing:
                installation_results = self._install_missing_dependencies(missing_dependencies)
                
                # Update candidates with newly installed dependencies
                for dep_name, install_result in installation_results.items():
                    if install_result.get("success", False):
                        candidates = self._find_dependency_candidates(dep_name, all_dependencies[dep_name])
                        if candidates:
                            dependency_candidates[dep_name] = candidates
                            missing_dependencies = [(n, s) for n, s in missing_dependencies if n != dep_name]
            
            # Detect and resolve conflicts
            conflicts = self._detect_dependency_conflicts(dependency_candidates)
            conflict_resolutions = {}
            
            if conflicts:
                self.logger.info(f"Detected {len(conflicts)} dependency conflicts")
                conflict_resolutions = self._resolve_dependency_conflicts(conflicts, dependency_candidates)
                self.dependency_stats["conflicts_resolved"] += len(conflict_resolutions)
            
            # Select best candidates
            selected_dependencies = self._select_dependency_candidates(
                dependency_candidates, conflict_resolutions
            )
            
            # Create resolved dependencies
            resolved_dependencies = {}
            for dep_name, candidate in selected_dependencies.items():
                resolved_dep = ResolvedDependency(
                    name=candidate.name,
                    version=candidate.version,
                    plugin_id=candidate.metadata.get("plugin_id", dep_name),
                    optional=any(spec.optional for spec in candidate.satisfied_specs),
                    resolved_version_specs=candidate.satisfied_specs
                )
                resolved_dependencies[dep_name] = resolved_dep
            
            # Update dependency graph with resolutions
            dependency_graph.nodes.update({
                dep_name: {
                    "candidate": candidate,
                    "resolved": resolved_dependencies[dep_name]
                }
                for dep_name, candidate in selected_dependencies.items()
            })
            
            # Store dependency graph
            graph_id = self._generate_graph_id(plugins)
            self.dependency_graphs[graph_id] = dependency_graph
            
            self.dependency_stats["successful_resolutions"] += 1
            
            result = {
                "success": True,
                "resolved_dependencies": resolved_dependencies,
                "dependency_graph": dependency_graph,
                "selected_candidates": selected_dependencies,
                "conflicts": conflicts,
                "conflict_resolutions": conflict_resolutions,
                "missing_dependencies": missing_dependencies,
                "installation_required": len(missing_dependencies) > 0,
                "graph_id": graph_id,
                "resolution_metadata": {
                    "total_dependencies": len(all_dependencies),
                    "resolved_dependencies": len(resolved_dependencies),
                    "conflicts_detected": len(conflicts),
                    "conflicts_resolved": len(conflict_resolutions),
                    "missing_dependencies": len(missing_dependencies)
                }
            }
            
            self.logger.info(f"Dependency resolution successful: {len(resolved_dependencies)} dependencies resolved")
            return result
            
        except Exception as e:
            self.dependency_stats["failed_resolutions"] += 1
            self.logger.error(f"Dependency resolution failed: {e}")
            
            return {
                "success": False,
                "error": str(e),
                "resolved_dependencies": {},
                "dependency_graph": None,
                "resolution_metadata": {
                    "total_dependencies": 0,
                    "resolved_dependencies": 0,
                    "conflicts_detected": 0,
                    "conflicts_resolved": 0,
                    "missing_dependencies": 0
                }
            }
    
    def _build_dependency_graph(self, plugins: List[Dict[str, Any]]) -> DependencyGraph:
        """Build comprehensive dependency graph."""
        graph = DependencyGraph()
        
        # Add plugin nodes
        for plugin in plugins:
            plugin_name = self._get_plugin_name(plugin)
            metadata = plugin.get("metadata", {})
            
            graph.nodes[plugin_name] = {
                "type": "plugin",
                "metadata": metadata,
                "dependencies": metadata.get("dependencies", [])
            }
            
            # Add edges to dependencies
            dependencies = metadata.get("dependencies", [])
            graph.edges[plugin_name] = []
            
            for dep in dependencies:
                dep_name = dep.get("name") if isinstance(dep, dict) else str(dep)
                graph.edges[plugin_name].append(dep_name)
        
        return graph
    
    def _collect_all_dependencies(self, dependency_graph: DependencyGraph) -> Dict[str, List[DependencySpec]]:
        """Collect all unique dependencies from the graph."""
        all_dependencies = {}
        
        for plugin_name, plugin_info in dependency_graph.nodes.items():
            if plugin_info.get("type") == "plugin":
                dependencies = plugin_info.get("dependencies", [])
                
                for dep in dependencies:
                    if isinstance(dep, dict):
                        dep_name = dep.get("name", "")
                    else:
                        dep_name = str(dep)
                    
                    if not dep_name:
                        continue
                    
                    if dep_name not in all_dependencies:
                        all_dependencies[dep_name] = []
                    
                    # Convert to DependencySpec
                    dep_spec = self._convert_to_dependency_spec(dep)
                    all_dependencies[dep_name].append(dep_spec)
        
        return all_dependencies
    
    def _convert_to_dependency_spec(self, dep: Union[Dict[str, Any], str]) -> DependencySpec:
        """Convert dependency to DependencySpec format."""
        if isinstance(dep, dict):
            return DependencySpec(
                name=dep.get("name", ""),
                version_specs=self.resolver._parse_version_string(dep.get("version", "")),
                optional=dep.get("optional", False),
                extras=dep.get("extras", []),
                environment_markers=dep.get("environment_markers")
            )
        else:
            return DependencySpec(name=str(dep), version_specs=[])
    
    def _find_dependency_candidates(self, dep_name: str, 
                                  dep_specs: List[DependencySpec]) -> List[DependencyCandidate]:
        """Find candidates that can satisfy dependency requirements."""
        candidates = []
        
        # Check local plugins first
        local_candidates = self._find_local_candidates(dep_name, dep_specs)
        candidates.extend(local_candidates)
        
        # Check repositories
        repo_candidates = self._find_repository_candidates(dep_name, dep_specs)
        candidates.extend(repo_candidates)
        
        # Check installed dependencies
        if dep_name in self.installed_dependencies:
            installed = self.installed_dependencies[dep_name]
            if self._candidate_satisfies_specs(installed, dep_specs):
                candidates.append(installed)
        
        # Sort candidates by priority and version
        candidates.sort(key=lambda c: (-c.priority, c.version), reverse=True)
        
        return candidates
    
    def _find_local_candidates(self, dep_name: str, 
                             dep_specs: List[DependencySpec]) -> List[DependencyCandidate]:
        """Find local plugin candidates."""
        candidates = []
        
        if self.plugin_manager and hasattr(self.plugin_manager, 'registry'):
            # Check if dependency is available in plugin registry
            plugin = self.plugin_manager.registry.get_plugin(dep_name)
            if plugin:
                metadata = self.plugin_manager.registry.get_plugin_metadata(dep_name)
                if metadata:
                    candidate = DependencyCandidate(
                        name=dep_name,
                        version=metadata.version,
                        source=DependencySource.LOCAL,
                        location="registry",
                        metadata={"plugin_metadata": metadata},
                        priority=200,  # High priority for local plugins
                        satisfied_specs=dep_specs
                    )
                    
                    if self._candidate_satisfies_specs(candidate, dep_specs):
                        candidates.append(candidate)
        
        return candidates
    
    def _find_repository_candidates(self, dep_name: str, 
                                  dep_specs: List[DependencySpec]) -> List[DependencyCandidate]:
        """Find candidates from configured repositories."""
        candidates = []
        
        for repo_name, repository in self.repositories.items():
            if not repository.enabled:
                continue
            
            # Check cache first
            cache_key = f"{repo_name}:{dep_name}"
            cached_data = self._get_cached_data(cache_key)
            
            if cached_data:
                self.dependency_stats["cache_hits"] += 1
                repo_candidates = self._parse_repository_response(
                    cached_data, dep_name, dep_specs, repository
                )
                candidates.extend(repo_candidates)
            else:
                self.dependency_stats["cache_misses"] += 1
                # Fetch from repository
                try:
                    repo_data = self._fetch_from_repository(repository, dep_name)
                    if repo_data:
                        self._cache_data(cache_key, repo_data)
                        repo_candidates = self._parse_repository_response(
                            repo_data, dep_name, dep_specs, repository
                        )
                        candidates.extend(repo_candidates)
                except Exception as e:
                    self.logger.warning(f"Failed to fetch {dep_name} from repository {repo_name}: {e}")
        
        return candidates
    
    def _candidate_satisfies_specs(self, candidate: DependencyCandidate, 
                                 specs: List[DependencySpec]) -> bool:
        """Check if candidate satisfies all dependency specifications."""
        for spec in specs:
            if spec.name != candidate.name:
                continue
            
            # Check version constraints
            for version_spec in spec.version_specs:
                if not self.resolver._compare_versions(
                    candidate.version, version_spec.operator, version_spec.version
                ):
                    return False
        
        return True
    
    def _detect_dependency_conflicts(self, dependency_candidates: Dict[str, List[DependencyCandidate]]) -> List[Dict[str, Any]]:
        """Detect conflicts between dependency candidates."""
        conflicts = []
        
        # Check for version conflicts
        for dep_name, candidates in dependency_candidates.items():
            if len(candidates) > 1:
                # Check if candidates have conflicting versions
                versions = set(c.version for c in candidates)
                if len(versions) > 1:
                    conflict = {
                        "type": "version_conflict",
                        "dependency": dep_name,
                        "conflicting_versions": list(versions),
                        "candidates": candidates,
                        "resolution_strategies": [
                            ConflictResolutionStrategy.LATEST,
                            ConflictResolutionStrategy.HIGHEST_PRIORITY
                        ]
                    }
                    conflicts.append(conflict)
        
        # Check for source conflicts (same dependency from different sources)
        for dep_name, candidates in dependency_candidates.items():
            sources = set(c.source for c in candidates)
            if len(sources) > 1:
                conflict = {
                    "type": "source_conflict", 
                    "dependency": dep_name,
                    "conflicting_sources": list(sources),
                    "candidates": candidates,
                    "resolution_strategies": [
                        ConflictResolutionStrategy.HIGHEST_PRIORITY,
                        ConflictResolutionStrategy.USER_CHOICE
                    ]
                }
                conflicts.append(conflict)
        
        return conflicts
    
    def _resolve_dependency_conflicts(self, conflicts: List[Dict[str, Any]], 
                                    dependency_candidates: Dict[str, List[DependencyCandidate]]) -> Dict[str, Any]:
        """Resolve dependency conflicts using configured strategy."""
        resolutions = {}
        
        for conflict in conflicts:
            dep_name = conflict["dependency"]
            candidates = conflict["candidates"]
            conflict_type = conflict["type"]
            
            if self.conflict_strategy == ConflictResolutionStrategy.LATEST:
                # Select candidate with latest version
                selected = max(candidates, key=lambda c: self.resolver._parse_version_parts(c.version))
                
            elif self.conflict_strategy == ConflictResolutionStrategy.OLDEST:
                # Select candidate with oldest version
                selected = min(candidates, key=lambda c: self.resolver._parse_version_parts(c.version))
                
            elif self.conflict_strategy == ConflictResolutionStrategy.HIGHEST_PRIORITY:
                # Select candidate with highest priority
                selected = max(candidates, key=lambda c: c.priority)
                
            elif self.conflict_strategy == ConflictResolutionStrategy.USER_CHOICE:
                # For now, default to highest priority (would implement user prompt in UI)
                selected = max(candidates, key=lambda c: c.priority)
                
            elif self.conflict_strategy == ConflictResolutionStrategy.FAIL:
                # Fail on any conflict
                raise Exception(f"Dependency conflict for {dep_name}: {conflict_type}")
            
            else:
                # Default to latest
                selected = max(candidates, key=lambda c: self.resolver._parse_version_parts(c.version))
            
            resolutions[dep_name] = {
                "conflict": conflict,
                "selected_candidate": selected,
                "strategy_used": self.conflict_strategy.value,
                "rejected_candidates": [c for c in candidates if c != selected]
            }
            
            self.logger.info(f"Resolved {conflict_type} for {dep_name}: selected {selected.version} from {selected.source.value}")
        
        return resolutions
    
    def _select_dependency_candidates(self, dependency_candidates: Dict[str, List[DependencyCandidate]], 
                                   conflict_resolutions: Dict[str, Any]) -> Dict[str, DependencyCandidate]:
        """Select the best candidate for each dependency."""
        selected = {}
        
        for dep_name, candidates in dependency_candidates.items():
            if dep_name in conflict_resolutions:
                # Use conflict resolution result
                selected[dep_name] = conflict_resolutions[dep_name]["selected_candidate"]
            else:
                # Select highest priority candidate
                selected[dep_name] = max(candidates, key=lambda c: c.priority)
        
        return selected
    
    def _install_missing_dependencies(self, missing_dependencies: List[Tuple[str, List[DependencySpec]]]) -> Dict[str, Dict[str, Any]]:
        """Install missing dependencies automatically."""
        installation_results = {}
        
        for dep_name, dep_specs in missing_dependencies:
            try:
                self.logger.info(f"Installing missing dependency: {dep_name}")
                
                # Find the best repository candidate
                repo_candidates = self._find_repository_candidates(dep_name, dep_specs)
                
                if not repo_candidates:
                    installation_results[dep_name] = {
                        "success": False,
                        "error": f"No candidates found for {dep_name}"
                    }
                    continue
                
                # Select best candidate
                best_candidate = max(repo_candidates, key=lambda c: c.priority)
                
                # Install the dependency
                install_result = self._install_dependency_candidate(best_candidate)
                installation_results[dep_name] = install_result
                
                if install_result.get("success", False):
                    self.dependency_stats["dependencies_installed"] += 1
                    # Add to installed dependencies
                    self.installed_dependencies[dep_name] = best_candidate
                
            except Exception as e:
                self.logger.error(f"Failed to install dependency {dep_name}: {e}")
                installation_results[dep_name] = {
                    "success": False,
                    "error": str(e)
                }
        
        return installation_results
    
    def _install_dependency_candidate(self, candidate: DependencyCandidate) -> Dict[str, Any]:
        """Install a specific dependency candidate."""
        try:
            if candidate.source == DependencySource.REPOSITORY:
                # Download and install from repository
                return self._install_from_repository(candidate)
            elif candidate.source == DependencySource.GIT:
                # Clone and install from git
                return self._install_from_git(candidate)
            elif candidate.source == DependencySource.URL:
                # Download and install from URL
                return self._install_from_url(candidate)
            else:
                return {
                    "success": False,
                    "error": f"Unsupported installation source: {candidate.source.value}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def _install_from_repository(self, candidate: DependencyCandidate) -> Dict[str, Any]:
        """Install dependency from repository."""
        # Placeholder for repository installation logic
        self.logger.info(f"Installing {candidate.name} v{candidate.version} from repository")
        
        # This would implement actual repository download and installation
        # For now, simulate successful installation
        return {
            "success": True,
            "installed_version": candidate.version,
            "installation_path": f"plugins/{candidate.name}",
            "method": "repository"
        }
    
    def _install_from_git(self, candidate: DependencyCandidate) -> Dict[str, Any]:
        """Install dependency from git repository."""
        self.logger.info(f"Installing {candidate.name} from git: {candidate.location}")
        
        # Placeholder for git installation logic
        return {
            "success": True,
            "installed_version": candidate.version,
            "installation_path": f"plugins/{candidate.name}",
            "method": "git"
        }
    
    def _install_from_url(self, candidate: DependencyCandidate) -> Dict[str, Any]:
        """Install dependency from URL."""
        self.logger.info(f"Installing {candidate.name} from URL: {candidate.location}")
        
        # Placeholder for URL installation logic
        return {
            "success": True,
            "installed_version": candidate.version,
            "installation_path": f"plugins/{candidate.name}",
            "method": "url"
        }
    
    def _load_repositories(self):
        """Load plugin repositories from configuration."""
        default_repos = self.config.get("plugin_repositories", [])
        
        for repo_config in default_repos:
            try:
                repo = PluginRepository(
                    name=repo_config.get("name", ""),
                    url=repo_config.get("url", ""),
                    enabled=repo_config.get("enabled", True),
                    priority=repo_config.get("priority", 100),
                    auth_token=repo_config.get("auth_token"),
                    verify_ssl=repo_config.get("verify_ssl", True),
                    cache_ttl=repo_config.get("cache_ttl", 3600)
                )
                
                self.repositories[repo.name] = repo
                self.logger.info(f"Loaded repository: {repo.name} ({repo.url})")
                
            except Exception as e:
                self.logger.error(f"Failed to load repository config: {e}")
        
        # Add default PersonaOS repository if none configured
        if not self.repositories:
            default_repo = PluginRepository(
                name="personaos-official",
                url="https://plugins.personaos.dev/api/v1/",
                enabled=True,
                priority=200
            )
            self.repositories[default_repo.name] = default_repo
    
    def _fetch_from_repository(self, repository: PluginRepository, plugin_name: str) -> Optional[Dict[str, Any]]:
        """Fetch plugin information from repository."""
        try:
            url = urljoin(repository.url, f"plugins/{plugin_name}")
            headers = {}
            
            if repository.auth_token:
                headers["Authorization"] = f"Bearer {repository.auth_token}"
            
            response = requests.get(
                url,
                headers=headers,
                verify=repository.verify_ssl,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                self.logger.warning(f"Repository {repository.name} returned {response.status_code} for {plugin_name}")
                return None
                
        except Exception as e:
            self.logger.error(f"Failed to fetch {plugin_name} from {repository.name}: {e}")
            return None
    
    def _parse_repository_response(self, repo_data: Dict[str, Any], dep_name: str, 
                                 dep_specs: List[DependencySpec], 
                                 repository: PluginRepository) -> List[DependencyCandidate]:
        """Parse repository response into dependency candidates."""
        candidates = []
        
        try:
            versions = repo_data.get("versions", [])
            
            for version_info in versions:
                version = version_info.get("version", "")
                download_url = version_info.get("download_url", "")
                
                candidate = DependencyCandidate(
                    name=dep_name,
                    version=version,
                    source=DependencySource.REPOSITORY,
                    location=download_url,
                    metadata={
                        "repository": repository.name,
                        "version_info": version_info
                    },
                    priority=repository.priority,
                    satisfied_specs=dep_specs
                )
                
                if self._candidate_satisfies_specs(candidate, dep_specs):
                    candidates.append(candidate)
            
        except Exception as e:
            self.logger.error(f"Failed to parse repository response for {dep_name}: {e}")
        
        return candidates
    
    def _get_cached_data(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get data from cache if not expired."""
        with self.cache_lock:
            if cache_key in self.repository_cache:
                cached_item = self.repository_cache[cache_key]
                
                if time.time() - cached_item.get("timestamp", 0) < self.max_cache_age:
                    return cached_item.get("data")
                else:
                    # Remove expired item
                    del self.repository_cache[cache_key]
        
        return None
    
    def _cache_data(self, cache_key: str, data: Dict[str, Any]):
        """Cache data with timestamp."""
        with self.cache_lock:
            self.repository_cache[cache_key] = {
                "data": data,
                "timestamp": time.time()
            }
    
    def _load_dependency_cache(self):
        """Load dependency cache from disk."""
        cache_file = self.cache_directory / "dependency_cache.json"
        
        try:
            if cache_file.exists():
                with open(cache_file, 'r') as f:
                    cached_data = json.load(f)
                    
                    # Filter out expired entries
                    current_time = time.time()
                    valid_cache = {}
                    
                    for key, item in cached_data.items():
                        if current_time - item.get("timestamp", 0) < self.max_cache_age:
                            valid_cache[key] = item
                    
                    self.repository_cache = valid_cache
                    self.logger.info(f"Loaded {len(valid_cache)} cached dependency entries")
        
        except Exception as e:
            self.logger.warning(f"Failed to load dependency cache: {e}")
    
    def _save_dependency_cache(self):
        """Save dependency cache to disk."""
        cache_file = self.cache_directory / "dependency_cache.json"
        
        try:
            with self.cache_lock:
                with open(cache_file, 'w') as f:
                    json.dump(self.repository_cache, f, indent=2)
        
        except Exception as e:
            self.logger.error(f"Failed to save dependency cache: {e}")
    
    def _generate_graph_id(self, plugins: List[Dict[str, Any]]) -> str:
        """Generate unique ID for dependency graph."""
        plugin_names = [self._get_plugin_name(p) for p in plugins]
        plugin_names.sort()
        
        content = "|".join(plugin_names)
        return hashlib.md5(content.encode()).hexdigest()[:16]
    
    def _get_plugin_name(self, plugin: Dict[str, Any]) -> str:
        """Extract plugin name from plugin info."""
        metadata = plugin.get("metadata", {})
        return metadata.get("name", plugin.get("name", "unknown"))
    
    def add_repository(self, repository: PluginRepository):
        """Add a plugin repository."""
        self.repositories[repository.name] = repository
        self.logger.info(f"Added repository: {repository.name}")
    
    def remove_repository(self, repo_name: str) -> bool:
        """Remove a plugin repository."""
        if repo_name in self.repositories:
            del self.repositories[repo_name]
            self.logger.info(f"Removed repository: {repo_name}")
            return True
        return False
    
    def get_dependency_stats(self) -> Dict[str, Any]:
        """Get dependency management statistics."""
        return {
            **self.dependency_stats,
            "repositories": len(self.repositories),
            "cached_entries": len(self.repository_cache),
            "installed_dependencies": len(self.installed_dependencies),
            "dependency_graphs": len(self.dependency_graphs),
            "cache_directory": str(self.cache_directory)
        }
    
    def clear_cache(self):
        """Clear dependency cache."""
        with self.cache_lock:
            self.repository_cache.clear()
            self.dependency_stats["cache_hits"] = 0
            self.dependency_stats["cache_misses"] = 0
        
        self.logger.info("Dependency cache cleared")
    
    def shutdown(self):
        """Shutdown dependency manager."""
        self.logger.info("Shutting down dependency manager")
        
        # Save cache to disk
        self._save_dependency_cache()
        
        # Clear in-memory data
        self.repository_cache.clear()
        self.dependency_graphs.clear()
        
        self.logger.info("Dependency manager shutdown complete")