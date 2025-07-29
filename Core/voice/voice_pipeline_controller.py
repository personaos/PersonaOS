"""
Voice Pipeline Controller for PersonaOS.

This module orchestrates the complete voice conversation workflow:
STT → Intent Processing → LLM → TTS

It manages voice conversation state and integrates with existing PersonaOS
systems while maintaining thread safety and performance.
"""

import asyncio
import threading
import time
from enum import Enum
from typing import Dict, Any, Optional, Callable
from loguru import logger

from ..sst.voice_to_intent_bridge import VoiceToIntentBridge
from ..intent.intent_processor import IntentProcessor
from ..llm.llm_handler import LLMManager
from ..llm.memory import MemoryManager
from ..audio import AudioProcessor

class VoiceState(Enum):
    """Voice conversation states."""
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    SPEAKING = "speaking"
    ERROR = "error"
    DISABLED = "disabled"

class VoicePipelineController:
    """
    Main controller for voice conversation pipeline.
    
    Orchestrates the complete voice workflow while maintaining compatibility
    with existing PersonaOS interfaces (CLI, web UI).
    """
    
    def __init__(self, config: Dict[str, Any], llm_manager: LLMManager, memory_manager: Optional[MemoryManager] = None):
        """
        Initialize the voice pipeline controller.
        
        Args:
            config: Configuration dictionary
            llm_manager: LLM manager instance
            memory_manager: Optional memory manager for conversation storage
        """
        self.config = config
        self.llm_manager = llm_manager
        self.memory_manager = memory_manager
        
        # Voice components
        self.voice_bridge = None
        self.intent_processor = IntentProcessor(config)
        self.audio_processor = AudioProcessor(config)
        
        # State management
        self.current_state = VoiceState.DISABLED
        self.state_lock = threading.Lock()
        self.active_session = False
        
        # Callbacks (enabled by configuration)
        self.state_change_callback = None
        self.response_callback = None
        self.error_callback = None
        self.callbacks_enabled = config.get("voice_state_callbacks", True)
        
        # Performance tracking (configurable)
        self.metrics_enabled = config.get("voice_metrics_enabled", True)
        self.conversation_metrics = {
            "total_conversations": 0,
            "average_response_time": 0.0,
            "last_conversation_time": None
        } if self.metrics_enabled else None
        
        # Voice pipeline settings
        self.response_timeout = config.get("voice_response_timeout", 30)
        self.auto_start = config.get("voice_auto_start", False)
        
        # Error handling and fallback settings
        self.fallback_enabled = config.get("voice_fallback_enabled", True)
        self.max_retry_attempts = config.get("voice_max_retries", 3)
        self.fallback_callback = None
        
        # Error tracking
        self.error_count = 0
        self.last_error = None
        self.consecutive_failures = 0
        
        # TTS fallback settings
        self.tts_fallback_enabled = config.get("tts_fallback_enabled", True)
        self.tts_error_count = 0
        
        logger.info("VoicePipelineController initialized")
    
    def initialize(self) -> bool:
        """
        Initialize the voice pipeline components.
        
        Returns:
            True if initialization successful, False otherwise
        """
        if not self.config.get("stt_enabled", False):
            logger.info("Voice pipeline disabled in configuration")
            self._set_state(VoiceState.DISABLED)
            return False
        
        try:
            # Initialize voice bridge (STT system)
            self.voice_bridge = VoiceToIntentBridge(self.config)
            if not self.voice_bridge.initialize():
                logger.error("Failed to initialize voice bridge")
                self._set_state(VoiceState.ERROR)
                return False
            
            # Initialize TTS system
            if not self.audio_processor.initialize_tts():
                logger.warning("TTS initialization failed, voice output will be disabled")
            else:
                logger.info("TTS initialized successfully")
            
            # Set up voice input callback
            self.voice_bridge.intent_callback = self._handle_voice_intent
            
            self._set_state(VoiceState.IDLE)
            self._reset_error_tracking()  # Reset error count on successful initialization
            logger.success("Voice pipeline initialized successfully")
            
            # Auto-start voice session if configured
            if self.auto_start:
                logger.info("Auto-starting voice session")
                if self.start_voice_session():
                    logger.info("Voice session auto-started successfully")
                else:
                    logger.warning("Failed to auto-start voice session")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize voice pipeline: {e}")
            self._handle_pipeline_error(e, "initialization")
            return False
    
    def start_voice_session(self) -> bool:
        """
        Start a voice conversation session.
        
        Returns:
            True if session started successfully, False otherwise
        """
        if self.current_state == VoiceState.DISABLED:
            logger.warning("Cannot start voice session - pipeline is disabled")
            return False
        
        if self.active_session:
            logger.warning("Voice session already active")
            return True
        
        try:
            if not self.voice_bridge:
                logger.error("Voice bridge not initialized")
                return False
            
            # Start voice processing
            if self.voice_bridge.start_voice_processing():
                self.active_session = True
                self._set_state(VoiceState.LISTENING)
                self._reset_error_tracking()  # Reset on successful session start
                logger.info("Voice session started")
                return True
            else:
                logger.error("Failed to start voice processing")
                self._set_state(VoiceState.ERROR)
                return False
                
        except Exception as e:
            logger.error(f"Failed to start voice session: {e}")
            self._handle_pipeline_error(e, "voice_session_start")
            return False
    
    def stop_voice_session(self) -> bool:
        """
        Stop the current voice conversation session.
        
        Returns:
            True if session stopped successfully, False otherwise
        """
        if not self.active_session:
            return True
        
        try:
            if self.voice_bridge:
                self.voice_bridge.stop_voice_processing()
            
            self.active_session = False
            self._set_state(VoiceState.IDLE)
            logger.info("Voice session stopped")
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop voice session: {e}")
            return False
    
    def process_voice_command_direct(self, command_text: str) -> Dict[str, Any]:
        """
        Process a voice command directly (for testing or manual input).
        
        Args:
            command_text: Text command to process
            
        Returns:
            Processing result dictionary
        """
        start_time = time.time()
        
        try:
            self._set_state(VoiceState.PROCESSING)
            
            # Process through intent system
            intent_result = self.intent_processor.process(command_text)
            
            # Handle based on intent action
            if intent_result.get("action") == "llm_response":
                # Generate LLM response
                llm_response = self._generate_llm_response(intent_result["user_input"])
                intent_result["response"] = llm_response
                
                # Convert response to speech for direct command
                self._speak_response(llm_response)
                
            elif intent_result.get("action") in ["tool_executed", "tool_failed"]:
                # Speak tool execution results for direct command
                if "response" in intent_result:
                    self._speak_response(intent_result["response"])
            
            # Update metrics if enabled
            processing_time = time.time() - start_time
            if self.metrics_enabled:
                self._update_metrics(processing_time)
            
            # Add voice-specific metadata
            intent_result.update({
                "input_type": "voice_direct",
                "processing_time": processing_time,
                "voice_state": self.current_state.value
            })
            
            self._set_state(VoiceState.LISTENING if self.active_session else VoiceState.IDLE)
            return intent_result
            
        except Exception as e:
            logger.error(f"Failed to process voice command: {e}")
            self._set_state(VoiceState.ERROR)
            return {
                "action": "error",
                "response": "I encountered an error processing your voice command.",
                "error": str(e),
                "input_type": "voice_direct"
            }
    
    def _handle_voice_intent(self, intent_result: Dict[str, Any]):
        """
        Internal callback to handle voice intents from the voice bridge.
        
        Args:
            intent_result: Intent processing result from voice bridge
        """
        start_time = time.time()
        
        try:
            self._set_state(VoiceState.PROCESSING)
            
            original_text = intent_result.get("original_text", "")
            logger.info(f"Processing voice input: '{original_text}'")
            
            # Handle different intent actions
            if intent_result.get("action") == "llm_response":
                # Generate LLM response
                llm_response = self._generate_llm_response(intent_result["user_input"])
                intent_result["response"] = llm_response
                
                # Convert response to speech
                self._speak_response(llm_response)
                
                # Store in memory if available
                if self.memory_manager:
                    self.memory_manager.store_conversation_turn(
                        user_message=original_text,
                        assistant_message=llm_response,
                        metadata={"input_type": "voice", "processing_time": time.time() - start_time}
                    )
            
            elif intent_result.get("action") in ["tool_executed", "tool_failed"]:
                # Speak tool execution results
                if "response" in intent_result:
                    self._speak_response(intent_result["response"])
            
            elif intent_result.get("action") in ["blocked", "refused"]:
                # Speak safety/error messages
                if "response" in intent_result:
                    self._speak_response(intent_result["response"])
            
            # Update metrics if enabled
            processing_time = time.time() - start_time
            if self.metrics_enabled:
                self._update_metrics(processing_time)
            
            # Call response callback if set
            if self.response_callback:
                self.response_callback(intent_result)
            
            self._set_state(VoiceState.LISTENING)
            
        except Exception as e:
            logger.error(f"Error handling voice intent: {e}")
            self._handle_pipeline_error(e, "voice_intent_processing")
            
            # Try to trigger fallback to text mode
            if self.fallback_enabled and self.fallback_callback:
                try:
                    logger.info("Triggering fallback to text mode")
                    self.fallback_callback("Voice processing failed, switching to text mode")
                except Exception as fallback_error:
                    logger.error(f"Fallback callback failed: {fallback_error}")
    
    def _generate_llm_response(self, user_input: str) -> str:
        """
        Generate response using the LLM system.
        
        Args:
            user_input: User's input text
            
        Returns:
            Generated response text
        """
        try:
            # Use existing conversation handling from PersonaOS
            from ..llm.llm_handler import handle_conversation
            
            response = handle_conversation(
                user_input, 
                self.config, 
                self.memory_manager, 
                self.llm_manager
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to generate LLM response: {e}")
            return "I apologize, but I encountered an error generating a response."
    
    def _generate_llm_response_streaming(self, user_input: str):
        """
        Generate streaming LLM response for real-time TTS.
        
        Args:
            user_input: User's input text
            
        Returns:
            Generator yielding response chunks
        """
        try:
            # Check if LLM manager supports streaming
            if hasattr(self.llm_manager, 'generate_streaming'):
                # Use streaming generation if available
                for chunk in self.llm_manager.generate_streaming(user_input):
                    yield chunk
            else:
                # Fallback to non-streaming generation
                response = self._generate_llm_response(user_input)
                # Simulate streaming by yielding words
                words = response.split()
                for word in words:
                    yield word + " "
                    time.sleep(0.1)  # Small delay to simulate streaming
                    
        except Exception as e:
            logger.error(f"Failed to generate streaming LLM response: {e}")
            yield "I apologize, but I encountered an error generating a streaming response."
    
    def _speak_response(self, text: str):
        """
        Convert text response to speech and play audio with error handling.
        
        Args:
            text: Text to convert to speech
        """
        if not text or not text.strip():
            return
        
        try:
            # Set speaking state
            self._set_state(VoiceState.SPEAKING)
            
            # Try to speak the text
            if self.audio_processor.speak_text(text):
                logger.debug(f"Speaking response: '{text[:50]}{'...' if len(text) > 50 else ''}'")
                # Reset TTS error count on success
                self.tts_error_count = 0
            else:
                # TTS failed, handle fallback
                self._handle_tts_failure(text)
            
        except Exception as e:
            logger.error(f"Error speaking response: {e}")
            self._handle_tts_failure(text, e)
        finally:
            # Return to appropriate state
            if self.active_session:
                self._set_state(VoiceState.LISTENING)
            else:
                self._set_state(VoiceState.IDLE)
    
    def _handle_tts_failure(self, text: str, error: Exception = None):
        """
        Handle TTS failure with fallback mechanisms.
        
        Args:
            text: Text that failed to be spoken
            error: Optional exception that caused the failure
        """
        self.tts_error_count += 1
        
        error_msg = str(error) if error else "TTS synthesis failed"
        logger.warning(f"TTS failure #{self.tts_error_count}: {error_msg}")
        
        if self.tts_fallback_enabled:
            # Fallback to text display
            if self.response_callback:
                try:
                    fallback_result = {
                        "action": "tts_fallback",
                        "response": text,
                        "original_text": text,
                        "error": error_msg,
                        "tts_error_count": self.tts_error_count
                    }
                    self.response_callback(fallback_result)
                    logger.info("Fallback to text display activated")
                except Exception as e:
                    logger.error(f"Fallback callback failed: {e}")
            
            # Try to recover TTS after multiple failures
            if self.tts_error_count >= 3:
                logger.warning("Multiple TTS failures detected, attempting TTS recovery")
                self._attempt_tts_recovery()
        
        # Trigger general voice fallback if configured
        if self.fallback_callback:
            try:
                self.fallback_callback(f"TTS failed: {error_msg}. Continuing with text output.")
            except Exception as e:
                logger.error(f"Voice fallback callback failed: {e}")
    
    def _attempt_tts_recovery(self):
        """Attempt to recover TTS functionality."""
        try:
            logger.info("Attempting TTS recovery...")
            
            # Reinitialize TTS
            if self.audio_processor.initialize_tts():
                logger.success("TTS recovery successful")
                self.tts_error_count = 0
            else:
                logger.warning("TTS recovery failed")
                
        except Exception as e:
            logger.error(f"TTS recovery attempt failed: {e}")
    
    def _speak_response_streaming(self, text_generator):
        """
        Convert streaming text to speech for real-time audio output.
        
        Args:
            text_generator: Generator yielding text chunks
        """
        try:
            # Set speaking state
            self._set_state(VoiceState.SPEAKING)
            
            # Use audio processor for streaming TTS
            if self.audio_processor.speak_text_streaming(text_generator):
                logger.debug("Started streaming TTS for LLM response")
            else:
                logger.warning("Failed to start streaming TTS")
            
        except Exception as e:
            logger.error(f"Error in streaming TTS: {e}")
        finally:
            # Return to appropriate state
            if self.active_session:
                self._set_state(VoiceState.LISTENING)
            else:
                self._set_state(VoiceState.IDLE)
    
    def _set_state(self, new_state: VoiceState):
        """
        Set the voice pipeline state with thread safety.
        
        Args:
            new_state: New state to set
        """
        with self.state_lock:
            old_state = self.current_state
            self.current_state = new_state
            
            if old_state != new_state:
                logger.debug(f"Voice state changed: {old_state.value} → {new_state.value}")
                
                if self.callbacks_enabled and self.state_change_callback:
                    try:
                        self.state_change_callback(old_state, new_state)
                    except Exception as e:
                        logger.error(f"Error in state change callback: {e}")
    
    def _update_metrics(self, processing_time: float):
        """
        Update conversation performance metrics.
        
        Args:
            processing_time: Time taken to process the conversation
        """
        if not self.metrics_enabled or not self.conversation_metrics:
            return
            
        self.conversation_metrics["total_conversations"] += 1
        
        # Update running average
        total = self.conversation_metrics["total_conversations"]
        current_avg = self.conversation_metrics["average_response_time"]
        new_avg = ((total - 1) * current_avg + processing_time) / total
        self.conversation_metrics["average_response_time"] = new_avg
        
        self.conversation_metrics["last_conversation_time"] = time.time()
    
    def get_state(self) -> VoiceState:
        """
        Get the current voice pipeline state.
        
        Returns:
            Current voice state
        """
        with self.state_lock:
            return self.current_state
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get comprehensive status of the voice pipeline.
        
        Returns:
            Status dictionary with current state and metrics
        """
        return {
            "state": self.current_state.value,
            "active_session": self.active_session,
            "voice_enabled": self.config.get("stt_enabled", False),
            "voice_bridge_status": self.voice_bridge.get_status() if self.voice_bridge else None,
            "metrics": self.conversation_metrics.copy() if self.conversation_metrics else None,
            "config": {
                "stt_model": self.config.get("stt_model", "base"),
                "stt_language": self.config.get("stt_language", "en"),
                "safety_level": self.config.get("safety_level", "standard"),
                "voice_pipeline_enabled": self.config.get("voice_pipeline_enabled", True),
                "voice_auto_start": self.auto_start,
                "voice_response_timeout": self.response_timeout,
                "voice_metrics_enabled": self.metrics_enabled,
                "voice_callbacks_enabled": self.callbacks_enabled,
                "voice_fallback_enabled": self.fallback_enabled,
                "voice_max_retries": self.max_retry_attempts
            }
        }
    
    def set_callbacks(self, 
                     state_change_callback: Optional[Callable] = None,
                     response_callback: Optional[Callable] = None,
                     error_callback: Optional[Callable] = None):
        """
        Set callback functions for voice events.
        
        Args:
            state_change_callback: Called when voice state changes
            response_callback: Called when voice response is generated
            error_callback: Called when voice error occurs
        """
        self.state_change_callback = state_change_callback
        self.response_callback = response_callback
        self.error_callback = error_callback
    
    def cleanup(self):
        """Clean up voice pipeline resources including tool registry."""
        try:
            self.stop_voice_session()
            
            if self.voice_bridge:
                self.voice_bridge.cleanup()
            
            if self.audio_processor:
                self.audio_processor.cleanup()
            
            if hasattr(self, 'tool_registry') and self.tool_registry:
                self.tool_registry.cleanup()
            
            self._set_state(VoiceState.DISABLED)
            logger.info("Voice pipeline controller cleaned up")
            
        except Exception as e:
            logger.error(f"Error during voice pipeline cleanup: {e}")
    
    def _handle_pipeline_error(self, error: Exception, context: str):
        """
        Handle pipeline errors with proper logging and fallback management.
        
        Args:
            error: The exception that occurred
            context: Description of where the error occurred
        """
        self.error_count += 1
        self.consecutive_failures += 1
        self.last_error = {
            "error": str(error),
            "context": context,
            "timestamp": time.time(),
            "error_type": type(error).__name__
        }
        
        # Log detailed error information
        logger.error(f"Voice pipeline error in {context}: {error}")
        logger.debug(f"Error type: {type(error).__name__}")
        logger.debug(f"Total errors: {self.error_count}, Consecutive: {self.consecutive_failures}")
        
        # Set error state
        self._set_state(VoiceState.ERROR)
        
        # Check if we should attempt recovery
        if self.consecutive_failures >= self.max_retry_attempts:
            logger.warning(f"Max retry attempts ({self.max_retry_attempts}) reached. Voice pipeline disabled.")
            self._set_state(VoiceState.DISABLED)
            
            # Trigger fallback if enabled
            if self.fallback_enabled and self.fallback_callback:
                try:
                    self.fallback_callback(f"Voice pipeline disabled after {self.consecutive_failures} failures")
                except Exception as e:
                    logger.error(f"Fallback callback failed: {e}")
        
        # Call error callback if set
        if self.callbacks_enabled and self.error_callback:
            try:
                self.error_callback(error)
            except Exception as e:
                logger.error(f"Error callback failed: {e}")
    
    def _reset_error_tracking(self):
        """Reset error tracking counters after successful operation."""
        if self.consecutive_failures > 0:
            logger.info(f"Voice pipeline recovered after {self.consecutive_failures} failures")
            self.consecutive_failures = 0
    
    def attempt_recovery(self) -> bool:
        """
        Attempt to recover from error state by reinitializing the voice pipeline.
        
        Returns:
            True if recovery successful, False otherwise
        """
        if self.current_state != VoiceState.ERROR:
            logger.warning("Recovery attempt called but pipeline not in error state")
            return True
        
        logger.info("Attempting voice pipeline recovery")
        
        try:
            # Clean up current state
            if self.voice_bridge:
                self.voice_bridge.cleanup()
                self.voice_bridge = None
            
            # Reinitialize
            return self.initialize()
            
        except Exception as e:
            logger.error(f"Recovery attempt failed: {e}")
            self._handle_pipeline_error(e, "recovery_attempt")
            return False
    
    def get_error_status(self) -> Dict[str, Any]:
        """
        Get detailed error status information.
        
        Returns:
            Dictionary with error tracking information
        """
        return {
            "error_count": self.error_count,
            "consecutive_failures": self.consecutive_failures,
            "last_error": self.last_error,
            "max_retry_attempts": self.max_retry_attempts,
            "fallback_enabled": self.fallback_enabled,
            "can_attempt_recovery": self.current_state == VoiceState.ERROR
        }
    
    def set_fallback_callback(self, callback: Optional[Callable[[str], None]]):
        """
        Set callback function for fallback to text mode.
        
        Args:
            callback: Function to call when fallback is needed
        """
        self.fallback_callback = callback
    
    def process_voice_command_streaming(self, command_text: str) -> bool:
        """
        Process a voice command with streaming TTS response.
        
        Args:
            command_text: Text command to process with streaming output
            
        Returns:
            True if processing started successfully, False otherwise
        """
        if not self.is_voice_available():
            logger.error("Voice pipeline not available")
            return False
        
        try:
            self._set_state(VoiceState.PROCESSING)
            
            # Process through intent system
            intent_result = self.intent_processor.process(command_text)
            
            # Handle streaming LLM responses
            if intent_result.get("action") == "llm_response":
                # Generate streaming LLM response
                response_generator = self._generate_llm_response_streaming(intent_result["user_input"])
                
                # Convert to streaming speech
                self._speak_response_streaming(response_generator)
                return True
            else:
                # For non-LLM responses, use regular TTS
                if "response" in intent_result:
                    self._speak_response(intent_result["response"])
                return True
                
        except Exception as e:
            logger.error(f"Failed to process streaming voice command: {e}")
            self._set_state(VoiceState.ERROR)
            return False
    
    def stop_speech(self) -> bool:
        """
        Stop current TTS speech output.
        
        Returns:
            True if stopped successfully, False otherwise
        """
        try:
            return self.audio_processor.stop_speech()
        except Exception as e:
            logger.error(f"Failed to stop speech: {e}")
            return False
    
    def is_speaking(self) -> bool:
        """
        Check if TTS is currently speaking.
        
        Returns:
            True if currently speaking, False otherwise
        """
        try:
            return self.audio_processor.is_speaking()
        except Exception as e:
            logger.error(f"Failed to check speaking status: {e}")
            return False
    
    def set_voice(self, voice_id: str) -> bool:
        """
        Set the TTS voice.
        
        Args:
            voice_id: Voice identifier
            
        Returns:
            True if voice set successfully, False otherwise
        """
        try:
            return self.audio_processor.set_voice(voice_id)
        except Exception as e:
            logger.error(f"Failed to set voice: {e}")
            return False
    
    def get_available_voices(self) -> Dict[str, Dict[str, Any]]:
        """
        Get available TTS voices.
        
        Returns:
            Dictionary of available voices
        """
        try:
            return self.audio_processor.get_available_voices()
        except Exception as e:
            logger.error(f"Failed to get available voices: {e}")
            return {}

    def is_voice_available(self) -> bool:
        """
        Check if voice functionality is available and working.
        
        Returns:
            True if voice is available, False otherwise
        """
        return (
            self.current_state != VoiceState.DISABLED and
            self.current_state != VoiceState.ERROR and
            self.voice_bridge is not None
        )