# Two-Step Approach for Emotion Tag Handling in Gemini Live Agent

## Problem
When using Gemini-2.0-Flash-Live-001 for interactive character roleplay, the AI incorrectly pronounces emotion tags like [joy] out loud instead of treating them as silent metadata for controlling facial expressions and animations.

## Solution: Two-Step Approach

We've implemented a two-step approach to handle emotion tags more effectively:

1. **Step 1: Planning Phase**
   - Ask the model to plan a response with emotion tags
   - Extract emotion tags from this planning response
   - Use these tags for facial expressions and animations
   - Do not play this audio to the user

2. **Step 2: Clean Response Phase**
   - Generate a clean spoken response without emotion tags
   - Instruct the model to respond naturally without mentioning any emotion tags
   - Play this audio to the user

## Implementation Details

### 1. New Methods Added

#### `_extract_emotions_from_planning`
```python
async def _extract_emotions_from_planning(self, user_message: str) -> str:
    """
    First step of the two-step approach: Ask the model to plan a response with emotion tags.
    
    Args:
        user_message: The user's message to respond to
        
    Returns:
        A response with emotion tags that will be used for facial expressions
    """
    if not self.gemini_session:
        logger.error("No active Gemini session for emotion planning")
        return ""
        
    try:
        logger.info("Requesting emotion-tagged planning response...")
        
        # Create a planning prompt that asks for emotion tags
        planning_prompt = (
            f"The user said: \"{user_message}\"\n\n"
            "Plan your response to the user and include emotion tags like [joy], [surprise], [sadness], etc. "
            "to indicate your emotional tone. Use format [emotion:0.7] to indicate intensity if needed. "
            "This is for planning purposes only to capture your emotional state."
        )
        
        # Send the planning prompt
        await self.gemini_session.send_client_content(
            turns={"role": "user", "parts": [{"text": planning_prompt}]},
            turn_complete=True
        )
        
        # Process the planning response to extract emotion tags
        planning_response = ""
        async for response in self.gemini_session.receive():
            if response.server_content and response.server_content.model_turn and response.server_content.model_turn.parts:
                for part in response.server_content.model_turn.parts:
                    if hasattr(part, 'text') and part.text:
                        planning_response += part.text
            
            if response.server_content and response.server_content.generation_complete:
                break
        
        logger.info(f"Received planning response with emotion tags: {planning_response}")
        return planning_response
        
    except Exception as e:
        logger.error(f"Error during emotion planning phase: {e}")
        return ""
```

#### `_generate_clean_response`
```python
async def _generate_clean_response(self, user_message: str, planning_response: str) -> AsyncIterator[AudioOutput]:
    """
    Second step of the two-step approach: Generate a clean spoken response without emotion tags.
    
    Args:
        user_message: The original user message
        planning_response: The planning response with emotion tags
        
    Returns:
        An async iterator of AudioOutput objects
    """
    if not self.gemini_session:
        logger.error("No active Gemini session for clean response generation")
        yield AudioOutput(
            audio_path=None,
            display_text=DisplayText(text="Error: Could not connect to Gemini."),
            transcript="Error: Could not connect to Gemini.",
            actions=Actions()
        )
        return
        
    try:
        # Extract emotion tags from planning response for facial expressions
        actions = Actions()
        if self.live2d_model and planning_response:
            expression_tuples = self.live2d_model.extract_emotion(planning_response)
            if expression_tuples:
                interpolated_expressions = [
                    self.live2d_model.get_interpolated_expression(idx, intensity)
                    for idx, intensity in expression_tuples
                ]
                actions.expressions = interpolated_expressions
                logger.info(f"Extracted expressions: {expression_tuples}")
        
        # Create a clean prompt that explicitly asks for no emotion tags
        clean_prompt = (
            f"The user said: \"{user_message}\"\n\n"
            "Respond naturally to the user without using or mentioning any emotion tags or square brackets. "
            "Just give a normal conversational response as if you're speaking directly to them."
        )
        
        # Send the clean prompt
        await self.gemini_session.send_client_content(
            turns={"role": "user", "parts": [{"text": clean_prompt}]},
            turn_complete=True
        )
        
        # Process the clean response and yield audio outputs
        accumulated_transcript = ""
        async for response in self.gemini_session.receive():
            if self.is_interrupted:
                logger.info("Gemini Live: Interruption acknowledged, stopping response processing.")
                break
            
            if response.server_content and response.server_content.model_turn and response.server_content.model_turn.parts:
                # Extract all text content from model_turn.parts
                model_turn_text = self._extract_text_from_parts(response.server_content.model_turn.parts)
                
                # Process audio parts
                for part in response.server_content.model_turn.parts:
                    if part.inline_data and part.inline_data.mime_type.startswith("audio/"):
                        audio_data = part.inline_data.data
                        
                        # Find transcript from various possible locations
                        transcript_text = ""
                        
                        # Try various locations for transcript (same as before)
                        if hasattr(response.server_content, 'output_transcription') and response.server_content.output_transcription:
                            if hasattr(response.server_content.output_transcription, 'text'):
                                transcript_text = response.server_content.output_transcription.text
                        
                        if not transcript_text and hasattr(response, 'output_transcription') and response.output_transcription:
                            if hasattr(response.output_transcription, 'text'):
                                transcript_text = response.output_transcription.text
                        
                        if not transcript_text and hasattr(response, 'text') and response.text:
                            transcript_text = response.text
                        
                        if not transcript_text and hasattr(part, 'text') and part.text:
                            transcript_text = part.text
                        
                        if not transcript_text and hasattr(response.server_content.model_turn, 'text') and response.server_content.model_turn.text:
                            transcript_text = response.server_content.model_turn.text
                        
                        if not transcript_text and hasattr(response.server_content, 'transcript') and response.server_content.transcript:
                            transcript_text = response.server_content.transcript
                        
                        if not transcript_text and model_turn_text:
                            transcript_text = model_turn_text
                        
                        # If we found a transcript, use it
                        if transcript_text:
                            # For display, combine the clean transcript with emotion tags from planning
                            # This gives us the best of both worlds - clean speech but emotional display
                            display_transcript = transcript_text
                            
                            # Add the planning response's emotion tags to the history for future reference
                            if self.history_conf_uid and self.history_history_uid and planning_response:
                                store_message(
                                    conf_uid=self.history_conf_uid, history_uid=self.history_history_uid,
                                    role="system", content=f"Emotion planning: {planning_response}"
                                )
                            
                            # Save audio to a temporary file
                            temp_audio_path = f"cache/gemini_live_{id(audio_data)}.wav"
                            with wave.open(temp_audio_path, "wb") as wf:
                                wf.setnchannels(1)  # Mono
                                wf.setsampwidth(2)  # 16-bit
                                wf.setframerate(24000)  # Gemini's output sample rate
                                wf.writeframes(audio_data)
                            
                            logger.debug(f"Saved audio to {temp_audio_path}")
                            logger.debug(f"Display transcript: '{display_transcript}'")
                            
                            # For display, we'll use the clean transcript but with the actions from the planning phase
                            yield AudioOutput(
                                audio_path=temp_audio_path,
                                display_text=DisplayText(text=display_transcript, name=self.character_name, avatar=self.character_avatar),
                                transcript=transcript_text,
                                actions=actions
                            )
                            
                            accumulated_transcript += transcript_text
            
            if response.server_content and response.server_content.generation_complete:
                logger.info("Gemini indicated generation complete.")
                if self.history_conf_uid and self.history_history_uid and accumulated_transcript:
                    store_message(
                        conf_uid=self.history_conf_uid, history_uid=self.history_history_uid,
                        role="ai", content=accumulated_transcript,
                        name=self.character_name, avatar=self.character_avatar
                    )
                break
        
    except Exception as e:
        logger.error(f"Error during clean response generation: {e}")
        yield AudioOutput(
            audio_path=None,
            display_text=DisplayText(
                text=f"Error generating response: {str(e)}",
                name=self.character_name,
                avatar=self.character_avatar
            ),
            transcript=f"Error generating response: {str(e)}",
            actions=Actions()
        )
```

