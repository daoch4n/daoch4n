# API Routes

The `routes.py` module defines the FastAPI `APIRouter` instances for various functionalities of the application, including the main client WebSocket communication and web tool integrations for ASR (Automatic Speech Recognition) and TTS (Text-to-Speech). These routes expose the core services to the frontend and other potential clients.

## Functions

### `init_client_ws_route(default_context_cache: ServiceContext) -> APIRouter`
Initializes and returns an `APIRouter` specifically for handling the `/client-ws` WebSocket connections. This is the primary communication channel between the frontend application and the backend server for real-time interactions.

**Arguments:**
*   `default_context_cache` (`ServiceContext`): An instance of `ServiceContext` that provides access to shared resources and configurations for new client sessions.

**Returns:**
*   `APIRouter`: A FastAPI router configured with the WebSocket endpoint.

#### WebSocket Endpoint: `/client-ws`
This WebSocket endpoint manages the lifecycle of client connections.

**Behavior:**
1.  **Accepts Connection:** Upon a new connection, the WebSocket is accepted.
2.  **Client UID Generation:** A unique client identifier (`client_uid`) is generated for each new connection using `uuid4()`.
3.  **Connection Handling:** The `WebSocketHandler` (initialized with `default_context_cache`) is used to manage the new connection and subsequent communication.
4.  **Disconnection Handling:** If the WebSocket connection is closed (`WebSocketDisconnect`) or any other exception occurs, the `WebSocketHandler`'s `handle_disconnect` method is called to clean up resources associated with the client.

### `init_webtool_routes(default_context_cache: ServiceContext) -> APIRouter`
Initializes and returns an `APIRouter` for various web tool-related endpoints, including redirects for the web tool frontend, an ASR transcription endpoint, and a TTS WebSocket endpoint.

**Arguments:**
*   `default_context_cache` (`ServiceContext`): An instance of `ServiceContext` providing access to shared resources like the ASR and TTS engines.

**Returns:**
*   `APIRouter`: A FastAPI router configured with the web tool endpoints.

#### HTTP Redirect Endpoints: `/web-tool` and `/web_tool`
These GET endpoints provide redirects to the main `index.html` page of the web tool.

**Behavior:**
*   Both `/web-tool` and `/web_tool` will issue an HTTP 302 (Found) redirect to `/web-tool/index.html`.

#### POST Endpoint: `/asr`
Handles audio transcription requests. Clients can upload WAV audio files, which are then processed by the ASR (Automatic Speech Recognition) engine.

**Arguments (Form Data):**
*   `file` (`UploadFile`): The audio file to be transcribed. Expected to be a 16-bit PCM WAV format.

**Processing Logic:**
1.  Reads the content of the uploaded file.
2.  Performs basic validation on the file size and audio data buffer.
3.  Converts the raw audio data (16-bit PCM) into a `float32` NumPy array, suitable for the ASR engine.
4.  Calls `default_context_cache.asr_engine.async_transcribe_np` to perform the transcription.

**Returns:**
*   `JSONResponse` (`{"text": str}`): On success, returns a JSON object containing the transcribed text.
*   `JSONResponse` (`{"error": str}`): On failure (e.g., `ValueError` for invalid audio format, or other exceptions), returns a JSON object with an error message and an appropriate HTTP status code (400 for bad request, 500 for internal server error).

#### WebSocket Endpoint: `/tts-ws`
Manages real-time Text-to-Speech (TTS) generation. Clients send text, and the server streams back audio paths for the generated speech.

**Behavior:**
1.  **Accepts Connection:** Upon a new connection, the WebSocket is accepted.
2.  **Receives Text:** Continuously listens for incoming JSON messages containing a `text` field.
3.  **Sentence Splitting:** The received text is split into individual sentences.
4.  **Audio Generation and Streaming:**
    *   For each sentence, `default_context_cache.tts_engine.async_generate_audio` is called to generate an audio file.
    *   The path to the generated audio file and the corresponding sentence are sent back to the client via WebSocket with a `status: "partial"`.
5.  **Completion Signal:** After all sentences have been processed, a `{"status": "complete"}` message is sent to the client.

**Error Handling:**
*   If an error occurs during TTS generation for a sentence, an `{"status": "error", "message": str(e)}` message is sent to the client.
*   Handles `WebSocketDisconnect` gracefully. Any other exceptions lead to the WebSocket being closed and an error logged.