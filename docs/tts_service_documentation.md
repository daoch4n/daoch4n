# TTS Service Documentation

This document provides information about the TTS service, a microservice for Japanese text-to-speech synthesis using the Kokoro TTS engine.

## Overview

The TTS service is a Flask-based microservice that provides a REST API for generating speech from text using the Kokoro TTS engine. It supports emotion-aware speech synthesis, multiple voices, and configuration options.

## Features

- **Emotion-Aware Speech Synthesis**: The service can generate speech with emotional inflections based on emotion tags in the text.
- **Multiple Voices**: The service supports multiple Japanese female voices from the Kokoro-82M model.
- **Configuration Options**: The service can be configured with various options, including sample rate, output format, and emotion mapping.
- **REST API**: The service provides a simple REST API for generating speech, listing available voices, and managing configuration.
- **Docker Support**: The service can be run in a Docker container for easy deployment.

## API Endpoints

### Health Check

```
GET /health
```

Returns the health status of the service.

**Response**:
```json
{
  "status": "ok"
}
```

### List Voices

```
GET /voices
```

Returns a list of available voices.

**Response**:
```json
{
  "voices": ["jf_alpha", "jf_gongitsune", "jf_nezumi", "jf_tebukuro"],
  "default": "jf_alpha"
}
```

### Get Configuration

```
GET /config
```

Returns the current configuration of the service.

**Response**:
```json
{
  "device": "cpu",
  "repo_id": null,
  "sample_rate": 24000,
  "output_format": "wav",
  "emotion_mapping": {
    "joy": 1.2,
    "sadness": 0.8,
    "anger": 1.1,
    "fear": 0.9,
    "surprise": 1.3,
    "disgust": 1.0,
    "neutral": 1.0,
    "smirk": 1.1
  }
}
```

### Update Configuration

```
POST /config
```

Updates the configuration of the service.

**Request**:
```json
{
  "sample_rate": 24000,
  "output_format": "wav",
  "emotion_mapping": {
    "joy": 1.2,
    "sadness": 0.8,
    "anger": 1.1,
    "fear": 0.9,
    "surprise": 1.3,
    "disgust": 0.85,
    "neutral": 1.0,
    "smirk": 1.1
  }
}
```

**Response**:
```json
{
  "status": "ok",
  "message": "Configuration updated successfully",
  "config": {
    "device": "cpu",
    "repo_id": null,
    "sample_rate": 24000,
    "output_format": "wav",
    "emotion_mapping": {
      "joy": 1.2,
      "sadness": 0.8,
      "anger": 1.1,
      "fear": 0.9,
      "surprise": 1.3,
      "disgust": 0.85,
      "neutral": 1.0,
      "smirk": 1.1
    }
  }
}
```

### Generate Speech

```
POST /tts
```

Generates speech from text.

**Request**:
```json
{
  "text": "こんにちは、私はダオコです。[joy:0.8]よろしくお願いします！",
  "voice": "jf_alpha"
}
```

**Response**:
Binary audio data (WAV format)

## Emotion Tags

The service supports emotion tags in the text to generate speech with emotional inflections. Emotion tags have the following format:

```
[emotion:intensity]
```

Where:
- `emotion` is the name of the emotion (e.g., joy, sadness, anger, fear, surprise, disgust, neutral, smirk)
- `intensity` is a float value between 0.0 and 1.0 indicating the intensity of the emotion

For example:
```
こんにちは、私はダオコです。[joy:0.8]よろしくお願いします！
```

This will generate speech with a joyful inflection for the second part of the text.

## Docker Deployment

The service can be deployed using Docker Compose:

```bash
cd tts_service
docker-compose up -d
```

This will build and start the TTS service container, exposing the service on port 5000.

## Client Usage

The service can be used with the provided TTS service client:

```python
from open_llm_vtuber.tts.tts_service_client import TTSServiceClient

# Create a client
client = TTSServiceClient(base_url="http://localhost:5000")

# Check if the service is healthy
if client.health_check():
    print("Service is healthy")

# Get available voices
voices = client.get_available_voices()
print(f"Available voices: {voices}")

# Generate speech
output_path = client.generate_speech(
    text="こんにちは、私はダオコです。[joy:0.8]よろしくお願いします！",
    voice="jf_alpha"
)
print(f"Generated audio file: {output_path}")
```

## Testing

The service can be tested using the provided test script:

```bash
cd tts_service
python test_service.py --list-voices
python test_service.py --get-config
python test_service.py --update-config
python test_service.py --text "こんにちは、私はダオコです。[joy:0.8]よろしくお願いします！"
```

## Troubleshooting

If the service fails to start, check the logs:

```bash
docker-compose logs
```

Common issues:
- Missing dependencies: Make sure all required dependencies are installed
- Port conflict: Make sure port 5000 is not already in use
- Model loading error: Make sure the Kokoro model is available at the specified path
