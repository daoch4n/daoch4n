# WebSocket Handler

The `websocket_handler.py` module defines the `WebSocketHandler` class, which is central to managing real-time communication between the server and connected frontend clients via WebSockets. It is responsible for handling new connections, routing incoming messages to appropriate handlers, managing client-specific service contexts, and cleaning up resources upon disconnection. This module integrates various core functionalities such as chat history management, configuration switching, and MCP (Model Context Protocol) tool invocation.

## Enums

### `MessageType`
An enumeration defining categories of WebSocket message types.

```python
class MessageType(Enum):
    CONVERSATION = ["mic-audio-end", "text-input", "ai-speak-signal"]
    CONFIG = ["fetch-configs", "switch-config"]
    CONTROL = ["interrupt-signal", "audio-play-start"]
    DATA = ["mic-audio-data"]
```

**Members:**
*   `CONVERSATION`: Messages related to conversational flow (e.g., audio input end, text input, AI speaking signals).
*   `CONFIG`: Messages for fetching or switching application configurations.
*   `CONTROL`: Control signals (e.g., interruptions, audio playback start).
*   `DATA`: Raw data streams (e.g., microphone audio data).

## Type Definitions

### `WSMessage` (TypedDict)
A `TypedDict` defining the expected structure of incoming WebSocket messages. It uses `total=False` as not all fields are always present.

```python
class WSMessage(TypedDict, total=False):
    type: str
    action: Optional[str]
    text: Optional[str]
    audio: Optional[List[float]]
    images: Optional[List[str]]
    history_uid: Optional[str]
    file: Optional[str]
    display_text: Optional[dict]
```

**Fields:**
*   `type` (`str`): The primary identifier of the message (e.g., "mic-audio-end", "fetch-configs").
*   `action` (`Optional[str]`): An optional action associated with the message.
*   `text` (`Optional[str]`): Text content, used for text input, transcription results, etc.
*   `audio` (`Optional[List[float]]`): Audio data, typically as a list of floating-point samples.
*   `images` (`Optional[List[str]]`): List of image URLs or data (currently not extensively used).
*   `history_uid` (`Optional[str]`): A unique identifier for chat history sessions.
*   `file` (`Optional[str]`): File name or path, used for config switching or background fetching.
*   `display_text` (`Optional[dict]`): A dictionary for display-related text information (e.g., for specific UI elements).

## Classes

### `WebSocketHandler`
Manages all aspects of WebSocket connections, including client registration, message routing, and context management.

#### Attributes:
*   `client_connections` (`Dict[str, WebSocket]`): A dictionary mapping `client_uid` to their active `WebSocket` connection.
*   `client_contexts` (`Dict[str, ServiceContext]`): A dictionary mapping `client_uid` to their `ServiceContext` instance, which holds client-specific configurations and service instances.
*   `current_conversation_tasks` (`Dict[str, Optional[asyncio.Task]]`): Stores the `asyncio.Task` for ongoing conversations for each client, allowing for cancellation.
*   `default_context_cache` (`ServiceContext`): A base `ServiceContext` instance from which new client contexts are cloned.
*   `received_data_buffers` (`Dict[str, np.ndarray]`): Buffers for accumulating incoming audio data for each client.
*   `_message_handlers` (`Dict[str, Callable]`): A private dictionary mapping message types to their corresponding asynchronous handler methods.

#### `__init__(self, default_context_cache: ServiceContext)`
Initializes the `WebSocketHandler` by setting up empty dictionaries for client connections, contexts, and conversation tasks, and storing the `default_context_cache`. It also initializes the internal message handler mapping.

**Arguments:**
*   `default_context_cache` (`ServiceContext`): The default service context to be used as a template for new client sessions.

#### `_init_message_handlers(self) -> Dict[str, Callable]`
(Private Method) Populates the `_message_handlers` dictionary with mappings from message `type` strings to the corresponding `_handle_` methods. This method is called during initialization.

**Returns:**
*   `Dict[str, Callable]`: A dictionary of message type strings to handler functions.

#### `handle_new_connection(self, websocket: WebSocket, client_uid: str) -> None`
Asynchronously handles the setup process for a new WebSocket connection. This involves initializing a new `ServiceContext` for the session, storing client data, and sending initial messages to the client.

**Arguments:**
*   `websocket` (`WebSocket`): The newly accepted WebSocket connection.
*   `client_uid` (`str`): The unique identifier generated for the new client.

**Raises:**
*   `Exception`: If any step of the initialization fails, the error is logged, cleanup is attempted, and the exception is re-raised.

#### `_store_client_data(self, websocket: WebSocket, client_uid: str, session_service_context: ServiceContext)`
(Private Method) Stores the WebSocket connection, the newly created `ServiceContext`, and initializes an empty audio data buffer for the given client.

#### `_send_initial_messages(self, websocket: WebSocket, client_uid: str, session_service_context: ServiceContext)`
(Private Method) Sends initial messages to the newly connected client, including a "Connection established" message, Live2D model information, character configuration details, and a signal to start the microphone.

#### `_init_service_context(self) -> ServiceContext`
(Private Method) Creates a new `ServiceContext` instance for a client session by performing a deep copy of the `default_context_cache`'s configuration objects. This ensures that each client has its own mutable copy of the configuration while sharing immutable service engine instances.

**Returns:**
*   `ServiceContext`: A new `ServiceContext` instance for the session.

#### `handle_websocket_communication(self, websocket: WebSocket, client_uid: str) -> None`
Asynchronously manages the continuous communication loop for an established WebSocket connection. It receives incoming JSON messages, processes them using the global `message_handler`, and routes them to the appropriate internal handlers.

