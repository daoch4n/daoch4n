# Kokoro-82M TTS Integration with Live2D Character (Daoko)

This document describes the integration of the Kokoro-82M speech synthesis model with the Live2D character (Daoko) in the project.

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

The Kokoro TTS integration can be configured using the YAML configuration file. A sample configuration file is provided at `docs/conf/kokoro_tts_daoko.yaml`.

### Key Configuration Parameters

- `TTS_ENGINE`: Set to "kokoro_tts" to use the Kokoro TTS engine
- `TTS_VOICE`: The voice to use (default: "af_heart")
- `TTS_LANGUAGE`: The language code (default: "en")
- `TTS_DEVICE`: The device to use for inference ("cuda" or "cpu")
- `TTS_REPO_ID`: (Optional) Repository ID for a custom Kokoro model
- `TTS_EMOTION_MAPPING`: Mapping from emotion tags to Kokoro voice styles

Example configuration:
```yaml
TTS_CONFIG:
  TTS_ENGINE: "kokoro_tts"
  TTS_VOICE: "af_heart"
  TTS_LANGUAGE: "en"
  TTS_DEVICE: "cpu"  # Use CPU to avoid CUDA version conflicts
  # No need to specify TTS_REPO_ID - will use the default Kokoro-82M model
  TTS_CACHE_DIR: "cache"
  TTS_SAMPLE_RATE: 24000
  TTS_OUTPUT_FORMAT: "wav"
  TTS_EMOTION_MAPPING:
    joy: "happy"
    sadness: "sad"
    anger: "angry"
    fear: "fearful"
    surprise: "surprised"
    disgust: "disgusted"
    neutral: "neutral"
    smirk: "happy"
```

If you want to use a specific model version or a different model, you can specify the `TTS_REPO_ID` parameter:

```yaml
TTS_CONFIG:
  # Other parameters...
  TTS_REPO_ID: "hexgrad/Kokoro-82M"  # Explicitly use this model
```

## Usage

To use the Kokoro TTS engine with Daoko, simply set the TTS engine to "kokoro_tts" in your configuration file and provide the necessary parameters.

### Emotion-Aware Speech Synthesis

The Kokoro TTS engine supports emotion-aware speech synthesis by mapping emotion tags in the text to appropriate voice styles. For example, if the text contains the emotion tag `[joy:0.8]`, the Kokoro TTS engine will use a happy voice style for that text.

The emotion mapping is defined in the configuration file and can be customized as needed.

### Available Voices

The Kokoro-82M model comes with several built-in voices. The default voice is "af_heart", but you can use any of the available voices:

- "af_heart"
- "en_us_001"
- "en_us_002"
- "en_us_003"
- "en_us_004"
- "en_us_005"
- "en_us_006"
- "en_us_007"
- "en_us_008"

For a complete list of available voices, refer to the [Kokoro-82M documentation](https://huggingface.co/hexgrad/Kokoro-82M/blob/main/VOICES.md).

## Integration with Emotion System

The Kokoro TTS engine integrates with the existing emotion system for Daoko. When an emotion tag is detected in the text, the engine:

1. Extracts the emotion tag and its intensity value
2. Maps the emotion to an appropriate voice style using the emotion mapping
3. Generates speech with the appropriate emotional inflection
4. The Live2D character (Daoko) then plays the generated audio while displaying the corresponding facial expression and body motion

This creates a cohesive experience where Daoko's speech, facial expressions, and body motions all match the emotional content of the conversation.

## Troubleshooting

### Common Issues

- **Model not found**: Ensure that the Kokoro-82M model is properly downloaded and the path is correctly specified in the configuration file.
- **CUDA out of memory**: If you encounter CUDA out of memory errors, try using a smaller batch size or switch to CPU inference.
- **Audio quality issues**: Adjust the sample rate or try a different voice to improve audio quality.

### Logs

Check the logs for any error messages related to the Kokoro TTS engine. The logs can provide valuable information for troubleshooting issues.

## References

- [Kokoro-82M on Hugging Face](https://huggingface.co/hexgrad/Kokoro-82M)
- [Kokoro GitHub Repository](https://github.com/hexgrad/kokoro)
- [StyleTTS 2 Paper](https://arxiv.org/abs/2306.07691)
- [ISTFTNet Paper](https://arxiv.org/abs/2203.02395)
