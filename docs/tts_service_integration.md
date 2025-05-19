# TTS Service Integration

This document describes the integration of the TTS Service for Japanese voice synthesis in the Open-LLM-VTuber project.

## Overview

The TTS Service is a microservice that provides Japanese text-to-speech synthesis using Kokoro TTS. It is designed to isolate the complexity of Japanese text processing and TTS generation from the main application.

> **Note**: We have standardized on the microservice approach for Kokoro TTS integration, removing the direct integration option to simplify the codebase.

## Architecture

The TTS Service consists of the following components:

1. **TTS Service**: A Flask API server that provides a simple REST API for generating speech from text.
2. **TTS Service Client**: A Python client library that communicates with the TTS Service.

## Features

- Japanese text-to-speech synthesis
- Support for multiple voices (jf_alpha, jf_gongitsune, jf_nezumi, jf_tebukuro)
- Emotion support through text tags (e.g., [joy:0.8])
- Simple REST API
- Configurable sample rate and output format
- Improved phoneme processing with MeCab integration
- Robust error handling and fallback mechanisms
- Configuration management via REST API
- Simple start/stop scripts for service management

## Installation

1. Install system dependencies:

```bash
sudo apt-get update && sudo apt-get install -y mecab libmecab-dev mecab-ipadic-utf8 swig
```

2. Create MeCab configuration:

```bash
sudo mkdir -p /usr/local/etc
echo "dicdir = /var/lib/mecab/dic/ipadic-utf8" | sudo tee /usr/local/etc/mecabrc
```

3. Install Python dependencies:

```bash
cd tts_service
pip install -r requirements.txt
```

   > **Note**: Make sure you have compatible versions of numpy, scipy, and torch installed. The TTS service requires numpy==1.22.3, scipy==1.10.1, and torch==2.0.1.

4. Start the TTS Service using the provided script:

```bash
cd tts_service
./start_service.sh
```

5. The service will be available at http://localhost:5000

6. To stop the service:

```bash
cd tts_service
./stop_service.sh
```

## Configuration

The TTS Service is configured in the `conf.yaml` file:

```yaml
tts_config:
  tts_model: 'tts_service'

  # TTS Service configuration
  tts_service:
    base_url: "http://localhost:5000"  # URL of the TTS Service
```

## Usage

### Using the TTS Service Client

```python
from open_llm_vtuber.tts.tts_service_client import TTSServiceClient

# Create a client
client = TTSServiceClient(base_url="http://localhost:5000")

# Check if the service is healthy
if client.health_check():
    # Get available voices
    voices = client.get_available_voices()
    print(f"Available voices: {voices}")

    # Get current configuration
    config = client.get_config()
    print(f"Current configuration: {config}")

    # Update configuration
    new_config = {
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
    client.update_config(new_config)

    # Generate speech
    output_path = client.generate_speech(
        text="こんにちは、私はダオコです。[joy:0.8]よろしくお願いします！",
        voice="jf_alpha"
    )
    print(f"Generated audio file: {output_path}")
```

### Using the TTS Factory

```python
from open_llm_vtuber.tts.tts_factory import TTSFactory

# Create a TTS engine
tts_engine = TTSFactory.get_tts_engine(
    "tts_service",
    base_url="http://localhost:5000"
)

# Generate speech
output_path = tts_engine.generate_audio(
    "こんにちは、私はダオコです。[joy:0.8]"
)
print(f"Generated audio file: {output_path}")
```

## API Endpoints

### Generate Speech

```
POST /tts
```

Request body:

```json
{
  "text": "こんにちは、私はダオコです。[joy:0.8]",
  "voice": "jf_alpha"
}
```

Response: Audio file (WAV format)

### Get Available Voices

```
GET /voices
```

Response:

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

Response:

```json
{
  "device": "cpu",
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

Request body:

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

Response:

```json
{
  "status": "ok",
  "message": "Configuration updated successfully",
  "config": {
    "device": "cpu",
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

### Health Check

```
GET /health
```

Response:

```json
{
  "status": "ok"
}
```

## Emotion Tags

You can add emotion tags to the text to express different emotions:

```
こんにちは、私はダオコです。[joy:0.8]
```

The available emotions are:
- `joy` - Happy
- `sadness` - Sad
- `anger` - Angry
- `fear` - Fearful
- `surprise` - Surprised
- `disgust` - Disgusted
- `neutral` - Neutral
- `smirk` - Happy (alternative)

The number after the colon is the intensity of the emotion (0.0 to 1.0).

## Troubleshooting

### TTS Service Issues

If you encounter issues with the TTS Service, check the logs:

```bash
cd tts_service
cat tts_service.log
```

You can also check if the service is running:

```bash
curl http://localhost:5000/health
```

If the service is not responding, you can restart it:

```bash
cd tts_service
./stop_service.sh
./start_service.sh
```

### Dependency Issues

If you encounter issues with dependencies, make sure you have the correct versions installed:

```bash
pip install numpy==1.22.3 scipy==1.10.1 torch==2.0.1
```

Common dependency issues include:

- **NumPy version conflicts**: The TTS service requires numpy==1.22.3
- **SciPy version conflicts**: The TTS service requires scipy==1.10.1
- **PyTorch version conflicts**: The TTS service requires torch==2.0.1

You may need to create a virtual environment to isolate the dependencies:

```bash
python -m venv tts_env
source tts_env/bin/activate
cd tts_service
pip install -r requirements.txt
```

### MeCab Issues

If you encounter issues with MeCab, make sure it's properly installed and the dictionary is available:

```bash
# Check MeCab installation
mecab -v

# Check MeCab dictionary
mecab -D
```
