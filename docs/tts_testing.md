# TTS Testing Guide

This document explains how to use the unified TTS testing script to test different TTS engines and voices.

## Overview

The project includes a unified TTS testing script (`test_tts.sh`) that consolidates functionality from multiple test scripts and adds command-line flags for different functionalities. This script makes it easy to test different TTS engines and voices without having to remember the specific commands for each engine.

## Usage

```bash
./test_tts.sh [options]
```

### Options

- `--engine, -e ENGINE`: TTS engine to use (kokoro, alltalk) [default: kokoro]
- `--voice, -v VOICE`: Voice to use for TTS
- `--text, -t TEXT`: Text to synthesize
- `--output, -o OUTPUT`: Output file name (without extension)
- `--list-voices, -l`: List available voices and exit
- `--no-play, -n`: Don't attempt to play the audio
- `--verbose`: Show verbose output
- `--help, -h`: Show help message and exit

### Examples

List all available voices:
```bash
./test_tts.sh --list-voices
```

Test a specific voice:
```bash
./test_tts.sh --voice jf_alpha
```

Test a specific voice with custom text:
```bash
./test_tts.sh --voice jf_alpha --text "こんにちは、私はダオコです。[joy:0.8]"
```

Test AllTalk TTS with a specific voice:
```bash
./test_tts.sh --engine alltalk --voice en_US-ljspeech-high.onnx
```

## Available TTS Engines

### Kokoro TTS

The Kokoro-82M TTS engine is a lightweight, high-quality TTS model with emotional capabilities. It includes support for the Misaki tokenizer for Japanese language processing.

#### Available Voices

- `af_heart` (default): African female voice
- `en_us_001` to `en_us_008`: English US voices
- `jf_alpha`, `jf_gongitsune`, `jf_nezumi`, `jf_tebukuro`: Japanese female voices
- `zh_001` to `zh_010`: Chinese voices

### AllTalk TTS

The AllTalk TTS engine is a local text-to-speech system that supports voice cloning and RVC voice conversion.

#### Available Voices

- `en_US-ljspeech-high.onnx` (default): English US voice
- Other voices depend on your AllTalk TTS installation

## Emotion Tags

Both TTS engines support emotion tags in the text. Emotion tags are specified in square brackets and can include an optional intensity value:

```
Hello, I'm happy! [joy:0.8]
```

Available emotions:
- `joy`: Happy/excited
- `sadness`: Sad/downcast
- `anger`: Angry/frustrated
- `fear`: Fearful/anxious
- `surprise`: Surprised
- `disgust`: Disgusted
- `neutral`: Neutral (default)
- `smirk`: Mischievous/playful

## Output Files

Generated audio files are saved in the `cache` directory with the specified output name (or a default name if not specified) and the appropriate file extension (`.wav` for Kokoro TTS, `.wav` or the specified format for AllTalk TTS).

## Troubleshooting

### Model Files Not Found

If you encounter an error about model files not being found, make sure the Kokoro-82M model files are available at `~/alltalk_tts/models/kokoro/`.

### Package Installation Issues

If you encounter package installation issues, try running the script with the `--verbose` flag to see more detailed output:

```bash
VERBOSE=true ./test_tts.sh --voice jf_alpha
```

### Other Issues

If you encounter other issues, please check the logs for error messages and refer to the documentation for the specific TTS engine:

- [Kokoro-82M on Hugging Face](https://huggingface.co/hexgrad/Kokoro-82M)
- [Misaki Tokenizer](https://github.com/hexgrad/misaki)
- [AllTalk TTS](https://github.com/erew123/alltalk_tts)
