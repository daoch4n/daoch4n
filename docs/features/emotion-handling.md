# Emotion Handling in Gemini Live Agent

## Overview

The Gemini Live Agent supports emotion tags in the format `[emotion]` or `[emotion:intensity]` (e.g., `[joy:0.7]`, `[surprise:0.3]`). These tags are primarily used to control the facial expressions and animations of the Live2D model and should not be spoken aloud by the Text-to-Speech (TTS) system. This document outlines the strategies for handling these tags, including their removal from speech, their use for facial expressions with intensity, and their integration with body motions.

## Problem Statement

When using the Gemini Live API for interactive character roleplay, the model would sometimes incorrectly pronounce emotion tags out loud. This issue led to:

1.  **Unnatural Speech**: The character speaks emotion tags, breaking immersion (e.g., "I'm [joy] happy!" becomes "I'm joy happy!").
2.  **Confused User Experience**: Users hear technical metadata that should be invisible.
3.  **Reduced Expressiveness**: The character sounds robotic when pronouncing these tags.
4.  **Inconsistent Behavior**: Tags are sometimes pronounced, sometimes not.

Previous attempts to solve this, such as explicit system prompt instructions or post-processing, were inconsistent and unreliable.

## Solution Approaches

We have implemented two main approaches to prevent emotion tags from being pronounced, ensuring they are used solely for visual expressions:

### 1. Single Prompt Approach (Default)

This approach uses a single prompt that instructs the model to include emotion tags for facial expressions but explicitly not to pronounce them.

**Prompt Example:**
```
You can include emotion tags like [joy], [surprise], [sadness], etc. to indicate
your emotional tone. Use format [emotion:0.7] to indicate intensity if needed.
These tags will control your facial expressions but should NOT be spoken aloud.
Respond naturally as if the tags aren't there.
```

**Pros:**
- Lower latency (only one API call)
- Lower token usage
- Simpler implementation

**Cons:**
- May occasionally pronounce emotion tags if the model doesn't follow instructions perfectly.
- Less control over the separation of emotion planning and speech generation.

### 2. Dual Prompt System (Two-Step Approach)

This approach completely separates the emotion planning from the speech generation to ensure reliable prevention of emotion tag pronunciation.

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  User Message   │────▶│  Planning Phase  │────▶│ Response Phase  │
└─────────────────┘     └─────────────────┘     └─────────────────┘
       │                        │                        │
       ▼                        ▼                        ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ Emotion Tags    │     │ Clean Speech    │     │ Facial          │
│ Extracted       │     │ Without Tags    │     │ Expressions     │
└─────────────────┘     └─────────────────┘     └─────────────────┘
       │                        │
       ▼                        ▼
┌─────────────────┐     ┌─────────────────┐
│ Audio Output    │     │ Visual Output   │
│ to User         │     │ to User         │
└─────────────────┘     └─────────────────┘
```

**Step 1: Planning Phase**
The model is asked to plan a response with emotion tags. This response is *never* spoken to the user but is used to extract emotion tags for facial expressions and animations.

**Planning Prompt Example:**
```
Plan your response to the user and include emotion tags like [joy], [surprise], [sadness], etc.
to indicate your emotional tone. Use format [emotion:0.7] to indicate intensity if needed.
This is for planning purposes only to capture your emotional state.
```

**Step 2: Clean Response Phase**
The model is then asked to generate a clean spoken response *without* any emotion tags. This is the audio that is actually played to the user.

**Clean Response Prompt Example:**
```
Respond naturally to the user without using or mentioning any emotion tags or square brackets.
Just give a normal conversational response as if you're speaking directly to them.
```

**Pros:**
- More reliable prevention of emotion tag pronunciation.
- Better separation of emotion planning and speech generation.
- More consistent behavior.

**Cons:**
- Higher latency (requires two API calls).
- Higher token usage.
- More complex implementation.

## Configuration

You can choose between the single prompt approach (default) and the dual prompt system by setting the `use_dual_prompt_system` flag in your `conf.yaml` file:

```yaml
character_config:
  agent_config:
    conversation_agent_choice: gemini_live_agent
    agent_settings:
      gemini_live_agent:
        api_key: 'YOUR_GEMINI_API_KEY'
        model_name: 'gemini-2.0-flash-live-001'
        language_code: 'en-US'
        voice_name: 'Kore'
        system_instruction: "Your system instruction here"
        use_dual_prompt_system: false  # Set to true to use the dual prompt system
