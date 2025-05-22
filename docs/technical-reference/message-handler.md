# Message Handler

The `message_handler.py` module provides a `MessageHandler` class designed to manage asynchronous message responses from clients. It uses `asyncio.Event` to allow different parts of the application to wait for specific types of responses from individual clients. This is particularly useful in an event-driven or WebSocket-based architecture where responses might not be immediately available.

## Classes

### `MessageHandler`
A class that handles the asynchronous waiting and processing of messages from various clients. It maintains a mapping of client UIDs to response types and their associated `asyncio.Event` objects and response data.

#### Attributes:
*   `_response_events` (`Dict[str, Dict[str, asyncio.Event]]`): A nested dictionary where the first key is `client_uid`, the second key is `response_type`, and the value is an `asyncio.Event` object. This event is set when a corresponding message is received.
*   `_response_data` (`Dict[str, Dict[str, dict]]`): A nested dictionary storing the actual message data. The structure mirrors `_response_events`.

#### `__init__(self)`
Initializes the `MessageHandler` instance, setting up empty dictionaries for `_response_events` and `_response_data`.

#### `wait_for_response(self, client_uid: str, response_type: str, timeout: float | None = None) -> Optional[dict]`
Asynchronously waits for a specific type of response from a given client. This method creates an `asyncio.Event` and waits for it to be set (signaling the arrival of the desired response). It supports an optional timeout.

**Arguments:**
*   `client_uid` (`str`): The unique identifier of the client from whom the response is expected.
*   `response_type` (`str`): The `type` field of the message dictionary that this method is waiting for.
*   `timeout` (`float | None`): An optional timeout in seconds. If a float is provided, the method will wait for that duration before timing out. If `None`, it waits indefinitely.

**Returns:**
*   `Optional[dict]`: The received response message dictionary if the event is set before the timeout (or indefinitely). Returns `None` if a timeout occurs.

**Error Handling:**
*   Logs a warning if a timeout occurs while waiting for the response.

#### `handle_message(self, client_uid: str, message: dict) -> None`
Processes an incoming message. If there is an `asyncio.Event` waiting for this message's `type` from the specified `client_uid`, the message data is stored, and the event is set to unblock any waiting coroutines.

**Arguments:**
*   `client_uid` (`str`): The unique identifier of the client that sent the message.
*   `message` (`dict`): The incoming message data, expected to contain a "type" key.

**Logic:**
*   Extracts the `type` from the `message`.
*   Checks if an `asyncio.Event` exists for the given `client_uid` and `message.type`.
*   If found, stores the `message` in `_response_data` and calls `set()` on the corresponding `asyncio.Event`.

#### `cleanup_client(self, client_uid: str) -> None`
Cleans up all pending `asyncio.Event` objects and cached response data associated with a specific client. This method should be called when a client disconnects to prevent memory leaks and ensure proper resource management.

**Arguments:**
*   `client_uid` (`str`): The unique identifier of the client to clean up.

**Logic:**
*   Iterates through all `asyncio.Event` objects for the given `client_uid` and calls `set()` on each to unblock any waiting coroutines (which will then receive `None` or whatever data was last set).
*   Removes the client's entries from both `_response_events` and `_response_data`.

## Global Instance

### `message_handler`
A global instance of the `MessageHandler` class, intended for direct use across the application to handle message waiting and processing.

```python
message_handler = MessageHandler()