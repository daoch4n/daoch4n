#!/usr/bin/env python3
"""
TTS Microservice for Japanese voice synthesis.
This service provides a simple API for generating speech from text using Kokoro TTS.
"""

import os
import sys
import tempfile
import re
from pathlib import Path
import uuid
import json
from typing import Dict, Any, Optional, List, Tuple

import numpy as np
import soundfile as sf
from flask import Flask, request, jsonify, send_file, abort
from loguru import logger

# Configure logging
logger.remove()
logger.add(sys.stderr, level="INFO")
logger.add("tts_service.log", rotation="10 MB", level="INFO")


# Ensure the project root is in sys.path to allow importing open_llm_vtuber utilities
project_root = Path(__file__).resolve().parent.parent.parent # kokoro/tts_service/app.py -> kokoro/tts_service -> kokoro -> project root
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
    logger.info(f"Added project root to sys.path: {project_root}")

try:
    from open_llm_vtuber.utils.mecab_utils import get_mecab_tagger
    # We don't directly use GenericTagger type hint here from utils, fugashi will be imported by the util if needed.
except ImportError as e:
    logger.error(f"Could not import get_mecab_tagger from open_llm_vtuber.utils.mecab_utils. "
                 f"Ensure the path is correct and the main project structure is accessible. Error: {e}")
    # Fallback: The service might still run with its basic phoneme map if MeCab can't be initialized.
    get_mecab_tagger = None # Ensure it's defined for later checks, even if it's None


# Create Flask app
app = Flask(__name__)

# Create output directory
OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

# Create cache directory
CACHE_DIR = Path("cache")
CACHE_DIR.mkdir(exist_ok=True)

# Default configuration
DEFAULT_CONFIG = {
    "device": "cpu",
    "repo_id": None,
    "sample_rate": 24000,
    "output_format": "wav",
    "emotion_mapping": {
        "joy": 1.2,      # Faster for happy emotions
        "sadness": 0.8,  # Slower for sad emotions
        "anger": 1.1,    # Slightly faster for angry emotions
        "fear": 0.9,     # Slightly slower for fearful emotions
        "surprise": 1.3, # Faster for surprised emotions
        "disgust": 1.0,  # Normal speed for disgust
        "neutral": 1.0,  # Normal speed for neutral
        "smirk": 1.1     # Slightly faster for smirk
    }
}

# Global variables
tts_pipeline = None
tts_config = DEFAULT_CONFIG.copy()
use_mecab = True  # Flag to indicate whether to use MeCab for phoneme conversion

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

def _convert_language_code(language: str) -> str:
    """
    Convert standard language code to Kokoro format.

    Args:
        language: Standard language code (e.g., 'en', 'ja')

    Returns:
        Kokoro language code ('a' for English, 'j' for Japanese, etc.)
    """
    # Kokoro uses 'a' for English
    if language.lower() in ['en', 'eng', 'english']:
        return 'a'
    # Kokoro uses 'j' for Japanese
    elif language.lower() in ['ja', 'jp', 'jpn', 'japanese']:
        return 'j'
    # For other languages, use the original code
    return language