```

### System Instruction
The system instruction should include clear instructions about not pronouncing emotion tags. Here's an example:

```yaml
system_instruction: "You are a cheerful and helpful VTuber assistant named
  Daoko. Respond concisely. Express emotions using tags like [joy:0.7] or
  [surprise:0.3] in your text.

  CRITICAL INSTRUCTION: These emotion tags will control your facial expressions but must NEVER be spoken aloud.
  When generating speech audio, you MUST NOT vocalize any emotion tags like [joy], [joy:0.7], [surprise], etc.

  Example: If your response is '[joy:0.7] I'm happy to help you!', you should only speak 'I'm happy to help you!'
  without saying the '[joy:0.7]' part.

  Example: If your response is 'I'm [surprise] shocked by that news!', you should only speak 'I'm shocked by that news!'
  without saying the word 'surprise' or the brackets.

  Place emotion tags naturally within your text, but understand that they are ONLY metadata for the system
  and NEVER part of what you actually say. This is extremely important for proper functioning of the system."
```

## Technical Implementation Details

### Emotion Tag Removal
The `_remove_emotion_tags` method uses a comprehensive regex pattern to identify and remove emotion tags from the text before it's sent to the TTS system. A double cleaning pass is performed as an additional safety measure.

```python
import re

def _remove_emotion_tags(self, text: str) -> str:
    """
    Remove emotion tags from text.

    Args:
        text: Text with potential emotion tags

    Returns:
        Text with emotion tags removed
    """
    if not text:
        return ""

    # Regular expression to match both formats:
    # [emotion] and [emotion:intensity]
    emotion_pattern = r'\[\s*([a-zA-Z_]+)(?:\s*:\s*([0-9]*\.?[0-9]+))?\s*\]'

    # Remove all emotion tags from the text
    clean_text = re.sub(emotion_pattern, '', text)

    # Clean up any extra spaces
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()

    return clean_text
```

### Planning Phase (`_extract_emotions_from_planning`)
This asynchronous method sends a prompt to the Gemini model specifically asking for a response with emotion tags. It then extracts these tags from the model's planning response.

```python
import asyncio
import logging
from typing import AsyncIterator, List, Tuple, Dict, Any, Optional
import wave # Assuming wave is used for audio handling, as seen in original file

# Placeholder for external dependencies/classes for demonstration purposes
class GeminiSession:
    async def send_client_content(self, turns, turn_complete):
        pass
    async def receive(self):
        yield type('obj', (object,), {'server_content': type('obj', (object,), {'model_turn': type('obj', (object,), {'parts': []}), 'generation_complete': True})})()
class AudioOutput:
    def __init__(self, audio_path, display_text, transcript, actions):
        pass
class DisplayText:
    def __init__(self, text, name=None, avatar=None):
        pass
class Actions:
    def __init__(self, expressions=None, voice_modulation=None, gestures=None):
        self.expressions = expressions if expressions is not None else []
        self.voice_modulation = voice_modulation if voice_modulation is not None else {}
        self.gestures = gestures if gestures is not None else []
class Live2DModel:
    def extract_emotion(self, text):
        # Placeholder for emotion extraction logic
        # Example: parse [emotion:intensity] from text
        emotions = []
        matches = re.findall(r'\[([a-zA-Z_]+)(?::([0-9]*\.?[0-9]+))?\]', text)
        for emotion, intensity_str in matches:
            intensity = float(intensity_str) if intensity_str else 1.0
            emotions.append((emotion, intensity))
        return emotions
    def get_interpolated_expression(self, idx, intensity):
        # Placeholder for Live2D expression interpolation
        return {"expression_index": idx, "intensity": intensity}
class BatchInput:
    def __init__(self, texts):
        self.texts = texts
class TextPart:
    def __init__(self, content):
        self.content = content
def store_message(conf_uid, history_uid, role, content, name=None, avatar=None):
    pass

logger = logging.getLogger(__name__)

class GeminiLiveAgent:
    def __init__(self, gemini_session=None, live2d_model=None, character_name="Character", character_avatar="avatar.png", history_conf_uid=None, history_history_uid=None):
        self.gemini_session = gemini_session
        self.live2d_model = live2d_model
        self.character_name = character_name
        self.character_avatar = character_avatar
        self.history_conf_uid = history_conf_uid
        self.history_history_uid = history_history_uid
        self.is_interrupted = False
        self.active_audio_stream = False

    async def _ensure_session(self):
        # Placeholder for session establishment logic
        if not self.gemini_session:
            self.gemini_session = GeminiSession() # Mock session

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

### Clean Response Phase (`_generate_clean_response`)
This method generates the actual spoken response. It uses the emotion tags extracted from the planning phase to control facial expressions and sends a separate prompt to Gemini to generate a clean response without any tags.

