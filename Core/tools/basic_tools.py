import time
import datetime
import requests
import json
import re
from typing import Dict, Any, Optional
from .tool_registry import BaseTool, ToolResult, VoiceToolContext

# Import parameter collection types if available
try:
    from .voice_parameter_collector import ParameterSpec, ParameterType
except ImportError:
    ParameterSpec = None
    ParameterType = None

class WebSearchTool(BaseTool):
    def __init__(self):
        super().__init__("web_search", "Search the web for information")
        self.voice_aliases = ["search", "google", "look up", "find"]
        self.voice_parameter_patterns = {
            "query": r"search (?:for |about )?(.+?)(?:\s|$)"
        }
    
    def execute(self, query: str = "", **kwargs) -> ToolResult:
        if not query:
            return ToolResult(
                success=False,
                error="Search query is required"
            )
        
        # Placeholder implementation - in real usage, integrate with search API
        return ToolResult(
            success=True,
            data={
                "query": query,
                "results": [
                    {
                        "title": f"Search result for: {query}",
                        "url": "https://example.com",
                        "snippet": f"This is a placeholder result for the query '{query}'"
                    }
                ]
            },
            metadata={"source": "placeholder", "timestamp": time.time()}
        )
    
    def parse_voice_parameters(self, voice_text: str) -> Dict[str, Any]:
        """Parse search query from voice command."""
        params = {}
        voice_lower = voice_text.lower()
        
        # Try different patterns to extract search query
        patterns = [
            r"search (?:for |about )?(.+)",
            r"google (.+)",
            r"look up (.+)",
            r"find (.+)",
            r"what is (.+)",
            r"who is (.+)",
            r"where is (.+)",
            r"how to (.+)"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, voice_lower)
            if match:
                params["query"] = match.group(1).strip()
                break
        
        return params
    
    def format_voice_response(self, data: Any, voice_context: VoiceToolContext) -> str:
        """Format search results for voice output."""
        if not data or "results" not in data:
            return "I couldn't find any search results."
        
        results = data["results"]
        if not results:
            return f"I didn't find any results for '{data.get('query', 'your search')}'."
        
        first_result = results[0]
        query = data.get("query", "your search")
        
        return f"I found information about {query}. {first_result.get('snippet', 'Here are the search results.')}"

class WeatherTool(BaseTool):
    def __init__(self):
        super().__init__("weather", "Get weather information for a location")
        self.voice_aliases = ["weather forecast", "temperature", "how's the weather"]
    
    def execute(self, location: str = "current location", **kwargs) -> ToolResult:
        # Placeholder implementation - in real usage, integrate with weather API
        return ToolResult(
            success=True,
            data={
                "location": location,
                "temperature": "22°C",
                "condition": "Partly cloudy",
                "humidity": "65%",
                "wind": "10 km/h"
            },
            metadata={"source": "placeholder", "timestamp": time.time()}
        )
    
    def parse_voice_parameters(self, voice_text: str) -> Dict[str, Any]:
        """Parse location from voice weather command."""
        params = {}
        voice_lower = voice_text.lower()
        
        # Patterns to extract location
        patterns = [
            r"weather (?:in |for |at )?(.+)",
            r"temperature (?:in |for |at )?(.+)",
            r"(?:how'?s the weather|weather forecast) (?:in |for |at )?(.+)",
            r"what'?s the weather like (?:in |for |at )?(.+)"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, voice_lower)
            if match:
                location = match.group(1).strip()
                if location and location not in ["today", "now", "currently"]:
                    params["location"] = location
                break
        
        return params
    
    def format_voice_response(self, data: Any, voice_context: VoiceToolContext) -> str:
        """Format weather information for voice output."""
        if not data:
            return "I couldn't get weather information."
        
        location = data.get("location", "your area")
        temp = data.get("temperature", "unknown temperature")
        condition = data.get("condition", "unknown conditions")
        
        return f"The weather in {location} is currently {condition} with a temperature of {temp}."

