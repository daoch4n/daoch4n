#!/usr/bin/env python3
"""
Test script for AllTalk TTS integration with RVC voice conversion.

This script tests the AllTalk TTS integration by generating a test audio file
using the AllTalk TTS engine with RVC voice conversion.
"""

import os
import sys
import argparse
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.open_llm_vtuber.tts.alltalk_tts import TTSEngine
from loguru import logger


def main():
    """Test the AllTalk TTS integration."""
    parser = argparse.ArgumentParser(description="Test AllTalk TTS integration")
    parser.add_argument(
        "--api-url",
        type=str,
        default="http://127.0.0.1:7851",
        help="URL of the AllTalk TTS API server",
    )
    parser.add_argument(
        "--voice",
        type=str,
        default="en_US-ljspeech-high.onnx",
        help="Voice to use for TTS",
    )
    parser.add_argument(
        "--language",
        type=str,
        default="en",
        help="Language to use for TTS",
    )
    parser.add_argument(
        "--rvc-enabled",
        action="store_true",
        help="Enable RVC voice conversion",
    )
    parser.add_argument(
        "--rvc-model",
        type=str,
        default="daoko[23]_16hs_3bs_SPLICED_NPROC_40k_v1",
        help="RVC model to use for voice conversion",
    )
    parser.add_argument(
        "--rvc-pitch",
        type=int,
        default=0,
        help="Pitch adjustment for RVC voice conversion",
    )
    parser.add_argument(
        "--output-format",
        type=str,
        default="wav",
        help="Output audio format",
    )
    parser.add_argument(
        "--text",
        type=str,
        default="Hello, this is a test of the AllTalk TTS integration with RVC voice conversion.",
        help="Text to speak",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="test_alltalk_tts",
        help="Output file name (without extension)",
    )

    args = parser.parse_args()

    # Create the TTS engine
    tts_engine = TTSEngine(
        api_url=args.api_url,
        voice=args.voice,
        language=args.language,
        rvc_enabled=args.rvc_enabled,
        rvc_model=args.rvc_model,
        rvc_pitch=args.rvc_pitch,
        output_format=args.output_format,
    )

    # Generate the audio
    logger.info(f"Generating audio for text: {args.text}")
    output_file = tts_engine.generate_audio(args.text, args.output)

    if output_file:
        logger.info(f"Audio generated successfully: {output_file}")
        # Get the absolute path
        output_file_abs = os.path.abspath(output_file)
        logger.info(f"Absolute path: {output_file_abs}")
    else:
        logger.error("Failed to generate audio")


if __name__ == "__main__":
    main()
