from typing import Dict, List, Optional, Set
from enum import Enum
from dataclasses import dataclass
import re

class SafetyLevel(Enum):
    SAFE = "safe"
    CAUTION = "caution"
    UNSAFE = "unsafe"
    BLOCKED = "blocked"

@dataclass
class SafetyResult:
    level: SafetyLevel
    allowed: bool
    reason: str
    suggested_action: Optional[str] = None

class SafetyValidator:
    def __init__(self):
        self.blocked_commands = self._load_blocked_commands()
        self.sensitive_patterns = self._load_sensitive_patterns()
        self.safe_tools = self._load_safe_tools()
        self.restricted_tools = self._load_restricted_tools()
    
    def _load_blocked_commands(self) -> Set[str]:
        return {
            "system_shutdown",
            "system_restart", 
            "file_delete",
            "network_scan",
            "password_access",
            "credential_access",
            "admin_privilege",
            "root_access",
            "registry_modify",
            "firewall_disable",
            "antivirus_disable"
        }
    
    def _load_sensitive_patterns(self) -> List[str]:
        return [
            r"(?:password|passwd|pwd|credential|secret|token|key|auth)",
            r"(?:delete|remove|erase|wipe|destroy).*(?:file|folder|directory|disk|drive)",
            r"(?:shutdown|restart|reboot|halt).*(?:system|computer|machine)",
            r"(?:install|execute|run).*(?:\.exe|\.bat|\.cmd|\.sh|\.ps1)",
            r"(?:access|read|open).*(?:private|personal|confidential|sensitive)",
            r"(?:hack|crack|break|bypass|exploit)",
            r"(?:admin|administrator|root|sudo|privilege)",
            r"(?:network|wifi|internet).*(?:scan|probe|attack)"
        ]
    
    def _load_safe_tools(self) -> Set[str]:
        return {
            "web_search",
            "weather",
            "time",
            "calculator",
            "timer",
            "joke_generator",
            "fact_lookup",
            "unit_converter",
            "text_analyzer"
        }
    
    def _load_restricted_tools(self) -> Dict[str, str]:
        return {
            "file_browser": "Read-only file browsing in safe directories only",
            "web_browser": "Limited to whitelisted domains",
            "email_client": "Send-only, no credential access",
            "calendar": "View and create events only",
            "note_taking": "Local notes only, no cloud sync"
        }
    
    def validate_intent(self, intent_result) -> SafetyResult:
        if intent_result.intent.value == "unsafe":
            return SafetyResult(
                level=SafetyLevel.BLOCKED,
                allowed=False,
                reason="Intent classified as unsafe by pattern matching"
            )
        
        if intent_result.tool:
            return self._validate_tool_usage(intent_result.tool, intent_result.args)
        
        return SafetyResult(
            level=SafetyLevel.SAFE,
            allowed=True,
            reason="Safe response intent"
        )
    
    def _validate_tool_usage(self, tool: str, args: Optional[Dict]) -> SafetyResult:
        if tool in self.blocked_commands:
            return SafetyResult(
                level=SafetyLevel.BLOCKED,
                allowed=False,
                reason=f"Tool '{tool}' is in blocked commands list"
            )
        
        if tool in self.safe_tools:
            return self._validate_tool_args(tool, args)
        
        if tool in self.restricted_tools:
            restriction = self.restricted_tools[tool]
            return SafetyResult(
                level=SafetyLevel.CAUTION,
                allowed=True,
                reason=f"Tool '{tool}' has restrictions: {restriction}",
                suggested_action="Proceed with limited functionality"
            )
        
        return SafetyResult(
            level=SafetyLevel.CAUTION,
            allowed=True,
            reason=f"Unknown tool '{tool}' - proceeding with caution",
            suggested_action="Monitor execution closely"
        )
    
    def _validate_tool_args(self, tool: str, args: Optional[Dict]) -> SafetyResult:
        if not args:
            return SafetyResult(
                level=SafetyLevel.SAFE,
                allowed=True,
                reason="No arguments to validate"
            )
        
        for key, value in args.items():
            if isinstance(value, str):
                safety_check = self._check_text_safety(value)
                if not safety_check.allowed:
                    return SafetyResult(
                        level=SafetyLevel.UNSAFE,
                        allowed=False,
                        reason=f"Unsafe content in argument '{key}': {safety_check.reason}"
                    )
        
        if tool == "web_search":
            return self._validate_search_query(args.get("query", ""))
        elif tool == "file_browser":
            return self._validate_file_access(args.get("path", ""))
        
        return SafetyResult(
            level=SafetyLevel.SAFE,
            allowed=True,
            reason="Arguments passed safety validation"
        )
    
    def _check_text_safety(self, text: str) -> SafetyResult:
        text_lower = text.lower()
        
        for pattern in self.sensitive_patterns:
            if re.search(pattern, text_lower):
                return SafetyResult(
                    level=SafetyLevel.UNSAFE,
                    allowed=False,
                    reason=f"Text contains sensitive pattern: {pattern}"
                )
        
        suspicious_keywords = [
            "hack", "crack", "exploit", "malware", "virus",
            "illegal", "piracy", "drugs", "weapons"
        ]
        
        for keyword in suspicious_keywords:
            if keyword in text_lower:
                return SafetyResult(
                    level=SafetyLevel.CAUTION,
                    allowed=True,
                    reason=f"Text contains potentially sensitive keyword: {keyword}",
                    suggested_action="Review content before proceeding"
                )
        
        return SafetyResult(
            level=SafetyLevel.SAFE,
            allowed=True,
            reason="Text passed safety checks"
        )
    
    def _validate_search_query(self, query: str) -> SafetyResult:
        if not query or len(query.strip()) == 0:
            return SafetyResult(
                level=SafetyLevel.UNSAFE,
                allowed=False,
                reason="Empty search query"
            )
        
        if len(query) > 200:
            return SafetyResult(
                level=SafetyLevel.CAUTION,
                allowed=True,
                reason="Search query is unusually long",
                suggested_action="Truncate query to first 200 characters"
            )
        
        return self._check_text_safety(query)
    
    def _validate_file_access(self, path: str) -> SafetyResult:
        if not path:
            return SafetyResult(
                level=SafetyLevel.SAFE,
                allowed=True,
                reason="No specific path provided"
            )
        
        dangerous_paths = [
            "/etc/", "/sys/", "/proc/", "/root/",
            "C:\\Windows\\System32\\", "C:\\Program Files\\",
            ".ssh/", ".aws/", ".env", "password", "credential"
        ]
        
        path_lower = path.lower()
        for dangerous in dangerous_paths:
            if dangerous.lower() in path_lower:
                return SafetyResult(
                    level=SafetyLevel.BLOCKED,
                    allowed=False,
                    reason=f"Access to restricted path: {dangerous}"
                )
        
        return SafetyResult(
            level=SafetyLevel.SAFE,
            allowed=True,
            reason="File path appears safe"
        )
    
    def add_blocked_command(self, command: str):
        self.blocked_commands.add(command)
    
    def add_safe_tool(self, tool: str):
        self.safe_tools.add(tool)
    
    def add_restricted_tool(self, tool: str, restriction: str):
        self.restricted_tools[tool] = restriction