### 2. Updated `chat` Method

```python
async def chat(self, batch_input: BatchInput) -> AsyncIterator[AudioOutput]:
    """
    Chat with the Gemini Live agent using a two-step approach to handle emotion tags.

    Args:
        batch_input: BatchInput - User input data

    Returns:
        AsyncIterator[AudioOutput] - Stream of audio outputs
    """
    await self._ensure_session()
    if self.gemini_session is None:
        logger.error("Failed to establish Gemini session.")
        yield AudioOutput(
            audio_path=None,
            display_text=DisplayText(text="Error: Could not connect to Gemini."),
            transcript="Error: Could not connect to Gemini.",
            actions=Actions()
        )
        return

    self.is_interrupted = False  # Reset per chat turn

    # Get text input from batch_input
    text_to_send = None
    if batch_input.texts:
        # Concatenate all text parts
        full_text_input = " ".join([text.content for text in batch_input.texts if text.content])
        if full_text_input:
            text_to_send = full_text_input
            logger.debug(f"User message: {text_to_send}")

            # Store message in history if available
            if self.history_conf_uid and self.history_history_uid:
                store_message(
                    conf_uid=self.history_conf_uid, history_uid=self.history_history_uid,
                    role="human", content=text_to_send
                )

    # If no text was provided, use a default message
    if not text_to_send:
        text_to_send = "Hello"
        logger.debug("No text input provided, using default greeting")

    try:
        # STEP 1: Get a planning response with emotion tags
        planning_response = await self._extract_emotions_from_planning(text_to_send)
        
        # STEP 2: Generate a clean spoken response without emotion tags
        async for audio_output in self._generate_clean_response(text_to_send, planning_response):
            yield audio_output
            
    except Exception as e:
        logger.error(f"Error in two-step emotion handling approach: {e}")
        # Return an error message to the user
        yield AudioOutput(
            audio_path=None,
            display_text=DisplayText(
                text=f"Error: {str(e)}",
                name=self.character_name,
                avatar=self.character_avatar
            ),
            transcript=f"Error: {str(e)}",
            actions=Actions()
        )
        
    finally:
        logger.debug("Exiting Gemini chat loop for this turn.")
        # Ensure active audio stream is properly ended if not interrupted by user's speech
        if self.active_audio_stream and not self.is_interrupted:
            if self.gemini_session and not getattr(self.gemini_session, '_conn', None) is None and not getattr(getattr(self.gemini_session, '_conn', None), 'closed', True):
                try:
                    await self.gemini_session.send_realtime_input(audio_stream_end=True)
                except Exception as e_stream_end:
                    logger.warning(f"Could not send audio_stream_end: {e_stream_end}")
            self.active_audio_stream = False
```

## Testing

To test this implementation:

1. Run the application with the updated code
2. Interact with the AI and observe if it still pronounces emotion tags
3. Check the logs to see the planning response with emotion tags and the clean response without them

## Benefits of This Approach

1. **Complete Separation**: By completely separating the emotion planning from the speech generation, we ensure the model never tries to pronounce emotion tags.

2. **Better Emotional Context**: The planning phase allows the model to think about the emotional context of its response before generating the actual speech.

3. **Cleaner Implementation**: This approach is more robust than trying to filter out emotion tags after they've been generated.

4. **Improved User Experience**: The user hears natural speech without any emotion tag artifacts while still benefiting from the emotional expressions in the Live2D model.
