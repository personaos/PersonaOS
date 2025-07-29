"""
Hot Reload Manager for PersonaOS Plugins

This module provides hot-reloading capabilities for plugins during development,
monitoring file changes and automatically reloading plugins when modifications
are detected.
"""

import os
import time
import logging
import threading
from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Callable
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent, FileCreatedEvent, FileDeletedEvent

class PluginFileChangeHandler(FileSystemEventHandler):
    """Handles file system events for plugin files."""
    
    def __init__(self, hot_reload_manager):
        """
        Initialize file change handler.
        
        Args:
            hot_reload_manager: Reference to HotReloadManager instance
        """
        super().__init__()
        self.hot_reload_manager = hot_reload_manager
        self.logger = logging.getLogger("plugin_file_change_handler")
    
    def on_modified(self, event):
        """Handle file modification events."""
        if not event.is_directory:
            self.hot_reload_manager._handle_file_change(event.src_path, "modified")
    
    def on_created(self, event):
        """Handle file creation events."""
        if not event.is_directory:
            self.hot_reload_manager._handle_file_change(event.src_path, "created")
    
    def on_deleted(self, event):
        """Handle file deletion events."""
        if not event.is_directory:
            self.hot_reload_manager._handle_file_change(event.src_path, "deleted")

class HotReloadManager:
    """
    Manages hot-reloading of plugins during development.
    
    Monitors plugin directories for file changes and automatically
    reloads affected plugins when modifications are detected.
    """
    
    def __init__(self, config: Dict[str, Any] = None, plugin_manager = None):
        """
        Initialize hot reload manager.
        
        Args:
            config: PersonaOS configuration dictionary
            plugin_manager: Reference to main plugin manager
        """
        self.config = config or {}
        self.plugin_manager = plugin_manager
        self.logger = logging.getLogger("hot_reload_manager")
        
        # Hot reload configuration
        self.enabled = config.get("plugin_hot_reload", False)
        self.reload_delay = config.get("plugin_reload_delay", 1.0)  # Delay before reload
        self.watch_extensions = config.get("plugin_watch_extensions", [".py", ".yaml", ".yml", ".json"])
        self.ignore_patterns = config.get("plugin_ignore_patterns", ["__pycache__", ".pyc", ".git"])
        
        # File watching state
        self.observer = None
        self.watched_directories: Set[Path] = set()
        self.plugin_file_mappings: Dict[str, str] = {}  # file_path -> plugin_id
        self.pending_reloads: Dict[str, float] = {}  # plugin_id -> scheduled_time
        
        # Reload management
        self.reload_queue: Dict[str, Dict[str, Any]] = {}  # plugin_id -> reload_info
        self.reload_thread = None
        self.reload_thread_active = False
        self.shutdown_event = threading.Event()
        
        # Statistics
        self.reload_stats = {
            "total_file_changes": 0,
            "successful_reloads": 0,
            "failed_reloads": 0,
            "ignored_changes": 0
        }
        
        # Event handlers
        self.event_handlers: Dict[str, List[Callable]] = {
            "file_changed": [],
            "reload_started": [],
            "reload_completed": [],
            "reload_failed": []
        }
        
        # Thread safety
        self._reload_lock = threading.RLock()
        
        self.logger.info(f"HotReloadManager initialized (enabled: {self.enabled})")
    
    def start_watching(self, directories: List[Path] = None) -> bool:
        """
        Start watching plugin directories for changes.
        
        Args:
            directories: Optional list of directories to watch
            
        Returns:
            True if watching started successfully, False otherwise
        """
        if not self.enabled:
            self.logger.info("Hot reload is disabled")
            return False
        
        if self.observer and self.observer.is_alive():
            self.logger.warning("File watching is already active")
            return True
        
        try:
            self.logger.info("Starting hot reload file watching")
            
            # Use provided directories or get from plugin manager
            if directories:
                watch_dirs = directories
            elif self.plugin_manager:
                watch_dirs = self.plugin_manager.get_plugin_directories()
            else:
                self.logger.error("No directories to watch")
                return False
            
            # Initialize observer
            self.observer = Observer()
            event_handler = PluginFileChangeHandler(self)
            
            # Add watches for each directory
            for directory in watch_dirs:
                if directory.exists() and directory.is_dir():
                    self.observer.schedule(event_handler, str(directory), recursive=True)
                    self.watched_directories.add(directory)
                    self.logger.info(f"Watching directory: {directory}")
                else:
                    self.logger.warning(f"Directory does not exist: {directory}")
            
            # Start observer
            self.observer.start()
            
            # Start reload processing thread
            self._start_reload_thread()
            
            # Build initial file mappings
            self._build_file_mappings()
            
            self.logger.info(f"Hot reload watching started for {len(self.watched_directories)} directories")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start hot reload watching: {e}")
            return False
    
    def stop_watching(self) -> bool:
        """
        Stop watching plugin directories for changes.
        
        Returns:
            True if watching stopped successfully, False otherwise
        """
        try:
            self.logger.info("Stopping hot reload file watching")
            
            # Stop observer
            if self.observer and self.observer.is_alive():
                self.observer.stop()
                self.observer.join(timeout=5)
                self.observer = None
            
            # Stop reload thread
            self._stop_reload_thread()
            
            # Clear state
            self.watched_directories.clear()
            self.plugin_file_mappings.clear()
            self.pending_reloads.clear()
            self.reload_queue.clear()
            
            self.logger.info("Hot reload watching stopped")
            return True
            
        except Exception as e:
            self.logger.error(f"Error stopping hot reload watching: {e}")
            return False
    
    def _handle_file_change(self, file_path: str, change_type: str):
        """
        Handle file system change events.
        
        Args:
            file_path: Path to changed file
            change_type: Type of change (modified, created, deleted)
        """
        with self._reload_lock:
            self.reload_stats["total_file_changes"] += 1
            
            file_path_obj = Path(file_path)
            
            # Check if we should ignore this file
            if self._should_ignore_file(file_path_obj):
                self.reload_stats["ignored_changes"] += 1
                return
            
            # Check if it's a plugin-related file
            if not self._is_plugin_file(file_path_obj):
                self.reload_stats["ignored_changes"] += 1
                return
            
            self.logger.debug(f"Plugin file {change_type}: {file_path}")
            
            # Find affected plugins
            affected_plugins = self._find_affected_plugins(file_path_obj)
            
            if not affected_plugins:
                self.logger.debug(f"No plugins affected by change to {file_path}")
                return
            
            # Fire file change event
            self._fire_event("file_changed", {
                "file_path": file_path,
                "change_type": change_type,
                "affected_plugins": affected_plugins
            })
            
            # Schedule reloads for affected plugins
            current_time = time.time()
            for plugin_id in affected_plugins:
                scheduled_time = current_time + self.reload_delay
                self.pending_reloads[plugin_id] = scheduled_time
                
                # Update reload queue
                self.reload_queue[plugin_id] = {
                    "plugin_id": plugin_id,
                    "scheduled_time": scheduled_time,
                    "trigger_file": file_path,
                    "change_type": change_type,
                    "attempts": 0
                }
                
                self.logger.info(f"Scheduled reload for plugin {plugin_id} in {self.reload_delay}s")
    
    def _should_ignore_file(self, file_path: Path) -> bool:
        """Check if file should be ignored based on patterns."""
        file_str = str(file_path)
        
        # Check ignore patterns
        for pattern in self.ignore_patterns:
            if pattern in file_str:
                return True
        
        # Check extension whitelist
        if self.watch_extensions and file_path.suffix not in self.watch_extensions:
            return True
        
        return False
    
    def _is_plugin_file(self, file_path: Path) -> bool:
        """Check if file is part of a plugin."""
        # Check if it's in a watched directory
        for watched_dir in self.watched_directories:
            try:
                file_path.relative_to(watched_dir)
                return True
            except ValueError:
                continue
        
        return False
    
    def _find_affected_plugins(self, file_path: Path) -> List[str]:
        """Find plugins that might be affected by a file change."""
        affected_plugins = []
        
        # Direct mapping
        file_str = str(file_path)
        if file_str in self.plugin_file_mappings:
            affected_plugins.append(self.plugin_file_mappings[file_str])
        
        # Check if file is within any plugin directory
        if self.plugin_manager and hasattr(self.plugin_manager, 'registry'):
            for plugin_id in self.plugin_manager.registry:
                plugin_status = self.plugin_manager.get_plugin_status(plugin_id)
                if plugin_status:
                    discovery_info = plugin_status.get("discovery_info", {})
                    plugin_path = discovery_info.get("path")
                    
                    if plugin_path:
                        plugin_path_obj = Path(plugin_path)
                        
                        # Check if changed file is within plugin directory
                        try:
                            if plugin_path_obj.is_dir():
                                file_path.relative_to(plugin_path_obj)
                                if plugin_id not in affected_plugins:
                                    affected_plugins.append(plugin_id)
                            elif plugin_path_obj == file_path:
                                if plugin_id not in affected_plugins:
                                    affected_plugins.append(plugin_id)
                        except ValueError:
                            continue
        
        return affected_plugins
    
    def _build_file_mappings(self):
        """Build mappings between files and plugins."""
        if not self.plugin_manager or not hasattr(self.plugin_manager, 'registry'):
            return
        
        self.plugin_file_mappings.clear()
        
        for plugin_id in self.plugin_manager.registry:
            plugin_status = self.plugin_manager.get_plugin_status(plugin_id)
            if plugin_status:
                discovery_info = plugin_status.get("discovery_info", {})
                plugin_path = discovery_info.get("path")
                
                if plugin_path:
                    plugin_path_obj = Path(plugin_path)
                    
                    if plugin_path_obj.is_dir():
                        # Map all Python files in plugin directory
                        for py_file in plugin_path_obj.rglob("*.py"):
                            self.plugin_file_mappings[str(py_file)] = plugin_id
                        
                        # Map metadata files
                        for metadata_file in plugin_path_obj.glob("*.{yaml,yml,json}"):
                            if any(name in metadata_file.name.lower() for name in ["plugin", "manifest", "metadata"]):
                                self.plugin_file_mappings[str(metadata_file)] = plugin_id
                    else:
                        # Single file plugin
                        self.plugin_file_mappings[str(plugin_path_obj)] = plugin_id
        
        self.logger.info(f"Built file mappings for {len(self.plugin_file_mappings)} files")
    
    def _start_reload_thread(self):
        """Start background thread for processing reloads."""
        if self.reload_thread and self.reload_thread.is_alive():
            return
        
        self.reload_thread_active = True
        self.shutdown_event.clear()
        
        def reload_processor():
            while self.reload_thread_active and not self.shutdown_event.is_set():
                try:
                    self._process_pending_reloads()
                    self.shutdown_event.wait(0.5)  # Check every 500ms
                except Exception as e:
                    self.logger.error(f"Error in reload processor: {e}")
        
        self.reload_thread = threading.Thread(
            target=reload_processor,
            name="PluginHotReloadProcessor",
            daemon=True
        )
        self.reload_thread.start()
        
        self.logger.debug("Started hot reload processing thread")
    
    def _stop_reload_thread(self):
        """Stop background reload processing thread."""
        self.reload_thread_active = False
        self.shutdown_event.set()
        
        if self.reload_thread and self.reload_thread.is_alive():
            self.reload_thread.join(timeout=2)
        
        self.reload_thread = None
        self.logger.debug("Stopped hot reload processing thread")
    
    def _process_pending_reloads(self):
        """Process plugins scheduled for reload."""
        current_time = time.time()
        plugins_to_reload = []
        
        with self._reload_lock:
            # Find plugins ready for reload
            for plugin_id, scheduled_time in list(self.pending_reloads.items()):
                if current_time >= scheduled_time:
                    plugins_to_reload.append(plugin_id)
                    del self.pending_reloads[plugin_id]
        
        # Process reloads
        for plugin_id in plugins_to_reload:
            self._perform_plugin_reload(plugin_id)
    
    def _perform_plugin_reload(self, plugin_id: str):
        """
        Perform actual plugin reload.
        
        Args:
            plugin_id: ID of plugin to reload
        """
        reload_info = self.reload_queue.get(plugin_id, {})
        reload_info["attempts"] = reload_info.get("attempts", 0) + 1
        
        try:
            self.logger.info(f"Starting hot reload for plugin: {plugin_id}")
            
            # Fire reload started event
            self._fire_event("reload_started", {
                "plugin_id": plugin_id,
                "reload_info": reload_info
            })
            
            # Perform the reload
            if self.plugin_manager:
                reload_result = self.plugin_manager.reload_plugin(plugin_id)
                
                if reload_result.get("success", False):
                    self.reload_stats["successful_reloads"] += 1
                    
                    # Rebuild file mappings after successful reload
                    self._build_file_mappings()
                    
                    self.logger.info(f"Successfully hot-reloaded plugin: {plugin_id}")
                    
                    # Fire success event
                    self._fire_event("reload_completed", {
                        "plugin_id": plugin_id,
                        "reload_info": reload_info,
                        "reload_result": reload_result
                    })
                    
                else:
                    raise Exception(reload_result.get("error", "Reload failed"))
            else:
                raise Exception("No plugin manager available")
        
        except Exception as e:
            self.reload_stats["failed_reloads"] += 1
            self.logger.error(f"Hot reload failed for plugin {plugin_id}: {e}")
            
            # Fire failure event
            self._fire_event("reload_failed", {
                "plugin_id": plugin_id,
                "reload_info": reload_info,
                "error": str(e)
            })
            
            # Retry logic (max 3 attempts)
            if reload_info["attempts"] < 3:
                retry_delay = reload_info["attempts"] * 2  # Exponential backoff
                retry_time = time.time() + retry_delay
                
                self.pending_reloads[plugin_id] = retry_time
                reload_info["scheduled_time"] = retry_time
                
                self.logger.info(f"Scheduling retry {reload_info['attempts']} for plugin {plugin_id} in {retry_delay}s")
            else:
                self.logger.error(f"Max reload attempts reached for plugin {plugin_id}")
        
        finally:
            # Clean up reload queue if no more retries
            if plugin_id not in self.pending_reloads:
                self.reload_queue.pop(plugin_id, None)
    
    def force_reload_plugin(self, plugin_id: str) -> Dict[str, Any]:
        """
        Force immediate reload of a plugin.
        
        Args:
            plugin_id: Plugin ID to reload
            
        Returns:
            Reload result dictionary
        """
        try:
            self.logger.info(f"Force reloading plugin: {plugin_id}")
            
            # Cancel any pending reload
            with self._reload_lock:
                self.pending_reloads.pop(plugin_id, None)
                self.reload_queue.pop(plugin_id, None)
            
            # Perform immediate reload
            if self.plugin_manager:
                result = self.plugin_manager.reload_plugin(plugin_id)
                
                if result.get("success", False):
                    self.reload_stats["successful_reloads"] += 1
                    self._build_file_mappings()
                else:
                    self.reload_stats["failed_reloads"] += 1
                
                return result
            else:
                return {"success": False, "error": "No plugin manager available"}
                
        except Exception as e:
            self.logger.error(f"Force reload failed for plugin {plugin_id}: {e}")
            self.reload_stats["failed_reloads"] += 1
            return {"success": False, "error": str(e)}
    
    def get_reload_status(self) -> Dict[str, Any]:
        """Get hot reload system status."""
        return {
            "enabled": self.enabled,
            "watching": self.observer and self.observer.is_alive() if self.observer else False,
            "watched_directories": [str(d) for d in self.watched_directories],
            "pending_reloads": len(self.pending_reloads),
            "reload_queue_size": len(self.reload_queue),
            "file_mappings": len(self.plugin_file_mappings),
            "stats": self.reload_stats.copy(),
            "config": {
                "reload_delay": self.reload_delay,
                "watch_extensions": self.watch_extensions,
                "ignore_patterns": self.ignore_patterns
            }
        }
    
    def get_pending_reloads(self) -> Dict[str, float]:
        """Get plugins pending reload with scheduled times."""
        return self.pending_reloads.copy()
    
    def cancel_pending_reload(self, plugin_id: str) -> bool:
        """
        Cancel pending reload for a plugin.
        
        Args:
            plugin_id: Plugin ID to cancel reload for
            
        Returns:
            True if reload was cancelled, False if not pending
        """
        with self._reload_lock:
            if plugin_id in self.pending_reloads:
                del self.pending_reloads[plugin_id]
                self.reload_queue.pop(plugin_id, None)
                self.logger.info(f"Cancelled pending reload for plugin: {plugin_id}")
                return True
        
        return False
    
    def add_event_handler(self, event_type: str, handler: Callable):
        """Add event handler for hot reload events."""
        if event_type in self.event_handlers:
            self.event_handlers[event_type].append(handler)
    
    def remove_event_handler(self, event_type: str, handler: Callable):
        """Remove event handler for hot reload events."""
        if event_type in self.event_handlers and handler in self.event_handlers[event_type]:
            self.event_handlers[event_type].remove(handler)
    
    def _fire_event(self, event_type: str, event_data: Dict[str, Any]):
        """Fire hot reload event to registered handlers."""
        handlers = self.event_handlers.get(event_type, [])
        
        for handler in handlers:
            try:
                handler(event_type, event_data)
            except Exception as e:
                self.logger.error(f"Hot reload event handler error for {event_type}: {e}")
    
    def shutdown(self):
        """Shutdown hot reload manager."""
        self.logger.info("Shutting down hot reload manager")
        self.stop_watching()
        self.logger.info("Hot reload manager shutdown complete")