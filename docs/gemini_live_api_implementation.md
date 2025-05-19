# Gemini Live API Implementation Guide

This document explains how the Gemini Live API is implemented in the Open LLM VTuber project, focusing on the technical details of the WebSocket-based bidirectional communication.

## Overview

The Gemini Live API enables real-time, bidirectional voice and video interactions with Gemini models. It uses WebSockets to establish a stateful connection that allows for:

- Streaming audio input to the model
- Receiving audio output from the model
- Interrupting the model's responses
- Maintaining conversation context

## Key Technical Details

### API Method: bidiGenerateContent

The Gemini Live API uses a method called `bidiGenerateContent` (bidirectional generate content), which is different from the standard `generateContent` method used by regular Gemini models. This is a crucial distinction:

- **bidiGenerateContent**: Used by Live API models (with "live" in their name)
- **generateContent**: Used by standard Gemini models

### Supported Models

As of May 2025, the following models support the Live API:

- `gemini-2.0-flash-live-001`: The primary model for Live API
- `gemini-2.0-flash-live-preview-04-09`: A preview version (may be deprecated)

These models **only** support `bidiGenerateContent` and cannot be used with `generateContent`.

### WebSocket Connection

The Live API establishes a WebSocket connection to:
```
wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent
```

This connection is managed by the Google Generative AI SDK when using the `client.aio.live.connect()` method.

### Message Types

The WebSocket connection exchanges several types of messages:

1. **Setup Messages**: Configure the session (model, parameters, etc.)
2. **Client Content Messages**: Send text or other content to the model
3. **Realtime Input Messages**: Stream audio or video in real-time
4. **Server Content Messages**: Receive generated content from the model
5. **Tool Response Messages**: Handle function calls and responses

## Implementation in Our Code

### Connection Establishment

In `GeminiLiveAgent._ensure_session()`, we establish the WebSocket connection:

```python
self.gemini_session = await client.aio.live.connect(
    model=self.model_name,  # "gemini-2.0-flash-live-001"
    config=session_config_copy
)
```

### Session Configuration

The session is configured with parameters like:

```python
self.session_config = {
    "response_modalities": ["AUDIO"],  # For audio output
    "speech_config": {
        "language_code": config.language_code,
        "voice_config": {
            "prebuilt_voice_config": {
                "voice_name": config.voice_name  # e.g., "Kore"
            }
        }
    },
    "output_audio_transcription": {},  # Get transcription of what Gemini says
    "system_instruction": {...},  # System instructions
    "context_window_compression": {...},  # For longer sessions
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

## Common Errors and Solutions

### 404 Model Not Found

**Error**: `404 models/gemini-2.0-flash-live-001 is not found for API version v1beta`

**Causes**:
- The model name is incorrect
- The model is not available in your region
- The model has been deprecated or replaced

**Solutions**:
- Verify the model name is correct (check for typos)
- Try a different region
- Check the latest documentation for current model names

### Method Not Supported

**Error**: `not supported for generateContent`

**Causes**:
- Trying to use a Live API model with `generateContent`
- Trying to use a standard model with `bidiGenerateContent`

**Solutions**:
- Use Live API models only with `client.aio.live.connect()`
- Use standard models only with `model.generate_content()`

### Authentication Errors

**Error**: `Invalid API key` or `Authentication failed`

**Causes**:
- API key is invalid or expired
- API key doesn't have access to the requested model

**Solutions**:
- Verify your API key is correct
- Check if your API key has the necessary permissions

## Best Practices

1. **Always use the correct model type**:
   - Live API models (with "live" in the name) for bidirectional communication
   - Standard models for regular text generation

2. **Handle errors gracefully**:
   - Provide clear, specific error messages to users
   - Implement proper error logging for troubleshooting

3. **Configure session parameters appropriately**:
   - Set response modalities based on your needs
   - Configure voice settings for natural speech

4. **Monitor token usage**:
   - Live API can consume tokens quickly
   - Implement rate limiting if necessary

## References

- [Gemini API Documentation](https://ai.google.dev/gemini-api/docs)
- [Live API Documentation](https://ai.google.dev/api/live)
- [WebSockets API Reference](https://ai.google.dev/api/live#websocket-endpoint-url)
