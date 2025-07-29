from abc import ABC, abstractmethod
from typing import Iterator, Optional, Dict, Any
import logging

class BaseModelHandler(ABC):
    """
    Abstract base class for all model handlers in PersonaOS.
    
    This interface defines the standard methods that all model backends
    (Ollama, llama-cpp-python, OpenAI, etc.) must implement.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the model handler with configuration.
        
        Args:
            config: Configuration dictionary containing model settings
        """
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self._is_loaded = False
    
    @abstractmethod
    def load_model(self) -> bool:
        """
        Load the model into memory and prepare for inference.
        
        Returns:
            True if model loaded successfully, False otherwise
        """
        pass
    
    @abstractmethod
    def generate(self, prompt: str, stream: bool = False) -> str | Iterator[str]:
        """
        Generate a response from the model.
        
        Args:
            prompt: Input text prompt
            stream: Whether to return streaming response
            
        Returns:
            Complete response string or iterator of response tokens
        """
        pass
    
    @abstractmethod
    def generate_streaming(self, prompt: str) -> Iterator[str]:
        """
        Generate a streaming response from the model.
        
        Args:
            prompt: Input text prompt
            
        Yields:
            Response tokens as they are generated
        """
        pass
    
    @abstractmethod
    def stop(self) -> bool:
        """
        Stop any ongoing generation and clean up resources.
        
        Returns:
            True if stopped successfully, False otherwise
        """
        pass
    
    @abstractmethod
    def unload_model(self) -> bool:
        """
        Unload the model from memory and free resources.
        
        Returns:
            True if unloaded successfully, False otherwise
        """
        pass
    
    def is_loaded(self) -> bool:
        """
        Check if the model is currently loaded and ready for inference.
        
        Returns:
            True if model is loaded, False otherwise
        """
        return self._is_loaded
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the current model.
        
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
        Validate the configuration for this handler.
        
        Returns:
            True if configuration is valid, False otherwise
        """
        return True