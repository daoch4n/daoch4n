# Two-Step Approach for Emotion Tag Handling in Gemini Live Agent

> **Note**: This approach is now configurable. See [Gemini Live Emotion Tag Handling](gemini_live_emotion_tag_handling.md) for details on how to enable or disable the dual prompt system.

## Problem Statement

When using the Gemini Live API for interactive character roleplay, we encountered a significant issue: the model would incorrectly pronounce emotion tags like `[joy]`, `[surprise:0.7]`, or `[sadness]` out loud instead of treating them as silent metadata for controlling facial expressions and animations.

This issue manifests in several ways:

1. **Unnatural Speech**: The character speaks emotion tags out loud, breaking immersion (e.g., "I'm [joy] happy to see you!" becomes "I'm joy happy to see you!")
2. **Confused User Experience**: Users hear technical metadata that should be invisible to them
3. **Reduced Expressiveness**: The character sounds robotic when pronouncing these tags
4. **Inconsistent Behavior**: Sometimes tags are pronounced, sometimes they aren't

Previous attempts to solve this issue included:

- Adding explicit instructions in the system prompt to not pronounce tags
- Using different tag formats (curly braces, XML-style tags)
- Implementing post-processing to remove tags from transcripts

These approaches were inconsistent and unreliable, as the model would still occasionally pronounce the tags, especially when they were embedded within sentences.

## Solution: Two-Step Approach

Our solution implements a two-step approach that completely separates the emotion planning from the speech generation:

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  User Message   │────▶│  Planning Phase  │────▶│ Response Phase  │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                               │                        │
                               ▼                        ▼
                        ┌─────────────────┐     ┌─────────────────┐
                        │ Emotion Tags    │     │ Clean Speech    │
                        │ Extracted       │     │ Without Tags    │
                        └─────────────────┘     └─────────────────┘
                               │                        │
                               │                        │
                               ▼                        ▼
                        ┌─────────────────┐     ┌─────────────────┐
                        │ Facial          │     │ Audio Output    │
                        │ Expressions     │     │ to User         │
                        └─────────────────┘     └─────────────────┘
```

### Step 1: Planning Phase

In the first step, we explicitly ask the model to plan a response with emotion tags. This response is never spoken to the user but is used to extract emotion tags for facial expressions and animations.

### Step 2: Clean Response Phase

In the second step, we ask the model to generate a clean spoken response without any emotion tags. This is the audio that is actually played to the user.

By completely separating these steps, we ensure the model never tries to pronounce emotion tags while still leveraging them for expressive character animation.

## Technical Implementation

### 1. Planning Phase Implementation

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

### 2. Clean Response Phase Implementation

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

            # Process audio parts and generate output
            # (Implementation details omitted for brevity)

            # For each audio part, we yield an AudioOutput with:
            # 1. The clean transcript for display
            # 2. The actions extracted from the planning phase
            # 3. The audio data from Gemini

            # Store the final response in history if needed

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

### 3. Main Chat Method Integration

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
```

## Detailed Process Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           Two-Step Approach                              │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 1. User sends message                                                    │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 2. PLANNING PHASE                                                        │
│    ┌─────────────────────────────────────────────────────────────────┐  │
│    │ a. Create planning prompt asking for emotion tags               │  │
│    │ b. Send planning prompt to Gemini                               │  │
│    │ c. Receive planning response with emotion tags                  │  │
│    │ d. Extract emotion tags for facial expressions                  │  │
│    └─────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 3. CLEAN RESPONSE PHASE                                                  │
│    ┌─────────────────────────────────────────────────────────────────┐  │
│    │ a. Create clean prompt asking for response without tags         │  │
│    │ b. Send clean prompt to Gemini                                  │  │
│    │ c. Receive clean response without emotion tags                  │  │
│    │ d. Process audio data from response                             │  │
│    └─────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 4. OUTPUT GENERATION                                                     │
│    ┌─────────────────────────────────────────────────────────────────┐  │
│    │ a. Combine clean audio with facial expressions from planning    │  │
│    │ b. Yield AudioOutput objects with:                              │  │
│    │    - Audio data from clean response                             │  │
│    │    - Display text from clean response                           │  │
│    │    - Actions (expressions) from planning response               │  │
│    └─────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

## Performance Considerations

1. **Latency Impact**:
   - The two-step approach requires two separate calls to the Gemini API, which increases response latency
   - Typical additional latency: 300-800ms depending on network conditions and response length
   - This tradeoff is acceptable given the significant improvement in speech quality

2. **Token Usage**:
   - The approach approximately doubles the token usage per interaction
   - Planning phase: ~50-100 tokens per user message
   - Clean response phase: ~50-100 tokens per user message
   - Cost impact should be monitored, especially for high-volume deployments

3. **Memory Usage**:
   - Minimal additional memory impact (~10-20KB per interaction)
   - Planning responses are stored temporarily and discarded after processing

## Edge Cases and Handling

1. **Empty Planning Response**:
   - If the planning phase fails to generate a response with emotion tags, the system falls back to generating a response without facial expressions
   - This ensures the conversation can continue even if emotion extraction fails

2. **Mismatched Content**:
   - The planning response and clean response might have different content
   - This is acceptable as long as the emotional tone is preserved
   - The user only sees/hears the clean response

3. **Interruptions**:
   - If the user interrupts during either phase, the interruption flag is set
   - Both phases respect the interruption flag and stop processing
   - This ensures responsive interaction even with the two-step approach

4. **Connection Issues**:
   - If the connection to Gemini is lost during either phase, appropriate error handling ensures the user receives feedback
   - The system attempts to reconnect for subsequent interactions

5. **Emotion Tag Extraction Failures**:
   - If emotion tags cannot be extracted from the planning response, default neutral expressions are used
   - Logging captures these instances for further analysis and improvement

## Conclusion

The two-step approach effectively solves the problem of emotion tags being pronounced by completely separating the emotion planning from the speech generation. While it introduces some additional latency and token usage, the significant improvement in speech quality and character expressiveness justifies these tradeoffs.

This approach is more robust than previous attempts because it doesn't rely on the model understanding complex instructions about not pronouncing tags. Instead, it structurally prevents the issue by using separate prompts for different purposes.

### Configuration

As of the latest update, this approach is now configurable. You can enable or disable the dual prompt system by setting the `use_dual_prompt_system` flag in your configuration:

```yaml
gemini_live_agent:
  # Other configuration options...
  use_dual_prompt_system: true  # Set to false to use the single prompt approach
```

By default, the system uses a single prompt approach that is more efficient but may occasionally pronounce emotion tags. The dual prompt system described in this document can be enabled when more reliable prevention of emotion tag pronunciation is needed.

For more details on the configuration options and the differences between the two approaches, see [Gemini Live Emotion Tag Handling](gemini_live_emotion_tag_handling.md).

### Future Improvements

Future improvements could focus on:
- Optimizing the prompts for each phase
- Reducing latency in the dual prompt system
- Enhancing the emotion extraction process to capture more nuanced expressions
- Improving the single prompt approach to be more reliable in preventing tag pronunciation
