from typing import Dict, Any, Optional
import logging
import time
import re
from .intent_classifier import IntentClassifier, IntentType
from .safety_validator import SafetyValidator
from ..tools.tool_registry import ToolRegistry, VoiceToolContext

# Import voice-specific components
try:
    from ..tools.workflow_manager import WorkflowManager
    from ..tools.emergency_controller import EmergencyController
    from ..tools.voice_parameter_collector import VoiceParameterCollector
except ImportError:
    WorkflowManager = None
    EmergencyController = None
    VoiceParameterCollector = None

class IntentProcessor:
    def __init__(self, config: Dict = None, tool_registry: Optional[ToolRegistry] = None, 
                 workflow_manager: Optional[Any] = None, emergency_controller: Optional[Any] = None):
        self.config = config or {}
        self.intent_classifier = IntentClassifier()
        self.safety_validator = SafetyValidator(config)
        
        # Use provided components or create new ones
        self.tool_registry = tool_registry or ToolRegistry()
        self.workflow_manager = workflow_manager
        self.emergency_controller = emergency_controller
        
        self.logger = logging.getLogger("intent_processor")
        
        # Voice-specific intent patterns
        self.voice_intent_patterns = self._load_voice_intent_patterns()
        
        # Intent processing state
        self.active_voice_sessions = {}  # Track voice-specific processing sessions
        
        self.logger.info("IntentProcessor initialized with voice support")
    
    def process(self, user_input: str, input_metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process user input through intent classification and safety validation.
        
        Args:
            user_input: User's input text
            input_metadata: Optional metadata about the input source (voice, web, cli)
            
        Returns:
            Intent processing result dictionary
        """
        input_metadata = input_metadata or {}
        input_type = input_metadata.get("input_type", "text")
        
        self.logger.info(f"Processing {input_type} input: {user_input}")
        
        # Special handling for voice input
        if input_type == "voice":
            return self._process_voice_input(user_input, input_metadata)
        
        # Standard text processing
        return self._process_text_input(user_input, input_metadata)
    
    def _process_text_input(self, user_input: str, input_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Process standard text input through the original pipeline."""
        # Step 1: Classify intent
        intent_result = self.intent_classifier.classify(user_input)
        self.logger.info(f"Intent classified as: {intent_result.intent.value}")
        
        # Step 2: Validate safety (with input source context)
        safety_result = self.safety_validator.validate_intent(intent_result)
        self.logger.info(f"Safety validation: {safety_result.level.value} - Allowed: {safety_result.allowed}")
        
        # Step 3: Handle based on intent and safety
        if not safety_result.allowed:
            return self._handle_blocked_request(intent_result, safety_result, input_metadata)
        
        if intent_result.intent == IntentType.UNSAFE:
            return self._handle_unsafe_request(intent_result, safety_result, input_metadata)
        elif intent_result.intent == IntentType.TOOL_REQUIRED:
            return self._handle_tool_request(intent_result, safety_result, input_metadata)
        else:  # SAFE_RESPONSE
            return self._handle_safe_response(intent_result, safety_result, user_input, input_metadata)
    
    def _process_voice_input(self, user_input: str, input_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Process voice input with enhanced voice-specific intent detection."""
        voice_context = input_metadata.get("voice_context")
        confidence = input_metadata.get("confidence", 1.0)
        
        # Check for emergency triggers first
        if self.emergency_controller and self.emergency_controller.check_emergency_trigger(user_input):
            return {
                "intent": "emergency",
                "action": "emergency_trigger",
                "response": "Emergency stop detected",
                "emergency_trigger": user_input,
                **input_metadata
            }
        
        # Check for voice-specific tool/workflow patterns
        voice_intent = self._classify_voice_intent(user_input, confidence)
        
        if voice_intent["intent_type"] == "voice_tool":
            return self._handle_voice_tool_intent(voice_intent, input_metadata)
        elif voice_intent["intent_type"] == "voice_workflow":
            return self._handle_voice_workflow_intent(voice_intent, input_metadata)
        elif voice_intent["intent_type"] == "parameter_collection":
            return self._handle_parameter_collection_intent(voice_intent, input_metadata)
        else:
            # Fall back to standard processing for non-voice-specific intents
            return self._process_text_input(user_input, input_metadata)
    
    def _handle_blocked_request(self, intent_result, safety_result, input_metadata: Dict[str, Any]) -> Dict[str, Any]:
        response_text = "I cannot process this request as it appears to be unsafe or inappropriate."
        
        # Customize response for voice input
        if input_metadata.get("input_type") == "voice":
            response_text = "I'm sorry, but I cannot process that voice command as it appears to be unsafe or inappropriate."
        
        return {
            "intent": intent_result.intent.value,
            "action": "blocked",
            "response": response_text,
            "safety_reason": safety_result.reason,
            "confidence": intent_result.confidence,
            **input_metadata
        }
    
    def _handle_unsafe_request(self, intent_result, safety_result, input_metadata: Dict[str, Any]) -> Dict[str, Any]:
        response_text = "I cannot help with this request as it may be unsafe or harmful."
        
        # Customize response for voice input
        if input_metadata.get("input_type") == "voice":
            response_text = "I'm sorry, but I cannot help with that voice request as it may be unsafe or harmful."
        
        return {
            "intent": intent_result.intent.value,
            "action": "refused",
            "response": response_text,
            "safety_reason": safety_result.reason,
            "confidence": intent_result.confidence,
            **input_metadata
        }
    
    def _handle_tool_request(self, intent_result, safety_result, input_metadata: Dict[str, Any]) -> Dict[str, Any]:
        tool_name = intent_result.tool
        tool_args = intent_result.args or {}
        
        input_type = input_metadata.get("input_type", "text")
        self.logger.info(f"Executing tool: {tool_name} with args: {tool_args} (via {input_type})")
        
        # For voice input, use voice-aware tool execution if available
        if input_type == "voice" and hasattr(self.tool_registry, 'execute_tool_with_voice'):
            voice_context = VoiceToolContext(
                input_type="voice",
                original_text=input_metadata.get("original_text", ""),
                confidence=input_metadata.get("confidence", 1.0),
                timestamp=time.time(),
                safety_level=self.config.get("safety_level", "standard")
            )
            tool_result = self.tool_registry.execute_tool_with_voice(tool_name, voice_context, **tool_args)
        else:
            # Execute the tool normally
            tool_result = self.tool_registry.execute_tool(tool_name, **tool_args)
        
        if tool_result.success:
            response = self._format_tool_response(tool_name, tool_result.data, input_metadata)
            return {
                "intent": intent_result.intent.value,
                "action": "tool_executed",
                "tool": tool_name,
                "tool_result": tool_result.data,
                "response": response,
                "confidence": intent_result.confidence,
                "safety_level": safety_result.level.value,
                **input_metadata
            }
        else:
            error_response = f"I encountered an error while trying to {tool_name}: {tool_result.error}"
            
            # Customize error response for voice
            if input_type == "voice":
                error_response = f"I'm sorry, but there was an error with the {tool_name} command: {tool_result.error}"
                
            return {
                "intent": intent_result.intent.value,
                "action": "tool_failed",
                "tool": tool_name,
                "error": tool_result.error,
                "response": error_response,
                "confidence": intent_result.confidence,
                **input_metadata
            }
    
    def _handle_safe_response(self, intent_result, safety_result, user_input: str, input_metadata: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "intent": intent_result.intent.value,
            "action": "llm_response",
            "user_input": user_input,
            "response": None,  # Will be filled by LLM
            "confidence": intent_result.confidence,
            "safety_level": safety_result.level.value,
            **input_metadata
        }
    
    def _format_tool_response(self, tool_name: str, tool_data: Any, input_metadata: Dict[str, Any] = None) -> str:
        """Format tool results into human-readable responses, optionally customized for input type."""
        input_metadata = input_metadata or {}
        is_voice = input_metadata.get("input_type") == "voice"
        
        if tool_name == "web_search":
            base_response = f"I found search results for '{tool_data.get('query', '')}'. Here's what I found: {tool_data.get('results', [{}])[0].get('snippet', 'No results available')}"
            return base_response
        
        elif tool_name == "weather":
            data = tool_data
            if is_voice:
                return f"The weather in {data.get('location', 'your area')} is currently {data.get('condition', 'unknown')} with a temperature of {data.get('temperature', 'unknown')}."
            else:
                return f"The weather in {data.get('location', 'your area')} is {data.get('condition', 'unknown')} with a temperature of {data.get('temperature', 'unknown')}."
        
        elif tool_name == "time":
            if is_voice:
                return f"The current time is {tool_data.get('formatted', 'unknown')}"
            else:
                return f"The current time is {tool_data.get('formatted', 'unknown')}"
        
        elif tool_name == "calculator":
            if is_voice:
                return f"The answer is {tool_data.get('formatted', 'calculation error')}"
            else:
                return f"The answer is: {tool_data.get('formatted', 'calculation error')}"
        
        elif tool_name == "timer":
            message = tool_data.get('message', 'Timer set successfully')
            if is_voice:
                return f"Okay, {message.lower()}"
            else:
                return message
        
        else:
            # Generic formatting for unknown tools
            if is_voice:
                return f"I've completed the {tool_name} command successfully"
            else:
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
    
    def _load_voice_intent_patterns(self) -> Dict[str, Any]:
        """Load voice-specific intent patterns."""
        return {
            "emergency_patterns": [
                r"emergency",
                r"stop.*everything",
                r"cancel.*all",
                r"abort.*now",
                r"halt.*system"
            ],
            "tool_patterns": {
                "web_search": [
                    r"search (?:for |about )?(.+)",
                    r"google (.+)",
                    r"look up (.+)",
                    r"find (.+)"
                ],
                "weather": [
                    r"weather (?:in |for |at )?(.+)",
                    r"temperature (?:in |for |at )?(.+)",
                    r"(?:what'?s the weather|weather forecast)"
                ],
                "timer": [
                    r"set (?:a )?timer",
                    r"timer for (.+)",
                    r"countdown (.+)"
                ],
                "calculator": [
                    r"calculate (.+)",
                    r"what is (.+)",
                    r"compute (.+)"
                ]
            },
            "workflow_patterns": {
                "web_research": [
                    r"research (.+) and (?:get|check) weather",
                    r"search (.+) and weather"
                ],
                "calculation_with_timer": [
                    r"calculate (.+) and set timer",
                    r"compute (.+) then timer"
                ]
            },
            "control_patterns": {
                "cancel": [r"cancel", r"stop", r"abort"],
                "pause": [r"pause", r"hold", r"wait"],
                "status": [r"status", r"where are we", r"what step"],
                "help": [r"help", r"what can you do", r"commands"]
            }
        }
    
    def _classify_voice_intent(self, user_input: str, confidence: float) -> Dict[str, Any]:
        """Classify voice input for voice-specific intent patterns."""
        user_lower = user_input.lower().strip()
        
        # Check for emergency patterns
        for pattern in self.voice_intent_patterns["emergency_patterns"]:
            if re.search(pattern, user_lower):
                return {
                    "intent_type": "emergency",
                    "pattern_matched": pattern,
                    "confidence": confidence
                }
        
        # Check for workflow patterns
        for workflow_name, patterns in self.voice_intent_patterns["workflow_patterns"].items():
            for pattern in patterns:
                import re
                match = re.search(pattern, user_lower)
                if match:
                    return {
                        "intent_type": "voice_workflow",
                        "workflow_name": workflow_name,
                        "pattern_matched": pattern,
                        "extracted_params": match.groups(),
                        "confidence": confidence
                    }
        
        # Check for tool patterns
        for tool_name, patterns in self.voice_intent_patterns["tool_patterns"].items():
            for pattern in patterns:
                import re
                match = re.search(pattern, user_lower)
                if match:
                    return {
                        "intent_type": "voice_tool",
                        "tool_name": tool_name,
                        "pattern_matched": pattern,
                        "extracted_params": match.groups(),
                        "confidence": confidence
                    }
        
        # Check for control patterns
        for control_type, patterns in self.voice_intent_patterns["control_patterns"].items():
            for pattern in patterns:
                if re.search(pattern, user_lower):
                    return {
                        "intent_type": "voice_control",
                        "control_type": control_type,
                        "pattern_matched": pattern,
                        "confidence": confidence
                    }
        
        # Default to standard text processing
        return {
            "intent_type": "standard",
            "confidence": confidence
        }
    
    def _handle_voice_tool_intent(self, voice_intent: Dict[str, Any], input_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Handle voice-specific tool execution intent."""
        tool_name = voice_intent["tool_name"]
        extracted_params = voice_intent.get("extracted_params", [])
        
        # Create voice context
        voice_context = VoiceToolContext(
            input_type="voice",
            original_text=input_metadata.get("original_text", ""),
            confidence=voice_intent["confidence"],
            timestamp=time.time(),
            safety_level=self.config.get("safety_level", "standard")
        )
        
        # Build tool parameters from extracted data
        tool_params = self._build_tool_params(tool_name, extracted_params)
        
        self.logger.info(f"Voice tool intent: {tool_name} with params: {tool_params}")
        
        # Validate with voice safety validator
        if hasattr(self.safety_validator, 'validate_voice_tool_execution'):
            safety_result = self.safety_validator.validate_voice_tool_execution(
                tool_name, tool_params, voice_context
            )
            
            if not safety_result.allowed:
                return {
                    "intent": "voice_tool",
                    "action": "blocked",
                    "tool_name": tool_name,
                    "response": safety_result.voice_warning_message or safety_result.reason,
                    "safety_reason": safety_result.reason,
                    **input_metadata
                }
        
        # Check if parameter collection is needed
        tool = self.tool_registry.get_tool(tool_name)
        if tool and hasattr(tool, 'requires_parameter_collection') and tool.requires_parameter_collection(**tool_params):
            # Start parameter collection
            if hasattr(self.tool_registry, 'execute_tool_with_parameter_collection'):
                collection_result = self.tool_registry.execute_tool_with_parameter_collection(
                    tool_name, voice_context, tool_params
                )
                
                return {
                    "intent": "voice_tool",
                    "action": "parameter_collection_started",
                    "tool_name": tool_name,
                    "collection_result": collection_result,
                    **input_metadata
                }
        
        # Execute tool directly
        if hasattr(self.tool_registry, 'execute_tool_with_voice'):
            tool_result = self.tool_registry.execute_tool_with_voice(tool_name, voice_context, **tool_params)
        else:
            tool_result = self.tool_registry.execute_tool(tool_name, **tool_params)
        
        if tool_result.success:
            response = tool_result.voice_response or self._format_tool_response(tool_name, tool_result.data, input_metadata)
            return {
                "intent": "voice_tool",
                "action": "tool_executed",
                "tool_name": tool_name,
                "tool_result": tool_result.data,
                "response": response,
                "confidence": voice_intent["confidence"],
                **input_metadata
            }
        else:
            error_response = tool_result.voice_response or f"I encountered an error with {tool_name}: {tool_result.error}"
            return {
                "intent": "voice_tool",
                "action": "tool_failed",
                "tool_name": tool_name,
                "error": tool_result.error,
                "response": error_response,
                "confidence": voice_intent["confidence"],
                **input_metadata
            }
    
    def _handle_voice_workflow_intent(self, voice_intent: Dict[str, Any], input_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Handle voice workflow initiation intent."""
        workflow_name = voice_intent["workflow_name"]
        extracted_params = voice_intent.get("extracted_params", [])
        
        if not self.workflow_manager:
            return {
                "intent": "voice_workflow",
                "action": "workflow_unavailable",
                "response": "Workflow functionality is not available",
                **input_metadata
            }
        
        # Create voice context
        voice_context = VoiceToolContext(
            input_type="voice",
            original_text=input_metadata.get("original_text", ""),
            confidence=voice_intent["confidence"],
            timestamp=time.time(),
            safety_level=self.config.get("safety_level", "standard")
        )
        
        # Build initial parameters from extracted data
        initial_params = self._build_workflow_params(workflow_name, extracted_params)
        
        self.logger.info(f"Voice workflow intent: {workflow_name} with initial params: {initial_params}")
        
        try:
            # Initiate workflow
            workflow_id = self.workflow_manager.initiate_workflow(
                workflow_name, voice_context, initial_params
            )
            
            return {
                "intent": "voice_workflow",
                "action": "workflow_initiated",
                "workflow_name": workflow_name,
                "workflow_id": workflow_id,
                "response": f"Starting {workflow_name} workflow",
                "confidence": voice_intent["confidence"],
                **input_metadata
            }
            
        except Exception as e:
            self.logger.error(f"Failed to initiate workflow {workflow_name}: {e}")
            return {
                "intent": "voice_workflow",
                "action": "workflow_failed",
                "workflow_name": workflow_name,
                "error": str(e),
                "response": f"Failed to start {workflow_name} workflow",
                **input_metadata
            }
    
    def _handle_parameter_collection_intent(self, voice_intent: Dict[str, Any], input_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Handle parameter collection continuation."""
        session_id = input_metadata.get("parameter_session_id")
        voice_input = input_metadata.get("original_text", "")
        confidence = voice_intent["confidence"]
        
        if not session_id or not hasattr(self.tool_registry, 'continue_parameter_collection'):
            return {
                "intent": "parameter_collection",
                "action": "collection_unavailable",
                "response": "Parameter collection is not available",
                **input_metadata
            }
        
        # Continue parameter collection
        collection_result = self.tool_registry.continue_parameter_collection(
            session_id, voice_input, confidence
        )
        
        return {
            "intent": "parameter_collection",
            "action": collection_result.get("action", "collection_continued"),
            "session_id": session_id,
            "collection_result": collection_result,
            **input_metadata
        }
    
    def _build_tool_params(self, tool_name: str, extracted_params: list) -> Dict[str, Any]:
        """Build tool parameters from extracted voice patterns."""
        params = {}
        
        if tool_name == "web_search" and extracted_params:
            params["query"] = extracted_params[0].strip()
        elif tool_name == "weather" and extracted_params:
            params["location"] = extracted_params[0].strip()
        elif tool_name == "calculator" and extracted_params:
            params["expression"] = extracted_params[0].strip()
        elif tool_name == "timer" and extracted_params:
            # Parse timer duration
            duration_text = extracted_params[0].strip()
            import re
            duration_match = re.search(r'(\d+)\s+(second|minute|hour)s?', duration_text.lower())
            if duration_match:
                params["duration"] = int(duration_match.group(1))
                params["unit"] = duration_match.group(2)
        
        return params
    
    def _build_workflow_params(self, workflow_name: str, extracted_params: list) -> Dict[str, Any]:
        """Build workflow parameters from extracted voice patterns."""
        params = {}
        
        if workflow_name == "web_research" and extracted_params:
            params["query"] = extracted_params[0].strip()
        elif workflow_name == "calculation_with_timer" and extracted_params:
            params["expression"] = extracted_params[0].strip()
        
        return params
    
    def process_voice_continuation(self, user_input: str, session_context: Dict[str, Any]) -> Dict[str, Any]:
        """Process voice input as continuation of an existing session."""
        session_type = session_context.get("session_type")
        session_id = session_context.get("session_id")
        
        input_metadata = {
            "input_type": "voice",
            "original_text": user_input,
            "session_context": session_context,
            **session_context
        }
        
        if session_type == "parameter_collection":
            input_metadata["parameter_session_id"] = session_id
            voice_intent = {"intent_type": "parameter_collection", "confidence": 1.0}
            return self._handle_parameter_collection_intent(voice_intent, input_metadata)
        
        elif session_type == "workflow":
            # Handle workflow continuation through workflow manager
            if self.workflow_manager and hasattr(self.workflow_manager, 'continue_workflow'):
                voice_context = VoiceToolContext(
                    input_type="voice",
                    original_text=user_input,
                    confidence=1.0,
                    timestamp=time.time()
                )
                
                workflow_result = self.workflow_manager.continue_workflow(
                    session_id, user_input, voice_context
                )
                
                return {
                    "intent": "voice_workflow_continuation",
                    "action": workflow_result.get("action", "workflow_continued"),
                    "session_id": session_id,
                    "workflow_result": workflow_result,
                    **input_metadata
                }
        
        # Default to regular processing
        return self.process(user_input, input_metadata)