#!/usr/bin/env python3
"""
PersonaOS Universal Launcher
Smart launcher that detects system state and provides multiple interface options
"""

import os
import sys
import subprocess
import time
import threading
from pathlib import Path
from dotenv import load_dotenv

# Import enhanced error handling
try:
    from error_handler import ErrorContext, handle_exception, setup_global_exception_handler
    ERROR_HANDLING_AVAILABLE = True
except ImportError:
    ERROR_HANDLING_AVAILABLE = False

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
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*50}")
    print("🤖 PersonaOS Universal Launcher")
    print(f"{'='*50}{Colors.END}\n")

def check_system_health():
    """Perform comprehensive system health check"""
    print_status("Performing system health check...")
    issues = []
    
    # Check if .env file exists and is complete
    env_file = Path(".env")
    if not env_file.exists():
        issues.append("Configuration file (.env) missing")
    else:
        load_dotenv()
        required_vars = ['LLM_PROVIDER', 'WEB_UI_PORT', 'FRONTEND_PORT']
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            issues.append(f"Missing environment variables: {', '.join(missing_vars)}")
    
    # Check if Ollama is available
    try:
        result = subprocess.run(["ollama", "--version"], capture_output=True, text=True)
        if result.returncode != 0:
            issues.append("Ollama not responding")
    except FileNotFoundError:
        issues.append("Ollama not installed")
    
    # Check if Python dependencies are installed
    try:
        import requests
        from cryptography.fernet import Fernet
    except ImportError as e:
        issues.append(f"Missing Python dependencies: {str(e).split()[-1]}")
    
    # Check if Node.js is available for Web UI
    node_available = False
    try:
        result = subprocess.run(["node", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            node_available = True
    except FileNotFoundError:
        pass
    
    # Check if frontend dependencies are installed
    frontend_dir = Path("persona_web_ui/frontend")
    if node_available and frontend_dir.exists():
        node_modules = frontend_dir / "node_modules"
        if not node_modules.exists():
            issues.append("Web UI dependencies not installed (run: npm install in frontend directory)")
    
    return issues, node_available

def run_health_repair():
    """Attempt to automatically repair common issues"""
    print_status("Attempting to repair system issues...")
    
    # Run setup if .env is missing
    env_file = Path(".env")
    if not env_file.exists():
        print_status("Running configuration setup...")
        try:
            from setup_env import run_env_setup
            run_env_setup()
            print_status("Configuration completed", "success")
        except Exception as e:
            print_status(f"Configuration failed: {e}", "error")
            return False
    
    # Install Python dependencies if missing
    try:
        import requests
    except ImportError:
        print_status("Installing missing Python dependencies...")
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], check=True)
            print_status("Python dependencies installed", "success")
        except subprocess.CalledProcessError:
            print_status("Failed to install Python dependencies", "error")
            return False
    
    return True

def find_free_port(start_port, max_attempts=10):
    """Find a free port starting from start_port"""
    import socket
    
    for i in range(max_attempts):
        port = start_port + i
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('localhost', port))
                return port
        except OSError:
            continue
    return None

def start_cli_mode():
    """Start PersonaOS in CLI mode"""
    print_status("Starting PersonaOS CLI interface...")
    
    try:
        # Use existing core/main.py
        subprocess.run([sys.executable, "core/main.py"])
    except KeyboardInterrupt:
        print_status("\nPersonaOS CLI stopped by user", "info")
    except FileNotFoundError:
        print_status("PersonaOS core not found", "error")
        return False
    
    return True

