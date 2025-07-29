import os
from typing import Iterator, Dict, Any, Optional
import logging
from .base_model_handler import BaseModelHandler

try:
    from llama_cpp import Llama
    LLAMA_CPP_AVAILABLE = True
except ImportError:
    LLAMA_CPP_AVAILABLE = False
    Llama = None

class LlamaCppHandler(BaseModelHandler):
    """
    Handler for running GGUF models locally using llama-cpp-python.
    
    This handler provides direct model execution (DME) capabilities,
    allowing PersonaOS to run quantized LLaMA models locally without
    external dependencies like Ollama.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the llama-cpp handler.
        
        Args:
            config: Configuration dictionary containing:
                - model_path: Path to GGUF model file
                - n_ctx: Context length (default: 2048)
                - n_threads: CPU threads (default: auto-detect)
                - n_gpu_layers: GPU layers (default: 0 for CPU-only)
                - temperature: Sampling temperature (default: 0.7)
                - top_p: Top-p sampling (default: 0.9)
                - max_tokens: Max response tokens (default: 512)
        """
        super().__init__(config)
        
        if not LLAMA_CPP_AVAILABLE:
            raise ImportError(
                "llama-cpp-python is not installed. "
                "Install it with: pip install llama-cpp-python"
            )
        
        self.model: Optional[Llama] = None
        self.model_path = config.get("model_path")
        self.n_ctx = config.get("n_ctx", 2048)
        self.n_threads = config.get("n_threads", -1)  # Auto-detect
        self.n_gpu_layers = config.get("n_gpu_layers", 0)  # CPU-only by default
        
        # Generation parameters
        self.temperature = config.get("temperature", 0.7)
        self.top_p = config.get("top_p", 0.9)
        self.max_tokens = config.get("max_tokens", 512)
        self.stop_sequences = config.get("stop_sequences", [])
        
        # Validate configuration
        if not self.model_path:
            raise ValueError("model_path must be specified in config")
        
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"Model file not found: {self.model_path}")
    
    def load_model(self) -> bool:
        """
        Load the GGUF model into memory.
        
        Returns:
            True if model loaded successfully, False otherwise
        """
        try:
            self.logger.info(f"Loading model from: {self.model_path}")
            self.logger.info(f"Context length: {self.n_ctx}, GPU layers: {self.n_gpu_layers}")
            
            self.model = Llama(
                model_path=self.model_path,
                n_ctx=self.n_ctx,
                n_threads=self.n_threads,
                n_gpu_layers=self.n_gpu_layers,
                verbose=self.config.get("verbose", False)
            )
            
            self._is_loaded = True
            self.logger.info("Model loaded successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to load model: {e}")
            self._is_loaded = False
            return False
    
    def generate(self, prompt: str, stream: bool = False) -> str | Iterator[str]:
        """
        Generate a response from the model.
        
        Args:
            prompt: Input text prompt
            stream: Whether to return streaming response
            
        Returns:
            Complete response string or iterator of response tokens
        """
        if not self.is_loaded():
            raise RuntimeError("Model not loaded. Call load_model() first.")
        
        if stream:
            return self.generate_streaming(prompt)
        else:
            return self._generate_complete(prompt)
    
    def _generate_complete(self, prompt: str) -> str:
        """Generate a complete response (non-streaming)."""
        try:
            response = self.model.create_completion(
                prompt=prompt,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                top_p=self.top_p,
                stop=self.stop_sequences,
                stream=False
            )
            
            return response['choices'][0]['text'].strip()
            
        except Exception as e:
            self.logger.error(f"Generation failed: {e}")
            return f"Error during generation: {str(e)}"
    
    def generate_streaming(self, prompt: str) -> Iterator[str]:
        """
        Generate a streaming response from the model.
        
        Args:
            prompt: Input text prompt
            
        Yields:
            Response tokens as they are generated
        """
        if not self.is_loaded():
            raise RuntimeError("Model not loaded. Call load_model() first.")
        
        try:
            stream = self.model.create_completion(
                prompt=prompt,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                top_p=self.top_p,
                stop=self.stop_sequences,
                stream=True
            )
            
            for chunk in stream:
                if 'choices' in chunk and len(chunk['choices']) > 0:
                    token = chunk['choices'][0].get('text', '')
                    if token:
                        yield token
                        
        except Exception as e:
            self.logger.error(f"Streaming generation failed: {e}")
            yield f"Error during streaming: {str(e)}"
    
    def stop(self) -> bool:
        """
        Stop any ongoing generation.
        
        Note: llama-cpp-python doesn't have explicit stop mechanism,
        but we can implement this for future use.
        
        Returns:
            True (always successful for this implementation)
        """
        self.logger.info("Stop requested (no-op for llama-cpp)")
        return True
    
    def unload_model(self) -> bool:
        """
        Unload the model from memory and free resources.
        
        Returns:
            True if unloaded successfully, False otherwise
        """
        try:
            if self.model is not None:
                # Force garbage collection
                del self.model
                self.model = None
                
            self._is_loaded = False
            self.logger.info("Model unloaded successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to unload model: {e}")
            return False
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the current model.
        
        Returns:
            Dictionary containing model metadata
        """
        info = super().get_model_info()
        info.update({
            "model_path": self.model_path,
            "context_length": self.n_ctx,
            "gpu_layers": self.n_gpu_layers,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "max_tokens": self.max_tokens,
            "backend": "llama-cpp-python"
        })
        return info
    
    def validate_config(self) -> bool:
        """
        Validate the configuration for this handler.
        
        Returns:
            True if configuration is valid, False otherwise
        """
        if not self.model_path:
            self.logger.error("model_path is required")
            return False
        
        if not os.path.exists(self.model_path):
            self.logger.error(f"Model file does not exist: {self.model_path}")
            return False
        
        if not self.model_path.lower().endswith('.gguf'):
            self.logger.warning("Model file should have .gguf extension")
        
        if self.n_ctx < 512:
            self.logger.error("Context length should be at least 512")
            return False
        
        if self.max_tokens <= 0:
            self.logger.error("max_tokens must be positive")
            return False
        
        if not 0.0 <= self.temperature <= 2.0:
            self.logger.error("temperature should be between 0.0 and 2.0")
            return False
        
        if not 0.0 <= self.top_p <= 1.0:
            self.logger.error("top_p should be between 0.0 and 1.0")
            return False
        
        return True