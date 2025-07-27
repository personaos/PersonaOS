#!/usr/bin/env python3
"""
API Key Manager CLI for PersonaOS

Command-line interface for managing API keys securely.
Provides easy setup, validation, and management of API credentials.
"""

import argparse
import sys
import getpass
from typing import Optional
from pathlib import Path

# Add current and parent directories to path for imports
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
sys.path.insert(0, str(parent_dir))
sys.path.insert(0, str(current_dir))

try:
    from api_manager import APIKeyManager, get_api_manager
except ImportError:
    try:
        from core.api_manager import APIKeyManager, get_api_manager
    except ImportError:
        print("[ERROR] Could not import api_manager module")
        print("Make sure you're running from the PersonaOS root directory")
        sys.exit(1)

def setup_argument_parser():
    """Set up command line argument parser."""
    parser = argparse.ArgumentParser(
        description="PersonaOS API Key Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Add an API key interactively
  python core/api_manager_cli.py add openai

  # Add an API key with name
  python core/api_manager_cli.py add openai --name "primary_key"

  # List all keys
  python core/api_manager_cli.py list

  # Validate a key
  python core/api_manager_cli.py validate openai

  # Migrate from environment variables
  python core/api_manager_cli.py migrate

  # Show supported providers
  python core/api_manager_cli.py providers
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Add key command
    add_parser = subparsers.add_parser('add', help='Add a new API key')
    add_parser.add_argument('provider', help='Provider name (e.g., openai, anthropic)')
    add_parser.add_argument('--name', help='Custom name for the key')
    add_parser.add_argument('--key', help='API key (if not provided, will prompt securely)')
    add_parser.add_argument('--rate-limit', type=int, help='Rate limit (requests per minute)')
    add_parser.add_argument('--quota', type=int, help='Monthly quota')
    
    # List keys command
    list_parser = subparsers.add_parser('list', help='List configured API keys')
    list_parser.add_argument('--provider', help='Filter by provider')
    
    # Validate key command
    validate_parser = subparsers.add_parser('validate', help='Validate an API key')
    validate_parser.add_argument('provider', help='Provider name')
    validate_parser.add_argument('--name', help='Specific key name to validate')
    
    # Remove key command
    remove_parser = subparsers.add_parser('remove', help='Remove an API key')
    remove_parser.add_argument('key_id', help='Key ID to remove')
    
    # Deactivate key command
    deactivate_parser = subparsers.add_parser('deactivate', help='Deactivate an API key')
    deactivate_parser.add_argument('key_id', help='Key ID to deactivate')
    
    # Migrate command
    migrate_parser = subparsers.add_parser('migrate', help='Migrate keys from environment variables')
    
    # Providers command
    providers_parser = subparsers.add_parser('providers', help='Show supported providers')
    
    # Test command
    test_parser = subparsers.add_parser('test', help='Test API key functionality')
    test_parser.add_argument('provider', help='Provider to test')
    test_parser.add_argument('--name', help='Specific key name to test')
    
    return parser

def print_header():
    """Print CLI header."""
    print("=" * 60)
    print("PersonaOS API Key Manager")
    print("Secure API credential management for local AI assistant")
    print("=" * 60)

def print_providers():
    """Print supported providers."""
    manager = get_api_manager()
    
    print("\n[*] Supported Providers:")
    print("-" * 40)
    
    for provider_id, config in manager.SUPPORTED_PROVIDERS.items():
        print(f"* {provider_id:<12} - {config['name']}")
        print(f"  {'Model:':<12} {config['default_model']}")
        if config['test_endpoint']:
            print(f"  {'Validation:':<12} [YES] Available")
        else:
            print(f"  {'Validation:':<12} [NO] Not available")
        print()

def add_key_command(args):
    """Handle add key command."""
    manager = get_api_manager()
    
    # Validate provider
    if args.provider not in manager.SUPPORTED_PROVIDERS:
        print(f"[ERROR] Unsupported provider '{args.provider}'")
        print("Run 'python core/api_manager_cli.py providers' to see supported providers")
        return False
    
    # Get API key
    if args.key:
        api_key = args.key
    else:
        provider_name = manager.SUPPORTED_PROVIDERS[args.provider]['name']
        api_key = getpass.getpass(f"Enter {provider_name} API key: ")
    
    if not api_key.strip():
        print("[ERROR] API key cannot be empty")
        return False
    
    # Add the key
    success = manager.add_key(
        provider=args.provider,
        api_key=api_key.strip(),
        key_name=args.name,
        rate_limit=args.rate_limit,
        monthly_quota=args.quota
    )
    
    if success:
        print(f"[SUCCESS] Successfully added API key for {args.provider}")
        if args.name:
            print(f"   Key name: {args.name}")
    else:
        print(f"[ERROR] Failed to add API key for {args.provider}")
        print("   Check that the key format is valid")
    
    return success

def list_keys_command(args):
    """Handle list keys command."""
    manager = get_api_manager()
    keys = manager.list_keys(args.provider)
    
    if not keys:
        if args.provider:
            print(f"[INFO] No API keys found for provider: {args.provider}")
        else:
            print("[INFO] No API keys configured")
        return
    
    print(f"\n[*] API Keys ({len(keys)} found):")
    print("-" * 80)
    
    for key_info in keys:
        status = "[ACTIVE]" if key_info['is_active'] else "[INACTIVE]"
        print(f"Provider: {key_info['provider']:<12} | Name: {key_info['key_name']:<20} | {status}")
        print(f"  ID: {key_info['key_id']}")
        print(f"  Created: {key_info['created_at']}")
        print(f"  Used: {key_info['usage_count']} times")
        if key_info['last_used']:
            print(f"  Last used: {key_info['last_used']}")
        if key_info['rate_limit']:
            print(f"  Rate limit: {key_info['rate_limit']}/min")
        if key_info['monthly_quota']:
            print(f"  Monthly quota: {key_info['monthly_quota']}")
        print()

def validate_key_command(args):
    """Handle validate key command."""
    manager = get_api_manager()
    
    print(f"[INFO] Validating {args.provider} API key...")
    
    is_valid, message = manager.validate_key(args.provider, args.name)
    
    if is_valid:
        print(f"[SUCCESS] API key validation: {message}")
    else:
        print(f"[ERROR] API key validation failed: {message}")
    
    return is_valid

def remove_key_command(args):
    """Handle remove key command."""
    manager = get_api_manager()
    
    # Confirm deletion
    response = input(f"Are you sure you want to remove key {args.key_id}? (y/N): ")
    if response.lower() != 'y':
        print("Operation cancelled")
        return False
    
    success = manager.remove_key(args.key_id)
    
    if success:
        print(f"[SUCCESS] Successfully removed key {args.key_id}")
    else:
        print(f"[ERROR] Key {args.key_id} not found")
    
    return success

def deactivate_key_command(args):
    """Handle deactivate key command."""
    manager = get_api_manager()
    
    success = manager.deactivate_key(args.key_id)
    
    if success:
        print(f"[SUCCESS] Successfully deactivated key {args.key_id}")
    else:
        print(f"[ERROR] Key {args.key_id} not found")
    
    return success

def migrate_command(args):
    """Handle migrate command."""
    manager = get_api_manager()
    
    print("[INFO] Migrating API keys from environment variables...")
    results = manager.migrate_from_env()
    
    if not results:
        print("[INFO] No API keys found in environment variables")
        return
    
    print(f"\n[SUCCESS] Migration completed:")
    for env_var, success in results.items():
        status = "[SUCCESS]" if success else "[FAILED]"
        print(f"  {env_var}: {status}")
    
    successful_migrations = sum(results.values())
    print(f"\n[INFO] {successful_migrations}/{len(results)} keys migrated successfully")
    
    if successful_migrations > 0:
        print("\n[WARNING] Consider removing API keys from your .env file for security")

def test_key_command(args):
    """Handle test key command."""
    manager = get_api_manager()
    
    # Get the key
    api_key = manager.get_key(args.provider, args.name)
    if not api_key:
        print(f"[ERROR] No API key found for {args.provider}")
        return False
    
    print(f"[INFO] Testing {args.provider} API key...")
    print(f"   Key found: [YES]")
    print(f"   Key format: {'[VALID]' if manager._validate_key_format(args.provider, api_key) else '[INVALID]'}")
    
    # Validate through API if possible
    is_valid, message = manager.validate_key(args.provider, args.name)
    print(f"   API validation: {'[SUCCESS]' if is_valid else '[ERROR]'} {message}")
    
    return is_valid

def main():
    """Main CLI entry point."""
    parser = setup_argument_parser()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    print_header()
    
    try:
        if args.command == 'add':
            add_key_command(args)
        elif args.command == 'list':
            list_keys_command(args)
        elif args.command == 'validate':
            validate_key_command(args)
        elif args.command == 'remove':
            remove_key_command(args)
        elif args.command == 'deactivate':
            deactivate_key_command(args)
        elif args.command == 'migrate':
            migrate_command(args)
        elif args.command == 'providers':
            print_providers()
        elif args.command == 'test':
            test_key_command(args)
        else:
            print(f"[ERROR] Unknown command: {args.command}")
            parser.print_help()
    
    except KeyboardInterrupt:
        print("\n\n[INFO] Operation cancelled by user")
    except Exception as e:
        print(f"\n[ERROR] {e}")
        if args.command in ['add', 'validate', 'test']:
            print("   Make sure your API key is valid and you have internet connectivity")

if __name__ == "__main__":
    main()