**Arguments:**
*   `websocket` (`WebSocket`): The active WebSocket connection.
*   `client_uid` (`str`): The unique identifier of the client.

**Error Handling:**
*   Catches `WebSocketDisconnect` to gracefully handle client disconnections.
*   Catches `json.JSONDecodeError` for invalid JSON messages.
*   Logs other exceptions and sends an error message back to the client.

#### `_route_message(self, websocket: WebSocket, client_uid: str, data: WSMessage) -> None`
(Private Method) Routes an incoming WebSocket message (`data`) to the appropriate handler method based on its `type` field.

**Arguments:**
*   `websocket` (`WebSocket`): The WebSocket connection.
*   `client_uid` (`str`): The client's unique identifier.
*   `data` (`WSMessage`): The incoming message data.

**Logic:**
*   Retrieves the `type` from the message.
*   Looks up the corresponding handler in `self._message_handlers`.
*   If a handler is found, it's invoked.
*   Logs a warning for unknown message types, with an exception for `frontend-playback-complete` which is often a client-side acknowledgement.

#### `handle_disconnect(self, client_uid: str) -> None`
Handles the disconnection of a client. This method cleans up all resources associated with the disconnected client, including removing their WebSocket connection, service context, audio buffers, and canceling any active conversation tasks. It also calls `message_handler.cleanup_client`.

**Arguments:**
*   `client_uid` (`str`): The unique identifier of the disconnected client.

#### `_handle_interrupt(self, websocket: WebSocket, client_uid: str, data: WSMessage) -> None`
(Private Method) Handles an `interrupt-signal` message, typically sent when the user wants to stop the AI's current speech or action. It leverages `handle_individual_interrupt` from `conversation_handler`.

#### `_handle_history_list_request(self, websocket: WebSocket, client_uid: str, data: WSMessage) -> None`
(Private Method) Responds to a `fetch-history-list` request by retrieving a list of all chat histories for the current configuration and sending it back to the client.

#### `_handle_fetch_history(self, websocket: WebSocket, client_uid: str, data: dict)`
(Private Method) Handles `fetch-and-set-history` requests. It retrieves a specific chat history by `history_uid`, updates the client's `ServiceContext` with this `history_uid`, sets the agent's memory, and sends the history messages back to the client.

#### `_handle_create_history(self, websocket: WebSocket, client_uid: str, data: WSMessage) -> None`
(Private Method) Handles `create-new-history` requests. It creates a new chat history file, updates the client's `ServiceContext` and agent's memory with the new `history_uid`, and notifies the client.

#### `_handle_delete_history(self, websocket: WebSocket, client_uid: str, data: dict)`
(Private Method) Handles `delete-history` requests. It deletes the specified chat history file and notifies the client of the success or failure. If the deleted history was the currently active one, `history_uid` in the context is reset.

#### `_handle_audio_data(self, websocket: WebSocket, client_uid: str, data: WSMessage) -> None`
(Private Method) Handles `mic-audio-data` messages containing raw audio chunks. If the agent is a `GeminiLiveAgent`, audio is streamed directly to it. Otherwise, audio data is appended to the `received_data_buffers` for later processing.

#### `_handle_raw_audio_data(self, websocket: WebSocket, client_uid: str, data: WSMessage) -> None`
(Private Method) Handles `raw-audio-data` messages, primarily for VAD (Voice Activity Detection) processing. It passes audio chunks to the VAD engine and, based on VAD output, appends detected speech to buffers and sends control signals (e.g., "mic-audio-end") to the frontend.

#### `_handle_conversation_trigger(self, websocket: WebSocket, client_uid: str, data: WSMessage) -> None`
(Private Method) Acts as a centralized handler for messages that trigger a conversation flow (e.g., `mic-audio-end`, `text-input`, `ai-speak-signal`). It delegates the actual conversation handling to `handle_conversation_trigger` from `conversation_handler`.

#### `_handle_fetch_configs(self, websocket: WebSocket, client_uid: str, data: WSMessage) -> None`
(Private Method) Handles `fetch-configs` requests by scanning the configured alternative configurations directory and sending the list of available config files to the client.

#### `_handle_config_switch(self, websocket: WebSocket, client_uid: str, data: dict)`
(Private Method) Handles `switch-config` requests. It calls `context.handle_config_switch` to load and apply a new configuration, which then notifies the client of the switch.

#### `_handle_fetch_backgrounds(self, websocket: WebSocket, client_uid: str, data: WSMessage) -> None`
(Private Method) Handles `fetch-backgrounds` requests by scanning the backgrounds directory and sending the list of available background image files to the client.

#### `_handle_mcp_tool_invoke(self, websocket: WebSocket, client_uid: str, data: WSMessage) -> None`
(Private Method) Handles `mcp-tool-invoke` requests, which are sent by the frontend to trigger an MCP tool on behalf of the LLM agent.

**Complex Logic: MCP Tool Invocation:**
*   Checks if MCP is enabled and initialized in the `ServiceContext`.
*   Validates the presence of `tool_name` in the incoming message.
*   **User Consent:** If `mcp_client.config.user_consent_required` is `True`, it sends an `mcp-consent-request` to the client. The server then waits for the client to send back the request with a `consent` field before proceeding with tool invocation.
*   If consent is granted (or not required), `context.mcp_client.invoke_tool` is called.
*   Sends an `mcp-tool-result` message back to the client, indicating success or failure, along with the tool's result or an error message.
*   Handles `KeyError` (tool not found), `ConnectionError` (MCP server connection issues), and other general exceptions during tool invocation.