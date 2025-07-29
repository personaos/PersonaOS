"""
Project Navigator for PersonaOS DevAgent.

Maps and indexes the project structure, tracks dependencies,
and provides code context for development tasks.
"""

import os
import json
import ast
import re
import logging
from typing import Dict, List, Set, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass
from collections import defaultdict


@dataclass
class FileInfo:
    """Information about a project file."""
    path: str
    size: int
    modified: float
    file_type: str
    language: Optional[str] = None
    imports: List[str] = None
    classes: List[str] = None
    functions: List[str] = None
    dependencies: List[str] = None


@dataclass
class ModuleInfo:
    """Information about a Python module."""
    name: str
    path: str
    files: List[str]
    dependencies: Set[str]
    exports: List[str]
    description: Optional[str] = None


class ProjectNavigator:
    """
    Maps and navigates the PersonaOS project structure.
    
    Provides indexing, dependency tracking, and context assistance
    for autonomous development tasks.
    """
    
    def __init__(self, project_root: str, config: Optional[Dict] = None):
        self.project_root = Path(project_root).resolve()
        self.config = config or {}
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Project structure cache
        self.file_index: Dict[str, FileInfo] = {}
        self.module_index: Dict[str, ModuleInfo] = {}
        self.dependency_graph: Dict[str, Set[str]] = defaultdict(set)
        self.reverse_deps: Dict[str, Set[str]] = defaultdict(set)
        
        # File type mappings
        self.language_map = {
            '.py': 'python',
            '.js': 'javascript', 
            '.ts': 'typescript',
            '.jsx': 'javascript',
            '.tsx': 'typescript',
            '.md': 'markdown',
            '.yaml': 'yaml',
            '.yml': 'yaml',
            '.json': 'json',
            '.html': 'html',
            '.css': 'css',
            '.sh': 'shell',
            '.bat': 'batch'
        }
        
        # Ignore patterns
        self.ignore_patterns = {
            '__pycache__', '.git', '.venv', 'venv', 'node_modules',
            '.pytest_cache', '.mypy_cache', 'dist', 'build',
            '*.pyc', '*.pyo', '*.egg-info'
        }
        
        self._build_index()
    
    def _build_index(self) -> None:
        """Build comprehensive project index."""
        self.logger.info(f"Building project index for {self.project_root}")
        
        # Clear existing indexes
        self.file_index.clear()
        self.module_index.clear() 
        self.dependency_graph.clear()
        self.reverse_deps.clear()
        
        # Walk project directory
        for root, dirs, files in os.walk(self.project_root):
            # Filter ignored directories
            dirs[:] = [d for d in dirs if not self._should_ignore(d)]
            
            for file in files:
                if self._should_ignore(file):
                    continue
                    
                file_path = Path(root) / file
                rel_path = file_path.relative_to(self.project_root)
                
                try:
                    file_info = self._analyze_file(file_path, str(rel_path))
                    self.file_index[str(rel_path)] = file_info
                    
                    # Build dependency graph
                    if file_info.dependencies:
                        for dep in file_info.dependencies:
                            self.dependency_graph[str(rel_path)].add(dep)
                            self.reverse_deps[dep].add(str(rel_path))
                            
                except Exception as e:
                    self.logger.warning(f"Failed to analyze {rel_path}: {e}")
        
        # Build module index
        self._build_module_index()
        
        self.logger.info(f"Indexed {len(self.file_index)} files, {len(self.module_index)} modules")
    
    def _should_ignore(self, name: str) -> bool:
        """Check if file/directory should be ignored."""
        for pattern in self.ignore_patterns:
            if pattern.startswith('*'):
                if name.endswith(pattern[1:]):
                    return True
            elif name == pattern:
                return True
        return False
    
    def _analyze_file(self, file_path: Path, rel_path: str) -> FileInfo:
        """Analyze a single file and extract metadata."""
        stat = file_path.stat()
        file_type = file_path.suffix.lower()
        language = self.language_map.get(file_type)
        
        file_info = FileInfo(
            path=rel_path,
            size=stat.st_size,
            modified=stat.st_mtime,
            file_type=file_type,
            language=language,
            imports=[],
            classes=[],
            functions=[],
            dependencies=[]
        )
        
        # Analyze Python files in detail
        if language == 'python':
            try:
                self._analyze_python_file(file_path, file_info)
            except Exception as e:
                self.logger.debug(f"Python analysis failed for {rel_path}: {e}")
        
        # Analyze other file types for imports/dependencies
        elif language in ['javascript', 'typescript']:
            try:
                self._analyze_js_file(file_path, file_info)
            except Exception as e:
                self.logger.debug(f"JS/TS analysis failed for {rel_path}: {e}")
        
        return file_info
    
    def _analyze_python_file(self, file_path: Path, file_info: FileInfo) -> None:
        """Analyze Python file for imports, classes, functions."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for name in node.names:
                        file_info.imports.append(name.name)
                        file_info.dependencies.append(name.name)
                        
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        file_info.imports.append(node.module)
                        file_info.dependencies.append(node.module)
                        
                elif isinstance(node, ast.ClassDef):
                    file_info.classes.append(node.name)
                    
                elif isinstance(node, ast.FunctionDef):
                    file_info.functions.append(node.name)
                    
        except (SyntaxError, UnicodeDecodeError) as e:
            self.logger.debug(f"Could not parse Python file {file_path}: {e}")
    
    def _analyze_js_file(self, file_path: Path, file_info: FileInfo) -> None:
        """Analyze JavaScript/TypeScript file for imports."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Simple regex-based import detection
            import_patterns = [
                r"import\s+.*?from\s+['\"]([^'\"]+)['\"]",
                r"require\s*\(\s*['\"]([^'\"]+)['\"]\s*\)",
                r"import\s*\(\s*['\"]([^'\"]+)['\"]\s*\)"
            ]
            
            for pattern in import_patterns:
                matches = re.findall(pattern, content)
                for match in matches:
                    file_info.imports.append(match)
                    file_info.dependencies.append(match)
                    
        except UnicodeDecodeError as e:
            self.logger.debug(f"Could not read JS/TS file {file_path}: {e}")
    
    def _build_module_index(self) -> None:
        """Build index of Python modules."""
        python_files = {path: info for path, info in self.file_index.items() 
                       if info.language == 'python'}
        
        # Group files by module (directory structure)
        module_files = defaultdict(list)
        
        for file_path, file_info in python_files.items():
            path_parts = Path(file_path).parts
            if len(path_parts) > 1:
                module_name = '.'.join(path_parts[:-1]) if path_parts[0] != '__init__.py' else path_parts[0]
                module_files[module_name].append(file_path)
            else:
                # Root level file
                module_name = Path(file_path).stem
                module_files[module_name].append(file_path)
        
        # Create module info objects
        for module_name, files in module_files.items():
            dependencies = set()
            exports = []
            
            for file_path in files:
                file_info = self.file_index[file_path]
                dependencies.update(file_info.dependencies or [])
                exports.extend(file_info.classes or [])
                exports.extend(file_info.functions or [])
            
            # Try to get module description from docstring
            description = self._get_module_description(files)
            
            self.module_index[module_name] = ModuleInfo(
                name=module_name,
                path=str(Path(files[0]).parent) if files else '',
                files=files,
                dependencies=dependencies,
                exports=exports,
                description=description
            )
    
    def _get_module_description(self, files: List[str]) -> Optional[str]:
        """Extract module description from __init__.py or main file."""
        init_file = None
        main_file = None
        
        for file_path in files:
            if Path(file_path).name == '__init__.py':
                init_file = file_path
                break
            elif not main_file:
                main_file = file_path
        
        target_file = init_file or main_file
        if not target_file:
            return None
        
        try:
            full_path = self.project_root / target_file
            with open(full_path, 'r', encoding='utf-8') as f:
                tree = ast.parse(f.read())
            
            # Look for module-level docstring
            if (tree.body and isinstance(tree.body[0], ast.Expr) 
                and isinstance(tree.body[0].value, ast.Str)):
                return tree.body[0].value.s.strip()
                
        except Exception:
            pass
        
        return None
    
    def get_file_info(self, file_path: str) -> Optional[FileInfo]:
        """Get information about a specific file."""
        return self.file_index.get(file_path)
    
    def get_module_info(self, module_name: str) -> Optional[ModuleInfo]:
        """Get information about a specific module."""
        return self.module_index.get(module_name)
    
    def find_files(self, pattern: str = None, language: str = None, 
                   contains: str = None) -> List[FileInfo]:
        """Find files matching criteria."""
        results = []
        
        for file_path, file_info in self.file_index.items():
            # Pattern matching
            if pattern and not re.search(pattern, file_path, re.IGNORECASE):
                continue
            
            # Language filter
            if language and file_info.language != language:
                continue
            
            # Content search (basic)
            if contains:
                try:
                    full_path = self.project_root / file_path
                    with open(full_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    if contains.lower() not in content.lower():
                        continue
                except Exception:
                    continue
            
            results.append(file_info)
        
        return results
    
    def get_dependencies(self, file_path: str) -> Set[str]:
        """Get direct dependencies of a file."""
        return self.dependency_graph.get(file_path, set())
    
    def get_dependents(self, file_path: str) -> Set[str]:
        """Get files that depend on the given file."""
        return self.reverse_deps.get(file_path, set())
    
    def get_related_files(self, file_path: str, depth: int = 1) -> Set[str]:
        """Get files related to the given file through dependencies."""
        related = set()
        to_visit = {file_path}
        visited = set()
        
        for _ in range(depth):
            next_visit = set()
            for current in to_visit:
                if current in visited:
                    continue
                visited.add(current)
                
                # Add dependencies and dependents
                deps = self.get_dependencies(current)
                dependents = self.get_dependents(current)
                
                related.update(deps)
                related.update(dependents)
                next_visit.update(deps)
                next_visit.update(dependents)
            
            to_visit = next_visit - visited
        
        related.discard(file_path)  # Remove original file
        return related
    
    def get_context_for_file(self, file_path: str, max_files: int = 10) -> List[str]:
        """Get relevant context files for development work."""
        if file_path not in self.file_index:
            return []
        
        # Start with direct dependencies and dependents
        context_files = list(self.get_related_files(file_path, depth=1))
        
        # Add files from same module
        file_parts = Path(file_path).parts
        if len(file_parts) > 1:
            module_dir = str(Path(*file_parts[:-1]))
            same_module = [path for path in self.file_index.keys() 
                          if path.startswith(module_dir) and path != file_path]
            context_files.extend(same_module[:3])  # Limit same-module files
        
        # Sort by relevance (dependency count, modification time, etc.)
        def relevance_score(path: str) -> float:
            info = self.file_index.get(path)
            if not info:
                return 0
            
            score = 0
            # Prefer recently modified files
            score += info.modified / 1000000  
            # Prefer files with more connections
            score += len(self.get_dependencies(path)) * 10
            score += len(self.get_dependents(path)) * 10
            
            return score
        
        context_files.sort(key=relevance_score, reverse=True)
        return context_files[:max_files]
    
    def get_project_structure(self) -> Dict:
        """Get hierarchical project structure."""
        structure = {}
        
        for file_path in self.file_index.keys():
            parts = Path(file_path).parts
            current = structure
            
            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]
            
            # Add file info
            file_info = self.file_index[file_path]
            current[parts[-1]] = {
                'type': 'file',
                'language': file_info.language,
                'size': file_info.size,
                'functions': len(file_info.functions or []),
                'classes': len(file_info.classes or [])
            }
        
        return structure
    
    def refresh_index(self) -> None:
        """Refresh the project index (rescan files)."""
        self._build_index()
    
    def get_stats(self) -> Dict:
        """Get project statistics."""
        lang_stats = defaultdict(int)
        total_size = 0
        
        for file_info in self.file_index.values():
            if file_info.language:
                lang_stats[file_info.language] += 1
            total_size += file_info.size
        
        return {
            'total_files': len(self.file_index),
            'total_modules': len(self.module_index),
            'total_size': total_size,
            'languages': dict(lang_stats),
            'dependencies': len(self.dependency_graph)
        }