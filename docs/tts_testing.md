# TTS Testing Guide

This document explains how to use the unified TTS testing script to test different TTS engines and voices.

## Overview

The project includes a unified TTS testing script (`test_tts.sh`) that consolidates functionality from multiple test scripts and adds command-line flags for different functionalities. This script makes it easy to test different TTS engines and voices without having to remember the specific commands for each engine.

## Usage

```bash
./test_tts.sh [options]
```

### Options

- `--engine, -e ENGINE`: TTS engine to use (e.g., alltalk) [default: alltalk]
- `--voice, -v VOICE`: Voice to use for TTS (specific to the chosen engine)
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

Test AllTalk TTS with a specific voice:
```bash
./test_tts.sh --engine alltalk --voice en_US-ljspeech-high.onnx --text "Hello world"
```

Test AllTalk TTS with RVC:
```bash
./test_tts.sh --engine alltalk --voice en_US-ljspeech-high.onnx --rvc-enabled --rvc-model "your_rvc_model_name" --text "Testing RVC."
```

## Available TTS Engines

This script primarily supports engines that have a command-line interface or a test script that can be wrapped by `test_tts.sh`.

### AllTalk TTS

The AllTalk TTS engine is a local text-to-speech system that supports voice cloning and RVC voice conversion.

#### Available Voices

- `en_US-ljspeech-high.onnx` (default): English US voice
- Other voices depend on your AllTalk TTS installation

## Emotion Tags

Emotion tags are generally handled by the specific TTS engine being called. This script passes the text through. For AllTalk TTS, it may interpret emotion tags based on its own configuration. Emotion tags are specified in square brackets and can include an optional intensity value:

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

Generated audio files are saved in the `cache` directory with the specified output name (or a default name if not specified) and the appropriate file extension (e.g., `.wav` or as specified by the underlying engine being tested).

## Troubleshooting

### Package Installation Issues

If you encounter package installation issues when trying to run the script or a specific engine through it, ensure all dependencies for that engine are correctly installed. Try running the script with the `--verbose` flag to see more detailed output:

```bash
VERBOSE=true ./test_tts.sh --engine alltalk --text "Testing"
```

### Other Issues

If you encounter other issues, please check the logs for error messages and refer to the documentation for the specific TTS engine you are attempting to test (e.g., AllTalk TTS).

- [AllTalk TTS](https://github.com/erew123/alltalk_tts)