class TimeTool(BaseTool):
    def __init__(self):
        super().__init__("time", "Get current time and date")
        self.voice_aliases = ["current time", "what time is it", "time now", "date"]
    
    def execute(self, **kwargs) -> ToolResult:
        now = datetime.datetime.now()
        return ToolResult(
            success=True,
            data={
                "current_time": now.strftime("%H:%M:%S"),
                "current_date": now.strftime("%Y-%m-%d"),
                "formatted": now.strftime("%A, %B %d, %Y at %I:%M %p"),
                "timezone": str(now.astimezone().tzinfo)
            }
        )
    
    def parse_voice_parameters(self, voice_text: str) -> Dict[str, Any]:
        """Parse time-related parameters from voice command."""
        # Time tool doesn't typically need parameters, but we can parse timezone requests
        params = {}
        voice_lower = voice_text.lower()
        
        # Check for timezone requests
        timezone_patterns = [
            r"time in (.+)",
            r"what time is it in (.+)",
            r"current time in (.+)"
        ]
        
        for pattern in timezone_patterns:
            match = re.search(pattern, voice_lower)
            if match:
                location = match.group(1).strip()
                if location:
                    params["timezone_location"] = location
                break
        
        return params
    
    def format_voice_response(self, data: Any, voice_context: VoiceToolContext) -> str:
        """Format time information for voice output."""
        if not data:
            return "I couldn't get the current time."
        
        formatted_time = data.get("formatted", "unknown time")
        return f"The current time is {formatted_time}."

class CalculatorTool(BaseTool):
    def __init__(self):
        super().__init__("calculator", "Perform mathematical calculations")
        self.voice_aliases = ["calculate", "math", "compute", "what is"]
    
    def execute(self, expression: str = "", **kwargs) -> ToolResult:
        if not expression:
            return ToolResult(
                success=False,
                error="Mathematical expression is required"
            )
        
        try:
            # Simple eval with safety checks
            allowed_chars = set("0123456789+-*/.() ")
            if not all(c in allowed_chars for c in expression):
                return ToolResult(
                    success=False,
                    error="Expression contains invalid characters"
                )
            
            # Basic safety check for function calls
            if any(func in expression for func in ["import", "eval", "exec", "__"]):
                return ToolResult(
                    success=False,
                    error="Expression contains forbidden operations"
                )
            
            result = eval(expression)
            return ToolResult(
                success=True,
                data={
                    "expression": expression,
                    "result": result,
                    "formatted": f"{expression} = {result}"
                }
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Calculation error: {str(e)}"
            )
    
    def parse_voice_parameters(self, voice_text: str) -> Dict[str, Any]:
        """Parse mathematical expression from voice command."""
        params = {}
        voice_lower = voice_text.lower()
        
        # Patterns to extract mathematical expressions
        patterns = [
            r"calculate (.+)",
            r"what is (.+)",
            r"compute (.+)",
            r"math (.+)",
            r"(.+) equals?",
            r"(.+) is?"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, voice_lower)
            if match:
                expression = match.group(1).strip()
                # Convert spoken math to symbols
                expression = self._convert_spoken_math(expression)
                if expression:
                    params["expression"] = expression
                break
        
        return params
    
    def _convert_spoken_math(self, spoken: str) -> str:
        """Convert spoken mathematical expressions to symbolic form."""
        # Basic conversions for common spoken math
        conversions = {
            "plus": "+",
            "add": "+",
            "minus": "-",
            "subtract": "-",
            "times": "*",
            "multiply": "*",
            "multiplied by": "*",
            "divide": "/",
            "divided by": "/",
            "squared": "**2",
            "cubed": "**3",
            "to the power of": "**",
            "percent": "/100"
        }
        
        result = spoken.lower()
        for word, symbol in conversions.items():
            result = result.replace(word, symbol)
        
        # Clean up extra spaces
        result = " ".join(result.split())
        
        return result
    
    def format_voice_response(self, data: Any, voice_context: VoiceToolContext) -> str:
        """Format calculation result for voice output."""
        if not data:
            return "I couldn't perform the calculation."
        
        expression = data.get("expression", "")
        result = data.get("result", "")
        
        if expression and result is not None:
            return f"{expression} equals {result}."
        elif result is not None:
            return f"The result is {result}."
        else:
            return "The calculation completed successfully."

