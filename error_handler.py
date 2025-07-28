#!/usr/bin/env python3
"""
PersonaOS Enhanced Error Handling
Provides user-friendly error messages and recovery suggestions
"""

import sys
import traceback
import logging
from pathlib import Path
from typing import Optional, Dict, List

class PersonaOSError(Exception):
    """Base exception class for PersonaOS-specific errors"""
    def __init__(self, message: str, error_code: str = "GENERAL", suggestions: List[str] = None):
        self.message = message
        self.error_code = error_code
        self.suggestions = suggestions or []
        super().__init__(self.message)

class ConfigurationError(PersonaOSError):
    """Raised when there are configuration issues"""
    def __init__(self, message: str, suggestions: List[str] = None):
        super().__init__(message, "CONFIG_ERROR", suggestions)

class DependencyError(PersonaOSError):
    """Raised when dependencies are missing or incompatible"""
    def __init__(self, message: str, suggestions: List[str] = None):
        super().__init__(message, "DEPENDENCY_ERROR", suggestions)

class ServiceError(PersonaOSError):
    """Raised when external services (like Ollama) are unavailable"""
    def __init__(self, message: str, suggestions: List[str] = None):
        super().__init__(message, "SERVICE_ERROR", suggestions)

class ErrorHandler:
    """Enhanced error handler with user-friendly messages and recovery suggestions"""
    
    def __init__(self, debug_mode: bool = False):
        self.debug_mode = debug_mode
        self.error_patterns = self._load_error_patterns()
        
    def _load_error_patterns(self) -> Dict[str, Dict]:
        """Load common error patterns and their user-friendly explanations"""
        return {
            # Python/Import Errors
            "ModuleNotFoundError": {
                "title": "Missing Python Package",
                "explanation": "A required Python package is not installed.",
                "suggestions": [
                    "Run: pip install -r requirements.txt",
                    "Or use: python install.py (automatic)",
                    "Check if you're in the correct directory"
                ]
            },
            
            "ImportError": {
                "title": "Import Problem",
                "explanation": "There's an issue importing a Python module.",
                "suggestions": [
                    "Reinstall dependencies: pip install -r requirements.txt",
                    "Check Python version (requires 3.7+): python --version",
                    "Run system health check: python start.py --health"
                ]
            },
            
            # File/Configuration Errors
            "FileNotFoundError": {
                "title": "Missing File",
                "explanation": "A required file or directory could not be found.",
                "suggestions": [
                    "Check if you're in the PersonaOS directory",
                    "Run setup: python core/main.py",
                    "Reinstall: python install.py"
                ]
            },
            
            "PermissionError": {
                "title": "Permission Denied",
                "explanation": "PersonaOS doesn't have permission to access a file or directory.",
                "suggestions": [
                    "Run terminal as Administrator (Windows) or use sudo (Linux/macOS)",
                    "Check file permissions in the PersonaOS directory",
                    "Make sure antivirus isn't blocking PersonaOS"
                ]
            },
            
            # Network/Service Errors
            "ConnectionRefusedError": {
                "title": "Connection Refused",
                "explanation": "Cannot connect to a service (likely Ollama or Web UI).",
                "suggestions": [
                    "Check if Ollama is running: ollama --version",
                    "Restart Ollama service",
                    "Check ports aren't blocked: python start.py --health",
                    "Try: python start.py (auto port detection)"
                ]
            },
            
            "TimeoutError": {
                "title": "Operation Timeout",
                "explanation": "An operation took too long to complete.",
                "suggestions": [
                    "Wait longer (AI model loading can take 5+ minutes)",
                    "Check internet connection",
                    "Try a smaller AI model: ollama pull openhermes:7b",
                    "Restart PersonaOS"
                ]
            },
            
            # API/Service Specific
            "requests.exceptions.ConnectionError": {
                "title": "Network Connection Error",
                "explanation": "Cannot connect to external service or API.",
                "suggestions": [
                    "Check internet connection",
                    "Verify API endpoints are accessible",
                    "Check firewall settings",
                    "Use local Ollama instead of cloud APIs"
                ]
            },
            
            "subprocess.CalledProcessError": {
                "title": "External Command Failed",
                "explanation": "An external command (like Ollama) failed to execute.",
                "suggestions": [
                    "Check if Ollama is installed: ollama --version",
                    "Reinstall Ollama from https://ollama.com",
                    "Run: python install.py (automatic installation)",
                    "Check system requirements"
                ]
            },
            
            # JSON/Configuration Errors
            "json.JSONDecodeError": {
                "title": "Configuration File Error",
                "explanation": "A configuration file contains invalid JSON.",
                "suggestions": [
                    "Reset configuration: python core/main.py --reset-env",
                    "Check .env file for syntax errors",
                    "Restore from backup if available"
                ]
            },
            
            # Port/Network Issues
            "OSError": {
                "title": "System Error",
                "explanation": "A system-level error occurred (often port-related).",
                "suggestions": [
                    "Check if ports are available: python start.py --health",
                    "Use auto port detection: python start.py",
                    "Restart your computer",
                    "Check for conflicting applications"
                ]
            }
        }
    
    def format_error(self, exception: Exception, context: str = "") -> str:
        """Format an exception into a user-friendly error message"""
        error_type = type(exception).__name__
        error_message = str(exception)
        
        # Check if it's a PersonaOS-specific error
        if isinstance(exception, PersonaOSError):
            return self._format_personaos_error(exception, context)
        
        # Look for known error patterns
        pattern = self.error_patterns.get(error_type)
        if not pattern:
            # Try to match by error message content
            pattern = self._match_error_by_content(error_message)
        
        if pattern:
            return self._format_known_error(error_type, error_message, pattern, context)
        else:
            return self._format_unknown_error(error_type, error_message, context)
    
    def _format_personaos_error(self, error: PersonaOSError, context: str) -> str:
        """Format a PersonaOS-specific error"""
        lines = [
            f"❌ {error.error_code}: {error.message}",
            ""
        ]
        
        if context:
            lines.extend([f"📍 Context: {context}", ""])
        
        if error.suggestions:
            lines.append("💡 Suggested solutions:")
            for suggestion in error.suggestions:
                lines.append(f"  • {suggestion}")
            lines.append("")
        
        lines.append("🆘 Need more help? Run: python start.py --health")
        
        return "\n".join(lines)
    
    def _format_known_error(self, error_type: str, message: str, pattern: Dict, context: str) -> str:
        """Format a known error pattern"""
        lines = [
            f"❌ {pattern['title']}",
            f"📋 {pattern['explanation']}",
            ""
        ]
        
        if context:
            lines.extend([f"📍 Where: {context}", ""])
        
        if self.debug_mode:
            lines.extend([f"🔧 Technical details: {error_type}: {message}", ""])
        
        lines.append("💡 How to fix this:")
        for suggestion in pattern['suggestions']:
            lines.append(f"  • {suggestion}")
        
        lines.extend([
            "",
            "🆘 Still stuck? Run: python start.py --health",
            "📖 Check troubleshooting guide: docs/troubleshooting.md"
        ])
        
        return "\n".join(lines)
    
    def _format_unknown_error(self, error_type: str, message: str, context: str) -> str:
        """Format an unknown error"""
        lines = [
            f"❌ Unexpected Error: {error_type}",
            f"📋 {message}",
            ""
        ]
        
        if context:
            lines.extend([f"📍 Context: {context}", ""])
        
        lines.extend([
            "💡 Try these general solutions:",
            "  • Run system health check: python start.py --health",
            "  • Restart PersonaOS",
            "  • Check troubleshooting guide: docs/troubleshooting.md",
            "  • Report this issue if it persists",
            ""
        ])
        
        if self.debug_mode:
            lines.extend([
                "🔧 Technical details:",
                f"Error Type: {error_type}",
                f"Message: {message}",
                ""
            ])
        
        lines.append("🐛 Report bugs at: https://github.com/personaos/PersonaOS/issues")
        
        return "\n".join(lines)
    
    def _match_error_by_content(self, message: str) -> Optional[Dict]:
        """Try to match error by message content"""
        message_lower = message.lower()
        
        # Port-related errors
        if "port" in message_lower and ("in use" in message_lower or "bind" in message_lower):
            return {
                "title": "Port Already in Use",
                "explanation": "The required network port is being used by another application.",
                "suggestions": [
                    "Use auto port detection: python start.py",
                    "Check what's using the port: netstat -an | grep :8000",
                    "Try different ports in .env file",
                    "Restart your computer"
                ]
            }
        
        # Ollama-related errors
        if "ollama" in message_lower:
            return {
                "title": "Ollama Service Issue",
                "explanation": "There's a problem with the Ollama AI service.",
                "suggestions": [
                    "Check Ollama installation: ollama --version",
                    "Restart Ollama service",
                    "Reinstall Ollama: python install.py",
                    "Download AI model: ollama pull openhermes"
                ]
            }
        
        # API Key errors
        if "api" in message_lower and ("key" in message_lower or "auth" in message_lower):
            return {
                "title": "API Authentication Error",
                "explanation": "There's an issue with API key authentication.",
                "suggestions": [
                    "Check API key format and validity",
                    "Reconfigure: python core/main.py --reset-env",
                    "Use local Ollama instead (no API key needed)",
                    "Verify API service status"
                ]
            }
        
        return None
    
    def log_error(self, exception: Exception, context: str = ""):
        """Log error to file for debugging"""
        log_file = Path("personaos_errors.log")
        
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"\n{'='*50}\n")
            f.write(f"Timestamp: {__import__('datetime').datetime.now()}\n")
            f.write(f"Context: {context}\n")
            f.write(f"Error: {type(exception).__name__}: {exception}\n")
            
            if self.debug_mode:
                f.write("Traceback:\n")
                traceback.print_exc(file=f)
            
            f.write(f"{'='*50}\n")

