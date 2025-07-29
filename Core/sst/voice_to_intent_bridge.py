"""
Voice-to-Intent Bridge for PersonaOS.

This module connects the STT system to the existing intent processing pipeline,
enabling voice commands to be processed through the same safety and validation
framework as text commands.
"""

import time
from typing import Dict, Any, Callable, Optional
from loguru import logger

from ..intent.intent_processor import IntentProcessor
from ..audio import AudioProcessor

class VoiceToIntentBridge:
    """
    Bridge between voice input (STT) and intent processing.
    
    This class orchestrates the flow from voice input through STT to intent
    processing, maintaining the same safety and validation standards as text input.
    """
    
    def __init__(self, config: Dict[str, Any], intent_callback: Optional[Callable[[Dict[str, Any]], None]] = None):
        """
        Initialize the voice-to-intent bridge.
        
        Args:
            config: Configuration dictionary
            intent_callback: Optional callback to receive processed intents
        """
        self.config = config
        self.intent_callback = intent_callback
        
        # Initialize components
        self.audio_processor = AudioProcessor(config)
        self.intent_processor = IntentProcessor(config)
        
        # State tracking
        self.voice_active = False
        
        logger.info("VoiceToIntentBridge initialized")
    
    def initialize(self) -> bool:
        """
        Initialize the voice processing system.
        
        Returns:
            True if initialization successful, False otherwise
        """
        if not self.config.get("stt_enabled", False):
            logger.info("Voice processing disabled in configuration")
            return False
        
        # Initialize STT
        if not self.audio_processor.initialize_stt():
            logger.error("Failed to initialize STT system")
            return False
        
        logger.success("Voice-to-intent bridge initialized successfully")
        return True
    
    def start_voice_processing(self) -> bool:
        """
        Start listening for voice input and processing through intent pipeline.
        
        Returns:
            True if voice processing started successfully, False otherwise
        """
        if self.voice_active:
            logger.warning("Voice processing already active")
            return True
        
        if not self.audio_processor.stt_handler:
            logger.error("STT not initialized. Call initialize() first.")
            return False
        
        try:
            # Start voice input capture with our callback
            success = self.audio_processor.start_voice_input(self._handle_transcribed_text)
            if success:
                self.voice_active = True
                logger.info("Voice processing started")
            return success
            
        except Exception as e:
            logger.error(f"Failed to start voice processing: {e}")
            return False
    
    def stop_voice_processing(self) -> bool:
        """
        Stop voice input processing.
        
        Returns:
            True if stopped successfully, False otherwise
        """
        if not self.voice_active:
            return True
        
        try:
            success = self.audio_processor.stop_voice_input()
            if success:
                self.voice_active = False
                logger.info("Voice processing stopped")
            return success
            
        except Exception as e:
            logger.error(f"Failed to stop voice processing: {e}")
            return False
    
    def process_voice_command(self, voice_text: str) -> Dict[str, Any]:
        """
        Process a voice command through the intent pipeline.
        
        Args:
            voice_text: Transcribed voice text
            
        Returns:
            Processed intent result
        """
        logger.info(f"Processing voice command: '{voice_text}'")
        
        try:
            # Prepare voice metadata
            voice_metadata = {
                "input_type": "voice",
                "original_text": voice_text,
                "timestamp": time.time()
            }
            
            # Process through intent system with voice metadata
            intent_result = self.intent_processor.process(voice_text, voice_metadata)
            
            logger.debug(f"Voice intent processed: {intent_result['action']}")
            return intent_result
            
        except Exception as e:
            logger.error(f"Failed to process voice command: {e}")
            return {
                "intent": "error",
                "action": "error",
                "response": "I encountered an error processing your voice command.",
                "error": str(e),
                "input_type": "voice",
                "original_text": voice_text
            }
    
    def transcribe_audio_file(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Transcribe an audio file and process it through intent pipeline.
        
        Args:
            file_path: Path to audio file
            
        Returns:
            Processed intent result or None if failed
        """
        logger.info(f"Transcribing and processing audio file: {file_path}")
        
        # Transcribe audio file
        transcribed_text = self.audio_processor.transcribe_audio_file(file_path)
        if not transcribed_text:
            logger.error("Failed to transcribe audio file")
            return None
        
        # Process through intent pipeline
        return self.process_voice_command(transcribed_text)
    
    def _handle_transcribed_text(self, transcribed_text: str):
        """
        Internal callback to handle transcribed text from STT.
        
        Args:
            transcribed_text: Text transcribed from voice input
        """
        if not transcribed_text or not transcribed_text.strip():
            logger.debug("Empty transcription received, ignoring")
            return
        
        logger.info(f"Voice transcribed: '{transcribed_text}'")
        
        # Process through intent pipeline
        intent_result = self.process_voice_command(transcribed_text)
        
        # Call user callback if provided
        if self.intent_callback:
            try:
                self.intent_callback(intent_result)
            except Exception as e:
                logger.error(f"Error in intent callback: {e}")
    
    def is_voice_active(self) -> bool:
        """
        Check if voice processing is currently active.
        
        Returns:
            True if voice processing is active, False otherwise
        """
        return self.voice_active
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current status of voice processing system.
        
        Returns:
            Status dictionary with system information
        """
        return {
            "voice_active": self.voice_active,
            "stt_enabled": self.config.get("stt_enabled", False),
            "stt_model": self.config.get("stt_model", "base"),
            "stt_language": self.config.get("stt_language", "en"),
            "stt_loaded": self.audio_processor.stt_handler.is_loaded() if self.audio_processor.stt_handler else False
        }
    
    def cleanup(self):
        """Clean up voice processing resources."""
        try:
            self.stop_voice_processing()
            self.audio_processor.cleanup()
            logger.info("VoiceToIntentBridge cleaned up")
        except Exception as e:
            logger.error(f"Error during voice bridge cleanup: {e}")