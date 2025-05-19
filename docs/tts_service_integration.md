# TTS Service Integration

This document describes the integration of the TTS Service for Japanese voice synthesis in the Open-LLM-VTuber project.

## Overview

The TTS Service is a microservice that provides Japanese text-to-speech synthesis using Kokoro TTS. It is designed to isolate the complexity of Japanese text processing and TTS generation from the main application.

## Architecture

The TTS Service consists of the following components:

1. **TTS Service Microservice**: A Flask API server that provides a simple REST API for generating speech from text.
2. **TTS Service Client**: A Python client library that communicates with the TTS Service.
3. **Docker Container**: The TTS Service is packaged as a Docker container for easy deployment.

## Features

- Japanese text-to-speech synthesis
- Support for multiple voices (jf_alpha, jf_gongitsune, jf_nezumi, jf_tebukuro)
- Emotion support through text tags (e.g., [joy:0.8])
- Simple REST API

## Installation

### Using Docker (Recommended)

1. Start the TTS Service using the provided script:

```bash
./start_tts_service.sh
```

2. The service will be available at http://localhost:5000

3. To stop the service:

```bash
./stop_tts_service.sh
```

### Manual Installation

If you prefer to run the TTS Service without Docker, you can follow these steps:

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

4. Run the service:

```bash
cd tts_service
python app.py
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
    
    # Generate speech
    output_path = client.generate_speech(
        text="こんにちは、私はダオコです。[joy:0.8]",
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

### Docker Issues

If you encounter issues with Docker, make sure Docker and Docker Compose are installed and running:

```bash
docker --version
docker-compose --version
docker ps
```

### TTS Service Issues

If you encounter issues with the TTS Service, check the logs:

```bash
docker-compose -f tts_service/docker-compose.yml logs
```

### MeCab Issues

If you encounter issues with MeCab, make sure it's properly installed and the dictionary is available:

```bash
# Check MeCab installation
mecab -v

# Check MeCab dictionary
mecab -D
```
