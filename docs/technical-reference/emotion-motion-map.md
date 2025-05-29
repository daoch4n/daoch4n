# Emotion Motion Map

The `emotion_motion_map.py` module defines the mapping between emotion tags and corresponding Live2D motions. This is crucial for animating the VTuber model based on the detected emotions in the conversation.

## Constants

### `DEFAULT_EMOTION_MOTION_MAP`
A dictionary that defines the default mapping from emotion tags to a list of Live2D motion names.

```python
DEFAULT_EMOTION_MOTION_MAP = {
    "joy": ["tap_body"],
    "sadness": ["shake"],
    "anger": ["shake"],
    "disgust": ["shake"],
    "fear": ["pinch_in"],
    "surprise": ["flick_head"],
    "smirk": ["tap_body"],
    "neutral": ["idle"],
}
```

**Keys:** Emotion tags (e.g., "joy", "sadness", "neutral").
**Values:** A list of strings, where each string is the name of a Live2D motion file (without extension).

## Classes

### `EmotionMotionMapper`
Maps emotion tags to appropriate Live2D motions. This class provides functionality to retrieve a suitable motion name for a given emotion tag.

#### `__init__(self, custom_mapping: Optional[Dict[str, List[str]]] = None)`
Initializes the `EmotionMotionMapper`.

**Arguments:**
*   `custom_mapping` (`Optional[Dict[str, List[str]]]`): An optional dictionary for custom emotion-to-motion mappings. If provided, this mapping will override the `DEFAULT_EMOTION_MOTION_MAP`.

#### `get_motion_for_emotion(self, emotion: str) -> Optional[str]`
Retrieves an appropriate Live2D motion name for the given emotion tag. The emotion tag is converted to lowercase before lookup. Currently, it returns the first motion in the list of options for a given emotion. Future enhancements might include more sophisticated logic for motion selection (e.g., random selection).

**Arguments:**
*   `emotion` (`str`): The emotion tag (e.g., "joy", "neutral"). This should be the raw emotion string, without any surrounding brackets.

**Returns:**
*   `Optional[str]`: A string representing the name of a Live2D motion (e.g., "tap_body", "idle"), or `None` if no mapping is found for the given emotion or if the mapped list of motions is empty.