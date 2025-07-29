"""
Example Hello World Plugin for PersonaOS

This is a simple example plugin that demonstrates the PersonaOS plugin architecture,
including tool integration, voice support, and security features.
"""

from core.plugins.base_plugin import BasePlugin, PluginMetadata, PluginType, PluginPermission
from core.tools.tool_registry import ToolResult, VoiceToolContext
from typing import Dict, Any, Optional

class HelloWorldPlugin(BasePlugin):
    """
    Simple example plugin that provides greeting functionality.
    
    This plugin demonstrates:
    - Basic plugin structure and lifecycle
    - Tool execution with voice support
    - Parameter handling and validation
    - Security permissions
    - Voice response formatting
    """
    
    def get_metadata(self) -> PluginMetadata:
        """Return plugin metadata."""
        return PluginMetadata(
            name="hello_world",
            version="1.0.0",
            description="A simple example plugin that provides greeting functionality",
            author="PersonaOS Team",
            plugin_type=PluginType.TOOL,
            permissions=[
                PluginPermission(name="audio.speak", description="Provide audio responses"),
                PluginPermission(name="config.read", description="Read configuration settings")
            ],
            dependencies=[],
            tool_info={
                "name": "hello",
                "description": "Greet the user with a personalized message",
                "supports_voice": True,
                "voice_aliases": ["greet", "say hello", "hello there"],
                "requires_confirmation": False,
                "supports_parameter_collection": True,
                "parameter_specs": [
                    {
                        "name": "name",
                        "type": "string",
                        "required": False,
                        "description": "Name to include in greeting"
                    },
                    {
                        "name": "language",
                        "type": "string", 
                        "required": False,
                        "description": "Language for greeting (en, es, fr)"
                    }
                ]
            }
        )
    
    def on_load(self) -> bool:
        """Called when plugin is loaded."""
        self.logger.info("HelloWorld plugin loaded successfully")
        
        # Initialize plugin state
        self.greetings = {
            "en": "Hello",
            "es": "Hola", 
            "fr": "Bonjour",
            "de": "Hallo",
            "it": "Ciao",
            "pt": "Olá"
        }
        
        return True
    
    def on_activate(self) -> bool:
        """Called when plugin is activated."""
        self.logger.info("HelloWorld plugin activated")
        return True
    
    def on_deactivate(self) -> bool:
        """Called when plugin is deactivated."""
        self.logger.info("HelloWorld plugin deactivated")
        return True
    
    def on_unload(self) -> bool:
        """Called when plugin is unloaded."""
        self.logger.info("HelloWorld plugin unloaded")
        return True
    
    def execute_tool(self, **kwargs) -> Dict[str, Any]:
        """
        Execute the hello tool.
        
        Args:
            **kwargs: Tool parameters including:
                - name: Optional name to greet
                - language: Optional language code
                
        Returns:
            Tool execution result
        """
        try:
            # Get parameters
            name = kwargs.get("name", "there")
            language = kwargs.get("language", "en").lower()
            
            # Get greeting in requested language
            greeting = self.greetings.get(language, self.greetings["en"])
            
            # Create personalized message
            if name and name.lower() != "there":
                message = f"{greeting}, {name}!"
            else:
                message = f"{greeting} there!"
            
            # Add additional context
            result_data = {
                "message": message,
                "greeting": greeting,
                "name": name,
                "language": language,
                "available_languages": list(self.greetings.keys())
            }
            
            return {
                "success": True,
                "data": result_data,
                "message": message
            }
            
        except Exception as e:
            self.logger.error(f"HelloWorld tool execution failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def execute_tool_with_voice(self, voice_context: VoiceToolContext, **kwargs) -> Dict[str, Any]:
        """
        Execute tool with voice context for enhanced voice interaction.
        
        Args:
            voice_context: Voice execution context
            **kwargs: Tool parameters
            
        Returns:
            Tool execution result with voice response
        """
        # Get standard result
        result = self.execute_tool(**kwargs)
        
        if result.get("success", False):
            # Create voice-friendly response
            data = result.get("data", {})
            message = data.get("message", "Hello!")
            
            # Add voice-specific formatting
            voice_response = message
            
            # Add time-based variation for voice
            import time
            current_hour = time.localtime().tm_hour
            
            if current_hour < 12:
                voice_response = f"Good morning! {message}"
            elif current_hour < 17:
                voice_response = f"Good afternoon! {message}"
            else:
                voice_response = f"Good evening! {message}"
            
            # Add confidence acknowledgment if low
            if voice_context.confidence < 0.8:
                voice_response += " I hope I understood you correctly."
            
            result["voice_response"] = voice_response
        
        return result
    
    def format_voice_response(self, data: Any, voice_context: VoiceToolContext) -> str:
        """
        Format result data for voice output.
        
        Args:
            data: Tool execution result data
            voice_context: Voice execution context
            
        Returns:
            Voice-friendly response string
        """
        if isinstance(data, dict) and "message" in data:
            return data["message"]
        
        return "Hello there!"
    
    def parse_voice_parameters(self, voice_text: str) -> Dict[str, Any]:
        """
        Parse voice command to extract parameters.
        
        Args:
            voice_text: Original voice command text
            
        Returns:
            Parsed parameters dictionary
        """
        params = {}
        voice_lower = voice_text.lower()
        
        # Extract name patterns
        name_patterns = [
            r"hello (?:to )?([a-zA-Z]+)",
            r"greet ([a-zA-Z]+)",
            r"say hello to ([a-zA-Z]+)"
        ]
        
        import re
        for pattern in name_patterns:
            match = re.search(pattern, voice_lower)
            if match:
                params["name"] = match.group(1)
                break
        
        # Extract language patterns
        language_patterns = {
            "spanish": "es",
            "french": "fr", 
            "german": "de",
            "italian": "it",
            "portuguese": "pt"
        }
        
        for lang_name, lang_code in language_patterns.items():
            if lang_name in voice_lower:
                params["language"] = lang_code
                break
        
        return params
    
    def validate_tool_args(self, **kwargs) -> bool:
        """
        Validate tool arguments.
        
        Args:
            **kwargs: Arguments to validate
            
        Returns:
            True if arguments are valid
        """
        # Language validation
        language = kwargs.get("language")
        if language and language not in self.greetings:
            return False
        
        # Name validation (basic)
        name = kwargs.get("name")
        if name and len(name) > 50:  # Reasonable name length limit
            return False
        
        return True
    
    def get_voice_confirmation_prompt(self, **kwargs) -> Optional[str]:
        """
        Get confirmation prompt for voice execution.
        
        Args:
            **kwargs: Tool parameters
            
        Returns:
            None (this tool doesn't require confirmation)
        """
        return None  # Simple greeting doesn't need confirmation