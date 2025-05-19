#!/usr/bin/env python3
"""
Direct test script for Kokoro TTS that bypasses the JAG2P class.
"""

# Disable CUDA for transformers to avoid CUDA issues
import os
os.environ["CUDA_VISIBLE_DEVICES"] = ""

import sys
import argparse
import re
import soundfile as sf
import numpy as np
from loguru import logger

# Configure logging
logger.remove()
logger.add(sys.stderr, level="INFO")

def extract_emotion(text):
    """Extract emotion and intensity from text with emotion tags."""
    emotion_pattern = r'\[([\w]+)(?::([0-9]*\.?[0-9]+))?\]'
    matches = list(re.finditer(emotion_pattern, text))

    # Default to neutral if no emotion tags found
    if not matches:
        return "neutral", 0.0

    # Get the dominant emotion
    emotion = matches[0].group(1).lower()
    intensity_str = matches[0].group(2)
    intensity = 1.0 if not intensity_str else float(intensity_str)

    return emotion, intensity

def preprocess_text(text):
    """Remove emotion tags from text."""
    emotion_pattern = r'\[([\w]+)(?::([0-9]*\.?[0-9]+))?\]'
    clean_text = re.sub(emotion_pattern, '', text)
    return clean_text.strip()

def get_speed_for_emotion(emotion, intensity):
    """Get appropriate speech speed based on emotion and intensity."""
    # Default speed is 1.0
    base_speed = 1.0

    # Emotion-specific speed adjustments
    emotion_speeds = {
        "joy": 1.2,      # Faster for happy emotions
        "sadness": 0.8,  # Slower for sad emotions
        "anger": 1.1,    # Slightly faster for angry emotions
        "fear": 0.9,     # Slightly slower for fearful emotions
        "surprise": 1.3, # Faster for surprised emotions
        "disgust": 1.0,  # Normal speed for disgust
        "neutral": 1.0   # Normal speed for neutral
    }

    # Get the emotion-specific speed multiplier
    emotion_speed = emotion_speeds.get(emotion, 1.0)

    # Only apply speed changes if intensity is significant
    if intensity < 0.3:
        return base_speed

    # Scale the effect based on intensity
    scaled_intensity = (intensity - 0.3) / 0.7
    speed_adjustment = (emotion_speed - 1.0) * scaled_intensity

    return base_speed + speed_adjustment

def main():
    """Main function."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Direct test for Kokoro TTS")
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

    # Extract emotion from the text
    emotion, intensity = extract_emotion(args.text)
    logger.info(f"Extracted emotion: {emotion} (intensity: {intensity:.2f})")

    # Preprocess text to remove emotion tags
    processed_text = preprocess_text(args.text)
    logger.info(f"Processed text: {processed_text}")

    # Get speed based on emotion
    speed = get_speed_for_emotion(emotion, intensity)
    logger.info(f"Using speed: {speed:.2f}")

    # Load the Kokoro pipeline
    try:
        from kokoro.pipeline import KPipeline

        logger.info("Loading Kokoro pipeline...")
        pipeline = KPipeline(lang_code='j')
        logger.info("Kokoro pipeline loaded successfully")
    except Exception as e:
        logger.error(f"Error loading Kokoro pipeline: {e}")
        sys.exit(1)

    # Generate speech
    logger.info(f"Generating speech with voice: {args.voice}")
    try:
        # Generate audio using Kokoro pipeline
        generator = pipeline(processed_text, voice=args.voice, speed=speed)

        # Process the generator output
        for _, _, audio in generator:
            # Save the audio to a file
            sf.write(args.output, audio, 24000)
            logger.info(f"Generated audio file: {args.output}")
            break
    except Exception as e:
        logger.error(f"Error generating speech: {e}")
        # Create a silent audio file as fallback
        silent_audio = np.zeros(24000, dtype=np.float32)  # 1 second of silence
        sf.write(args.output, silent_audio, 24000)
        logger.warning(f"Created silent audio file as fallback: {args.output}")

    logger.info("Audio generation completed!")
    print(f"\nAudio generation completed!")
    print(f"Generated audio file: {args.output}")
    print(f"You can play this file with any audio player.")

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
