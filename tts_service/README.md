# Japanese TTS Microservice

This microservice provides a simple API for generating Japanese speech from text using Kokoro TTS.

## Features

- Japanese text-to-speech synthesis
- Support for multiple voices (jf_alpha, jf_gongitsune, jf_nezumi, jf_tebukuro)
- Emotion support through text tags (e.g., [joy:0.8])
- Simple REST API

## Installation

### Using Docker (Recommended)

1. Build and start the service using Docker Compose:

```bash
docker-compose up -d
```

2. The service will be available at http://localhost:5000

### Manual Installation

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
pip install -r requirements.txt
```

4. Run the service:

```bash
python app.py
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

## Client Library

A Python client library is available in the main application:

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

## Troubleshooting

### MeCab Issues

If you encounter issues with MeCab, make sure it's properly installed and the dictionary is available:

```bash
# Check MeCab installation
mecab -v

# Check MeCab dictionary
mecab -D
```

### Audio Generation Issues

If you encounter issues with audio generation, check the logs:

```bash
docker-compose logs
```

Or if running manually:

```bash
cat tts_service.log
```
