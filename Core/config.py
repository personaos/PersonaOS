# core/config.py

import os
from dotenv import load_dotenv

def load_config():
    """
    Load runtime configuration from .env and return as a dictionary.
    This config will be passed to modules (LLM, STT, TTS, etc.)
    """
    load_dotenv()  # Ensure environment variables are loaded

    config = {
        # General settings
        "llm_model": os.getenv("LLM_MODEL", "ollama"),

        # Ollama-specific
        "ollama_model": os.getenv("OLLAMA_MODEL", "llama2"),
        "ollama_api_url": os.getenv("OLLAMA_API_URL", None),  # If None, defaults to CLI mode

        # Wakeword (future use)
        "wakeword_engine": os.getenv("WAKEWORD_ENGINE", "porcupine"),
        "porcupine_keyword_path": os.getenv("PORCUPINE_KEYWORD_PATH", "wakeword/hey_persona.ppn"),
        "porcupine_library_path": os.getenv("PORCUPINE_LIBRARY_PATH", None),
        "porcupine_model_path": os.getenv("PORCUPINE_MODEL_PATH", None),
        "porcupine_access_key": os.getenv("PORCUPINE_ACCESS_KEY", None),

        # Memory (placeholder for future memory modules)
        "memory_enabled": os.getenv("MEMORY_ENABLED", "true").lower() == "true",
    }

    return config
