#!/usr/bin/env python3
"""
PersonaOS Automated Installer
Comprehensive installation script that handles all prerequisites and setup
"""

import os
import sys
import subprocess
import platform
import urllib.request
import shutil
import json
from pathlib import Path

# Color codes for console output
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_status(message, status="info"):
    """Print colored status messages"""
    if status == "success":
        print(f"{Colors.GREEN}✅ {message}{Colors.END}")
    elif status == "warning":
        print(f"{Colors.YELLOW}⚠️  {message}{Colors.END}")
    elif status == "error":
        print(f"{Colors.RED}❌ {message}{Colors.END}")
    elif status == "info":
        print(f"{Colors.BLUE}ℹ️  {message}{Colors.END}")
    else:
        print(f"🔧 {message}")

def print_header():
    """Print welcome header"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}")
    print("🤖 PersonaOS Automated Installer v1.0")
    print("Setting up your AI assistant environment...")
    print(f"{'='*60}{Colors.END}\n")

def check_python():
    """Check if Python 3.7+ is installed"""
    print_status("Checking Python installation...")
    
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 7):
        print_status(f"Python {version.major}.{version.minor} detected. PersonaOS requires Python 3.7+", "error")
        print_status("Please install Python 3.7+ from https://python.org", "error")
        return False
    
    print_status(f"Python {version.major}.{version.minor}.{version.micro} ✓", "success")
    return True

def check_git():
    """Check if Git is installed"""
    print_status("Checking Git installation...")
    
    try:
        result = subprocess.run(["git", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            print_status(f"Git {result.stdout.strip().split()[2]} ✓", "success")
            return True
    except FileNotFoundError:
        pass
    
    print_status("Git not found", "warning")
    print_status("Git is recommended for updates. Install from https://git-scm.com", "info")
    return False

def check_node():
    """Check if Node.js is installed (required for Web UI)"""
    print_status("Checking Node.js installation...")
    
    try:
        result = subprocess.run(["node", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            version = result.stdout.strip()
            print_status(f"Node.js {version} ✓", "success")
            return True
    except FileNotFoundError:
        pass
    
    print_status("Node.js not found", "warning")
    print_status("Node.js is required for Web UI. Install from https://nodejs.org", "info")
    return False

def check_ollama():
    """Check if Ollama is installed"""
    print_status("Checking Ollama installation...")
    
    try:
        result = subprocess.run(["ollama", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            print_status("Ollama ✓", "success")
            return True
    except FileNotFoundError:
        pass
    
    print_status("Ollama not found", "warning")
    return False

def install_ollama():
    """Install Ollama based on the operating system"""
    print_status("Installing Ollama...")
    
    system = platform.system().lower()
    
    if system == "windows":
        print_status("Please install Ollama manually from https://ollama.com/download", "info")
        print_status("1. Download the Windows installer", "info")
        print_status("2. Run the installer as administrator", "info")
        print_status("3. Restart this installer after Ollama is installed", "info")
        return False
    
    elif system == "darwin":  # macOS
        try:
            # Download and install Ollama for macOS
            print_status("Downloading Ollama for macOS...")
            subprocess.run(["curl", "-fsSL", "https://ollama.com/install.sh"], 
                         shell=True, check=True)
            print_status("Ollama installed successfully", "success")
            return True
        except subprocess.CalledProcessError:
            print_status("Failed to install Ollama automatically", "error")
            print_status("Please install manually from https://ollama.com/download", "info")
            return False
    
    elif system == "linux":
        try:
            # Install Ollama for Linux
            print_status("Installing Ollama for Linux...")
            result = subprocess.run([
                "curl", "-fsSL", "https://ollama.com/install.sh"
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                subprocess.run(["sh"], input=result.stdout, text=True, check=True)
                print_status("Ollama installed successfully", "success")
                return True
            else:
                raise subprocess.CalledProcessError(result.returncode, "curl")
        except subprocess.CalledProcessError:
            print_status("Failed to install Ollama automatically", "error")
            print_status("Please install manually: curl -fsSL https://ollama.com/install.sh | sh", "info")
            return False
    
    else:
        print_status(f"Unsupported operating system: {system}", "error")
        print_status("Please install Ollama manually from https://ollama.com/download", "info")
        return False

def install_python_dependencies():
    """Install Python dependencies from requirements.txt"""
    print_status("Installing Python dependencies...")
    
    req_file = Path("requirements.txt")
    if not req_file.exists():
        print_status("requirements.txt not found", "error")
        return False
    
    try:
        subprocess.run([
            sys.executable, "-m", "pip", "install", "-r", "requirements.txt"
        ], check=True)
        print_status("Python dependencies installed successfully", "success")
        return True
    except subprocess.CalledProcessError as e:
        print_status(f"Failed to install Python dependencies: {e}", "error")
        return False

def install_node_dependencies():
    """Install Node.js dependencies for the Web UI"""
    print_status("Installing Node.js dependencies for Web UI...")
    
    frontend_dir = Path("persona_web_ui/frontend")
    if not frontend_dir.exists():
        print_status("Frontend directory not found", "warning")
        return False
    
    try:
        subprocess.run(["npm", "install"], cwd=frontend_dir, check=True)
        print_status("Node.js dependencies installed successfully", "success")
        return True
    except subprocess.CalledProcessError as e:
        print_status(f"Failed to install Node.js dependencies: {e}", "error")
        return False
    except FileNotFoundError:
        print_status("npm not found. Please install Node.js first", "error")
        return False

def download_default_model():
    """Download a default Ollama model"""
    print_status("Setting up default AI model...")
    
    try:
        # Check if any models are already installed
        result = subprocess.run(["ollama", "list"], capture_output=True, text=True)
        if "openhermes" in result.stdout or len(result.stdout.strip().split('\n')) > 1:
            print_status("AI model already available", "success")
            return True
        
        print_status("Downloading default AI model (openhermes)...")
        print_status("This may take a few minutes depending on your internet connection...", "info")
        
        subprocess.run(["ollama", "pull", "openhermes"], check=True)
        print_status("Default AI model downloaded successfully", "success")
        return True
        
    except subprocess.CalledProcessError as e:
        print_status(f"Failed to download AI model: {e}", "error")
        print_status("You can download it later with: ollama pull openhermes", "info")
        return False
    except FileNotFoundError:
        print_status("Ollama not found. Please install Ollama first", "error")
        return False

def run_initial_setup():
    """Run the initial PersonaOS configuration"""
    print_status("Running initial PersonaOS configuration...")
    
    try:
        # Import and run the existing setup
        from setup_env import run_env_setup, is_env_complete
        
        if not is_env_complete():
            print_status("Starting configuration wizard...", "info")
            run_env_setup()
        else:
            print_status("Configuration already complete", "success")
        
        return True
    except ImportError as e:
        print_status(f"Failed to import setup module: {e}", "error")
        return False
    except Exception as e:
        print_status(f"Configuration failed: {e}", "error")
        return False

def create_desktop_shortcuts():
    """Create desktop shortcuts for easy access"""
    print_status("Creating desktop shortcuts...")
    
    try:
        desktop = Path.home() / "Desktop"
        if not desktop.exists():
            print_status("Desktop directory not found, skipping shortcuts", "warning")
            return False
        
        # Create PersonaOS CLI shortcut
        cli_script = f"""@echo off
