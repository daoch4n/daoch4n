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
            response = requests.get(f"{self.api_url}/api/ready", timeout=5)
            if response.status_code == 200:
                logger.info("AllTalk TTS server is running")

                # Get available voices
                voices_response = requests.get(f"{self.api_url}/api/voices", timeout=5)
                if voices_response.status_code == 200:
                    voices_data = voices_response.json()
                    logger.info(f"Available voices: {', '.join(voices_data)}")

                # Get available RVC models if RVC is enabled
                if self.rvc_enabled:
                    rvc_response = requests.get(f"{self.api_url}/api/rvcvoices", timeout=5)
                    if rvc_response.status_code == 200:
                        rvc_data = rvc_response.json()
                        logger.info(f"Available RVC models: {', '.join(rvc_data)}")
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
            # Always use the standard TTS endpoint first
            data = {
                "text_input": text,
                "voice_selection": self.voice,
                "language_selection": self.language,
                "output_filename": Path(file_name).stem
            }

            # Send request to standard TTS endpoint
            response = requests.post(
                f"{self.api_url}/api/tts-generate",
                data=data,
                timeout=120
            )

            # Check if the request was successful
            if response.status_code == 200:
                response_data = response.json()

                if "output_file_url" in response_data:
                    # Get the audio file path
                    audio_url = response_data['output_file_url']

                    # If RVC is enabled, apply RVC to the generated audio
                    if self.rvc_enabled and self.rvc_model != "Disabled":
                        logger.info(f"Applying RVC voice conversion with model: {self.rvc_model}")

                        # Extract the file name from the URL
                        # The URL is typically in the format "/api/audio/filename.wav"
                        audio_file_name = os.path.basename(audio_url)

                        # For voice2rvc, we need to use the full path relative to the outputs directory
                        # The error suggests the file is in the "outputs" directory
                        audio_file_path = f"outputs/{audio_file_name}"

                        # Create output path for RVC-processed audio
                        output_file_name = f"rvc_{Path(file_name).stem}.{self.file_extension}"
                        output_rvc_path = f"outputs/{output_file_name}"

                        logger.info(f"Using input file path: {audio_file_path}")
                        logger.info(f"Using output file path: {output_rvc_path}")

                        # Prepare RVC request data
                        rvc_data = {
                            "input_tts_path": audio_file_path,
                            "output_rvc_path": output_rvc_path,
                            "pth_name": self.rvc_model,
                            "pitch": str(self.rvc_pitch),
                            "method": "harvest"  # Default method
                        }

                        # Send request to voice2rvc endpoint
                        rvc_response = requests.post(
                            f"{self.api_url}/api/voice2rvc",
                            data=rvc_data,
                            timeout=120
                        )

                        if rvc_response.status_code == 200:
                            rvc_response_data = rvc_response.json()

                            if "status" in rvc_response_data and rvc_response_data["status"] == "success":
                                if "output_path" in rvc_response_data:
                                    # The output_path from the response is the full path to the processed file
                                    # We need to extract just the filename for the API URL
                                    output_path = rvc_response_data["output_path"]
                                    logger.info(f"RVC processing returned output path: {output_path}")

                                    # Extract just the filename from the output path
                                    output_filename = os.path.basename(output_path)

                                    # Update the audio URL to the RVC-processed audio
                                    audio_url = f"/api/audio/{output_filename}"
                                    logger.info(f"RVC processing successful, new audio URL: {audio_url}")
                                else:
                                    # If no output_path is provided, use our predefined output filename
                                    logger.warning(f"RVC processing did not return an output path: {rvc_response_data}")
                                    audio_url = f"/api/audio/{output_file_name}"
                                    logger.info(f"Using fallback audio URL: {audio_url}")
                            else:
                                logger.warning(f"RVC processing returned non-success status: {rvc_response_data}")
                        else:
                            logger.error(f"Failed to apply RVC: {rvc_response.status_code}")
                            logger.error(f"RVC Response: {rvc_response.text}")

                    # Get the audio file from the server
                    audio_response = requests.get(
                        f"{self.api_url}{audio_url}",
                        timeout=120
                    )

                    if audio_response.status_code == 200:
                        # Save the audio content to a file
                        with open(file_name, "wb") as audio_file:
                            audio_file.write(audio_response.content)
                        return file_name
                    else:
                        logger.error(f"Failed to get audio file: {audio_response.status_code}")
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