def start_web_ui():
    """Start PersonaOS Web UI (backend + frontend)"""
    print_status("Starting PersonaOS Web UI...")
    
    # Load environment variables
    load_dotenv()
    backend_port = int(os.getenv('WEB_UI_PORT', '8000'))
    frontend_port = int(os.getenv('FRONTEND_PORT', '5173'))
    
    # Find free ports if needed
    free_backend_port = find_free_port(backend_port)
    free_frontend_port = find_free_port(frontend_port)
    
    if not free_backend_port:
        print_status(f"Cannot find free port for backend (tried {backend_port}-{backend_port+9})", "error")
        return False
    
    if not free_frontend_port:
        print_status(f"Cannot find free port for frontend (tried {frontend_port}-{frontend_port+9})", "error")
        return False
    
    # Update environment if ports changed
    if free_backend_port != backend_port:
        print_status(f"Using backend port {free_backend_port} (configured: {backend_port})", "warning")
    if free_frontend_port != frontend_port:
        print_status(f"Using frontend port {free_frontend_port} (configured: {frontend_port})", "warning")
    
    backend_dir = Path("persona_web_ui/backend")
    frontend_dir = Path("persona_web_ui/frontend")
    
    if not backend_dir.exists():
        print_status("Backend directory not found", "error")
        return False
    
    if not frontend_dir.exists():
        print_status("Frontend directory not found", "error")
        return False
    
    # Start backend
    print_status(f"Starting backend on port {free_backend_port}...")
    try:
        backend_process = subprocess.Popen(
            [sys.executable, "main.py"],
            cwd=backend_dir,
            env={**os.environ, 'WEB_UI_PORT': str(free_backend_port)}
        )
        
        # Wait for backend to start
        time.sleep(3)
        
        # Check if backend is still running
        if backend_process.poll() is not None:
            print_status("Backend failed to start", "error")
            return False
        
        print_status("Backend started successfully", "success")
        
    except Exception as e:
        print_status(f"Failed to start backend: {e}", "error")
        return False
    
    # Start frontend
    print_status(f"Starting frontend on port {free_frontend_port}...")
    try:
        frontend_env = {
            **os.environ,
            'FRONTEND_PORT': str(free_frontend_port),
            'VITE_API_BASE_URL': f'http://localhost:{free_backend_port}'
        }
        
        frontend_process = subprocess.Popen(
            ["npm", "run", "dev"],
            cwd=frontend_dir,
            env=frontend_env
        )
        
        # Wait for frontend to start
        time.sleep(5)
        
        # Check if frontend is still running
        if frontend_process.poll() is not None:
            print_status("Frontend failed to start", "error")
            backend_process.terminate()
            return False
        
        print_status("Frontend started successfully", "success")
        
    except Exception as e:
        print_status(f"Failed to start frontend: {e}", "error")
        backend_process.terminate()
        return False
    
    # Display access information
    print_status("\n" + "="*50, "success")
    print_status("🎉 PersonaOS Web UI is now running!", "success")
    print_status(f"• Backend API: http://localhost:{free_backend_port}", "info")
    print_status(f"• Web Interface: http://localhost:{free_frontend_port}", "info")
    print_status(f"• API Documentation: http://localhost:{free_backend_port}/docs", "info")
    print_status("="*50, "success")
    print_status("\nPress Ctrl+C to stop both services", "info")
    
    try:
        # Keep both processes running
        while True:
            time.sleep(1)
            
            # Check if processes are still alive
            if backend_process.poll() is not None:
                print_status("Backend process stopped", "warning")
                break
            if frontend_process.poll() is not None:
                print_status("Frontend process stopped", "warning")
                break
                
    except KeyboardInterrupt:
        print_status("\nStopping PersonaOS Web UI...", "info")
    finally:
        # Clean up processes
        try:
            frontend_process.terminate()
            backend_process.terminate()
            frontend_process.wait(timeout=5)
            backend_process.wait(timeout=5)
        except:
            pass
        print_status("PersonaOS Web UI stopped", "info")
    
    return True

def show_menu():
    """Display the main menu"""
    print(f"\n{Colors.BOLD}Choose your PersonaOS interface:{Colors.END}")
    print("1. 🖥️  CLI Mode (Terminal interface)")
    print("2. 🌐 Web UI Mode (Browser interface)")
    print("3. 🔧 System Health Check")
    print("4. ⚙️  Configuration Setup")
    print("5. 📚 Help & Documentation")
    print("6. 🚪 Exit")
    
    return input(f"\n{Colors.BOLD}Select option (1-6): {Colors.END}").strip()