```python
    def _extract_text_from_parts(self, parts):
        # Placeholder for text extraction from parts
        return " ".join([p.text for p in parts if hasattr(p, 'text')])

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
                        self.live2d_model.get_interpolated_expression(expr_index, intensity) # Changed from idx to expr_index to match live2d_model.py
                        for expr_index, intensity in expression_tuples
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
                        if hasattr(part, 'inline_data') and part.inline_data and hasattr(part.inline_data, 'mime_type') and part.inline_data.mime_type.startswith("audio/"):
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
                
                if response.server_content and hasattr(response.server_content, 'generation_complete') and response.server_content.generation_complete:
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

### Main Chat Method Integration (`chat`)
The main `chat` method orchestrates the two-step process, calling `_extract_emotions_from_planning` first, then `_generate_clean_response` to produce the final audio output with synchronized facial expressions.

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
                        # Placeholder for send_realtime_input
                        # await self.gemini_session.send_realtime_input(audio_stream_end=True)
                        pass
                    except Exception as e_stream_end:
                        logger.warning(f"Could not send audio_stream_end: {e_stream_end}")
                self.active_audio_stream = False
```

## Performance Considerations

1.  **Latency Impact**: The dual prompt system requires two separate calls to the Gemini API, which increases response latency (typically 300-800ms). This tradeoff is accepted for improved speech quality.
2.  **Token Usage**: The dual prompt approach approximately doubles the token usage per interaction (~50-100 tokens per phase per user message).
3.  **Memory Usage**: Minimal additional memory impact (~10-20KB per interaction) as planning responses are temporary.

## Detailed Feature Implementations

This section provides more in-depth details on specific emotion-related features, including how emotion intensity is handled and how motions are integrated.

### Emotion Intensity for Live2D Models

The system is designed to handle emotion intensity values (e.g., `[joy:0.7]`) to allow for nuanced facial expressions.

**Backend Emotion Extraction and Transmission:**
The backend correctly extracts emotion tags and their intensity values from text using regex and packages them for transmission to the frontend.
The `extract_emotion` method in `src/open_llm_vtuber/live2d_model.py` and `get_interpolated_expression` method correctly process and format these values.

```python
# From src/open_llm_vtuber/live2d_model.py
def extract_emotion(self, str_to_check: str) -> list:
    # Regular expression to match both formats:
    # [emotion] and [emotion:intensity]
    emotion_pattern = r'\[([\w]+)(?::([0-9]*\.?[0-9]+))?\]'
    
    # Find all emotion tags in the text
    matches = re.finditer(emotion_pattern, str_to_check)
    
    expression_list = [] # Ensure this list is initialized
    for match in matches:
        emotion = match.group(1)
        intensity_str = match.group(2)
        
        # Check if the emotion exists in our emotion map
        # Placeholder for self.emo_map logic, assuming it maps emotion names to indices
        if emotion in getattr(self, 'emo_map', {}): # Added getattr for robustness
            # Get the expression index
            expression_index = self.emo_map[emotion]
            
            # Parse intensity value, default to 1.0 if not specified
            intensity = 1.0
            if intensity_str:
                try:
                    intensity = float(intensity_str)
                    # Clamp intensity to valid range [0.0, 1.0]
                    intensity = max(0.0, min(1.0, intensity))
                except ValueError:
                    intensity = 1.0
                    
            expression_list.append((expression_index, intensity))
    return expression_list # Return the list

def get_interpolated_expression(self, expression_index: int, intensity: float) -> dict:
    # Ensure intensity is within valid range
    intensity = max(0.0, min(1.0, intensity))
    
    # Create a dictionary with the expression index and intensity
    interpolated_expression = {
        "expression_index": expression_index,
        "intensity": intensity
    }
    
    return interpolated_expression
```

**Frontend Application (Current Status):**
In `frontend-src/src/renderer/src/hooks/utils/use-audio-task.ts`, the frontend receives the expression data. However, the `model.expression` and `setExpression` methods in `live2d.tsx` currently only process a name/index and do not inherently handle the intensity value for interpolating expressions.

### Emotion-Motion Integration

The Live2D model animation system has been enhanced to automatically change both facial expressions and body poses based on emotion tags in the AI's responses. This creates a more dynamic and expressive character that reacts naturally to the emotional content of the conversation.

The system is intensity-aware, meaning that body motions are only triggered when the emotion intensity is greater than 0.5. This allows for more nuanced reactions where mild emotions (intensity ≤ 0.5) only change facial expressions, while stronger emotions (intensity > 0.5) also trigger body motions.

**Emotion-Motion Mapping:**
The backend maps emotions to appropriate motions using the `EmotionMotionMapper` class in `src/open_llm_vtuber/emotion_motion_map.py`. The default mapping is:

