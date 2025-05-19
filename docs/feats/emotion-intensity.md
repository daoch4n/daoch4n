# Emotion Intensity Implementation for Live2D Models

## Overview

This document analyzes the current implementation of emotion intensity modifiers in the Live2D model system, specifically for the Shizuku character. It examines how emotion tags with intensity values (e.g., `[joy:0.7]`, `[surprise:0.3]`) are processed throughout the system and identifies areas for improvement.

## Current Implementation

The emotion intensity system is implemented across several components:

1. **Backend Emotion Extraction**
2. **Backend-to-Frontend Transmission**
3. **Frontend Expression Application**
4. **Live2D Model Expression Handling**

### 1. Backend Emotion Extraction

**Status: ✅ Fully Implemented**

In `src/open_llm_vtuber/live2d_model.py`, the `extract_emotion` method properly extracts emotion tags and their intensity values from text:

```python
def extract_emotion(self, str_to_check: str) -> list:
    # Regular expression to match both formats:
    # [emotion] and [emotion:intensity]
    emotion_pattern = r'\[([\w]+)(?::([0-9]*\.?[0-9]+))?\]'
    
    # Find all emotion tags in the text
    matches = re.finditer(emotion_pattern, str_to_check)
    
    for match in matches:
        emotion = match.group(1)
        intensity_str = match.group(2)
        
        # Check if the emotion exists in our emotion map
        if emotion in self.emo_map:
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
```

This code correctly:
- Uses a regex pattern to match both `[emotion]` and `[emotion:intensity]` formats
- Extracts the intensity value if present
- Converts it to a float and clamps it to the range [0.0, 1.0]
- Defaults to 1.0 if no intensity is specified or if parsing fails

### 2. Backend-to-Frontend Transmission

**Status: ✅ Fully Implemented**

In `src/open_llm_vtuber/agent/transformers.py`, the `actions_extractor` decorator properly packages the expression index and intensity for transmission to the frontend:

```python
# Extract emotion expressions with intensity values
expression_tuples = live2d_model.extract_emotion(sentence.text)
if expression_tuples:
    # Convert expression tuples to interpolated expression dictionaries
    interpolated_expressions = []
    for expr_index, intensity in expression_tuples:
        interpolated_expr = live2d_model.get_interpolated_expression(
            expr_index, intensity
        )
        interpolated_expressions.append(interpolated_expr)
        logger.debug(f"Expression {expr_index} with intensity {intensity}")

    actions.expressions = interpolated_expressions
```

And in `live2d_model.py`, the `get_interpolated_expression` method creates a dictionary with the expression index and intensity:

```python
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

### 3. Frontend Expression Application

**Status: ❌ Incomplete Implementation**

In `frontend-src/src/renderer/src/hooks/utils/use-audio-task.ts`, the frontend receives and attempts to apply the expression:

```typescript
if (expressions?.[0] !== undefined) {
  model.expression(expressions[0]);
  
  // Handle motion if available
  if (motions?.[0] !== undefined) {
    const motionName = motions[0];
    console.log(`Starting motion: ${motionName}`);
    
    // Check if model has motion method
    if (model.motion) {
      model.motion(motionName);
    } else {
      console.warn('Motion method not available on model');
    }
  }
}
```

However, when we look at how the `expression` method is implemented in `live2d.tsx`:

```typescript
window.live2d = {
  expression: (name?: string | number) => modelRef.current?.expression(name),
  setExpression: (name?: string | number) => {
    if (name !== undefined) {
      modelRef.current?.internalModel.motionManager.expressionManager?.setExpression(name);
    }
  },
  // ...
};
```

The issue is that:
1. The `expression` method is just passing the name/index to the model's own `expression` method
2. There's no evidence that this method handles the intensity value
3. Other parts of the code use `setExpression` which only takes a name/index parameter, not an intensity value

### 4. Live2D Model Expression Handling

**Status: ❌ No Built-in Support**

The Live2D model's expression files (like `f02.exp.json`) define fixed parameters for expressions:

```json
{
  "type": "Live2D Expression",
  "fade_in": 500,
  "fade_out": 500,
  "params": [
    {"id": "PARAM_EYE_BALL_X", "val": -0.4},
    {"id": "PARAM_EYE_BALL_Y", "val": -0.7},
    {"id": "PARAM_EYE_L_OPEN", "val": 0.7, "def": 1, "calc": "mult"},
    // ...
  ]
}
```

These parameters define how the model's features should be adjusted for a particular expression, but there's no built-in mechanism to handle varying intensities.

## Conclusion

The current implementation:
- ✅ Correctly extracts intensity values from emotion tags
- ✅ Properly transmits these values from the backend to the frontend
- ❌ Does not properly apply these intensity values in the frontend
- ❌ The Live2D model itself doesn't have built-in support for expression intensities

## Recommended Improvements

To fully implement intensity-based facial expressions:

1. **Modify the Frontend Expression Method**:
   ```typescript
   // In live2d.tsx
   expression: (exprData?: any) => {
     if (typeof exprData === 'object' && exprData.expression_index !== undefined && exprData.intensity !== undefined) {
       // Handle expression with intensity
       const expressionIndex = exprData.expression_index;
       const intensity = exprData.intensity;
       
       // Get the neutral expression parameters
       const neutralParams = modelRef.current?.internalModel.motionManager.expressionManager?.definitions[0]?.parameters || [];
       
       // Get the target expression parameters
       const targetParams = modelRef.current?.internalModel.motionManager.expressionManager?.definitions[expressionIndex]?.parameters || [];
       
       // Interpolate between neutral and target based on intensity
       const interpolatedParams = interpolateParameters(neutralParams, targetParams, intensity);
       
       // Apply the interpolated parameters
       applyParameters(modelRef.current, interpolatedParams);
     } else {
       // Fall back to the original behavior for backward compatibility
       modelRef.current?.expression(exprData);
     }
   }
   ```

2. **Implement Parameter Interpolation**:
   ```typescript
   function interpolateParameters(neutralParams, targetParams, intensity) {
     return targetParams.map(targetParam => {
       const neutralParam = neutralParams.find(p => p.id === targetParam.id);
       if (!neutralParam) return targetParam;
       
       // Linear interpolation between neutral and target values
       const interpolatedValue = neutralParam.value + (targetParam.value - neutralParam.value) * intensity;
       
       return {
         ...targetParam,
         value: interpolatedValue
       };
     });
   }
   ```

3. **Apply Interpolated Parameters**:
   ```typescript
   function applyParameters(model, params) {
     params.forEach(param => {
       model.internalModel.coreModel.setParameterValueById(param.id, param.value);
     });
   }
   ```

By implementing these changes, the system would properly support intensity-based facial expressions, allowing for more nuanced emotional displays in the Live2D model.
