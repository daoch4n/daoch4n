#!/usr/bin/env python3
"""
Test script for AllTalk TTS integration with RVC voice conversion.

This script tests the AllTalk TTS integration by generating a test audio file
using the AllTalk TTS engine with RVC voice conversion.
"""

import os
import sys
import argparse
import yaml
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from open_llm_vtuber.tts.tts_factory import TTSFactory
from loguru import logger


def load_config(config_path):
    """Load configuration from a YAML file."""
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    return config


def test_alltalk_tts(config_path=None, text=None, output_path=None, play_audio=True):
    """
    Test the AllTalk TTS engine.

    Args:
        config_path: Path to the configuration file
        text: Text to synthesize (if None, uses a default test text)
        output_path: Path to save the generated audio file (if None, uses a default path)
        play_audio: Whether to attempt to play the audio after generation
    """
    # Ensure cache directory exists
    cache_dir = "cache"
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)
        print(f"Created cache directory: {cache_dir}")

    # Default test text with emotion tags
    if text is None:
        text = (
            "Hello, I'm Daoko! [joy:0.8] "
            "I'm so happy to meet you! [joy:0.9] "
            "Sometimes I feel a bit sad though. [sadness:0.6] "
            "And occasionally I get angry too! [anger:0.7] "
            "But most of the time, I'm just neutral. [neutral] "
            "Oh! That surprised me! [surprise:0.8] "
            "Anyway, I hope we can be friends! [joy:0.7]"
        )

    # Load configuration
    if config_path is None:
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "conf.yaml"
        )

    config = load_config(config_path)

    # Extract the TTS configuration from the conf.yaml file
    tts_config = {}
    if "tts_config" in config:
        if config["tts_config"].get("tts_model") == "alltalk_tts" and "alltalk_tts" in config["tts_config"]:
            # Extract the AllTalk TTS configuration
            alltalk_config = config["tts_config"]["alltalk_tts"]
            tts_config = {
                "TTS_ENGINE": "alltalk_tts",
                "TTS_API_URL": alltalk_config.get("api_url"),
                "TTS_VOICE": alltalk_config.get("voice"),
                "TTS_LANGUAGE": alltalk_config.get("language"),
                "TTS_RVC_ENABLED": alltalk_config.get("rvc_enabled"),
                "TTS_RVC_MODEL": alltalk_config.get("rvc_model"),
                "TTS_RVC_PITCH": alltalk_config.get("rvc_pitch"),
                "TTS_OUTPUT_FORMAT": alltalk_config.get("output_format"),
                "TTS_EMOTION_MAPPING": alltalk_config.get("emotion_mapping"),
            }
        else:
            # Fallback to the TTS_CONFIG if available
            tts_config = config.get("TTS_CONFIG", {})

    # Create the TTS engine
    kwargs = {
        "engine_type": tts_config.get("TTS_ENGINE", "alltalk_tts"),
        "api_url": tts_config.get("TTS_API_URL", "http://127.0.0.1:7851"),
        "voice": tts_config.get("TTS_VOICE", "en_US-ljspeech-high.onnx"),
        "language": tts_config.get("TTS_LANGUAGE", "ja"),
        "rvc_enabled": tts_config.get("TTS_RVC_ENABLED", False),
        "rvc_model": tts_config.get("TTS_RVC_MODEL", "Disabled"),
        "rvc_pitch": tts_config.get("TTS_RVC_PITCH", 0),
        "output_format": tts_config.get("TTS_OUTPUT_FORMAT", "wav"),
        "emotion_mapping": tts_config.get("TTS_EMOTION_MAPPING", None),
    }

    # Print the configuration for debugging
    print(f"Using TTS configuration:")
    print(f"  Engine: {kwargs['engine_type']}")
    print(f"  API URL: {kwargs['api_url']}")
    print(f"  Voice: {kwargs['voice']}")
    print(f"  Language: {kwargs['language']}")
    print(f"  RVC Enabled: {kwargs['rvc_enabled']}")
    print(f"  RVC Model: {kwargs['rvc_model']}")
    print(f"  RVC Pitch: {kwargs['rvc_pitch']}")
    print(f"  Output Format: {kwargs['output_format']}")

    # Create the TTS engine
    try:
        tts_engine = TTSFactory.get_tts_engine(**kwargs)
    except Exception as e:
        print(f"Error creating TTS engine: {e}")
        raise

    # Generate speech
    print(f"Generating speech for text: {text}")
    output_file = tts_engine.generate_audio(text, output_path or "test_alltalk")

    print(f"Generated audio file: {output_file}")

    # Print information about the generated audio file
    print(f"\nAudio generation successful!")
    print(f"Generated audio file: {output_file}")
    print(f"You can play this file with any audio player.")

    # Play the audio if requested
    if play_audio:
        if not os.path.exists(output_file):
            print(f"Error: Audio file {output_file} does not exist.")
        else:
            print("\nAttempting to play the audio...")
            print(f"Please play the audio file manually: {output_file}")

    return output_file