```python
DEFAULT_EMOTION_MOTION_MAP = {
    "joy": ["tap_body"],       # Happy/excited motions
    "sadness": ["shake"],      # Sad/downcast motions
    "anger": ["shake"],        # Angry/frustrated motions
    "disgust": ["shake"],      # Disgusted motions
    "fear": ["pinch_in"],      # Fearful/anxious motions
    "surprise": ["flick_head"], # Surprised motions
    "smirk": ["tap_body"],     # Mischievous/playful motions
    "neutral": ["idle"],       # Default idle motions
}
```

**Backend Processing:**
The `actions_extractor` transformer in `src/open_llm_vtuber/agent/transformers.py` extracts emotions from the text and maps them to appropriate motions, but only when the emotion intensity is greater than 0.5.

```python
# Example of backend logic for motion extraction (from transformers.py)
# Map emotions to motions (using the same emotion tags)
motions = []
# Assuming 'sentence' is a text object and 'live2d_model' and 'emotion_mapper' are available
# text = sentence.text.lower()
# emotion_pattern = r'\[([\w]+)(?::([0-9]*\.?[0-9]+))?\]'
# matches = re.finditer(emotion_pattern, text)

# for match in matches:
#     emotion = match.group(1)
#     intensity_str = match.group(2)

#     # Parse intensity value, default to 1.0 if not specified
#     intensity = 1.0
#     if intensity_str:
#         try:
#             intensity = float(intensity_str)
#             # Clamp intensity to valid range [0.0, 1.0]
#             intensity = max(0.0, min(1.0, intensity))
#         except ValueError:
#             # If conversion fails, use default intensity
#             intensity = 1.0

#     # Only add motion if intensity is greater than 0.5
#     if intensity > 0.5 and emotion in live2d_model.emo_map: # Assuming live2d_model.emo_map has emotion names
#         # Get corresponding motion for this emotion
#         motion = emotion_mapper.get_motion_for_emotion(emotion) # Assuming emotion_mapper is available
#         if motion and motion not in motions:  # Avoid duplicates
#             motions.append(motion)
#             logger.debug(f"Adding motion {motion} for emotion {emotion} with intensity {intensity}")

# # Set motions if any were found
# if motions:
#     actions.motions = motions
#     logger.debug(f"Mapped emotions to motions: {motions}")
```

**Frontend Integration:**
The frontend receives the motion information through the WebSocket and applies it to the Live2D model.

```typescript
// In use-audio-task.ts
if (expressions?.[0] !== undefined) { // Expressions are applied first
  model.expression(expressions[0]); // This still needs to be updated to handle intensity

  // Handle motion if available
  if (motions?.[0] !== undefined) {
    const motionName = motions[0];
    console.log(`Starting motion: ${motionName}`);

    try {
      // Use the motion method with appropriate priority
      // The motion method is defined in the Live2DModel class from pixi-live2d-display
      // It takes a motion group name and plays a random motion from that group
      const priority = 2; // Normal priority (same as MotionPriority.NORMAL)
      model.motion(motionName, undefined, priority);
      console.log(`Motion started: ${motionName}`);
    } catch (error) {
      console.warn(`Failed to play motion ${motionName}:`, error);
    }
  }
}
```

**Available Motions:**
The Live2D model (shizuku) has the following motion groups:

- `idle`: Default idle animations
- `tap_body`: Happy/excited animations
- `pinch_in`: Fearful/anxious animations
- `pinch_out`: Surprised animations
- `shake`: Sad/angry animations
- `flick_head`: Surprised animations

Each motion group contains multiple animation files (e.g., `idle_00.mtn`, `idle_01.mtn`, `idle_02.mtn`).

**Usage:**
To trigger emotions and motions in the AI's responses, include emotion tags in the text:

```
I'm so happy to see you! [joy:0.8]       # Strong joy - changes expression and triggers motion
I'm a bit happy today. [joy:0.3]         # Mild joy - only changes expression, no motion
That's really scary! [fear:0.9]          # Strong fear - changes expression and triggers motion
That's somewhat concerning. [fear:0.4]   # Mild fear - only changes expression, no motion
I'm not sure about that... [neutral]     # Default intensity (1.0) - changes expression and triggers motion
```

The system will automatically:
1. Extract the emotion tags and their intensity values
2. Set the appropriate facial expression (for all emotions regardless of intensity)
3. Play the corresponding body motion (only for emotions with intensity > 0.5)

**Customization:**
To customize the emotion-motion mapping, modify the `DEFAULT_EMOTION_MOTION_MAP` in `src/open_llm_vtuber/emotion_motion_map.py`.

## Advanced Emotion Integration & Future Improvements

### Contextual Emotion Prompting
Enhance the planning prompt with character-specific emotional context to achieve more consistent and nuanced emotional responses aligned with character personality.

