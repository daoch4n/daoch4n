"""
Tool implementation for MCP.

Tools allow the LLM to perform actions in the real world.
"""

from typing import Any, Callable, Dict, List, Optional, Union
from pydantic import BaseModel, Field


class ToolParameter(BaseModel):
    """
    A parameter for an MCP tool.
    """

    name: str
    type: str
    description: str
    required: bool = False
    default: Optional[Any] = None


class Tool(BaseModel):
    """
    A tool in the MCP protocol.
    
    Tools allow the LLM to perform actions in the real world, such as
    triggering animations, playing sounds, or fetching data.
    """

    name: str
    description: str
    parameters: List[ToolParameter] = Field(default_factory=list)
    handler: Optional[Callable] = None
    server_name: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert the tool to a dictionary for JSON serialization."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": [
                {
                    "name": param.name,
                    "type": param.type,
                    "description": param.description,
                    "required": param.required,
                    **({"default": param.default} if param.default is not None else {})
                }
                for param in self.parameters
            ]
        }


class ToolManager:
    """
    Manages tools for the MCP client.
    
    This class provides methods for registering and retrieving tools.
    """

    def __init__(self):
        self._tools: Dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        """
        Register a new tool.
        
        Args:
            tool: The tool to register
        """
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool:
        """
        Get a tool by name.
        
        Args:
            name: The name of the tool to get
            
        Returns:
            The requested tool
            
        Raises:
            KeyError: If the tool does not exist
        """
        if name not in self._tools:
            raise KeyError(f"Tool '{name}' not found")
        
        return self._tools[name]

    def list(self) -> List[Tool]:
        """
        List all registered tools.
        
        Returns:
            A list of all registered tools
        """
        return list(self._tools.values())

    def to_dict(self) -> Dict[str, Dict[str, Any]]:
        """
        Convert all tools to a dictionary for JSON serialization.
        
        Returns:
            A dictionary of tool dictionaries
        """
        return {name: tool.to_dict() for name, tool in self._tools.items()}
