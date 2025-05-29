"""
This module contains the pydantic model for the configurations of
different types of agents.
"""

from pydantic import BaseModel, Field
import os
from typing import Dict, ClassVar, Optional, Literal, List, Any
from .i18n import I18nMixin, Description
from .stateless_llm import StatelessLLMConfigs

# ======== Configurations for different Agents ========


class BasicMemoryAgentConfig(I18nMixin, BaseModel):
    """Configuration for the basic memory agent."""

    llm_provider: Literal[
        "openai_compatible_llm",
        "claude_llm",
        "llama_cpp_llm",
        "ollama_llm",
        "openai_llm",
        "gemini_llm",
        "zhipu_llm",
        "deepseek_llm",
        "groq_llm",
        "mistral_llm",
    ] = Field(..., alias="llm_provider")

    faster_first_response: Optional[bool] = Field(True, alias="faster_first_response")
    segment_method: Literal["regex", "pysbd"] = Field("pysbd", alias="segment_method")
    DESCRIPTIONS: ClassVar[Dict[str, Description]] = {
        "llm_provider": Description(notes=None,
            en="LLM provider to use for this agent",
            zh="Basic Memory Agent 智能体使用的大语言模型选项",
        ),
        "faster_first_response": Description(notes=None,
            en="Whether to respond as soon as encountering a comma in the first sentence to reduce latency (default: True)",
            zh="是否在第一句回应时遇上逗号就直接生成音频以减少首句延迟（默认：True）",
        ),
        "segment_method": Description(notes=None,
            en="Method for segmenting sentences: 'regex' or 'pysbd' (default: 'pysbd')",
            zh="分割句子的方法：'regex' 或 'pysbd'（默认：'pysbd'）",
        ),
    }


class Mem0VectorStoreConfig(I18nMixin, BaseModel):
    """Configuration for Mem0 vector store."""

    provider: str = Field(..., alias="provider")
    config: Dict = Field(..., alias="config")

    DESCRIPTIONS: ClassVar[Dict[str, Description]] = {
        "provider": Description(notes=None,
            en="Vector store provider (e.g., qdrant)", zh="向量存储提供者（如 qdrant）"
        ),
        "config": Description(notes=None,
            en="Provider-specific configuration", zh="提供者特定配置"
        ),
    }


class Mem0LLMConfig(I18nMixin, BaseModel):
    """Configuration for Mem0 LLM."""

    provider: str = Field(..., alias="provider")
    config: Dict = Field(..., alias="config")

    DESCRIPTIONS: ClassVar[Dict[str, Description]] = {
        "provider": Description(notes=None,en="LLM provider name", zh="语言模型提供者名称"),
        "config": Description(notes=None,
            en="Provider-specific configuration", zh="提供者特定配置"
        ),
    }


class Mem0EmbedderConfig(I18nMixin, BaseModel):
    """Configuration for Mem0 embedder."""

    provider: str = Field(..., alias="provider")
    config: Dict = Field(..., alias="config")

    DESCRIPTIONS: ClassVar[Dict[str, Description]] = {
        "provider": Description(notes=None,en="Embedder provider name", zh="嵌入模型提供者名称"),
        "config": Description(notes=None,
            en="Provider-specific configuration", zh="提供者特定配置"
        ),
    }


class Mem0Config(I18nMixin, BaseModel):
    """Configuration for Mem0."""

    vector_store: Mem0VectorStoreConfig = Field(..., alias="vector_store")
    llm: Mem0LLMConfig = Field(..., alias="llm")
    embedder: Mem0EmbedderConfig = Field(..., alias="embedder")

    DESCRIPTIONS: ClassVar[Dict[str, Description]] = {
        "vector_store": Description(notes=None,en="Vector store configuration", zh="向量存储配置"),
        "llm": Description(notes=None,en="LLM configuration", zh="语言模型配置"),
        "embedder": Description(notes=None,en="Embedder configuration", zh="嵌入模型配置"),
    }


# =================================


