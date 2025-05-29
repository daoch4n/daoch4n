# Gemini Live Integration Guide

This document provides comprehensive information about the Gemini Live integration for the Open LLM VTuber project, focusing on its technical details, usage, and best practices. Gemini Live is Google's real-time conversational AI model that supports streaming audio input and output, enabling more natural and responsive interactions.

## Overview

The Gemini Live API enables low-latency, bidirectional voice and video interactions with Gemini models. It uses WebSockets to establish a stateful connection, allowing for:

- Streaming audio input to the model
- Receiving audio output from the model
- Interrupting the model's responses
- Maintaining conversation context

This integration allows the VTuber application to use Gemini Live as an agent, providing several advantages over traditional text-based agents:

- **Lower Latency**: Direct audio streaming reduces end-to-end latency.
- **More Natural Interactions**: Real-time interruptions and responses create a more conversational experience.
- **High-Quality Voice Synthesis**: Gemini's built-in voice synthesis provides natural-sounding responses.
- **Advanced Capabilities**: Support for tools, context compression, and multi-modal inputs.

## Key Technical Details and Architecture

The Gemini Live integration follows a client-server architecture:

1.  **Client**: The Live2D VTuber application frontend (browser).
2.  **Server**: The Python backend that communicates with the Gemini Live API.
3.  **Gemini Live API**: Google's real-time conversational AI service.

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

### API Method: bidiGenerateContent

The Gemini Live API uses a method called `bidiGenerateContent` (bidirectional generate content), which is different from the standard `generateContent` method used by regular Gemini models. This is a crucial distinction:

-   **bidiGenerateContent**: Used by Live API models (with "live" in their name).
-   **generateContent**: Used by standard Gemini models.

### Supported Models

As of May 2025, the following models support the Live API:

-   `gemini-2.0-flash-live-001`: The primary model for Live API.
-   `gemini-2.0-flash-live-preview-04-09`: A preview version (may be deprecated).
-   Other models with `-live` in their name.

These models **only** support `bidiGenerateContent` and cannot be used with `generateContent`.

### WebSocket Connection

The Live API establishes a WebSocket connection to:
```
wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent
```
This connection is managed by the Google Generative AI SDK when using the `client.aio.live.connect()` method.

### Message Types

The WebSocket connection exchanges several types of messages:

1.  **Setup Messages**: Configure the session (model, parameters, etc.).
2.  **Client Content Messages**: Send text or other content to the model.
3.  **Realtime Input Messages**: Stream audio or video in real-time.
4.  **Server Content Messages**: Receive generated content from the model.
5.  **Tool Response Messages**: Handle function calls and responses.

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

## Configuration

To use the Gemini Live API, configure the following in `conf.yaml`:

### Basic Configuration

```yaml
character_config:
  agent_config:
    conversation_agent_choice: gemini_live_agent
    agent_settings:
      gemini_live_agent:
        api_key: 'YOUR_GEMINI_API_KEY'
        model_name: 'gemini-2.0-flash-live-001'
        language_code: 'ja-JP'  # Or your preferred language
        voice_name: 'Kore'      # Available voices: Puck, Charon, Kore, etc.
        system_instruction: "Your system instruction here"
```

### Voice Activity Detection (VAD) Configuration

Configure automatic VAD sensitivity:

```yaml
# Automatic VAD settings
start_of_speech_sensitivity: "START_SENSITIVITY_MEDIUM"
end_of_speech_sensitivity: "END_SENSITIVITY_MEDIUM"
silence_duration_ms: 800
prefix_padding_ms: 200
```

Or use manual VAD control:

```yaml
# Manual VAD control
disable_automatic_vad: true
```

### Tool Configuration

Enable and configure tools:

```yaml
# Tool configurations
enable_function_calling: true
function_declarations:
  - name: "get_weather"
    description: "Get the current weather for a location"
    parameters:
      type: "object"
      properties:
        location:
          type: "string"
          description: "The city and state, e.g., San Francisco, CA"
      required: ["location"]
enable_code_execution: true
enable_google_search: true
```

