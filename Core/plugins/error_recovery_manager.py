"""
Error Recovery Manager for PersonaOS Plugins

This module provides comprehensive error recovery capabilities for plugin
loading and management, including retry strategies, fallback mechanisms,
and error isolation.
"""

import time
import logging
import threading
from typing import Dict, List, Any, Optional, Callable, Set
from dataclasses import dataclass, field
from enum import Enum

class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class RecoveryStrategy(Enum):
    """Error recovery strategies."""
    RETRY = "retry"
    FALLBACK = "fallback"
    ISOLATE = "isolate"
    DISABLE = "disable"
    IGNORE = "ignore"

@dataclass
class ErrorRecord:
    """Record of a plugin error."""
    plugin_id: str
    error: Exception
    error_type: str
    severity: ErrorSeverity
    timestamp: float
    context: Dict[str, Any] = field(default_factory=dict)
    recovery_attempted: bool = False
    recovery_successful: bool = False
    recovery_strategy: Optional[RecoveryStrategy] = None

@dataclass
class RecoveryRule:
    """Rule for error recovery."""
    error_patterns: List[str]
    strategies: List[RecoveryStrategy]
    max_retries: int = 3
    retry_delay: float = 2.0
    backoff_factor: float = 2.0
    severity_threshold: ErrorSeverity = ErrorSeverity.MEDIUM

