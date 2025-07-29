"""
Local TTS Handler for PersonaOS using pyttsx3.

This module implements the BaseTTSHandler using pyttsx3 for offline,
local text-to-speech conversion. It provides high-quality speech synthesis
without requiring external API calls or internet connectivity.
"""

import threading
import time
import queue
from typing import Dict, Any, Optional, Generator, List
from loguru import logger

try:
    import pyttsx3
    PYTTSX3_AVAILABLE = True
except ImportError:
    PYTTSX3_AVAILABLE = False
    logger.warning("pyttsx3 not available. TTS functionality will be disabled.")

from .base_tts_handler import BaseTTSHandler


class LocalTTSHandler(BaseTTSHandler):
    """
    Local TTS handler using pyttsx3 for offline speech synthesis.
    
    Provides comprehensive TTS functionality including voice selection,
    language support, streaming synthesis, and audio playback.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the Local TTS Handler.
        
        Args:
            config: Configuration dictionary with TTS settings
        """
        super().__init__(config)
        
        # TTS engine instance
        self.engine = None
        
        # Voice and language settings
        self.available_voices = {}
        self.available_languages = {}
        
        # Playback control
        self.is_speaking_flag = False
        self.should_stop = False
        
        # Streaming support
        self.streaming_queue = queue.Queue()
        self.streaming_thread = None
        self.streaming_active = False
        
        # Configuration
        self.default_rate = config.get("tts_rate", 200)
        self.default_volume = config.get("tts_volume", 0.9)
        self.default_voice = config.get("tts_voice", None)
        self.default_language = config.get("tts_language", "en")
        
        logger.info("LocalTTSHandler initialized")
    
    def initialize(self) -> bool:
        """
        Initialize the pyttsx3 TTS engine and load available voices.
        
        Returns:
            True if initialization successful, False otherwise
        """
        if not PYTTSX3_AVAILABLE:
            logger.error("pyttsx3 not available. Cannot initialize TTS.")
            return False
        
        try:
            with self._lock:
                # Initialize pyttsx3 engine
                self.engine = pyttsx3.init()
                
                if not self.engine:
                    logger.error("Failed to initialize pyttsx3 engine")
                    return False
                
                # Set default properties
                self.engine.setProperty('rate', self.default_rate)
                self.engine.setProperty('volume', self.default_volume)
                
                # Load available voices
                self._load_available_voices()
                
                # Set default voice if specified
                if self.default_voice:
                    self.set_voice(self.default_voice)
                
                # Set default language
                if self.default_language:
                    self.set_language(self.default_language)
                
                self.is_initialized = True
                logger.success("LocalTTSHandler initialized successfully")
                return True
                
        except Exception as e:
            logger.error(f"Failed to initialize LocalTTSHandler: {e}")
            return False
    
    def _load_available_voices(self):
        """Load and catalog available TTS voices."""
        try:
            voices = self.engine.getProperty('voices')
            self.available_voices = {}
            self.available_languages = {}
            
            for i, voice in enumerate(voices):
                voice_id = voice.id
                voice_name = voice.name if hasattr(voice, 'name') else f"Voice {i}"
                
                # Extract language from voice (if available)
                language = "en"  # Default
                if hasattr(voice, 'languages') and voice.languages:
                    language = voice.languages[0][:2].lower()  # Extract language code
                
                self.available_voices[voice_id] = {
                    "name": voice_name,
                    "language": language,
                    "gender": "unknown",  # pyttsx3 doesn't provide gender info
                    "id": voice_id
                }
                
                # Track available languages
                if language not in self.available_languages:
                    self.available_languages[language] = self._get_language_name(language)
            
            logger.info(f"Loaded {len(self.available_voices)} TTS voices")
            logger.debug(f"Available languages: {list(self.available_languages.keys())}")
            
        except Exception as e:
            logger.error(f"Failed to load available voices: {e}")
            self.available_voices = {}
            self.available_languages = {"en": "English"}
    
    def _get_language_name(self, language_code: str) -> str:
        """Get human-readable language name from code."""
        language_names = {
            "en": "English",
            "es": "Spanish", 
            "fr": "French",
            "de": "German",
            "it": "Italian",
            "pt": "Portuguese",
            "ru": "Russian",
            "zh": "Chinese",
            "ja": "Japanese",
            "ko": "Korean"
        }
        return language_names.get(language_code.lower(), language_code.title())
    
    def synthesize(self, text: str, **kwargs) -> bool:
        """
        Convert text to speech and play audio.
        
        Args:
            text: Text to convert to speech
            **kwargs: Additional parameters (voice, rate, volume)
            
        Returns:
            True if synthesis successful, False otherwise
        """
        if not self.is_initialized or not self.engine:
            logger.error("TTS engine not initialized")
            return False
        
        if not text or not text.strip():
            logger.warning("Empty text provided for TTS synthesis")
            return True
        
        try:
            with self._lock:
                # Set temporary properties if provided
                original_rate = self.engine.getProperty('rate')
                original_volume = self.engine.getProperty('volume')
                
                if 'rate' in kwargs:
                    self.engine.setProperty('rate', kwargs['rate'])
                if 'volume' in kwargs:
                    self.engine.setProperty('volume', kwargs['volume'])
                if 'voice' in kwargs:
                    self.set_voice(kwargs['voice'])
                
                # Prepare for synthesis
                self.is_speaking_flag = True
                self.should_stop = False
                
                logger.info(f"Synthesizing text: '{text[:50]}{'...' if len(text) > 50 else ''}'")
                
                # Perform TTS synthesis
                self.engine.say(text)
                self.engine.runAndWait()
                
                # Restore original properties
                self.engine.setProperty('rate', original_rate)
                self.engine.setProperty('volume', original_volume)
                
                self.is_speaking_flag = False
                logger.debug("TTS synthesis completed")
                return True
                
        except Exception as e:
            logger.error(f"TTS synthesis failed: {e}")
            self.is_speaking_flag = False
            return False
    
    def synthesize_to_file(self, text: str, file_path: str, **kwargs) -> bool:
        """
        Convert text to speech and save to audio file.
        
        Args:
            text: Text to convert to speech
            file_path: Path where audio file should be saved
            **kwargs: Additional synthesis parameters
            
        Returns:
            True if synthesis successful, False otherwise
        """
        if not self.is_initialized or not self.engine:
            logger.error("TTS engine not initialized")
            return False
        
        try:
            with self._lock:
                # pyttsx3 doesn't directly support file output
                # This would require additional implementation with audio capture
                logger.warning("synthesize_to_file not yet implemented for pyttsx3")
                return False
                
        except Exception as e:
            logger.error(f"Failed to synthesize to file: {e}")
            return False
    
    def synthesize_streaming(self, text_generator: Generator[str, None, None], **kwargs) -> bool:
        """
        Convert streaming text to speech for real-time audio output.
        
        Args:
            text_generator: Generator yielding text chunks
            **kwargs: Additional synthesis parameters
            
        Returns:
            True if streaming synthesis started successfully, False otherwise
        """
        if not self.is_initialized or not self.engine:
            logger.error("TTS engine not initialized")
            return False
        
        if self.streaming_active:
            logger.warning("Streaming TTS already active")
            return False
        
        try:
            # Start streaming synthesis in separate thread
            self.streaming_active = True
            self.streaming_thread = threading.Thread(
                target=self._streaming_synthesis_worker,
                args=(text_generator, kwargs),
                daemon=True
            )
            self.streaming_thread.start()
            
            logger.info("Streaming TTS synthesis started")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start streaming TTS: {e}")
            self.streaming_active = False
            return False
    
    def _streaming_synthesis_worker(self, text_generator: Generator[str, None, None], kwargs: Dict[str, Any]):
        """Worker function for streaming TTS synthesis."""
        try:
            sentence_buffer = ""
            
            for text_chunk in text_generator:
                if self.should_stop:
                    break
                
                sentence_buffer += text_chunk
                
                # Look for sentence endings to create natural speech breaks
                if any(punct in sentence_buffer for punct in ['.', '!', '?', '\n']):
                    # Extract complete sentences
                    sentences = []
                    temp_buffer = ""
                    
                    for char in sentence_buffer:
                        temp_buffer += char
                        if char in ['.', '!', '?']:
                            sentences.append(temp_buffer.strip())
                            temp_buffer = ""
                    
                    # Keep incomplete sentence in buffer
                    sentence_buffer = temp_buffer
                    
                    # Synthesize complete sentences
                    for sentence in sentences:
                        if sentence and not self.should_stop:
                            self.synthesize(sentence, **kwargs)
            
            # Synthesize any remaining text
            if sentence_buffer.strip() and not self.should_stop:
                self.synthesize(sentence_buffer.strip(), **kwargs)
                
        except Exception as e:
            logger.error(f"Streaming TTS worker error: {e}")
        finally:
            self.streaming_active = False
            logger.debug("Streaming TTS synthesis completed")
    
    def stop(self) -> bool:
        """
        Stop current TTS playback immediately.
        
        Returns:
            True if stopped successfully, False otherwise
        """
        try:
            with self._lock:
                self.should_stop = True
                
                if self.engine:
                    self.engine.stop()
                
                # Stop streaming if active
                if self.streaming_active:
                    self.streaming_active = False
                    if self.streaming_thread and self.streaming_thread.is_alive():
                        self.streaming_thread.join(timeout=1.0)
                
                self.is_speaking_flag = False
                logger.info("TTS playback stopped")
                return True
                
        except Exception as e:
            logger.error(f"Failed to stop TTS: {e}")
            return False
    
    def set_voice(self, voice_id: str) -> bool:
        """
        Set the voice for TTS synthesis.
        
        Args:
            voice_id: Identifier for the voice to use
            
        Returns:
            True if voice set successfully, False otherwise
        """
        if not self.is_initialized or not self.engine:
            logger.error("TTS engine not initialized")
            return False
        
        try:
            if voice_id in self.available_voices:
                self.engine.setProperty('voice', voice_id)
                self.current_voice = voice_id
                logger.info(f"TTS voice set to: {self.available_voices[voice_id]['name']}")
                return True
            else:
                logger.warning(f"Voice '{voice_id}' not available")
                return False
                
        except Exception as e:
            logger.error(f"Failed to set TTS voice: {e}")
            return False
    
    def set_language(self, language_code: str) -> bool:
        """
        Set the language for TTS synthesis.
        
        Args:
            language_code: Language code (e.g., 'en', 'es', 'fr')
            
        Returns:
            True if language set successfully, False otherwise
        """
        if not self.is_initialized:
            logger.error("TTS engine not initialized")
            return False
        
        try:
            # Find a voice that supports the requested language
            compatible_voices = [
                voice_id for voice_id, voice_info in self.available_voices.items()
                if voice_info['language'] == language_code.lower()
            ]
            
            if compatible_voices:
                # Use the first compatible voice
                if self.set_voice(compatible_voices[0]):
                    self.current_language = language_code.lower()
                    logger.info(f"TTS language set to: {language_code}")
                    return True
            
            logger.warning(f"No voices available for language: {language_code}")
            return False
            
        except Exception as e:
            logger.error(f"Failed to set TTS language: {e}")
            return False
    
    def get_available_voices(self) -> Dict[str, Dict[str, Any]]:
        """
        Get list of available voices for TTS.
        
        Returns:
            Dictionary mapping voice IDs to voice information
        """
        return self.available_voices.copy()
    
    def get_available_languages(self) -> Dict[str, str]:
        """
        Get list of available languages for TTS.
        
        Returns:
            Dictionary mapping language codes to language names
        """
        return self.available_languages.copy()
    
    def is_speaking(self) -> bool:
        """
        Check if TTS is currently speaking/playing audio.
        
        Returns:
            True if currently speaking, False otherwise
        """
        return self.is_speaking_flag or self.streaming_active
    
    def cleanup(self) -> bool:
        """
        Clean up TTS resources and stop any ongoing synthesis.
        
        Returns:
            True if cleanup successful, False otherwise
        """
        try:
            # Stop any ongoing synthesis
            self.stop()
            
            with self._lock:
                if self.engine:
                    # pyttsx3 doesn't have explicit cleanup
                    self.engine = None
                
                self.is_initialized = False
                self.current_voice = None
                self.current_language = None
                self.available_voices = {}
                self.available_languages = {}
                
            logger.info("LocalTTSHandler cleaned up")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cleanup TTS handler: {e}")
            return False