```python
planning_prompt = (
    f"The user said: \"{user_message}\"\n\n"
    f"As {self.character_name}, who tends to be {self.character_personality}, "
    f"plan your response with appropriate emotion tags like [joy], [surprise], etc. "
    f"Consider your character's emotional baseline and how you would naturally react. "
    f"Use format [emotion:0.7] to indicate intensity if needed."
)
```

**Technical Implementation**:
- Add character personality traits to the configuration
- Dynamically generate personality-aware planning prompts
- Track emotional history to maintain consistency across interactions

**Expected Benefits**:
- More consistent emotional responses aligned with character personality
- Reduced "emotional whiplash" between interactions
- More nuanced emotional expressions

### Frontend Expression Intensity Application (Recommended Improvement)

To fully implement intensity-based facial expressions, the frontend's expression method needs to be modified to interpolate between expressions based on the provided intensity.

**Proposed Changes for `live2d.tsx`:**
```typescript
// In live2d.tsx
expression: (exprData?: any) => {
  if (typeof exprData === 'object' && exprData.expression_index !== undefined && exprData.intensity !== undefined) {
    // Handle expression with intensity
    const expressionIndex = exprData.expression_index;
    const intensity = exprData.intensity;
    
    // Get the neutral expression parameters (assuming index 0 is neutral)
    const neutralExpression = modelRef.current?.internalModel.motionManager.expressionManager?.definitions[0];
    const neutralParams = neutralExpression ? neutralExpression.parameters : [];
    
    // Get the target expression parameters
    const targetExpression = modelRef.current?.internalModel.motionManager.expressionManager?.definitions[expressionIndex];
    const targetParams = targetExpression ? targetExpression.parameters : [];
    
    // Interpolate between neutral and target based on intensity
    const interpolatedParams = interpolateParameters(neutralParams, targetParams, intensity);
    
    // Apply the interpolated parameters
    applyParameters(modelRef.current, interpolatedParams);
  } else {
    // Fall back to the original behavior for backward compatibility
    modelRef.current?.expression(exprData);
  }
}

// Helper function to interpolate parameters
function interpolateParameters(neutralParams, targetParams, intensity) {
  // Create a map for neutral parameters for quicker lookup
  const neutralMap = new Map(neutralParams.map(p => [p.id, p]));

  return targetParams.map(targetParam => {
    const neutralParam = neutralMap.get(targetParam.id);
    const neutralValue = neutralParam ? neutralParam.val : 0.0; // Assume 0.0 if not found in neutral

    // Linear interpolation between neutral and target values
    const interpolatedValue = neutralValue + (targetParam.val - neutralValue) * intensity; // Use .val as in Live2D expression JSON
    
    return {
      ...targetParam,
      val: interpolatedValue // Update 'val' property
    };
  });
}

// Helper function to apply interpolated parameters
function applyParameters(model, params) {
  params.forEach(param => {
    model.internalModel.coreModel.setParameterValueById(param.id, param.val); // Use .val
  });
}
```
*Note: The Live2D expression JSON uses `val` for value, not `value`. The interpolation and application functions are adjusted accordingly.*

**Expected Benefits**:
- Proper application of emotion intensity for nuanced facial expressions.
- More natural and dynamic visual responses from the Live2D model.

### Emotion Tag Vocabulary Expansion
Expand the emotion tag vocabulary and implement mapping to supported expressions, allowing for richer emotional expression without modifying the Live2D model directly.

```python
# Emotion mapping dictionary
EMOTION_MAPPING = {
    # Basic emotions directly supported by Live2D
    "joy": "joy",
    "sadness": "sadness",
    "anger": "anger",
    "surprise": "surprise",
    
    # Extended emotions mapped to basic emotions
    "excitement": "joy",
    "happiness": "joy",
    "delight": "joy",
    "amusement": "joy",
    "contentment": "joy",
    
    "melancholy": "sadness",
    "disappointment": "sadness",
    "grief": "sadness",
    "regret": "sadness",
    
    "annoyance": "anger",
    "frustration": "anger",
    "irritation": "anger",
    
    "amazement": "surprise",
    "shock": "surprise",
    "astonishment": "surprise",
    
    # Complex emotions as combinations
    "pride": {"joy": 0.7, "surprise": 0.3},
    "embarrassment": {"sadness": 0.3, "surprise": 0.7},
    "confusion": {"surprise": 0.6, "sadness": 0.4},
    "nervousness": {"surprise": 0.5, "sadness": 0.5},
}

def map_emotion(emotion_tag: str) -> List[Tuple[str, float]]:
    """Map extended emotion vocabulary to supported Live2D expressions."""
    emotion_name = emotion_tag.lower()
    if emotion_name in EMOTION_MAPPING:
        mapping = EMOTION_MAPPING[emotion_name]
        if isinstance(mapping, str):
            return [(mapping, 1.0)]
        elif isinstance(mapping, dict):
            return [(emotion, intensity) for emotion, intensity in mapping.items()]
    return [("neutral", 1.0)]  # Default fallback
```

