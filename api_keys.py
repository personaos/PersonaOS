#!/usr/bin/env python3
"""
Direct API Key Manager for PersonaOS

Simple script that directly manages API keys without complex imports.
Run from PersonaOS root directory.
"""

import os
import sys
import argparse
import getpass
import json
from pathlib import Path

# Add core to path
sys.path.insert(0, 'core')

# Direct import
try:
    import api_manager
    SECURE_AVAILABLE = True
    print("[INFO] Using secure encrypted API key storage")
except ImportError as e:
    print(f"[WARNING] Secure manager not available: {e}")
    print("[INFO] Using simple .env file storage")
    SECURE_AVAILABLE = False

def main():
    parser = argparse.ArgumentParser(description="PersonaOS API Key Manager")
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Add command
    add_parser = subparsers.add_parser('add', help='Add API key')
    add_parser.add_argument('provider', help='Provider (openai, anthropic, google, etc.)')
    
    # List command
    subparsers.add_parser('list', help='List API keys')
    
    # Providers command
    subparsers.add_parser('providers', help='Show supported providers')
    
    # Test command  
    test_parser = subparsers.add_parser('test', help='Test API key')
    test_parser.add_argument('provider', help='Provider to test')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    print("=" * 60)
    print("PersonaOS API Key Manager")
    print("=" * 60)
    
    if SECURE_AVAILABLE:
        # Use secure manager
        manager = api_manager.get_api_manager()
        
        if args.command == 'providers':
            print("\n[*] Supported Providers:")
            for provider, config in manager.SUPPORTED_PROVIDERS.items():
                print(f"  {provider:<12} - {config['name']}")
        
        elif args.command == 'add':
            provider = args.provider
            if provider not in manager.SUPPORTED_PROVIDERS:
                print(f"[ERROR] Unsupported provider: {provider}")
                return
            
            key = getpass.getpass(f"Enter {provider} API key: ")
            success = manager.add_key(provider, key)
            
            if success:
                print(f"[SUCCESS] Added {provider} API key (encrypted)")
            else:
                print(f"[ERROR] Failed to add {provider} API key")
        
        elif args.command == 'list':
            keys = manager.list_keys()
            if keys:
                print(f"\n[*] Configured Keys ({len(keys)}):")
                for key in keys:
                    status = "[ACTIVE]" if key['is_active'] else "[INACTIVE]"
                    print(f"  {key['provider']:<12} {status}")
            else:
                print("[INFO] No API keys configured")
        
        elif args.command == 'test':
            provider = args.provider
            key = manager.get_key(provider)
            if key:
                print(f"[SUCCESS] {provider} API key found and accessible")
            else:
                print(f"[ERROR] No {provider} API key found")
    
    else:
        # Use simple .env approach
        from dotenv import load_dotenv, set_key
        load_dotenv()
        
        providers = {
            'openai': 'OPENAI_API_KEY',
            'anthropic': 'ANTHROPIC_API_KEY', 
            'google': 'GOOGLE_API_KEY',
            'cohere': 'COHERE_API_KEY',
            'picovoice': 'PICOVOICE_API_KEY',
            'elevenlabs': 'ELEVENLABS_API_KEY'
        }
        
        if args.command == 'providers':
            print("\n[*] Supported Providers:")
            for provider in providers:
                print(f"  {provider}")
        
        elif args.command == 'add':
            provider = args.provider
            if provider not in providers:
                print(f"[ERROR] Unsupported provider: {provider}")
                return
            
            key = getpass.getpass(f"Enter {provider} API key: ")
            env_var = providers[provider]
            set_key('.env', env_var, key)
            print(f"[SUCCESS] Added {provider} API key to .env file")
        
        elif args.command == 'list':
            found_keys = []
            for provider, env_var in providers.items():
                if os.getenv(env_var):
                    found_keys.append(provider)
            
            if found_keys:
                print(f"\n[*] Configured Keys ({len(found_keys)}):")
                for provider in found_keys:
                    print(f"  {provider}")
            else:
                print("[INFO] No API keys configured")
        
        elif args.command == 'test':
            provider = args.provider
            if provider in providers:
                env_var = providers[provider]
                if os.getenv(env_var):
                    print(f"[SUCCESS] {provider} API key found")
                else:
                    print(f"[ERROR] No {provider} API key found")
            else:
                print(f"[ERROR] Unsupported provider: {provider}")

if __name__ == "__main__":
    main()