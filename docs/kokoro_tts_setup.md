# Kokoro TTS Setup

This document describes how to set up the Kokoro TTS engine for the project.

## Overview

The Kokoro-82M TTS model is integrated with the main project environment using uv. This setup uses symbolic links to the model files to avoid duplicating large files.

## Prerequisites

1. Python 3.10 or higher
2. Kokoro-82M model files (located at ~/alltalk_tts/models/kokoro)
3. uv package manager (for managing Python dependencies)

## Recommended Setup: TTS Microservice

The primary and recommended method for using Kokoro TTS is through the TTS microservice. Configure it by setting the TTS model to `kokoro_tts` in your main application's configuration file:

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
This approach is generally preferred for stability and separation of concerns.

For quick testing of Kokoro TTS functionality (e.g., if you are developing the TTS service itself or want to test voices in isolation), a dedicated script is available:

```bash
./test_kokoro.sh
```

This script will:
1. Create symbolic links to the Kokoro-82M model files
2. Create or use the main virtual environment
3. Install the required packages using uv
4. Test all Japanese female voices with sample text

## Manual Setup for Direct Integration (Alternative)

Direct integration involves using the Kokoro TTS engine (e.g., via `open_llm_vtuber.tts.kokoro_tts` as shown in "Using Kokoro TTS in Your Code" below) directly within your application. This method might be used for development, specific testing scenarios, or when a separate microservice is not desired.

If you choose this approach, follow these steps:

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

### 4. Using Kokoro TTS in Your Code

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

### 5. Configuration for Direct Integration

When using direct integration, you might manage configuration through a specific file (e.g., `docs/conf/kokoro_tts_venv.yaml` if using a dedicated virtual environment for testing TTS) or directly in your application code. This configuration typically specifies:
1. Use of CPU inference (to avoid CUDA conflicts).
2. The Kokoro-82M model to be used (often defaults to the standard one).
3. Emotion mapping settings, if applicable to your direct setup.

You can modify such configuration files or code to suit your direct integration needs.

## Japanese Language Support

The Kokoro-82M TTS model includes several Japanese voices (prefixed with `jf_` for female voices):

- `jf_alpha`
- `jf_gongitsune`
- `jf_nezumi`
- `jf_tebukuro`

When using these voices, the implementation (both in the microservice and direct integration) automatically:

1. Sets the language to Japanese (`ja`).
2. Uses the Misaki tokenizer for proper Japanese text processing. (For direct integration, ensure Misaki is installed in your environment as per "Manual Setup Steps").
3. Adjusts speech parameters based on emotion tags (see "Emotion Handling in Kokoro TTS" section).

To use a Japanese voice in your configuration for direct integration (the microservice config is shown above):
```yaml
# Example for direct integration configuration
TTS_CONFIG:
  TTS_ENGINE: kokoro_tts # This key might vary based on your direct integration's config structure
  TTS_VOICE: jf_alpha  # or any other Japanese voice
  TTS_LANGUAGE: ja     # Ensure language is set to Japanese
```
(Note: The specific YAML structure for direct integration configuration might differ from the microservice configuration shown earlier.)

The Misaki tokenizer is automatically installed as part of the setup process for direct integration (see step 2) and is used to properly process Japanese text before sending it to the Kokoro-82M model.

## Emotion Handling in Kokoro TTS

The way emotion tags (e.g., `[joy:0.8]`) affect speech output differs significantly between the TTS Microservice and Direct Integration using `KokoroWrapper`.

### TTS Microservice Emotion Handling

As detailed in `docs/kokoro_tts_integration.md`, the **TTS Microservice** actively processes emotion tags:
- It extracts the emotion and intensity from the first tag.
- It adjusts **speech speed** based on the emotion and intensity, using a configurable `emotion_mapping` (e.g., `joy: 1.2` for faster speech).
- It removes all emotion tags before sending the cleaned text to the Kokoro engine.
- It currently **does not** modify voice style or pitch based on these tags.

### Direct Integration (`KokoroWrapper`) Emotion Handling

When using `KokoroWrapper` for direct integration:
- The `KokoroWrapper` itself **does not implement any specific logic to parse emotion tags or modify speech parameters** (like speed or pitch) based on them.
- The input text, including any emotion tags, is passed **directly** to the underlying Kokoro TTS engine.
- Any effect these tags have on the generated speech is entirely dependent on the **native capabilities of the Kokoro TTS engine and the specific voice being used**. Some Kokoro voices might be designed to respond to certain embedded tags or SSML-like syntax, but this is not managed or standardized by the `KokoroWrapper`.
- The `emotion_mapping` section in `conf.yaml` (under `tts_config.kokoro_tts`) is **not used by `KokoroWrapper`** to adjust speech speed or other parameters. This configuration is primarily relevant for the TTS Microservice.
- If you require explicit and configurable control over speech parameters based on emotion tags (specifically for speed adjustments), using the **TTS Microservice is the recommended approach.**
- For direct integration, you would need to rely on the Kokoro engine's inherent features for any emotion or style expression, which may vary and might require different tagging formats than the `[emotion:intensity]` style.

(Note: Redundant sections have been removed or integrated above for clarity.)

## Troubleshooting

### Model Files Not Found

If the Kokoro TTS engine can't find the model files (either for microservice or direct integration), ensure you have run the symbolic link setup script:

```bash
./setup_kokoro_symlink.sh
```
This script creates symbolic links from the Hugging Face cache directory to the Kokoro-82M model files. If issues persist, verify the paths in the script and that the original model files exist at `~/alltalk_tts/models/kokoro/`.

### CUDA Version Conflicts

If you encounter CUDA version conflicts, try using CPU inference by setting `device: "cpu"` in your configuration file.

### Japanese Text Not Processed Correctly (for Direct Integration)

If Japanese text is not processed correctly during direct integration, make sure the Misaki tokenizer is installed in your Python environment:

```bash
source .venv/bin/activate
uv pip install git+https://github.com/hexgrad/misaki.git
```

### Other Issues

If you encounter other issues, please check the logs for error messages and refer to the [Kokoro-82M documentation](https://huggingface.co/hexgrad/Kokoro-82M) for more information.

## References

- [Kokoro-82M on Hugging Face](https://huggingface.co/hexgrad/Kokoro-82M)
- [Misaki Tokenizer](https://github.com/hexgrad/misaki)
