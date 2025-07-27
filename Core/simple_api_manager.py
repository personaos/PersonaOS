#!/usr/bin/env python3
"""
Simple API Key Manager for PersonaOS (No cryptography dependency)

A lightweight API key manager that stores keys in environment variables
and provides easy setup commands without encryption dependencies.
"""

import os
import json
import argparse
import getpass
import sys
from pathlib import Path
from dotenv import load_dotenv, set_key

# Supported providers and their key formats
SUPPORTED_PROVIDERS = {
    'openai': {
        'name': 'OpenAI',
        'env_var': 'OPENAI_API_KEY',
        'key_prefix': 'sk-',
        'example': 'sk-...'
    },
    'anthropic': {
        'name': 'Anthropic Claude',
        'env_var': 'ANTHROPIC_API_KEY', 
        'key_prefix': 'sk-ant-',
        'example': 'sk-ant-...'
    },
    'google': {
        'name': 'Google AI (Gemini)',
        'env_var': 'GOOGLE_API_KEY',
        'key_prefix': '',
        'example': 'AIza...'
    },
    'cohere': {
        'name': 'Cohere',
        'env_var': 'COHERE_API_KEY',
        'key_prefix': '',
        'example': 'your-cohere-key'
    },
    'picovoice': {
        'name': 'Picovoice (Wake Word)',
        'env_var': 'PICOVOICE_API_KEY',
        'key_prefix': '',
        'example': 'your-picovoice-key'
    },
    'elevenlabs': {
        'name': 'ElevenLabs (TTS)',
        'env_var': 'ELEVENLABS_API_KEY',
        'key_prefix': '',
        'example': 'your-elevenlabs-key'
    }
}

def get_env_file_path():
    """Get the path to the .env file."""
    return Path('.env')

def load_current_keys():
    """Load current API keys from .env file."""
    load_dotenv()
    keys = {}
    
    for provider, config in SUPPORTED_PROVIDERS.items():
        env_var = config['env_var']
        value = os.getenv(env_var)
        if value:
            keys[provider] = {
                'provider': provider,
                'env_var': env_var,
                'value': value[:10] + '...' if len(value) > 10 else value,
                'full_value': value,
                'has_key': True
            }
        else:
            keys[provider] = {
                'provider': provider,
                'env_var': env_var,
                'value': None,
                'full_value': None,
                'has_key': False
            }
    
    return keys

def validate_key_format(provider, api_key):
    """Basic validation of API key format."""
    if not api_key or not api_key.strip():
        return False, "API key cannot be empty"
    
    config = SUPPORTED_PROVIDERS.get(provider)
    if not config:
        return False, f"Unsupported provider: {provider}"
    
    key_prefix = config['key_prefix']
    if key_prefix and not api_key.startswith(key_prefix):
        return False, f"Key should start with '{key_prefix}'"
    
    if len(api_key) < 10:
        return False, "Key appears too short"
    
    return True, "Key format looks valid"

def set_api_key(provider, api_key, env_file=None):
    """Set an API key in the .env file."""
    if env_file is None:
        env_file = get_env_file_path()
    
    # Validate provider
    if provider not in SUPPORTED_PROVIDERS:
        return False, f"Unsupported provider: {provider}"
    
    # Validate key format
    is_valid, message = validate_key_format(provider, api_key)
    if not is_valid:
        return False, message
    
    # Set the key in .env file
    config = SUPPORTED_PROVIDERS[provider]
    env_var = config['env_var']
    
    try:
        set_key(env_file, env_var, api_key)
        return True, f"Successfully set {env_var}"
    except Exception as e:
        return False, f"Failed to set key: {e}"

def print_providers():
    """Print supported providers."""
    print("\n[*] Supported Providers:")
    print("-" * 50)
    
    for provider_id, config in SUPPORTED_PROVIDERS.items():
        print(f"* {provider_id:<12} - {config['name']}")
        print(f"  {'Environment:':<12} {config['env_var']}")
        print(f"  {'Example:':<12} {config['example']}")
        print()

def print_current_keys():
    """Print currently configured keys."""
    keys = load_current_keys()
    
    configured_keys = [k for k in keys.values() if k['has_key']]
    
    if not configured_keys:
        print("[INFO] No API keys currently configured")
        return
    
    print(f"\n[*] Configured API Keys ({len(configured_keys)} found):")
    print("-" * 60)
    
    for key_info in keys.values():
        if key_info['has_key']:
            status = "[SET]"
            print(f"Provider: {key_info['provider']:<12} | {status} | {key_info['env_var']}")
            print(f"  Value: {key_info['value']}")
            print()

