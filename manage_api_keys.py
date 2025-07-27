#!/usr/bin/env python3
"""
API Key Manager Wrapper for PersonaOS

Simple wrapper script to manage API keys without import issues.
Run this from the PersonaOS root directory.
"""

import os
import sys
import subprocess
from pathlib import Path

def main():
    """Main wrapper function."""
    # Ensure we're in the right directory
    root_dir = Path(__file__).parent
    os.chdir(root_dir)
    
    # Add core to Python path
    core_dir = root_dir / 'core'
    sys.path.insert(0, str(core_dir))
    sys.path.insert(0, str(root_dir))
    
    # Check if cryptography is available
    try:
        import cryptography
        print("[INFO] Using secure encrypted API key manager")
        use_secure = True
    except ImportError:
        print("[WARNING] Cryptography not available, using simple manager")
        print("Install with: pip install cryptography")
        use_secure = False
    
    # Import the appropriate manager
    if use_secure:
        try:
            # Import and run secure manager
            sys.path.insert(0, str(core_dir))
            from api_manager_cli import main as cli_main
            cli_main()
            return
        except Exception as e:
            print(f"[ERROR] Secure manager failed: {e}")
            print("[INFO] Falling back to simple manager")
            use_secure = False
    
    if not use_secure:
        # Import and run simple manager
        try:
            from core.simple_api_manager import main as simple_main
            simple_main()
        except Exception as e:
            print(f"[ERROR] Both managers failed: {e}")
            print("\nTroubleshooting:")
            print("1. Make sure you're in the PersonaOS root directory")
            print("2. Install dependencies: pip install -r requirements.txt")
            print("3. Check that core/api_manager.py exists")
            sys.exit(1)

if __name__ == "__main__":
    main()