### Context Window Compression

Configure context window compression for longer sessions:

```yaml
# Context window compression
enable_context_compression: true
compression_window_size: 10
compression_token_threshold: 4000
```

### Audio Transcription

Enable input audio transcription:

```yaml
# Audio transcription
enable_input_audio_transcription: true
```

## Implementation Details

The Gemini Live Agent implementation in `src/open_llm_vtuber/agent/agents/gemini_live_agent.py` handles:

1.  Establishing a WebSocket connection to the Gemini Live API.
2.  Sending text and audio input to the model.
3.  Receiving and processing audio and text responses.
4.  Handling session resumption for longer conversations.
5.  Providing clear error messages if connection issues occur.

### Connection Establishment

In `GeminiLiveAgent._ensure_session()`, the WebSocket connection is established:

```python
self.gemini_session = await client.aio.live.connect(
    model=self.model_name,  # "gemini-2.0-flash-live-001"
    config=session_config_copy
)
```

### Session Configuration

The session is configured with parameters like:

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

### Native Mode Only

The Gemini Live Agent operates exclusively in native mode, using the Live API's `bidiGenerateContent` method. If the Live API connection fails, the agent will provide a clear error message rather than falling back to a different model:

```python
# Provide specific error information
if "404" in error_msg and "not found" in error_msg:
    logger.error(f"Model '{self.model_name}' not found. Check if the model name is correct.")
    logger.error("Live API models should end with '-live-001', '-live-preview' or similar suffix.")
elif "not supported for" in error_msg and "generateContent" in error_msg:
    logger.error(f"Model '{self.model_name}' doesn't support the requested method.")
    logger.error("Live API models only support bidiGenerateContent, not generateContent.")
elif "API key" in error_msg or "authentication" in error_msg.lower():
    logger.error("API key issue. Check if your Gemini API key is valid.")
```
This ensures that all Live API features like audio streaming are available when the connection is successful.

### Audio Processing

Audio is processed in the following way:

1.  Audio is captured from the user's microphone.
2.  The audio is converted from float32 to int16 PCM format.
3.  The audio is streamed directly to Gemini Live.
4.  Gemini processes the audio and generates a response.
5.  The response audio is saved to a temporary file.
6.  The audio is played back to the user.

#### Audio Format

-   Input Audio: PCM 16-bit, 16kHz, mono
-   Output Audio: PCM 16-bit, 24kHz, mono

### Live2D Integration

The Gemini Live agent integrates with the Live2D model by:

1.  Extracting emotion tags from Gemini's responses (e.g., `[joy:0.7]`).
2.  Mapping these emotions to Live2D expressions.
3.  Applying the expressions to the Live2D model with appropriate timing.

### Session Management

Sessions are managed to provide continuous conversations:

1.  Session handles are stored in metadata.
2.  Sessions can be resumed using the stored handles.
3.  GoAway messages are handled with reconnection logic.
4.  Token usage is tracked to prevent exceeding limits.

#### Session Resumption

Session resumption is handled to provide continuous conversations:

```python
if self.session_resumption_handle:
    session_config_copy["session_resumption"] = genai_types.SessionResumptionConfig(
        handle=self.session_resumption_handle
    )
else:
    session_config_copy["session_resumption"] = genai_types.SessionResumptionConfig()
```

#### GoAway Message Handling

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

## Gemini SDK Update

This section describes the update from the old `google-generativeai` SDK to the new `google-genai` SDK for the Gemini Live Agent implementation.

Google has released a new set of Google Gen AI libraries for working with the Gemini API. The new SDK is fully compatible with all Gemini API models and features, including recent additions like the Live API and Veo.

### Changes Made

The following changes were made to update the Gemini Live Agent implementation:

1.  Updated imports:
    ```python
    # Old
    import google.generativeai as genai
    from google.generativeai import types as genai_types
    
    # New
    from google import genai
    from google.genai import types as genai_types
    ```

