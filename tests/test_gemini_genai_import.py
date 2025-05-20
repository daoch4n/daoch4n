#!/usr/bin/env python3
"""Test script to check the correct import syntax for the Google Gen AI SDK."""

try:
    print("Trying import google.genai...")
    import google.genai
    print("Success! The correct import is: import google.genai")
except ImportError as e:
    print(f"Error: {e}")

try:
    print("\nTrying from google import genai...")
    from google import genai
    print("Success! The correct import is: from google import genai")
except ImportError as e:
    print(f"Error: {e}")

try:
    print("\nTrying import google_genai...")
    import google_genai
    print("Success! The correct import is: import google_genai")
except ImportError as e:
    print(f"Error: {e}")
