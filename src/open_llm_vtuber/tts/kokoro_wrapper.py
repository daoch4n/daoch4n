# -*- coding: utf-8 -*-
"""
Custom wrapper for the Kokoro TTS engine.

This wrapper facilitates direct integration of the Kokoro TTS library into an application.
It handles the initialization of the Kokoro pipeline, MeCab tagger setup,
and provides a method to generate speech.

Note: For production environments or general use, the recommended approach is to
use the TTS microservice as detailed in the project documentation (see docs/kokoro_tts_integration.md).
This KokoroWrapper is primarily intended for:
- Legacy systems already using direct integration.
- Specific testing or development scenarios where direct library control is beneficial.
- Situations where a separate microservice is not feasible.

Proper setup of MeCab and its dictionaries is crucial for this wrapper to function correctly,
especially for Japanese language processing.
"""

import os
import sys
from pathlib import Path
from loguru import logger

# Try to import the required modules
try:
    # fugashi.GenericTagger is imported by mecab_utils
    from kokoro import KPipeline
    from open_llm_vtuber.utils.mecab_utils import get_mecab_tagger, GenericTagger # GenericTagger for type hint
except ImportError as e:
    logger.error(
        "Failed to import required modules (fugashi or kokoro). "
        "Please ensure they are installed, e.g., with: pip install fugashi[unidic-lite] kokoro. "
        f"Details: {e}"
    )
    # Depending on the application structure, sys.exit(1) might be too abrupt.
    # Consider raising a custom exception or allowing the app to handle this.
    # For now, re-raising to make it clear initialization failed.
    raise ImportError("Missing essential TTS dependencies: fugashi or kokoro.") from e