**Technical Implementation**:
- Create a comprehensive emotion mapping dictionary
- Implement emotion mapping function in the emotion extraction process
- Add configuration option to enable/disable extended emotion vocabulary

**Expected Benefits**:
- Richer emotional expression without modifying the Live2D model
- More natural language in planning responses
- Better mapping between linguistic emotions and visual expressions

### Parallel Processing
Implement parallel processing for short responses to reduce latency (potentially 200-400ms improvement) by running planning and clean response phases concurrently.

```python
# This is a conceptual example, actual implementation would be within the agent's chat method
async def chat_with_parallel_processing(self, batch_input: BatchInput) -> AsyncIterator[AudioOutput]:
    """Chat with parallel processing of planning and clean response for short messages."""
    text_to_send = self._extract_text_from_batch(batch_input) # Assuming this method exists
    
    # For short messages, run both phases in parallel
    if len(text_to_send) < 100:  # Character threshold for parallel processing
        # Create tasks for both phases
        planning_task = asyncio.create_task(self._extract_emotions_from_planning(text_to_send))
        
        # Start clean response generation immediately
        clean_response_generator = self._generate_clean_response_without_waiting(text_to_send) # Assuming this method exists
        
        # Process clean responses while waiting for planning to complete
        planning_result = None
        buffer = []
        
        async for response in clean_response_generator:
            if planning_result is None and planning_task.done():
                planning_result = planning_task.result()
                # Apply emotions to buffered and future responses
                for buffered_response in buffer:
                    buffered_response.actions = self._extract_actions_from_planning(planning_result) # Assuming this method exists
                    yield buffered_response
                buffer = []
            
            if planning_result is not None:
                # Apply emotions from planning
                response.actions = self._extract_actions_from_planning(planning_result)
                yield response
            else:
                # Buffer response until planning is complete
                buffer.append(response)
        
        # Handle any remaining buffered responses
        if buffer and planning_task.done():
            planning_result = planning_task.result()
            for buffered_response in buffer:
                buffered_response.actions = self._extract_actions_from_planning(planning_result)
                yield buffered_response
    else:
        # For longer messages, use the sequential approach
        planning_response = await self._extract_emotions_from_planning(text_to_send)
        async for response in self._generate_clean_response(text_to_send, planning_response):
            yield response
```

**Technical Implementation**:
- Implement parallel processing for short messages
- Add buffering mechanism to hold responses until planning is complete
- Add configuration option to set the character threshold for parallel processing

**Expected Benefits**:
- Reduced latency for short interactions (potentially 200-400ms improvement)
- Smoother user experience for quick exchanges
- Graceful fallback to sequential processing for complex interactions

### Caching Mechanism
Implement a caching mechanism for common interactions to significantly reduce latency (potentially 500-800ms improvement) and API costs for repetitive interactions.

```python
class EmotionResponseCache:
    """Cache for emotion responses to reduce latency for common interactions."""
    
    def __init__(self, max_size=100):
        self.cache = {}
        self.max_size = max_size
        self.hits = 0
        self.misses = 0
    
    def get(self, user_message: str) -> Optional[Tuple[str, List[Tuple[str, float]]]]:
        """Get cached planning response and expressions for a user message."""
        # Normalize message for better cache hits
        normalized_message = self._normalize_message(user_message)
        
        if normalized_message in self.cache:
            self.hits += 1
            return self.cache[normalized_message]
        
        self.misses += 1
        return None
    
    def put(self, user_message: str, planning_response: str, expressions: List[Tuple[str, float]]):
        """Cache planning response and expressions for a user message."""
        # Normalize message for better cache hits
        normalized_message = self._normalize_message(user_message)
        
        # Implement LRU eviction if cache is full
        if len(self.cache) >= self.max_size:
            # Remove oldest entry
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]
        
        self.cache[normalized_message] = (planning_response, expressions)
    
    def _normalize_message(self, message: str) -> str:
        """Normalize message for better cache hits."""
        # Convert to lowercase
        normalized = message.lower()
        # Remove punctuation
        normalized = re.sub(r'[^\w\s]', '', normalized)
        # Remove extra whitespace
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        return normalized
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "hits": self.hits,
            "misses": self.misses,
            "hit_ratio": self.hits / (self.hits + self.misses) if (self.hits + self.misses) > 0 else 0
        }
```

**Technical Implementation**:
- Implement a caching mechanism for planning responses and expressions
- Add cache hit/miss metrics for monitoring
- Implement intelligent message normalization for better cache hits
- Add configuration options for cache size and TTL