class ErrorRecoveryManager:
    """
    Manages error recovery for plugin operations.
    
    Provides sophisticated error handling including:
    - Error classification and severity assessment
    - Configurable recovery strategies
    - Retry mechanisms with exponential backoff
    - Error isolation and fallback handling
    - Recovery success tracking and learning
    """
    
    def __init__(self, config: Dict[str, Any] = None, plugin_manager = None):
        """
        Initialize error recovery manager.
        
        Args:
            config: PersonaOS configuration dictionary
            plugin_manager: Reference to main plugin manager
        """
        self.config = config or {}
        self.plugin_manager = plugin_manager
        self.logger = logging.getLogger("error_recovery_manager")
        
        # Recovery configuration
        self.enabled = config.get("plugin_error_recovery_enabled", True)
        self.max_global_retries = config.get("plugin_max_global_retries", 5)
        self.isolation_enabled = config.get("plugin_error_isolation_enabled", True)
        self.learning_enabled = config.get("plugin_error_learning_enabled", True)
        
        # Error tracking
        self.error_records: Dict[str, List[ErrorRecord]] = {}  # plugin_id -> errors
        self.recovery_history: Dict[str, Dict[str, Any]] = {}  # plugin_id -> recovery stats
        self.global_error_count = 0
        self.recent_errors: List[ErrorRecord] = []  # Last 100 errors
        
        # Recovery rules
        self.recovery_rules = self._load_recovery_rules()
        
        # Error patterns and classification
        self.error_classifiers = self._load_error_classifiers()
        
        # Recovery state
        self.isolated_plugins: Set[str] = set()
        self.disabled_plugins: Set[str] = set()
        self.retry_queues: Dict[str, List[Dict[str, Any]]] = {}
        
        # Threading
        self.recovery_thread = None
        self.recovery_thread_active = False
        self.shutdown_event = threading.Event()
        self._recovery_lock = threading.RLock()
        
        # Statistics
        self.recovery_stats = {
            "total_errors": 0,
            "successful_recoveries": 0,
            "failed_recoveries": 0,
            "isolation_events": 0,
            "disable_events": 0
        }
        
        # Event handlers
        self.event_handlers: Dict[str, List[Callable]] = {
            "error_recorded": [],
            "recovery_started": [],
            "recovery_completed": [],
            "recovery_failed": [],
            "plugin_isolated": [],
            "plugin_disabled": []
        }
        
        if self.enabled:
            self._start_recovery_thread()
        
        self.logger.info(f"ErrorRecoveryManager initialized (enabled: {self.enabled})")
    
    def handle_plugin_error(self, plugin_id: str, error: Exception, 
                          context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Handle a plugin error with recovery strategies.
        
        Args:
            plugin_id: ID of plugin that encountered error
            error: Exception that occurred
            context: Additional context about the error
            
        Returns:
            Recovery result dictionary
        """
        if not self.enabled:
            return {"recovery_attempted": False, "reason": "Error recovery disabled"}
        
        with self._recovery_lock:
            self.recovery_stats["total_errors"] += 1
            self.global_error_count += 1
            
            # Classify and record error
            error_record = self._create_error_record(plugin_id, error, context or {})
            self._record_error(error_record)
            
            # Fire error recorded event
            self._fire_event("error_recorded", {
                "plugin_id": plugin_id,
                "error_record": error_record
            })
            
            # Check if plugin should be isolated
            if self._should_isolate_plugin(plugin_id, error_record):
                return self._isolate_plugin(plugin_id, error_record)
            
            # Check if plugin should be disabled
            if self._should_disable_plugin(plugin_id, error_record):
                return self._disable_plugin(plugin_id, error_record)
            
            # Determine recovery strategy
            recovery_strategy = self._determine_recovery_strategy(plugin_id, error_record)
            
            if recovery_strategy == RecoveryStrategy.IGNORE:
                self.logger.info(f"Ignoring error for plugin {plugin_id}: {error}")
                return {"recovery_attempted": False, "strategy": "ignore"}
            
            # Schedule recovery
            recovery_result = self._schedule_recovery(plugin_id, error_record, recovery_strategy)
            
            return recovery_result
    
    def _create_error_record(self, plugin_id: str, error: Exception, 
                           context: Dict[str, Any]) -> ErrorRecord:
        """Create error record with classification."""
        error_type = type(error).__name__
        severity = self._classify_error_severity(error, context)
        
        return ErrorRecord(
            plugin_id=plugin_id,
            error=error,
            error_type=error_type,
            severity=severity,
            timestamp=time.time(),
            context=context
        )
    
    def _record_error(self, error_record: ErrorRecord):
        """Record error in tracking systems."""
        plugin_id = error_record.plugin_id
        
        # Add to plugin-specific errors
        if plugin_id not in self.error_records:
            self.error_records[plugin_id] = []
        self.error_records[plugin_id].append(error_record)
        
        # Maintain recent errors list (last 100)
        self.recent_errors.append(error_record)
        if len(self.recent_errors) > 100:
            self.recent_errors.pop(0)
        
        # Update recovery history
        if plugin_id not in self.recovery_history:
            self.recovery_history[plugin_id] = {
                "error_count": 0,
                "recovery_attempts": 0,
                "successful_recoveries": 0,
                "last_error_time": 0
            }
        
        history = self.recovery_history[plugin_id]
        history["error_count"] += 1
        history["last_error_time"] = error_record.timestamp
        
        self.logger.warning(f"Recorded {error_record.severity.value} error for plugin {plugin_id}: {error_record.error}")
    
    def _classify_error_severity(self, error: Exception, context: Dict[str, Any]) -> ErrorSeverity:
        """Classify error severity based on type and context."""
        error_type = type(error).__name__
        error_message = str(error).lower()
        
        # Critical errors
        critical_patterns = [
            "system", "security", "corruption", "memory", "segmentation",
            "fatal", "critical", "cannot recover"
        ]
        
        if any(pattern in error_message for pattern in critical_patterns):
            return ErrorSeverity.CRITICAL
        
        # High severity errors
        high_patterns = [
            "import", "module", "dependency", "permission", "access denied",
            "file not found", "network", "timeout"
        ]
        
        if (error_type in ["ImportError", "ModuleNotFoundError", "PermissionError", "FileNotFoundError"] or
            any(pattern in error_message for pattern in high_patterns)):
            return ErrorSeverity.HIGH
        
        # Medium severity errors
        medium_patterns = [
            "attribute", "type", "value", "key", "index", "validation"
        ]
        
        if (error_type in ["AttributeError", "TypeError", "ValueError", "KeyError", "IndexError"] or
            any(pattern in error_message for pattern in medium_patterns)):
            return ErrorSeverity.MEDIUM
        
        # Default to low severity
        return ErrorSeverity.LOW
    
    def _should_isolate_plugin(self, plugin_id: str, error_record: ErrorRecord) -> bool:
        """Determine if plugin should be isolated."""
        if not self.isolation_enabled:
            return False
        
        # Check if already isolated
        if plugin_id in self.isolated_plugins:
            return False
        
        # Critical errors trigger immediate isolation
        if error_record.severity == ErrorSeverity.CRITICAL:
            return True
        
        # Check error frequency
        plugin_errors = self.error_records.get(plugin_id, [])
        recent_errors = [e for e in plugin_errors if time.time() - e.timestamp < 300]  # Last 5 minutes
        
        if len(recent_errors) >= 5:  # 5 errors in 5 minutes
            return True
        
        # Check specific error patterns
        isolation_patterns = ["security", "corruption", "infinite loop", "resource exhaustion"]
        error_message = str(error_record.error).lower()
        
        if any(pattern in error_message for pattern in isolation_patterns):
            return True
        
        return False
    
    def _should_disable_plugin(self, plugin_id: str, error_record: ErrorRecord) -> bool:
        """Determine if plugin should be disabled."""
        # Check if already disabled
        if plugin_id in self.disabled_plugins:
            return False
        
        # Check recovery history
        history = self.recovery_history.get(plugin_id, {})
        error_count = history.get("error_count", 0)
        recovery_attempts = history.get("recovery_attempts", 0)
        successful_recoveries = history.get("successful_recoveries", 0)
        
        # Disable if too many errors with low recovery success
        if error_count >= 10 and recovery_attempts >= 5:
            success_rate = successful_recoveries / recovery_attempts if recovery_attempts > 0 else 0
            if success_rate < 0.2:  # Less than 20% success rate
                return True
        
        return False
    
    def _determine_recovery_strategy(self, plugin_id: str, error_record: ErrorRecord) -> RecoveryStrategy:
        """Determine appropriate recovery strategy for error."""
        error_message = str(error_record.error).lower()
        error_type = error_record.error_type
        
        # Check recovery rules
        for rule in self.recovery_rules:
            for pattern in rule.error_patterns:
                if (pattern.lower() in error_message or 
                    pattern.lower() in error_type.lower()):
                    
                    if error_record.severity.value >= rule.severity_threshold.value:
                        return rule.strategies[0] if rule.strategies else RecoveryStrategy.RETRY
        
        # Default strategy based on severity
        if error_record.severity == ErrorSeverity.CRITICAL:
            return RecoveryStrategy.ISOLATE
        elif error_record.severity == ErrorSeverity.HIGH:
            return RecoveryStrategy.RETRY
        elif error_record.severity == ErrorSeverity.MEDIUM:
            return RecoveryStrategy.RETRY
        else:
            return RecoveryStrategy.IGNORE
    
    def _schedule_recovery(self, plugin_id: str, error_record: ErrorRecord, 
                         strategy: RecoveryStrategy) -> Dict[str, Any]:
        """Schedule recovery for plugin error."""
        # Update error record
        error_record.recovery_attempted = True
        error_record.recovery_strategy = strategy
        
        # Update recovery history
        history = self.recovery_history[plugin_id]
        history["recovery_attempts"] += 1
        
        # Add to retry queue if retry strategy
        if strategy == RecoveryStrategy.RETRY:
            if plugin_id not in self.retry_queues:
                self.retry_queues[plugin_id] = []
            
            retry_info = {
                "plugin_id": plugin_id,
                "error_record": error_record,
                "strategy": strategy,
                "attempts": 0,
                "max_retries": 3,
                "next_retry_time": time.time() + 2.0,  # 2 second delay
                "retry_delay": 2.0
            }
            
            self.retry_queues[plugin_id].append(retry_info)
            
            self.logger.info(f"Scheduled retry recovery for plugin {plugin_id}")
            
            return {
                "recovery_attempted": True,
                "strategy": strategy.value,
                "scheduled": True,
                "next_retry_time": retry_info["next_retry_time"]
            }
        
        else:
            # Immediate recovery for other strategies
            return self._execute_recovery(plugin_id, error_record, strategy)
    
    def _execute_recovery(self, plugin_id: str, error_record: ErrorRecord, 
                        strategy: RecoveryStrategy) -> Dict[str, Any]:
        """Execute recovery strategy immediately."""
        try:
            self.logger.info(f"Executing {strategy.value} recovery for plugin {plugin_id}")
            
            # Fire recovery started event
            self._fire_event("recovery_started", {
                "plugin_id": plugin_id,
                "error_record": error_record,
                "strategy": strategy
            })
            
            success = False
            
            if strategy == RecoveryStrategy.RETRY:
                success = self._retry_plugin_operation(plugin_id, error_record)
            elif strategy == RecoveryStrategy.FALLBACK:
                success = self._execute_fallback(plugin_id, error_record)
            elif strategy == RecoveryStrategy.ISOLATE:
                success = self._isolate_plugin(plugin_id, error_record).get("success", False)
            elif strategy == RecoveryStrategy.DISABLE:
                success = self._disable_plugin(plugin_id, error_record).get("success", False)
            
            # Update recovery record
            error_record.recovery_successful = success
            
            # Update statistics
            if success:
                self.recovery_stats["successful_recoveries"] += 1
                self.recovery_history[plugin_id]["successful_recoveries"] += 1
            else:
                self.recovery_stats["failed_recoveries"] += 1
            
            # Fire recovery completed event
            event_type = "recovery_completed" if success else "recovery_failed"
            self._fire_event(event_type, {
                "plugin_id": plugin_id,
                "error_record": error_record,
                "strategy": strategy,
                "success": success
            })
            
            result = {
                "recovery_attempted": True,
                "strategy": strategy.value,
                "success": success,
                "timestamp": time.time()
            }
            
            self.logger.info(f"Recovery {'successful' if success else 'failed'} for plugin {plugin_id}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Recovery execution failed for plugin {plugin_id}: {e}")
            
            return {
                "recovery_attempted": True,
                "strategy": strategy.value,
                "success": False,
                "error": str(e),
                "timestamp": time.time()
            }
    
    def _retry_plugin_operation(self, plugin_id: str, error_record: ErrorRecord) -> bool:
        """Retry the failed plugin operation."""
        try:
            if not self.plugin_manager:
                return False
            
            # Determine what operation to retry based on context
            context = error_record.context
            operation = context.get("operation", "reload")
            
            if operation == "load":
                result = self.plugin_manager.load_plugin(context.get("plugin_path", ""))
            elif operation == "activate":
                result = self.plugin_manager.activate_plugin(plugin_id)
            elif operation == "reload":
                result = self.plugin_manager.reload_plugin(plugin_id)
            else:
                # Default to reload
                result = self.plugin_manager.reload_plugin(plugin_id)
            
            return result.get("success", False)
            
        except Exception as e:
            self.logger.error(f"Retry operation failed for plugin {plugin_id}: {e}")
            return False
    
    def _execute_fallback(self, plugin_id: str, error_record: ErrorRecord) -> bool:
        """Execute fallback recovery strategy."""
        try:
            # Fallback strategies could include:
            # - Loading a default/safe version of the plugin
            # - Activating alternative plugins
            # - Switching to safe mode
            
            self.logger.info(f"Executing fallback for plugin {plugin_id}")
            
            # For now, just try to deactivate and keep loaded
            if self.plugin_manager:
                deactivate_result = self.plugin_manager.deactivate_plugin(plugin_id)
                return deactivate_result.get("success", False)
            
            return False
            
        except Exception as e:
            self.logger.error(f"Fallback execution failed for plugin {plugin_id}: {e}")
            return False
    
    def _isolate_plugin(self, plugin_id: str, error_record: ErrorRecord) -> Dict[str, Any]:
        """Isolate plugin to prevent further errors."""
        try:
            self.isolated_plugins.add(plugin_id)
            self.recovery_stats["isolation_events"] += 1
            
            # Deactivate plugin if active
            if self.plugin_manager:
                self.plugin_manager.deactivate_plugin(plugin_id)
            
            self._fire_event("plugin_isolated", {
                "plugin_id": plugin_id,
                "error_record": error_record
            })
            
            self.logger.warning(f"Plugin {plugin_id} isolated due to {error_record.severity.value} error")
            
            return {
                "success": True,
                "action": "isolated",
                "plugin_id": plugin_id,
                "reason": f"{error_record.severity.value} error: {error_record.error}"
            }
            
        except Exception as e:
            self.logger.error(f"Failed to isolate plugin {plugin_id}: {e}")
            return {"success": False, "error": str(e)}
    
    def _disable_plugin(self, plugin_id: str, error_record: ErrorRecord) -> Dict[str, Any]:
        """Disable plugin permanently."""
        try:
            self.disabled_plugins.add(plugin_id)
            self.recovery_stats["disable_events"] += 1
            
            # Unload plugin completely
            if self.plugin_manager:
                self.plugin_manager.unload_plugin(plugin_id)
            
            self._fire_event("plugin_disabled", {
                "plugin_id": plugin_id,
                "error_record": error_record
            })
            
            self.logger.error(f"Plugin {plugin_id} disabled due to repeated failures")
            
            return {
                "success": True,
                "action": "disabled",
                "plugin_id": plugin_id,
                "reason": "Repeated failures with low recovery success rate"
            }
            
        except Exception as e:
            self.logger.error(f"Failed to disable plugin {plugin_id}: {e}")
            return {"success": False, "error": str(e)}
    
    def _start_recovery_thread(self):
        """Start background recovery processing thread."""
        if self.recovery_thread and self.recovery_thread.is_alive():
            return
        
        self.recovery_thread_active = True
        self.shutdown_event.clear()
        
        def recovery_processor():
            while self.recovery_thread_active and not self.shutdown_event.is_set():
                try:
                    self._process_retry_queues()
                    self.shutdown_event.wait(1.0)  # Check every second
                except Exception as e:
                    self.logger.error(f"Error in recovery processor: {e}")
        
        self.recovery_thread = threading.Thread(
            target=recovery_processor,
            name="PluginErrorRecoveryProcessor",
            daemon=True
        )
        self.recovery_thread.start()
        
        self.logger.debug("Started error recovery processing thread")
    
    def _process_retry_queues(self):
        """Process pending retry operations."""
        current_time = time.time()
        
        with self._recovery_lock:
            for plugin_id, retry_queue in list(self.retry_queues.items()):
                processed_items = []
                
                for retry_info in retry_queue:
                    if current_time >= retry_info["next_retry_time"]:
                        # Execute retry
                        retry_info["attempts"] += 1
                        
                        success = self._retry_plugin_operation(
                            plugin_id, 
                            retry_info["error_record"]
                        )
                        
                        if success or retry_info["attempts"] >= retry_info["max_retries"]:
                            # Remove from queue
                            processed_items.append(retry_info)
                            
                            # Update statistics
                            if success:
                                self.recovery_stats["successful_recoveries"] += 1
                                self.recovery_history[plugin_id]["successful_recoveries"] += 1
                            else:
                                self.recovery_stats["failed_recoveries"] += 1
                        else:
                            # Schedule next retry with exponential backoff
                            retry_info["retry_delay"] *= 2.0
                            retry_info["next_retry_time"] = current_time + retry_info["retry_delay"]
                
                # Remove processed items
                for item in processed_items:
                    retry_queue.remove(item)
                
                # Clean up empty queues
                if not retry_queue:
                    del self.retry_queues[plugin_id]
    
    def _load_recovery_rules(self) -> List[RecoveryRule]:
        """Load recovery rules from configuration."""
        default_rules = [
            RecoveryRule(
                error_patterns=["ImportError", "ModuleNotFoundError"],
                strategies=[RecoveryStrategy.RETRY, RecoveryStrategy.DISABLE],
                max_retries=2,
                severity_threshold=ErrorSeverity.HIGH
            ),
            RecoveryRule(
                error_patterns=["PermissionError", "FileNotFoundError"],
                strategies=[RecoveryStrategy.RETRY],
                max_retries=3,
                severity_threshold=ErrorSeverity.MEDIUM
            ),
            RecoveryRule(
                error_patterns=["TimeoutError", "NetworkError"],
                strategies=[RecoveryStrategy.RETRY, RecoveryStrategy.FALLBACK],
                max_retries=5,
                retry_delay=5.0,
                severity_threshold=ErrorSeverity.MEDIUM
            ),
            RecoveryRule(
                error_patterns=["SecurityError", "CorruptionError"],
                strategies=[RecoveryStrategy.ISOLATE],
                severity_threshold=ErrorSeverity.CRITICAL
            )
        ]
        
        # Load from config if available
        config_rules = self.config.get("plugin_recovery_rules", [])
        
        # Convert config rules to RecoveryRule objects
        for rule_config in config_rules:
            try:
                rule = RecoveryRule(
                    error_patterns=rule_config.get("error_patterns", []),
                    strategies=[RecoveryStrategy(s) for s in rule_config.get("strategies", ["retry"])],
                    max_retries=rule_config.get("max_retries", 3),
                    retry_delay=rule_config.get("retry_delay", 2.0),
                    severity_threshold=ErrorSeverity(rule_config.get("severity_threshold", "medium"))
                )
                default_rules.append(rule)
            except Exception as e:
                self.logger.warning(f"Invalid recovery rule in config: {e}")
        
        return default_rules
    
    def _load_error_classifiers(self) -> Dict[str, Any]:
        """Load error classification patterns."""
        return self.config.get("plugin_error_classifiers", {
            "critical_patterns": ["system", "security", "corruption", "fatal"],
            "high_patterns": ["import", "dependency", "permission", "network"],
            "medium_patterns": ["attribute", "type", "value", "validation"],
            "low_patterns": ["warning", "info", "debug"]
        })
    
    def get_error_summary(self, plugin_id: str = None) -> Dict[str, Any]:
        """Get error summary for plugin or all plugins."""
        if plugin_id:
            errors = self.error_records.get(plugin_id, [])
            history = self.recovery_history.get(plugin_id, {})
            
            return {
                "plugin_id": plugin_id,
                "total_errors": len(errors),
                "recent_errors": len([e for e in errors if time.time() - e.timestamp < 3600]),
                "recovery_history": history,
                "isolated": plugin_id in self.isolated_plugins,
                "disabled": plugin_id in self.disabled_plugins,
                "pending_retries": len(self.retry_queues.get(plugin_id, []))
            }
        else:
            return {
                "global_stats": self.recovery_stats.copy(),
                "total_plugins_with_errors": len(self.error_records),
                "isolated_plugins": len(self.isolated_plugins),
                "disabled_plugins": len(self.disabled_plugins),
                "total_pending_retries": sum(len(q) for q in self.retry_queues.values()),
                "recent_errors": len([e for e in self.recent_errors if time.time() - e.timestamp < 3600])
            }
    
    def reset_plugin_errors(self, plugin_id: str) -> bool:
        """Reset error history for a plugin."""
        try:
            with self._recovery_lock:
                # Clear error records
                if plugin_id in self.error_records:
                    del self.error_records[plugin_id]
                
                # Reset recovery history
                if plugin_id in self.recovery_history:
                    del self.recovery_history[plugin_id]
                
                # Remove from isolation/disabled lists
                self.isolated_plugins.discard(plugin_id)
                self.disabled_plugins.discard(plugin_id)
                
                # Clear retry queues
                if plugin_id in self.retry_queues:
                    del self.retry_queues[plugin_id]
                
                self.logger.info(f"Reset error history for plugin {plugin_id}")
                return True
        
        except Exception as e:
            self.logger.error(f"Failed to reset errors for plugin {plugin_id}: {e}")
            return False
    
    def add_event_handler(self, event_type: str, handler: Callable):
        """Add event handler for error recovery events."""
        if event_type in self.event_handlers:
            self.event_handlers[event_type].append(handler)
    
    def remove_event_handler(self, event_type: str, handler: Callable):
        """Remove event handler for error recovery events."""
        if event_type in self.event_handlers and handler in self.event_handlers[event_type]:
            self.event_handlers[event_type].remove(handler)
    
    def _fire_event(self, event_type: str, event_data: Dict[str, Any]):
        """Fire error recovery event to registered handlers."""
        handlers = self.event_handlers.get(event_type, [])
        
        for handler in handlers:
            try:
                handler(event_type, event_data)
            except Exception as e:
                self.logger.error(f"Error recovery event handler error for {event_type}: {e}")
    
    def shutdown(self):
        """Shutdown error recovery manager."""
        self.logger.info("Shutting down error recovery manager")
        
        # Stop recovery thread
        self.recovery_thread_active = False
        self.shutdown_event.set()
        
        if self.recovery_thread and self.recovery_thread.is_alive():
            self.recovery_thread.join(timeout=2)
        
        self.recovery_thread = None
        
        self.logger.info("Error recovery manager shutdown complete")