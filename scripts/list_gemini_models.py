#!/usr/bin/env python3
"""
Script to list available Gemini models for the current API key.
This helps diagnose which models are actually accessible.
"""

import os
import sys
import google.generativeai as genai

def list_available_models(api_key=None):
    """List all available Gemini models for the given API key."""
    # Use provided API key or get from environment
    if api_key:
        genai.configure(api_key=api_key)
    elif "GEMINI_API_KEY" in os.environ:
        genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    else:
        print("Error: No API key provided. Please provide as argument or set GEMINI_API_KEY environment variable.")
        sys.exit(1)

    try:
        # List all models
        print("Available models:")
        print("-" * 50)

        models = genai.list_models()

        for model in models:
            print(f"Model: {model.name}")
            print(f"  Display name: {getattr(model, 'display_name', 'N/A')}")
            print(f"  Description: {getattr(model, 'description', 'N/A')}")
            print(f"  Supported generation methods: {getattr(model, 'supported_generation_methods', 'N/A')}")
            print(f"  Input token limit: {getattr(model, 'input_token_limit', 'N/A')}")
            print(f"  Output token limit: {getattr(model, 'output_token_limit', 'N/A')}")
            print("-" * 50)

        # Specifically check for Live API models
        live_models = [m for m in models if "live" in m.name.lower()]
        if live_models:
            print("\nLive API Models:")
            for model in live_models:
                print(f"- {model.name}")
        else:
            print("\nNo Live API models found.")

        # Check for Flash models
        flash_models = [m for m in models if "flash" in m.name.lower()]
        if flash_models:
            print("\nFlash Models:")
            for model in flash_models:
                print(f"- {model.name}")
        else:
            print("\nNo Flash models found.")

    except Exception as e:
        print(f"Error listing models: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Get API key from command line if provided
    api_key = None
    if len(sys.argv) > 1:
        api_key = sys.argv[1]

    # Get API key from conf.yaml if not provided
    if not api_key:
        try:
            import yaml
            with open("conf.yaml", "r") as f:
                config = yaml.safe_load(f)
                api_key = config.get("character_config", {}).get("agent_config", {}).get("agent_settings", {}).get("gemini_live_agent", {}).get("api_key")
                if not api_key:
                    # Try the regular gemini_llm config
                    api_key = config.get("character_config", {}).get("agent_config", {}).get("llm_configs", {}).get("gemini_llm", {}).get("llm_api_key")
        except Exception as e:
            print(f"Warning: Could not read API key from conf.yaml: {e}")

    list_available_models(api_key)
