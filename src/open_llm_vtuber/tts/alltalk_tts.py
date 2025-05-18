"""
AllTalk TTS integration for Open-LLM-VTuber.

This module provides integration with AllTalk TTS, a local text-to-speech system
that supports voice cloning and RVC voice conversion.
"""

import os
import json
import requests
from pathlib import Path
from loguru import logger
from .tts_interface import TTSInterface


class TTSEngine(TTSInterface):
    """
    AllTalk TTS engine implementation.

    This class provides integration with AllTalk TTS, which is running as a local server.
    It supports both standard TTS and RVC voice conversion.
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
        """
        self.api_url = api_url
        self.voice = voice
        self.language = language
        self.rvc_enabled = rvc_enabled
        self.rvc_model = rvc_model
        self.rvc_pitch = rvc_pitch
        self.file_extension = output_format
        self.new_audio_dir = "cache"

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
            # Prepare the request data according to the API documentation
            data = {
                "text_input": text,
                "character_voice_gen": self.voice,
                "language": self.language,
                "output_file_name": Path(file_name).stem,
                "output_file_timestamp": True,
                "autoplay": False
            }

            # If RVC is enabled, add RVC parameters
            if self.rvc_enabled and self.rvc_model != "Disabled":
                logger.info(f"Using RVC voice conversion with model: {self.rvc_model}")
                data["rvccharacter_voice_gen"] = self.rvc_model
                data["rvccharacter_pitch"] = self.rvc_pitch

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
