import os
import subprocess
import requests
import json
import logging
from .model_config_loader import ModelConfigLoader
from .base_model_handler import BaseModelHandler

class OllamaHandler(BaseModelHandler):
    """
    Legacy Ollama handler adapted to use BaseModelHandler interface.
    """
    
    def __init__(self, config):
        super().__init__(config)
        self.model = config.get("model", "llama2")
        self.api_url = config.get("api_url")
        self._is_loaded = True  # Ollama is always "loaded"

    def load_model(self) -> bool:
        """Ollama models are loaded on-demand, so this is always successful."""
        self._is_loaded = True
        return True

    def generate(self, prompt: str, stream: bool = False):
        """Generate response using Ollama."""
        if stream:
            return self.generate_streaming(prompt)
        else:
            return self.query(prompt)

    def generate_streaming(self, prompt: str):
        """Ollama doesn't support streaming in this implementation."""
        response = self.query(prompt)
        yield response

    def stop(self) -> bool:
        """Stop is not applicable for Ollama."""
        return True

    def unload_model(self) -> bool:
        """Unload is not applicable for Ollama."""
        return True

    def query_cli(self, prompt):
        try:
            result = subprocess.run(
                ["ollama", "chat", self.model, "--prompt", prompt],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            return f"Error calling Ollama CLI: {e.stderr}"

    def query_api(self, prompt):
        if not self.api_url:
            return "API URL not set for Ollama API mode."

        url = f"{self.api_url}/chat/completions"
        headers = {"Content-Type": "application/json"}
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}]
        }
        try:
            response = requests.post(url, headers=headers, data=json.dumps(payload))
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()
        except requests.RequestException as e:
            return f"Error calling Ollama API: {str(e)}"

    def query(self, prompt):
        if self.api_url:
            return self.query_api(prompt)
        else:
            return self.query_cli(prompt)


class LLMManager:
    """
    Enhanced LLM Manager with DME support.
    
    Manages different model backends including Ollama and llama-cpp-python.
    """
    
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.model_config_loader = ModelConfigLoader()
        self.llm = None
        self.current_backend = None
        self._init_llm()

    def _init_llm(self):
        """Initialize the LLM based on configuration."""
        # Check for DME model backend setting
        backend_name = self.config.get("model_backend") or self.config.get("llm_model", "ollama")
        
        try:
            backend_config = self.model_config_loader.get_backend_config(backend_name)
            if not backend_config:
                self.logger.warning(f"Backend '{backend_name}' not found, falling back to ollama")
                backend_config = self.model_config_loader.get_backend_config("ollama")
                backend_name = "ollama"
            
            backend_type = backend_config.get("type", backend_name)
            self.current_backend = backend_name
            
            if backend_type == "ollama":
                # Legacy compatibility - merge old config format
                legacy_config = {
                    "model": self.config.get("ollama_model", backend_config.get("model", "llama2")),
                    "api_url": self.config.get("ollama_api_url", backend_config.get("api_url"))
                }
                backend_config.update(legacy_config)
                self.llm = OllamaHandler(backend_config)
                
            elif backend_type == "llama_cpp":
                from .llama_cpp_handler import LlamaCppHandler
                self.llm = LlamaCppHandler(backend_config)
                
                # Load model automatically for DME backends
                if not self.llm.load_model():
                    self.logger.error("Failed to load llama-cpp model")
                    self.llm = None
                    
            else:
                raise NotImplementedError(f"Backend type '{backend_type}' not supported")
                
            self.logger.info(f"Initialized LLM backend: {backend_name} (type: {backend_type})")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize LLM backend '{backend_name}': {e}")
            # Fallback to basic Ollama configuration
            self._init_fallback_ollama()

    def _init_fallback_ollama(self):
        """Initialize fallback Ollama handler when other backends fail."""
        self.logger.info("Falling back to basic Ollama configuration")
        fallback_config = {
            "model": self.config.get("ollama_model", "llama2"),
            "api_url": self.config.get("ollama_api_url")
        }
        self.llm = OllamaHandler(fallback_config)
        self.current_backend = "ollama"

    def query(self, prompt, stream=False):
        """
        Query the LLM with enhanced DME support.
        
        Args:
            prompt: Input prompt
            stream: Whether to use streaming (if supported)
            
        Returns:
            Response string or iterator for streaming
        """
        if not self.llm:
            return "No LLM initialized."
        
        try:
            # Use new interface if available
            if hasattr(self.llm, 'generate'):
                return self.llm.generate(prompt, stream=stream)
            # Fallback to legacy interface
            else:
                return self.llm.query(prompt)
                
        except Exception as e:
            self.logger.error(f"Query failed: {e}")
            return f"Error during LLM query: {str(e)}"

    def switch_backend(self, backend_name: str) -> bool:
        """
        Switch to a different model backend.
        
        Args:
            backend_name: Name of backend to switch to
            
        Returns:
            True if switch was successful
        """
        if backend_name == self.current_backend:
            return True
        
        try:
            # Unload current model if it's a DME backend
            if self.llm and hasattr(self.llm, 'unload_model'):
                self.llm.unload_model()
            
            # Save current backend for rollback
            old_backend = self.current_backend
            old_llm = self.llm
            
            # Update config and reinitialize
            self.config["model_backend"] = backend_name
            self._init_llm()
            
            if self.llm is None:
                # Rollback on failure
                self.current_backend = old_backend
                self.llm = old_llm
                return False
            
            self.logger.info(f"Switched to backend: {backend_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to switch backend to '{backend_name}': {e}")
            return False

    def list_available_backends(self) -> list[str]:
        """Get list of available backends."""
        return self.model_config_loader.list_available_backends()

    def get_current_backend_info(self) -> dict:
        """Get information about current backend."""
        if not self.llm:
            return {"backend": None, "status": "not_initialized"}
        
        info = {
            "backend": self.current_backend,
            "status": "loaded" if self.llm.is_loaded() else "unloaded"
        }
        
        if hasattr(self.llm, 'get_model_info'):
            info.update(self.llm.get_model_info())
        
        return info


def init_llm_manager(config):
    return LLMManager(config)


def handle_conversation(prompt, config, memory, llm_manager):
    from ..intent.intent_processor import IntentProcessor
    
    # Add user message to memory
    if memory:
        memory.add_message("user", prompt)
    
    # Initialize intent processor
    intent_processor = IntentProcessor(config)
    
    # Process user input through intent system
    intent_response = intent_processor.process(prompt)
    
    # Handle different actions
    if intent_response["action"] in ["blocked", "refused", "tool_executed", "tool_failed"]:
        response = intent_response["response"]
        
        # Add system response to memory
        if memory:
            memory.add_message("system", response, {"intent_action": intent_response["action"]})
        
        return response
    
    elif intent_response["action"] == "llm_response":
        # Get conversation context for LLM
        context_messages = []
        if memory:
            context_messages = memory.get_context_for_llm(config.get("max_context_length", 4000))
        
        # If we have context, use it; otherwise just query with the current prompt
        if context_messages:
            # For now, use the full context as a single prompt
            # TODO: Implement proper conversation context handling in LLM
            full_context = "\n".join([f"{msg['role']}: {msg['content']}" for msg in context_messages])
            response = llm_manager.query(full_context)
        else:
            response = llm_manager.query(prompt)
        
        # Add assistant response to memory
        if memory:
            memory.add_message("assistant", response)
        
        return response
    
    else:
        # Fallback to direct LLM query
        response = llm_manager.query(prompt)
        
        # Add assistant response to memory
        if memory:
            memory.add_message("assistant", response)
        
        return response
