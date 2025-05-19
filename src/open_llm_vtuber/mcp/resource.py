"""
Resource implementation for MCP.

Resources provide contextual information to the LLM.
"""

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel


class Resource(BaseModel):
    """
    A resource in the MCP protocol.
    
    Resources provide contextual information to the LLM, such as user preferences,
    chat history, or live stream metrics.
    """

    name: str
    type: str
    data: Any
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert the resource to a dictionary for JSON serialization."""
        result = {
            "name": self.name,
            "type": self.type,
            "data": self.data,
        }
        
        if self.description:
            result["description"] = self.description
            
        if self.metadata:
            result["metadata"] = self.metadata
            
        return result


class ResourceManager:
    """
    Manages resources for the MCP client.
    
    This class provides methods for registering, updating, and retrieving resources.
    """

    def __init__(self):
        self._resources: Dict[str, Resource] = {}

    def register(self, resource: Resource) -> None:
        """
        Register a new resource.
        
        Args:
            resource: The resource to register
        """
        self._resources[resource.name] = resource

    def update(self, name: str, data: Any) -> None:
        """
        Update an existing resource's data.
        
        Args:
            name: The name of the resource to update
            data: The new data for the resource
        
        Raises:
            KeyError: If the resource does not exist
        """
        if name not in self._resources:
            raise KeyError(f"Resource '{name}' not found")
        
        self._resources[name].data = data

    def get(self, name: str) -> Resource:
        """
        Get a resource by name.
        
        Args:
            name: The name of the resource to get
            
        Returns:
            The requested resource
            
        Raises:
            KeyError: If the resource does not exist
        """
        if name not in self._resources:
            raise KeyError(f"Resource '{name}' not found")
        
        return self._resources[name]

    def list(self) -> List[Resource]:
        """
        List all registered resources.
        
        Returns:
            A list of all registered resources
        """
        return list(self._resources.values())

    def to_dict(self) -> Dict[str, Dict[str, Any]]:
        """
        Convert all resources to a dictionary for JSON serialization.
        
        Returns:
            A dictionary of resource dictionaries
        """
        return {name: resource.to_dict() for name, resource in self._resources.items()}
