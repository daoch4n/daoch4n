# Implementation Plan: Automatic Facial Expressions and Body Poses Based on Emotion Tags

## Overview
The goal is to enhance the Live2D model animation system to automatically change both facial expressions and body poses based on emotion tags in the AI's responses, rather than requiring manual clicks.

## Current System Analysis
1. **Emotion Detection**: The system already detects emotion tags in the AI's responses (e.g., `[joy]`, `[sadness]`) in the `extract_emotion` method of the `Live2dModel` class in the backend.

2. **Facial Expression Setting**: The frontend already sets facial expressions based on emotion tags via the `setExpression` method in `use-live2d-expression.ts` hook, which is called when audio is played in `use-audio-task.ts`.

3. **Body Motion System**: The Live2D model has a motion system that can play animations via `startMotion` and `startRandomMotion` methods in `lappmodel.ts`. There's also a `startTapMotion` method that plays motions when the model is tapped.

4. **Emotion-Motion Mapping**: The backend has an `emotion_motion_map.py` file that maps emotions to appropriate motions, but this mapping isn't currently used by the frontend.

## Implementation Steps

### 1. Enhance the WebSocket Message Format
Modify the backend to include both expression and motion information in the WebSocket messages:

```typescript
// Current format in websocket-handler.tsx
addAudioTask({
  audioBase64: message.audio || '',
  volumes: message.volumes || [],
  sliceLength: message.slice_length || 0,
  displayText: message.display_text || null,
  expressions: message.actions?.expressions || null,  // Already exists
  forwarded: message.forwarded || false,
});

// Need to add motions field
```

### 2. Modify the Backend to Send Motion Information

Update the backend's `emotion_motion_map.py` to be used when processing AI responses:

```python
# In src/open_llm_vtuber/conversations/tts_manager.py or similar
def process_response(text, ...):
    # Extract emotions
    emotions = live2d_model.extract_emotion(text)
    
    # Get corresponding motions for these emotions
    motions = []
    for emotion in emotions:
        motion = emotion_motion_mapper.get_motion_for_emotion(emotion)
        if motion:
            motions.append(motion)
    
    # Include both in the response
    return {
        "text": cleaned_text,
        "actions": {
            "expressions": emotions,
            "motions": motions
        }
    }
```

### 3. Update the Frontend Audio Task Hook

Modify the `use-audio-task.ts` hook to handle both expressions and motions:

```typescript
// In handleAudioPlayback function
if (lappAdapter && expressions?.[0] !== undefined) {
  setExpression(
    expressions[0],
    lappAdapter,
    `Set expression to: ${expressions[0]}`,
  );
  
  // Add motion handling
  if (options.motions?.[0] !== undefined) {
    const motionName = options.motions[0];
    console.log(`Starting motion: ${motionName}`);
    const model = lappAdapter.getModel();
    if (model) {
      model.startRandomMotion(motionName, LAppDefine.PriorityNormal);
    }
  }
}
```

### 4. Update the WebSocket Handler

Modify the WebSocket handler to extract and pass motion information:

```typescript
// In websocket-handler.tsx
case 'audio':
  if (aiState === 'interrupted' || aiState === 'listening') {
    console.log('Audio playback intercepted. Sentence:', message.display_text?.text);
  } else {
    console.log("actions", message.actions);
    addAudioTask({
      audioBase64: message.audio || '',
      volumes: message.volumes || [],
      sliceLength: message.slice_length || 0,
      displayText: message.display_text || null,
      expressions: message.actions?.expressions || null,
      motions: message.actions?.motions || null,  // Add this line
      forwarded: message.forwarded || false,
    });
  }
  break;
```

### 5. Update the AudioTask Type Definition

```typescript
// In use-audio-task.ts
interface AudioTaskOptions {
  audioBase64: string
  volumes: number[]
  sliceLength: number
  displayText?: DisplayText | null
  expressions?: string[] | number[] | null
  motions?: string[] | null  // Add this line
  speaker_uid?: string
  forwarded?: boolean
}
```

## Files to Modify

1. **Backend:**
   - `src/open_llm_vtuber/emotion_motion_map.py` - Ensure it's properly integrated
   - `src/open_llm_vtuber/conversations/tts_manager.py` - Update to include motions in responses

2. **Frontend:**
   - `Open-LLM-VTuber-Web/src/renderer/src/hooks/utils/use-audio-task.ts` - Update to handle motions
   - `Open-LLM-VTuber-Web/src/renderer/src/services/websocket-handler.tsx` - Update to pass motions
   - `Open-LLM-VTuber-Web/src/renderer/src/services/websocket-service.ts` - Update message type definitions

## Testing Plan

1. Test with different emotion tags to ensure both expressions and motions are triggered
2. Verify that the motion selection is appropriate for each emotion
3. Test with rapid emotion changes to ensure smooth transitions
4. Test with long responses containing multiple emotion tags
