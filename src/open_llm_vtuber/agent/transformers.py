from typing import AsyncIterator, Tuple, Callable, List
from functools import wraps
from .output_types import Actions, SentenceOutput, DisplayText
from ..utils.tts_preprocessor import tts_filter as filter_text
from ..live2d_model import Live2dModel
from ..config_manager import TTSPreprocessorConfig
from ..utils.sentence_divider import SentenceDivider
from ..utils.sentence_divider import SentenceWithTags, TagState
from ..emotion_motion_map import EmotionMotionMapper
from loguru import logger


def sentence_divider(
    faster_first_response: bool = True,
    segment_method: str = "pysbd",
    valid_tags: List[str] = None,
):
    """
    Decorator that transforms token stream into sentences with tags

    Args:
        faster_first_response: bool - Whether to enable faster first response
        segment_method: str - Method for sentence segmentation
        valid_tags: List[str] - List of valid tags to process
    """

    def decorator(
        func: Callable[..., AsyncIterator[str]],
    ) -> Callable[..., AsyncIterator[SentenceWithTags]]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> AsyncIterator[SentenceWithTags]:
            divider = SentenceDivider(
                faster_first_response=faster_first_response,
                segment_method=segment_method,
                valid_tags=valid_tags or [],
            )
            token_stream = func(*args, **kwargs)
            async for sentence in divider.process_stream(token_stream):
                yield sentence
                logger.debug(f"sentence_divider: {sentence}")

        return wrapper

    return decorator


def actions_extractor(live2d_model: Live2dModel):
    """
    Decorator that extracts actions from sentences, including both
    facial expressions and body motions based on emotion tags.
    Supports emotion intensity values for more nuanced expressions.
    """
    # Create an emotion-to-motion mapper
    emotion_mapper = EmotionMotionMapper()

    def decorator(
        func: Callable[..., AsyncIterator[SentenceWithTags]],
    ) -> Callable[..., AsyncIterator[Tuple[SentenceWithTags, Actions]]]:
        @wraps(func)
        async def wrapper(
            *args, **kwargs
        ) -> AsyncIterator[Tuple[SentenceWithTags, Actions]]:
            sentence_stream = func(*args, **kwargs)
            async for sentence in sentence_stream:
                actions = Actions()
                # Only extract emotions for non-tag text
                if not any(
                    tag.state in [TagState.START, TagState.END] for tag in sentence.tags
                ):
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

                yield sentence, actions

        return wrapper

    return decorator


def display_processor():
    """
    Decorator that processes text for display.
    """

    def decorator(
        func: Callable[..., AsyncIterator[Tuple[SentenceWithTags, Actions]]],
    ) -> Callable[..., AsyncIterator[Tuple[SentenceWithTags, DisplayText, Actions]]]:
        @wraps(func)
        async def wrapper(
            *args, **kwargs
        ) -> AsyncIterator[Tuple[SentenceWithTags, DisplayText, Actions]]:
            stream = func(*args, **kwargs)

            async for sentence, actions in stream:
                text = sentence.text
                # Handle think tag states
                for tag in sentence.tags:
                    if tag.name == "think":
                        if tag.state == TagState.START:
                            text = "("
                        elif tag.state == TagState.END:
                            text = ")"

                display = DisplayText(text=text)  # Simplified DisplayText creation
                yield sentence, display, actions

        return wrapper

    return decorator


def tts_filter(
    tts_preprocessor_config: TTSPreprocessorConfig = None,
):
    """
    Decorator that filters text for TTS.
    Skips TTS for think tag content.
    """

    def decorator(
        func: Callable[
            ..., AsyncIterator[Tuple[SentenceWithTags, DisplayText, Actions]]
        ],
    ) -> Callable[..., AsyncIterator[SentenceOutput]]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> AsyncIterator[SentenceOutput]:
            sentence_stream = func(*args, **kwargs)
            config = tts_preprocessor_config or TTSPreprocessorConfig()

            async for sentence, display, actions in sentence_stream:
                if any(tag.name == "think" for tag in sentence.tags):
                    tts = ""
                else:
                    tts = filter_text(
                        text=display.text,
                        remove_special_char=config.remove_special_char,
                        ignore_brackets=config.ignore_brackets,
                        ignore_parentheses=config.ignore_parentheses,
                        ignore_asterisks=config.ignore_asterisks,
                        ignore_angle_brackets=config.ignore_angle_brackets,
                    )

                logger.debug(f"[{display.name}] display: {display.text}")
                logger.debug(f"[{display.name}] tts: {tts}")

                yield SentenceOutput(
                    display_text=display,
                    tts_text=tts,
                    actions=actions,
                )

        return wrapper

    return decorator
