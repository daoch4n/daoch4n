#!/usr/bin/env python3
"""
Test script for the TTS microservice.
"""

import sys
import argparse
import requests
import tempfile
import os
from pathlib import Path

def main():
    """Main function."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Test TTS microservice")
    parser.add_argument("--url", default="http://localhost:5000", help="URL of the TTS service")
    parser.add_argument("--voice", default="jf_alpha", help="Voice to use")
    parser.add_argument("--text", default="こんにちは、私はダオコです。[joy:0.8]よろしくお願いします！", help="Text to synthesize")
    parser.add_argument("--output", default=None, help="Output file")
    parser.add_argument("--list-voices", action="store_true", help="List available voices")
    parser.add_argument("--get-config", action="store_true", help="Get current configuration")
    parser.add_argument("--update-config", action="store_true", help="Update configuration")
    args = parser.parse_args()

    # Create a session
    session = requests.Session()

    # Check if the service is healthy
    try:
        response = session.get(f"{args.url}/health")
        response.raise_for_status()

        data = response.json()
        if data.get("status") != "ok":
            print(f"Error: Service is not healthy: {data}")
            sys.exit(1)

        print("Service is healthy")
    except Exception as e:
        print(f"Error checking service health: {e}")
        sys.exit(1)

    # List available voices
    if args.list_voices:
        try:
            response = session.get(f"{args.url}/voices")
            response.raise_for_status()

            data = response.json()
            print("Available voices:")
            for voice in data.get("voices", []):
                if voice == data.get("default"):
                    print(f"- {voice} (default)")
                else:
                    print(f"- {voice}")

            sys.exit(0)
        except Exception as e:
            print(f"Error getting available voices: {e}")
            sys.exit(1)

    # Get current configuration
    if args.get_config:
        try:
            response = session.get(f"{args.url}/config")
            response.raise_for_status()

            config = response.json()
            print("Current configuration:")
            for key, value in config.items():
                print(f"- {key}: {value}")

            sys.exit(0)
        except Exception as e:
            print(f"Error getting configuration: {e}")
            sys.exit(1)

    # Update configuration
    if args.update_config:
        try:
            # Example configuration update
            new_config = {
                "sample_rate": 24000,
                "output_format": "wav",
                "emotion_mapping": {
                    "joy": 1.2,
                    "sadness": 0.8,
                    "anger": 1.1,
                    "fear": 0.9,
                    "surprise": 1.3,
                    "disgust": 0.85,
                    "neutral": 1.0,
                    "smirk": 1.1
                }
            }

            print("Updating configuration...")
            response = session.post(f"{args.url}/config", json=new_config)
            response.raise_for_status()

            data = response.json()
            if data.get("status") == "ok":
                print("Configuration updated successfully")
                print("New configuration:")
                for key, value in data.get("config", {}).items():
                    print(f"- {key}: {value}")
            else:
                print(f"Error updating configuration: {data}")

            sys.exit(0)
        except Exception as e:
            print(f"Error updating configuration: {e}")
            sys.exit(1)

    # Generate speech
    try:
        # Prepare request data
        data = {
            "text": args.text,
            "voice": args.voice
        }

        print(f"Generating speech for text: {args.text}")
        print(f"Using voice: {args.voice}")

        # Send request to TTS service
        response = session.post(f"{args.url}/tts", json=data)
        response.raise_for_status()

        # Create a temporary file if output_path is not provided
        if args.output is None:
            fd, output_path = tempfile.mkstemp(suffix=".wav")
            os.close(fd)
        else:
            output_path = args.output

        # Save the audio to a file
        with open(output_path, "wb") as f:
            f.write(response.content)

        print(f"Generated audio file: {output_path}")

        # Try to play the audio
        try:
            import sounddevice as sd
            import soundfile as sf

            print("Playing audio...")
            audio, sr = sf.read(output_path)
            sd.play(audio, sr)
            sd.wait()
        except ImportError:
            print("sounddevice or soundfile not installed. Please install them to play audio.")
            print(f"You can play the audio file manually: {output_path}")
        except Exception as e:
            print(f"Error playing audio: {e}")
            print(f"You can play the audio file manually: {output_path}")
    except Exception as e:
        print(f"Error generating speech: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
