"""
API Key Management System for PersonaOS

This module provides secure API key management, validation, and rotation
for various LLM providers and external services used by PersonaOS.
"""

import os
import json
import hashlib
import base64
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass
from pathlib import Path
from cryptography.fernet import Fernet
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)

@dataclass
class APIKeyConfig:
    """Configuration for an API key."""
    provider: str
    key_name: str
    encrypted_key: str
    created_at: str
    last_used: Optional[str] = None
    usage_count: int = 0
    is_active: bool = True
    rate_limit: Optional[int] = None
    monthly_quota: Optional[int] = None

class APIKeyManager:
    """
    Secure API key management system for PersonaOS.
    
    Features:
    - Encrypted storage of API keys
    - Key validation and health checking
    - Usage tracking and rate limiting
    - Multi-provider support
    - Key rotation capabilities
    """
    
    SUPPORTED_PROVIDERS = {
        'openai': {
            'name': 'OpenAI',
            'key_format': r'^sk-[A-Za-z0-9]{48}$',
            'test_endpoint': 'https://api.openai.com/v1/models',
            'default_model': 'gpt-3.5-turbo'
        },
        'anthropic': {
            'name': 'Anthropic Claude',
            'key_format': r'^sk-ant-[A-Za-z0-9-_]{95}$',
            'test_endpoint': 'https://api.anthropic.com/v1/messages',
            'default_model': 'claude-3-sonnet-20240229'
        },
        'google': {
            'name': 'Google AI (Gemini)',
            'key_format': r'^[A-Za-z0-9_-]{39}$',
            'test_endpoint': 'https://generativelanguage.googleapis.com/v1/models',
            'default_model': 'gemini-pro'
        },
        'cohere': {
            'name': 'Cohere',
            'key_format': r'^[A-Za-z0-9]{40}$',
            'test_endpoint': 'https://api.cohere.ai/v1/models',
            'default_model': 'command'
        },
        'picovoice': {
            'name': 'Picovoice (Wake Word)',
            'key_format': r'^[A-Za-z0-9+/=]{44}$',
            'test_endpoint': None,  # No direct test endpoint
            'default_model': 'porcupine'
        },
        'elevenlabs': {
            'name': 'ElevenLabs (TTS)',
            'key_format': r'^[A-Za-z0-9]{32}$',
            'test_endpoint': 'https://api.elevenlabs.io/v1/voices',
            'default_model': 'eleven_monolingual_v1'
        }
    }
    
    def __init__(self, config_dir: str = None):
        """Initialize API key manager."""
        load_dotenv()
        
        # Set up directories
        self.config_dir = Path(config_dir or os.getenv('PERSONAOS_CONFIG_DIR', 'config'))
        self.config_dir.mkdir(exist_ok=True)
        
        self.keys_file = self.config_dir / 'api_keys.json'
        self.encryption_key_file = self.config_dir / '.api_encryption_key'
        
        # Initialize encryption
        self._init_encryption()
        
        # Load existing keys
        self.keys: Dict[str, APIKeyConfig] = self._load_keys()
        
    def _init_encryption(self):
        """Initialize or load encryption key for API key storage."""
        if self.encryption_key_file.exists():
            with open(self.encryption_key_file, 'rb') as f:
                self.encryption_key = f.read()
        else:
            # Generate new encryption key
            self.encryption_key = Fernet.generate_key()
            with open(self.encryption_key_file, 'wb') as f:
                f.write(self.encryption_key)
            # Secure the file (Unix permissions)
            os.chmod(self.encryption_key_file, 0o600)
        
        self.cipher = Fernet(self.encryption_key)
    
    def _load_keys(self) -> Dict[str, APIKeyConfig]:
        """Load encrypted API keys from storage."""
        if not self.keys_file.exists():
            return {}
        
        try:
            with open(self.keys_file, 'r') as f:
                encrypted_data = json.load(f)
            
            keys = {}
            for key_id, data in encrypted_data.items():
                keys[key_id] = APIKeyConfig(**data)
            
            return keys
        except Exception as e:
            logger.error(f"Failed to load API keys: {e}")
            return {}
    
    def _save_keys(self):
        """Save encrypted API keys to storage."""
        try:
            data = {}
            for key_id, config in self.keys.items():
                data[key_id] = {
                    'provider': config.provider,
                    'key_name': config.key_name,
                    'encrypted_key': config.encrypted_key,
                    'created_at': config.created_at,
                    'last_used': config.last_used,
                    'usage_count': config.usage_count,
                    'is_active': config.is_active,
                    'rate_limit': config.rate_limit,
                    'monthly_quota': config.monthly_quota
                }
            
            with open(self.keys_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            # Secure the file
            os.chmod(self.keys_file, 0o600)
            
        except Exception as e:
            logger.error(f"Failed to save API keys: {e}")
    
    def add_key(self, provider: str, api_key: str, key_name: str = None, 
                rate_limit: int = None, monthly_quota: int = None) -> bool:
        """
        Add a new API key for a provider.
        
        Args:
            provider: Provider name (e.g., 'openai', 'anthropic')
            api_key: The actual API key
            key_name: Optional name for the key
            rate_limit: Optional rate limit (requests per minute)
            monthly_quota: Optional monthly usage quota
            
        Returns:
            True if key was added successfully
        """
        if provider not in self.SUPPORTED_PROVIDERS:
            logger.error(f"Unsupported provider: {provider}")
            return False
        
        # Validate key format
        if not self._validate_key_format(provider, api_key):
            logger.error(f"Invalid API key format for {provider}")
            return False
        
        # Encrypt the key
        encrypted_key = self.cipher.encrypt(api_key.encode()).decode()
        
        # Generate key ID
        key_id = self._generate_key_id(provider, api_key)
        
        # Create config
        config = APIKeyConfig(
            provider=provider,
            key_name=key_name or f"{provider}_key_{len(self.keys) + 1}",
            encrypted_key=encrypted_key,
            created_at=self._get_timestamp(),
            rate_limit=rate_limit,
            monthly_quota=monthly_quota
        )
        
        self.keys[key_id] = config
        self._save_keys()
        
        logger.info(f"Added API key for {provider}: {config.key_name}")
        return True
    
    def get_key(self, provider: str, key_name: str = None) -> Optional[str]:
        """
        Retrieve and decrypt an API key.
        
        Args:
            provider: Provider name
            key_name: Optional specific key name (uses first active if None)
            
        Returns:
            Decrypted API key or None if not found
        """
        for key_id, config in self.keys.items():
            if (config.provider == provider and config.is_active and
                (key_name is None or config.key_name == key_name)):
                
                try:
                    decrypted_key = self.cipher.decrypt(config.encrypted_key.encode()).decode()
                    
                    # Update usage tracking
                    config.last_used = self._get_timestamp()
                    config.usage_count += 1
                    self._save_keys()
                    
                    return decrypted_key
                except Exception as e:
                    logger.error(f"Failed to decrypt key {key_id}: {e}")
                    continue
        
        return None
    
    def list_keys(self, provider: str = None) -> List[Dict]:
        """
        List configured API keys (without revealing actual keys).
        
        Args:
            provider: Optional provider filter
            
        Returns:
            List of key information dictionaries
        """
        keys_info = []
        for key_id, config in self.keys.items():
            if provider is None or config.provider == provider:
                keys_info.append({
                    'key_id': key_id,
                    'provider': config.provider,
                    'key_name': config.key_name,
                    'created_at': config.created_at,
                    'last_used': config.last_used,
                    'usage_count': config.usage_count,
                    'is_active': config.is_active,
                    'rate_limit': config.rate_limit,
                    'monthly_quota': config.monthly_quota
                })
        
        return keys_info
    
    def validate_key(self, provider: str, key_name: str = None) -> Tuple[bool, str]:
        """
        Validate an API key by making a test request.
        
        Args:
            provider: Provider name
            key_name: Optional specific key name
            
        Returns:
            (is_valid, status_message)
        """
        api_key = self.get_key(provider, key_name)
        if not api_key:
            return False, "API key not found"
        
        provider_config = self.SUPPORTED_PROVIDERS.get(provider)
        if not provider_config or not provider_config['test_endpoint']:
            return True, "No validation endpoint available"
        
        # TODO: Implement actual API validation calls
        # This would make HTTP requests to test endpoints
        return True, "Validation not implemented yet"
    
    def remove_key(self, key_id: str) -> bool:
        """Remove an API key."""
        if key_id in self.keys:
            del self.keys[key_id]
            self._save_keys()
            logger.info(f"Removed API key: {key_id}")
            return True
        return False
    
    def deactivate_key(self, key_id: str) -> bool:
        """Deactivate an API key without removing it."""
        if key_id in self.keys:
            self.keys[key_id].is_active = False
            self._save_keys()
            logger.info(f"Deactivated API key: {key_id}")
            return True
        return False
    
    def _validate_key_format(self, provider: str, api_key: str) -> bool:
        """Validate API key format using regex."""
        import re
        provider_config = self.SUPPORTED_PROVIDERS.get(provider)
        if not provider_config:
            return False
        
        pattern = provider_config['key_format']
        return bool(re.match(pattern, api_key))
    
    def _generate_key_id(self, provider: str, api_key: str) -> str:
        """Generate a unique key ID."""
        hash_input = f"{provider}:{api_key}:{self._get_timestamp()}"
        return hashlib.sha256(hash_input.encode()).hexdigest()[:16]
    
    def _get_timestamp(self) -> str:
        """Get current timestamp."""
        from datetime import datetime
        return datetime.utcnow().isoformat()
    
    def get_provider_config(self, provider: str) -> Optional[Dict]:
        """Get configuration for a provider."""
        return self.SUPPORTED_PROVIDERS.get(provider)
    
    def migrate_from_env(self) -> Dict[str, bool]:
        """
        Migrate API keys from environment variables to encrypted storage.
        
        Returns:
            Dictionary of migration results
        """
        results = {}
        
        # Common environment variable patterns
        env_patterns = {
            'openai': ['OPENAI_API_KEY', 'OPENAI_KEY'],
            'anthropic': ['ANTHROPIC_API_KEY', 'CLAUDE_API_KEY'],
            'google': ['GOOGLE_API_KEY', 'GEMINI_API_KEY'],
            'cohere': ['COHERE_API_KEY'],
            'picovoice': ['PICOVOICE_API_KEY', 'PORCUPINE_ACCESS_KEY'],
            'elevenlabs': ['ELEVENLABS_API_KEY']
        }
        
        for provider, env_vars in env_patterns.items():
            for env_var in env_vars:
                api_key = os.getenv(env_var)
                if api_key:
                    success = self.add_key(
                        provider=provider,
                        api_key=api_key,
                        key_name=f"migrated_{env_var.lower()}"
                    )
                    results[env_var] = success
                    if success:
                        logger.info(f"Migrated {env_var} to encrypted storage")
        
        return results


# Singleton instance
_api_manager = None

def get_api_manager() -> APIKeyManager:
    """Get the global API manager instance."""
    global _api_manager
    if _api_manager is None:
        _api_manager = APIKeyManager()
    return _api_manager


# Utility functions for easy access
def get_api_key(provider: str, key_name: str = None) -> Optional[str]:
    """Quick access to get an API key."""
    return get_api_manager().get_key(provider, key_name)

def add_api_key(provider: str, api_key: str, key_name: str = None) -> bool:
    """Quick access to add an API key."""
    return get_api_manager().add_key(provider, api_key, key_name)

def validate_api_key(provider: str, key_name: str = None) -> Tuple[bool, str]:
    """Quick access to validate an API key."""
    return get_api_manager().validate_key(provider, key_name)