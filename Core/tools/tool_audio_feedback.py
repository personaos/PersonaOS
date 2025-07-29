"""
Tool Audio Feedback System

This module provides audio feedback integration for tool execution,
including status updates, result announcements, and error notifications.
"""

import time
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass
from enum import Enum
import logging

from ..tools.tool_registry import ToolResult, VoiceToolContext

class ToolExecutionState(Enum):
    """States of tool execution for audio feedback."""
    STARTING = "starting"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    CONFIRMATION_REQUIRED = "confirmation_required"

@dataclass
class AudioFeedbackTemplate:
    """Template for generating audio feedback messages."""
    state: ToolExecutionState
    tool_name: str
    template: str
    priority: str = "normal"  # "low", "normal", "high", "urgent"
    interruptible: bool = True

class ToolAudioFeedback:
    """
    Manages audio feedback for tool execution states and results.
    Integrates with TTS system to provide real-time audio updates.
    """
    
    def __init__(self, audio_processor=None, config: Optional[Dict] = None):
        """
        Initialize the tool audio feedback system.
        
        Args:
            audio_processor: AudioProcessor instance for TTS
            config: Configuration dictionary
        """
        self.audio_processor = audio_processor
        self.config = config or {}
        self.logger = logging.getLogger("tool_audio_feedback")
        
        # Audio feedback settings
        self.feedback_enabled = self.config.get("tool_audio_feedback_enabled", True)
        self.streaming_feedback = self.config.get("tool_streaming_feedback", True)
        self.feedback_volume = self.config.get("tool_feedback_volume", 0.8)
        self.interrupt_for_urgent = self.config.get("interrupt_for_urgent_feedback", True)
        
        # State management
        self.active_tool_sessions = {}  # Track ongoing tool executions
        self.feedback_queue = []  # Queue for pending audio feedback
        self.is_speaking_feedback = False
        
        # Load audio templates
        self.templates = self._load_feedback_templates()
        
        self.logger.info("ToolAudioFeedback initialized")
    
    def _load_feedback_templates(self) -> Dict[str, Dict[str, AudioFeedbackTemplate]]:
        """Load predefined audio feedback templates for different tools and states."""
        templates = {
            # Generic templates (used as fallback)
            "generic": {
                ToolExecutionState.STARTING: AudioFeedbackTemplate(
                    ToolExecutionState.STARTING, "generic", 
                    "Starting {tool_name}..."
                ),
                ToolExecutionState.RUNNING: AudioFeedbackTemplate(
                    ToolExecutionState.RUNNING, "generic",
                    "{tool_name} is running..."
                ),
                ToolExecutionState.COMPLETED: AudioFeedbackTemplate(
                    ToolExecutionState.COMPLETED, "generic",
                    "{tool_name} completed successfully."
                ),
                ToolExecutionState.FAILED: AudioFeedbackTemplate(
                    ToolExecutionState.FAILED, "generic",
                    "{tool_name} failed. {error_message}", 
                    priority="high"
                ),
                ToolExecutionState.CANCELLED: AudioFeedbackTemplate(
                    ToolExecutionState.CANCELLED, "generic",
                    "{tool_name} was cancelled."
                ),
                ToolExecutionState.CONFIRMATION_REQUIRED: AudioFeedbackTemplate(
                    ToolExecutionState.CONFIRMATION_REQUIRED, "generic",
                    "{tool_name} requires confirmation. {confirmation_message}",
                    priority="urgent", interruptible=False
                )
            },
            
            # Tool-specific templates
            "web_search": {
                ToolExecutionState.STARTING: AudioFeedbackTemplate(
                    ToolExecutionState.STARTING, "web_search",
                    "Searching the web for {query}..."
                ),
                ToolExecutionState.COMPLETED: AudioFeedbackTemplate(
                    ToolExecutionState.COMPLETED, "web_search",
                    "Search completed. {result_summary}"
                )
            },
            
            "weather": {
                ToolExecutionState.STARTING: AudioFeedbackTemplate(
                    ToolExecutionState.STARTING, "weather",
                    "Getting weather information for {location}..."
                ),
                ToolExecutionState.COMPLETED: AudioFeedbackTemplate(
                    ToolExecutionState.COMPLETED, "weather",
                    "Weather update: {weather_info}"
                )
            },
            
            "calculator": {
                ToolExecutionState.STARTING: AudioFeedbackTemplate(
                    ToolExecutionState.STARTING, "calculator",
                    "Calculating {expression}..."
                ),
                ToolExecutionState.COMPLETED: AudioFeedbackTemplate(
                    ToolExecutionState.COMPLETED, "calculator",
                    "Calculation result: {result}"
                )
            },
            
            "timer": {
                ToolExecutionState.STARTING: AudioFeedbackTemplate(
                    ToolExecutionState.STARTING, "timer",
                    "Setting timer for {duration} {unit}..."
                ),
                ToolExecutionState.COMPLETED: AudioFeedbackTemplate(
                    ToolExecutionState.COMPLETED, "timer",
                    "Timer set successfully. {timer_message}"
                )
            }
        }
        
        return templates
    
    def announce_tool_execution_start(self, tool_name: str, tool_args: Dict, voice_context: Optional[VoiceToolContext] = None):
        """
        Announce the start of tool execution via audio.
        
        Args:
            tool_name: Name of the tool being executed
            tool_args: Tool execution arguments
            voice_context: Voice execution context if applicable
        """
        if not self.feedback_enabled:
            return
        
        session_id = f"{tool_name}_{int(time.time())}"
        self.active_tool_sessions[session_id] = {
            "tool_name": tool_name,
            "start_time": time.time(),
            "args": tool_args,
            "voice_context": voice_context
        }
        
        template = self._get_template(tool_name, ToolExecutionState.STARTING)
        message = self._format_template_message(template, tool_name, tool_args)
        
        self._queue_audio_feedback(message, template.priority, template.interruptible)
        self.logger.info(f"Announced start of {tool_name} execution")
        
        return session_id
    
    def announce_tool_execution_progress(self, session_id: str, progress_info: str):
        """
        Announce progress updates for long-running tools.
        
        Args:
            session_id: Tool execution session ID
            progress_info: Progress information to announce
        """
        if not self.feedback_enabled or not self.streaming_feedback:
            return
        
        if session_id not in self.active_tool_sessions:
            self.logger.warning(f"Unknown session ID for progress update: {session_id}")
            return
        
        session = self.active_tool_sessions[session_id]
        tool_name = session["tool_name"]
        
        template = self._get_template(tool_name, ToolExecutionState.RUNNING)
        message = progress_info or template.template.format(tool_name=tool_name)
        
        self._queue_audio_feedback(message, "low", True)
        self.logger.info(f"Announced progress for {tool_name}: {progress_info}")
    
    def announce_tool_execution_completion(self, session_id: str, result: ToolResult):
        """
        Announce the completion of tool execution with results.
        
        Args:
            session_id: Tool execution session ID
            result: Tool execution result
        """
        if not self.feedback_enabled:
            return
        
        if session_id not in self.active_tool_sessions:
            self.logger.warning(f"Unknown session ID for completion: {session_id}")
            return
        
        session = self.active_tool_sessions[session_id]
        tool_name = session["tool_name"]
        
        if result.success:
            # Use voice_response if available, otherwise format using templates
            if result.voice_response:
                message = result.voice_response
            else:
                template = self._get_template(tool_name, ToolExecutionState.COMPLETED)
                message = self._format_completion_message(template, tool_name, result)
            
            self._queue_audio_feedback(message, "normal", True)
            self.logger.info(f"Announced successful completion of {tool_name}")
        else:
            template = self._get_template(tool_name, ToolExecutionState.FAILED)
            message = template.template.format(
                tool_name=tool_name,
                error_message=result.error or "Unknown error occurred"
            )
            
            self._queue_audio_feedback(message, template.priority, template.interruptible)
            self.logger.warning(f"Announced failure of {tool_name}: {result.error}")
        
        # Clean up session
        del self.active_tool_sessions[session_id]
    
    def announce_confirmation_required(self, tool_name: str, confirmation_message: str, voice_context: Optional[VoiceToolContext] = None):
        """
        Announce that user confirmation is required for tool execution.
        
        Args:
            tool_name: Name of the tool requiring confirmation
            confirmation_message: Confirmation prompt message
            voice_context: Voice execution context if applicable
        """
        if not self.feedback_enabled:
            return
        
        template = self._get_template(tool_name, ToolExecutionState.CONFIRMATION_REQUIRED)
        message = template.template.format(
            tool_name=tool_name,
            confirmation_message=confirmation_message
        )
        
        self._queue_audio_feedback(message, template.priority, template.interruptible)
        self.logger.info(f"Announced confirmation required for {tool_name}")
    
    def announce_tool_cancellation(self, session_id: str, reason: str = "User requested cancellation"):
        """
        Announce that tool execution was cancelled.
        
        Args:
            session_id: Tool execution session ID
            reason: Reason for cancellation
        """
        if not self.feedback_enabled:
            return
        
        if session_id not in self.active_tool_sessions:
            self.logger.warning(f"Unknown session ID for cancellation: {session_id}")
            return
        
        session = self.active_tool_sessions[session_id]
        tool_name = session["tool_name"]
        
        template = self._get_template(tool_name, ToolExecutionState.CANCELLED)
        message = template.template.format(tool_name=tool_name)
        
        if reason != "User requested cancellation":
            message += f" Reason: {reason}"
        
        self._queue_audio_feedback(message, "normal", True)
        self.logger.info(f"Announced cancellation of {tool_name}: {reason}")
        
        # Clean up session
        del self.active_tool_sessions[session_id]
    
    def _get_template(self, tool_name: str, state: ToolExecutionState) -> AudioFeedbackTemplate:
        """Get the appropriate template for a tool and state."""
        # Try tool-specific template first
        if tool_name in self.templates and state in self.templates[tool_name]:
            return self.templates[tool_name][state]
        
        # Fall back to generic template
        return self.templates["generic"][state]
    
    def _format_template_message(self, template: AudioFeedbackTemplate, tool_name: str, tool_args: Dict) -> str:
        """Format a template message with tool-specific information."""
        format_args = {"tool_name": tool_name}
        
        # Add common tool arguments to format args
        if "query" in tool_args:
            format_args["query"] = tool_args["query"]
        if "location" in tool_args:
            format_args["location"] = tool_args["location"]
        if "expression" in tool_args:
            format_args["expression"] = tool_args["expression"]
        if "duration" in tool_args:
            format_args["duration"] = tool_args["duration"]
        if "unit" in tool_args:
            format_args["unit"] = tool_args["unit"]
        
        try:
            return template.template.format(**format_args)
        except KeyError as e:
            self.logger.warning(f"Missing format argument {e} for template, using generic message")
            return f"Executing {tool_name}..."
    
    def _format_completion_message(self, template: AudioFeedbackTemplate, tool_name: str, result: ToolResult) -> str:
        """Format a completion message with result-specific information."""
        format_args = {"tool_name": tool_name}
        
        # Extract result-specific information
        if result.data:
            if isinstance(result.data, dict):
                # Add common result fields
                if "message" in result.data:
                    format_args["result_summary"] = result.data["message"]
                elif "formatted" in result.data:
                    format_args["result_summary"] = result.data["formatted"]
                
                # Tool-specific result formatting
                if tool_name == "weather" and "condition" in result.data:
                    format_args["weather_info"] = f"{result.data.get('condition', '')} with temperature {result.data.get('temperature', '')}"
                elif tool_name == "calculator" and "result" in result.data:
                    format_args["result"] = str(result.data["result"])
                elif tool_name == "timer" and "message" in result.data:
                    format_args["timer_message"] = result.data["message"]
        
        try:
            return template.template.format(**format_args)
        except KeyError:
            # Fallback to simple completion message
            return f"{tool_name} completed successfully."
    
    def _queue_audio_feedback(self, message: str, priority: str = "normal", interruptible: bool = True):
        """
        Queue audio feedback message for playback.
        
        Args:
            message: Message to speak
            priority: Message priority ("low", "normal", "high", "urgent")
            interruptible: Whether this message can be interrupted
        """
        feedback_item = {
            "message": message,
            "priority": priority,
            "interruptible": interruptible,
            "timestamp": time.time()
        }
        
        # Handle priority insertion
        if priority == "urgent":
            # Insert at the beginning, interrupt current speech if needed
            self.feedback_queue.insert(0, feedback_item)
            if self.interrupt_for_urgent and self.is_speaking_feedback:
                self._interrupt_current_speech()
        elif priority == "high":
            # Insert after any urgent messages
            insert_pos = 0
            for i, item in enumerate(self.feedback_queue):
                if item["priority"] != "urgent":
                    insert_pos = i
                    break
            else:
                insert_pos = len(self.feedback_queue)
            self.feedback_queue.insert(insert_pos, feedback_item)
        else:
            # Normal and low priority go at the end
            self.feedback_queue.append(feedback_item)
        
        # Start processing if not already speaking
        if not self.is_speaking_feedback:
            self._process_feedback_queue()
    
    def _process_feedback_queue(self):
        """Process queued audio feedback messages."""
        if not self.feedback_queue or not self.audio_processor:
            return
        
        feedback_item = self.feedback_queue.pop(0)
        message = feedback_item["message"]
        
        self.is_speaking_feedback = True
        
        try:
            success = self.audio_processor.speak_text(message)
            if success:
                self.logger.info(f"Played audio feedback: {message}")
            else:
                self.logger.error(f"Failed to play audio feedback: {message}")
        except Exception as e:
            self.logger.error(f"Error playing audio feedback: {e}")
        finally:
            self.is_speaking_feedback = False
            
            # Process next item in queue if available
            if self.feedback_queue:
                self._process_feedback_queue()
    
    def _interrupt_current_speech(self):
        """Interrupt currently playing audio feedback."""
        if self.audio_processor and self.is_speaking_feedback:
            try:
                self.audio_processor.stop_speech()
                self.is_speaking_feedback = False
                self.logger.info("Interrupted current audio feedback for urgent message")
            except Exception as e:
                self.logger.error(f"Failed to interrupt current speech: {e}")
    
    def clear_feedback_queue(self):
        """Clear all pending audio feedback messages."""
        self.feedback_queue.clear()
        self.logger.info("Cleared audio feedback queue")
    
    def stop_all_feedback(self):
        """Stop all audio feedback and clear queue."""
        self._interrupt_current_speech()
        self.clear_feedback_queue()
        self.logger.info("Stopped all audio feedback")
    
    def is_feedback_active(self) -> bool:
        """Check if audio feedback is currently active."""
        return self.is_speaking_feedback or len(self.feedback_queue) > 0
    
    def get_feedback_status(self) -> Dict[str, Any]:
        """Get current status of audio feedback system."""
        return {
            "enabled": self.feedback_enabled,
            "speaking": self.is_speaking_feedback,
            "queue_length": len(self.feedback_queue),
            "active_sessions": len(self.active_tool_sessions),
            "streaming_enabled": self.streaming_feedback
        }
    
    def configure_feedback(self, **kwargs):
        """Update audio feedback configuration."""
        config_mapping = {
            "enabled": "feedback_enabled",
            "streaming": "streaming_feedback", 
            "volume": "feedback_volume",
            "interrupt_urgent": "interrupt_for_urgent"
        }
        
        for key, value in kwargs.items():
            if key in config_mapping:
                setattr(self, config_mapping[key], value)
                self.logger.info(f"Updated audio feedback config: {key} = {value}")