def list_available_voices():
    """List all available voices in the AllTalk TTS server."""
    print("Available voices in AllTalk TTS server:")
    print("- kokoro_jf_alpha (Kokoro Japanese female voice - recommended for Daoko)")
    print("- kokoro_af_heart (Kokoro African female voice)")
    print("- kokoro_en_us_001 to kokoro_en_us_008 (Kokoro English US voices)")
    print("- kokoro_jf_gongitsune, kokoro_jf_nezumi, kokoro_jf_tebukuro (Other Kokoro Japanese female voices)")
    print("- en_US-ljspeech-high.onnx (English US voice - high quality)")
    print("- en_US-ljspeech-medium.onnx (English US voice - medium quality)")
    print("- en_US-ljspeech-low.onnx (English US voice - low quality)")
    print("\nFor more voices, check the AllTalk TTS server API at /api/charactervoices")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test the AllTalk TTS engine")
    parser.add_argument("--config", help="Path to the configuration file")
    parser.add_argument("--text", help="Text to synthesize")
    parser.add_argument("--output", help="Path to save the generated audio file")
    parser.add_argument("--no-play", action="store_true", help="Don't attempt to play the audio")
    parser.add_argument("--voice", help="Voice to use (e.g., kokoro_jf_alpha, en_US-ljspeech-high.onnx)")
    parser.add_argument("--rvc-enabled", action="store_true", help="Enable RVC voice conversion")
    parser.add_argument("--rvc-model", help="RVC model to use for voice conversion")
    parser.add_argument("--rvc-pitch", type=int, help="Pitch adjustment for RVC voice conversion")
    parser.add_argument("--list-voices", action="store_true", help="List available voices")

    args = parser.parse_args()

    if args.list_voices:
        list_available_voices()
        sys.exit(0)

    # Set up the text and output path
    text = args.text
    output = args.output

    # If voice is specified, we'll pass it directly to the TTS engine
    voice = args.voice
    rvc_enabled = args.rvc_enabled
    rvc_model = args.rvc_model
    rvc_pitch = args.rvc_pitch

    # Load the configuration
    config_path = args.config

    # Create a custom configuration with the specified parameters
    custom_config = None
    if voice or rvc_enabled or rvc_model is not None or rvc_pitch is not None:
        if not config_path:
            config_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "conf.yaml"
            )

        # Load the configuration
        custom_config = load_config(config_path)

        # Print debug information
        print(f"Command line arguments:")
        print(f"  Voice: {voice}")
        print(f"  RVC Enabled: {rvc_enabled}")
        print(f"  RVC Model: {rvc_model}")
        print(f"  RVC Pitch: {rvc_pitch}")

        # Update the parameters in the configuration
        if "tts_config" in custom_config and "alltalk_tts" in custom_config["tts_config"]:
            if voice:
                custom_config["tts_config"]["alltalk_tts"]["voice"] = voice
            if rvc_enabled:
                custom_config["tts_config"]["alltalk_tts"]["rvc_enabled"] = True
            if rvc_model:
                custom_config["tts_config"]["alltalk_tts"]["rvc_model"] = rvc_model
            if rvc_pitch is not None:
                custom_config["tts_config"]["alltalk_tts"]["rvc_pitch"] = rvc_pitch
        elif "TTS_CONFIG" in custom_config:
            # Fallback to the old format
            if voice:
                custom_config["TTS_CONFIG"]["TTS_VOICE"] = voice
            if rvc_enabled:
                custom_config["TTS_CONFIG"]["TTS_RVC_ENABLED"] = True
            if rvc_model:
                custom_config["TTS_CONFIG"]["TTS_RVC_MODEL"] = rvc_model
            if rvc_pitch is not None:
                custom_config["TTS_CONFIG"]["TTS_RVC_PITCH"] = rvc_pitch

    # Run the test with the custom configuration
    if custom_config:
        # Create a temporary configuration file
        temp_config_path = "temp_alltalk_config.yaml"
        with open(temp_config_path, 'w') as f:
            yaml.dump(custom_config, f)

        # Use the temporary configuration file
        test_alltalk_tts(temp_config_path, text, output, not args.no_play)

        # Clean up the temporary file
        try:
            os.remove(temp_config_path)
        except:
            pass
    else:
        # Use the original configuration file
        test_alltalk_tts(config_path, text, output, not args.no_play)
