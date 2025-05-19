#!/usr/bin/env python3
"""
TTS Microservice for Japanese voice synthesis.
This service provides a simple API for generating speech from text using Kokoro TTS.
"""

# Disable CUDA for transformers to avoid CUDA issues
import os
os.environ["CUDA_VISIBLE_DEVICES"] = ""

import sys
import tempfile
import re
from pathlib import Path
import uuid
import json
from typing import Dict, Any, Optional

import numpy as np
import soundfile as sf
from flask import Flask, request, jsonify, send_file, abort
from loguru import logger

# Configure logging
logger.remove()
logger.add(sys.stderr, level="INFO")
logger.add("tts_service.log", rotation="10 MB", level="INFO")

# Create Flask app
app = Flask(__name__)

# Create output directory
OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

# Define a simple mapping from Japanese characters to phonemes
# This is a very basic mapping and not comprehensive
PHONEME_MAP = {
    'あ': 'a', 'い': 'i', 'う': 'u', 'え': 'e', 'お': 'o',
    'か': 'k a', 'き': 'k i', 'く': 'k u', 'け': 'k e', 'こ': 'k o',
    'さ': 's a', 'し': 'sh i', 'す': 's u', 'せ': 's e', 'そ': 's o',
    'た': 't a', 'ち': 'ch i', 'つ': 'ts u', 'て': 't e', 'と': 't o',
    'な': 'n a', 'に': 'n i', 'ぬ': 'n u', 'ね': 'n e', 'の': 'n o',
    'は': 'h a', 'ひ': 'h i', 'ふ': 'f u', 'へ': 'h e', 'ほ': 'h o',
    'ま': 'm a', 'み': 'm i', 'む': 'm u', 'め': 'm e', 'も': 'm o',
    'や': 'y a', 'ゆ': 'y u', 'よ': 'y o',
    'ら': 'r a', 'り': 'r i', 'る': 'r u', 'れ': 'r e', 'ろ': 'r o',
    'わ': 'w a', 'を': 'o', 'ん': 'N',
    'が': 'g a', 'ぎ': 'g i', 'ぐ': 'g u', 'げ': 'g e', 'ご': 'g o',
    'ざ': 'z a', 'じ': 'j i', 'ず': 'z u', 'ぜ': 'z e', 'ぞ': 'z o',
    'だ': 'd a', 'ぢ': 'j i', 'づ': 'z u', 'で': 'd e', 'ど': 'd o',
    'ば': 'b a', 'び': 'b i', 'ぶ': 'b u', 'べ': 'b e', 'ぼ': 'b o',
    'ぱ': 'p a', 'ぴ': 'p i', 'ぷ': 'p u', 'ぺ': 'p e', 'ぽ': 'p o',
    'きゃ': 'ky a', 'きゅ': 'ky u', 'きょ': 'ky o',
    'しゃ': 'sh a', 'しゅ': 'sh u', 'しょ': 'sh o',
    'ちゃ': 'ch a', 'ちゅ': 'ch u', 'ちょ': 'ch o',
    'にゃ': 'ny a', 'にゅ': 'ny u', 'にょ': 'ny o',
    'ひゃ': 'hy a', 'ひゅ': 'hy u', 'ひょ': 'hy o',
    'みゃ': 'my a', 'みゅ': 'my u', 'みょ': 'my o',
    'りゃ': 'ry a', 'りゅ': 'ry u', 'りょ': 'ry o',
    'ぎゃ': 'gy a', 'ぎゅ': 'gy u', 'ぎょ': 'gy o',
    'じゃ': 'j a', 'じゅ': 'j u', 'じょ': 'j o',
    'びゃ': 'by a', 'びゅ': 'by u', 'びょ': 'by o',
    'ぴゃ': 'py a', 'ぴゅ': 'py u', 'ぴょ': 'py o',
    'っ': 'q',  # Small tsu (geminate consonant marker)
    '。': '.', '、': ',', '！': '!', '？': '?',
    ' ': ' ', '　': ' ',  # Spaces
}

# Emotion mapping
EMOTION_MAP = {
    'joy': 1.2,      # Faster for joy
    'sadness': 0.8,  # Slower for sadness
    'anger': 1.1,    # Slightly faster for anger
    'fear': 0.9,     # Slightly slower for fear
    'surprise': 1.3, # Faster for surprise
    'disgust': 0.85, # Slower for disgust
    'neutral': 1.0,  # Normal speed for neutral
    'smirk': 1.1,    # Slightly faster for smirk
}

# Global variable for the TTS pipeline
tts_pipeline = None

def text_to_phonemes(text: str) -> str:
    """
    Convert Japanese text to phonemes.
    
    Args:
        text: Japanese text
        
    Returns:
        Phoneme sequence
    """
    # Extract emotion tags
    emotion_tags = re.findall(r'\[(.*?):(.*?)\]', text)
    
    # Remove emotion tags from text
    clean_text = re.sub(r'\[(.*?):(.*?)\]', '', text).strip()
    
    # Convert to phonemes
    phonemes = []
    i = 0
    while i < len(clean_text):
        # Check for two-character sequences first
        if i < len(clean_text) - 1 and clean_text[i:i+2] in PHONEME_MAP:
            phonemes.append(PHONEME_MAP[clean_text[i:i+2]])
            i += 2
        # Then check for single characters
        elif clean_text[i] in PHONEME_MAP:
            phonemes.append(PHONEME_MAP[clean_text[i]])
            i += 1
        # Skip unknown characters
        else:
            i += 1
    
    # Join phonemes with spaces
    return ' '.join(phonemes)

