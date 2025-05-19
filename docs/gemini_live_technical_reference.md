# Gemini Live Technical Reference

## Architecture

The Gemini Live integration follows a client-server architecture:

1. **Client**: The Live2D VTuber application frontend
2. **Server**: The Python backend that communicates with Gemini Live API
3. **Gemini Live API**: Google's real-time conversational AI service

### Component Diagram

```
┌─────────────┐     ┌─────────────────────────────────┐     ┌─────────────────┐
│             │     │                                 │     │                 │
│   Frontend  │◄────┤  Backend (WebSocketHandler)    │◄────┤  Gemini Live    │
│   (Browser) │     │                                 │     │  API            │
│             │────►│                                 │────►│                 │
└─────────────┘     └─────────────────────────────────┘     └─────────────────┘
                                    │
                                    │
                                    ▼
                    ┌─────────────────────────────────┐
                    │                                 │
                    │  GeminiLiveAgent                │
                    │                                 │
                    └─────────────────────────────────┘
                                    │
                                    │
                                    ▼
                    ┌─────────────────────────────────┐
                    │                                 │
                    │  Live2D Model                   │
                    │                                 │
                    └─────────────────────────────────┘
```

## Class Reference

### GeminiLiveConfig

Configuration class for the Gemini Live agent.

#### Properties

| Property                       | Type                | Description                                       |
|--------------------------------|---------------------|---------------------------------------------------|
| api_key                        | str                 | Gemini API Key                                    |
| model_name                     | str                 | Gemini Live model name                            |
| language_code                  | str                 | Language code for speech (e.g., en-US)            |
| voice_name                     | Optional[str]       | Gemini voice name (e.g., Kore)                    |
| system_instruction             | Optional[str]       | System instruction/persona for Gemini             |
| start_of_speech_sensitivity    | Optional[Literal]   | VAD start of speech sensitivity                   |
| end_of_speech_sensitivity      | Optional[Literal]   | VAD end of speech sensitivity                     |
| prefix_padding_ms              | Optional[int]       | VAD prefix padding in milliseconds                |
| silence_duration_ms            | Optional[int]       | VAD silence duration in milliseconds              |
| enable_function_calling        | bool                | Enable function calling capability                |
| function_declarations          | Optional[List[Dict]]| Function declarations for function calling        |
| enable_code_execution          | bool                | Enable code execution capability                  |
| enable_google_search           | bool                | Enable Google Search capability                   |
| enable_context_compression     | bool                | Enable context window compression                 |
| compression_window_size        | int                 | Number of turns in sliding window                 |
| compression_token_threshold    | int                 | Token threshold that triggers compression         |
| enable_input_audio_transcription | bool              | Enable transcription of audio input               |
| disable_automatic_vad          | bool                | Disable automatic VAD for manual control          |

### GeminiLiveAgent

Agent class that implements the AgentInterface for Gemini Live.

#### Methods

| Method                  | Parameters                      | Return Type                  | Description                                       |
|-------------------------|--------------------------------|------------------------------|---------------------------------------------------|
| __init__                | config, character_name, character_avatar, live2d_model | None | Initialize the agent                              |
| chat                    | batch_input: BatchInput        | AsyncIterator[AudioOutput]   | Chat with the agent                               |
| stream_audio_chunk      | audio_chunk: bytes             | None                         | Stream an audio chunk to Gemini Live              |
| end_audio_stream        | None                           | None                         | Signal the end of the audio stream                |
| handle_interrupt        | heard_response: str            | None                         | Handle an interruption signal                     |
| set_memory_from_history | conf_uid: str, history_uid: str | None                        | Set the agent's memory from a history             |
| close_session           | None                           | None                         | Close the Gemini Live session                     |

#### Private Methods

| Method                  | Parameters                      | Return Type                  | Description                                       |
|-------------------------|--------------------------------|------------------------------|---------------------------------------------------|
| _ensure_session         | None                           | None                         | Ensure that a Gemini Live session is active       |
| _send_history_to_gemini | None                           | None                         | Send conversation history to Gemini               |
| _setup_tool_handlers    | None                           | Dict[str, Callable]          | Set up handlers for different tool types          |
| _handle_function_call   | function_call: Dict[str, Any]  | Dict[str, Any]               | Handle a function call from Gemini                |
| _handle_code_execution  | code_execution: Dict[str, Any] | Dict[str, Any]               | Handle a code execution request from Gemini       |
| _handle_google_search   | search_query: Dict[str, Any]   | Dict[str, Any]               | Handle a Google Search request from Gemini        |
| _process_tool_calls     | tool_calls: List[Dict[str, Any]]| None                        | Process tool calls from Gemini                    |

## Protocol Reference

### WebSocket Messages

#### Client to Server

| Message Type      | Description                                       | Payload                                           |
|-------------------|---------------------------------------------------|---------------------------------------------------|
| text-input        | Text input from the user                          | `{ "type": "text-input", "text": "Hello" }`       |
| mic-audio-end     | End of audio input from the user                  | `{ "type": "mic-audio-end" }`                     |
| audio             | Audio data from the user                          | `{ "type": "audio", "audio": [float32 array] }`   |
| ai-speak-signal   | Signal for the AI to speak                        | `{ "type": "ai-speak-signal" }`                   |

