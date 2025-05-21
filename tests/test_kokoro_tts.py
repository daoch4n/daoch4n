#!/usr/bin/env python3
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for direct Kokoro-82M TTS integration using KokoroWrapper.

This script is designed to test the functionality of the Kokoro TTS engine when
integrated directly into the application via the `KokoroWrapper` class (obtained
from the `TTSFactory` with engine type "kokoro_tts").

It is distinct from `tts_service/test_service.py`, which tests the Kokoro TTS
microservice. This script focuses on the legacy/alternative direct integration
method, useful for development, specific testing scenarios, or when the
microservice is not used.

The script loads configuration from `conf.yaml`, allows overriding parameters
via command-line arguments, generates speech for a sample text, and optionally
attempts to play it back.
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
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        return config
    except FileNotFoundError:
        print(f"Error: Configuration file not found at {config_path}")
        sys.exit(1)
    except yaml.YAMLError as e:
        print(f"Error parsing YAML configuration file {config_path}: {e}")
        sys.exit(1)


def test_kokoro_tts(tts_params: dict, text_to_synthesize: str, output_file_path: str, play_audio_flag: bool):
    """
    Tests the Kokoro TTS engine using direct integration (KokoroWrapper).

    Args:
        tts_params: Dictionary containing parameters for TTS engine initialization
                    (voice, language, device, cache_dir, etc.).
        text_to_synthesize: Text to synthesize.
        output_file_path: Path to save the generated audio file.
        play_audio_flag: Whether to attempt to play the audio after generation.
    """
    # Ensure cache directory exists (used by KokoroWrapper if not overridden)
    default_cache_dir = tts_params.get("cache_dir", "cache")
    if not os.path.exists(default_cache_dir):
        try:
            os.makedirs(default_cache_dir)
            print(f"Created cache directory: {default_cache_dir}")
        except OSError as e:
            print(f"Warning: Could not create cache directory {default_cache_dir}: {e}. "
                  "Kokoro TTS might fail if caching is essential and paths are not writable.")

    # Construct kwargs for TTSFactory, ensuring 'engine_type' is set for KokoroWrapper
    factory_kwargs = {
        "engine_type": "kokoro_tts", # Crucial for selecting KokoroWrapper
        "voice": tts_params.get("voice", "jf_alpha"),
        "language": tts_params.get("language", "ja"),
        "device": tts_params.get("device", "cpu"), # Default to CPU for tests; can be overridden by conf.yaml via tts_params
        "cache_dir": tts_params.get("cache_dir", "cache"),
        "sample_rate": tts_params.get("sample_rate", 24000),
        "output_format": tts_params.get("output_format", "wav"),
        "emotion_mapping": tts_params.get("emotion_mapping"), # Will be None if not in tts_params
        "repo_id": tts_params.get("repo_id") # Will be None if not in tts_params
    }

    print("Initializing Kokoro TTS engine (direct integration via KokoroWrapper) with parameters:")
    for key, value in factory_kwargs.items():
        if value is not None: # Don't print params that are not set (like repo_id if None)
             print(f"  {key}: {value}")

    try:
        tts_engine = TTSFactory.get_tts_engine(**factory_kwargs)
    except Exception as e:
        print(f"Error creating TTS engine (KokoroWrapper): {e}")
        print("Please ensure that Kokoro TTS (direct integration) is correctly set up,")
        print("including MeCab and any necessary model files if not using default repo.")
        print("Refer to `docs/kokoro_tts_setup.md` for direct integration guidance.")
        raise # Re-raise the exception to fail the test

    print(f"\nGenerating speech for text: \"{text_to_synthesize[:100]}...\"")
    try:
        generated_file = tts_engine.generate_audio(text_to_synthesize, output_file_path)
        print(f"Generated audio file: {generated_file}")
    except Exception as e:
        print(f"Error during speech generation: {e}")
        raise # Re-raise the exception to fail the test

    print(f"\nAudio generation successful!")
    print(f"Generated audio file: {generated_file}")
    print(f"You can play this file with any audio player.")

    if play_audio_flag:
        if not os.path.exists(generated_file):
            print(f"Error: Audio file {generated_file} does not exist (should not happen).")
        else:
            print("\nAttempting to play the audio...")
            # Platform-dependent audio playback is complex.
            # For automated tests, usually skip playback or use a library that handles it.
            # For manual testing, this print is often sufficient.
            print(f"To play the audio, please open the file manually: {generated_file}")
            # Example for macOS: subprocess.call(["afplay", generated_file])
            # Example for Linux: subprocess.call(["xdg-open", generated_file])
            # Example for Windows: os.startfile(generated_file)

    return generated_file


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Test direct Kokoro TTS integration (KokoroWrapper).",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "--config",
        default=os.path.join(Path(__file__).resolve().parent.parent, "conf.yaml"),
        help="Path to the main configuration file (conf.yaml)."
    )
    parser.add_argument(
        "--text",
        default=(
            "こんにちは、私は音読さんです。[joy:0.8] "
            "あなたに会えてとても嬉しいです。[joy:0.9] "
            "時々、少し悲しい気持ちになることもあります。[sadness:0.6] "
            "でも、ほとんどの場合は元気です。[neutral] "
            "よろしくお願いします！[joy:0.7]"
        ),
        help="Text to synthesize."
    )
    parser.add_argument(
        "--output",
        default=os.path.join("cache", "test_kokoro_direct_output.wav"),
        help="Path to save the generated audio file."
    )
    parser.add_argument(
        "--no-play",
        action="store_true",
        help="Don't attempt to guide manual playback of the audio."
    )
    parser.add_argument(
        "--voice",
        type=str,
        default=None, # Will use value from conf.yaml if not specified
        help="Specific Kokoro voice to use (e.g., jf_alpha). Overrides conf.yaml."
    )
    parser.add_argument(
        "--device",
        type=str,
        default=None, # Will use value from conf.yaml, or 'cpu' as per test_kokoro_tts default
        help="Device to use ('cpu' or 'cuda'). Overrides conf.yaml."
    )
    parser.add_argument(
        "--list-voices",
        action="store_true",
        help="Show information about available voices (points to documentation)."
    )

    args = parser.parse_args()

    if args.list_voices:
        print("Voice selection for Kokoro TTS (direct integration) depends on the model used.")
        print("Commonly available voices for the default Kokoro-82M model include:")
        print("  Japanese Female: jf_alpha, jf_gongitsune, jf_nezumi, jf_tebukuro")
        print("  Chinese Female: zf_xiaobei, zf_xiaoni, zf_xiaoxiao, zf_xiaoyi")
        print("Please refer to `docs/kokoro_tts_integration.md` or the model's documentation for a complete and up-to-date list.")
        sys.exit(0)

    # Load base configuration from conf.yaml
    main_config = load_config(args.config)
    kokoro_specific_config = {}
    if main_config and "tts_config" in main_config and "kokoro_tts" in main_config["tts_config"]:
        kokoro_specific_config = main_config["tts_config"]["kokoro_tts"]
    else:
        print(f"Warning: 'tts_config.kokoro_tts' section not found in {args.config}. Using defaults.")

    # Prepare parameters for test_kokoro_tts, allowing CLI args to override conf.yaml values
    # Default values for parameters not in conf.yaml or overridden are handled inside test_kokoro_tts/TTSFactory.
    tts_params_for_test = {
        "voice": args.voice or kokoro_specific_config.get("voice"),
        "language": kokoro_specific_config.get("language"), # No direct CLI override, uses conf or default
        "device": args.device or kokoro_specific_config.get("device"), # CLI --device overrides conf
        "cache_dir": kokoro_specific_config.get("cache_dir"),
        "sample_rate": kokoro_specific_config.get("sample_rate"),
        "output_format": kokoro_specific_config.get("output_format"),
        "emotion_mapping": kokoro_specific_config.get("emotion_mapping"),
        "repo_id": kokoro_specific_config.get("repo_id")
    }
    # Filter out None values if we only want to pass explicitly set overrides or conf values
    tts_params_for_test = {k: v for k, v in tts_params_for_test.items() if v is not None}


    # Ensure output directory exists
    output_dir = Path(args.output).parent
    if not output_dir.exists():
        print(f"Creating output directory: {output_dir}")
        output_dir.mkdir(parents=True, exist_ok=True)

    test_kokoro_tts(
        tts_params=tts_params_for_test,
        text_to_synthesize=args.text,
        output_file_path=args.output,
        play_audio_flag=not args.no_play
    )
