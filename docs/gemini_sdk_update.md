# Gemini SDK Update

This document describes the update from the old `google-generativeai` SDK to the new `google-genai` SDK for the Gemini Live Agent implementation.

## Overview

Google has released a new set of Google Gen AI libraries for working with the Gemini API. The new SDK is fully compatible with all Gemini API models and features, including recent additions like the Live API and Veo.

## Changes Made

The following changes were made to update the Gemini Live Agent implementation:

1. Updated imports:
   ```python
   # Old
   import google.generativeai as genai
   from google.generativeai import types as genai_types
   
   # New
   from google import genai
   from google.genai import types as genai_types
   ```

2. Updated client initialization:
   ```python
   # Old
   genai.configure(api_key=config.api_key)
   
   # New
   self.client = genai.Client(api_key=config.api_key)
   ```

3. Updated Live API connection:
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

4. Updated audio streaming:
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

## Installation

To install the new Google Gen AI SDK:

```bash
pip install -U -q "google-genai"
```

## API Key Configuration

The API key can be set in two ways:

1. Environment variable:
   ```bash
   export GOOGLE_API_KEY="YOUR_API_KEY"
   ```

2. Directly in the code:
   ```python
   client = genai.Client(api_key="your_api_key")
   ```

## Benefits of the New SDK

1. Full compatibility with all Gemini API models and features
2. Better support for the Live API
3. Improved error handling and type safety
4. More consistent API design
5. Better documentation and examples

## Troubleshooting

If you encounter issues with the new SDK:

1. Make sure you have the latest version installed:
   ```bash
   pip install -U -q "google-genai"
   ```

2. Check that your API key has access to the Gemini Live API

3. Verify that you're using a model that supports the Live API (with `-live` in the name)

4. Check the logs for specific error messages

## References

- [Google Gen AI SDK Documentation](https://ai.google.dev/docs/gemini_api_overview)
- [Gemini API Migration Guide](https://ai.google.dev/docs/migration_guide)
