from typing import Dict, Any, Optional
import logging
from .intent_classifier import IntentClassifier, IntentType
from .safety_validator import SafetyValidator
from ..tools.tool_registry import ToolRegistry

class IntentProcessor:
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.intent_classifier = IntentClassifier()
        self.safety_validator = SafetyValidator()
        self.tool_registry = ToolRegistry()
        self.logger = logging.getLogger("intent_processor")
    
    def process(self, user_input: str) -> Dict[str, Any]:
        self.logger.info(f"Processing user input: {user_input}")
        
        # Step 1: Classify intent
        intent_result = self.intent_classifier.classify(user_input)
        self.logger.info(f"Intent classified as: {intent_result.intent.value}")
        
        # Step 2: Validate safety
        safety_result = self.safety_validator.validate_intent(intent_result)
        self.logger.info(f"Safety validation: {safety_result.level.value} - Allowed: {safety_result.allowed}")
        
        # Step 3: Handle based on intent and safety
        if not safety_result.allowed:
            return self._handle_blocked_request(intent_result, safety_result)
        
        if intent_result.intent == IntentType.UNSAFE:
            return self._handle_unsafe_request(intent_result, safety_result)
        elif intent_result.intent == IntentType.TOOL_REQUIRED:
            return self._handle_tool_request(intent_result, safety_result)
        else:  # SAFE_RESPONSE
            return self._handle_safe_response(intent_result, safety_result, user_input)
    
    def _handle_blocked_request(self, intent_result, safety_result) -> Dict[str, Any]:
        return {
            "intent": intent_result.intent.value,
            "action": "blocked",
            "response": "I cannot process this request as it appears to be unsafe or inappropriate.",
            "safety_reason": safety_result.reason,
            "confidence": intent_result.confidence
        }
    
    def _handle_unsafe_request(self, intent_result, safety_result) -> Dict[str, Any]:
        return {
            "intent": intent_result.intent.value,
            "action": "refused",
            "response": "I cannot help with this request as it may be unsafe or harmful.",
            "safety_reason": safety_result.reason,
            "confidence": intent_result.confidence
        }
    
    def _handle_tool_request(self, intent_result, safety_result) -> Dict[str, Any]:
        tool_name = intent_result.tool
        tool_args = intent_result.args or {}
        
        self.logger.info(f"Executing tool: {tool_name} with args: {tool_args}")
        
        # Execute the tool
        tool_result = self.tool_registry.execute_tool(tool_name, **tool_args)
        
        if tool_result.success:
            response = self._format_tool_response(tool_name, tool_result.data)
            return {
                "intent": intent_result.intent.value,
                "action": "tool_executed",
                "tool": tool_name,
                "tool_result": tool_result.data,
                "response": response,
                "confidence": intent_result.confidence,
                "safety_level": safety_result.level.value
            }
        else:
            return {
                "intent": intent_result.intent.value,
                "action": "tool_failed",
                "tool": tool_name,
                "error": tool_result.error,
                "response": f"I encountered an error while trying to {tool_name}: {tool_result.error}",
                "confidence": intent_result.confidence
            }
    
    def _handle_safe_response(self, intent_result, safety_result, user_input: str) -> Dict[str, Any]:
        return {
            "intent": intent_result.intent.value,
            "action": "llm_response",
            "user_input": user_input,
            "response": None,  # Will be filled by LLM
            "confidence": intent_result.confidence,
            "safety_level": safety_result.level.value
        }
    
    def _format_tool_response(self, tool_name: str, tool_data: Any) -> str:
        """Format tool results into human-readable responses"""
        
        if tool_name == "web_search":
            return f"I found search results for '{tool_data.get('query', '')}'. Here's what I found: {tool_data.get('results', [{}])[0].get('snippet', 'No results available')}"
        
        elif tool_name == "weather":
            data = tool_data
            return f"The weather in {data.get('location', 'your area')} is {data.get('condition', 'unknown')} with a temperature of {data.get('temperature', 'unknown')}."
        
        elif tool_name == "time":
            return f"The current time is {tool_data.get('formatted', 'unknown')}"
        
        elif tool_name == "calculator":
            return f"The answer is: {tool_data.get('formatted', 'calculation error')}"
        
        elif tool_name == "timer":
            return f"{tool_data.get('message', 'Timer set successfully')}"
        
        else:
            # Generic formatting for unknown tools
            return f"Tool {tool_name} executed successfully: {str(tool_data)}"
    
    def add_custom_pattern(self, pattern):
        """Add custom intent pattern"""
        self.intent_classifier.add_pattern(pattern)
    
    def add_safe_tool(self, tool_name: str):
        """Add tool to safe tools list"""
        self.safety_validator.add_safe_tool(tool_name)
    
    def register_tool(self, tool):
        """Register a new tool"""
        self.tool_registry.register_tool(tool)