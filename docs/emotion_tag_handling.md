# Emotion Tag Handling in Gemini Live Agent

This document explains how emotion tags are handled in the Gemini Live Agent implementation and how to properly configure the system to avoid emotion tag pronunciation issues.

## Overview

The Gemini Live Agent supports emotion tags in the format `[emotion]` or `[emotion:intensity]` (e.g., `[joy:0.7]`, `[surprise:0.3]`). These tags are used to control the facial expressions of the Live2D model but should not be spoken aloud by the TTS system.

## Issue: Emotion Tag Pronunciation

In some cases, the Gemini Live API might include emotion tags in the generated speech, causing the AI to pronounce tags like "[joy]" out loud. This is undesirable as these tags are meant to be metadata for controlling facial expressions, not part of the spoken content.

## Primary Solutions

We've implemented two approaches to prevent emotion tags from being pronounced:

### 1. Single Prompt Approach (Default)

This approach uses a single prompt with instructions not to pronounce emotion tags:

1. **Enhanced System Instruction**: The system instruction is modified to explicitly instruct the model not to vocalize emotion tags. This instruction is placed at the beginning of the system prompt for maximum effectiveness.

2. **Robust Emotion Tag Removal**: The `_remove_emotion_tags` method uses a comprehensive regex pattern to identify and remove emotion tags from the text before it's sent to the TTS system.

3. **Double Cleaning**: As an additional safety measure, we perform a second cleaning pass on the transcript to ensure all emotion tags are removed.

### 2. Dual Prompt System (Optional)

This approach completely separates emotion planning from speech generation:

1. **Planning Phase**: First, the model is asked to plan a response with emotion tags. This response is never spoken to the user but is used to extract emotion tags for facial expressions.

2. **Clean Response Phase**: Then, the model is asked to generate a clean spoken response without any emotion tags. This is the audio that is actually played to the user.

You can enable this approach by setting `use_dual_prompt_system: true` in your configuration. See [Gemini Live Emotion Tag Handling](gemini_live_emotion_tag_handling.md) for more details.

## Advanced Strategies

If the primary solution doesn't completely resolve the issue, consider these advanced strategies:

### 1. Alternative Tag Formats

Some models are less likely to pronounce tags if they are less "word-like." Consider using:

