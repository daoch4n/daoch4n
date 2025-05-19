# Gemini Live Integration for Live2D VTuber Application

## Overview

This document provides comprehensive information about the Gemini Live integration for the Live2D VTuber application. Gemini Live is Google's real-time conversational AI model that supports streaming audio input and output, enabling more natural and responsive interactions.

The integration allows the VTuber application to use Gemini Live as an agent, providing several advantages over traditional text-based agents:

- **Lower Latency**: Direct audio streaming reduces the end-to-end latency
- **More Natural Interactions**: Real-time interruptions and responses create a more conversational experience
- **High-Quality Voice Synthesis**: Gemini's built-in voice synthesis provides natural-sounding responses
- **Advanced Capabilities**: Support for tools, context compression, and multi-modal inputs

## Features

### Core Features

- **Real-time Audio Streaming**: Stream audio directly to and from Gemini Live
- **Text Input Support**: Send text input for non-voice interactions
- **Live2D Expression Integration**: Extract emotions from Gemini's responses for Live2D expressions
- **Session Management**: Resume sessions for continuous conversations
- **History Integration**: Store and retrieve conversation history

### Advanced Features

- **Tool Integration**:
  - Function Calling: Define and call custom functions
  - Code Execution: Execute code and return results
  - Google Search: Search the web for information

- **Context Window Compression**:
  - Sliding Window: Configure the number of turns to include
  - Token Threshold: Set the token count that triggers compression
  - Longer Sessions: Enable extended conversations without context limits

- **Audio Transcription**:
  - Input Transcription: Get text transcripts of user audio
  - Output Transcription: Get text transcripts of Gemini's audio responses

- **Voice Activity Detection (VAD)**:
  - Automatic VAD: Configure sensitivity for speech detection
  - Manual VAD: Control activity detection manually
  - Customizable Parameters: Adjust silence duration, padding, etc.

- **Token Usage Tracking**:
  - Prompt Tokens: Track tokens used in user inputs
  - Completion Tokens: Track tokens used in Gemini's responses
  - Total Tokens: Monitor overall token usage

## Configuration

### Basic Configuration

The Gemini Live agent is configured through the `GeminiLiveConfig` class in the configuration system. Here's a basic example:

```yaml
gemini_live_agent:
  api_key: 'YOUR_GEMINI_API_KEY'
  model_name: 'gemini-2.0-flash-live-001'
  language_code: 'en-US'
  voice_name: 'Kore'
  system_instruction: "You are a helpful assistant named Gemini."
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

### Agent Implementation

The Gemini Live integration is implemented through the `GeminiLiveAgent` class, which implements the `AgentInterface`. The agent handles:

- Session management with Gemini Live API
- Audio streaming and processing
- Text input and output
- Tool handling
- History management
- Token usage tracking

### Audio Processing

Audio is processed in the following way:

1. Audio is captured from the user's microphone
2. The audio is converted from float32 to int16 PCM format
3. The audio is streamed directly to Gemini Live
4. Gemini processes the audio and generates a response
5. The response audio is saved to a temporary file
6. The audio is played back to the user

### Live2D Integration

The Gemini Live agent integrates with the Live2D model by:

1. Extracting emotion tags from Gemini's responses (e.g., `[joy:0.7]`)
2. Mapping these emotions to Live2D expressions
3. Applying the expressions to the Live2D model with appropriate timing

### Session Management

Sessions are managed to provide continuous conversations:

1. Session handles are stored in metadata
2. Sessions can be resumed using the stored handles
3. GoAway messages are handled with reconnection logic
4. Token usage is tracked to prevent exceeding limits

## Usage Examples

### Basic Usage

To use Gemini Live as your agent:

1. Configure Gemini Live in your character configuration file
2. Start the application
3. Speak to the agent or send text input
4. The agent will respond with audio and Live2D expressions

### Using Tools

To use tools with Gemini Live:

1. Enable the desired tools in your configuration
2. Ask questions that require tool use (e.g., "What's the weather in Tokyo?")
3. Gemini will call the appropriate tool and incorporate the results in its response

### Manual VAD Control

To use manual VAD control:

1. Set `disable_automatic_vad: true` in your configuration
2. The application will manually send activity start/end signals
3. This provides more control over when Gemini considers speech to be active

## Troubleshooting

### Common Issues

- **Connection Errors**: Check your API key and internet connection
- **Audio Not Working**: Verify microphone permissions and audio settings
- **High Latency**: Adjust VAD settings or use manual VAD control
- **Session Termination**: Enable context window compression for longer sessions
- **Tool Errors**: Check function declarations and implementation

### Debugging

The agent includes extensive logging to help diagnose issues:

- Token usage is logged for monitoring
- Session events are logged (connection, resumption, etc.)
- Tool calls and responses are logged
- Audio processing events are logged

## Best Practices

- **System Instructions**: Provide clear instructions for the agent's persona
- **Emotion Tags**: Include instructions for using emotion tags in responses
- **Token Management**: Use context compression for longer conversations
- **Tool Design**: Design tools with clear descriptions and parameters
- **Error Handling**: Implement robust error handling for tools and sessions

## Future Enhancements

Potential future enhancements for the Gemini Live integration:

- **Multi-modal Input**: Support for image and video input
- **Custom Voice Training**: Support for custom voice models
- **Advanced Tool Integration**: More sophisticated tool implementations
- **Streaming Tool Responses**: Real-time tool response processing
- **Enhanced Emotion Extraction**: More nuanced emotion detection and mapping

## Conclusion

The Gemini Live integration provides a powerful and natural way to interact with the Live2D VTuber application. By leveraging Gemini's real-time capabilities, the application can provide a more engaging and responsive experience for users.
