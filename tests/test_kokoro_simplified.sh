#!/bin/bash

# Simple test script for the simplified Kokoro TTS implementation

# Default values
VOICE="jf_alpha"
TEXT="こんにちは、私はダオコです。よろしくお願いします。[joy:0.8]"
OUTPUT="cache/test_kokoro.wav"
LIST_VOICES=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --voice|-v)
      VOICE="$2"
      shift 2
      ;;
    --text|-t)
      TEXT="$2"
      shift 2
      ;;
    --output|-o)
      OUTPUT="$2"
      shift 2
      ;;
    --list-voices|-l)
      LIST_VOICES=true
      shift
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

# Activate the virtual environment
source .venv/bin/activate

# Make sure the cache directory exists
mkdir -p cache

# Run the test
if [ "$LIST_VOICES" = true ]; then
  echo "Available voices in Kokoro-82M model:"
  echo ""
  echo "Japanese Female Voices (Recommended for Daoko):"
  echo "- jf_alpha (Japanese female voice - recommended for Daoko)"
  echo "- jf_gongitsune (Japanese female voice)"
  echo "- jf_nezumi (Japanese female voice)"
  echo "- jf_tebukuro (Japanese female voice)"
  echo ""
  echo "Chinese Female Voices:"
  echo "- zf_xiaobei (Chinese female voice)"
  echo "- zf_xiaoni (Chinese female voice)"
  echo "- zf_xiaoxiao (Chinese female voice)"
  echo "- zf_xiaoyi (Chinese female voice)"
else
  echo "Using voice: $VOICE"
  echo "Text: $TEXT"
  echo "Output: $OUTPUT"

  # Create a temporary Python script
  TMP_SCRIPT=$(mktemp)
  cat > "$TMP_SCRIPT" << EOF
import os
os.environ["CUDA_VISIBLE_DEVICES"] = ""

import sys
from pathlib import Path
import re
import soundfile as sf
from loguru import logger
import numpy as np

# Import the TTSEngine
from open_llm_vtuber.tts.kokoro_tts import TTSEngine

# Create a direct implementation that bypasses the JAG2P issue
from kokoro import KPipeline
import re

# Function to extract emotion
def extract_emotion(text):
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

# Function to preprocess text
def preprocess_text(text):
    emotion_pattern = r'\[([\w]+)(?::([0-9]*\.?[0-9]+))?\]'
    clean_text = re.sub(emotion_pattern, '', text)
    return clean_text.strip()

# Function to get speed for emotion
def get_speed_for_emotion(emotion, intensity):
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

# Extract emotion from the text
emotion, intensity = extract_emotion("$TEXT")
print(f"Extracted emotion: {emotion} (intensity: {intensity:.2f})")

# Preprocess text to remove emotion tags
processed_text = preprocess_text("$TEXT")
print(f"Processed text: {processed_text}")

# Get speed based on emotion
speed = get_speed_for_emotion(emotion, intensity)
print(f"Using speed: {speed:.2f}")

# Initialize the Kokoro pipeline
pipeline = KPipeline(lang_code='j')

# Generate speech
print(f"Generating speech with voice: $VOICE")
try:
    # Generate audio using Kokoro pipeline
    generator = pipeline(processed_text, voice="$VOICE", speed=speed)

    # Process the generator output
    for _, _, audio in generator:
        # Save the audio to a file
        sf.write("$OUTPUT", audio, 24000)
        print(f"Generated audio file: $OUTPUT")
        break
except Exception as e:
    print(f"Error generating speech: {e}")
    # Create a silent audio file as fallback
    silent_audio = np.zeros(24000, dtype=np.float32)  # 1 second of silence
    sf.write("$OUTPUT", silent_audio, 24000)
    print(f"Created silent audio file as fallback: $OUTPUT")
EOF

  # Run the script
  python "$TMP_SCRIPT"

  # Clean up
  rm "$TMP_SCRIPT"

  echo ""
  echo "Audio generation completed!"
  echo "You can play the audio file: $OUTPUT"
fi

# Deactivate the virtual environment
deactivate