- Curly braces: `{joy}` instead of `[joy]`
- XML-style tags: `<emotion type="joy"/>`
- Unicode zero-width spaces inside tags: `[j​oy]` (there's an invisible character between 'j' and 'o')

Test each format to see which the model is least likely to pronounce.

### 2. Reinforcement in Every Message

Consider programmatically prepending the instruction about not pronouncing tags to every user message, not just at session start. This can help reinforce the instruction throughout a long conversation.

### 3. Model Feedback

Ask the model to confirm its understanding:

```
"Repeat back: What should you do when you see [emotion] tags?"
```

If it answers correctly, it's more likely to comply with the instruction.

## Configuration

### Emotion Tag Handling Approach

You can choose between the single prompt approach (default) and the dual prompt system by setting the `use_dual_prompt_system` flag in your configuration:

```yaml
gemini_live_agent:
  # Other configuration options...
  use_dual_prompt_system: false  # Set to true to use the dual prompt system
```

For more details on the configuration options and the differences between the two approaches, see [Gemini Live Emotion Tag Handling](gemini_live_emotion_tag_handling.md).

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

### Implementation Details

The Gemini Live Agent implementation includes the following key components for handling emotion tags:

1. **System Instruction Enhancement**:
   ```python
   # Add strong instruction about not speaking emotion tags
   emotion_instruction = """
   CRITICAL INSTRUCTION: When generating speech audio, you MUST NOT speak or vocalize any emotion tags like [joy], [joy:0.7], [surprise], [surprise:0.3], etc.

   These emotion tags are ONLY metadata for controlling facial expressions and animations. They should NEVER be spoken aloud.

   Example: If your response is "[joy:0.7] I'm happy to help you!", you should only speak "I'm happy to help you!" without saying the "[joy:0.7]" part.

   This is extremely important for proper functioning of the system.
   """

   # Append the emotion instruction to the system instruction
   modified_instruction += "\n\n" + emotion_instruction
   ```

2. **Emotion Tag Removal**:
   ```python
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
       # This pattern is more robust and handles various formats
       emotion_pattern = r'\[\s*([a-zA-Z_]+)(?:\s*:\s*([0-9]*\.?[0-9]+))?\s*\]'

       # Remove all emotion tags from the text
       clean_text = re.sub(emotion_pattern, '', text)

       # Clean up any extra spaces
       clean_text = re.sub(r'\s+', ' ', clean_text).strip()

       return clean_text
   ```

3. **Double Cleaning for Safety**:
   ```python
   # Double-check that clean_transcript doesn't contain any emotion tags
   # This is a safety measure in case the first cleaning missed something
   final_clean_transcript = self._remove_emotion_tags(clean_transcript)
   ```

## TTS System Interaction with Emotion Tags

Beyond preventing the LLM from vocalizing emotion tags, it's important to understand how these tags might be interpreted or used by the Text-to-Speech (TTS) system itself. The behavior can vary significantly depending on the TTS engine and integration method.

### Kokoro TTS Microservice

The Kokoro TTS microservice (detailed in `docs/kokoro_tts_integration.md`) has specific logic to handle emotion tags:

-   **Tag Parsing:** It parses the first `[emotion:intensity]` tag from the input text.
-   **Speed Adjustment:** The primary effect is on **speech speed**. The service uses a configurable `emotion_mapping` (e.g., `joy: 1.2`, `sadness: 0.8`) to determine a speed multiplier based on the detected emotion. The intensity value from the tag (0.0 to 1.0) scales this effect, with a threshold of 0.3 below which no speed change occurs.
-   **Tag Removal:** All emotion tags are removed from the text before it is sent to the underlying Kokoro engine for synthesis.
-   **No Direct Style/Pitch Change:** The microservice currently does not use emotion tags to change the voice style (e.g., a "happy voice") or pitch directly. Any such nuances would depend on the base characteristics of the selected Kokoro voice.

### Kokoro TTS Direct Integration (`KokoroWrapper`)

When using Kokoro TTS via direct integration with `KokoroWrapper` (detailed in `docs/kokoro_tts_setup.md`):

-   **No Wrapper-Level Processing:** The `KokoroWrapper` itself **does not parse emotion tags or modify speech parameters** like speed or pitch based on them.
-   **Tags Passed to Engine:** The input text, including any emotion tags, is passed directly to the underlying Kokoro TTS engine.
-   **Engine/Voice Dependent Behavior:** Any effect the tags have on speech output depends entirely on the **native capabilities of the Kokoro TTS engine and the specific voice being used.** Some voices might be designed to interpret specific embedded tags or SSML-like syntax, but this is not managed or standardized by the `KokoroWrapper`.
-   **No `emotion_mapping` Use:** The `emotion_mapping` in `conf.yaml` (if defined for `kokoro_tts` direct integration) is not used by `KokoroWrapper` for parameter adjustments in the same way the microservice uses its own `emotion_mapping`.

For explicit control over speech speed based on emotion tags when using Kokoro, the TTS microservice is the recommended approach.

### Other TTS Systems

For other TTS engines integrated with the application, their handling of embedded emotion tags will vary:
- Some may ignore them completely.
- Some may have their own syntax for style or prosody control (e.g., SSML).
- Some might be designed to interpret `[emotion:intensity]` tags if explicitly documented for that engine.

Always refer to the specific documentation for the active TTS engine to understand how it interacts with text containing emotion tags. The primary goal of the emotion tag removal strategies described in this document is to prevent the *Language Model (LLM)* from speaking the tags, ensuring the TTS system receives text that is either clean or contains tags it is specifically designed to process.

## Troubleshooting

If you still experience issues with emotion tags being pronounced:

1. **Check the System Instruction**: Ensure the system instruction clearly instructs the model not to vocalize emotion tags.

2. **Verify the Emotion Tag Pattern**: The regex pattern should match all variations of emotion tags used in your system.

3. **Enable Debug Logging**: Set the logger level to DEBUG to see the original and cleaned transcripts.

4. **Test with Simple Examples**: Test with simple examples containing emotion tags to verify the cleaning process works correctly.

## References

- [Gemini Live API Usage Guide](gemini_live_api_usage.md)
- [Live2D Emotion-Motion Integration Plan](live2d_emotion_motion_integration_plan.md)
- [Two-Step Approach for Emotion Tag Handling](two_step_emotion_handling.md)
- [Gemini Live Emotion Tag Handling](gemini_live_emotion_tag_handling.md)
