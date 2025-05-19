# Kokoro-82M TTS Integration with Live2D Character (Daoko)

This document describes the integration of the Kokoro-82M speech synthesis model with the Live2D character (Daoko) in the project.

> **Note**: We have moved to a microservice architecture for the Kokoro TTS integration. Please see the [TTS Service Integration](tts_service_integration.md) document for the latest approach.

## Overview

The Kokoro-82M model is an open-weight TTS model with 82 million parameters. Despite its lightweight architecture, it delivers comparable quality to larger models while being significantly faster and more cost-efficient. With Apache-licensed weights, Kokoro can be deployed anywhere from production environments to personal projects.

This integration allows Daoko to speak using the Kokoro-82M voice model, with appropriate emotional inflections that match her current emotional state.

## Features

- High-quality speech synthesis with the Kokoro-82M model
- Emotion-aware speech synthesis that matches Daoko's emotional state
- Integration with the existing emotion system for facial expressions and body motions
- Support for multiple languages (primarily English)
- Efficient performance suitable for real-time applications

## Installation

### Prerequisites

- Git LFS (Large File Storage)
- Python 3.8+
- PyTorch
- Kokoro Python package

### Installation Steps

1. Install Git LFS:
   ```bash
   sudo apt-get update && sudo apt-get install -y git-lfs
   git lfs install
   ```

2. Clone the Kokoro-82M model:
   ```bash
   mkdir -p ~/alltalk_tts/models/kokoro
   cd ~/alltalk_tts/models/kokoro
   git lfs clone https://huggingface.co/hexgrad/Kokoro-82M .
   ```

3. Install the Kokoro Python package:
   ```bash
   pip install kokoro
   ```

## Configuration

> **Note**: The configuration has changed with the microservice approach. Please see the [TTS Service Integration](tts_service_integration.md) document for the latest configuration.

### Legacy Configuration (Direct Integration)

The direct Kokoro TTS integration is configured in the main `conf.yaml` file.

### Key Configuration Parameters

- `tts_model`: Set to "kokoro_tts" to use the Kokoro TTS engine directly
- `voice`: The voice to use (recommended: "jf_alpha" for Daoko)
- `language`: The language code (recommended: "ja" for Japanese)
- `device`: The device to use for inference ("cuda" or "cpu")
- `emotion_mapping`: Mapping from emotion tags to Kokoro voice styles

Example configuration:
```yaml
tts_config:
  tts_model: 'kokoro_tts'

  kokoro_tts:
    voice: "jf_alpha"  # Japanese female voice for Daoko
    language: "ja"     # Japanese language
    device: "cpu"      # Use CPU to avoid CUDA version conflicts
    cache_dir: "cache"
    sample_rate: 24000
    output_format: "wav"
    emotion_mapping:
      joy: "happy"
      sadness: "sad"
      anger: "angry"
      fear: "fearful"
      surprise: "surprised"
      disgust: "disgusted"
      neutral: "neutral"
      smirk: "happy"
```

### New Configuration (Microservice Approach)

The new TTS Service microservice approach is configured as follows:

```yaml
tts_config:
  tts_model: 'tts_service'

  # TTS Service configuration (microservice for Japanese TTS)
  tts_service:
    base_url: "http://localhost:5000"  # URL of the TTS Service
```

### Dependencies

The Kokoro TTS integration requires the following dependencies:

1. **Python Packages**:
   - `kokoro` - The main Kokoro TTS package
   - `misaki` - Japanese tokenizer for Kokoro
   - `pyopenjtalk` - Japanese text processing
   - `fugashi[unidic-lite]` - Japanese morphological analyzer with dictionary
   - `unidic-lite` - Japanese dictionary for MeCab
   - `jaconv` - Japanese text conversion
   - `mojimoji` - Japanese character conversion
   - `spacy` - Text processing

2. **System Dependencies**:
   - `mecab` - Japanese morphological analyzer
   - `libmecab-dev` - MeCab development files
   - `mecab-ipadic-utf8` - MeCab dictionary

These dependencies are automatically installed when you run the `test_tts.sh` script or the `fix_kokoro_env.sh` script.

## Usage

> **Note**: The usage has changed with the microservice approach. Please see the [TTS Service Integration](tts_service_integration.md) document for the latest usage instructions.

### Legacy Usage (Direct Integration)

To use the Kokoro TTS engine directly with Daoko, set the TTS engine to "kokoro_tts" in your configuration file and provide the necessary parameters.

### New Usage (Microservice Approach)

To use the TTS Service microservice with Daoko:

1. Start the TTS Service:
   ```bash
   ./start_tts_service.sh
   ```

2. Set the TTS engine to "tts_service" in your configuration file:
   ```yaml
   tts_config:
     tts_model: 'tts_service'
   ```

