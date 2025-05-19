"""
MCP client implementation.

This module provides the core MCP client implementation for connecting to
MCP-compliant servers and managing resources and tools.
"""

import asyncio
import json
import uuid
from typing import Any, Dict, List, Optional, Union, Callable
import aiohttp
from loguru import logger

from .config import MCPConfig, MCPServerConfig
from .resource import Resource, ResourceManager
from .tool import Tool, ToolManager


class MCPClient:
    """
    Model Context Protocol (MCP) client implementation.
    
    This class provides methods for connecting to MCP-compliant servers,
    registering resources and tools, and handling MCP requests and responses.
    """

    def __init__(self, config: MCPConfig):
        """
        Initialize the MCP client.
        
        Args:
            config: The MCP configuration
        """
        self.config = config
        self.resource_manager = ResourceManager()
        self.tool_manager = ToolManager()
        self.server_connections: Dict[str, Dict[str, Any]] = {}
        self.session: Optional[aiohttp.ClientSession] = None
        self._initialized = False

    async def initialize(self) -> None:
        """
        Initialize the MCP client and establish connections to servers.
        """
        if self._initialized:
            return

        if not self.config.enabled:
            logger.info("MCP integration is disabled")
            return

        self.session = aiohttp.ClientSession()
        
        # Initialize connections to all enabled servers
        for server_config in self.config.servers:
            if server_config.enabled:
                try:
                    await self._connect_to_server(server_config)
                except Exception as e:
                    logger.error(f"Failed to connect to MCP server {server_config.name}: {e}")
        
        self._initialized = True
        logger.info(f"MCP client initialized with {len(self.server_connections)} server connections")

    async def shutdown(self) -> None:
        """
        Shutdown the MCP client and close all connections.
        """
        if self.session:
            await self.session.close()
            self.session = None
        
        self.server_connections = {}
        self._initialized = False
        logger.info("MCP client shut down")

    async def _connect_to_server(self, server_config: MCPServerConfig) -> None:
        """
        Connect to an MCP server and perform capability negotiation.
        
        Args:
            server_config: The server configuration
            
        Raises:
            ConnectionError: If the connection fails
        """
        if not self.session:
            raise RuntimeError("MCP client not initialized")
        
        logger.info(f"Connecting to MCP server: {server_config.name} at {server_config.url}")
        
        # Prepare headers
        headers = {"Content-Type": "application/json"}
        if server_config.api_key:
            headers["Authorization"] = f"Bearer {server_config.api_key}"
        
        # Perform capability negotiation
        try:
            async with self.session.post(
                f"{server_config.url}/capabilities",
                headers=headers,
                json={"client_version": "1.0.0"},
                timeout=self.config.default_timeout
            ) as response:
                if response.status != 200:
                    raise ConnectionError(f"Failed to negotiate capabilities: {response.status}")
                
                capabilities = await response.json()
                
                self.server_connections[server_config.name] = {
                    "config": server_config,
                    "capabilities": capabilities,
                    "headers": headers
                }
                
                logger.info(f"Connected to MCP server {server_config.name} with capabilities: {capabilities}")
        except Exception as e:
            logger.error(f"Failed to connect to MCP server {server_config.name}: {e}")
            raise ConnectionError(f"Failed to connect to MCP server {server_config.name}: {e}")

    def register_resource(self, resource: Resource) -> None:
        """
        Register a resource with the MCP client.
        
        Args:
            resource: The resource to register
        """
        self.resource_manager.register(resource)
        logger.debug(f"Registered MCP resource: {resource.name}")

    def register_tool(self, tool: Tool) -> None:
        """
        Register a tool with the MCP client.
        
        Args:
            tool: The tool to register
        """
        self.tool_manager.register(tool)
        logger.debug(f"Registered MCP tool: {tool.name}")

    async def invoke_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        """
        Invoke a tool by name.
        
        Args:
            tool_name: The name of the tool to invoke
            parameters: The parameters to pass to the tool
            
        Returns:
            The result of the tool invocation
            
        Raises:
            KeyError: If the tool does not exist
            ConnectionError: If the server connection fails
        """
        if not self._initialized:
            raise RuntimeError("MCP client not initialized")
        
        try:
            tool = self.tool_manager.get(tool_name)
        except KeyError:
            logger.error(f"Tool not found: {tool_name}")
            raise
        
        # If the tool has a local handler, use it
        if tool.handler:
            logger.debug(f"Invoking local tool: {tool_name}")
            return await tool.handler(**parameters)
        
        # Otherwise, invoke the tool on the server
        if not tool.server_name or tool.server_name not in self.server_connections:
            raise ConnectionError(f"No server connection for tool: {tool_name}")
        
        server_conn = self.server_connections[tool.server_name]
        
        if not self.session:
            raise RuntimeError("MCP client not initialized")
        
        logger.debug(f"Invoking remote tool: {tool_name} on server {tool.server_name}")
        
        request_id = str(uuid.uuid4())
        
        try:
            async with self.session.post(
                f"{server_conn['config'].url}/tools/{tool_name}",
                headers=server_conn["headers"],
                json={"request_id": request_id, "parameters": parameters},
                timeout=self.config.default_timeout
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise ConnectionError(f"Tool invocation failed: {response.status} - {error_text}")
                
                result = await response.json()
                return result.get("result")
        except Exception as e:
            logger.error(f"Failed to invoke tool {tool_name}: {e}")
            raise ConnectionError(f"Failed to invoke tool {tool_name}: {e}")

    def get_resources_for_prompt(self) -> Dict[str, Any]:
        """
        Get all resources formatted for inclusion in an LLM prompt.
        
        Returns:
            A dictionary of resources formatted for the LLM
        """
        return self.resource_manager.to_dict()

    def get_tools_for_prompt(self) -> Dict[str, Any]:
        """
        Get all tools formatted for inclusion in an LLM prompt.
        
        Returns:
            A dictionary of tools formatted for the LLM
        """
        return self.tool_manager.to_dict()