**Expected Benefits**:
- Significantly reduced latency for common interactions (potentially 500-800ms improvement)
- Reduced API costs for repetitive interactions
- Consistent emotional responses for similar inputs

### Emotion Transition Smoothing
Implement emotion transition smoothing for more natural and fluid expression changes, reducing the "uncanny valley" effect.

```python
class EmotionTransitionManager:
    """Manages smooth transitions between emotional states."""
    
    def __init__(self, transition_speed=0.2):
        self.current_emotions = {}  # Current emotional state
        self.target_emotions = {}   # Target emotional state
        self.transition_speed = transition_speed  # How quickly to transition (0-1)
    
    def set_target_emotions(self, emotions: List[Tuple[str, float]]):
        """Set the target emotional state."""
        self.target_emotions = {emotion: intensity for emotion, intensity in emotions}
    
    def update(self) -> List[Tuple[str, float]]:
        """Update current emotions based on transition speed and return current state."""
        # For each target emotion
        for emotion, target_intensity in self.target_emotions.items():
            # Get current intensity or default to 0
            current_intensity = self.current_emotions.get(emotion, 0.0)
            
            # Calculate new intensity with smoothing
            if abs(current_intensity - target_intensity) < self.transition_speed:
                # If close enough, snap to target
                new_intensity = target_intensity
            else:
                # Otherwise, move toward target
                direction = 1 if target_intensity > current_intensity else -1
                new_intensity = current_intensity + (direction * self.transition_speed)
            
            # Update current emotion
            if new_intensity > 0:
                self.current_emotions[emotion] = new_intensity
            elif emotion in self.current_emotions:
                del self.current_emotions[emotion]
        
        # Remove emotions that are no longer in target
        for emotion in list(self.current_emotions.keys()):
            if emotion not in self.target_emotions:
                current_intensity = self.current_emotions[emotion]
                new_intensity = max(0, current_intensity - self.transition_speed)
                
                if new_intensity > 0:
                    self.current_emotions[emotion] = new_intensity
                else:
                    del self.current_emotions[emotion]
        
        # Return current emotional state as list of tuples
        return [(emotion, intensity) for emotion, intensity in self.current_emotions.items()]
```

**Technical Implementation**:
- Implement emotion transition manager
- Integrate with Live2D model animation system
- Add configuration options for transition speed and smoothing algorithm
- Update animation loop to call transition manager at appropriate intervals

**Expected Benefits**:
- More natural and fluid emotional expressions
- Reduced "uncanny valley" effect from abrupt expression changes
- More lifelike character behavior

### Multimodal Emotion Expression
Extend emotion expression beyond facial expressions to include voice modulation (pitch, speed, energy, breathiness) and gestures/body language, leading to more holistic and believable character behavior.

```python
class MultimodalEmotionExpression:
    """Expresses emotions through multiple modalities."""
    
    def __init__(self, live2d_model, voice_modifier=None, gesture_system=None):
        self.live2d_model = live2d_model
        self.voice_modifier = voice_modifier
        self.gesture_system = gesture_system
    
    def express_emotions(self, emotions: List[Tuple[str, float]]) -> Actions:
        """Express emotions through all available modalities."""
        actions = Actions()
        
        # 1. Facial expressions
        if self.live2d_model:
            interpolated_expressions = [
                self.live2d_model.get_interpolated_expression(idx, intensity)
                for idx, intensity in emotions
            ]
            actions.expressions = interpolated_expressions
        
        # 2. Voice modulation
        if self.voice_modifier:
            voice_params = self._emotions_to_voice_params(emotions)
            actions.voice_modulation = voice_params
        
        # 3. Gestures and body language
        if self.gesture_system:
            gestures = self._emotions_to_gestures(emotions)
            actions.gestures = gestures
        
        return actions
    
    def _emotions_to_voice_params(self, emotions: List[Tuple[str, float]]) -> Dict[str, float]:
        """Convert emotions to voice modulation parameters."""
        voice_params = {
            "pitch": 0.0,      # -1.0 to 1.0
            "speed": 0.0,      # -1.0 to 1.0
            "energy": 0.0,     # 0.0 to 1.0
            "breathiness": 0.0  # 0.0 to 1.0
        }
        
        for emotion, intensity in emotions:
            if emotion == "joy":
                voice_params["pitch"] += 0.2 * intensity
                voice_params["speed"] += 0.1 * intensity
                voice_params["energy"] += 0.3 * intensity
            elif emotion == "sadness":
                voice_params["pitch"] -= 0.2 * intensity
                voice_params["speed"] -= 0.2 * intensity
                voice_params["breathiness"] += 0.3 * intensity
            elif emotion == "anger":
                voice_params["pitch"] += 0.1 * intensity
                voice_params["speed"] += 0.2 * intensity
                voice_params["energy"] += 0.5 * intensity
            elif emotion == "surprise":
                voice_params["pitch"] += 0.3 * intensity
                voice_params["speed"] += 0.1 * intensity
                voice_params["energy"] += 0.2 * intensity
        
        # Clamp values to valid ranges
        for param in voice_params:
            if param == "pitch" or param == "speed":
                voice_params[param] = max(-1.0, min(1.0, voice_params[param]))
            else:
                voice_params[param] = max(0.0, min(1.0, voice_params[param]))
        
        return voice_params
    
    def _emotions_to_gestures(self, emotions: List[Tuple[str, float]]) -> List[str]:
        """Convert emotions to gesture triggers."""
        gestures = []
        
        # Determine dominant emotion
        if emotions:
            dominant_emotion = max(emotions, key=lambda x: x[1])
            emotion, intensity = dominant_emotion
            
            # Only trigger gestures for significant emotions
            if intensity > 0.6:
                if emotion == "joy":
                    gestures.append("nod_happy")
                    if intensity > 0.8:
                        gestures.append("clap_hands")
                elif emotion == "sadness":
                    gestures.append("head_down")
                    if intensity > 0.8:
                        gestures.append("wipe_tear")
                elif emotion == "anger":
                    gestures.append("head_shake")
                    if intensity > 0.8:
                        gestures.append("cross_arms")
                elif emotion == "surprise":
                    gestures.append("step_back")
                    if intensity > 0.8:
                        gestures.append("hands_up")
        
        return gestures
```

