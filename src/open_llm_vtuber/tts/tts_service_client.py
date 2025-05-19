"""
Client for the TTS microservice.

This module provides a client for the TTS microservice that implements the TTSInterface.
It handles communication with the TTS service and provides methods for generating speech
and managing the service configuration.
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
        self.cache_dir = "cache"
        self.file_extension = "wav"

        # Create cache directory if it doesn't exist
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)

        # Try to get the current configuration
        self._update_local_config()

    def _update_local_config(self) -> None:
        """
        Update local configuration from the TTS service.
        """
        try:
            response = self.session.get(f"{self.base_url}/config")
            if response.status_code == 200:
                config = response.json()
                if "output_format" in config:
                    self.file_extension = config["output_format"]
                logger.info(f"Updated local configuration from TTS service")
        except Exception as e:
            logger.warning(f"Failed to get configuration from TTS service: {e}")

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

    def get_config(self) -> Dict[str, Any]:
        """
        Get the current configuration from the TTS service.

        Returns:
            Dictionary containing the current configuration
        """
        try:
            response = self.session.get(f"{self.base_url}/config")
            response.raise_for_status()

            return response.json()
        except Exception as e:
            logger.error(f"Error getting configuration: {e}")
            return {}

    def update_config(self, config: Dict[str, Any]) -> bool:
        """
        Update the TTS service configuration.

        Args:
            config: Dictionary containing the new configuration

        Returns:
            True if the configuration was updated successfully, False otherwise
        """
        try:
            response = self.session.post(f"{self.base_url}/config", json=config)
            response.raise_for_status()

            # Update local configuration
            self._update_local_config()

            return True
        except Exception as e:
            logger.error(f"Error updating configuration: {e}")
            return False

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

            # Create a file in the cache directory if output_path is not provided
            if output_path is None:
                os.makedirs(self.cache_dir, exist_ok=True)
                output_path = os.path.join(self.cache_dir, f"{hash(text)}_{voice}.{self.file_extension}")

            # Save the audio to a file
            with open(output_path, "wb") as f:
                f.write(response.content)

            logger.info(f"Generated audio file: {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"Error generating speech: {e}")

            # Create a silent audio file as fallback
            if output_path is None:
                os.makedirs(self.cache_dir, exist_ok=True)
                output_path = os.path.join(self.cache_dir, f"silent_{hash(text)}_{voice}.{self.file_extension}")

            try:
                # Create a silent WAV file (1 second of silence)
                with open(output_path, "wb") as f:
                    # Simple WAV header for 1 second of silence at 24kHz
                    sample_rate = 24000
                    channels = 1
                    bits_per_sample = 16

                    # Calculate sizes
                    data_size = sample_rate * channels * bits_per_sample // 8
                    file_size = 36 + data_size

                    # Write WAV header
                    f.write(b"RIFF")
                    f.write(file_size.to_bytes(4, byteorder="little"))
                    f.write(b"WAVE")
                    f.write(b"fmt ")
                    f.write((16).to_bytes(4, byteorder="little"))
                    f.write((1).to_bytes(2, byteorder="little"))  # PCM format
                    f.write(channels.to_bytes(2, byteorder="little"))
                    f.write(sample_rate.to_bytes(4, byteorder="little"))
                    f.write((sample_rate * channels * bits_per_sample // 8).to_bytes(4, byteorder="little"))
                    f.write((channels * bits_per_sample // 8).to_bytes(2, byteorder="little"))
                    f.write(bits_per_sample.to_bytes(2, byteorder="little"))
                    f.write(b"data")
                    f.write(data_size.to_bytes(4, byteorder="little"))

                    # Write silence (all zeros)
                    f.write(b"\x00" * data_size)

                logger.warning(f"Created silent audio file as fallback: {output_path}")
            except Exception as fallback_error:
                logger.error(f"Failed to create fallback silent audio: {fallback_error}")

            return output_path

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
