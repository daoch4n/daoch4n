"""
Mapping between emotion tags and Live2D motions.
This module defines the relationship between emotion tags and appropriate body motions.
"""

from typing import Dict, List, Optional
from loguru import logger

# Default emotion to motion mapping
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

class EmotionMotionMapper:
    """
    Maps emotion tags to appropriate Live2D motions.
    
    This class provides functionality to map emotion tags to appropriate
    Live2D motions based on the emotion's meaning and context.
    """
    
    def __init__(self, custom_mapping: Optional[Dict[str, List[str]]] = None):
        """
        Initialize the EmotionMotionMapper.
        
        Args:
            custom_mapping: Optional custom mapping from emotions to motions.
                           If provided, will override the default mapping.
        """
        self.emotion_motion_map = custom_mapping or DEFAULT_EMOTION_MOTION_MAP
        logger.debug(f"Initialized EmotionMotionMapper with {len(self.emotion_motion_map)} mappings")
    
    def get_motion_for_emotion(self, emotion: str) -> Optional[str]:
        """
        Get an appropriate motion for the given emotion.
        
        Args:
            emotion: The emotion tag (without brackets).
            
        Returns:
            A motion name that corresponds to the emotion, or None if no mapping exists.
        """
        emotion = emotion.lower()
        if emotion not in self.emotion_motion_map:
            logger.debug(f"No motion mapping found for emotion: {emotion}")
            return None
            
        motion_options = self.emotion_motion_map[emotion]
        if not motion_options:
            return None
            
        # For now, just return the first motion in the list
        # In the future, we could randomly select one or use more sophisticated logic
        return motion_options[0]
