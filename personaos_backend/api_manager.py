#!/usr/bin/env python3
"""
PersonaOS API Key Manager

A secure CLI tool for managing API keys used by PersonaOS backend.
Supports OpenAI, Anthropic, Groq, and custom LLM providers.

Usage:
    python personaos_backend/api_manager.py set openai
    python personaos_backend/api_manager.py get openai
    python personaos_backend/api_manager.py list
    python personaos_backend/api_manager.py delete openai
    python personaos_backend/api_manager.py set openai --default
"""

import argparse
import os
import sys
import getpass
import stat
from pathlib import Path
from typing import Dict, Optional

try:
    from dotenv import load_dotenv, set_key, unset_key
except ImportError:
    print("Error: python-dotenv package is required. Install with: pip install python-dotenv")
    sys.exit(1)


class APIKeyManager:
    """Secure API key management for PersonaOS"""
    
    SUPPORTED_PROVIDERS = {
        'openai': 'OPENAI_API_KEY',
        'anthropic': 'ANTHROPIC_API_KEY', 
        'groq': 'GROQ_API_KEY',
        'custom_llm': 'CUSTOM_LLM_API_KEY'
    }
    
    def __init__(self, env_path: str = '.env'):
        self.env_path = Path(env_path)
        self.ensure_env_file()
        load_dotenv(self.env_path)
    
    def ensure_env_file(self):
        """Create .env file if it doesn't exist and set secure permissions"""
        if not self.env_path.exists():
            self.env_path.touch()
            print(f"Created {self.env_path}")
        
        # Set secure permissions on Unix systems
        if os.name != 'nt':  # Not Windows
            current_perms = oct(self.env_path.stat().st_mode)[-3:]
            if current_perms != '600':
                try:
                    self.env_path.chmod(stat.S_IRUSR | stat.S_IWUSR)
                    print(f"Set secure permissions (600) on {self.env_path}")
                except PermissionError:
                    print(f"Warning: Could not set secure permissions on {self.env_path}")
    
    def get_env_key(self, provider: str) -> str:
        """Get environment variable name for provider"""
        if provider not in self.SUPPORTED_PROVIDERS:
            raise ValueError(f"Unsupported provider: {provider}. Supported: {list(self.SUPPORTED_PROVIDERS.keys())}")
        return self.SUPPORTED_PROVIDERS[provider]
    
    def set_api_key(self, provider: str, set_default: bool = False) -> bool:
        """Securely set API key for provider"""
        env_key = self.get_env_key(provider)
        
        # Check if key already exists
        existing_key = os.getenv(env_key)
        if existing_key:
            confirm = input(f"API key for {provider} already exists. Overwrite? (yes/no): ").lower()
            if confirm not in ['yes', 'y']:
                print("Operation cancelled.")
                return False
        
        # Securely prompt for API key
        api_key = getpass.getpass(f"Enter API key for {provider}: ")
        if not api_key.strip():
            print("Error: API key cannot be empty.")
            return False
        
        # Set the API key
        set_key(self.env_path, env_key, api_key)
        print(f"✅ API key for {provider} set successfully.")
        
        # Set as default provider if requested
        if set_default:
            set_key(self.env_path, 'DEFAULT_LLM_PROVIDER', provider)
            print(f"✅ Set {provider} as default LLM provider.")
        
        return True
    
    def get_api_key(self, provider: str) -> Optional[str]:
        """Get API key for provider (returns None if not found)"""
        env_key = self.get_env_key(provider)
        return os.getenv(env_key)
    
    def list_api_keys(self) -> Dict[str, bool]:
        """List all configured API keys (returns provider -> has_key mapping)"""
        result = {}
        for provider, env_key in self.SUPPORTED_PROVIDERS.items():
            key = os.getenv(env_key)
            result[provider] = key is not None
            if key:
                # Show masked key for confirmation
                masked_key = self._mask_key(key)
                print(f"✅ {provider:<12} {masked_key}")
            else:
                print(f"❌ {provider:<12} Not configured")
        
        # Show default provider if set
        default_provider = os.getenv('DEFAULT_LLM_PROVIDER')
        if default_provider:
            print(f"\n🎯 Default provider: {default_provider}")
        
        return result
    
    def delete_api_key(self, provider: str) -> bool:
        """Delete API key for provider"""
        env_key = self.get_env_key(provider)
        
        if not os.getenv(env_key):
            print(f"No API key found for {provider}.")
            return False
        
        confirm = input(f"Delete API key for {provider}? (yes/no): ").lower()
        if confirm not in ['yes', 'y']:
            print("Operation cancelled.")
            return False
        
        unset_key(self.env_path, env_key)
        print(f"✅ API key for {provider} deleted successfully.")
        return True
    
    def _mask_key(self, key: str) -> str:
        """Mask API key for display (show first 2 and last 4 chars)"""
        if len(key) <= 8:
            return "*" * len(key)
        return f"{key[:2]}****{key[-4:]}"


def main():
    parser = argparse.ArgumentParser(
        description="PersonaOS API Key Manager - Securely manage API keys for LLM providers",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python personaos_backend/api_manager.py set openai
  python personaos_backend/api_manager.py set openai --default
  python personaos_backend/api_manager.py get openai
  python personaos_backend/api_manager.py list
  python personaos_backend/api_manager.py delete openai
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Set command
    set_parser = subparsers.add_parser('set', help='Set API key for provider')
    set_parser.add_argument('provider', choices=APIKeyManager.SUPPORTED_PROVIDERS.keys(),
                           help='LLM provider to configure')
    set_parser.add_argument('--default', action='store_true',
                           help='Set this provider as the default LLM provider')
    
    # Get command  
    get_parser = subparsers.add_parser('get', help='Get API key for provider')
    get_parser.add_argument('provider', choices=APIKeyManager.SUPPORTED_PROVIDERS.keys(),
                           help='LLM provider to query')
    
    # List command
    subparsers.add_parser('list', help='List all configured API keys')
    
    # Delete command
    delete_parser = subparsers.add_parser('delete', help='Delete API key for provider')
    delete_parser.add_argument('provider', choices=APIKeyManager.SUPPORTED_PROVIDERS.keys(),
                              help='LLM provider to delete')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        manager = APIKeyManager()
        
        if args.command == 'set':
            manager.set_api_key(args.provider, args.default)
        
        elif args.command == 'get':
            key = manager.get_api_key(args.provider)
            if key:
                print(f"✅ API key for {args.provider} is configured.")
            else:
                print(f"❌ No API key found for {args.provider}.")
                sys.exit(1)
        
        elif args.command == 'list':
            manager.list_api_keys()
        
        elif args.command == 'delete':
            manager.delete_api_key(args.provider)
    
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()