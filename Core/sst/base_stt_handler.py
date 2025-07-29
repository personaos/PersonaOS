from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, BinaryIO
import logging

class BaseSTTHandler(ABC):
    """
    Abstract base class for all speech-to-text handlers in PersonaOS.
    
    This interface defines the standard methods that all STT backends
    (Whisper, other STT engines) must implement.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the STT handler with configuration.
        
        Args:
            config: Configuration dictionary containing STT settings
        """
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self._is_loaded = False
    
    @abstractmethod
    def load_model(self) -> bool:
        """
        Load the STT model into memory and prepare for transcription.
        
        Returns:
            True if model loaded successfully, False otherwise
        """
        pass
    
    @abstractmethod
    def transcribe_audio(self, audio_data: bytes) -> Optional[str]:
        """
        Transcribe audio data to text.
        
        Args:
            audio_data: Raw audio data in bytes
            
        Returns:
            Transcribed text or None if transcription failed
        """
        pass
    
    @abstractmethod
    def transcribe_file(self, audio_file_path: str) -> Optional[str]:
        """
        Transcribe audio file to text.
        
        Args:
            audio_file_path: Path to audio file
            
        Returns:
            Transcribed text or None if transcription failed
        """
        pass
    
    @abstractmethod
    def start_streaming_transcription(self) -> bool:
        """
        Start real-time streaming transcription from microphone.
        
        Returns:
            True if streaming started successfully, False otherwise
        """
        pass
    
    @abstractmethod
    def stop_streaming_transcription(self) -> bool:
        """
        Stop streaming transcription and clean up resources.
        
        Returns:
            True if stopped successfully, False otherwise
        """
        pass
    
    @abstractmethod
    def unload_model(self) -> bool:
        """
        Unload the STT model from memory and free resources.
        
        Returns:
            True if unloaded successfully, False otherwise
        """
        pass
    
    def is_loaded(self) -> bool:
        """
        Check if the STT model is currently loaded and ready for transcription.
        
        Returns:
            True if model is loaded, False otherwise
        """
        return self._is_loaded
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the current STT model.
        
        Returns:
            Dictionary containing model metadata
        """
        return {
            "handler_type": self.__class__.__name__,
            "is_loaded": self.is_loaded(),
            "config": self.config
        }
    
    def validate_config(self) -> bool:
        """
        Validate the configuration for this STT handler.
        
        Returns:
            True if configuration is valid, False otherwise
        """
        required_keys = ["stt_enabled", "stt_model"]
        return all(key in self.config for key in required_keys)