class HumeAIConfig(I18nMixin, BaseModel):
    """Configuration for the Hume AI agent."""

    api_key: str = Field(os.getenv("GEMINI_API_KEY", ""), alias="api_key")
    host: str = Field("api.hume.ai", alias="host")
    config_id: Optional[str] = Field(None, alias="config_id")
    idle_timeout: int = Field(15, alias="idle_timeout")

    DESCRIPTIONS: ClassVar[Dict[str, Description]] = {
        "api_key": Description(notes=None,
            en="API key for Hume AI service", zh="Hume AI 服务的 API 密钥"
        ),
        "host": Description(notes=None,
            en="Host URL for Hume AI service (default: api.hume.ai)",
            zh="Hume AI 服务的主机地址（默认：api.hume.ai）",
        ),
        "config_id": Description(notes=None,
            en="Configuration ID for EVI settings", zh="EVI 配置 ID"
        ),
        "idle_timeout": Description(notes=None,
            en="Idle timeout in seconds before disconnecting (default: 15)",
            zh="空闲超时断开连接的秒数（默认：15）",
        ),
    }


class GeminiLiveConfig(I18nMixin, BaseModel):
    """Configuration for the Gemini Live agent."""

    api_key: str = Field(os.getenv("GEMINI_API_KEY", ""), alias="api_key")
    model_name: str = Field("gemini-2.0-flash-live-001", alias="model_name")  # This model ONLY supports bidiGenerateContent (Live API), not generateContent
    language_code: str = Field("en-US", alias="language_code")
    voice_name: Optional[str] = Field("Kore", alias="voice_name")
    system_instruction: Optional[str] = Field(None, alias="system_instruction")
    start_of_speech_sensitivity: Optional[Literal[
        "START_SENSITIVITY_UNSPECIFIED",
        "START_SENSITIVITY_LOW",
        "START_SENSITIVITY_MEDIUM",
        "START_SENSITIVITY_HIGH"
    ]] = Field(None, alias="start_of_speech_sensitivity")
    end_of_speech_sensitivity: Optional[Literal[
        "END_SENSITIVITY_UNSPECIFIED",
        "END_SENSITIVITY_LOW",
        "END_SENSITIVITY_MEDIUM",
        "END_SENSITIVITY_HIGH"
    ]] = Field(None, alias="end_of_speech_sensitivity")
    prefix_padding_ms: Optional[int] = Field(None, alias="prefix_padding_ms")
    silence_duration_ms: Optional[int] = Field(None, alias="silence_duration_ms")

    # Tool configurations
    enable_function_calling: bool = Field(False, alias="enable_function_calling")
    function_declarations: Optional[List[Dict[str, Any]]] = Field(None, alias="function_declarations")
    enable_code_execution: bool = Field(False, alias="enable_code_execution")
    enable_google_search: bool = Field(False, alias="enable_google_search")

    # Context window compression
    enable_context_compression: bool = Field(True, alias="enable_context_compression")
    compression_window_size: int = Field(10, alias="compression_window_size")
    compression_token_threshold: int = Field(4000, alias="compression_token_threshold")

    # Audio transcription
    enable_input_audio_transcription: bool = Field(True, alias="enable_input_audio_transcription")

    # Manual VAD control
    disable_automatic_vad: bool = Field(False, alias="disable_automatic_vad")

    # Emotion tag handling approach
    use_dual_prompt_system: bool = Field(False, alias="use_dual_prompt_system")

    DESCRIPTIONS: ClassVar[Dict[str, Description]] = {
        "api_key": Description(notes=None,
            en="Gemini API Key", zh="Gemini API 密钥"
        ),
        "model_name": Description(notes=None,
            en="Gemini Live Model Name (use gemini-2.0-flash-live-001 for Live API). Live models ONLY support bidiGenerateContent, not generateContent.",
            zh="Gemini Live 模型名称 (使用 gemini-2.0-flash-live-001 用于 Live API). Live 模型只支持 bidiGenerateContent，不支持 generateContent。"
        ),
        "language_code": Description(notes=None,
            en="Language code for speech (e.g., en-US, ja-JP)",
            zh="语音语言代码 (例如 en-US, ja-JP)"
        ),
        "voice_name": Description(notes=None,
            en="Gemini voice name (e.g., Puck, Kore)",
            zh="Gemini 语音名称 (例如 Puck, Kore)"
        ),
        "system_instruction": Description(notes=None,
            en="System instruction/persona for Gemini",
            zh="给 Gemini 的系统指令/角色设定"
        ),
        "start_of_speech_sensitivity": Description(notes=None,
            en="VAD start of speech sensitivity",
            zh="VAD 语音开始敏感度"
        ),
        "end_of_speech_sensitivity": Description(notes=None,
            en="VAD end of speech sensitivity",
            zh="VAD 语音结束敏感度"
        ),
        "prefix_padding_ms": Description(notes=None,
            en="VAD prefix padding in milliseconds",
            zh="VAD 前缀填充毫秒数"
        ),
        "silence_duration_ms": Description(notes=None,
            en="VAD silence duration in milliseconds",
            zh="VAD 静音持续毫秒数"
        ),
        "enable_function_calling": Description(notes=None,
            en="Enable function calling capability",
            zh="启用函数调用功能"
        ),
        "function_declarations": Description(notes=None,
            en="Function declarations for function calling",
            zh="函数调用的函数声明"
        ),
        "enable_code_execution": Description(notes=None,
            en="Enable code execution capability",
            zh="启用代码执行功能"
        ),
        "enable_google_search": Description(notes=None,
            en="Enable Google Search capability",
            zh="启用Google搜索功能"
        ),
        "enable_context_compression": Description(notes=None,
            en="Enable context window compression for longer sessions",
            zh="启用上下文窗口压缩以支持更长的对话会话"
        ),
        "compression_window_size": Description(notes=None,
            en="Number of turns to include in the sliding window for compression",
            zh="压缩滑动窗口中包含的回合数"
        ),
        "compression_token_threshold": Description(notes=None,
            en="Token threshold that triggers compression",
            zh="触发压缩的令牌阈值"
        ),
        "enable_input_audio_transcription": Description(notes=None,
            en="Enable transcription of audio input",
            zh="启用输入音频的转录"
        ),
        "disable_automatic_vad": Description(notes=None,
            en="Disable automatic VAD and use manual activity detection",
            zh="禁用自动VAD并使用手动活动检测"
        ),
        "use_dual_prompt_system": Description(notes=None,
            en="Use the two-step approach for handling emotion tags (planning phase + clean response phase)",
            zh="使用两步法处理情绪标签（规划阶段 + 清洁响应阶段）"
        ),
    }