def add_key_interactive(provider):
    """Add a key interactively."""
    if provider not in SUPPORTED_PROVIDERS:
        print(f"[ERROR] Unsupported provider: {provider}")
        print("Run 'python core/simple_api_manager.py providers' to see supported providers")
        return False
    
    config = SUPPORTED_PROVIDERS[provider]
    provider_name = config['name']
    
    print(f"\nAdding API key for {provider_name}")
    print(f"Environment variable: {config['env_var']}")
    print(f"Expected format: {config['example']}")
    print()
    
    # Get API key securely
    api_key = getpass.getpass(f"Enter {provider_name} API key: ")
    
    if not api_key.strip():
        print("[ERROR] API key cannot be empty")
        return False
    
    # Set the key
    success, message = set_api_key(provider, api_key.strip())
    
    if success:
        print(f"[SUCCESS] {message}")
        print(f"[INFO] Key added to .env file")
        return True
    else:
        print(f"[ERROR] {message}")
        return False

def test_key(provider):
    """Test if a key is configured."""
    keys = load_current_keys()
    
    if provider not in keys or not keys[provider]['has_key']:
        print(f"[ERROR] No API key found for {provider}")
        return False
    
    key_info = keys[provider]
    api_key = key_info['full_value']
    
    print(f"[INFO] Testing {provider} API key...")
    print(f"   Key found: [YES]")
    
    # Validate format
    is_valid, message = validate_key_format(provider, api_key)
    print(f"   Key format: {'[VALID]' if is_valid else '[INVALID]'} - {message}")
    
    # Length check
    print(f"   Key length: {len(api_key)} characters")
    
    return is_valid

def remove_key(provider):
    """Remove a key from .env file."""
    if provider not in SUPPORTED_PROVIDERS:
        print(f"[ERROR] Unsupported provider: {provider}")
        return False
    
    config = SUPPORTED_PROVIDERS[provider]
    env_var = config['env_var']
    env_file = get_env_file_path()
    
    if not env_file.exists():
        print("[INFO] No .env file found")
        return False
    
    # Read current .env content
    try:
        with open(env_file, 'r') as f:
            lines = f.readlines()
        
        # Remove the line with this env var
        new_lines = []
        removed = False
        
        for line in lines:
            if line.strip().startswith(f"{env_var}="):
                removed = True
                continue
            new_lines.append(line)
        
        if removed:
            with open(env_file, 'w') as f:
                f.writelines(new_lines)
            print(f"[SUCCESS] Removed {env_var} from .env file")
            return True
        else:
            print(f"[INFO] {env_var} not found in .env file")
            return False
            
    except Exception as e:
        print(f"[ERROR] Failed to remove key: {e}")
        return False

def setup_env_file():
    """Create .env file from template if it doesn't exist."""
    env_file = get_env_file_path()
    template_file = Path('.env.template')
    
    if env_file.exists():
        print("[INFO] .env file already exists")
        return True
    
    if not template_file.exists():
        print("[WARNING] .env.template not found, creating basic .env file")
        
        # Create basic .env file
        with open(env_file, 'w') as f:
            f.write("# PersonaOS API Keys\n")
            f.write("# Add your API keys below\n\n")
            
            for provider, config in SUPPORTED_PROVIDERS.items():
                f.write(f"# {config['name']}\n")
                f.write(f"{config['env_var']}=\n\n")
        
        print(f"[SUCCESS] Created .env file with placeholders")
        return True
    
    # Copy from template
    try:
        import shutil
        shutil.copy(template_file, env_file)
        print("[SUCCESS] Created .env file from template")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to create .env file: {e}")
        return False

def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Simple PersonaOS API Key Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Show supported providers
  python core/simple_api_manager.py providers

  # Add an API key
  python core/simple_api_manager.py add openai

  # List current keys  
  python core/simple_api_manager.py list

  # Test a key
  python core/simple_api_manager.py test openai

  # Remove a key
  python core/simple_api_manager.py remove openai

  # Setup .env file
  python core/simple_api_manager.py setup
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Providers command
    subparsers.add_parser('providers', help='Show supported providers')
    
    # List command
    subparsers.add_parser('list', help='List configured API keys')
    
    # Add command
    add_parser = subparsers.add_parser('add', help='Add an API key')
    add_parser.add_argument('provider', help='Provider name (e.g., openai, anthropic)')
    
    # Test command
    test_parser = subparsers.add_parser('test', help='Test an API key')
    test_parser.add_argument('provider', help='Provider name to test')
    
    # Remove command
    remove_parser = subparsers.add_parser('remove', help='Remove an API key')
    remove_parser.add_argument('provider', help='Provider name to remove')
    
    # Setup command
    subparsers.add_parser('setup', help='Setup .env file')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    print("=" * 60)
    print("PersonaOS Simple API Key Manager")
    print("Easy API credential management without encryption")
    print("=" * 60)
    
    try:
        if args.command == 'providers':
            print_providers()
        elif args.command == 'list':
            print_current_keys()
        elif args.command == 'add':
            add_key_interactive(args.provider)
        elif args.command == 'test':
            test_key(args.provider)
        elif args.command == 'remove':
            remove_key(args.provider)
        elif args.command == 'setup':
            setup_env_file()
        else:
            print(f"[ERROR] Unknown command: {args.command}")
            parser.print_help()
    
    except KeyboardInterrupt:
        print("\n\n[INFO] Operation cancelled by user")
    except Exception as e:
        print(f"\n[ERROR] {e}")

if __name__ == "__main__":
    main()