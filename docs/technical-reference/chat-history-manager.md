# Chat History Manager

The `chat_history_manager.py` module provides functionalities for managing chat histories, including creating, storing, retrieving, updating, and deleting chat messages and their associated metadata. It ensures safe file operations by sanitizing paths and generating unique identifiers for chat sessions.

## Data Structures

### `HistoryMessage` (TypedDict)
Represents a single message in the chat history.

```python
class HistoryMessage(TypedDict):
    role: Literal["human", "ai"]
    timestamp: str
    content: str
    name: Optional[str]
    avatar: Optional[str]
```

**Attributes:**
*   `role` (`Literal["human", "ai"]`): The role of the message sender, either "human" or "ai".
*   `timestamp` (`str`): The ISO formatted timestamp when the message was recorded.
*   `content` (`str`): The actual content of the message.
*   `name` (`Optional[str]`): An optional display name for the sender.
*   `avatar` (`Optional[str]`): An optional URL or path to the sender's avatar.

## Functions

### `_is_safe_filename(filename: str) -> bool`
Validates if a given filename is safe and contains only allowed characters.

**Arguments:**
*   `filename` (`str`): The filename to validate.

**Returns:**
*   `bool`: `True` if the filename is safe, `False` otherwise.

### `_sanitize_path_component(component: str) -> str`
Sanitizes and validates a path component to prevent directory traversal attacks.

**Arguments:**
*   `component` (`str`): The path component to sanitize.

**Returns:**
*   `str`: The sanitized path component.

**Raises:**
*   `ValueError`: If the component contains invalid characters or is unsafe.

### `_ensure_conf_dir(conf_uid: str) -> str`
Ensures that the directory for a specific configuration UID exists. Creates the directory if it doesn't already exist.

**Arguments:**
*   `conf_uid` (`str`): The unique identifier for the configuration.

**Returns:**
*   `str`: The absolute path to the configuration directory.

**Raises:**
*   `ValueError`: If `conf_uid` is empty.

### `_get_safe_history_path(conf_uid: str, history_uid: str) -> str`
Constructs and sanitizes the full file path for a chat history, preventing path traversal.

**Arguments:**
*   `conf_uid` (`str`): Configuration unique identifier.
*   `history_uid` (`str`): History unique identifier.

**Returns:**
*   `str`: The safe and normalized full path to the history file.

**Raises:**
*   `ValueError`: If path traversal is detected.

### `create_new_history(conf_uid: str) -> str`
Creates a new chat history file with a unique ID and an initial metadata entry.

**Arguments:**
*   `conf_uid` (`str`): The unique identifier for the configuration under which this history belongs.

**Returns:**
*   `str`: The `history_uid` of the newly created chat history, or an empty string if creation fails.

### `store_message(conf_uid: str, history_uid: str, role: Literal["human", "ai"], content: str, name: str | None = None, avatar: str | None = None)`
Stores a new message in the specified chat history file. Appends the message to the end of the history.

**Arguments:**
*   `conf_uid` (`str`): Configuration unique identifier.
*   `history_uid` (`str`): History unique identifier.
*   `role` (`Literal["human", "ai"]`): The role of the message sender ("human" or "ai").
*   `content` (`str`): The message content.
*   `name` (`str | None`): Optional display name for the sender.
*   `avatar` (`str | None`): Optional avatar URL for the sender.

### `get_metadata(conf_uid: str, history_uid: str) -> dict`
Retrieves the metadata associated with a specific chat history. Metadata is stored as the first entry in the history file with `role: "metadata"`.

**Arguments:**
*   `conf_uid` (`str`): Configuration unique identifier.
*   `history_uid` (`str`): History unique identifier.

**Returns:**
*   `dict`: A dictionary containing the metadata, or an empty dictionary if not found or an error occurs.

### `update_metadate(conf_uid: str, history_uid: str, metadata: dict) -> bool`
Updates the metadata for a specific chat history. If metadata already exists, it merges the new `metadata` dictionary with the existing one, preserving existing fields. If no metadata exists, a new metadata entry is created.

**Arguments:**
*   `conf_uid` (`str`): Configuration unique identifier.
*   `history_uid` (`str`): History unique identifier.
*   `metadata` (`dict`): A dictionary containing the metadata fields to update or add.

**Returns:**
*   `bool`: `True` if metadata was successfully updated/created, `False` otherwise.

### `get_history(conf_uid: str, history_uid: str) -> List[HistoryMessage]`
Reads and returns the chat history for the given `conf_uid` and `history_uid`, excluding the metadata entry.

**Arguments:**
*   `conf_uid` (`str`): Configuration unique identifier.
*   `history_uid` (`str`): History unique identifier.

**Returns:**
*   `List[HistoryMessage]`: A list of `HistoryMessage` objects representing the chat history. Returns an empty list if the file is not found or an error occurs.

### `delete_history(conf_uid: str, history_uid: str) -> bool`
Deletes a specific chat history file.

**Arguments:**
*   `conf_uid` (`str`): Configuration unique identifier.
*   `history_uid` (`str`): History unique identifier.

**Returns:**
*   `bool`: `True` if the history file was successfully deleted, `False` otherwise.

### `get_history_list(conf_uid: str) -> List[dict]`
Retrieves a list of all chat histories associated with a given `conf_uid`, including their `uid`, `latest_message`, and `timestamp`. It also cleans up any empty history files.

**Arguments:**
*   `conf_uid` (`str`): Configuration unique identifier.

**Returns:**
*   `List[dict]`: A sorted list of dictionaries, each containing information about a history file.

### `modify_latest_message(conf_uid: str, history_uid: str, role: Literal["human", "ai", "system"], new_content: str) -> bool`
Modifies the content of the latest message in a chat history, provided its role matches the specified `role`.

**Arguments:**
*   `conf_uid` (`str`): Configuration unique identifier.
*   `history_uid` (`str`): History unique identifier.
*   `role` (`Literal["human", "ai", "system"]`): The expected role of the latest message.
*   `new_content` (`str`): The new content to update the latest message with.

**Returns:**
*   `bool`: `True` if the latest message was successfully modified, `False` otherwise.

### `rename_history_file(conf_uid: str, old_history_uid: str, new_history_uid: str) -> bool`
Renames a chat history file by changing its `history_uid`.

**Arguments:**
*   `conf_uid` (`str`): Configuration unique identifier.
*   `old_history_uid` (`str`): The current unique identifier of the history file.
*   `new_history_uid` (`str`): The new unique identifier for the history file.

**Returns:**
*   `bool`: `True` if the history file was successfully renamed, `False` otherwise.