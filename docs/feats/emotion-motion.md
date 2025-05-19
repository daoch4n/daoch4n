# Emotion-Motion Integration for Live2D Model

This document describes the implementation of automatic body motions based on emotion tags in the AI's responses.

## Overview

The Live2D model animation system has been enhanced to automatically change both facial expressions and body poses based on emotion tags in the AI's responses. This creates a more dynamic and expressive character that reacts naturally to the emotional content of the conversation.

The system is intensity-aware, meaning that body motions are only triggered when the emotion intensity is greater than 0.5. This allows for more nuanced reactions where mild emotions (intensity ≤ 0.5) only change facial expressions, while stronger emotions (intensity > 0.5) also trigger body motions.

## Implementation Details

### 1. Emotion-Motion Mapping

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

### 2. Backend Processing

The `actions_extractor` transformer in `src/open_llm_vtuber/agent/transformers.py` extracts emotions from the text and maps them to appropriate motions, but only when the emotion intensity is greater than 0.5:

```python
# Map emotions to motions (using the same emotion tags)
motions = []
# Extract emotion tags from text using regex to handle both formats
import re
text = sentence.text.lower()
emotion_pattern = r'\[([\w]+)(?::([0-9]*\.?[0-9]+))?\]'
matches = re.finditer(emotion_pattern, text)

for match in matches:
    emotion = match.group(1)
    intensity_str = match.group(2)

    # Parse intensity value, default to 1.0 if not specified
    intensity = 1.0
    if intensity_str:
        try:
            intensity = float(intensity_str)
            # Clamp intensity to valid range [0.0, 1.0]
            intensity = max(0.0, min(1.0, intensity))
        except ValueError:
            # If conversion fails, use default intensity
            intensity = 1.0

    # Only add motion if intensity is greater than 0.5
    if intensity > 0.5 and emotion in live2d_model.emo_map:
        # Get corresponding motion for this emotion
        motion = emotion_mapper.get_motion_for_emotion(emotion)
        if motion and motion not in motions:  # Avoid duplicates
            motions.append(motion)
            logger.debug(f"Adding motion {motion} for emotion {emotion} with intensity {intensity}")

# Set motions if any were found
if motions:
    actions.motions = motions
    logger.debug(f"Mapped emotions to motions: {motions}")
```

### 3. Frontend Integration

The frontend receives the motion information through the WebSocket and applies it to the Live2D model:

```typescript
// In use-audio-task.ts
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
```

## Available Motions

The Live2D model (shizuku) has the following motion groups:

- `idle`: Default idle animations
- `tap_body`: Happy/excited animations
- `pinch_in`: Fearful/anxious animations
- `pinch_out`: Surprised animations
- `shake`: Sad/angry animations
- `flick_head`: Surprised animations

Each motion group contains multiple animation files (e.g., `idle_00.mtn`, `idle_01.mtn`, `idle_02.mtn`).

## Usage

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

## Customization

To customize the emotion-motion mapping, modify the `DEFAULT_EMOTION_MOTION_MAP` in `src/open_llm_vtuber/emotion_motion_map.py`.

## Troubleshooting

If motions are not playing correctly:

1. Check the browser console for errors
2. Verify that the emotion tag is recognized (should be one of: joy, sadness, anger, disgust, fear, surprise, smirk, neutral)
3. Confirm that the motion group exists in the Live2D model
4. Ensure the WebSocket connection is working properly

## Future Improvements

Potential enhancements to the emotion-motion system:

1. Add more diverse motions for each emotion
2. Implement random selection from multiple motion options for each emotion
3. Add intensity-based motion selection (similar to expression intensity)
4. Support for custom emotion-motion mappings through configuration files
