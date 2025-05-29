# Service Context

The `service_context.py` module defines the `ServiceContext` class, which serves as a central repository for initialized instances of various core services (ASR, TTS, LLM Agent, VAD, Translator, Live2D Model, and MCP Client) and their associated configurations. This class is crucial for managing the runtime state and dependencies for each connected client session, ensuring that services are properly initialized, updated, and accessible.

## Classes

### `ServiceContext`
Initializes, stores, and updates the ASR, TTS, LLM agent, VAD, and Live2D model instances, along with their configurations, for a connected client. It also manages the system prompt and chat history UID.

#### Attributes:
*   `config` (`Config`): The complete application configuration object.
*   `system_config` (`SystemConfig`): Configuration specific to the overall system, including MCP settings and tool prompts.
*   `character_config` (`CharacterConfig`): Configuration specific to the current character, including ASR, TTS, VAD, Agent, Translator, and Live2D model settings.
*   `live2d_model` (`Live2dModel`): An initialized instance of the Live2D model handler.
*   `asr_engine` (`ASRInterface`): An initialized ASR (Automatic Speech Recognition) engine instance.
*   `tts_engine` (`TTSInterface`): An initialized TTS (Text-to-Speech) engine instance.
*   `agent_engine` (`AgentInterface`): An initialized LLM (Large Language Model) agent instance.
*   `vad_engine` (`VADInterface | None`): An initialized VAD (Voice Activity Detection) engine instance, or `None` if VAD is disabled.
*   `translate_engine` (`TranslateInterface | None`): An initialized translation engine instance, or `None` if translation is disabled.
*   `mcp_client` (`MCPClient | None`): An initialized Model Context Protocol (MCP) client instance, or `None` if MCP is disabled.
*   `system_prompt` (`str`): The combined system prompt for the LLM agent, including the persona prompt and any tool-related prompts.
*   `history_uid` (`str`): The unique identifier for the current chat history session.

#### `__init__(self)`
Initializes all service instances and configuration attributes to `None` or empty strings.

#### `__str__(self)`
Provides a string representation of the `ServiceContext` instance, summarizing the loaded configurations and initialized engines.

#### `load_cache(self, config: Config, system_config: SystemConfig, character_config: CharacterConfig, live2d_model: Live2dModel, asr_engine: ASRInterface, tts_engine: TTSInterface, vad_engine: VADInterface, agent_engine: AgentInterface, translate_engine: TranslateInterface | None, mcp_client: MCPClient | None = None) -> None`
Loads the `ServiceContext` with references to pre-existing service instances and configuration objects. This method is used to share instances without reinitialization, promoting efficiency.

**Arguments:**
*   `config` (`Config`): The complete application configuration.
*   `system_config` (`SystemConfig`): The system configuration.
*   `character_config` (`CharacterConfig`): The character-specific configuration.
*   `live2d_model` (`Live2dModel`): An initialized Live2D model instance.
*   `asr_engine` (`ASRInterface`): An initialized ASR engine.
*   `tts_engine` (`TTSInterface`): An initialized TTS engine.
*   `vad_engine` (`VADInterface`): An initialized VAD engine.
*   `agent_engine` (`AgentInterface`): An initialized LLM agent engine.
*   `translate_engine` (`TranslateInterface | None`): An initialized translation engine (optional).
*   `mcp_client` (`MCPClient | None`): An initialized MCP client (optional).

**Raises:**
*   `ValueError`: If `character_config` or `system_config` is `None`.

#### `load_from_config(self, config: Config) -> None`
Loads the `ServiceContext` based on a provided `Config` object. This method handles the initialization (or re-initialization if configurations differ) of all service engines and the Live2D model.

**Arguments:**
*   `config` (`Config`): The configuration dictionary to load.

**Logic:**
1.  Updates internal `config`, `system_config`, and `character_config` attributes.
2.  Initializes (or reinitializes) `Live2dModel` using `init_live2d`.
3.  Initializes the `AgentInterface` using `init_agent`. If the agent is a "Gemini Live Agent", it skips the initialization of ASR, TTS, and VAD as these are handled externally in that case.
4.  Initializes ASR, TTS, VAD, and Translation engines using their respective `init_` methods, if not using a Gemini Live Agent.
5.  Logs a message indicating that the MCP client will be initialized during server startup, as `load_from_config` is not an `async` method.
6.  Updates the stored `config` references.

#### `init_live2d(self, live2d_model_name: str) -> None`
Initializes the `Live2dModel` instance based on the provided model name.

**Arguments:**
*   `live2d_model_name` (`str`): The name of the Live2D model to initialize.

**Error Handling:**
*   Logs a critical error if Live2D initialization fails but attempts to proceed without it.

#### `init_asr(self, asr_config: ASRConfig) -> None`
Initializes or updates the ASR engine. The engine is reinitialized only if it's currently `None` or if the `asr_config` has changed.

**Arguments:**
*   `asr_config` (`ASRConfig`): The ASR configuration.

#### `init_tts(self, tts_config: TTSConfig) -> None`
Initializes or updates the TTS engine. The engine is reinitialized only if it's currently `None` or if the `tts_config` has changed.

**Arguments:**
*   `tts_config` (`TTSConfig`): The TTS configuration.

#### `init_vad(self, vad_config: VADConfig) -> None`
Initializes or updates the VAD (Voice Activity Detection) engine. The engine is reinitialized only if it's currently `None` or if the `vad_config` has changed.

**Arguments:**
*   `vad_config` (`VADConfig`): The VAD configuration.

#### `init_agent(self, agent_config: AgentConfig, persona_prompt: str) -> bool`
Initializes or updates the LLM agent engine. This method also handles loading the persona prompt, prioritizing `DAOKO.MD` if available, otherwise using the one from the configuration. It constructs the full system prompt by appending tool prompts.

