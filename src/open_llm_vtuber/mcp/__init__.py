"""
Model Context Protocol (MCP) implementation for Open LLM Vtuber.

This package provides the MCP client implementation and related utilities
for integrating with MCP-compliant servers.
"""

from .client import MCPClient
from .config import MCPConfig, MCPServerConfig
from .resource import Resource
from .tool import Tool

__all__ = [
    "MCPClient",
    "MCPConfig",
    "MCPServerConfig",
    "Resource",
    "Tool",
]
