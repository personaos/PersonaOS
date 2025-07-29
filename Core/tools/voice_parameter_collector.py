"""
Voice Parameter Collector

This module handles sophisticated voice-based parameter collection for tools,
including multi-turn conversations, validation, and confirmation dialogs.
"""

import time
import re
from typing import Dict, Any, Optional, List, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
import logging

class ParameterType(Enum):
    """Types of parameters that can be collected via voice."""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    EMAIL = "email"
    URL = "url"
    FILE_PATH = "file_path"
    DATE = "date"
    TIME = "time"
    DURATION = "duration"
    CHOICE = "choice"
    LIST = "list"

class CollectionState(Enum):
    """States of parameter collection process."""
    WAITING = "waiting"
    COLLECTING = "collecting"
    VALIDATING = "validating"
    CONFIRMING = "confirming"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class ParameterSpec:
    """Specification for a parameter to be collected."""
    name: str
    param_type: ParameterType
    required: bool = True
    description: str = ""
    validation_rules: Dict[str, Any] = field(default_factory=dict)
    voice_prompts: List[str] = field(default_factory=list)
    confirmation_required: bool = False
    choices: Optional[List[str]] = None
    default_value: Optional[Any] = None
    sensitive: bool = False  # For passwords, API keys, etc.

@dataclass
class CollectionSession:
    """Active parameter collection session."""
    session_id: str
    tool_name: str
    parameters_spec: List[ParameterSpec]
    collected_values: Dict[str, Any] = field(default_factory=dict)
    current_parameter_index: int = 0
    state: CollectionState = CollectionState.WAITING
    attempt_count: int = 0
    max_attempts: int = 3
    started_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    voice_context: Optional[Any] = None

