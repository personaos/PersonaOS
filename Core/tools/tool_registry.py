from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass
from abc import ABC, abstractmethod
import traceback
import logging

# Import audio feedback system
try:
    from .tool_audio_feedback import ToolAudioFeedback
except ImportError:
    ToolAudioFeedback = None

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