class TimerTool(BaseTool):
    def __init__(self):
        super().__init__("timer", "Set a timer for a specified duration")
        self.active_timers = {}
        self.voice_aliases = ["set timer", "timer", "countdown", "remind me"]
        
        # Enable advanced parameter collection for this tool
        if ParameterSpec and ParameterType:
            self.supports_parameter_collection = True
            self.parameter_specs = [
                ParameterSpec(
                    name="duration",
                    param_type=ParameterType.INTEGER,
                    required=True,
                    description="How long should the timer run?",
                    voice_prompts=[
                        "How long should the timer run? Please specify in minutes.",
                        "What duration would you like for the timer?"
                    ],
                    validation_rules={
                        "min_value": 1,
                        "max_value": 1440  # 24 hours in minutes
                    },
                    confirmation_required=False
                ),
                ParameterSpec(
                    name="unit",
                    param_type=ParameterType.CHOICE,
                    required=False,
                    description="Time unit for the timer",
                    choices=["second", "minute", "hour"],
                    default_value="minute",
                    voice_prompts=[
                        "What time unit? Say seconds, minutes, or hours."
                    ],
                    confirmation_required=False
                ),
                ParameterSpec(
                    name="label",
                    param_type=ParameterType.STRING,
                    required=False,
                    description="Optional label for the timer",
                    voice_prompts=[
                        "Would you like to add a label for this timer? Or say skip to continue."
                    ],
                    confirmation_required=False
                )
            ]
    
    def execute(self, duration: int = 5, unit: str = "minute", **kwargs) -> ToolResult:
        if duration <= 0:
            return ToolResult(
                success=False,
                error="Duration must be positive"
            )
        
        # Convert to seconds
        multipliers = {
            "second": 1,
            "minute": 60,
            "hour": 3600
        }
        
        if unit not in multipliers:
            return ToolResult(
                success=False,
                error=f"Invalid time unit: {unit}. Use second, minute, or hour"
            )
        
        total_seconds = duration * multipliers[unit]
        timer_id = f"timer_{int(time.time())}"
        end_time = time.time() + total_seconds
        
        self.active_timers[timer_id] = {
            "duration": duration,
            "unit": unit,
            "total_seconds": total_seconds,
            "end_time": end_time,
            "started_at": time.time()
        }
        
        return ToolResult(
            success=True,
            data={
                "timer_id": timer_id,
                "duration": duration,
                "unit": unit,
                "total_seconds": total_seconds,
                "message": f"Timer set for {duration} {unit}{'s' if duration > 1 else ''}"
            }
        )
    
    def check_timer(self, timer_id: str) -> ToolResult:
        if timer_id not in self.active_timers:
            return ToolResult(
                success=False,
                error="Timer not found"
            )
        
        timer = self.active_timers[timer_id]
        current_time = time.time()
        remaining = timer["end_time"] - current_time
        
        if remaining <= 0:
            del self.active_timers[timer_id]
            return ToolResult(
                success=True,
                data={
                    "timer_id": timer_id,
                    "status": "completed",
                    "message": "Timer has finished!"
                }
            )
        
        return ToolResult(
            success=True,
            data={
                "timer_id": timer_id,
                "status": "running",
                "remaining_seconds": int(remaining),
                "remaining_formatted": f"{int(remaining // 60)}:{int(remaining % 60):02d}"
            }
        )
    
    def parse_voice_parameters(self, voice_text: str) -> Dict[str, Any]:
        """Parse timer duration from voice command."""
        params = {}
        voice_lower = voice_text.lower()
        
        # Patterns to extract timer duration and unit
        patterns = [
            r"set timer for (\d+) (second|minute|hour)s?",
            r"timer for (\d+) (second|minute|hour)s?",
            r"countdown (\d+) (second|minute|hour)s?",
            r"remind me in (\d+) (second|minute|hour)s?",
            r"(\d+) (second|minute|hour) timer",
            r"timer (\d+) (second|minute|hour)s?"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, voice_lower)
            if match:
                duration = int(match.group(1))
                unit = match.group(2)
                params["duration"] = duration
                params["unit"] = unit
                break
        
        # If no specific pattern matched, try to extract just numbers
        if not params:
            number_match = re.search(r"(\d+)", voice_lower)
            if number_match:
                duration = int(number_match.group(1))
                # Default to minutes for voice commands
                params["duration"] = duration
                params["unit"] = "minute"
        
        return params
    
    def format_voice_response(self, data: Any, voice_context: VoiceToolContext) -> str:
        """Format timer result for voice output."""
        if not data:
            return "I couldn't set the timer."
        
        if "message" in data:
            return data["message"]
        
        duration = data.get("duration", "")
        unit = data.get("unit", "")
        
        if duration and unit:
            unit_plural = f"{unit}s" if duration > 1 else unit
            return f"Timer set for {duration} {unit_plural}."
        
        return "Timer has been set successfully."