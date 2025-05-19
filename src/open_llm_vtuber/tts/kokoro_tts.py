"""
Kokoro-82M TTS integration for Open-LLM-VTuber.

This module provides integration with the Kokoro-82M text-to-speech model,
which is a lightweight, high-quality TTS model with emotional capabilities.
It includes support for the Misaki tokenizer for Japanese language processing.
"""

# Disable CUDA for transformers to avoid CUDA issues
import os
os.environ["CUDA_VISIBLE_DEVICES"] = ""

import asyncio
import tempfile
import re
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
import soundfile as sf
from loguru import logger
import torch
from kokoro import KPipeline

# Import our custom wrapper
try:
    from .kokoro_wrapper import KokoroWrapper
    WRAPPER_AVAILABLE = True
    logger.info("KokoroWrapper found. Using custom wrapper for Kokoro TTS.")
except ImportError:
    logger.warning("KokoroWrapper not found. Using default KPipeline.")
    WRAPPER_AVAILABLE = False

# Import Misaki tokenizer for Japanese language support
try:
    from misaki import Misaki
    MISAKI_AVAILABLE = True
except ImportError:
    logger.warning("Misaki tokenizer not found. Japanese text processing may be limited.")
    MISAKI_AVAILABLE = False
except Exception as e:
    logger.warning(f"Error importing Misaki tokenizer: {e}")
    logger.warning("Japanese text processing may be limited.")
    MISAKI_AVAILABLE = False

from .tts_interface import TTSInterface


