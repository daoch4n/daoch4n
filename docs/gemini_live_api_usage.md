# Gemini Live API Usage Guide

This document explains how to properly use the Gemini Live API in the Open LLM VTuber project.

## Overview

The Gemini Live API enables low-latency bidirectional voice and video interactions with Gemini. It allows for natural, human-like voice conversations with the ability to interrupt the model's responses using voice commands. The model can process text, audio, and video input, and provide text and audio output.

## Model Selection

The Gemini Live API requires specific models that support the `bidiGenerateContent` method. The standard Gemini models that support `generateContent` cannot be used with the Live API.

### Supported Models

As of May 2025, the following model is supported for the Gemini Live API:

- `gemini-2.0-flash-live-001`

This model supports the `bidiGenerateContent` method required for the Live API.

### Compatibility Mode

If the Live API connection fails, the agent will fall back to compatibility mode, which uses a standard Gemini model (`gemini-2.0-flash`) with the `generateContent` method. In compatibility mode, some features like audio streaming will not be available.

## Configuration

To use the Gemini Live API, configure the following in `conf.yaml`:

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

## Implementation Details

The Gemini Live Agent implementation in `src/open_llm_vtuber/agent/agents/gemini_live_agent.py` handles:

1. Establishing a WebSocket connection to the Gemini Live API
2. Sending text and audio input to the model
3. Receiving and processing audio and text responses
4. Handling session resumption for longer conversations
5. Falling back to compatibility mode if the Live API connection fails

### Key Methods

- `_ensure_session()`: Establishes a connection to the Gemini Live API or falls back to compatibility mode
- `chat()`: Handles text-based interactions with the model
- `stream_audio_chunk()`: Streams audio data to the model for real-time processing
- `end_audio_stream()`: Signals the end of an audio stream

## Troubleshooting

### Common Errors

1. **404 Model Not Found**: Ensure you're using `gemini-2.0-flash-live-001` for the Live API. Other models won't work.

2. **API Version Error**: The error "not found for API version v1beta" indicates that the model might not be available in your region or for your API key.

3. **Method Not Supported**: The error "not supported for generateContent" occurs when trying to use a Live API model with the standard `generateContent` method. The Live API uses `bidiGenerateContent` instead.

### Solutions

1. **Check Available Models**: Use the `list_gemini_models.py` script to see which models are available for your API key.

2. **Verify API Key**: Ensure your API key has access to the Gemini Live API.

3. **Region Restrictions**: Some models may be restricted by region. Check if the model is available in your region.

## Limitations

1. **Response Modalities**: You can only set one response modality (TEXT or AUDIO) per session.

2. **Session Duration**: Audio-only sessions are limited to 15 minutes, and audio plus video sessions are limited to 2 minutes without compression.

3. **Context Window**: A session has a context window limit of 32k tokens.

4. **Audio Format**: Audio data is always raw, little-endian, 16-bit PCM. Audio output uses a sample rate of 24kHz.

## References

- [Gemini API Documentation](https://ai.google.dev/gemini-api/docs)
- [Live API Documentation](https://ai.google.dev/gemini-api/docs/live-api)
- [Gemini Models List](https://ai.google.dev/api/models)