def extract_emotion(text: str) -> tuple[str, Optional[str], float]:
    """
    Extract emotion tags from text.
    
    Args:
        text: Text with emotion tags
        
    Returns:
        Tuple of (clean_text, emotion, intensity)
    """
    # Default values
    emotion = None
    intensity = 0.0
    
    # Extract emotion tags
    emotion_tags = re.findall(r'\[(.*?):(.*?)\]', text)
    
    # Remove emotion tags from text
    clean_text = re.sub(r'\[(.*?):(.*?)\]', '', text).strip()
    
    # Process emotion tags
    if emotion_tags:
        # Use the first emotion tag
        emotion, intensity_str = emotion_tags[0]
        try:
            intensity = float(intensity_str)
        except ValueError:
            intensity = 0.5  # Default intensity
    
    return clean_text, emotion, intensity

def get_speech_parameters(emotion: Optional[str], intensity: float) -> Dict[str, Any]:
    """
    Get speech parameters based on emotion and intensity.
    
    Args:
        emotion: Emotion name
        intensity: Emotion intensity
        
    Returns:
        Dictionary of speech parameters
    """
    # Default parameters
    params = {
        "speed": 1.0,
    }
    
    # Adjust parameters based on emotion and intensity
    if emotion and emotion in EMOTION_MAP:
        # Scale the speed based on intensity
        base_speed = EMOTION_MAP[emotion]
        speed_adjustment = 1.0 + (base_speed - 1.0) * intensity
        params["speed"] = speed_adjustment
    
    return params

def initialize_tts():
    """Initialize the TTS pipeline."""
    global tts_pipeline
    
    if tts_pipeline is not None:
        return
    
    try:
        from kokoro.pipeline import KPipeline
        
        logger.info("Initializing Kokoro TTS pipeline...")
        tts_pipeline = KPipeline(lang_code='j')
        logger.info("Kokoro TTS pipeline initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Kokoro TTS pipeline: {e}")
        raise

def generate_speech(text: str, voice: str = "jf_alpha") -> str:
    """
    Generate speech from text.
    
    Args:
        text: Text to synthesize
        voice: Voice to use
        
    Returns:
        Path to the generated audio file
    """
    # Initialize TTS if not already initialized
    if tts_pipeline is None:
        initialize_tts()
    
    # Extract emotion
    clean_text, emotion, intensity = extract_emotion(text)
    logger.info(f"Text: {clean_text}, Emotion: {emotion}, Intensity: {intensity}")
    
    # Get speech parameters
    params = get_speech_parameters(emotion, intensity)
    logger.info(f"Speech parameters: {params}")
    
    # Convert text to phonemes
    phonemes = text_to_phonemes(clean_text)
    logger.info(f"Phonemes: {phonemes}")
    
    # Generate a unique filename
    output_file = OUTPUT_DIR / f"{uuid.uuid4()}.wav"
    
    try:
        # Generate speech
        audio = tts_pipeline.model.inference(
            phonemes,
            voice_emb=tts_pipeline.model.voice_emb[voice],
            speed=params["speed"]
        )
        
        # Convert to numpy array
        audio = audio.cpu().numpy()
        
        # Save the audio to a file
        sf.write(output_file, audio, 24000)
        logger.info(f"Generated audio file: {output_file}")
        
        return str(output_file)
    except Exception as e:
        logger.error(f"Error generating speech: {e}")
        
        # Create a silent audio file as fallback
        silent_audio = np.zeros(24000)  # 1 second of silence at 24kHz
        sf.write(output_file, silent_audio, 24000)
        logger.warning(f"Created silent audio file as fallback: {output_file}")
        
        return str(output_file)

@app.route('/tts', methods=['POST'])
def tts_endpoint():
    """TTS endpoint."""
    # Get request data
    data = request.json
    
    if not data or 'text' not in data:
        return jsonify({"error": "Missing required parameter: text"}), 400
    
    # Get parameters
    text = data['text']
    voice = data.get('voice', 'jf_alpha')
    
    # Generate speech
    try:
        output_file = generate_speech(text, voice)
        
        # Return the audio file
        return send_file(output_file, mimetype='audio/wav')
    except Exception as e:
        logger.error(f"Error in TTS endpoint: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/voices', methods=['GET'])
def voices_endpoint():
    """Get available voices."""
    # Initialize TTS if not already initialized
    if tts_pipeline is None:
        try:
            initialize_tts()
        except Exception as e:
            logger.error(f"Error initializing TTS: {e}")
            return jsonify({"error": str(e)}), 500
    
    # Get available voices
    try:
        voices = list(tts_pipeline.model.voice_emb.keys())
        
        # Filter to only include Japanese female voices
        japanese_voices = [v for v in voices if v.startswith('jf_')]
        
        return jsonify({
            "voices": japanese_voices,
            "default": "jf_alpha"
        })
    except Exception as e:
        logger.error(f"Error getting voices: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/health', methods=['GET'])
def health_endpoint():
    """Health check endpoint."""
    return jsonify({"status": "ok"})

if __name__ == '__main__':
    # Initialize TTS
    try:
        initialize_tts()
    except Exception as e:
        logger.error(f"Failed to initialize TTS: {e}")
        sys.exit(1)
    
    # Run the Flask app
    app.run(host='0.0.0.0', port=5000, debug=True)
