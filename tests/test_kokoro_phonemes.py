#!/usr/bin/env python3
"""
Test script for Kokoro TTS with custom phoneme sequence.
"""

# Disable CUDA for transformers to avoid CUDA issues
import os
os.environ["CUDA_VISIBLE_DEVICES"] = ""

import sys
import argparse
import soundfile as sf
import numpy as np
from loguru import logger

# Configure logging
logger.remove()
logger.add(sys.stderr, level="INFO")

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

def text_to_phonemes(text):
    """
    Convert Japanese text to phonemes.
    
    Args:
        text: Japanese text
        
    Returns:
        Phoneme sequence
    """
    # Remove emotion tags
    text = text.split('[')[0].strip()
    
    # Convert to phonemes
    phonemes = []
    i = 0
    while i < len(text):
        # Check for two-character sequences first
        if i < len(text) - 1 and text[i:i+2] in PHONEME_MAP:
            phonemes.append(PHONEME_MAP[text[i:i+2]])
            i += 2
        # Then check for single characters
        elif text[i] in PHONEME_MAP:
            phonemes.append(PHONEME_MAP[text[i]])
            i += 1
        # Skip unknown characters
        else:
            i += 1
    
    # Join phonemes with spaces
    return ' '.join(phonemes)

def main():
    """Main function."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Test Kokoro TTS with custom phonemes")
    parser.add_argument("--voice", default="jf_alpha", help="Voice to use")
    parser.add_argument("--text", default="こんにちは、私はダオコです。", help="Text to synthesize")
    parser.add_argument("--output", default="output.wav", help="Output file")
    parser.add_argument("--play", action="store_true", help="Play the audio after synthesis")
    args = parser.parse_args()

    # Convert text to phonemes
    phonemes = text_to_phonemes(args.text)
    logger.info(f"Converted text to phonemes: {phonemes}")

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
    try:
        logger.info(f"Generating speech for phonemes: {phonemes}")
        
        # Use the pipeline directly with phonemes
        audio = pipeline.model.inference(
            phonemes,
            voice_emb=pipeline.model.voice_emb[args.voice],
            speed=1.0
        )
        
        # Convert to numpy array
        audio = audio.cpu().numpy()
        
        # Save the audio to a file
        sf.write(args.output, audio, 24000)
        logger.info(f"Generated audio file: {args.output}")
    except Exception as e:
        logger.error(f"Error generating speech: {e}")
        # Create a silent audio file as fallback
        silent_audio = np.zeros(24000)  # 1 second of silence at 24kHz
        sf.write(args.output, silent_audio, 24000)
        logger.warning(f"Created silent audio file as fallback: {args.output}")
    
    # Play the audio if requested
    if args.play:
        try:
            import sounddevice as sd
            audio, sr = sf.read(args.output)
            sd.play(audio, sr)
            sd.wait()
        except Exception as e:
            logger.error(f"Error playing audio: {e}")
            logger.info(f"Please play the audio file manually: {args.output}")

if __name__ == "__main__":
    main()