2.  Updated client initialization:
    ```python
    # Old
    genai.configure(api_key=config.api_key)
    
    # New
    self.client = genai.Client(api_key=config.api_key)
    ```

3.  Updated Live API connection:
    ```python
    # Old
    client = genai.Client(api_key=genai.get_default_api_key())
    self.gemini_session = await client.aio.live.connect(
        model=self.model_name,
        config=session_config_copy
    )
    
    # New
    self.gemini_session = await self.client.aio.live.connect(
        model=self.model_name,
        config=session_config_copy
    )
    ```

4.  Updated audio streaming:
    ```python
    # Old
    await self.gemini_session.send_realtime_input(
        audio=genai_types.Blob(data=audio_chunk, mime_type="audio/pcm;rate=16000")
    )
    
    # New
    await self.gemini_session.send_realtime_input(
        audio={"data": audio_chunk, "mime_type": "audio/pcm;rate=16000"}
    )
    ```

### Installation

To install the new Google Gen AI SDK:

```bash
pip install -U -q "google-genai"
```

### API Key Configuration

The API key can be set in two ways:

1.  Environment variable:
    ```bash
    export GOOGLE_API_KEY="YOUR_API_KEY"
    ```

2.  Directly in the code:
    ```python
    client = genai.Client(api_key="your_api_key")
    ```

### Benefits of the New SDK

1.  Full compatibility with all Gemini API models and features.
2.  Better support for the Live API.
3.  Improved error handling and type safety.
4.  More consistent API design.
5.  Better documentation and examples.

## Usage Examples

### Basic Usage

To use Gemini Live as your agent:

1.  Configure Gemini Live in your character configuration file.
2.  Start the application.
3.  Speak to the agent or send text input.
4.  The agent will respond with audio and Live2D expressions.

### Using Tools

To use tools with Gemini Live:

1.  Enable the desired tools in your configuration.
2.  Ask questions that require tool use (e.g., "What's the weather in Tokyo?").
3.  Gemini will call the appropriate tool and incorporate the results in its response.

### Manual VAD Control

To use manual VAD control:

1.  Set `disable_automatic_vad: true` in your configuration.
2.  The application will manually send activity start/end signals.
3.  This provides more control over when Gemini considers speech to be active.

## Troubleshooting

### Common Errors

1.  **404 Model Not Found**:
    *   **Error**: `404 models/gemini-2.0-flash-live-001 is not found for API version v1beta`
    *   **Causes**: The model name is incorrect, the model is not available in your region, or the model has been deprecated or replaced.
    *   **Solutions**: Verify the model name is correct (check for typos), try a different region, or check the latest documentation for current model names. Ensure you're using `gemini-2.0-flash-live-001` for the Live API. Other models won't work.

2.  **Method Not Supported**:
    *   **Error**: `not supported for generateContent`
    *   **Causes**: Trying to use a Live API model with `generateContent`, or trying to use a standard model with `bidiGenerateContent`.
    *   **Solutions**: Use Live API models only with `client.aio.live.connect()`. Use standard models only with `model.generate_content()`.

3.  **API Version Error**: The error "not found for API version v1beta" indicates that the model might not be available in your region or for your API key.

4.  **Authentication Errors**:
    *   **Error**: `Invalid API key` or `Authentication failed`
    *   **Causes**: API key is invalid or expired, or API key doesn't have access to the requested model.
    *   **Solutions**: Verify your API key is correct, or check if your API key has the necessary permissions.

5.  **Connection Errors**: Check your API key and internet connection.

6.  **Audio Not Working**: Verify microphone permissions and audio settings.

7.  **High Latency**: Adjust VAD settings or use manual VAD control.

8.  **Session Termination**: Enable context window compression for longer sessions.

9.  **Tool Errors**: Check function declarations and implementation.

### Debugging

The agent includes extensive logging to help diagnose issues:

