#!/usr/bin/env python3
"""
Simple test script for the simplified Kokoro TTS implementation.
"""

# Disable CUDA for transformers to avoid CUDA issues
import os
os.environ["CUDA_VISIBLE_DEVICES"] = ""

import sys
import argparse
from pathlib import Path
import soundfile as sf

# Set up logging
from loguru import logger
logger.remove()
logger.add(sys.stderr, level="INFO")

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).resolve().parent))

# Import the TTSEngine from our simplified implementation
try:
    from src.open_llm_vtuber.tts.kokoro_tts import TTSEngine
except ImportError:
    logger.error("Failed to import TTSEngine. Make sure the project is installed.")
    sys.exit(1)

def main():
    """Main function."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Test Simplified Kokoro TTS")
    parser.add_argument("--voice", default="jf_alpha", help="Voice to use")
    parser.add_argument("--text", default="こんにちは、私はダオコです。[joy:0.8]", help="Text to synthesize")
    parser.add_argument("--output", default="cache/test_kokoro.wav", help="Output file")
    parser.add_argument("--list-voices", action="store_true", help="List available voices")
    args = parser.parse_args()

    # List available voices if requested
    if args.list_voices:
        list_available_voices()
        return

    # Ensure cache directory exists
    cache_dir = os.path.dirname(args.output)
    if cache_dir and not os.path.exists(cache_dir):
        os.makedirs(cache_dir)
        logger.info(f"Created directory: {cache_dir}")

    # Create the TTS engine
    try:
        logger.info(f"Initializing Kokoro TTS engine with voice: {args.voice}")
        tts_engine = TTSEngine(
            voice=args.voice,
            language="ja",
            device="cpu",
            cache_dir="cache",
            sample_rate=24000,
            output_format="wav"
        )
    except Exception as e:
        logger.error(f"Error creating TTS engine: {e}")
        sys.exit(1)

    # Generate speech
    logger.info(f"Generating speech for text: {args.text}")
    try:
        output_file = tts_engine.generate_audio(args.text, os.path.splitext(args.output)[0])
        logger.info(f"Generated audio file: {output_file}")
        print(f"\nAudio generation successful!")
        print(f"Generated audio file: {output_file}")
        print(f"You can play this file with any audio player.")
    except Exception as e:
        logger.error(f"Error generating speech: {e}")
        sys.exit(1)

def list_available_voices():
    """List all available voices in the Kokoro model."""
    print("Available voices in Kokoro-82M model:")
    print("\nJapanese Female Voices (Recommended for Daoko):")
    print("- jf_alpha (Japanese female voice - recommended for Daoko)")
    print("- jf_gongitsune (Japanese female voice)")
    print("- jf_nezumi (Japanese female voice)")
    print("- jf_tebukuro (Japanese female voice)")
    print("\nChinese Female Voices:")
    print("- zf_xiaobei (Chinese female voice)")
    print("- zf_xiaoni (Chinese female voice)")
    print("- zf_xiaoxiao (Chinese female voice)")
    print("- zf_xiaoyi (Chinese female voice)")

if __name__ == "__main__":
    main()