class AgentSettings(I18nMixin, BaseModel):
    """Settings for different types of agents."""

    basic_memory_agent: Optional[BasicMemoryAgentConfig] = Field(
        None, alias="basic_memory_agent"
    )
    mem0_agent: Optional[Mem0Config] = Field(None, alias="mem0_agent")
    hume_ai_agent: Optional[HumeAIConfig] = Field(None, alias="hume_ai_agent")
    gemini_live_agent: Optional[GeminiLiveConfig] = Field(None, alias="gemini_live_agent")

    DESCRIPTIONS: ClassVar[Dict[str, Description]] = {
        "basic_memory_agent": Description(notes=None,
            en="Configuration for basic memory agent", zh="基础记忆代理配置"
        ),
        "mem0_agent": Description(notes=None,en="Configuration for Mem0 agent", zh="Mem0代理配置"),
        "hume_ai_agent": Description(notes=None,
            en="Configuration for Hume AI agent", zh="Hume AI 代理配置"
        ),
        "gemini_live_agent": Description(notes=None,
            en="Configuration for Gemini Live agent", zh="Gemini Live 代理配置"
        ),
    }


class AgentConfig(I18nMixin, BaseModel):
    """This class contains all of the configurations related to agent."""

    conversation_agent_choice: Literal[
        "basic_memory_agent", "mem0_agent", "hume_ai_agent", "gemini_live_agent"
    ] = Field(..., alias="conversation_agent_choice")
    agent_settings: AgentSettings = Field(..., alias="agent_settings")
    llm_configs: StatelessLLMConfigs = Field(..., alias="llm_configs")

    DESCRIPTIONS: ClassVar[Dict[str, Description]] = {
        "conversation_agent_choice": Description(notes=None,
            en="Type of conversation agent to use", zh="要使用的对话代理类型"
        ),
        "agent_settings": Description(notes=None,
            en="Settings for different agent types", zh="不同代理类型的设置"
        ),
        "llm_configs": Description(notes=None,
            en="Pool of LLM provider configurations", zh="语言模型提供者配置池"
        ),
    }