-   Token usage is logged for monitoring.
-   Session events are logged (connection, resumption, etc.).
-   Tool calls and responses are logged.
-   Audio processing events are logged.

### Solutions Summary

-   **Check Available Models**: Use the `list_gemini_models.py` script to see which models are available for your API key.
-   **Verify API Key**: Ensure your API key has access to the Gemini Live API.
-   **Region Restrictions**: Some models may be restricted by region. Check if the model is available in your region.
-   **SDK Version**: Make sure you have the latest version installed: `pip install -U -q "google-genai"`.
-   **Network Connection**: Ensure your network connection is stable for WebSocket communication.
-   **Logs**: Check the logs for specific error messages.

## Best Practices

1.  **Always use the correct model type**:
    *   Live API models (with "live" in the name) for bidirectional communication.
    *   Standard models for regular text generation.
2.  **Handle errors gracefully**:
    *   Provide clear, specific error messages to users.
    *   Implement proper error logging for troubleshooting.
3.  **Configure session parameters appropriately**:
    *   Set response modalities based on your needs.
    *   Configure voice settings for natural speech.
4.  **Monitor token usage**:
    *   Live API can consume tokens quickly.
    *   Implement rate limiting if necessary.
5.  **System Instructions**: Provide clear instructions for the agent's persona.
6.  **Emotion Tags**: Include instructions for using emotion tags in responses.
7.  **Token Management**: Use context compression for longer conversations.
8.  **Tool Design**: Design tools with clear descriptions and parameters.
9.  **Error Handling**: Implement robust error handling for tools and sessions.

## Performance Considerations

-   **Latency**: The end-to-end latency is affected by:
    -   Network latency to Gemini Live API.
    -   Audio processing time.
    -   VAD sensitivity settings.
    -   WebSocket communication overhead.
-   **Memory Usage**: Memory usage is affected by:
    -   Audio buffer size.
    -   Context window size.
    -   Token threshold for compression.
    -   Number of concurrent sessions.
-   **CPU Usage**: CPU usage is affected by:
    -   Audio processing.
    -   WebSocket communication.
    -   Live2D model rendering.
    -   Tool execution.

## Security Considerations

-   **API Key**: The Gemini API key should be kept secure.
-   **User Data**: Audio data and transcripts should be handled according to privacy policies.
-   **Tool Execution**: Code execution tools should be sandboxed.
-   **Function Calling**: Function declarations should be validated.

## Limitations

1.  **Response Modalities**: You can only set one response modality (TEXT or AUDIO) per session.
2.  **Session Duration**: Audio-only sessions are limited to 15 minutes, and audio plus video sessions are limited to 2 minutes without compression.
3.  **Context Window**: A session has a context window limit of 32k tokens.

## Future Enhancements

Potential future enhancements for the Gemini Live integration:

-   **Multi-modal Input**: Support for image and video input.
-   **Custom Voice Training**: Support for custom voice models.
-   **Advanced Tool Integration**: More sophisticated tool implementations.
-   **Streaming Tool Responses**: Real-time tool response processing.
-   **Enhanced Emotion Extraction**: More nuanced emotion detection and mapping.

## Testing

The Gemini Live integration can be tested using:

-   **Unit Tests**: Test individual components.
-   **Integration Tests**: Test the interaction between components.
-   **End-to-End Tests**: Test the complete flow from user input to AI response.
-   **Performance Tests**: Test latency, memory usage, and CPU usage.
-   **Security Tests**: Test API key handling and data privacy.

## References

-   [Gemini API Documentation](https://ai.google.dev/gemini-api/docs)
-   [Live API Documentation](https://ai.google.dev/api/live)
-   [WebSockets API Reference](https://ai.google.dev/api/live#websocket-endpoint-url)
-   [Google Gen AI SDK Documentation](https://ai.google.dev/docs/gemini_api_overview)
-   [Gemini API Migration Guide](https://ai.google.dev/docs/migration_guide)
-   [Gemini Models List](https://ai.google.dev/api/models)