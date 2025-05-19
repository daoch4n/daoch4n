"""
Default tools for MCP integration.

This module provides default tools that can be registered with the MCP client.
"""

from typing import Dict, Any, List, Optional
from .tool import Tool, ToolParameter


def create_expression_tool(live2d_model: Any) -> Tool:
    """
    Create a tool for triggering Live2D expressions.
    
    Args:
        live2d_model: The Live2D model
        
    Returns:
        A Tool object for triggering expressions
    """
    # Get available expressions from the model
    available_expressions = live2d_model.expressions if live2d_model else []
    
    # Create the tool
    return Tool(
        name="set_expression",
        description=f"Set the Live2D character's facial expression. Available expressions: {', '.join(available_expressions)}",
        parameters=[
            ToolParameter(
                name="expression",
                type="string",
                description="The expression to set",
                required=True,
            ),
            ToolParameter(
                name="duration",
                type="number",
                description="Duration in seconds to hold the expression (default: 3)",
                required=False,
                default=3,
            ),
        ],
        handler=None,  # Will be set by the service context
    )


def create_motion_tool(live2d_model: Any) -> Tool:
    """
    Create a tool for triggering Live2D motions.
    
    Args:
        live2d_model: The Live2D model
        
    Returns:
        A Tool object for triggering motions
    """
    # Get available motions from the model
    available_motions = live2d_model.motions if live2d_model else []
    
    # Create the tool
    return Tool(
        name="play_motion",
        description=f"Play a motion animation on the Live2D character. Available motions: {', '.join(available_motions)}",
        parameters=[
            ToolParameter(
                name="motion",
                type="string",
                description="The motion to play",
                required=True,
            ),
            ToolParameter(
                name="loop",
                type="boolean",
                description="Whether to loop the motion (default: false)",
                required=False,
                default=False,
            ),
        ],
        handler=None,  # Will be set by the service context
    )


def create_weather_tool() -> Tool:
    """
    Create a tool for fetching weather information.
    
    Returns:
        A Tool object for fetching weather
    """
    return Tool(
        name="get_weather",
        description="Get current weather information for a location",
        parameters=[
            ToolParameter(
                name="location",
                type="string",
                description="The location to get weather for (city name or coordinates)",
                required=True,
            ),
            ToolParameter(
                name="units",
                type="string",
                description="Units to use (metric, imperial, or standard)",
                required=False,
                default="metric",
            ),
        ],
        handler=None,  # Will be set by the service context
        server_name="data_server",  # This tool will be handled by the data server
    )


def create_search_tool() -> Tool:
    """
    Create a tool for searching the web.
    
    Returns:
        A Tool object for web search
    """
    return Tool(
        name="web_search",
        description="Search the web for information",
        parameters=[
            ToolParameter(
                name="query",
                type="string",
                description="The search query",
                required=True,
            ),
            ToolParameter(
                name="num_results",
                type="integer",
                description="Number of results to return (default: 3)",
                required=False,
                default=3,
            ),
        ],
        handler=None,  # Will be set by the service context
        server_name="data_server",  # This tool will be handled by the data server
    )
