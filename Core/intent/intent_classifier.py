import re
import json
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

class IntentType(Enum):
    SAFE_RESPONSE = "safe_response"
    TOOL_REQUIRED = "tool_required"
    UNSAFE = "unsafe"

@dataclass
class IntentResult:
    intent: IntentType
    confidence: float
    tool: Optional[str] = None
    args: Optional[Dict] = None
    reason: Optional[str] = None

class IntentPattern:
    def __init__(self, pattern: str, intent: IntentType, tool: str = None, arg_extractors: Dict = None):
        self.pattern = re.compile(pattern, re.IGNORECASE)
        self.intent = intent
        self.tool = tool
        self.arg_extractors = arg_extractors or {}
    
    def match(self, text: str) -> Optional[IntentResult]:
        match = self.pattern.search(text)
        if not match:
            return None
        
        args = {}
        for arg_name, extractor in self.arg_extractors.items():
            if isinstance(extractor, str):
                try:
                    args[arg_name] = match.group(extractor)
                except IndexError:
                    args[arg_name] = None
            elif callable(extractor):
                args[arg_name] = extractor(text, match)
        
        return IntentResult(
            intent=self.intent,
            confidence=1.0,
            tool=self.tool,
            args=args if args else None
        )

class IntentClassifier:
    def __init__(self):
        self.patterns = []
        self._load_default_patterns()
    
    def _load_default_patterns(self):
        unsafe_patterns = [
            r"(delete|remove|erase).*(file|folder|directory|system)",
            r"(shutdown|restart|reboot).*(computer|system)",
            r"(install|download).*(software|program|app)",
            r"(access|hack|break).*(password|security|account)",
            r"(send|share).*(personal|private|sensitive)",
        ]
        
        for pattern in unsafe_patterns:
            self.patterns.append(IntentPattern(
                pattern=pattern,
                intent=IntentType.UNSAFE
            ))
        
        tool_patterns = [
            IntentPattern(
                pattern=r"(search|look up|find|google).+?(for|about)?\s*(.+)",
                intent=IntentType.TOOL_REQUIRED,
                tool="web_search",
                arg_extractors={"query": lambda text, match: self._extract_search_query(text)}
            ),
            IntentPattern(
                pattern=r"(weather|temperature|forecast).+?(in|for|at)?\s*(.+)",
                intent=IntentType.TOOL_REQUIRED,
                tool="weather",
                arg_extractors={"location": lambda text, match: self._extract_location(text)}
            ),
            IntentPattern(
                pattern=r"(set|start).+?(timer|alarm).+?(\d+)\s*(minute|hour|second)",
                intent=IntentType.TOOL_REQUIRED,
                tool="timer",
                arg_extractors={
                    "duration": lambda text, match: self._extract_duration(text),
                    "unit": lambda text, match: self._extract_time_unit(text)
                }
            ),
            IntentPattern(
                pattern=r"(what.+?time|current time|time is it)",
                intent=IntentType.TOOL_REQUIRED,
                tool="time"
            ),
        ]
        
        self.patterns.extend(tool_patterns)
        
        safe_patterns = [
            IntentPattern(
                pattern=r"(tell me|give me).+?(joke|story|fact)",
                intent=IntentType.SAFE_RESPONSE
            ),
            IntentPattern(
                pattern=r"(how are you|hello|hi|hey)",
                intent=IntentType.SAFE_RESPONSE
            ),
            IntentPattern(
                pattern=r"(explain|what is|define).+",
                intent=IntentType.SAFE_RESPONSE
            ),
        ]
        
        self.patterns.extend(safe_patterns)
    
    def classify(self, text: str) -> IntentResult:
        if not text or not text.strip():
            return IntentResult(
                intent=IntentType.SAFE_RESPONSE,
                confidence=0.5,
                reason="Empty input"
            )
        
        text = text.strip()
        
        for pattern in self.patterns:
            result = pattern.match(text)
            if result:
                return result
        
        return IntentResult(
            intent=IntentType.SAFE_RESPONSE,
            confidence=0.3,
            reason="No specific pattern matched, defaulting to safe response"
        )
    
    def _extract_search_query(self, text: str) -> str:
        patterns = [
            r"(?:search|look up|find|google)\s+(?:for|about)?\s*(.+)",
            r"(.+?)(?:\s+(?:search|lookup|find))",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return text
    
    def _extract_location(self, text: str) -> str:
        match = re.search(r"(?:in|for|at)\s+(.+)", text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        
        words = text.split()
        if len(words) > 1:
            return " ".join(words[-2:])
        
        return "current location"
    
    def _extract_duration(self, text: str) -> int:
        match = re.search(r"(\d+)", text)
        return int(match.group(1)) if match else 5
    
    def _extract_time_unit(self, text: str) -> str:
        units = ["second", "minute", "hour"]
        for unit in units:
            if unit in text.lower():
                return unit
        return "minute"
    
    def add_pattern(self, pattern: IntentPattern):
        self.patterns.insert(0, pattern)
    
    def to_dict(self) -> Dict:
        return {
            "intent": self.intent.value,
            "confidence": self.confidence,
            "tool": self.tool,
            "args": self.args,
            "reason": self.reason
        }