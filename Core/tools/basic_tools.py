import time
import datetime
import requests
import json
from typing import Dict, Any
from .tool_registry import BaseTool, ToolResult

class WebSearchTool(BaseTool):
    def __init__(self):
        super().__init__("web_search", "Search the web for information")
    
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

class WeatherTool(BaseTool):
    def __init__(self):
        super().__init__("weather", "Get weather information for a location")
    
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

class TimeTool(BaseTool):
    def __init__(self):
        super().__init__("time", "Get current time and date")
    
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

class CalculatorTool(BaseTool):
    def __init__(self):
        super().__init__("calculator", "Perform mathematical calculations")
    
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

class TimerTool(BaseTool):
    def __init__(self):
        super().__init__("timer", "Set a timer for a specified duration")
        self.active_timers = {}
    
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