#### Server to Client

| Message Type           | Description                                       | Payload                                           |
|------------------------|---------------------------------------------------|---------------------------------------------------|
| audio                  | Audio data from the AI                            | `{ "type": "audio", "audio": "base64 data" }`     |
| full-text              | Full text response from the AI                    | `{ "type": "full-text", "text": "Hello" }`        |
| backend-synth-complete | Backend synthesis is complete                     | `{ "type": "backend-synth-complete" }`            |
| force-new-message      | Force a new message in the UI                     | `{ "type": "force-new-message" }`                 |
| control                | Control message                                   | `{ "type": "control", "text": "..." }`            |
| error                  | Error message                                     | `{ "type": "error", "message": "Error message" }` |

### Gemini Live API

#### Session Configuration

```python
session_config = {
    "response_modalities": ["AUDIO"],
    "speech_config": {
        "language_code": "en-US",
        "voice_config": {
            "prebuilt_voice_config": {
                "voice_name": "Kore"
            }
        }
    },
    "output_audio_transcription": {},
    "input_audio_transcription": {},
    "system_instruction": {
        "parts": [{"text": "You are a helpful assistant."}]
    },
    "tools": [
        {"function_declarations": [...]},
        {"code_execution": {}},
        {"google_search": {}}
    ],
    "context_window_compression": {
        "sliding_window": {
            "window_size": 10
        },
        "token_threshold": 4000
    },
    "realtime_input_config": {
        "automatic_activity_detection": {
            "start_of_speech_sensitivity": "START_SENSITIVITY_MEDIUM",
            "end_of_speech_sensitivity": "END_SENSITIVITY_MEDIUM",
            "prefix_padding_ms": 200,
            "silence_duration_ms": 800
        }
    },
    "session_resumption": {}
}
```

#### Audio Format

- Input Audio: PCM 16-bit, 16kHz, mono
- Output Audio: PCM 16-bit, 24kHz, mono

## Implementation Notes

### Audio Processing

The audio processing pipeline involves:

1. **Frontend**: Captures audio using the Web Audio API
2. **WebSocket**: Streams audio as float32 arrays to the backend
3. **Backend**: Converts float32 to int16 PCM format
4. **Gemini Live**: Processes the audio and generates a response
5. **Backend**: Saves the response audio to a temporary file
6. **WebSocket**: Sends the audio file path to the frontend
7. **Frontend**: Plays the audio file

### Token Usage Tracking

Token usage is tracked to monitor costs and prevent exceeding limits:

```python
if response.server_content.usage_metadata:
    prompt_tokens = response.server_content.usage_metadata.prompt_token_count or 0
    completion_tokens = response.server_content.usage_metadata.candidates_token_count or 0
    total_tokens = response.server_content.usage_metadata.total_token_count or 0
    
    self.total_prompt_tokens += prompt_tokens
    self.total_completion_tokens += completion_tokens
    self.total_tokens += total_tokens
```

### Session Resumption

Session resumption is handled to provide continuous conversations:

```python
if self.session_resumption_handle:
    session_config_copy["session_resumption"] = genai_types.SessionResumptionConfig(
        handle=self.session_resumption_handle
    )
else:
    session_config_copy["session_resumption"] = genai_types.SessionResumptionConfig()
```

### GoAway Message Handling

GoAway messages are handled to reconnect before session termination:

```python
if response.go_away:
    time_left_seconds = response.go_away.time_left.seconds if response.go_away.time_left else 0
    
    if time_left_seconds > 10 and self.session_resumption_handle:
        # Close current session and reconnect
        if self.gemini_session:
            await self.gemini_session.close()
        self.gemini_session = None
        await self._ensure_session()
```

### Manual VAD Control

Manual VAD control is implemented for more precise speech detection:

```python
# If using manual VAD and this is the first chunk, send activity_start
if self.using_manual_vad and not self.active_audio_stream:
    await self.gemini_session.send_realtime_input(activity_start=True)

# If using manual VAD, send activity_end before audio_stream_end
if self.using_manual_vad:
    await self.gemini_session.send_realtime_input(activity_end=True)
```

## Performance Considerations

- **Latency**: The end-to-end latency is affected by:
  - Network latency to Gemini Live API
  - Audio processing time
  - VAD sensitivity settings
  - WebSocket communication overhead

- **Memory Usage**: Memory usage is affected by:
  - Audio buffer size
  - Context window size
  - Token threshold for compression
  - Number of concurrent sessions

- **CPU Usage**: CPU usage is affected by:
  - Audio processing
  - WebSocket communication
  - Live2D model rendering
  - Tool execution

## Security Considerations

- **API Key**: The Gemini API key should be kept secure
- **User Data**: Audio data and transcripts should be handled according to privacy policies
- **Tool Execution**: Code execution tools should be sandboxed
- **Function Calling**: Function declarations should be validated

## Testing

The Gemini Live integration can be tested using:

- **Unit Tests**: Test individual components
- **Integration Tests**: Test the interaction between components
- **End-to-End Tests**: Test the complete flow from user input to AI response
- **Performance Tests**: Test latency, memory usage, and CPU usage
- **Security Tests**: Test API key handling and data privacy
