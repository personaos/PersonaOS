from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass
from abc import ABC, abstractmethod
import traceback
import logging

@dataclass
class ToolResult:
    success: bool
    data: Any = None
    error: Optional[str] = None
    metadata: Optional[Dict] = None

class BaseTool(ABC):
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.logger = logging.getLogger(f"tool.{name}")
    
    @abstractmethod
    def execute(self, **kwargs) -> ToolResult:
        pass
    
    def validate_args(self, **kwargs) -> bool:
        return True

class ToolRegistry:
    def __init__(self):
        self.tools: Dict[str, BaseTool] = {}
        self.logger = logging.getLogger("tool_registry")
        self._register_default_tools()
    
    def register_tool(self, tool: BaseTool):
        self.tools[tool.name] = tool
        self.logger.info(f"Registered tool: {tool.name}")
    
    def get_tool(self, name: str) -> Optional[BaseTool]:
        return self.tools.get(name)
    
    def list_tools(self) -> List[str]:
        return list(self.tools.keys())
    
    def execute_tool(self, name: str, **kwargs) -> ToolResult:
        tool = self.get_tool(name)
        if not tool:
            return ToolResult(
                success=False,
                error=f"Tool '{name}' not found"
            )
        
        try:
            if not tool.validate_args(**kwargs):
                return ToolResult(
                    success=False,
                    error=f"Invalid arguments for tool '{name}'"
                )
            
            self.logger.info(f"Executing tool: {name} with args: {kwargs}")
            result = tool.execute(**kwargs)
            self.logger.info(f"Tool {name} completed successfully: {result.success}")
            return result
            
        except Exception as e:
            error_msg = f"Error executing tool '{name}': {str(e)}"
            self.logger.error(f"{error_msg}\n{traceback.format_exc()}")
            return ToolResult(
                success=False,
                error=error_msg
            )
    
    def _register_default_tools(self):
        from .basic_tools import (
            WebSearchTool, WeatherTool, TimeTool, 
            CalculatorTool, TimerTool
        )
        
        default_tools = [
            WebSearchTool(),
            WeatherTool(),
            TimeTool(),
            CalculatorTool(),
            TimerTool()
        ]
        
        for tool in default_tools:
            self.register_tool(tool)