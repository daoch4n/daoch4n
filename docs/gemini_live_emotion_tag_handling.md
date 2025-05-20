# Gemini Live Emotion Tag Handling

This document explains the two approaches for handling emotion tags in the Gemini Live Agent and how to configure them.

## Overview

The Gemini Live Agent supports two different approaches for handling emotion tags:

1. **Single Prompt Approach** (Default): Uses a single prompt that instructs the model to include emotion tags for facial expressions but not to pronounce them.
2. **Dual Prompt System**: Uses a two-step approach where the model first plans a response with emotion tags, then generates a clean spoken response without tags.

## Configuration

To configure which approach to use, set the `use_dual_prompt_system` flag in your `conf.yaml` file:

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

## Approaches Explained

### 1. Single Prompt Approach (Default)

The single prompt approach uses a single prompt that instructs the model to include emotion tags but not to pronounce them:

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
- May occasionally pronounce emotion tags if the model doesn't follow instructions perfectly
- Less control over the separation of emotion planning and speech generation

### 2. Dual Prompt System

The dual prompt system uses a two-step approach:

1. **Planning Phase**: Ask the model to plan a response with emotion tags
   ```
   Plan your response to the user and include emotion tags like [joy], [surprise], [sadness], etc. 
   to indicate your emotional tone. Use format [emotion:0.7] to indicate intensity if needed. 
   This is for planning purposes only to capture your emotional state.
   ```

2. **Clean Response Phase**: Generate a clean spoken response without emotion tags
   ```
   Respond naturally to the user without using or mentioning any emotion tags or square brackets. 
   Just give a normal conversational response as if you're speaking directly to them.
   ```

**Pros:**
- More reliable prevention of emotion tag pronunciation
- Better separation of emotion planning and speech generation
- More consistent behavior

**Cons:**
- Higher latency (requires two API calls)
- Higher token usage
- More complex implementation

## Performance Considerations

1. **Latency Impact**:
   - The dual prompt system requires two separate calls to the Gemini API, which increases response latency
   - Typical additional latency: 300-800ms depending on network conditions and response length

2. **Token Usage**:
   - The dual prompt approach approximately doubles the token usage per interaction
   - Planning phase: ~50-100 tokens per user message
   - Clean response phase: ~50-100 tokens per user message

## Recommended Usage

- **Use the single prompt approach (default)** for most use cases, especially when latency and token usage are concerns.
- **Use the dual prompt system** when you need more reliable prevention of emotion tag pronunciation or when the model consistently pronounces tags despite instructions.

## Implementation Details

Both approaches extract emotion tags from the model's response and use them to control the Live2D model's facial expressions. The difference is in how they generate the spoken response:

- The single prompt approach removes emotion tags from the transcript before displaying it to the user.
- The dual prompt system uses a separate prompt to generate a clean response without emotion tags.

In both cases, the emotion tags are used to control the Live2D model's facial expressions, but they are not spoken aloud by the TTS system.
