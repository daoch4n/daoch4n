# Kokoro TTS Virtual Environment Setup

This document explains how to set up a virtual environment for the Kokoro TTS integration to avoid dependency conflicts.

## Background

The Kokoro TTS integration requires specific versions of certain packages (like NumPy) that may conflict with the versions used by other parts of the project. To avoid these conflicts, we've created a virtual environment specifically for the Kokoro TTS integration.

## Setup Instructions

### 1. Install uv (if not already installed)

`uv` is a fast Python package installer and resolver. If you don't have it installed, you can install it with:

```bash
pip install uv
```

### 2. Create the Virtual Environment

```bash
mkdir -p .venv
uv venv .venv/kokoro-env
```

### 3. Install Dependencies

```bash
source .venv/kokoro-env/bin/activate
uv pip install -r kokoro-requirements.txt
pip install -e .
deactivate
```

### 4. Set Up Symbolic Link to Model Files

We've already downloaded the Kokoro-82M model files using Git LFS to `~/alltalk_tts/models/kokoro/`. To make these files accessible to the Kokoro package without downloading them again, we've created a script that sets up symbolic links:

```bash
./setup_kokoro_symlink.sh
```

This script creates symbolic links from the Hugging Face cache directory to our downloaded model files, allowing the Kokoro package to find and use them.

### 5. Fix the Virtual Environment

If you encounter issues with missing packages in the virtual environment, you can run the fix script:

```bash
./fix_kokoro_env.sh
```

This script ensures that all required packages are installed in the virtual environment, including:
- sounddevice
- soundfile
- pyyaml
- The project itself in development mode



### 6. Run the Test Script

We've created a wrapper script that:
1. Sets up symbolic links to the model files
2. Fixes the virtual environment
3. Activates the virtual environment
4. Runs the test script with the --no-play option (to avoid audio playback issues)
5. Deactivates the virtual environment

```bash
./run_kokoro_test.sh --text "Hello, I'm Daoko! [joy:0.8]" --output "daoko_greeting"
```

You can also specify a custom configuration file:

```bash
./run_kokoro_test.sh --config docs/conf/kokoro_tts_venv.yaml --text "Hello, I'm Daoko! [joy:0.8]" --output "daoko_greeting"
```

The script will generate an audio file but won't attempt to play it (to avoid audio playback issues). The location of the generated audio file will be displayed in the output.

### 7. Testing Different Voices

The Kokoro-82M model comes with several built-in voices. You can test different voices using the `--voice` parameter:

```bash
./run_kokoro_test.sh --voice "jf_alpha" --text "こんにちは、私はアルファです。" --output "alpha_greeting"
```

To see a list of available voices:

```bash
./run_kokoro_test.sh --list-voices
```

We've also created a convenience script for testing multiple voices:

```bash
# List all available voices
./test_voices.sh --list

# Test a specific voice
./test_voices.sh jf_alpha "こんにちは、私はアルファです。"

# Test all Japanese female voices
./test_voices.sh
```

The script will generate audio files for each voice in the `cache` directory.

### 8. Playing Audio Files

If you want to try playing the audio (which may fail depending on your system's audio configuration), you can run the test script directly:

```bash
source .venv/kokoro-env/bin/activate
python tests/test_kokoro_tts.py --text "Hello, I'm Daoko! [joy:0.8]" --output "daoko_greeting"
deactivate
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

To use the Kokoro TTS engine in the main application, you have two options:

### Option 1: Use the Virtual Environment

You can modify your application's startup script to activate the virtual environment before running the application:

```bash
#!/bin/bash
source .venv/kokoro-env/bin/activate
python -m src.open_llm_vtuber.main --config docs/conf/kokoro_tts_venv.yaml
deactivate
```

### Option 2: Fix the Dependency Conflicts

If you want to use the Kokoro TTS engine without a virtual environment, you'll need to fix the dependency conflicts by:

1. Downgrading NumPy to a version that's compatible with both Kokoro and your other dependencies
2. Ensuring that all other dependencies are compatible with this version of NumPy

This can be challenging and may require significant changes to your project's dependencies.

## Troubleshooting

### ImportError: cannot import name 'Inf' from 'numpy'

This error occurs when using a newer version of NumPy (2.x) with code that expects an older version. The solution is to use NumPy 1.24.3 in the virtual environment, which is compatible with the Kokoro package.

### CUDA Version Conflicts

If you encounter CUDA version conflicts, try using CPU inference by setting `TTS_DEVICE: "cpu"` in your configuration file.

### Other Issues

If you encounter other issues, please check the logs for error messages and refer to the [Kokoro-82M documentation](https://huggingface.co/hexgrad/Kokoro-82M) for more information.
