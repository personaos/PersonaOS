"""
Emergency Controller for Voice-Enabled Tool Execution

This module provides emergency stop functionality, error handling, and safety controls
for voice-initiated tool execution and workflows.
"""

import time
import threading
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass
from enum import Enum
import logging

class EmergencyState(Enum):
    """Emergency system states."""
    NORMAL = "normal"
    EMERGENCY_STOP = "emergency_stop"
    SYSTEM_HALT = "system_halt"
    RECOVERY_MODE = "recovery_mode"

@dataclass
class EmergencyEvent:
    """Emergency event record."""
    event_id: str
    event_type: str
    timestamp: float
    trigger: str  # What triggered the emergency
    context: Dict[str, Any]
    resolved: bool = False
    resolution_time: Optional[float] = None
    resolution_method: Optional[str] = None

class EmergencyController:
    """
    Manages emergency stops, error handling, and safety controls for voice tool execution.
    """
    
    def __init__(self, tool_registry=None, workflow_manager=None, audio_feedback=None, config: Optional[Dict] = None):
        """
        Initialize emergency controller.
        
        Args:
            tool_registry: ToolRegistry instance
            workflow_manager: WorkflowManager instance
            audio_feedback: ToolAudioFeedback instance
            config: Configuration dictionary
        """
        self.tool_registry = tool_registry
        self.workflow_manager = workflow_manager
        self.audio_feedback = audio_feedback
        self.config = config or {}
        self.logger = logging.getLogger("emergency_controller")
        
        # Emergency state
        self.current_state = EmergencyState.NORMAL
        self.state_lock = threading.Lock()
        
        # Emergency event tracking
        self.emergency_events: List[EmergencyEvent] = []
        self.event_counter = 0
        
        # Emergency triggers
        self.emergency_phrases = self._load_emergency_phrases()
        self.error_recovery_strategies = self._load_recovery_strategies()
        
        # Active monitoring
        self.active_tool_sessions = {}  # Track running tools for emergency stops
        self.monitoring_enabled = self.config.get("emergency_monitoring_enabled", True)
        self.response_timeout = self.config.get("emergency_response_timeout", 5.0)
        
        # Error handling settings
        self.max_consecutive_errors = self.config.get("max_consecutive_errors", 3)
        self.error_cooldown_period = self.config.get("error_cooldown_period", 30)
        self.consecutive_error_count = 0
        self.last_error_time = 0
        
        # Callbacks
        self.emergency_callback: Optional[Callable] = None
        self.error_callback: Optional[Callable] = None
        self.recovery_callback: Optional[Callable] = None
        
        self.logger.info("EmergencyController initialized")
    
    def _load_emergency_phrases(self) -> List[str]:
        """Load emergency stop phrases and patterns."""
        return [
            "emergency stop",
            "stop everything",
            "abort all",
            "cancel everything",
            "halt system",
            "emergency",
            "stop now",
            "kill all",
            "shutdown",
            "panic stop",
            "red alert",
            "danger"
        ]
    
    def _load_recovery_strategies(self) -> Dict[str, Dict[str, Any]]:
        """Load error recovery strategies."""
        return {
            "tool_timeout": {
                "strategy": "restart_tool",
                "max_retries": 2,
                "backoff_seconds": 5,
                "fallback": "cancel_tool"
            },
            "tool_crash": {
                "strategy": "isolate_and_restart",
                "max_retries": 1,
                "backoff_seconds": 10,
                "fallback": "disable_tool"
            },
            "voice_recognition_failure": {
                "strategy": "fallback_to_text",
                "max_retries": 3,
                "backoff_seconds": 2,
                "fallback": "manual_intervention"
            },
            "audio_system_failure": {
                "strategy": "text_only_mode",
                "max_retries": 1,
                "backoff_seconds": 15,
                "fallback": "system_notification"
            },
            "workflow_deadlock": {
                "strategy": "reset_workflow",
                "max_retries": 1,
                "backoff_seconds": 5,
                "fallback": "cancel_workflow"
            },
            "memory_overflow": {
                "strategy": "cleanup_and_continue",
                "max_retries": 2,
                "backoff_seconds": 10,
                "fallback": "system_restart"
            }
        }
    
    def check_emergency_trigger(self, voice_input: str) -> bool:
        """
        Check if voice input contains emergency stop triggers.
        
        Args:
            voice_input: Voice input text to check
            
        Returns:
            True if emergency trigger detected
        """
        if not voice_input:
            return False
        
        voice_lower = voice_input.lower().strip()
        
        # Check for emergency phrases
        for phrase in self.emergency_phrases:
            if phrase in voice_lower:
                self.logger.warning(f"Emergency trigger detected: '{phrase}' in '{voice_input}'")
                return True
        
        # Check for urgent patterns
        urgent_patterns = [
            r"stop.*everything",
            r"cancel.*all",
            r"abort.*now",
            r"emergency.*stop",
            r"halt.*system"
        ]
        
        import re
        for pattern in urgent_patterns:
            if re.search(pattern, voice_lower):
                self.logger.warning(f"Emergency pattern detected: '{pattern}' in '{voice_input}'")
                return True
        
        return False
    
    def trigger_emergency_stop(self, trigger_source: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Trigger emergency stop of all running tools and workflows.
        
        Args:
            trigger_source: What triggered the emergency
            context: Additional context information
            
        Returns:
            Emergency stop result
        """
        with self.state_lock:
            if self.current_state == EmergencyState.EMERGENCY_STOP:
                return {
                    "success": True,
                    "message": "Emergency stop already active",
                    "state": self.current_state.value
                }
            
            old_state = self.current_state
            self.current_state = EmergencyState.EMERGENCY_STOP
        
        # Create emergency event
        event = EmergencyEvent(
            event_id=f"emergency_{self.event_counter}",
            event_type="emergency_stop",
            timestamp=time.time(),
            trigger=trigger_source,
            context=context or {}
        )
        self.emergency_events.append(event)
        self.event_counter += 1
        
        self.logger.critical(f"EMERGENCY STOP TRIGGERED: {trigger_source}")
        
        # Immediate audio announcement
        if self.audio_feedback:
            self.audio_feedback._interrupt_current_speech()
            self.audio_feedback._queue_audio_feedback(
                "Emergency stop activated. Halting all operations.",
                "urgent", False
            )
        
        # Stop all active tools and workflows
        stop_results = self._execute_emergency_stop()
        
        # Call emergency callback if set
        if self.emergency_callback:
            try:
                self.emergency_callback(event, stop_results)
            except Exception as e:
                self.logger.error(f"Error in emergency callback: {e}")
        
        # Schedule automatic recovery check
        self._schedule_recovery_check(30)  # 30 seconds
        
        return {
            "success": True,
            "event_id": event.event_id,
            "state": self.current_state.value,
            "stop_results": stop_results,
            "message": "Emergency stop executed successfully"
        }
    
    def _execute_emergency_stop(self) -> Dict[str, Any]:
        """Execute the actual emergency stop procedures."""
        results = {
            "tools_stopped": 0,
            "workflows_cancelled": 0,
            "audio_stopped": False,
            "errors": []
        }
        
        try:
            # Stop all audio feedback immediately
            if self.audio_feedback:
                self.audio_feedback.stop_all_feedback()
                results["audio_stopped"] = True
            
            # Cancel all active workflows
            if self.workflow_manager:
                active_workflows = list(self.workflow_manager.active_workflows.keys())
                for workflow_id in active_workflows:
                    try:
                        success = self.workflow_manager.cancel_workflow(
                            workflow_id, "Emergency stop triggered"
                        )
                        if success:
                            results["workflows_cancelled"] += 1
                    except Exception as e:
                        results["errors"].append(f"Failed to cancel workflow {workflow_id}: {e}")
            
            # Stop all active tool sessions
            if self.tool_registry:
                for session_id in list(self.active_tool_sessions.keys()):
                    try:
                        self.tool_registry.cancel_tool_execution(
                            session_id, "Emergency stop triggered"
                        )
                        results["tools_stopped"] += 1
                        del self.active_tool_sessions[session_id]
                    except Exception as e:
                        results["errors"].append(f"Failed to stop tool session {session_id}: {e}")
            
            # Clear any pending operations
            self.active_tool_sessions.clear()
            
            self.logger.info(f"Emergency stop completed: {results}")
            
        except Exception as e:
            self.logger.error(f"Error during emergency stop execution: {e}")
            results["errors"].append(f"Emergency stop error: {e}")
        
        return results
    
    def handle_tool_error(self, tool_name: str, error: Exception, context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Handle tool execution errors with recovery strategies.
        
        Args:
            tool_name: Name of the tool that errored
            error: The exception that occurred
            context: Additional error context
            
        Returns:
            Error handling result
        """
        current_time = time.time()
        
        # Update consecutive error tracking
        if current_time - self.last_error_time > self.error_cooldown_period:
            self.consecutive_error_count = 0
        
        self.consecutive_error_count += 1
        self.last_error_time = current_time
        
        # Create error event
        event = EmergencyEvent(
            event_id=f"error_{self.event_counter}",
            event_type="tool_error",
            timestamp=current_time,
            trigger=f"Tool error: {tool_name}",
            context={
                "tool_name": tool_name,
                "error": str(error),
                "error_type": type(error).__name__,
                "consecutive_errors": self.consecutive_error_count,
                **(context or {})
            }
        )
        self.emergency_events.append(event)
        self.event_counter += 1
        
        self.logger.error(f"Tool error in {tool_name}: {error}")
        
        # Check if we need to trigger emergency protocols
        if self.consecutive_error_count >= self.max_consecutive_errors:
            self.logger.critical(f"Maximum consecutive errors reached ({self.consecutive_error_count})")
            
            # Announce critical error state
            if self.audio_feedback:
                self.audio_feedback._queue_audio_feedback(
                    f"Critical error state detected. Multiple tool failures occurred.",
                    "urgent", False
                )
            
            # Trigger emergency protocols but don't full stop
            return self._handle_critical_error_state(event)
        
        # Determine error type and recovery strategy
        error_type = self._classify_error(error, tool_name, context)
        recovery_strategy = self.error_recovery_strategies.get(error_type, {})
        
        # Attempt error recovery
        recovery_result = self._attempt_error_recovery(
            tool_name, error, error_type, recovery_strategy, event
        )
        
        # Provide audio feedback for error
        self._announce_error_and_recovery(tool_name, error, recovery_result)
        
        # Call error callback if set
        if self.error_callback:
            try:
                self.error_callback(event, recovery_result)
            except Exception as e:
                self.logger.error(f"Error in error callback: {e}")
        
        return recovery_result
    
    def _classify_error(self, error: Exception, tool_name: str, context: Optional[Dict]) -> str:
        """Classify error type for appropriate recovery strategy."""
        error_type = type(error).__name__.lower()
        error_message = str(error).lower()
        
        # Check for specific error patterns
        if "timeout" in error_message or "timeout" in error_type:
            return "tool_timeout"
        elif "crash" in error_message or "segmentation" in error_message:
            return "tool_crash"
        elif "memory" in error_message or "out of memory" in error_message:
            return "memory_overflow"
        elif "voice" in error_message or "speech" in error_message:
            return "voice_recognition_failure"
        elif "audio" in error_message or "sound" in error_message:
            return "audio_system_failure"
        elif "workflow" in error_message or "deadlock" in error_message:
            return "workflow_deadlock"
        else:
            return "general_error"
    
    def _attempt_error_recovery(self, tool_name: str, error: Exception, error_type: str, 
                               strategy: Dict, event: EmergencyEvent) -> Dict[str, Any]:
        """Attempt to recover from an error using the specified strategy."""
        if not strategy:
            return {
                "success": False,
                "method": "none",
                "message": "No recovery strategy available"
            }
        
        recovery_method = strategy.get("strategy", "none")
        max_retries = strategy.get("max_retries", 1)
        backoff_seconds = strategy.get("backoff_seconds", 5)
        fallback = strategy.get("fallback", "report_error")
        
        self.logger.info(f"Attempting recovery for {tool_name} using strategy: {recovery_method}")
        
        try:
            if recovery_method == "restart_tool":
                return self._restart_tool_recovery(tool_name, max_retries, backoff_seconds)
            
            elif recovery_method == "isolate_and_restart":
                return self._isolate_and_restart_recovery(tool_name, max_retries, backoff_seconds)
            
            elif recovery_method == "fallback_to_text":
                return self._fallback_to_text_recovery()
            
            elif recovery_method == "text_only_mode":
                return self._text_only_mode_recovery()
            
            elif recovery_method == "reset_workflow":
                return self._reset_workflow_recovery()
            
            elif recovery_method == "cleanup_and_continue":
                return self._cleanup_and_continue_recovery()
            
            else:
                return self._execute_fallback_strategy(fallback, tool_name, error)
        
        except Exception as recovery_error:
            self.logger.error(f"Recovery attempt failed: {recovery_error}")
            return self._execute_fallback_strategy(fallback, tool_name, recovery_error)
    
    def _restart_tool_recovery(self, tool_name: str, max_retries: int, backoff_seconds: int) -> Dict[str, Any]:
        """Recovery strategy: restart the specific tool."""
        # This is a placeholder - actual implementation would depend on tool architecture
        return {
            "success": True,
            "method": "restart_tool",
            "message": f"Tool {tool_name} restart scheduled"
        }
    
    def _isolate_and_restart_recovery(self, tool_name: str, max_retries: int, backoff_seconds: int) -> Dict[str, Any]:
        """Recovery strategy: isolate problematic tool and restart it."""
        return {
            "success": True,
            "method": "isolate_and_restart",
            "message": f"Tool {tool_name} isolated and restart scheduled"
        }
    
    def _fallback_to_text_recovery(self) -> Dict[str, Any]:
        """Recovery strategy: fall back to text-only interaction."""
        return {
            "success": True,
            "method": "fallback_to_text",
            "message": "Switching to text-only mode for this session"
        }
    
    def _text_only_mode_recovery(self) -> Dict[str, Any]:
        """Recovery strategy: disable audio and use text-only mode."""
        if self.audio_feedback:
            self.audio_feedback.configure_feedback(enabled=False)
        
        return {
            "success": True,
            "method": "text_only_mode",
            "message": "Audio disabled, using text-only mode"
        }
    
    def _reset_workflow_recovery(self) -> Dict[str, Any]:
        """Recovery strategy: reset current workflow."""
        if self.workflow_manager:
            active_workflows = list(self.workflow_manager.active_workflows.keys())
            for workflow_id in active_workflows:
                self.workflow_manager.cancel_workflow(workflow_id, "Error recovery reset")
        
        return {
            "success": True,
            "method": "reset_workflow",
            "message": "Active workflows have been reset"
        }
    
    def _cleanup_and_continue_recovery(self) -> Dict[str, Any]:
        """Recovery strategy: clean up resources and continue."""
        # Clear old sessions and free memory
        self.active_tool_sessions.clear()
        
        return {
            "success": True,
            "method": "cleanup_and_continue",
            "message": "System resources cleaned up"
        }
    
    def _execute_fallback_strategy(self, fallback: str, tool_name: str, error: Exception) -> Dict[str, Any]:
        """Execute fallback strategy when primary recovery fails."""
        if fallback == "cancel_tool":
            return {
                "success": True,
                "method": "cancel_tool",
                "message": f"Tool {tool_name} cancelled as fallback"
            }
        elif fallback == "disable_tool":
            return {
                "success": True,
                "method": "disable_tool",
                "message": f"Tool {tool_name} disabled due to errors"
            }
        elif fallback == "system_restart":
            return {
                "success": False,
                "method": "system_restart",
                "message": "System restart required - please restart PersonaOS"
            }
        else:
            return {
                "success": False,
                "method": "report_error",
                "message": f"Error reported: {error}"
            }
    
    def _handle_critical_error_state(self, event: EmergencyEvent) -> Dict[str, Any]:
        """Handle critical error state with multiple consecutive failures."""
        with self.state_lock:
            self.current_state = EmergencyState.SYSTEM_HALT
        
        # Stop all non-essential operations
        if self.workflow_manager:
            for workflow_id in list(self.workflow_manager.active_workflows.keys()):
                self.workflow_manager.cancel_workflow(workflow_id, "Critical error state")
        
        # Schedule recovery attempt
        self._schedule_recovery_check(60)  # 1 minute for critical errors
        
        return {
            "success": True,
            "state": "critical_error",
            "message": "System halted due to critical errors",
            "consecutive_errors": self.consecutive_error_count,
            "recovery_scheduled": True
        }
    
    def _announce_error_and_recovery(self, tool_name: str, error: Exception, recovery_result: Dict):
        """Announce error and recovery status via audio."""
        if not self.audio_feedback:
            return
        
        error_message = f"Error in {tool_name}."
        
        if recovery_result.get("success"):
            recovery_message = recovery_result.get("message", "Recovery attempted.")
            full_message = f"{error_message} {recovery_message}"
        else:
            full_message = f"{error_message} Unable to recover automatically."
        
        self.audio_feedback._queue_audio_feedback(full_message, "high", True)
    
    def _schedule_recovery_check(self, delay_seconds: int):
        """Schedule automatic recovery check after delay."""
        def recovery_check():
            time.sleep(delay_seconds)
            self.attempt_system_recovery()
        
        threading.Thread(target=recovery_check, daemon=True).start()
    
    def attempt_system_recovery(self) -> Dict[str, Any]:
        """Attempt to recover from emergency or critical error state."""
        if self.current_state == EmergencyState.NORMAL:
            return {"success": True, "message": "System already in normal state"}
        
        with self.state_lock:
            old_state = self.current_state
            self.current_state = EmergencyState.RECOVERY_MODE
        
        self.logger.info(f"Attempting system recovery from state: {old_state.value}")
        
        try:
            # Reset error counters
            self.consecutive_error_count = 0
            self.last_error_time = 0
            
            # Re-enable audio if disabled
            if self.audio_feedback:
                self.audio_feedback.configure_feedback(enabled=True)
            
            # Clear old sessions
            self.active_tool_sessions.clear()
            
            # Mark recent emergency events as resolved
            current_time = time.time()
            for event in self.emergency_events:
                if not event.resolved and current_time - event.timestamp < 300:  # 5 minutes
                    event.resolved = True
                    event.resolution_time = current_time
                    event.resolution_method = "automatic_recovery"
            
            with self.state_lock:
                self.current_state = EmergencyState.NORMAL
            
            if self.audio_feedback:
                self.audio_feedback._queue_audio_feedback(
                    "System recovery completed. Normal operations resumed.",
                    "normal", True
                )
            
            # Call recovery callback if set
            if self.recovery_callback:
                try:
                    self.recovery_callback(old_state, EmergencyState.NORMAL)
                except Exception as e:
                    self.logger.error(f"Error in recovery callback: {e}")
            
            self.logger.info("System recovery completed successfully")
            
            return {
                "success": True,
                "previous_state": old_state.value,
                "current_state": self.current_state.value,
                "message": "System recovered successfully"
            }
        
        except Exception as e:
            self.logger.error(f"System recovery failed: {e}")
            
            with self.state_lock:
                self.current_state = old_state  # Revert to previous state
            
            return {
                "success": False,
                "error": str(e),
                "current_state": self.current_state.value,
                "message": "System recovery failed"
            }
    
    def register_tool_session(self, session_id: str, tool_name: str, context: Dict):
        """Register an active tool session for emergency monitoring."""
        self.active_tool_sessions[session_id] = {
            "tool_name": tool_name,
            "start_time": time.time(),
            "context": context
        }
    
    def unregister_tool_session(self, session_id: str):
        """Unregister a completed tool session."""
        if session_id in self.active_tool_sessions:
            del self.active_tool_sessions[session_id]
    
    def get_emergency_status(self) -> Dict[str, Any]:
        """Get current emergency system status."""
        return {
            "current_state": self.current_state.value,
            "monitoring_enabled": self.monitoring_enabled,
            "active_tool_sessions": len(self.active_tool_sessions),
            "consecutive_errors": self.consecutive_error_count,
            "last_error_time": self.last_error_time,
            "recent_events": len([e for e in self.emergency_events 
                                if time.time() - e.timestamp < 300]),  # Last 5 minutes
            "unresolved_events": len([e for e in self.emergency_events if not e.resolved])
        }
    
    def set_callbacks(self, emergency_callback: Optional[Callable] = None,
                     error_callback: Optional[Callable] = None,
                     recovery_callback: Optional[Callable] = None):
        """Set callback functions for emergency events."""
        self.emergency_callback = emergency_callback
        self.error_callback = error_callback
        self.recovery_callback = recovery_callback
    
    def get_emergency_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent emergency events history."""
        recent_events = sorted(self.emergency_events, 
                             key=lambda e: e.timestamp, reverse=True)[:limit]
        
        return [
            {
                "event_id": event.event_id,
                "event_type": event.event_type,
                "timestamp": event.timestamp,
                "trigger": event.trigger,
                "resolved": event.resolved,
                "resolution_time": event.resolution_time,
                "resolution_method": event.resolution_method
            }
            for event in recent_events
        ]