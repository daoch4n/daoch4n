#!/usr/bin/env python3
"""Test script to explore the available methods in the Google Gen AI SDK."""

import asyncio
import inspect
import google.genai as genai
from google.genai import types as genai_types

API_KEY = "AIzaSyAJA2znNF2Xp-6vztj2bSmP-oskQSVTOvY"  # Using the API key from conf.yaml

async def main():
    # Create a client
    client = genai.Client(api_key=API_KEY)
    
    # Print available methods and attributes of the client
    print("Client attributes and methods:")
    for attr in dir(client):
        if not attr.startswith("_"):
            print(f"  {attr}")
    
    print("\nClient.aio attributes and methods:")
    for attr in dir(client.aio):
        if not attr.startswith("_"):
            print(f"  {attr}")
    
    print("\nClient.aio.live attributes and methods:")
    for attr in dir(client.aio.live):
        if not attr.startswith("_"):
            print(f"  {attr}")
    
    # Try to connect to the Gemini Live API
    try:
        print("\nConnecting to Gemini Live API...")
        live_connect = client.aio.live.connect(
            model="gemini-2.0-flash-live-001",
            config={}
        )
        
        # Enter the context manager to get the actual session
        async with live_connect as session:
            print("\nSession attributes and methods:")
            for attr in dir(session):
                if not attr.startswith("_"):
                    print(f"  {attr}")
            
            # Try to get the signature of the send_client_content method
            if hasattr(session, "send_client_content"):
                print("\nsend_client_content signature:")
                print(inspect.signature(session.send_client_content))
            
            # Try to get the signature of other potential methods for sending messages
            for method_name in ["send_message", "send_content", "send_text", "send"]:
                if hasattr(session, method_name):
                    print(f"\n{method_name} signature:")
                    print(inspect.signature(getattr(session, method_name)))
    except Exception as e:
        print(f"\nError connecting to Gemini Live API: {e}")

if __name__ == "__main__":
    asyncio.run(main())
