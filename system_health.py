#!/usr/bin/env python3
"""
PersonaOS System Health Checker
Comprehensive diagnostic and repair tool for PersonaOS
"""

import os
import sys
import subprocess
import json
import socket
import importlib
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dotenv import load_dotenv, dotenv_values

class HealthCheck:
    """System health checker for PersonaOS"""
    
    def __init__(self, verbose=False):
        self.verbose = verbose
        self.issues = []
        self.warnings = []
        self.info = []
        
    def log(self, message, level="info"):
        """Log a message at the specified level"""
        if level == "error":
            self.issues.append(message)
        elif level == "warning":
            self.warnings.append(message)
        else:
            self.info.append(message)
            
        if self.verbose:
            prefix = "❌" if level == "error" else "⚠️" if level == "warning" else "ℹ️"
            print(f"{prefix} {message}")
    
    def check_python_version(self) -> bool:
        """Check if Python version is compatible"""
        version = sys.version_info
        
        if version.major < 3 or (version.major == 3 and version.minor < 7):
            self.log(f"Python {version.major}.{version.minor} is too old. Requires Python 3.7+", "error")
            return False
        
        self.log(f"Python {version.major}.{version.minor}.{version.micro} ✓", "info")
        return True
    
    def check_dependencies(self) -> bool:
        """Check if required Python packages are installed"""
        required_packages = {
            'requests': 'requests',
            'yaml': 'pyyaml',
            'dotenv': 'python-dotenv',
            'cryptography': 'cryptography',
            'colorama': 'colorama',
            'fastapi': 'fastapi',
            'uvicorn': 'uvicorn'
        }
        
        missing = []
        for module, package in required_packages.items():
            try:
                importlib.import_module(module)
                self.log(f"Package {package} ✓", "info")
            except ImportError:
                missing.append(package)
                self.log(f"Missing package: {package}", "error")
        
        if missing:
            self.log(f"Install missing packages: pip install {' '.join(missing)}", "error")
            return False
        
        return True
    
    def check_ollama(self) -> Tuple[bool, Optional[str]]:
        """Check if Ollama is installed and working"""
        try:
            result = subprocess.run(
                ["ollama", "--version"], 
                capture_output=True, 
                text=True, 
                timeout=10
            )
            
            if result.returncode == 0:
                version = result.stdout.strip()
                self.log(f"Ollama {version} ✓", "info")
                
                # Check if Ollama service is running
                try:
                    list_result = subprocess.run(
                        ["ollama", "list"],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    
                    if list_result.returncode == 0:
                        models = list_result.stdout.strip().split('\n')[1:]  # Skip header
                        model_count = len([m for m in models if m.strip()])
                        
                        if model_count > 0:
                            self.log(f"Ollama has {model_count} model(s) available", "info")
                            return True, version
                        else:
                            self.log("No Ollama models installed", "warning")
                            return True, version
                    else:
                        self.log("Ollama service not responding", "error")
                        return False, version
                        
                except subprocess.TimeoutExpired:
                    self.log("Ollama service timeout", "error")
                    return False, version
                
            else:
                self.log(f"Ollama command failed: {result.stderr}", "error")
                return False, None
                
        except FileNotFoundError:
            self.log("Ollama not installed", "error")
            return False, None
        except subprocess.TimeoutExpired:
            self.log("Ollama command timeout", "error")
            return False, None
    
    def check_nodejs(self) -> Tuple[bool, Optional[str]]:
        """Check if Node.js is installed"""
        try:
            result = subprocess.run(
                ["node", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                version = result.stdout.strip()
                self.log(f"Node.js {version} ✓", "info")
                
                # Check npm
                npm_result = subprocess.run(
                    ["npm", "--version"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                if npm_result.returncode == 0:
                    npm_version = npm_result.stdout.strip()
                    self.log(f"npm {npm_version} ✓", "info")
                else:
                    self.log("npm not available", "warning")
                
                return True, version
            else:
                self.log("Node.js command failed", "error")
                return False, None
                
        except FileNotFoundError:
            self.log("Node.js not installed", "warning")
            return False, None
        except subprocess.TimeoutExpired:
            self.log("Node.js command timeout", "error")
            return False, None
    
    def check_configuration(self) -> bool:
        """Check PersonaOS configuration"""
        env_file = Path(".env")
        
        if not env_file.exists():
            self.log("Configuration file (.env) missing", "error")
            return False
        
        # Load and validate environment variables
        load_dotenv()
        env_vars = dotenv_values(env_file)
        
        required_vars = {
            'LLM_PROVIDER': 'LLM service provider',
            'WEB_UI_PORT': 'Backend API port',
            'FRONTEND_PORT': 'Frontend development port'
        }
        
        missing_vars = []
        for var, description in required_vars.items():
            if not env_vars.get(var):
                missing_vars.append(f"{var} ({description})")
                self.log(f"Missing configuration: {var}", "error")
            else:
                self.log(f"Configuration {var} ✓", "info")
        
        if missing_vars:
            self.log("Run configuration setup: python core/main.py", "error")
            return False
        
        # Validate port numbers
        for port_var in ['WEB_UI_PORT', 'FRONTEND_PORT']:
            port_value = env_vars.get(port_var)
            if port_value and not port_value.isdigit():
                self.log(f"Invalid port number for {port_var}: {port_value}", "error")
                return False
        
        return True
    
    def check_ports(self) -> bool:
        """Check if configured ports are available"""
        load_dotenv()
        
        backend_port = int(os.getenv('WEB_UI_PORT', '8000'))
        frontend_port = int(os.getenv('FRONTEND_PORT', '5173'))
        
        ports_to_check = [
            (backend_port, 'Backend API'),
            (frontend_port, 'Frontend Dev Server')
        ]
        
        all_available = True
        
        for port, description in ports_to_check:
            if self.is_port_in_use(port):
                self.log(f"Port {port} ({description}) is in use", "warning")
                # Find alternative port
                alt_port = self.find_free_port(port)
                if alt_port:
                    self.log(f"Alternative port available: {alt_port}", "info")
                else:
                    self.log(f"No alternative ports found near {port}", "warning")
            else:
                self.log(f"Port {port} ({description}) available ✓", "info")
        
        return all_available
    
    def is_port_in_use(self, port: int) -> bool:
        """Check if a port is currently in use"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                result = s.connect_ex(('localhost', port))
                return result == 0
        except:
            return False
    
    def find_free_port(self, start_port: int, max_attempts: int = 10) -> Optional[int]:
        """Find a free port starting from start_port"""
        for i in range(max_attempts):
            port = start_port + i
            if not self.is_port_in_use(port):
                return port
        return None
    
    def check_file_structure(self) -> bool:
        """Check if PersonaOS file structure is intact"""
        required_files = [
            'core/main.py',
            'core/config.py', 
            'setup_env.py',
            'requirements.txt',
            '.env.template'
        ]
        
        required_dirs = [
            'core',
            'core/llm',
            'persona_web_ui/backend',
            'persona_web_ui/frontend'
        ]
        
        missing_files = []
        missing_dirs = []
        
        for file_path in required_files:
            if not Path(file_path).exists():
                missing_files.append(file_path)
                self.log(f"Missing file: {file_path}", "error")
            else:
                self.log(f"File {file_path} ✓", "info")
        
        for dir_path in required_dirs:
            if not Path(dir_path).exists():
                missing_dirs.append(dir_path)
                self.log(f"Missing directory: {dir_path}", "error")
            else:
                self.log(f"Directory {dir_path} ✓", "info")
        
        return len(missing_files) == 0 and len(missing_dirs) == 0
    
    def check_frontend_dependencies(self) -> bool:
        """Check if frontend dependencies are installed"""
        frontend_dir = Path("persona_web_ui/frontend")
        
        if not frontend_dir.exists():
            self.log("Frontend directory not found", "error")
            return False
        
        node_modules = frontend_dir / "node_modules"
        package_json = frontend_dir / "package.json"
        
        if not package_json.exists():
            self.log("Frontend package.json missing", "error")
            return False
        
        if not node_modules.exists():
            self.log("Frontend dependencies not installed (npm install needed)", "warning")
            return False
        
        self.log("Frontend dependencies installed ✓", "info")
        return True
    
    def run_comprehensive_check(self) -> Dict[str, any]:
        """Run all health checks and return summary"""
        results = {}
        
        if self.verbose:
            print("🔍 Running PersonaOS System Health Check...\n")
        
        # Core system checks
        results['python'] = self.check_python_version()
        results['dependencies'] = self.check_dependencies()
        results['file_structure'] = self.check_file_structure()
        results['configuration'] = self.check_configuration()
        
        # External service checks
        ollama_ok, ollama_version = self.check_ollama()
        results['ollama'] = ollama_ok
        results['ollama_version'] = ollama_version
        
        node_ok, node_version = self.check_nodejs()
        results['nodejs'] = node_ok
        results['node_version'] = node_version
        
        # Web UI specific checks
        if node_ok:
            results['frontend_deps'] = self.check_frontend_dependencies()
        else:
            results['frontend_deps'] = False
        
        # Network checks
        results['ports'] = self.check_ports()
        
        # Summary
        critical_checks = ['python', 'dependencies', 'file_structure', 'configuration', 'ollama']
        critical_passed = sum(1 for check in critical_checks if results.get(check, False))
        
        results['summary'] = {
            'critical_passed': critical_passed,
            'critical_total': len(critical_checks),
            'web_ui_ready': results.get('nodejs', False) and results.get('frontend_deps', False),
            'issues': len(self.issues),
            'warnings': len(self.warnings),
            'status': 'healthy' if critical_passed == len(critical_checks) and len(self.issues) == 0 else 'issues'
        }
        
        return results
    
    def generate_report(self, results: Dict) -> str:
        """Generate a human-readable health report"""
        report = []
        summary = results['summary']
        
        # Header
        status_emoji = "✅" if summary['status'] == 'healthy' else "⚠️"
        report.append(f"{status_emoji} PersonaOS System Health Report")
        report.append("=" * 50)
        
        # Overall status
        if summary['status'] == 'healthy':
            report.append("🎉 System is healthy and ready to use!")
        else:
            report.append(f"⚠️  System has {summary['issues']} issues and {summary['warnings']} warnings")
        
        report.append("")
        
        # Core functionality
        report.append("🔧 Core Functionality:")
        core_checks = [
            ('python', 'Python Environment'),
            ('dependencies', 'Python Dependencies'),
            ('file_structure', 'File Structure'),
            ('configuration', 'Configuration'),
            ('ollama', 'Ollama AI Service')
        ]
        
        for check, name in core_checks:
            status = "✅" if results.get(check, False) else "❌"
            report.append(f"  {status} {name}")
        
        report.append("")
        
        # Web UI status
        report.append("🌐 Web UI Status:")
        if results.get('nodejs', False):
            report.append(f"  ✅ Node.js {results.get('node_version', 'installed')}")
            
            if results.get('frontend_deps', False):
                report.append("  ✅ Frontend Dependencies")
                report.append("  🎯 Web UI Ready!")
            else:
                report.append("  ❌ Frontend Dependencies (run: npm install)")
        else:
            report.append("  ❌ Node.js not installed")
            report.append("  ℹ️  Web UI unavailable (CLI mode only)")
        
        report.append("")
        
        # Issues and warnings
        if self.issues:
            report.append("❌ Issues Found:")
            for issue in self.issues:
                report.append(f"  • {issue}")
            report.append("")
        
        if self.warnings:
            report.append("⚠️  Warnings:")
            for warning in self.warnings:
                report.append(f"  • {warning}")
            report.append("")
        
        # Recommendations
        report.append("💡 Recommendations:")
        if summary['status'] != 'healthy':
            report.append("  • Run: python install.py (automatic repair)")
            if not results.get('ollama', False):
                report.append("  • Install Ollama: https://ollama.com/download")
            if not results.get('configuration', False):
                report.append("  • Configure system: python core/main.py")
        else:
            report.append("  • System ready! Run: python start.py")
        
        return "\n".join(report)

def main():
    """Main health check script"""
    verbose = "--verbose" in sys.argv or "-v" in sys.argv
    json_output = "--json" in sys.argv
    
    checker = HealthCheck(verbose=verbose)
    results = checker.run_comprehensive_check()
    
    if json_output:
        # Output results as JSON
        output = {
            'status': results['summary']['status'],
            'results': results,
            'issues': checker.issues,
            'warnings': checker.warnings,
            'info': checker.info
        }
        print(json.dumps(output, indent=2))
    else:
        # Output human-readable report
        report = checker.generate_report(results)
        print(report)
    
    # Exit with appropriate code
    sys.exit(0 if results['summary']['status'] == 'healthy' else 1)

if __name__ == "__main__":
    main()