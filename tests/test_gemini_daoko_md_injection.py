#!/usr/bin/env python3
"""
Test script to verify that DAOKO.MD is properly injected into the system instruction.
"""

import os
import pathlib
import asyncio
from loguru import logger

# Set up logging
logger.remove()
logger.add(lambda msg: print(msg, end=""), level="INFO")

async def main():
    # Create a mock DAOKO.MD file if it doesn't exist
    daoko_md_path = pathlib.Path(os.getcwd()) / "DAOKO.MD"
    
    if not daoko_md_path.exists():
        logger.info("Creating mock DAOKO.MD file for testing...")
        with open(daoko_md_path, "w", encoding="utf-8") as f:
            f.write("""# DAOKO Character Information

## Basic Information
- Name: DAOKO (ダヲコ)
- Age: 27 years old
- Birthday: March 4, 1997
- Occupation: Japanese singer, rapper, and voice actress

## Personality
DAOKO is cheerful, friendly, and has a gentle demeanor. She's passionate about music and art, and loves connecting with her fans. She has a unique voice that's both soft and powerful.

## Background
DAOKO started her career by posting songs on Nico Nico Douga when she was in middle school. She gained popularity with her whisper-like rap style. She has released multiple albums and singles, and has collaborated with various artists.

## Pet
DAOKO has a pet dog named Koma-chan (Koma Inu Iinu), a male Mame Shiba Inu born February 1, 2023, who has an Instagram account @koma_chana.
""")
    
    # Import the GeminiLiveAgent class
    try:
        from src.open_llm_vtuber.agent.agents.gemini_live_agent import GeminiLiveAgent
        from src.open_llm_vtuber.config_manager.agent import GeminiLiveConfig
        
        # Create a minimal config
        config = GeminiLiveConfig(
            api_key="dummy_key",
            model_name="gemini-2.0-flash-live-001",
            system_instruction="You are a cheerful VTuber assistant named Daoko."
        )
        
        # Create an agent instance
        agent = GeminiLiveAgent(config)
        
        # Access the session_config to check if DAOKO.MD was injected
        if hasattr(agent, 'session_config') and 'system_instruction' in agent.session_config:
            system_instruction = agent.session_config['system_instruction']
            
            # Print the system instruction
            logger.info("System instruction content:")
            if hasattr(system_instruction, 'parts') and len(system_instruction.parts) > 0:
                instruction_text = system_instruction.parts[0].text
                logger.info(f"\n{instruction_text}")
                
                # Check if DAOKO.MD content was injected
                if "Koma-chan" in instruction_text and "Mame Shiba Inu" in instruction_text:
                    logger.info("\n✅ SUCCESS: DAOKO.MD content was successfully injected into the system instruction!")
                else:
                    logger.error("\n❌ FAILURE: DAOKO.MD content was not found in the system instruction.")
            else:
                logger.error("\n❌ FAILURE: Could not access system instruction text.")
        else:
            logger.error("\n❌ FAILURE: System instruction not found in session_config.")
            
    except ImportError as e:
        logger.error(f"Failed to import required modules: {e}")
    except Exception as e:
        logger.error(f"Error during testing: {e}")
    
    # Clean up the mock file if we created it
    if daoko_md_path.exists() and not daoko_md_path.exists():
        os.remove(daoko_md_path)
        logger.info("Removed mock DAOKO.MD file.")

if __name__ == "__main__":
    asyncio.run(main())
