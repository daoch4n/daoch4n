"""
Client for the TTS microservice.
"""

import os
import tempfile
import requests
from pathlib import Path
from typing import Optional, List, Dict, Any
from loguru import logger

from .tts_interface import TTSInterface

class TTSServiceClient(TTSInterface):
    """Client for the TTS microservice that implements the TTSInterface."""

    def __init__(self, base_url: str = "http://localhost:5000"):
        """
        Initialize the TTS service client.

        Args:
            base_url: Base URL of the TTS service
        """
        self.base_url = base_url
        self.session = requests.Session()

    def get_available_voices(self) -> List[str]:
        """
        Get available voices from the TTS service.

        Returns:
            List of available voice names
        """
        try:
            response = self.session.get(f"{self.base_url}/voices")
            response.raise_for_status()

            data = response.json()
            return data.get("voices", [])
        except Exception as e:
            logger.error(f"Error getting available voices: {e}")
            return []

    def generate_speech(self, text: str, voice: str = "jf_alpha", output_path: Optional[str] = None) -> str:
        """
        Generate speech from text.

        Args:
            text: Text to synthesize
            voice: Voice to use
            output_path: Path to save the generated audio file (optional)

        Returns:
            Path to the generated audio file
        """
        try:
            # Prepare request data
            data = {
                "text": text,
                "voice": voice
            }

            # Send request to TTS service
            response = self.session.post(f"{self.base_url}/tts", json=data)
            response.raise_for_status()

            # Create a temporary file if output_path is not provided
            if output_path is None:
                fd, output_path = tempfile.mkstemp(suffix=".wav")
                os.close(fd)

            # Save the audio to a file
            with open(output_path, "wb") as f:
                f.write(response.content)

            logger.info(f"Generated audio file: {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"Error generating speech: {e}")
            raise

    def generate_audio(self, text: str, file_name_no_ext=None) -> str:
        """
        Generate speech audio file using TTS.

        Args:
            text: Text to synthesize
            file_name_no_ext: Name of the file without file extension (optional)

        Returns:
            Path to the generated audio file
        """
        # Generate a file name if not provided
        if file_name_no_ext is None:
            output_path = None
        else:
            output_path = self.generate_cache_file_name(file_name_no_ext)

        # Use the default voice (jf_alpha)
        return self.generate_speech(text, output_path=output_path)

    def health_check(self) -> bool:
        """
        Check if the TTS service is healthy.

        Returns:
            True if the service is healthy, False otherwise
        """
        try:
            response = self.session.get(f"{self.base_url}/health")
            response.raise_for_status()

            data = response.json()
            return data.get("status") == "ok"
        except Exception as e:
            logger.error(f"Error checking TTS service health: {e}")
            return False
