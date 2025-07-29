from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass
from abc import ABC, abstractmethod
import traceback
import logging
import time

# Import audio feedback system
try:
    from .tool_audio_feedback import ToolAudioFeedback
except ImportError:
    ToolAudioFeedback = None

# Import voice parameter collector
try:
    from .voice_parameter_collector import VoiceParameterCollector, ParameterSpec, ParameterType
except ImportError:
    VoiceParameterCollector = None
    ParameterSpec = None
    ParameterType = None

@dataclass
class ToolResult:
    success: bool
    data: Any = None
    error: Optional[str] = None
    metadata: Optional[Dict] = None
    voice_response: Optional[str] = None  # Customized response for voice output

@dataclass
class VoiceToolContext:
    """Context information for voice-initiated tool execution."""
    input_type: str = "voice"
    original_text: str = ""
    confidence: float = 1.0
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    timestamp: float = 0.0
    safety_level: str = "standard"
    requires_confirmation: bool = False

class BaseTool(ABC):
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.logger = logging.getLogger(f"tool.{name}")
        
        # Voice-specific properties
        self.supports_voice = True
        self.voice_aliases = []  # Alternative names for voice commands
        self.requires_confirmation = False  # Whether voice execution needs confirmation
        self.voice_parameter_patterns = {}  # Patterns for parsing voice parameters
        self.parameter_specs = []  # Parameter specifications for voice collection
        self.supports_parameter_collection = False  # Whether tool supports advanced parameter collection
    
    @abstractmethod
    def execute(self, **kwargs) -> ToolResult:
        pass
    
    def execute_with_voice_context(self, voice_context: VoiceToolContext, **kwargs) -> ToolResult:
        """
        Execute tool with voice context information.
        
        Args:
            voice_context: Voice execution context
            **kwargs: Tool parameters
            
        Returns:
            ToolResult with voice-specific formatting
        """
        self.logger.info(f"Executing {self.name} via voice: '{voice_context.original_text}'")
        
        # Add voice context to metadata
        kwargs['_voice_context'] = voice_context
        
        # Execute the tool
        result = self.execute(**kwargs)
        
        # Enhance result with voice-specific response if not already provided
        if result.success and not result.voice_response:
            result.voice_response = self.format_voice_response(result.data, voice_context)
        
        return result
    
    def format_voice_response(self, data: Any, voice_context: VoiceToolContext) -> str:
        """
        Format tool result data for voice output.
        
        Args:
            data: Tool execution result data
            voice_context: Voice execution context
            
        Returns:
            Human-friendly voice response
        """
        # Default implementation - subclasses can override for custom formatting
        if data is None:
            return f"{self.name} completed successfully"
        elif isinstance(data, dict):
            if 'message' in data:
                return str(data['message'])
            elif 'formatted' in data:
                return str(data['formatted'])
            else:
                return f"{self.name} completed with result"
        else:
            return f"{self.name} result: {str(data)}"
    
    def validate_args(self, **kwargs) -> bool:
        return True
    
    def parse_voice_parameters(self, voice_text: str) -> Dict[str, Any]:
        """
        Parse voice command text to extract tool parameters.
        
        Args:
            voice_text: Original voice command text
            
        Returns:
            Dictionary of parsed parameters
        """
        # Default implementation - subclasses can override for custom parsing
        return {}
    
    def get_voice_confirmation_prompt(self, **kwargs) -> Optional[str]:
        """
        Get confirmation prompt for voice execution if required.
        
        Args:
            **kwargs: Tool parameters
            
        Returns:
            Confirmation prompt or None if no confirmation needed
        """
        if not self.requires_confirmation:
            return None
        
        return f"Are you sure you want to execute {self.name}?"
    
    def get_parameter_specs(self) -> List:
        """
        Get parameter specifications for voice collection.
        
        Returns:
            List of ParameterSpec objects
        """
        return self.parameter_specs
    
    def requires_parameter_collection(self, **kwargs) -> bool:
        """
        Check if this tool requires parameter collection.
        
        Args:
            **kwargs: Current tool parameters
            
        Returns:
            True if parameter collection is needed
        """
        if not self.supports_parameter_collection or not self.parameter_specs:
            return False
        
        # Check if any required parameters are missing
        for param_spec in self.parameter_specs:
            if param_spec.required and param_spec.name not in kwargs:
                return True
        
        return False
    
    def validate_collected_parameters(self, collected_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate collected parameters against specifications.
        
        Args:
            collected_params: Parameters collected via voice
            
        Returns:
            Validation result dictionary
        """
        validation_errors = []
        
        for param_spec in self.parameter_specs:
            param_name = param_spec.name
            
            if param_spec.required and param_name not in collected_params:
                validation_errors.append(f"Required parameter '{param_name}' is missing")
                continue
            
            if param_name in collected_params:
                value = collected_params[param_name]
                
                # Type-specific validation would go here
                # This is a basic implementation
                if param_spec.param_type.value == "integer" and not isinstance(value, int):
                    try:
                        collected_params[param_name] = int(value)
                    except (ValueError, TypeError):
                        validation_errors.append(f"Parameter '{param_name}' must be an integer")
                
                elif param_spec.param_type.value == "float" and not isinstance(value, (int, float)):
                    try:
                        collected_params[param_name] = float(value)
                    except (ValueError, TypeError):
                        validation_errors.append(f"Parameter '{param_name}' must be a number")
        
        return {
            "valid": len(validation_errors) == 0,
            "errors": validation_errors,
            "validated_params": collected_params
        }

class ToolRegistry:
    def __init__(self, audio_processor=None, config: Optional[Dict] = None):
        self.tools: Dict[str, BaseTool] = {}
        self.logger = logging.getLogger("tool_registry")
        self.audio_processor = audio_processor
        self.config = config or {}
        
        # Initialize audio feedback system if available
        self.audio_feedback = None
        if ToolAudioFeedback and audio_processor:
            try:
                self.audio_feedback = ToolAudioFeedback(audio_processor, config)
                self.logger.info("Tool audio feedback system initialized")
            except Exception as e:
                self.logger.warning(f"Failed to initialize audio feedback: {e}")
        
        # Initialize voice parameter collector if available
        self.parameter_collector = None
        if VoiceParameterCollector:
            try:
                self.parameter_collector = VoiceParameterCollector(self.audio_feedback, config)
                self.logger.info("Voice parameter collector initialized")
            except Exception as e:
                self.logger.warning(f"Failed to initialize voice parameter collector: {e}")
        
        self._register_default_tools()
    
    def register_tool(self, tool: BaseTool):
        self.tools[tool.name] = tool
        self.logger.info(f"Registered tool: {tool.name}")
        
        # If audio feedback is available, let it know about new tools
        if self.audio_feedback and hasattr(tool, 'supports_voice') and tool.supports_voice:
            self.logger.info(f"Tool {tool.name} registered with voice support")
    
    def get_tool(self, name: str) -> Optional[BaseTool]:
        return self.tools.get(name)
    
    def list_tools(self) -> List[str]:
        return list(self.tools.keys())
    
    def execute_tool(self, name: str, **kwargs) -> ToolResult:
        """Execute a tool with standard (non-voice) execution."""
        tool = self.get_tool(name)
        if not tool:
            return ToolResult(
                success=False,
                error=f"Tool '{name}' not found"
            )
        
        try:
            if not tool.validate_args(**kwargs):
                return ToolResult(
                    success=False,
                    error=f"Invalid arguments for tool '{name}'"
                )
            
            self.logger.info(f"Executing tool: {name} with args: {kwargs}")
            result = tool.execute(**kwargs)
            self.logger.info(f"Tool {name} completed successfully: {result.success}")
            return result
            
        except Exception as e:
            error_msg = f"Error executing tool '{name}': {str(e)}"
            self.logger.error(f"{error_msg}\n{traceback.format_exc()}")
            return ToolResult(
                success=False,
                error=error_msg
            )
    
    def execute_tool_with_voice(self, name: str, voice_context: VoiceToolContext, **kwargs) -> ToolResult:
        """
        Execute a tool with voice context information and audio feedback.
        
        Args:
            name: Tool name
            voice_context: Voice execution context
            **kwargs: Tool parameters
            
        Returns:
            ToolResult with voice-specific formatting
        """
        tool = self.get_tool(name)
        if not tool:
            error_result = ToolResult(
                success=False,
                error=f"Tool '{name}' not found",
                voice_response=f"I couldn't find the {name} tool."
            )
            
            # Announce error via audio feedback
            if self.audio_feedback:
                self.audio_feedback._queue_audio_feedback(
                    error_result.voice_response, "high", True
                )
            
            return error_result
        
        if not tool.supports_voice:
            error_result = ToolResult(
                success=False,
                error=f"Tool '{name}' does not support voice execution",
                voice_response=f"The {name} tool cannot be used with voice commands."
            )
            
            # Announce error via audio feedback
            if self.audio_feedback:
                self.audio_feedback._queue_audio_feedback(
                    error_result.voice_response, "high", True
                )
            
            return error_result
        
        try:
            if not tool.validate_args(**kwargs):
                error_result = ToolResult(
                    success=False,
                    error=f"Invalid arguments for tool '{name}'",
                    voice_response=f"The parameters for {name} are not valid."
                )
                
                # Announce error via audio feedback
                if self.audio_feedback:
                    self.audio_feedback._queue_audio_feedback(
                        error_result.voice_response, "high", True
                    )
                
                return error_result
            
            self.logger.info(f"Executing tool via voice: {name} with args: {kwargs}")
            
            # Announce tool execution start
            session_id = None
            if self.audio_feedback:
                session_id = self.audio_feedback.announce_tool_execution_start(
                    name, kwargs, voice_context
                )
            
            # Execute the tool
            result = tool.execute_with_voice_context(voice_context, **kwargs)
            self.logger.info(f"Voice tool {name} completed: {result.success}")
            
            # Announce completion with results
            if self.audio_feedback and session_id:
                self.audio_feedback.announce_tool_execution_completion(session_id, result)
            
            return result
            
        except Exception as e:
            error_msg = f"Error executing voice tool '{name}': {str(e)}"
            self.logger.error(f"{error_msg}\n{traceback.format_exc()}")
            
            error_result = ToolResult(
                success=False,
                error=error_msg,
                voice_response=f"I encountered an error while running {name}. {str(e)}"
            )
            
            # Announce error via audio feedback
            if self.audio_feedback:
                self.audio_feedback._queue_audio_feedback(
                    error_result.voice_response, "high", True
                )
            
            return error_result
    
    def find_tool_by_voice_command(self, voice_text: str) -> Optional[str]:
        """
        Find tool name from voice command text.
        
        Args:
            voice_text: Voice command text
            
        Returns:
            Tool name if found, None otherwise
        """
        voice_lower = voice_text.lower()
        
        # First check exact tool names
        for tool_name in self.tools.keys():
            if tool_name in voice_lower:
                return tool_name
        
        # Then check voice aliases
        for tool_name, tool in self.tools.items():
            for alias in tool.voice_aliases:
                if alias.lower() in voice_lower:
                    return tool_name
        
        return None
    
    def get_voice_enabled_tools(self) -> List[str]:
        """
        Get list of tools that support voice execution.
        
        Returns:
            List of voice-enabled tool names
        """
        return [name for name, tool in self.tools.items() if tool.supports_voice]
    
    def announce_confirmation_required(self, tool_name: str, confirmation_message: str, voice_context: Optional[VoiceToolContext] = None):
        """
        Announce that user confirmation is required for a tool.
        
        Args:
            tool_name: Name of the tool requiring confirmation
            confirmation_message: Confirmation prompt message
            voice_context: Voice execution context if applicable
        """
        if self.audio_feedback:
            self.audio_feedback.announce_confirmation_required(
                tool_name, confirmation_message, voice_context
            )
    
    def cancel_tool_execution(self, session_id: str, reason: str = "User requested cancellation"):
        """
        Cancel an ongoing tool execution.
        
        Args:
            session_id: Tool execution session ID
            reason: Reason for cancellation
        """
        if self.audio_feedback:
            self.audio_feedback.announce_tool_cancellation(session_id, reason)
    
    def get_audio_feedback_status(self) -> Dict[str, Any]:
        """
        Get status of the tool audio feedback system.
        
        Returns:
            Dictionary with feedback system status
        """
        if self.audio_feedback:
            return self.audio_feedback.get_feedback_status()
        return {"enabled": False, "available": False}
    
    def configure_audio_feedback(self, **kwargs):
        """
        Configure tool audio feedback settings.
        
        Args:
            **kwargs: Configuration parameters
        """
        if self.audio_feedback:
            self.audio_feedback.configure_feedback(**kwargs)
        else:
            self.logger.warning("Audio feedback system not available for configuration")
    
    def execute_tool_with_parameter_collection(self, tool_name: str, voice_context: VoiceToolContext, 
                                              initial_params: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Execute a tool with voice parameter collection if needed.
        
        Args:
            tool_name: Name of the tool to execute
            voice_context: Voice execution context
            initial_params: Initial parameters if any
            
        Returns:
            Execution result or parameter collection session info
        """
        tool = self.get_tool(tool_name)
        if not tool:
            return {
                "success": False,
                "error": f"Tool '{tool_name}' not found",
                "action": "tool_not_found"
            }
        
        if not tool.supports_voice:
            return {
                "success": False,
                "error": f"Tool '{tool_name}' does not support voice execution",
                "action": "voice_not_supported"
            }
        
        current_params = initial_params or {}
        
        # Check if parameter collection is needed
        if tool.requires_parameter_collection(**current_params):
            if not self.parameter_collector:
                return {
                    "success": False,
                    "error": "Parameter collection not available",
                    "action": "parameter_collection_unavailable"
                }
            
            # Start parameter collection session
            session_id = f"{tool_name}_{int(time.time())}"
            
            collection_result = self.parameter_collector.start_collection_session(
                session_id, tool_name, tool.get_parameter_specs(), voice_context
            )
            
            if collection_result["success"]:
                return {
                    "success": True,
                    "action": "parameter_collection_started",
                    "session_id": session_id,
                    "tool_name": tool_name,
                    "collection_result": collection_result
                }
            else:
                return {
                    "success": False,
                    "error": collection_result.get("error", "Failed to start parameter collection"),
                    "action": "parameter_collection_failed"
                }
        
        # All parameters available, execute tool normally
        return self.execute_tool_with_voice(tool_name, voice_context, **current_params)
    
    def continue_parameter_collection(self, session_id: str, voice_input: str, 
                                    confidence: float = 1.0) -> Dict[str, Any]:
        """
        Continue parameter collection with voice input.
        
        Args:
            session_id: Parameter collection session ID
            voice_input: Voice input text
            confidence: Voice recognition confidence
            
        Returns:
            Collection continuation result
        """
        if not self.parameter_collector:
            return {
                "success": False,
                "error": "Parameter collection not available",
                "action": "parameter_collection_unavailable"
            }
        
        collection_result = self.parameter_collector.collect_parameter_value(
            session_id, voice_input, confidence
        )
        
        # Check if collection is completed
        if collection_result.get("action") == "collection_completed":
            # Execute the tool with collected parameters
            tool_name = collection_result["tool_name"]
            collected_params = collection_result["collected_parameters"]
            
            # Get the session info to retrieve voice context
            session_status = self.parameter_collector.get_session_status(session_id)
            if session_status:
                session = self.parameter_collector.active_sessions.get(session_id)
                if session and session.voice_context:
                    # Execute tool with collected parameters
                    execution_result = self.execute_tool_with_voice(
                        tool_name, session.voice_context, **collected_params
                    )
                    
                    return {
                        "success": True,
                        "action": "tool_executed_after_collection",
                        "tool_name": tool_name,
                        "collected_parameters": collected_params,
                        "execution_result": execution_result
                    }
        
        return collection_result
    
    def cancel_parameter_collection(self, session_id: str, reason: str = "User cancelled") -> Dict[str, Any]:
        """
        Cancel an active parameter collection session.
        
        Args:
            session_id: Session ID to cancel
            reason: Cancellation reason
            
        Returns:
            Cancellation result
        """
        if not self.parameter_collector:
            return {
                "success": False,
                "error": "Parameter collection not available"
            }
        
        return self.parameter_collector.cancel_collection_session(session_id, reason)
    
    def get_parameter_collection_status(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get status of a parameter collection session.
        
        Args:
            session_id: Session ID
            
        Returns:
            Session status or None if not found
        """
        if not self.parameter_collector:
            return None
        
        return self.parameter_collector.get_session_status(session_id)
    
    def list_parameter_collection_sessions(self) -> List[Dict[str, Any]]:
        """
        List all active parameter collection sessions.
        
        Returns:
            List of active sessions
        """
        if not self.parameter_collector:
            return []
        
        return self.parameter_collector.list_active_sessions()
    
    def _register_default_tools(self):
        from .basic_tools import (
            WebSearchTool, WeatherTool, TimeTool, 
            CalculatorTool, TimerTool
        )
        
        default_tools = [
            WebSearchTool(),
            WeatherTool(),
            TimeTool(),
            CalculatorTool(),
            TimerTool()
        ]
        
        for tool in default_tools:
            self.register_tool(tool)
    
    def cleanup(self):
        """Clean up tool registry resources."""
        if self.audio_feedback:
            self.audio_feedback.stop_all_feedback()
        self.logger.info("Tool registry cleaned up")