**Technical Implementation**:
- Extend the Actions class to support voice modulation and gestures
- Implement voice parameter mapping for different emotions
- Implement gesture mapping for different emotions
- Integrate with TTS system for voice modulation
- Integrate with Live2D motion system for gestures

**Expected Benefits**:
- More holistic and natural emotional expression
- Increased character believability and engagement
- Richer user experience through multimodal interaction

### Future Improvements from Motion Doc
- Add more diverse motions for each emotion
- Implement random selection from multiple motion options for each emotion
- Add intensity-based motion selection (similar to expression intensity)
- Support for custom emotion-motion mappings through configuration files

## TTS System Interaction with Emotion Tags

Beyond preventing the LLM from vocalizing emotion tags, it's important to understand how these tags might be interpreted or used by the Text-to-Speech (TTS) system itself. The behavior can vary significantly depending on the TTS engine and integration method.

### Kokoro TTS Microservice

The Kokoro TTS microservice has specific logic to handle emotion tags:
-   **Tag Parsing:** It parses the first `[emotion:intensity]` tag from the input text.
-   **Speed and Volume Adjustment:** The primary effect is on speech speed and volume. The service uses a configurable `emotion_mapping` (e.g., `joy: {"speed": 1.2, "volume": 1.1}`) to determine multipliers based on the detected emotion. The intensity value scales this effect, with a threshold of 0.3 below which no change occurs. These values can be overridden by explicit `speed` and `volume` parameters in the `/tts` API request.
-   **Tag Removal:** All emotion tags are removed from the text before it is sent to the underlying Kokoro engine for synthesis.
-   **No Direct Style/Pitch Change:** The microservice currently does not use emotion tags to change the voice style or pitch directly.

### Other TTS Systems

For other TTS engines, their handling of embedded emotion tags will vary:
- Some may ignore them completely.
- Some may have their own syntax for style or prosody control (e.g., SSML).
- Some might be designed to interpret `[emotion:intensity]` tags if explicitly documented for that engine.

The primary goal of the emotion tag removal strategies described in this document is to prevent the *Language Model (LLM)* from speaking the tags, ensuring the TTS system receives text that is either clean or contains tags it is specifically designed to process.

## Troubleshooting

If you still experience issues with emotion tags being pronounced or other emotion-related problems:

1.  **Check the System Instruction**: Ensure the system instruction clearly instructs the model not to vocalize emotion tags.
2.  **Verify the Emotion Tag Pattern**: The regex pattern used for removal should match all variations of emotion tags used in your system.
3.  **Enable Debug Logging**: Set the logger level to DEBUG to see the original and cleaned transcripts, as well as planning responses.
4.  **Test with Simple Examples**: Test with simple examples containing emotion tags to verify the cleaning process works correctly.
5.  **Review Performance Metrics**: Monitor latency and token usage, especially if using the dual prompt system, to identify bottlenecks.
6.  **Check TTS Service Logs**: If using the Kokoro TTS microservice, check its logs for any errors related to emotion tag processing or speech generation.

## References

-   [Gemini Live API Usage Guide](docs/integrations/gemini-live-api-usage.md)
-   [Live2D Emotion-Motion Integration Plan](docs/plans/live2d-emotion-motion-integration-plan.md)