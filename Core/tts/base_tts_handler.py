"""
Base TTS Handler Interface for PersonaOS.

This module defines the abstract interface that all TTS handlers must implement,
following the same pattern as the LLM BaseModelHandler for consistency.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Callable, Generator, Union
import threading


class BaseTTSHandler(ABC):
    """
    Abstract base class for all TTS handlers.
    
    This interface ensures consistency across different TTS implementations
    and provides the foundation for pluggable TTS systems.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the TTS handler with configuration.
        
        Args:
            config: Configuration dictionary containing TTS settings
        """
        self.config = config
        self.is_initialized = False
        self.current_voice = None
        self.current_language = None
        self._lock = threading.Lock()
    
    @abstractmethod
    def initialize(self) -> bool:
        """
        Initialize the TTS engine and load necessary models/resources.
        
        Returns:
            True if initialization successful, False otherwise
        """
        pass
    
    @abstractmethod
    def synthesize(self, text: str, **kwargs) -> bool:
        """
        Convert text to speech and play audio.
        
        Args:
            text: Text to convert to speech
            **kwargs: Additional synthesis parameters (voice, rate, volume, etc.)
            
        Returns:
            True if synthesis and playback successful, False otherwise
        """
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
    def synthesize_streaming(self, text_generator: Generator[str, None, None], **kwargs) -> bool:
        """
        Convert streaming text to speech for real-time audio output.
        
        Args:
            text_generator: Generator yielding text chunks for streaming TTS
            **kwargs: Additional synthesis parameters
            
        Returns:
            True if streaming synthesis successful, False otherwise
        """
        pass
    
    @abstractmethod
    def stop(self) -> bool:
        """
        Stop current TTS playback immediately.
        
        Returns:
            True if stopped successfully, False otherwise
        """
        pass
    
    @abstractmethod
    def set_voice(self, voice_id: str) -> bool:
        """
        Set the voice for TTS synthesis.
        
        Args:
            voice_id: Identifier for the voice to use
            
        Returns:
            True if voice set successfully, False otherwise
        """
        pass
    
    @abstractmethod
    def set_language(self, language_code: str) -> bool:
        """
        Set the language for TTS synthesis.
        
        Args:
            language_code: Language code (e.g., 'en', 'es', 'fr')
            
        Returns:
            True if language set successfully, False otherwise
        """
        pass
    
    @abstractmethod
    def get_available_voices(self) -> Dict[str, Dict[str, Any]]:
        """
        Get list of available voices for TTS.
        
        Returns:
            Dictionary mapping voice IDs to voice information
        """
        pass
    
    @abstractmethod
    def get_available_languages(self) -> Dict[str, str]:
        """
        Get list of available languages for TTS.
        
        Returns:
            Dictionary mapping language codes to language names
        """
        pass
    
    @abstractmethod
    def is_speaking(self) -> bool:
        """
        Check if TTS is currently speaking/playing audio.
        
        Returns:
            True if currently speaking, False otherwise
        """
        pass
    
    @abstractmethod
    def cleanup(self) -> bool:
        """
        Clean up TTS resources and stop any ongoing synthesis.
        
        Returns:
            True if cleanup successful, False otherwise
        """
        pass
    
    # Common utility methods that can be inherited
    
    def is_loaded(self) -> bool:
        """
        Check if the TTS handler is loaded and ready.
        
        Returns:
            True if loaded and ready, False otherwise
        """
        return self.is_initialized
    
    def get_current_voice(self) -> Optional[str]:
        """
        Get the currently selected voice.
        
        Returns:
            Current voice ID or None if not set
        """
        return self.current_voice
    
    def get_current_language(self) -> Optional[str]:
        """
        Get the currently selected language.
        
        Returns:
            Current language code or None if not set
        """
        return self.current_language
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current status of the TTS handler.
        
        Returns:
            Dictionary with status information
        """
        return {
            "initialized": self.is_initialized,
            "current_voice": self.current_voice,
            "current_language": self.current_language,
            "is_speaking": self.is_speaking(),
            "available_voices": len(self.get_available_voices()) if self.is_initialized else 0,
            "available_languages": len(self.get_available_languages()) if self.is_initialized else 0
        }
    
    def configure(self, **kwargs) -> bool:
        """
        Update TTS configuration settings.
        
        Args:
            **kwargs: Configuration parameters to update
            
        Returns:
            True if configuration updated successfully, False otherwise
        """
        try:
            for key, value in kwargs.items():
                if key in self.config:
                    self.config[key] = value
            return True
        except Exception:
            return False