class TTSEngine(TTSInterface):
    """
    Kokoro-82M TTS engine implementation.

    This class provides integration with the Kokoro-82M TTS model,
    which is a lightweight, high-quality TTS model with emotional capabilities.
    """

    def __init__(
        self,
        voice: str = "af_heart",
        language: str = "en",
        device: str = "cpu",  # Always use CPU to avoid CUDA issues
        repo_id: str = None,
        cache_dir: str = "cache",
        sample_rate: int = 24000,
        output_format: str = "wav",
        emotion_mapping: Optional[Dict[str, str]] = None,
    ):
        """
        Initialize the Kokoro-82M TTS engine.

        Args:
            voice: The voice to use for TTS (default: "af_heart", Japanese voices: "jf_alpha", "jf_gongitsune", etc.)
            language: The language code to use (default: "en", use "ja" for Japanese)
            device: The device to use for inference ("cuda" or "cpu")
            repo_id: Repository ID for the Kokoro model (if None, uses the default model)
            cache_dir: Directory to store generated audio files
            sample_rate: Sample rate for the generated audio (default: 24000)
            output_format: Output audio format (default: "wav")
            emotion_mapping: Optional mapping from emotion tags to Kokoro voice styles
        """
        self.voice = voice
        self.language = language
        self.device = device
        self.repo_id = repo_id
        self.sample_rate = sample_rate
        self.file_extension = output_format
        self.new_audio_dir = cache_dir

        # Default emotion mapping (can be overridden)
        self.emotion_mapping = emotion_mapping or {
            "joy": "happy",
            "sadness": "sad",
            "anger": "angry",
            "fear": "fearful",
            "surprise": "surprised",
            "disgust": "disgusted",
            "neutral": "neutral"
        }

        # Create cache directory if it doesn't exist
        if not os.path.exists(self.new_audio_dir):
            os.makedirs(self.new_audio_dir)

        # Initialize Misaki tokenizer for Japanese text if available
        self.misaki = None
        if MISAKI_AVAILABLE and self.is_japanese_voice():
            try:
                self.misaki = Misaki()
                logger.info("Misaki tokenizer initialized for Japanese text processing")
            except Exception as e:
                logger.error(f"Failed to initialize Misaki tokenizer: {e}")

        # Initialize the Kokoro pipeline
        try:
            # Try to use our custom wrapper if available
            if WRAPPER_AVAILABLE and self.is_japanese_voice():
                logger.info(f"Using KokoroWrapper for Japanese voice: {self.voice}")
                try:
                    self.pipeline = KokoroWrapper(
                        voice=self.voice,
                        language=self.language,
                        device=self.device,
                        repo_id=self.repo_id,
                        cache_dir=self.new_audio_dir
                    )
                    logger.info(f"KokoroWrapper initialized with voice: {self.voice}")
                except Exception as e:
                    logger.error(f"Failed to initialize KokoroWrapper: {e}")
                    logger.warning("Falling back to standard KPipeline")
                    # Fall back to standard KPipeline
                    self._initialize_standard_pipeline()
            else:
                # Use standard KPipeline
                self._initialize_standard_pipeline()
        except Exception as e:
            logger.error(f"Failed to initialize Kokoro-82M TTS engine: {e}")
            raise

    def _initialize_standard_pipeline(self):
        """Initialize the standard KPipeline."""
        # Convert language code to Kokoro format (e.g., 'en' to 'a')
        lang_code = self._convert_language_code(self.language)

        # Only pass repo_id if explicitly provided
        if self.repo_id:
            self.pipeline = KPipeline(
                lang_code=lang_code,
                repo_id=self.repo_id,
                device=self.device
            )
        else:
            # Use default model
            self.pipeline = KPipeline(
                lang_code=lang_code,
                device=self.device
            )
        logger.info(f"Standard Kokoro-82M TTS engine initialized with voice: {self.voice}")

    def is_japanese_voice(self) -> bool:
        """
        Check if the current voice is a Japanese voice.

        Returns:
            True if the voice is a Japanese voice, False otherwise
        """
        return (
            self.voice.startswith("jf_") or  # Japanese female voices
            self.voice.startswith("jm_") or  # Japanese male voices
            self.language.lower() in ["ja", "jp", "japanese"]
        )

    def _convert_language_code(self, language: str) -> str:
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
        # (Kokoro may support more languages in the future)
        return language

    # This method is already defined above

    def _preprocess_text(self, text: str) -> str:
        """
        Preprocess text before sending to the TTS model.

        This method handles emotion tags and converts them to a format
        that the Kokoro model can use for emotional inflection.
        For Japanese text, it also uses the Misaki tokenizer if available.

        Args:
            text: The input text with potential emotion tags

        Returns:
            Processed text ready for the TTS model
        """
        # Extract and remove emotion tags using regex
        import re
        emotion_pattern = r'\[([\w]+)(?::([0-9]*\.?[0-9]+))?\]'

        # Remove all emotion tags from the text
        clean_text = re.sub(emotion_pattern, '', text)

        # Process with Misaki tokenizer for Japanese text if available
        if self.is_japanese_voice() and self.misaki is not None:
            try:
                # Process the text with Misaki tokenizer
                processed_text = self.misaki.process(clean_text)
                logger.debug(f"Processed Japanese text with Misaki: {processed_text}")
                return processed_text
            except Exception as e:
                logger.error(f"Error processing Japanese text with Misaki: {e}")
                logger.warning("Falling back to default text processing")
                return clean_text

        # For non-Japanese text or if Misaki failed, return the clean text
        return clean_text

    def generate_audio(self, text: str, file_name_no_ext: Optional[str] = None) -> str:
        """
        Generate speech audio file using Kokoro-82M TTS.

        Args:
            text: The text to speak
            file_name_no_ext: Name of the file without extension (optional)

        Returns:
            str: The path to the generated audio file
        """
        file_name = self.generate_cache_file_name(file_name_no_ext, self.file_extension)

        try:
            # Extract emotion from the text
            emotion_style, intensity = self._extract_emotion(text)

            # Preprocess text to handle emotion tags and Japanese text
            processed_text = self._preprocess_text(text)

            # Determine speech parameters based on emotion
            speed = self._get_speed_for_emotion(emotion_style, intensity)
            voice = self._get_voice_for_emotion(emotion_style, intensity)

            logger.info(f"Using emotion: {emotion_style} (intensity: {intensity:.2f})")
            logger.info(f"Speech parameters: voice={voice}, speed={speed}")

            # Check if we're using the custom wrapper
            if WRAPPER_AVAILABLE and isinstance(self.pipeline, KokoroWrapper):
                # Generate audio using our custom wrapper
                try:
                    # KokoroWrapper.generate returns the path to the generated audio file
                    wrapper_output = self.pipeline.generate(processed_text, file_name)
                    logger.info(f"Generated audio file using KokoroWrapper: {wrapper_output}")
                    return wrapper_output
                except Exception as e:
                    logger.error(f"Error generating audio with KokoroWrapper: {e}")
                    logger.warning("Falling back to standard KPipeline")
                    # Fall back to standard KPipeline
                    self._initialize_standard_pipeline()

            # Generate audio using standard Kokoro pipeline
            generator = self.pipeline(
                processed_text,
                voice=voice,
                speed=speed
            )

            # Kokoro returns a generator with (gs, ps, audio) tuples
            # We'll use the first generated audio segment
            for _, _, audio in generator:
                # Save the audio to a file
                sf.write(file_name, audio, self.sample_rate)
                break  # Just use the first segment for now

            logger.info(f"Generated audio file: {file_name}")
            return file_name

        except Exception as e:
            logger.error(f"Error generating audio with Kokoro-82M: {e}")
            # Create a silent audio file as fallback
            self._create_silent_audio(file_name, duration=1.0)
            return file_name

    def _extract_emotion(self, text: str) -> tuple:
        """
        Extract emotion and intensity from text with emotion tags.

        Args:
            text: Text with potential emotion tags

        Returns:
            Tuple of (emotion_style, intensity)
        """
        # Extract emotion tags using regex
        import re
        emotion_pattern = r'\[([\w]+)(?::([0-9]*\.?[0-9]+))?\]'
        matches = list(re.finditer(emotion_pattern, text))

        # Default to neutral if no emotion tags found
        if not matches:
            return "neutral", 0.0

        # Get the dominant emotion (using the first one for simplicity)
        emotion = matches[0].group(1).lower()
        intensity_str = matches[0].group(2)
        intensity = 1.0 if not intensity_str else float(intensity_str)

        # Map the emotion to Kokoro style if available
        emotion_style = self.emotion_mapping.get(emotion, "neutral")

        return emotion_style, intensity

    def _get_speed_for_emotion(self, emotion: str, intensity: float) -> float:
        """
        Get appropriate speech speed based on emotion and intensity.

        Args:
            emotion: The emotion style
            intensity: The emotion intensity (0.0 to 1.0)

        Returns:
            Speed parameter for Kokoro TTS
        """
        # Default speed is 1.0
        base_speed = 1.0

        # Only apply speed changes if intensity is significant
        if intensity < 0.3:
            return base_speed

        # Scale the effect based on intensity (0.3 to 1.0 mapped to 0.0 to 1.0)
        scaled_intensity = (intensity - 0.3) / 0.7

        # Apply emotion-specific speed adjustments
        if emotion in ["happy", "joy", "excited", "surprised"]:
            # Happy/excited speech is faster
            return base_speed + (0.3 * scaled_intensity)
        elif emotion in ["sad", "depressed", "fearful"]:
            # Sad speech is slower
            return base_speed - (0.3 * scaled_intensity)
        elif emotion in ["angry", "disgusted"]:
            # Angry speech can be slightly faster
            return base_speed + (0.2 * scaled_intensity)
        else:
            # Neutral or unknown emotions use base speed
            return base_speed

    def _get_voice_for_emotion(self, emotion: str, intensity: float) -> str:
        """
        Get appropriate voice based on emotion and intensity.

        For now, we just use the configured voice regardless of emotion.
        In the future, this could be extended to select different voice files
        based on emotion, or to blend multiple voice files.

        Args:
            emotion: The emotion style
            intensity: The emotion intensity (0.0 to 1.0)

        Returns:
            Voice parameter for Kokoro TTS
        """
        # For now, just use the configured voice
        # This could be extended in the future to select different voices
        # based on emotion or to blend multiple voices
        return self.voice

    async def async_generate_audio(self, text: str, file_name_no_ext: Optional[str] = None) -> str:
        """
        Asynchronously generate speech audio file.

        Args:
            text: The text to speak
            file_name_no_ext: Name of the file without extension (optional)

        Returns:
            str: The path to the generated audio file
        """
        # Run the synchronous method in a thread pool
        return await asyncio.to_thread(self.generate_audio, text, file_name_no_ext)

    def _create_silent_audio(self, file_path: str, duration: float = 1.0) -> None:
        """
        Create a silent audio file as a fallback.

        Args:
            file_path: Path to save the silent audio
            duration: Duration of the silent audio in seconds
        """
        # Create a silent audio file (all zeros)
        samples = int(duration * self.sample_rate)
        silent_audio = torch.zeros(samples)
        sf.write(file_path, silent_audio.numpy(), self.sample_rate)
        logger.warning(f"Created silent audio file as fallback: {file_path}")

    def remove_file(self, file_path: str) -> None:
        """
        Remove a generated audio file.

        Args:
            file_path: Path to the file to remove
        """
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.debug(f"Removed audio file: {file_path}")
        except Exception as e:
            logger.error(f"Error removing audio file {file_path}: {e}")
