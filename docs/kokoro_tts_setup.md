# Kokoro TTS Setup

This document describes how to set up the Kokoro TTS engine for the project.

## Overview

The Kokoro-82M TTS model is integrated with the main project environment using uv. This setup uses symbolic links to the model files to avoid duplicating large files.

## Prerequisites

1. Python 3.10 or higher
2. Kokoro-82M model files (located at ~/alltalk_tts/models/kokoro)
3. uv package manager (for managing Python dependencies)

## Simplified Setup

The easiest way to set up the Kokoro TTS engine is to use the provided test script:

```bash
./test_kokoro.sh
```

This script will:
1. Create symbolic links to the Kokoro-82M model files
2. Create or use the main virtual environment
3. Install the required packages using uv
4. Test all Japanese female voices with sample text

## Manual Setup Steps

If you prefer to set up the Kokoro TTS engine manually, follow these steps:

### 1. Create Symbolic Links to Model Files

The setup script will automatically create symbolic links if they don't exist:

```bash
./setup_kokoro_symlink.sh
```

This script creates symbolic links from the Hugging Face cache directory to the Kokoro-82M model files.

### 2. Install Required Packages

Install the required packages in the main environment:

```bash
source .venv/bin/activate
uv pip install kokoro
uv pip install git+https://github.com/hexgrad/misaki.git
uv pip install -e .
```

The Misaki tokenizer is required for proper Japanese text processing.

### 3. Testing Specific Voices

You can test specific voices using the test script:

```bash
# Test a specific voice
./test_kokoro.sh jf_alpha "こんにちは、私はダオコです。[joy:0.8]"

# List all available voices
./test_kokoro.sh --list
```

### 5. Using Kokoro TTS in Your Code

To use the Kokoro TTS engine in your code, you can import it like this:

```python
from open_llm_vtuber.tts.kokoro_tts import TTSEngine

# Create a TTS engine instance
tts_engine = TTSEngine(
    voice="jf_alpha",  # Japanese female voice
    language="ja",     # Japanese language
    device="cpu"       # Use CPU for inference
)

# Generate audio
output_file = tts_engine.generate_audio(
    "こんにちは、私はダオコです。[joy:0.8]",  # Text with emotion tag
    "daoko_greeting"                      # Output file name (without extension)
)

print(f"Generated audio file: {output_file}")
```

### 6. Testing Specific Voices

You can test specific voices using the test script:

```bash
# Test a specific voice
./test_kokoro.sh jf_alpha "こんにちは、私はダオコです。[joy:0.8]"

# List all available voices
./test_kokoro.sh --list
```

The script will generate audio files in the `cache` directory.

## Emotion Handling in Kokoro TTS

The Kokoro-82M TTS model doesn't directly support emotion tags or a `style` parameter. Instead, our implementation handles emotions by:

1. **Extracting emotion tags** from the text (e.g., `[joy:0.8]`, `[sadness:0.6]`)
2. **Adjusting speech parameters** based on the emotion and intensity:
   - **Speed**: Adjusts the speech rate based on emotion (faster for happy/excited, slower for sad)
   - **Voice**: Currently uses the base voice for all emotions

The emotion intensity affects how strongly the speech parameters are modified:
- Intensities below 0.3 use the default speech parameters
- Intensities between 0.3 and 1.0 gradually increase the effect on speech parameters

## Japanese Language Support

The Kokoro-82M TTS model includes several Japanese voices (prefixed with `jf_` for female voices):

- `jf_alpha`
- `jf_gongitsune`
- `jf_nezumi`
- `jf_tebukuro`

When using these voices, the implementation automatically:

1. Sets the language to Japanese (`ja`)
2. Uses the Misaki tokenizer for proper Japanese text processing
3. Adjusts speech parameters based on emotion tags:
   - Modifies speech speed based on emotion (faster for happy/excited, slower for sad)
   - Uses the base voice for all emotions (future versions may support voice blending)

To use a Japanese voice in your configuration:

```yaml
TTS_CONFIG:
  TTS_ENGINE: kokoro_tts
  TTS_VOICE: jf_alpha  # or any other Japanese voice
  TTS_LANGUAGE: ja
```

## Configuration

The virtual environment uses a simplified configuration file (`docs/conf/kokoro_tts_venv.yaml`) that:

1. Uses CPU inference instead of CUDA to avoid CUDA version conflicts
2. Uses the default Kokoro-82M model (no need to specify a custom model path)
3. Has the same emotion mapping as the main configuration file

You can modify this configuration file to suit your needs.

## Japanese Language Support

The Kokoro-82M TTS model includes several Japanese voices (prefixed with `jf_` for female voices):

- `jf_alpha`
- `jf_gongitsune`
- `jf_nezumi`
- `jf_tebukuro`

When using these voices, the implementation automatically:

1. Sets the language to Japanese (`ja`)
2. Uses the Misaki tokenizer for proper Japanese text processing
3. Adjusts speech parameters based on emotion tags:
   - Modifies speech speed based on emotion (faster for happy/excited, slower for sad)
   - Uses the base voice for all emotions (future versions may support voice blending)

To use a Japanese voice, set the following in your configuration:

```yaml
TTS_CONFIG:
  TTS_ENGINE: kokoro_tts
  TTS_VOICE: jf_alpha  # or any other Japanese voice
  TTS_LANGUAGE: ja
```

The Misaki tokenizer is automatically installed as part of the setup process and is used to properly process Japanese text before sending it to the Kokoro-82M model.

## Emotion Handling in Kokoro TTS

The Kokoro-82M TTS model doesn't directly support emotion tags or a `style` parameter. Instead, our implementation handles emotions by:

1. **Extracting emotion tags** from the text (e.g., `[joy:0.8]`, `[sadness:0.6]`)
2. **Adjusting speech parameters** based on the emotion and intensity:
   - **Speed**: Adjusts the speech rate based on emotion (faster for happy/excited, slower for sad)
   - **Voice**: Currently uses the base voice for all emotions

The emotion intensity affects how strongly the speech parameters are modified:
- Intensities below 0.3 use the default speech parameters
- Intensities between 0.3 and 1.0 gradually increase the effect on speech parameters

Future enhancements may include:
- Voice blending for different emotions
- Pitch adjustments based on emotion
- Custom voice files optimized for specific emotions

## Integration with the Main Application

The Kokoro TTS engine is now integrated with the main application. To use it, simply set the TTS model to `kokoro_tts` in your configuration file:

```yaml
TTS_CONFIG:
  tts_model: kokoro_tts
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

## Troubleshooting

### Model Files Not Found

If the Kokoro TTS engine can't find the model files, make sure the symbolic links are set up correctly:

```bash
mkdir -p models/kokoro
ln -sf ~/alltalk_tts/models/kokoro/* models/kokoro/
./setup_kokoro_symlink.sh
```

### CUDA Version Conflicts

If you encounter CUDA version conflicts, try using CPU inference by setting `device: "cpu"` in your configuration file.

### Japanese Text Not Processed Correctly

If Japanese text is not processed correctly, make sure the Misaki tokenizer is installed:

```bash
source .venv/bin/activate
uv pip install git+https://github.com/hexgrad/misaki.git
```

### Other Issues

If you encounter other issues, please check the logs for error messages and refer to the [Kokoro-82M documentation](https://huggingface.co/hexgrad/Kokoro-82M) for more information.

## References

- [Kokoro-82M on Hugging Face](https://huggingface.co/hexgrad/Kokoro-82M)
- [Misaki Tokenizer](https://github.com/hexgrad/misaki)