class KokoroWrapper:
    """
    Wraps the Kokoro TTS engine for direct use, managing MeCab tagger and pipeline initialization.

    As highlighted in the module documentation, consider using the TTS microservice for
    most applications. This class is for specific direct integration needs.
    """

    def __init__(self, voice: str = "jf_alpha", language: str = "ja", device: str = "cpu", repo_id: str = None, cache_dir: str = "cache"):
        """
        Initializes the Kokoro TTS wrapper, setting up the MeCab tagger and Kokoro pipeline.

        Args:
            voice: The Kokoro voice to use (e.g., "jf_alpha").
            language: The language code (e.g., "ja" for Japanese).
            device: The device for TTS inference ("cpu" or "cuda").
            repo_id: Optional Hugging Face repository ID for a custom Kokoro model.
            cache_dir: Directory for model caching (used by underlying Kokoro/HF libraries).
        """
        logger.info("Initializing KokoroWrapper for direct TTS integration...")
        logger.info("Reminder: For production, the TTS microservice is generally recommended.")

        self.voice = voice
        self.language = language
        self.device = device
        self.repo_id = repo_id
        self.cache_dir = cache_dir

        try:
            # Create the tagger using the utility function
            self.tagger = self._create_tagger_with_util()
            if self.tagger is None:
                # The utility function logs errors, but we need to halt initialization here
                raise RuntimeError("Failed to initialize MeCab tagger via utility function. KokoroWrapper cannot proceed.")

            # Initialize the Kokoro pipeline
            self._initialize_pipeline()
        except Exception as e:
            logger.error(f"Error during KokoroWrapper initialization: {e}")
            # Propagate the error to indicate that the wrapper is not usable.
            # Consider a custom exception class for better error handling upstream.
            raise RuntimeError(f"KokoroWrapper setup failed: {e}") from e

    def _create_tagger_with_util(self) -> Optional[GenericTagger]:
        """
        Initializes and returns a MeCab tagger using the shared utility function.

        Returns:
            A GenericTagger instance if successful, otherwise None.
        """
        logger.info("Attempting to initialize MeCab tagger via mecab_utils.get_mecab_tagger...")
        # The mecab_utils.get_mecab_tagger handles its own logging for success/failure of different methods.
        tagger = get_mecab_tagger()
        if tagger is None:
            logger.error(
                "MeCab tagger initialization failed using shared utility. "
                "Japanese text processing will be severely impacted or fail."
            )
            # This method returning None will be caught in __init__
        return tagger

    def _initialize_pipeline(self):
        """
        Initializes the Kokoro TTS pipeline.

        This includes an attempt to patch the JAG2P component using a local
        `custom_jag2p` module, if available. It then sets up the KPipeline
        with the specified language, model repository, and device.

        Raises:
            RuntimeError: If pipeline initialization fails for any reason (e.g., model download issues,
                          compatibility problems, errors from `custom_jag2p`).
        """
        try:
            # Attempt to import and apply a custom patch for JAG2P (Japanese Grapheme-to-Phoneme).
            # This might be for bug fixes or project-specific customizations.
            try:
                from .custom_jag2p import patch_jag2p
                patch_jag2p()
                logger.info("Successfully applied custom_jag2p patch.")
            except ImportError:
                logger.warning("custom_jag2p.py not found or patch_jag2p function missing. Using default JAG2P from Kokoro library.")
            except Exception as e_patch: # More specific exceptions can be caught by patch_jag2p itself if designed so
                logger.warning(f"Failed to apply custom_jag2p patch: {e_patch}. Using default JAG2P.")
                # Depending on criticality, could re-raise or just warn.

            lang_code = self._convert_language_code(self.language)

            logger.info(f"Initializing Kokoro pipeline. Language: {self.language} -> Code: {lang_code}, Device: {self.device}")
            if self.repo_id:
                logger.info(f"Using custom model repository: {self.repo_id}")
                self.pipeline = KPipeline(lang_code=lang_code, repo_id=self.repo_id, device=self.device)
            else:
                logger.info("Using default Kokoro model repository.")
                self.pipeline = KPipeline(lang_code=lang_code, device=self.device)

            logger.info(f"Successfully initialized Kokoro pipeline with voice: {self.voice}")

        except FileNotFoundError as e_fnf:
            logger.error(f"Model files not found during Kokoro pipeline initialization: {e_fnf}. "
                         "Ensure models are downloaded and accessible, or check `repo_id` and `cache_dir`.")
            raise RuntimeError(f"Kokoro model files not found: {e_fnf}") from e_fnf
        except ValueError as e_val:
            logger.error(f"Invalid value provided during Kokoro pipeline initialization: {e_val}."
                         " Check language code, device, or other parameters.")
            raise RuntimeError(f"Kokoro pipeline configuration error: {e_val}") from e_val
        except ImportError as e_imp: # Should be caught at module level, but as safeguard
            logger.error(f"A module import failed during pipeline initialization (should not happen here): {e_imp}")
            raise RuntimeError(f"Kokoro dependency missing: {e_imp}") from e_imp
        except Exception as e_pipeline: # Catch-all for other Kokoro internal errors
            logger.error(f"An unexpected error occurred while initializing the Kokoro pipeline: {e_pipeline}")
            logger.error("This could be due to an issue with the Kokoro library itself, model compatibility, or system configuration.")
            logger.error("Consider using the TTS microservice for a more isolated and potentially stable environment.")
            raise RuntimeError(f"Kokoro pipeline failed to initialize: {e_pipeline}") from e_pipeline

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
        return language

    def generate(self, text, output_path=None):
        """
        Generates speech from the given text and saves it to the specified output path.

        Args:
            text: The input text to synthesize.
            output_path: The file path where the generated WAV audio will be saved.
                         If None, a default path might be used or an error raised
                         (current implementation requires it).

        Returns:
            The path to the generated audio file.

        Raises:
            ImportError: If `soundfile` is not installed.
            IOError: If the audio file cannot be written.
            RuntimeError: If speech generation fails or no audio is produced.
            ValueError: If `output_path` is not provided.
        """
        if not output_path:
            # Or define a default output_path, e.g., tempfile.mktemp(suffix=".wav")
            logger.error("Output path must be provided to save the generated audio.")
            raise ValueError("output_path cannot be None for generate method.")

        try:
            logger.debug(f"Generating speech for text: '{text[:50]}...' with voice: {self.voice}")
            # The pipeline call itself might raise errors if text is malformed or an internal state is bad.
            generator = self.pipeline(text, voice=self.voice)

            # Kokoro returns a generator; we typically expect one audio segment.
            audio_data = None
            for _, _, audio_segment in generator:
                audio_data = audio_segment
                break  # Use the first generated audio segment

            if audio_data is None:
                logger.warning(f"No audio data was produced by the Kokoro pipeline for text: {text}")
                raise RuntimeError("Kokoro pipeline did not generate any audio data.")

            # Save the audio to a file
            try:
                import soundfile as sf
            except ImportError as e_imp:
                logger.error("Soundfile library not found. Please install it: pip install soundfile")
                raise ImportError("Soundfile library is required to save audio.") from e_imp

            # Ensure the output directory exists
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)

            sf.write(output_path, audio_data, 24000)  # Kokoro default sample rate is 24kHz
            logger.info(f"Successfully generated speech and saved to: {output_path}")
            return output_path

        except (IOError, PermissionError) as e_io:
            logger.error(f"Failed to write audio to file {output_path}: {e_io}")
            raise IOError(f"Cannot write audio to {output_path}: {e_io}") from e_io
        except RuntimeError as e_rt: # Catch specific runtime errors from pipeline or our own
            logger.error(f"Runtime error during speech generation: {e_rt}")
            raise # Re-raise known RuntimeErrors
        except Exception as e_gen: # Catch-all for other unexpected errors from pipeline or soundfile
            logger.error(f"An unexpected error occurred during speech generation or saving: {e_gen}")
            logger.error(
                "If this issue persists with direct integration, consider using the TTS microservice. "
                "If using the microservice, check its logs."
            )
            raise RuntimeError(f"Speech generation failed: {e_gen}") from e_gen