**Arguments:**
*   `agent_config` (`AgentConfig`): The agent-specific configuration.
*   `persona_prompt` (`str`): The base persona prompt for the agent.

**Returns:**
*   `bool`: `True` if the initialized agent is a "Gemini Live Agent", `False` otherwise.

**Complex Logic: Persona Prompt Loading:**
*   Attempts to load `persona_prompt` from `DAOKO.MD` using `load_persona()`.
*   If `DAOKO.MD` is found, its content overrides the `persona_prompt` from the config.
*   If `DAOKO.MD` is not found or an error occurs during loading, the `persona_prompt` from the configuration is used. A default placeholder is used if `persona_prompt` is also empty.

**Complex Logic: System Prompt Construction:**
*   The `system_prompt` is constructed by combining the `persona_prompt` with additional "tool prompts" defined in `system_config.tool_prompts`.
*   Special handling exists for `live2d_expression_prompt` (where `[<insert_emomap_keys>]` is replaced with `self.live2d_model.emo_str`) and `mcp_tools_prompt` (where `{{tools}}` and `{{resources}}` are replaced with JSON representations of available MCP tools and resources).

**Error Handling:**
*   Logs errors if agent initialization fails.

#### `init_translate(self, translator_config: TranslatorConfig) -> None`
Initializes or updates the translation engine. The engine is reinitialized only if it's currently `None` or if the `translator_config` has changed. Translation is skipped if `translate_audio` is disabled in the `translator_config`.

**Arguments:**
*   `translator_config` (`TranslatorConfig`): The translation configuration.

#### `async init_mcp(self) -> None`
Initializes or updates the Model Context Protocol (MCP) client. This is an asynchronous method, typically called during server startup. The MCP client is initialized only if configured and enabled. If the configuration changes, the existing client is shut down and a new one is initialized.

**Logic:**
*   Checks `system_config.mcp_config` for MCP enablement.
*   If MCP is enabled and not already initialized (or if the configuration has changed), a new `MCPClient` is created and initialized.
*   Calls `_register_default_mcp_resources()` to register essential MCP resources and tools.

#### `async _register_default_mcp_resources(self) -> None`
(Private Asynchronous Method) Registers default MCP resources and tools with the `mcp_client`. This includes:
*   User preferences (`create_user_preferences_resource`)
*   Live2D model information (`create_live2d_info_resource`)
*   Platform information (`create_platform_info_resource`)
*   Chat history (`create_chat_history_resource`) if `history_uid` is set.
*   Live2D expression tool (`create_expression_tool`) with a custom handler that returns success/failure based on expression availability.
*   Live2D motion tool (`create_motion_tool`) with a custom handler that returns success/failure based on motion availability.
*   External tools like weather and search (`create_weather_tool`, `create_search_tool`).

**Complex Logic: MCP Tool Handlers:**
*   For Live2D expression and motion tools, custom `async` handlers are defined inline. These handlers validate if the requested expression or motion exists on the `live2d_model` and return a success/failure payload. The actual animation is expected to be handled by the frontend based on this payload.

#### `construct_system_prompt(self, persona_prompt: str) -> str`
Appends tool prompts to the base persona prompt to create the final system prompt for the LLM.

**Arguments:**
*   `persona_prompt` (`str`): The initial persona prompt.

**Returns:**
*   `str`: The complete system prompt.

**Logic:**
*   Removes `group_conversation_prompt` from `system_config.tool_prompts` if it exists, as it's deprecated.
*   Iterates through other tool prompts defined in `system_config.tool_prompts`.
*   Loads content for each prompt file.
*   Replaces placeholders in `live2d_expression_prompt` with Live2D emotion map keys (`self.live2d_model.emo_str`).
*   Replaces `{{tools}}` and `{{resources}}` placeholders in `mcp_tools_prompt` with JSON representations of MCP tools and resources, respectively.
*   Appends the processed tool prompt content to the `persona_prompt`.

#### `async handle_config_switch(self, websocket: WebSocket, config_file_name: str) -> None`
Handles requests to switch the application's configuration. It loads a new character configuration (either a base `conf.yaml` or an alternative merged with the base), reinitializes services based on the new config, and notifies the client.

**Arguments:**
*   `websocket` (`WebSocket`): The WebSocket connection to the client.
*   `config_file_name` (`str`): The name of the configuration file to switch to (e.g., "conf.yaml" or a file from `config_alts_dir`).

**Complex Logic: Config Merging:**
*   If `config_file_name` is "conf.yaml", it loads the base configuration.
*   If an alternative `config_file_name` is provided, it loads that configuration and performs a deep merge with the current `character_config` using `deep_merge` to combine settings, with the new config prioritizing values.
*   Validates the merged configuration.
*   Calls `load_from_config` to reinitialize all relevant services based on the new configuration.

**Client Communication:**
*   Sends `set-model-and-conf` and `config-switched` messages to the client via WebSocket to inform them of the successful configuration change, including updated model info and config UIDs.

**Error Handling:**
*   Logs errors and sends an `error` message back to the client via WebSocket if the configuration switch fails.

## Utility Functions

### `deep_merge(dict1, dict2)`
Recursively merges `dict2` into `dict1`. If keys exist in both dictionaries and their values are also dictionaries, the merge is performed recursively. Otherwise, values from `dict2` overwrite values from `dict1`.

**Arguments:**
*   `dict1` (`dict`): The base dictionary to merge into.
*   `dict2` (`dict`): The dictionary to merge from.

**Returns:**
*   `dict`: The deeply merged dictionary.