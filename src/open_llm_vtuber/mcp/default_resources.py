"""
Default resources for MCP integration.

This module provides default resources that can be registered with the MCP client.
"""

from typing import Dict, List, Any, Optional
from .resource import Resource


def create_user_preferences_resource(
    character_config: Any,
) -> Resource:
    """
    Create a resource for user preferences.
    
    Args:
        character_config: The character configuration
        
    Returns:
        A Resource object containing user preferences
    """
    # Extract relevant preferences from character config
    preferences = {
        "character_name": character_config.character_name,
        "human_name": character_config.human_name,
        "language": "en",  # Default language
    }
    
    # Add TTS preferences if available
    if hasattr(character_config, "tts_config"):
        tts_config = character_config.tts_config
        tts_model = tts_config.tts_model.lower()
        
        if tts_model == "edge_tts" and hasattr(tts_config, "edge_tts"):
            preferences["voice"] = tts_config.edge_tts.voice
        elif tts_model == "azure_tts" and hasattr(tts_config, "azure_tts"):
            preferences["voice"] = tts_config.azure_tts.voice
    
    # Create and return the resource
    return Resource(
        name="user_preferences",
        type="preferences",
        data=preferences,
        description="User preferences for the Vtuber application",
    )


def create_chat_history_resource(
    history: List[Dict[str, Any]],
    max_entries: int = 10,
) -> Resource:
    """
    Create a resource for chat history.
    
    Args:
        history: The chat history
        max_entries: Maximum number of entries to include
        
    Returns:
        A Resource object containing chat history
    """
    # Filter out system messages and limit to max_entries
    filtered_history = [
        msg for msg in history if msg.get("role") != "system"
    ][-max_entries:]
    
    # Create and return the resource
    return Resource(
        name="chat_history",
        type="conversation",
        data=filtered_history,
        description="Recent conversation history",
    )


def create_live2d_info_resource(
    live2d_model: Any,
) -> Resource:
    """
    Create a resource for Live2D model information.
    
    Args:
        live2d_model: The Live2D model
        
    Returns:
        A Resource object containing Live2D model information
    """
    # Extract relevant information from Live2D model
    model_info = {
        "name": live2d_model.model_info.get("name", "Unknown"),
        "expressions": live2d_model.expressions,
        "motions": live2d_model.motions,
    }
    
    # Create and return the resource
    return Resource(
        name="live2d_model",
        type="model_info",
        data=model_info,
        description="Information about the Live2D model",
    )


def create_platform_info_resource() -> Resource:
    """
    Create a resource for platform information.
    
    Returns:
        A Resource object containing platform information
    """
    # Platform information
    platform_info = {
        "name": "Open LLM Vtuber",
        "version": "1.0.0",  # This should be dynamically determined
        "capabilities": [
            "text_to_speech",
            "speech_to_text",
            "live2d_animation",
            "emotion_detection",
        ],
    }
    
    # Create and return the resource
    return Resource(
        name="platform_info",
        type="system_info",
        data=platform_info,
        description="Information about the platform",
    )