def text_to_phonemes(text: str) -> str:
    """
    Convert Japanese text to phonemes.

    Args:
        text: Japanese text

    Returns:
        Phoneme sequence
    """
    global use_mecab

    # Remove emotion tags from text as they are not part of phoneme conversion
    clean_text = re.sub(r'\[([\w]+)(?::([0-9]*\.?[0-9]+))?\]', '', text).strip()

    # The `use_mecab` global flag determines the conversion strategy.
    # The `use_mecab` global flag determines the conversion strategy.
    # If True (default), it attempts to use MeCab (via Fugashi) for more accurate,
    # context-aware phoneme conversion.
    if use_mecab:
        tagger = None
        if get_mecab_tagger: # Check if the utility function was imported successfully
            try:
                logger.info("Attempting to initialize MeCab tagger via shared utility (get_mecab_tagger)...")
                tagger = get_mecab_tagger() # Use the shared utility
            except Exception as e_util: # Catch any unexpected error from the utility itself
                logger.error(f"Error calling get_mecab_tagger utility: {e_util}")
                tagger = None # Ensure tagger is None if util fails

        if tagger:
            logger.info("MeCab tagger initialized successfully via utility for text_to_phonemes.")
            try:
                # Convert text to phonemes using MeCab
                phonemes = []
                for word in tagger(clean_text):
                    # Get the pronunciation if available
                    if hasattr(word, 'feature') and len(word.feature) > 7:
                        pron = word.feature[7]
                        if pron != '*':
                            # Convert katakana pronunciation to phonemes
                            # This is a simplified conversion
                            for char in pron:
                                if char in PHONEME_MAP:
                                    phonemes.append(PHONEME_MAP[char])
                            continue

                    # Fallback to character-by-character conversion
                    for char in word.surface:
                        if char in PHONEME_MAP:
                            phonemes.append(PHONEME_MAP[char])

                return ' '.join(phonemes)
            except Exception as e_mecab_process:
                logger.warning(f"MeCab processing failed with successfully initialized tagger: {e_mecab_process}. Disabling MeCab for future calls.")
                use_mecab = False # Disable MeCab for future calls
        else:
            # This block is reached if get_mecab_tagger was None (import failed) or returned None (init failed)
            logger.warning("MeCab tagger could not be initialized (utility failed or not imported). Disabling MeCab for this session.")
            use_mecab = False # Disable MeCab for future calls if tagger is None

    # Fallback phoneme conversion (if use_mecab is False):
    # This method is used if MeCab is not available or fails. It's a simple
    # character-by-character or two-character sequence lookup using PHONEME_MAP.
    # Limitations:
    # - Does not understand context, leading to potentially incorrect pronunciations
    #   (e.g., different readings of kanji based on context).
    # - Cannot handle words or characters not present in PHONEME_MAP.
    # - Less natural sounding compared to MeCab-based conversion.
    # - Does not perform proper morphological analysis.
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

    # Extract emotion tags using regex
    emotion_pattern = r'\[([\w]+)(?::([0-9]*\.?[0-9]+))?\]'
    matches = list(re.finditer(emotion_pattern, text))

    # Remove emotion tags from text
    clean_text = re.sub(emotion_pattern, '', text).strip()

    # Process emotion tags
    if matches:
        # Get the dominant emotion (using the first one for simplicity)
        emotion = matches[0].group(1).lower()
        intensity_str = matches[0].group(2)
        intensity = 1.0 if not intensity_str else float(intensity_str)

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
    global tts_config

    # Default parameters
    params = {
        "speed": 1.0,
    }

    # Get emotion mapping from config
    emotion_mapping = tts_config["emotion_mapping"]

    # Adjust parameters based on emotion and intensity
    if emotion and emotion in emotion_mapping:
        # Only apply speed changes if intensity is significant
        if intensity < 0.3:
            return params

        # Get the emotion-specific speed multiplier
        emotion_speed = emotion_mapping.get(emotion, 1.0)

        # Scale the effect based on intensity
        scaled_intensity = (intensity - 0.3) / 0.7
        speed_adjustment = (emotion_speed - 1.0) * scaled_intensity

        params["speed"] = 1.0 + speed_adjustment

    return params

def update_config(config_data: Dict[str, Any]) -> None:
    """
    Update the TTS service configuration.

    Args:
        config_data: New configuration data
    """
    global tts_config, tts_pipeline

    # Update configuration
    for key, value in config_data.items():
        if key in tts_config:
            tts_config[key] = value

    # Reinitialize TTS pipeline if needed
    if tts_pipeline is not None:
        tts_pipeline = None
        initialize_tts()

    logger.info(f"Updated TTS service configuration: {tts_config}")

def initialize_tts():
    """Initialize the TTS pipeline."""
    global tts_pipeline, tts_config

    if tts_pipeline is not None:
        return

    try:
        from kokoro import KPipeline

        # Get configuration
        device = tts_config["device"]
        repo_id = tts_config["repo_id"]

        # Convert language code to Kokoro format (e.g., 'ja' to 'j')
        # TODO: This service is primarily designed for Japanese ("ja").
        # If broader language support is envisioned for this microservice in the future,
        # the language code might need to become a configurable parameter,
        # potentially passed via API request (if the pipeline can be reinitialized
        # or supports multiple languages) or set via the service's overall configuration
        # (e.g., environment variable or /config endpoint).
        lang_code = _convert_language_code("ja")

        logger.info(f"Initializing Kokoro TTS pipeline with lang_code={lang_code}, device={device}, repo_id={repo_id}...")

        # Initialize the pipeline with or without repo_id
        if repo_id:
            tts_pipeline = KPipeline(
                lang_code=lang_code,
                repo_id=repo_id,
                device=device
            )
        else:
            tts_pipeline = KPipeline(
                lang_code=lang_code,
                device=device
            )

        logger.info("Kokoro TTS pipeline initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Kokoro TTS pipeline: {e}")
        raise

def create_silent_audio(file_path: str, duration: float = 1.0) -> None:
    """
    Create a silent audio file as a fallback.

    Args:
        file_path: Path to save the silent audio
        duration: Duration of the silent audio in seconds
    """
    global tts_config

    # Create a silent audio file (all zeros)
    sample_rate = tts_config["sample_rate"]
    samples = int(duration * sample_rate)
    silent_audio = np.zeros(samples, dtype=np.float32)
    sf.write(file_path, silent_audio, sample_rate)
    logger.warning(f"Created silent audio file as fallback: {file_path}")