def show_help():
    """Display help information"""
    print(f"\n{Colors.BOLD}PersonaOS Help & Documentation{Colors.END}")
    print("\n📖 Quick Start:")
    print("• First time? Run: python install.py")
    print("• CLI mode: python core/main.py")
    print("• Web UI mode: python start.py (this launcher)")
    print("• Configuration: python core/main.py --reset-env")
    
    print("\n🔧 Troubleshooting:")
    print("• System issues: Choose option 3 (Health Check)")
    print("• Port conflicts: Launcher auto-detects free ports")
    print("• Missing dependencies: Run python install.py")
    
    print("\n📁 Important Files:")
    print("• .env: Main configuration file")
    print("• requirements.txt: Python dependencies")
    print("• CLAUDE.md: Developer documentation")
    
    print("\n🌐 Web UI URLs:")
    load_dotenv()
    backend_port = os.getenv('WEB_UI_PORT', '8000')
    frontend_port = os.getenv('FRONTEND_PORT', '5173')
    print(f"• Backend: http://localhost:{backend_port}")
    print(f"• Frontend: http://localhost:{frontend_port}")
    print(f"• API Docs: http://localhost:{backend_port}/docs")

def main():
    """Main launcher interface"""
    # Set up enhanced error handling if available
    debug_mode = "--debug" in sys.argv or "--verbose" in sys.argv
    if ERROR_HANDLING_AVAILABLE:
        setup_global_exception_handler(debug_mode)
    
    print_header()
    
    # Parse command line arguments
    if "--cli" in sys.argv:
        with ErrorContext("CLI Mode Startup", debug_mode) if ERROR_HANDLING_AVAILABLE else None:
            start_cli_mode()
        return
    elif "--web" in sys.argv:
        with ErrorContext("Web UI Mode Startup", debug_mode) if ERROR_HANDLING_AVAILABLE else None:
            issues, node_available = check_system_health()
            if issues:
                print_status("System issues detected:", "warning")
                for issue in issues:
                    print_status(f"  • {issue}", "warning")
                if not run_health_repair():
                    sys.exit(1)
            
            if not node_available:
                print_status("Node.js not available. Starting CLI mode instead...", "warning")
                start_cli_mode()
            else:
                start_web_ui()
        return
    elif "--health" in sys.argv:
        with ErrorContext("System Health Check", debug_mode) if ERROR_HANDLING_AVAILABLE else None:
            issues, _ = check_system_health()
            if not issues:
                print_status("System health check passed", "success")
            else:
                for issue in issues:
                    print_status(issue, "warning")
                run_health_repair()
        return
    
    # Interactive mode
    while True:
        choice = show_menu()
        
        if choice == "1":
            # CLI Mode
            start_cli_mode()
            
        elif choice == "2":
            # Web UI Mode
            issues, node_available = check_system_health()
            
            if issues:
                print_status("System issues detected:", "warning")
                for issue in issues:
                    print_status(f"  • {issue}", "warning")
                
                repair = input("\nAttempt automatic repair? (y/N): ").strip().lower()
                if repair in ['y', 'yes']:
                    if not run_health_repair():
                        print_status("Repair failed. Please check system manually.", "error")
                        continue
                else:
                    continue
            
            if not node_available:
                print_status("Web UI requires Node.js. Please install Node.js or use CLI mode.", "warning")
                continue
            
            start_web_ui()
            
        elif choice == "3":
            # Health Check
            issues, node_available = check_system_health()
            
            if not issues:
                print_status("✅ All systems operational!", "success")
                print_status(f"• CLI Mode: Available", "info")
                print_status(f"• Web UI Mode: {'Available' if node_available else 'Requires Node.js'}", "info")
            else:
                print_status("System issues found:", "warning")
                for issue in issues:
                    print_status(f"  • {issue}", "warning")
                
                repair = input("\nAttempt automatic repair? (y/N): ").strip().lower()
                if repair in ['y', 'yes']:
                    run_health_repair()
            
        elif choice == "4":
            # Configuration Setup
            try:
                from setup_env import run_env_setup
                run_env_setup()
            except Exception as e:
                print_status(f"Configuration failed: {e}", "error")
            
        elif choice == "5":
            # Help
            show_help()
            
        elif choice == "6":
            # Exit
            print_status("Thank you for using PersonaOS! 👋", "success")
            break
            
        else:
            print_status("Invalid option. Please choose 1-6.", "warning")

if __name__ == "__main__":
    main()