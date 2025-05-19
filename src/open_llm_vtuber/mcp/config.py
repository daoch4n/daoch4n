"""
Configuration models for MCP integration.
"""

from pydantic import BaseModel, Field
from typing import Dict, List, Optional, ClassVar, Literal

from ..config_manager.i18n import I18nMixin, Description


class MCPServerConfig(I18nMixin, BaseModel):
    """Configuration for an MCP server connection."""

    name: str = Field(..., alias="name")
    url: str = Field(..., alias="url")
    api_key: Optional[str] = Field(None, alias="api_key")
    enabled: bool = Field(True, alias="enabled")
    server_type: Literal["animation", "voice", "data", "custom"] = Field(
        ..., alias="server_type"
    )
    description: Optional[str] = Field(None, alias="description")

    DESCRIPTIONS: ClassVar[Dict[str, Description]] = {
        "name": Description(
            en="Name of the MCP server", zh="MCP 服务器名称"
        ),
        "url": Description(
            en="URL of the MCP server", zh="MCP 服务器 URL"
        ),
        "api_key": Description(
            en="API key for the MCP server (if required)", zh="MCP 服务器 API 密钥（如果需要）"
        ),
        "enabled": Description(
            en="Whether this MCP server is enabled", zh="是否启用此 MCP 服务器"
        ),
        "server_type": Description(
            en="Type of MCP server (animation, voice, data, or custom)",
            zh="MCP 服务器类型（动画、语音、数据或自定义）"
        ),
        "description": Description(
            en="Description of the MCP server", zh="MCP 服务器描述"
        ),
    }


class MCPConfig(I18nMixin, BaseModel):
    """Configuration for MCP integration."""

    enabled: bool = Field(False, alias="enabled")
    servers: List[MCPServerConfig] = Field(default_factory=list, alias="servers")
    default_timeout: float = Field(10.0, alias="default_timeout")
    user_consent_required: bool = Field(True, alias="user_consent_required")

    DESCRIPTIONS: ClassVar[Dict[str, Description]] = {
        "enabled": Description(
            en="Whether MCP integration is enabled", zh="是否启用 MCP 集成"
        ),
        "servers": Description(
            en="List of MCP servers to connect to", zh="要连接的 MCP 服务器列表"
        ),
        "default_timeout": Description(
            en="Default timeout for MCP requests in seconds", zh="MCP 请求的默认超时时间（秒）"
        ),
        "user_consent_required": Description(
            en="Whether user consent is required for tool execution",
            zh="是否需要用户同意才能执行工具"
        ),
    }