3. The main application will automatically use the TTS Service for speech synthesis.

### Emotion-Aware Speech Synthesis

The Kokoro TTS engine supports emotion-aware speech synthesis by mapping emotion tags in the text to appropriate voice styles. For example, if the text contains the emotion tag `[joy:0.8]`, the Kokoro TTS engine will use a happy voice style for that text.

The emotion mapping is defined in the configuration file and can be customized as needed.

### Available Voices

The Kokoro-82M model comes with several built-in voices. For Daoko, we recommend using the Japanese female voices:

#### Japanese Female Voices (Recommended for Daoko)
- `jf_alpha` (Japanese female voice - recommended for Daoko)
- `jf_gongitsune` (Japanese female voice)
- `jf_nezumi` (Japanese female voice)
- `jf_tebukuro` (Japanese female voice)

#### Chinese Female Voices
- `zf_xiaobei` (Chinese female voice)
- `zf_xiaoni` (Chinese female voice)
- `zf_xiaoxiao` (Chinese female voice)
- `zf_xiaoyi` (Chinese female voice)

For a complete list of available voices, refer to the [Kokoro-82M documentation](https://huggingface.co/hexgrad/Kokoro-82M/blob/main/VOICES.md).

## Integration with Emotion System

The Kokoro TTS engine integrates with the existing emotion system for Daoko. When an emotion tag is detected in the text, the engine:

1. Extracts the emotion tag and its intensity value
2. Maps the emotion to an appropriate voice style using the emotion mapping
3. Generates speech with the appropriate emotional inflection
4. The Live2D character (Daoko) then plays the generated audio while displaying the corresponding facial expression and body motion

This creates a cohesive experience where Daoko's speech, facial expressions, and body motions all match the emotional content of the conversation.

## Troubleshooting

> **Note**: The troubleshooting steps have changed with the microservice approach. Please see the [TTS Service Integration](tts_service_integration.md) document for the latest troubleshooting information.

### Legacy Troubleshooting (Direct Integration)

#### Common Issues

- **Model not found**: Ensure that the Kokoro-82M model is properly downloaded and the path is correctly specified in the configuration file.
- **CUDA out of memory**: If you encounter CUDA out of memory errors, try using a smaller batch size or switch to CPU inference.
- **Audio quality issues**: Adjust the sample rate or try a different voice to improve audio quality.
- **Japanese text processing issues**: Make sure all the required Japanese language dependencies are installed.

#### Missing Dependencies

If you encounter errors related to missing dependencies, run the `fix_kokoro_env.sh` script to install all required dependencies:

```bash
./fix_kokoro_env.sh
```

#### MeCab Issues

If you encounter issues with MeCab, the scripts will attempt to fix the configuration automatically. However, if you still have issues, you can try the following:

```bash
# Check MeCab installation
mecab -v

# Check MeCab dictionary
mecab -D

# Create MeCab configuration file manually
sudo mkdir -p /usr/local/etc
echo "dicdir = /var/lib/mecab/dic/ipadic-utf8" | sudo tee /usr/local/etc/mecabrc

# Test MeCab
echo "テスト" | mecab
```

If you see an error like `param.cpp(69) [ifs] no such file or directory: /usr/local/etc/mecabrc`, it means the MeCab configuration file is missing. The scripts should create this file automatically, but you can also create it manually as shown above.

#### Testing

You can test the Kokoro TTS integration using the `test_tts.sh` script:

```bash
# List available voices
./test_tts.sh --list-voices

# Test with Japanese female alpha voice (recommended for Daoko)
./test_tts.sh --voice jf_alpha

# Test with a specific text
./test_tts.sh --voice jf_alpha --text "こんにちは、私はダオコです。よろしくお願いします。[joy:0.8]"
```

### New Troubleshooting (Microservice Approach)

#### TTS Service Issues

If you encounter issues with the TTS Service, check the Docker logs:

```bash
docker-compose -f tts_service/docker-compose.yml logs
```

#### Testing the TTS Service

You can test the TTS Service using the provided test script:

```bash
cd tts_service
python test_service.py --text "こんにちは、私はダオコです。よろしくお願いします。[joy:0.8]"
```

#### Checking TTS Service Health

You can check if the TTS Service is healthy:

```bash
curl http://localhost:5000/health
```

#### Logs

Check the logs for any error messages related to the TTS Service. The logs can provide valuable information for troubleshooting issues.

## References

- [Kokoro-82M on Hugging Face](https://huggingface.co/hexgrad/Kokoro-82M)
- [Kokoro GitHub Repository](https://github.com/hexgrad/kokoro)
- [StyleTTS 2 Paper](https://arxiv.org/abs/2306.07691)
- [ISTFTNet Paper](https://arxiv.org/abs/2203.02395)