def handle_exception(exception: Exception, context: str = "", debug_mode: bool = False) -> str:
    """Convenience function to handle any exception"""
    handler = ErrorHandler(debug_mode=debug_mode)
    
    # Log the error
    handler.log_error(exception, context)
    
    # Format and return user-friendly message
    return handler.format_error(exception, context)

def setup_global_exception_handler(debug_mode: bool = False):
    """Set up global exception handler for uncaught exceptions"""
    def exception_handler(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            # Allow Ctrl+C to work normally
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        
        # Handle the exception
        error_message = handle_exception(exc_value, "Global Exception", debug_mode)
        print(f"\n{error_message}")
        
        # Exit gracefully
        sys.exit(1)
    
    sys.excepthook = exception_handler

# Context manager for handling exceptions in specific code blocks
class ErrorContext:
    """Context manager for handling exceptions with specific context"""
    
    def __init__(self, context: str, debug_mode: bool = False):
        self.context = context
        self.debug_mode = debug_mode
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        if exc_value is not None:
            error_message = handle_exception(exc_value, self.context, self.debug_mode)
            print(f"\n{error_message}")
            return True  # Suppress the exception
        return False

# Example usage:
if __name__ == "__main__":
    # Test the error handler
    handler = ErrorHandler(debug_mode=True)
    
    # Test different error types
    test_errors = [
        ModuleNotFoundError("No module named 'nonexistent_package'"),
        FileNotFoundError("The file '.env' could not be found"),
        ConnectionRefusedError("Connection refused to localhost:8000"),
        ConfigurationError("Invalid API key format", ["Check API key format", "Run setup wizard"]),
    ]
    
    for error in test_errors:
        print(handler.format_error(error, "Testing"))
        print("\n" + "="*50 + "\n")