def generate_speech(text: str, voice: str = "jf_alpha", output_file: Optional[str] = None) -> str:
    """
    Generate speech from text.

    Args:
        text: Text to synthesize
        voice: Voice to use
        output_file: Optional path to save the generated audio file

    Returns:
        Path to the generated audio file
    """
    global tts_config

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

    # Generate a unique filename if not provided
    if output_file is None:
        output_format = tts_config["output_format"]
        output_file = str(OUTPUT_DIR / f"{uuid.uuid4()}.{output_format}")

    try:
        # Generate speech
        audio = tts_pipeline.model.inference(
            phonemes,
            voice_emb=tts_pipeline.model.voice_emb[voice],
            speed=params["speed"]
        )

        # Convert to numpy array
        audio = audio.cpu().numpy()

        # Get sample rate from config
        sample_rate = tts_config["sample_rate"]

        # Save the audio to a file
        sf.write(output_file, audio, sample_rate)
        logger.info(f"Generated audio file: {output_file}")

        return output_file
    except Exception as e:
        logger.error(f"Error generating speech: {e}")

        # Create a silent audio file as fallback
        create_silent_audio(output_file)

        return output_file

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
        # Consider adding 'as_attachment=True' if direct download is preferred by clients,
        # though for an API, embedding might be more common.
        return send_file(output_file, mimetype='audio/wav')
    except Exception as e:
        # Log the full error for server-side diagnostics
        logger.error(f"Error in TTS endpoint: {e}", exc_info=True)
        # Return a generic error message to the client
        return jsonify({"error": "An internal error occurred during speech generation."}), 500

@app.route('/voices', methods=['GET'])
def voices_endpoint():
    """Get available voices."""
    # Initialize TTS if not already initialized
    if tts_pipeline is None:
        try:
            initialize_tts()
        except Exception as e:
            logger.error(f"Error initializing TTS for /voices endpoint: {e}", exc_info=True)
            return jsonify({"error": "TTS engine initialization failed."}), 500

    # Get available voices
    try:
        if tts_pipeline and hasattr(tts_pipeline, 'model') and hasattr(tts_pipeline.model, 'voice_emb'):
            voices = list(tts_pipeline.model.voice_emb.keys())
            # Filter to only include Japanese female voices, as this service is primarily for Japanese.
            # This could be made configurable if language support expands.
            japanese_voices = [v for v in voices if v.startswith('jf_')]
            default_voice = "jf_alpha" if "jf_alpha" in japanese_voices else (japanese_voices[0] if japanese_voices else None)

            return jsonify({
                "voices": japanese_voices,
                "default": default_voice
            })
        else:
            logger.error("TTS pipeline or model not available for listing voices.")
            return jsonify({"error": "TTS model not available."}), 500
    except Exception as e:
        logger.error(f"Error getting voices: {e}", exc_info=True)
        return jsonify({"error": "Could not retrieve voice list."}), 500

@app.route('/health', methods=['GET'])
def health_endpoint():
    """Health check endpoint."""
    return jsonify({"status": "ok"})

@app.route('/config', methods=['GET', 'POST'])
def config_endpoint():
    """Configuration endpoint."""
    global tts_config

    # Handle GET request
    if request.method == 'GET':
        return jsonify(tts_config)

    # Handle POST request
    if request.method == 'POST':
        data = request.json

        if not data:
            return jsonify({"error": "Missing configuration data"}), 400

        try:
            # Update configuration
            update_config(data)

            return jsonify({
                "status": "ok",
                "message": "Configuration updated successfully",
                "config": tts_config
            })
        except Exception as e:
            logger.error(f"Error updating configuration: {e}", exc_info=True)
            return jsonify({"error": "Failed to update configuration."}), 500

if __name__ == '__main__':
    # Initialize TTS at startup
    try:
        initialize_tts()
    except Exception as e:
        # Error already logged by initialize_tts()
        logger.critical(f"Service failed to initialize TTS at startup: {e}. Exiting.")
        sys.exit(1)

    # Run the Flask app
    # Note: For production, use a proper WSGI server (e.g., Gunicorn) instead of Flask's built-in server.
    # Debug mode should be turned off in production. Port and host can be configured via environment variables.
    is_debug_mode = os.environ.get("FLASK_DEBUG", "True").lower() == "true"
    server_port = int(os.environ.get("TTS_SERVICE_PORT", 5000))
    logger.info(f"Starting Flask app. Debug mode: {is_debug_mode}, Port: {server_port}")
    app.run(host='0.0.0.0', port=server_port, debug=is_debug_mode)
