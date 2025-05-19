"""
AllTalk TTS integration for Open-LLM-VTuber.

This module provides integration with AllTalk TTS, a local text-to-speech system
that supports voice cloning and RVC voice conversion. It also handles emotion tags
for expressive speech synthesis.
"""

import os
import json
import re
import requests
from pathlib import Path
from typing import Optional, Dict, Tuple, Any
from loguru import logger
from .tts_interface import TTSInterface


class TTSEngine(TTSInterface):
    """
    AllTalk TTS engine implementation.

    This class provides integration with AllTalk TTS, which is running as a local server.
    It supports both standard TTS and RVC voice conversion, as well as emotion-aware
    speech synthesis through emotion tags in the text.
    """

    def __init__(
        self,
        api_url: str = "http://127.0.0.1:7851",
        voice: str = "female_01.wav",
        language: str = "en",
        rvc_enabled: bool = False,
        rvc_model: str = "Disabled",
        rvc_pitch: int = 0,
        output_format: str = "wav",
        emotion_mapping: Optional[Dict[str, str]] = None,
    ):
        """
        Initialize the AllTalk TTS engine.

        Args:
            api_url: The URL of the AllTalk TTS API server
            voice: The voice to use for TTS
            language: The language to use for TTS
            rvc_enabled: Whether to enable RVC voice conversion
            rvc_model: The RVC model to use for voice conversion
            rvc_pitch: The pitch adjustment for RVC voice conversion
            output_format: The output audio format (wav, mp3, etc.)
            emotion_mapping: Optional mapping from emotion tags to AllTalk styles
        """
        self.api_url = api_url
        self.voice = voice
        self.language = language
        self.rvc_enabled = rvc_enabled
        self.rvc_model = rvc_model
        self.rvc_pitch = rvc_pitch
        self.file_extension = output_format
        self.new_audio_dir = "cache"

        # Default emotion mapping (can be overridden)
        self.emotion_mapping = emotion_mapping or {
            "joy": "happy",
            "sadness": "sad",
            "anger": "angry",
            "fear": "fearful",
            "surprise": "surprised",
            "disgust": "disgusted",
            "neutral": "neutral",
            "smirk": "happy"
        }

        # Create cache directory if it doesn't exist
        if not os.path.exists(self.new_audio_dir):
            os.makedirs(self.new_audio_dir)

        # Check if AllTalk TTS server is running
        try:
            # Check server status
            response = requests.get(f"{self.api_url}/api/ready", timeout=5)
            if response.status_code == 200:
                logger.info("AllTalk TTS server is running")

                # Get available character voices
                try:
                    voices_response = requests.get(f"{self.api_url}/api/charactervoices", timeout=5)
                    if voices_response.status_code == 200:
                        voices_data = voices_response.json()
                        if isinstance(voices_data, list):
                            logger.info(f"Available character voices: {', '.join(voices_data)}")
                        else:
                            logger.info(f"Character voices response: {voices_data}")
                except Exception as e:
                    logger.warning(f"Failed to get character voices: {e}")

                # Get available RVC models if RVC is enabled
                if self.rvc_enabled:
                    try:
                        rvc_response = requests.get(f"{self.api_url}/api/rvcmodels", timeout=5)
                        if rvc_response.status_code == 200:
                            rvc_data = rvc_response.json()
                            if isinstance(rvc_data, list):
                                logger.info(f"Available RVC models: {', '.join(rvc_data)}")
                            else:
                                logger.info(f"RVC models response: {rvc_data}")
                    except Exception as e:
                        logger.warning(f"Failed to get RVC models: {e}")
            else:
                logger.error(f"AllTalk TTS server returned status code {response.status_code}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to connect to AllTalk TTS server: {e}")
            logger.error("Make sure AllTalk TTS server is running at the specified URL")

    def _extract_emotion(self, text: str) -> Tuple[str, float]:
        """
        Extract emotion and intensity from text with emotion tags.

        Args:
            text: Text with potential emotion tags

        Returns:
            Tuple of (emotion_style, intensity)
        """
        # Extract emotion tags using regex
        emotion_pattern = r'\[([\w]+)(?::([0-9]*\.?[0-9]+))?\]'
        matches = list(re.finditer(emotion_pattern, text))

        # Default to neutral if no emotion tags found
        if not matches:
            return "neutral", 0.0

        # Get the dominant emotion (using the first one for simplicity)
        emotion = matches[0].group(1).lower()
        intensity_str = matches[0].group(2)
        intensity = 1.0 if not intensity_str else float(intensity_str)

        # Map the emotion to AllTalk style if available
        emotion_style = self.emotion_mapping.get(emotion, "neutral")

        return emotion_style, intensity

    def _preprocess_text(self, text: str) -> str:
        """
        Preprocess text before sending to the TTS model.

        This method handles emotion tags and removes them from the text.

        Args:
            text: The input text with potential emotion tags

        Returns:
            Processed text ready for the TTS model
        """
        # Extract and remove emotion tags using regex
        emotion_pattern = r'\[([\w]+)(?::([0-9]*\.?[0-9]+))?\]'

        # Remove all emotion tags from the text
        clean_text = re.sub(emotion_pattern, '', text)

        return clean_text

    def _get_pitch_for_emotion(self, emotion: str, intensity: float) -> int:
        """
        Get appropriate pitch adjustment based on emotion and intensity.

        Args:
            emotion: The emotion style
            intensity: The emotion intensity (0.0 to 1.0)

        Returns:
            Pitch adjustment for AllTalk TTS
        """
        # Default pitch adjustment is the configured pitch
        base_pitch = self.rvc_pitch

        # Only apply pitch changes if intensity is significant
        if intensity < 0.3:
            return base_pitch

        # Scale the effect based on intensity (0.3 to 1.0 mapped to 0.0 to 1.0)
        scaled_intensity = (intensity - 0.3) / 0.7

        # Apply emotion-specific pitch adjustments
        if emotion in ["happy", "joy", "excited"]:
            # Happy/excited speech has higher pitch
            return base_pitch + int(2 * scaled_intensity)
        elif emotion in ["sad", "depressed", "fearful"]:
            # Sad speech has lower pitch
            return base_pitch - int(2 * scaled_intensity)
        elif emotion in ["angry", "disgusted"]:
            # Angry speech can have slightly lower pitch
            return base_pitch - int(1 * scaled_intensity)
        elif emotion in ["surprised"]:
            # Surprised speech has higher pitch
            return base_pitch + int(3 * scaled_intensity)
        else:
            # Neutral or unknown emotions use base pitch
            return base_pitch

    def generate_audio(self, text, file_name_no_ext=None):
        """
        Generate speech audio file using AllTalk TTS.

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

            # Preprocess text to handle emotion tags
            processed_text = self._preprocess_text(text)

            # Determine speech parameters based on emotion
            pitch_adjustment = self._get_pitch_for_emotion(emotion_style, intensity)

            logger.info(f"Using emotion: {emotion_style} (intensity: {intensity:.2f})")
            logger.info(f"Speech parameters: pitch={pitch_adjustment}")

            # Prepare the request data according to the API documentation
            data = {
                "text_input": processed_text,
                "character_voice_gen": self.voice,
                "language": self.language,
                "output_file_name": Path(file_name).stem,
                "output_file_timestamp": True,
                "autoplay": False
            }

            # If RVC is enabled, add RVC parameters with emotion-adjusted pitch
            if self.rvc_enabled and self.rvc_model != "Disabled":
                logger.info(f"Using RVC voice conversion with model: {self.rvc_model}")
                data["rvccharacter_voice_gen"] = self.rvc_model
                data["rvccharacter_pitch"] = pitch_adjustment

            # Send request to TTS generation endpoint
            logger.info(f"Sending TTS request with data: {data}")
            response = requests.post(
                f"{self.api_url}/api/tts-generate",
                data=data,
                timeout=120
            )

            # Check if the request was successful
            if response.status_code == 200:
                response_data = response.json()
                logger.info(f"TTS response: {response_data}")

                if "output_file_url" in response_data:
                    # Get the audio file URL
                    audio_url = response_data['output_file_url']
                    logger.info(f"Audio URL: {audio_url}")

                    # Get the audio file from the server
                    audio_response = requests.get(
                        f"{self.api_url}{audio_url}",
                        timeout=120
                    )

                    if audio_response.status_code == 200:
                        # Save the audio content to a file
                        with open(file_name, "wb") as audio_file:
                            audio_file.write(audio_response.content)
                        logger.info(f"Audio saved to: {file_name}")
                        return file_name
                    else:
                        logger.error(f"Failed to get audio file: {audio_response.status_code}")
                        logger.error(f"Audio Response: {audio_response.text}")
                        return None
                else:
                    logger.error(f"Unexpected response format: {response_data}")
                    return None
            else:
                # Handle errors or unsuccessful requests
                logger.error(f"Error: Failed to generate audio. Status code: {response.status_code}")
                logger.error(f"Response: {response.text}")
                return None

        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {e}")
            return None
        except Exception as e:
            logger.error(f"Error generating audio: {e}")
            return None
