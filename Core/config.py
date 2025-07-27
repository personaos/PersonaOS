# core/config.py

import os
from dotenv import load_dotenv
from typing import Dict, Optional
import logging

# Import API manager for secure key access
try:
    from .api_manager import get_api_manager
    API_MANAGER_AVAILABLE = True
except ImportError:
    API_MANAGER_AVAILABLE = False
    logging.warning("API Manager not available, falling back to environment variables")

def load_config():
    """
    Load runtime configuration from .env and secure API key storage.
    This config will be passed to modules (LLM, STT, TTS, etc.)
    
    Returns:
        Dictionary containing all configuration settings
    """
    load_dotenv()  # Ensure environment variables are loaded

    config = {
        # ==============================================
        # CORE SYSTEM SETTINGS
        # ==============================================
        
        # General LLM settings
        "llm_provider": os.getenv("LLM_PROVIDER", "ollama"),
        "llm_model": os.getenv("LLM_MODEL", "ollama"),

        # Ollama-specific (local/privacy-first option)
        "ollama_model": os.getenv("OLLAMA_MODEL", "openhermes"),
        "ollama_api_url": os.getenv("OLLAMA_API_URL", None),

        # Configuration directory
        "config_dir": os.getenv("PERSONAOS_CONFIG_DIR", "config"),

        # ==============================================
        # API KEY MANAGEMENT
        # ==============================================
        
        # Security settings
        "use_encrypted_storage": os.getenv("USE_ENCRYPTED_STORAGE", "true").lower() == "true",
        "auto_migrate_env_keys": os.getenv("AUTO_MIGRATE_ENV_KEYS", "true").lower() == "true",
        
        # Rate limiting
        "default_rate_limit": int(os.getenv("DEFAULT_RATE_LIMIT", "60")),
        "monthly_quota_warning": os.getenv("MONTHLY_QUOTA_WARNING", "true").lower() == "true",

        # ==============================================
        # AUDIO & HARDWARE
        # ==============================================
        
        # Wakeword detection
        "wakeword_engine": os.getenv("WAKEWORD_ENGINE", "porcupine"),
        "porcupine_keyword_path": os.getenv("PORCUPINE_KEYWORD_PATH", "wakeword/hey_persona.ppn"),
        "porcupine_library_path": os.getenv("PORCUPINE_LIBRARY_PATH", None),
        "porcupine_model_path": os.getenv("PORCUPINE_MODEL_PATH", None),
        
        # Audio devices
        "mic_device_index": _safe_int(os.getenv("MIC_DEVICE_INDEX")),
        "speaker_device_index": _safe_int(os.getenv("SPEAKER_DEVICE_INDEX")),

        # ==============================================
        # INTENT & SAFETY
        # ==============================================
        
        # Memory management
        "memory_enabled": os.getenv("MEMORY_ENABLED", "true").lower() == "true",
        
        # Intent processing
        "intent_enabled": os.getenv("INTENT_ENABLED", "true").lower() == "true",
        "safety_level": os.getenv("SAFETY_LEVEL", "standard"),  # strict, standard, relaxed
        "allow_tool_execution": os.getenv("ALLOW_TOOL_EXECUTION", "true").lower() == "true",
        "max_intent_confidence": float(os.getenv("MAX_INTENT_CONFIDENCE", "1.0")),

        # ==============================================
        # WEB UI & NETWORKING
        # ==============================================
        
        "web_ui_enabled": os.getenv("WEB_UI_ENABLED", "true").lower() == "true",
        "web_ui_port": int(os.getenv("WEB_UI_PORT", "8000")),
        "frontend_port": int(os.getenv("FRONTEND_PORT", "3000")),

        # ==============================================
        # DEVELOPMENT & DEBUGGING
        # ==============================================
        
        "debug_mode": os.getenv("DEBUG_MODE", "false").lower() == "true",
        "log_level": os.getenv("LOG_LEVEL", "INFO").upper(),
        "enable_api_logging": os.getenv("ENABLE_API_LOGGING", "false").lower() == "true",
    }

    # Add API keys (securely)
    config.update(_load_api_keys())
    
    # Auto-migrate environment keys if enabled
    if config["auto_migrate_env_keys"] and API_MANAGER_AVAILABLE:
        _auto_migrate_keys()

    return config