cd /d "{Path.cwd()}"
python core/main.py
pause"""
        
        cli_shortcut = desktop / "PersonaOS CLI.bat"
        with open(cli_shortcut, "w") as f:
            f.write(cli_script)
        
        # Create PersonaOS Web UI shortcut
        webui_script = f"""@echo off
cd /d "{Path.cwd()}"
start_webui.bat"""
        
        webui_shortcut = desktop / "PersonaOS Web UI.bat"
        with open(webui_shortcut, "w") as f:
            f.write(webui_script)
        
        print_status("Desktop shortcuts created", "success")
        return True
        
    except Exception as e:
        print_status(f"Failed to create shortcuts: {e}", "warning")
        return False

def main():
    """Main installation process"""
    print_header()
    
    # Parse command line arguments
    manual_mode = "--manual" in sys.argv
    skip_ollama = "--skip-ollama" in sys.argv
    skip_model = "--skip-model" in sys.argv
    
    if manual_mode:
        print_status("Manual mode enabled - skipping automatic installations", "info")
    
    # Step 1: Check prerequisites
    print_status("Step 1: Checking system prerequisites...", "info")
    
    python_ok = check_python()
    if not python_ok:
        sys.exit(1)
    
    git_ok = check_git()
    node_ok = check_node()
    ollama_ok = check_ollama()
    
    # Step 2: Install missing components
    if not manual_mode:
        print_status("\nStep 2: Installing missing components...", "info")
        
        if not ollama_ok and not skip_ollama:
            ollama_ok = install_ollama()
            if not ollama_ok:
                print_status("Ollama installation required. Please install manually and re-run this script.", "error")
                sys.exit(1)
        
        # Install Python dependencies
        if not install_python_dependencies():
            print_status("Failed to install Python dependencies", "error")
            sys.exit(1)
        
        # Install Node dependencies if Node.js is available
        if node_ok:
            install_node_dependencies()
        else:
            print_status("Skipping Web UI setup - Node.js not available", "warning")
    
    # Step 3: Download default model
    if not manual_mode and not skip_model and ollama_ok:
        print_status("\nStep 3: Setting up AI model...", "info")
        download_default_model()
    
    # Step 4: Run initial configuration
    print_status("\nStep 4: Running initial configuration...", "info")
    if not run_initial_setup():
        print_status("Initial configuration failed", "error")
        sys.exit(1)
    
    # Step 5: Create shortcuts
    if not manual_mode and platform.system().lower() == "windows":
        print_status("\nStep 5: Creating desktop shortcuts...", "info")
        create_desktop_shortcuts()
    
    # Installation complete
    print_status("\n" + "="*60, "success")
    print_status("🎉 PersonaOS installation completed successfully!", "success")
    print_status("="*60, "success")
    
    print_status("\nQuick Start Options:", "info")
    print_status("• Run CLI version: python core/main.py", "info")
    if node_ok:
        print_status("• Run Web UI: python start.py", "info")
        print_status("• Or use: start_webui.bat", "info")
    
    if not node_ok:
        print_status("\n💡 To enable Web UI, install Node.js and run: npm install in persona_web_ui/frontend/", "info")

if __name__ == "__main__":
    main()