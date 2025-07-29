import os
import yaml
import logging
from typing import Dict, Any, Optional
from pathlib import Path

class ModelConfigLoader:
    """
    Loader for model configuration from YAML files with environment variable overrides.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the model config loader.
        
        Args:
            config_path: Path to model_config.yaml file
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        
        if config_path is None:
            # Default to config/model_config.yaml relative to project root
            project_root = Path(__file__).parent.parent.parent
            config_path = project_root / "config" / "model_config.yaml"
        
        self.config_path = Path(config_path)
        self._config_cache = None
    
    def load_config(self, reload: bool = False) -> Dict[str, Any]:
        """
        Load model configuration from YAML file.
        
        Args:
            reload: Force reload from file even if cached
            
        Returns:
            Dictionary containing model configuration
        """
        if self._config_cache is not None and not reload:
            return self._config_cache
        
        try:
            if not self.config_path.exists():
                self.logger.warning(f"Model config file not found: {self.config_path}")
                return self._get_default_config()
            
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            # Apply environment variable overrides
            config = self._apply_env_overrides(config)
            
            # Validate configuration
            if not self._validate_config(config):
                self.logger.error("Invalid model configuration, using defaults")
                return self._get_default_config()
            
            self._config_cache = config
            self.logger.info(f"Loaded model configuration from {self.config_path}")
            return config
            
        except Exception as e:
            self.logger.error(f"Failed to load model config: {e}")
            return self._get_default_config()
    
    def get_backend_config(self, backend_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get configuration for a specific backend.
        
        Args:
            backend_name: Name of backend, or None for default
            
        Returns:
            Backend configuration dictionary
        """
        config = self.load_config()
        
        if backend_name is None:
            backend_name = config.get("default_backend", "ollama")
        
        backends = config.get("backends", {})
        if backend_name not in backends:
            self.logger.error(f"Backend '{backend_name}' not found in configuration")
            return {}
        
        return backends[backend_name]
    
    def list_available_backends(self) -> list[str]:
        """
        Get list of available backend names.
        
        Returns:
            List of backend names
        """
        config = self.load_config()
        return list(config.get("backends", {}).keys())
    
    def get_models_directory(self) -> Path:
        """
        Get the models directory path.
        
        Returns:
            Path to models directory
        """
        config = self.load_config()
        models_dir = config.get("model_management", {}).get("models_directory", "models")
        
        # Make relative to project root
        if not os.path.isabs(models_dir):
            project_root = Path(__file__).parent.parent.parent
            models_dir = project_root / models_dir
        
        return Path(models_dir)
    
    def _apply_env_overrides(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Apply environment variable overrides to configuration."""
        env_overrides = config.get("environment_overrides", {})
        
        for env_var, config_path in env_overrides.items():
            env_value = os.getenv(env_var)
            if env_value is not None:
                self._set_nested_value(config, config_path, self._convert_env_value(env_value))
        
        return config
    
    def _set_nested_value(self, config: Dict[str, Any], path: str, value: Any):
        """Set a nested configuration value using dot notation."""
        keys = path.split('.')
        current = config
        
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        current[keys[-1]] = value
    
    def _convert_env_value(self, value: str) -> Any:
        """Convert environment variable string to appropriate type."""
        # Handle booleans
        if value.lower() in ('true', 'false'):
            return value.lower() == 'true'
        
        # Handle integers
        try:
            return int(value)
        except ValueError:
            pass
        
        # Handle floats
        try:
            return float(value)
        except ValueError:
            pass
        
        # Return as string
        return value
    
    def _validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate the loaded configuration."""
        if not isinstance(config, dict):
            self.logger.error("Config must be a dictionary")
            return False
        
        if "backends" not in config:
            self.logger.error("Config must contain 'backends' section")
            return False
        
        backends = config["backends"]
        if not isinstance(backends, dict) or len(backends) == 0:
            self.logger.error("Backends section must be a non-empty dictionary")
            return False
        
        # Validate each backend
        for name, backend_config in backends.items():
            if not isinstance(backend_config, dict):
                self.logger.error(f"Backend '{name}' config must be a dictionary")
                return False
            
            if "type" not in backend_config:
                self.logger.error(f"Backend '{name}' must specify a type")
                return False
        
        return True
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration when file loading fails."""
        return {
            "default_backend": "ollama",
            "backends": {
                "ollama": {
                    "type": "ollama",
                    "model": "openhermes",
                    "api_url": None
                }
            },
            "model_management": {
                "models_directory": "models",
                "auto_download": False
            }
        }