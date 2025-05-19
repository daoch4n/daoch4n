# Gemini Live Native Mode

This document describes the native mode implementation of the Gemini Live Agent, which removes the compatibility mode fallback that was causing warnings about missing Live API features.

## Overview

The Gemini Live Agent now operates exclusively in native mode, using the Gemini Live API's `bidiGenerateContent` method via WebSocket connection. This ensures that all Live API features are available, including:

- Real-time audio streaming
- Voice Activity Detection (VAD)
- Session resumption
- Tool calling
- Token usage tracking

## Configuration

To use the Gemini Live Agent in native mode, configure the following in `conf.yaml`:

```yaml
character_config:
  agent_config:
    conversation_agent_choice: gemini_live_agent
    agent_settings:
      gemini_live_agent:
        api_key: 'YOUR_GEMINI_API_KEY'
        model_name: 'gemini-2.0-flash-live-preview-04-09'  # Must be a Live API compatible model
        language_code: 'ja-JP'  # Or your preferred language
        voice_name: 'Kore'      # Available voices: Puck, Charon, Kore, etc.
        system_instruction: "Your system instruction here"
```

## Supported Models

The following models are compatible with the Gemini Live API:

- `gemini-2.0-flash-live-preview-04-09` (recommended)
- `gemini-2.0-flash-live-001`
- Other models with `-live` in their name

## Error Handling

If the Gemini Live API connection fails, the agent will now provide a clear error message instead of falling back to compatibility mode. Common errors include:

- **Model not found (404)**: Check if the model name is correct and available in your region.
- **Method not supported**: Ensure you're using a model that supports the `bidiGenerateContent` method (models with `-live` in their name).
- **API key issues**: Verify that your Gemini API key is valid and has access to the Live API.

## Implementation Details

The Gemini Live Agent implementation has been updated to:

1. Remove all compatibility mode fallback mechanisms
2. Improve error handling and logging
3. Ensure proper session management
4. Maintain all existing features like emotion extraction for Live2D models

## Troubleshooting

If you encounter issues with the Gemini Live Agent:

1. Check that you're using a valid Live API model (with `-live` in the name)
2. Verify your API key has access to the Gemini Live API
3. Check the logs for specific error messages
4. Ensure your network connection is stable for WebSocket communication

## Related Files

- `src/open_llm_vtuber/agent/agents/gemini_live_agent.py`: Main implementation of the Gemini Live Agent
- `conf.yaml`: Configuration file for the agent
- `frontend-src/dist/web/`: Frontend files for the Live2D model integration