def _load_api_keys() -> Dict[str, Optional[str]]:
    """
    Load API keys from secure storage or environment variables.
    
    Returns:
        Dictionary of API keys for various providers
    """
    api_keys = {}
    
    if API_MANAGER_AVAILABLE and os.getenv("USE_ENCRYPTED_STORAGE", "true").lower() == "true":
        # Use secure API manager
        manager = get_api_manager()
        
        # Standard providers
        providers = ['openai', 'anthropic', 'google', 'cohere', 'picovoice', 'elevenlabs']
        
        for provider in providers:
            key = manager.get_key(provider)
            if key:
                api_keys[f"{provider}_api_key"] = key
                # Legacy compatibility
                if provider == 'picovoice':
                    api_keys["porcupine_access_key"] = key
    
    else:
        # Fallback to environment variables (less secure)
        logging.warning("Using environment variables for API keys (less secure)")
        
        api_keys = {
            "openai_api_key": os.getenv("OPENAI_API_KEY"),
            "anthropic_api_key": os.getenv("ANTHROPIC_API_KEY"), 
            "google_api_key": os.getenv("GOOGLE_API_KEY"),
            "cohere_api_key": os.getenv("COHERE_API_KEY"),
            "picovoice_api_key": os.getenv("PICOVOICE_API_KEY"),
            "porcupine_access_key": os.getenv("PICOVOICE_API_KEY") or os.getenv("PORCUPINE_ACCESS_KEY"),
            "elevenlabs_api_key": os.getenv("ELEVENLABS_API_KEY"),
        }
    
    return api_keys

def _auto_migrate_keys():
    """Automatically migrate API keys from environment to secure storage."""
    try:
        manager = get_api_manager()
        results = manager.migrate_from_env()
        
        if results:
            migrated_count = sum(results.values())
            logging.info(f"Auto-migrated {migrated_count} API keys to encrypted storage")
            
            if migrated_count > 0:
                logging.warning("Consider removing API keys from .env file for enhanced security")
    
    except Exception as e:
        logging.error(f"Failed to auto-migrate API keys: {e}")

def _safe_int(value: str) -> Optional[int]:
    """Safely convert string to int."""
    try:
        return int(value) if value else None
    except (ValueError, TypeError):
        return None

def get_api_key(provider: str, config: Dict = None) -> Optional[str]:
    """
    Get an API key for a specific provider.
    
    Args:
        provider: Provider name (e.g., 'openai', 'anthropic')
        config: Optional config dict (will load if not provided)
        
    Returns:
        API key string or None if not found
    """
    if config is None:
        config = load_config()
    
    # Try secure storage first
    if API_MANAGER_AVAILABLE:
        manager = get_api_manager()
        key = manager.get_key(provider)
        if key:
            return key
    
    # Fallback to config
    key_name = f"{provider}_api_key"
    return config.get(key_name)

def validate_config(config: Dict) -> Dict[str, str]:
    """
    Validate configuration and return any issues.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Dictionary of validation issues (empty if valid)
    """
    issues = {}
    
    # Check safety level
    valid_safety_levels = ['strict', 'standard', 'relaxed']
    if config['safety_level'] not in valid_safety_levels:
        issues['safety_level'] = f"Must be one of: {', '.join(valid_safety_levels)}"
    
    # Check log level
    valid_log_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
    if config['log_level'] not in valid_log_levels:
        issues['log_level'] = f"Must be one of: {', '.join(valid_log_levels)}"
    
    # Check ports
    if not (1024 <= config['web_ui_port'] <= 65535):
        issues['web_ui_port'] = "Must be between 1024 and 65535"
    
    if not (1024 <= config['frontend_port'] <= 65535):
        issues['frontend_port'] = "Must be between 1024 and 65535"
    
    # Check confidence range
    if not (0.0 <= config['max_intent_confidence'] <= 1.0):
        issues['max_intent_confidence'] = "Must be between 0.0 and 1.0"
    
    return issues
