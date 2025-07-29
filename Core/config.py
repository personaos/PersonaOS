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
        # AUDIO & VOICE SETTINGS
        # ==============================================
        
        # Speech-to-Text (STT) Configuration
        "stt_enabled": os.getenv("STT_ENABLED", "false").lower() == "true",
        "stt_model": os.getenv("STT_MODEL", "base"),
        "stt_language": os.getenv("STT_LANGUAGE", "en"),
        "stt_device_index": _safe_int(os.getenv("STT_DEVICE_INDEX")),
        
        # Text-to-Speech (TTS) Configuration
        "tts_enabled": os.getenv("TTS_ENABLED", "true").lower() == "true",
        "tts_voice": os.getenv("TTS_VOICE", None),
        "tts_language": os.getenv("TTS_LANGUAGE", "en"),
        "tts_rate": int(os.getenv("TTS_RATE", "200")),
        "tts_volume": float(os.getenv("TTS_VOLUME", "0.9")),
        "tts_streaming_enabled": os.getenv("TTS_STREAMING_ENABLED", "true").lower() == "true",
        
        # Voice Pipeline Controller Settings
        "voice_pipeline_enabled": os.getenv("VOICE_PIPELINE_ENABLED", "true").lower() == "true",
        "voice_auto_start": os.getenv("VOICE_AUTO_START", "false").lower() == "true",
        "voice_response_timeout": int(os.getenv("VOICE_RESPONSE_TIMEOUT", "30")),
        "voice_state_callbacks": os.getenv("VOICE_STATE_CALLBACKS", "true").lower() == "true",
        "voice_metrics_enabled": os.getenv("VOICE_METRICS_ENABLED", "true").lower() == "true",
        
        # Voice Error Handling & Fallback Settings
        "voice_fallback_enabled": os.getenv("VOICE_FALLBACK_ENABLED", "true").lower() == "true",
        "voice_max_retries": int(os.getenv("VOICE_MAX_RETRIES", "3")),
        "tts_fallback_enabled": os.getenv("TTS_FALLBACK_ENABLED", "true").lower() == "true",
        
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
        "memory_dir": os.getenv("MEMORY_DIR", "data/memory"),
        "enable_persistent_memory": os.getenv("ENABLE_PERSISTENT_MEMORY", "true").lower() == "true",
        "max_session_messages": int(os.getenv("MAX_SESSION_MESSAGES", "50")),
        "max_context_length": int(os.getenv("MAX_CONTEXT_LENGTH", "4000")),
        "memory_retention_days": int(os.getenv("MEMORY_RETENTION_DAYS", "30")),
        
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
    
    # Check memory settings
    if config['max_session_messages'] < 1:
        issues['max_session_messages'] = "Must be at least 1"
    
    if config['max_context_length'] < 100:
        issues['max_context_length'] = "Must be at least 100"
    
    if config['memory_retention_days'] < 1:
        issues['memory_retention_days'] = "Must be at least 1 day"
    
    # Check STT settings
    valid_stt_models = ['tiny', 'base', 'small', 'medium', 'large']
    if config['stt_model'] not in valid_stt_models:
        issues['stt_model'] = f"Must be one of: {', '.join(valid_stt_models)}"
    
    # Check STT language (basic validation)
    if config['stt_language'] and len(config['stt_language']) not in [2, 5]:  # 'en' or 'en-US'
        issues['stt_language'] = "Must be a valid language code (e.g., 'en', 'en-US', or 'auto')"
    
    # Check voice pipeline settings
    if config['voice_response_timeout'] < 5:
        issues['voice_response_timeout'] = "Must be at least 5 seconds"
    elif config['voice_response_timeout'] > 300:
        issues['voice_response_timeout'] = "Must be no more than 300 seconds (5 minutes)"
    
    # Check voice error handling settings
    if config['voice_max_retries'] < 1:
        issues['voice_max_retries'] = "Must be at least 1"
    elif config['voice_max_retries'] > 10:
        issues['voice_max_retries'] = "Must be no more than 10"
    
    # Check TTS settings
    if config['tts_rate'] < 50:
        issues['tts_rate'] = "Must be at least 50 words per minute"
    elif config['tts_rate'] > 500:
        issues['tts_rate'] = "Must be no more than 500 words per minute"
    
    if not (0.0 <= config['tts_volume'] <= 1.0):
        issues['tts_volume'] = "Must be between 0.0 and 1.0"
    
    # Check TTS language (basic validation)
    if config['tts_language'] and len(config['tts_language']) not in [2, 5]:  # 'en' or 'en-US'
        issues['tts_language'] = "Must be a valid language code (e.g., 'en', 'en-US')"
    
    return issues
