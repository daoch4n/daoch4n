#!/usr/bin/env python3
"""
Test script for the Kokoro-82M TTS integration.

This script tests the Kokoro TTS engine by generating speech for a sample text
and playing it back.
"""

import os
import sys
import argparse
import yaml
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from open_llm_vtuber.tts.tts_factory import TTSFactory


def load_config(config_path):
    """Load configuration from a YAML file."""
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    return config


def test_kokoro_tts(config_path=None, text=None, output_path=None, play_audio=True):
    """
    Test the Kokoro TTS engine.

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
    if "tts_config" in config and "kokoro_tts" in config["tts_config"]:
        # Extract the Kokoro TTS configuration
        kokoro_config = config["tts_config"]["kokoro_tts"]
        tts_config = {
            "TTS_ENGINE": "kokoro_tts",
            "TTS_VOICE": kokoro_config.get("voice"),
            "TTS_LANGUAGE": kokoro_config.get("language"),
            "TTS_DEVICE": kokoro_config.get("device"),
            "TTS_CACHE_DIR": kokoro_config.get("cache_dir"),
            "TTS_SAMPLE_RATE": kokoro_config.get("sample_rate"),
            "TTS_OUTPUT_FORMAT": kokoro_config.get("output_format"),
            "TTS_EMOTION_MAPPING": kokoro_config.get("emotion_mapping"),
        }
    else:
        # Fallback to the old format
        tts_config = config.get("TTS_CONFIG", {})

    # Create the TTS engine
    kwargs = {
        "engine_type": tts_config.get("TTS_ENGINE", "kokoro_tts"),
        "voice": tts_config.get("TTS_VOICE", "af_heart"),
        "language": tts_config.get("TTS_LANGUAGE", "en"),
        "device": "cpu",  # Force CPU mode to avoid CUDA issues
        "cache_dir": tts_config.get("TTS_CACHE_DIR", "cache"),
        "sample_rate": tts_config.get("TTS_SAMPLE_RATE", 24000),
        "output_format": tts_config.get("TTS_OUTPUT_FORMAT", "wav"),
        "emotion_mapping": tts_config.get("TTS_EMOTION_MAPPING", None),
    }

    # Only add repo_id if it's specified in the config
    if "TTS_REPO_ID" in tts_config:
        kwargs["repo_id"] = tts_config["TTS_REPO_ID"]

    # Print the configuration for debugging
    print(f"Using TTS configuration:")
    print(f"  Engine: {kwargs['engine_type']}")
    print(f"  Voice: {kwargs['voice']}")
    print(f"  Language: {kwargs['language']}")
    print(f"  Device: {kwargs['device']}")
    print(f"  Cache directory: {kwargs['cache_dir']}")

    # Create the TTS engine
    try:
        tts_engine = TTSFactory.get_tts_engine(**kwargs)
    except Exception as e:
        print(f"Error creating TTS engine: {e}")
        raise

    # Generate speech
    print(f"Generating speech for text: {text}")
    output_file = tts_engine.generate_audio(text, output_path or "test_kokoro")

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
    """List all available voices in the Kokoro model."""
    print("Available voices in Kokoro-82M model:")
    print("\nJapanese Female Voices (Recommended for Daoko):")
    print("- jf_alpha (Japanese female voice - recommended for Daoko)")
    print("- jf_gongitsune (Japanese female voice)")
    print("- jf_nezumi (Japanese female voice)")
    print("- jf_tebukuro (Japanese female voice)")
    print("\nOther Voices:")
    print("- af_heart (African female voice)")
    print("- en_us_001 to en_us_008 (English US voices)")
    print("- zh_001 to zh_010 (Chinese voices)")
    print("\nFor more voices, check the Kokoro-82M documentation.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test the Kokoro TTS engine")
    parser.add_argument("--config", help="Path to the configuration file")
    parser.add_argument("--text", help="Text to synthesize")
    parser.add_argument("--output", help="Path to save the generated audio file")
    parser.add_argument("--no-play", action="store_true", help="Don't attempt to play the audio")
    parser.add_argument("--voice", help="Voice to use (e.g., af_heart, jf_alpha, jf_gongitsune, jf_nezumi, jf_tebukuro)")
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
    if voice:
        print(f"Using voice: {voice}")

    # Load the configuration
    config_path = args.config

    # Create a custom configuration with the specified voice
    custom_config = None
    if voice:
        if not config_path:
            config_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "conf.yaml"
            )

        # Load the configuration
        custom_config = load_config(config_path)

        # Update the voice in the configuration
        if "tts_config" in custom_config and "kokoro_tts" in custom_config["tts_config"]:
            custom_config["tts_config"]["kokoro_tts"]["voice"] = voice
        elif "TTS_CONFIG" in custom_config:
            # Fallback to the old format
            custom_config["TTS_CONFIG"]["TTS_VOICE"] = voice

    # Run the test with the custom configuration
    if custom_config:
        # Create a temporary configuration file
        temp_config_path = "temp_kokoro_config.yaml"
        with open(temp_config_path, 'w') as f:
            yaml.dump(custom_config, f)

        # Use the temporary configuration file
        test_kokoro_tts(temp_config_path, text, output, not args.no_play)

        # Clean up the temporary file
        try:
            os.remove(temp_config_path)
        except:
            pass
    else:
        # Use the original configuration file
        test_kokoro_tts(config_path, text, output, not args.no_play)