class VoiceParameterCollector:
    """
    Collects tool parameters through voice interaction with validation and confirmation.
    """
    
    def __init__(self, audio_feedback=None, config: Optional[Dict] = None):
        """
        Initialize voice parameter collector.
        
        Args:
            audio_feedback: Audio feedback system
            config: Configuration dictionary
        """
        self.audio_feedback = audio_feedback
        self.config = config or {}
        self.logger = logging.getLogger("voice_parameter_collector")
        
        # Active collection sessions
        self.active_sessions: Dict[str, CollectionSession] = {}
        
        # Collection settings
        self.collection_timeout = self.config.get("parameter_collection_timeout", 300)  # 5 minutes
        self.max_collection_attempts = self.config.get("max_parameter_attempts", 3)
        self.confirmation_threshold = self.config.get("confirmation_confidence_threshold", 0.8)
        
        # Voice patterns for parameter types
        self.parameter_patterns = self._load_parameter_patterns()
        
        # Validation rules
        self.validation_rules = self._load_validation_rules()
        
        self.logger.info("VoiceParameterCollector initialized")
    
    def _load_parameter_patterns(self) -> Dict[ParameterType, List[str]]:
        """Load voice patterns for different parameter types."""
        return {
            ParameterType.STRING: [
                r"(.+)",  # Accept any text
            ],
            ParameterType.INTEGER: [
                r"(\d+)",
                r"(\d{1,3}(?:,\d{3})*)",  # With commas
                r"(zero|one|two|three|four|five|six|seven|eight|nine|ten)",
                r"(negative\s+\d+)",
                r"(minus\s+\d+)"
            ],
            ParameterType.FLOAT: [
                r"(\d+\.?\d*)",
                r"(\d*\.\d+)",
                r"(negative\s+\d+\.?\d*)",
                r"(minus\s+\d+\.?\d*)"
            ],
            ParameterType.BOOLEAN: [
                r"(yes|yeah|yep|true|correct|right|affirmative)",
                r"(no|nope|false|wrong|negative|incorrect)"
            ],
            ParameterType.EMAIL: [
                r"([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})",
                r"([a-zA-Z0-9._%+-]+\s+at\s+[a-zA-Z0-9.-]+\s+dot\s+[a-zA-Z]{2,})"
            ],
            ParameterType.URL: [
                r"(https?://[^\s]+)",
                r"(www\.[^\s]+)",
                r"([a-zA-Z0-9.-]+\.[a-zA-Z]{2,}[^\s]*)"
            ],
            ParameterType.FILE_PATH: [
                r"([/\\]?[^/\\]+[/\\][^/\\]*)",
                r"([a-zA-Z]:[/\\][^/\\]*)",
                r"(~[/\\][^/\\]*)",
                r"(\./[^/\\]*)"
            ],
            ParameterType.DURATION: [
                r"(\d+)\s+(second|minute|hour|day)s?",
                r"(\d+)\s+(sec|min|hr)s?",
                r"(\d+:\d+(?::\d+)?)"  # HH:MM or HH:MM:SS
            ]
        }
    
    def _load_validation_rules(self) -> Dict[str, Callable]:
        """Load validation functions for different parameter types."""
        return {
            "min_length": lambda value, min_len: len(str(value)) >= min_len,
            "max_length": lambda value, max_len: len(str(value)) <= max_len,
            "min_value": lambda value, min_val: float(value) >= min_val,
            "max_value": lambda value, max_val: float(value) <= max_val,
            "pattern": lambda value, pattern: re.match(pattern, str(value)) is not None,
            "choices": lambda value, choices: str(value).lower() in [c.lower() for c in choices],
            "email_format": lambda value, _: re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', str(value)) is not None,
            "url_format": lambda value, _: re.match(r'^https?://[^\s]+$', str(value)) is not None or re.match(r'^www\.[^\s]+$', str(value)) is not None
        }
    
    def start_collection_session(self, session_id: str, tool_name: str, 
                                parameters_spec: List[ParameterSpec], 
                                voice_context: Optional[Any] = None) -> Dict[str, Any]:
        """
        Start a new parameter collection session.
        
        Args:
            session_id: Unique session identifier
            tool_name: Name of the tool requiring parameters
            parameters_spec: List of parameter specifications
            voice_context: Voice execution context
            
        Returns:
            Session start result
        """
        if session_id in self.active_sessions:
            return {
                "success": False,
                "error": "Session already exists",
                "session_id": session_id
            }
        
        # Create collection session
        session = CollectionSession(
            session_id=session_id,
            tool_name=tool_name,
            parameters_spec=parameters_spec,
            voice_context=voice_context,
            max_attempts=self.max_collection_attempts
        )
        
        self.active_sessions[session_id] = session
        
        self.logger.info(f"Started parameter collection session {session_id} for {tool_name}")
        
        # Begin collecting first parameter
        return self._begin_parameter_collection(session_id)
    
    def _begin_parameter_collection(self, session_id: str) -> Dict[str, Any]:
        """Begin collecting the next parameter in the session."""
        session = self.active_sessions.get(session_id)
        if not session:
            return {"success": False, "error": "Session not found"}
        
        # Check if all parameters collected
        if session.current_parameter_index >= len(session.parameters_spec):
            return self._complete_collection_session(session_id)
        
        current_param = session.parameters_spec[session.current_parameter_index]
        session.state = CollectionState.COLLECTING
        session.attempt_count = 0
        session.updated_at = time.time()
        
        # Generate collection prompt
        prompt = self._generate_collection_prompt(current_param, session)
        
        # Announce parameter request
        if self.audio_feedback:
            self.audio_feedback._queue_audio_feedback(prompt, "normal", False)
        
        self.logger.info(f"Collecting parameter '{current_param.name}' for session {session_id}")
        
        return {
            "success": True,
            "action": "parameter_collection_started",
            "session_id": session_id,
            "parameter_name": current_param.name,
            "parameter_type": current_param.param_type.value,
            "prompt": prompt,
            "attempt": session.attempt_count + 1,
            "max_attempts": session.max_attempts
        }
    
    def collect_parameter_value(self, session_id: str, voice_input: str, 
                               confidence: float = 1.0) -> Dict[str, Any]:
        """
        Process voice input for parameter collection.
        
        Args:
            session_id: Collection session ID
            voice_input: Voice input text
            confidence: Voice recognition confidence
            
        Returns:
            Collection result
        """
        session = self.active_sessions.get(session_id)
        if not session:
            return {"success": False, "error": "Session not found"}
        
        if session.state not in [CollectionState.COLLECTING, CollectionState.CONFIRMING]:
            return {
                "success": False, 
                "error": f"Invalid session state: {session.state.value}"
            }
        
        current_param = session.parameters_spec[session.current_parameter_index]
        session.attempt_count += 1
        session.updated_at = time.time()
        
        self.logger.info(f"Processing voice input for parameter '{current_param.name}': '{voice_input}'")
        
        # Handle confirmation state
        if session.state == CollectionState.CONFIRMING:
            return self._handle_confirmation_response(session_id, voice_input, confidence)
        
        # Parse parameter value from voice input
        parsed_value = self._parse_parameter_value(voice_input, current_param, confidence)
        
        if parsed_value is None:
            return self._handle_collection_failure(session_id, "Could not understand the value")
        
        # Validate the parsed value
        validation_result = self._validate_parameter_value(parsed_value, current_param)
        
        if not validation_result["valid"]:
            return self._handle_collection_failure(session_id, validation_result["error"])
        
        # Store the collected value
        session.collected_values[current_param.name] = parsed_value
        
        # Check if confirmation is required
        if current_param.confirmation_required or confidence < self.confirmation_threshold:
            return self._request_parameter_confirmation(session_id, current_param, parsed_value)
        
        # Move to next parameter
        return self._advance_to_next_parameter(session_id)
    
    def _parse_parameter_value(self, voice_input: str, param_spec: ParameterSpec, 
                              confidence: float) -> Optional[Any]:
        """Parse parameter value from voice input based on parameter type."""
        voice_lower = voice_input.lower().strip()
        
        # Handle special cases first
        if param_spec.param_type == ParameterType.BOOLEAN:
            positive_patterns = ["yes", "yeah", "yep", "true", "correct", "right", "affirmative", "on", "enable"]
            negative_patterns = ["no", "nope", "false", "wrong", "negative", "incorrect", "off", "disable"]
            
            if any(pattern in voice_lower for pattern in positive_patterns):
                return True
            elif any(pattern in voice_lower for pattern in negative_patterns):
                return False
            else:
                return None
        
        # Handle choice parameters
        if param_spec.param_type == ParameterType.CHOICE and param_spec.choices:
            # Try exact match first
            for choice in param_spec.choices:
                if choice.lower() in voice_lower:
                    return choice
            
            # Try fuzzy matching
            import difflib
            closest_match = difflib.get_close_matches(voice_lower, 
                                                    [c.lower() for c in param_spec.choices], 
                                                    n=1, cutoff=0.6)
            if closest_match:
                # Find original case
                for choice in param_spec.choices:
                    if choice.lower() == closest_match[0]:
                        return choice
        
        # Use patterns for other types
        patterns = self.parameter_patterns.get(param_spec.param_type, [])
        
        for pattern in patterns:
            match = re.search(pattern, voice_input, re.IGNORECASE)
            if match:
                matched_value = match.group(1)
                
                # Convert to appropriate type
                try:
                    if param_spec.param_type == ParameterType.INTEGER:
                        # Handle word numbers
                        word_numbers = {
                            "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4,
                            "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10
                        }
                        
                        if matched_value.lower() in word_numbers:
                            return word_numbers[matched_value.lower()]
                        
                        # Handle negative numbers
                        if "negative" in matched_value.lower() or "minus" in matched_value.lower():
                            num_part = re.search(r'\d+', matched_value)
                            if num_part:
                                return -int(num_part.group())
                        
                        # Remove commas and convert
                        return int(matched_value.replace(",", ""))
                    
                    elif param_spec.param_type == ParameterType.FLOAT:
                        # Handle negative numbers
                        if "negative" in matched_value.lower() or "minus" in matched_value.lower():
                            num_part = re.search(r'\d+\.?\d*', matched_value)
                            if num_part:
                                return -float(num_part.group())
                        
                        return float(matched_value)
                    
                    elif param_spec.param_type == ParameterType.EMAIL:
                        # Handle spoken email format
                        if " at " in matched_value and " dot " in matched_value:
                            email = matched_value.replace(" at ", "@").replace(" dot ", ".")
                            return email
                        return matched_value
                    
                    elif param_spec.param_type == ParameterType.DURATION:
                        # Parse duration into seconds
                        duration_match = re.match(r'(\d+)\s+(second|minute|hour|day)s?', matched_value.lower())
                        if duration_match:
                            value, unit = duration_match.groups()
                            multipliers = {"second": 1, "minute": 60, "hour": 3600, "day": 86400}
                            return int(value) * multipliers.get(unit, 1)
                        
                        # Handle time format HH:MM:SS
                        time_match = re.match(r'(\d+):(\d+)(?::(\d+))?', matched_value)
                        if time_match:
                            hours, minutes, seconds = time_match.groups()
                            total_seconds = int(hours) * 3600 + int(minutes) * 60
                            if seconds:
                                total_seconds += int(seconds)
                            return total_seconds
                    
                    else:
                        return matched_value
                        
                except (ValueError, TypeError):
                    continue
        
        # If no patterns matched, return the raw input for string types
        if param_spec.param_type == ParameterType.STRING:
            return voice_input.strip()
        
        return None
    
    def _validate_parameter_value(self, value: Any, param_spec: ParameterSpec) -> Dict[str, Any]:
        """Validate a parameter value against its specification."""
        # Check required validation
        if param_spec.required and (value is None or str(value).strip() == ""):
            return {"valid": False, "error": f"{param_spec.name} is required"}
        
        # Skip validation if value is None and parameter is optional
        if value is None and not param_spec.required:
            return {"valid": True}
        
        # Apply validation rules
        for rule_name, rule_value in param_spec.validation_rules.items():
            if rule_name in self.validation_rules:
                validator = self.validation_rules[rule_name]
                try:
                    if not validator(value, rule_value):
                        return {"valid": False, "error": f"{param_spec.name} failed {rule_name} validation"}
                except Exception as e:
                    return {"valid": False, "error": f"Validation error: {e}"}
        
        return {"valid": True}
    
    def _generate_collection_prompt(self, param_spec: ParameterSpec, session: CollectionSession) -> str:
        """Generate voice prompt for parameter collection."""
        # Use custom voice prompts if available
        if param_spec.voice_prompts:
            base_prompt = param_spec.voice_prompts[0]
        else:
            # Generate default prompt based on parameter type
            if param_spec.param_type == ParameterType.BOOLEAN:
                base_prompt = f"Please say yes or no for {param_spec.name}"
            elif param_spec.param_type == ParameterType.CHOICE and param_spec.choices:
                choices_text = ", ".join(param_spec.choices[:-1]) + f", or {param_spec.choices[-1]}"
                base_prompt = f"Please choose {choices_text} for {param_spec.name}"
            elif param_spec.param_type == ParameterType.EMAIL:
                base_prompt = f"Please provide your email address for {param_spec.name}"
            elif param_spec.param_type == ParameterType.URL:
                base_prompt = f"Please provide the URL for {param_spec.name}"
            elif param_spec.param_type == ParameterType.INTEGER:
                base_prompt = f"Please provide a number for {param_spec.name}"
            elif param_spec.param_type == ParameterType.DURATION:
                base_prompt = f"Please specify the duration for {param_spec.name} in seconds, minutes, or hours"
            else:
                base_prompt = f"Please provide {param_spec.name}"
        
        # Add description if available
        if param_spec.description:
            base_prompt += f". {param_spec.description}"
        
        # Add attempt information if this is a retry
        if session.attempt_count > 0:
            remaining_attempts = session.max_attempts - session.attempt_count
            if remaining_attempts > 0:
                base_prompt += f". You have {remaining_attempts} attempts remaining."
        
        return base_prompt
    
    def _request_parameter_confirmation(self, session_id: str, param_spec: ParameterSpec, 
                                      value: Any) -> Dict[str, Any]:
        """Request confirmation for a collected parameter value."""
        session = self.active_sessions[session_id]
        session.state = CollectionState.CONFIRMING
        
        # Format value for confirmation
        if param_spec.sensitive:
            display_value = "[hidden]"
        elif param_spec.param_type == ParameterType.DURATION:
            # Convert seconds back to human readable
            if isinstance(value, int):
                if value >= 3600:
                    display_value = f"{value // 3600} hour(s) and {(value % 3600) // 60} minute(s)"
                elif value >= 60:
                    display_value = f"{value // 60} minute(s) and {value % 60} second(s)"
                else:
                    display_value = f"{value} second(s)"
            else:
                display_value = str(value)
        else:
            display_value = str(value)
        
        confirmation_prompt = f"I understood {param_spec.name} as {display_value}. Is this correct?"
        
        if self.audio_feedback:
            self.audio_feedback._queue_audio_feedback(confirmation_prompt, "normal", False)
        
        return {
            "success": True,
            "action": "confirmation_requested",
            "session_id": session_id,
            "parameter_name": param_spec.name,
            "value": value,
            "display_value": display_value,
            "prompt": confirmation_prompt
        }
    
    def _handle_confirmation_response(self, session_id: str, voice_input: str, 
                                    confidence: float) -> Dict[str, Any]:
        """Handle user response to parameter confirmation."""
        session = self.active_sessions[session_id]
        current_param = session.parameters_spec[session.current_parameter_index]
        
        voice_lower = voice_input.lower().strip()
        
        # Check for positive confirmation
        positive_responses = ["yes", "yeah", "yep", "correct", "right", "that's right", "affirmative", "ok", "okay"]
        negative_responses = ["no", "nope", "wrong", "incorrect", "that's wrong", "negative", "try again"]
        
        is_positive = any(response in voice_lower for response in positive_responses)
        is_negative = any(response in voice_lower for response in negative_responses)
        
        if is_positive and not is_negative:
            # Value confirmed, move to next parameter
            return self._advance_to_next_parameter(session_id)
        
        elif is_negative:
            # Value rejected, try collecting again
            session.state = CollectionState.COLLECTING
            
            retry_prompt = f"Let me collect {current_param.name} again. {self._generate_collection_prompt(current_param, session)}"
            
            if self.audio_feedback:
                self.audio_feedback._queue_audio_feedback(retry_prompt, "normal", False)
            
            return {
                "success": True,
                "action": "parameter_collection_retry",
                "session_id": session_id,
                "parameter_name": current_param.name,
                "prompt": retry_prompt
            }
        
        else:
            # Unclear response, ask for clarification
            clarification_prompt = "Please say yes if the value is correct, or no if you want to try again."
            
            if self.audio_feedback:
                self.audio_feedback._queue_audio_feedback(clarification_prompt, "normal", False)
            
            return {
                "success": True,
                "action": "confirmation_clarification",
                "session_id": session_id,
                "prompt": clarification_prompt
            }
    
    def _advance_to_next_parameter(self, session_id: str) -> Dict[str, Any]:
        """Advance to the next parameter in the collection sequence."""
        session = self.active_sessions[session_id]
        current_param = session.parameters_spec[session.current_parameter_index]
        
        self.logger.info(f"Successfully collected {current_param.name} = {session.collected_values.get(current_param.name)}")
        
        # Move to next parameter
        session.current_parameter_index += 1
        session.attempt_count = 0
        
        # Continue with next parameter
        return self._begin_parameter_collection(session_id)
    
    def _handle_collection_failure(self, session_id: str, error_message: str) -> Dict[str, Any]:
        """Handle parameter collection failure."""
        session = self.active_sessions[session_id]
        current_param = session.parameters_spec[session.current_parameter_index]
        
        if session.attempt_count >= session.max_attempts:
            # Max attempts reached, fail the session
            session.state = CollectionState.FAILED
            
            failure_message = f"I couldn't collect {current_param.name} after {session.max_attempts} attempts. Parameter collection failed."
            
            if self.audio_feedback:
                self.audio_feedback._queue_audio_feedback(failure_message, "high", True)
            
            # Clean up session
            del self.active_sessions[session_id]
            
            return {
                "success": False,
                "action": "collection_failed",
                "session_id": session_id,
                "parameter_name": current_param.name,
                "error": error_message,
                "message": failure_message
            }
        
        else:
            # Try again
            remaining_attempts = session.max_attempts - session.attempt_count
            retry_message = f"I didn't understand that. {error_message}. Please try again. You have {remaining_attempts} attempts remaining."
            
            if self.audio_feedback:
                self.audio_feedback._queue_audio_feedback(retry_message, "normal", True)
            
            return {
                "success": True,
                "action": "collection_retry",
                "session_id": session_id,
                "parameter_name": current_param.name,
                "error": error_message,
                "message": retry_message,
                "remaining_attempts": remaining_attempts
            }
    
    def _complete_collection_session(self, session_id: str) -> Dict[str, Any]:
        """Complete a parameter collection session."""
        session = self.active_sessions[session_id]
        session.state = CollectionState.COMPLETED
        
        completion_message = f"All parameters collected successfully for {session.tool_name}."
        
        if self.audio_feedback:
            self.audio_feedback._queue_audio_feedback(completion_message, "normal", True)
        
        # Keep session for a short time for retrieval
        result = {
            "success": True,
            "action": "collection_completed",
            "session_id": session_id,
            "tool_name": session.tool_name,
            "collected_parameters": session.collected_values.copy(),
            "message": completion_message,
            "collection_time": time.time() - session.started_at
        }
        
        self.logger.info(f"Parameter collection completed for session {session_id}")
        
        # Schedule session cleanup
        import threading
        def cleanup():
            time.sleep(60)  # Keep for 1 minute
            if session_id in self.active_sessions:
                del self.active_sessions[session_id]
        
        threading.Thread(target=cleanup, daemon=True).start()
        
        return result
    
    def cancel_collection_session(self, session_id: str, reason: str = "User cancelled") -> Dict[str, Any]:
        """Cancel an active parameter collection session."""
        if session_id not in self.active_sessions:
            return {"success": False, "error": "Session not found"}
        
        session = self.active_sessions[session_id]
        session.state = CollectionState.CANCELLED
        
        cancellation_message = f"Parameter collection for {session.tool_name} has been cancelled."
        
        if self.audio_feedback:
            self.audio_feedback._queue_audio_feedback(cancellation_message, "normal", True)
        
        # Clean up session
        del self.active_sessions[session_id]
        
        self.logger.info(f"Parameter collection session {session_id} cancelled: {reason}")
        
        return {
            "success": True,
            "action": "collection_cancelled",
            "session_id": session_id,
            "reason": reason,
            "message": cancellation_message
        }
    
    def get_session_status(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a parameter collection session."""
        session = self.active_sessions.get(session_id)
        if not session:
            return None
        
        current_param = None
        if session.current_parameter_index < len(session.parameters_spec):
            current_param = session.parameters_spec[session.current_parameter_index]
        
        return {
            "session_id": session_id,
            "tool_name": session.tool_name,
            "state": session.state.value,
            "current_parameter": current_param.name if current_param else None,
            "current_parameter_type": current_param.param_type.value if current_param else None,
            "progress": f"{session.current_parameter_index}/{len(session.parameters_spec)}",
            "collected_parameters": list(session.collected_values.keys()),
            "attempt_count": session.attempt_count,
            "max_attempts": session.max_attempts,
            "started_at": session.started_at,
            "updated_at": session.updated_at
        }
    
    def list_active_sessions(self) -> List[Dict[str, Any]]:
        """List all active parameter collection sessions."""
        return [self.get_session_status(session_id) for session_id in self.active_sessions.keys()]
    
    def cleanup_expired_sessions(self) -> int:
        """Clean up expired parameter collection sessions."""
        current_time = time.time()
        expired_sessions = []
        
        for session_id, session in self.active_sessions.items():
            if current_time - session.updated_at > self.collection_timeout:
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            self.cancel_collection_session(session_id, "Session timeout")
        
        return len(expired_sessions)