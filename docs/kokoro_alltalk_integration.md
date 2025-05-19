# Kokoro-82M Integration with AllTalk TTS for Daoko

This document describes how to use the Kokoro-82M speech synthesis model through AllTalk TTS with RVC voice conversion for the Daoko Live2D character.

## Overview

The Kokoro-82M model is an open-weight TTS model with 82 million parameters. While we previously integrated it directly, we now use it through AllTalk TTS to enable RVC (Retrieval-based Voice Conversion) functionality for Daoko. This approach provides several benefits:

1. **Voice Conversion**: RVC allows us to convert the base voice to sound more like Daoko
2. **Emotion-Aware Speech**: The integration supports emotion tags for expressive speech
3. **Consistent API**: AllTalk TTS provides a consistent API for different TTS engines

## Prerequisites

1. **AllTalk TTS Server**: You need to have the AllTalk TTS server running locally
2. **Kokoro-82M Model**: The model files should be available at `~/alltalk_tts/models/kokoro/`
3. **RVC Model for Daoko**: The RVC model for Daoko should be available in the AllTalk TTS server

## Configuration

To use Kokoro-82M through AllTalk TTS, you need to use the `alltalk_tts` engine in your configuration file. A sample configuration file is provided at `docs/conf/kokoro_alltalk_daoko.yaml`.

### Key Configuration Parameters

```yaml
TTS_CONFIG:
  TTS_ENGINE: "alltalk_tts"
  TTS_VOICE: "en_US-ljspeech-high.onnx"  # Base voice from AllTalk
  TTS_LANGUAGE: "en"
  TTS_API_URL: "http://127.0.0.1:7851"  # URL of the AllTalk TTS API server
  TTS_RVC_ENABLED: true  # Enable RVC voice conversion
  TTS_RVC_MODEL: "daoko[23]_16hs_3bs_SPLICED_NPROC_40k_v1"  # RVC model for Daoko
  TTS_RVC_PITCH: 0  # Pitch adjustment for RVC voice conversion
  TTS_CACHE_DIR: "cache"
  TTS_OUTPUT_FORMAT: "wav"
  # Emotion mapping from our emotion tags to AllTalk styles
  TTS_EMOTION_MAPPING:
    joy: "happy"
    sadness: "sad"
    anger: "angry"
    fear: "fearful"
    surprise: "surprised"
    disgust: "disgusted"
    neutral: "neutral"
    smirk: "happy"
```

## Emotion-Aware Speech Synthesis

The AllTalk TTS integration supports emotion-aware speech synthesis by mapping emotion tags in the text to appropriate voice styles and pitch adjustments. For example, if the text contains the emotion tag `[joy:0.8]`, the AllTalk TTS engine will use a happy voice style with a higher pitch for that text.

The emotion mapping is defined in the configuration file and can be customized as needed.

### How Emotions Affect Speech

Different emotions affect speech parameters in the following ways:

- **Joy/Happiness**: Higher pitch (+2 semitones at maximum intensity), slightly faster speech
- **Sadness**: Lower pitch (-2 semitones at maximum intensity), slightly slower speech
- **Anger**: Slightly lower pitch (-1 semitone at maximum intensity)
- **Fear**: Higher pitch (+3 semitones at maximum intensity)
- **Surprise**: Higher pitch (+4 semitones at maximum intensity)
- **Disgust**: Slightly lower pitch (-1 semitone at maximum intensity)
- **Neutral**: Default pitch and speed

#### RVC Pitch Adjustment

The pitch adjustment in RVC is measured in semitones (half-steps in musical terms):

- **+12 semitones**: Raises the pitch by one octave (often used to convert a male voice to a female-sounding voice)
- **-12 semitones**: Lowers the pitch by one octave (often used to convert a female voice to a male-sounding voice)
- **0 semitones**: Keeps the pitch unchanged (suitable for same-gender conversions)

Since the RVC model is already trained on Daoko's voice, we use 0 as the base pitch and only apply subtle adjustments (between -2 and +4 semitones) for emotional variations.

#### Emotion Intensity

The intensity of the emotion (e.g., `[joy:0.8]` vs `[joy:0.3]`) affects how much these parameters are adjusted:

- Intensities below 0.3 don't trigger pitch adjustments
- Intensities from 0.3 to 1.0 are mapped to proportional pitch adjustments
- Higher intensity values result in more pronounced adjustments

For example, `[joy:1.0]` would apply the full +2 semitone adjustment, while `[joy:0.65]` would apply a +1 semitone adjustment (approximately).

## Testing

You can test the Kokoro-AllTalk integration using the unified test script:

```bash
./test_tts.sh --engine alltalk --voice en_US-ljspeech-high.onnx --rvc-enabled --rvc-model "daoko[23]_16hs_3bs_SPLICED_NPROC_40k_v1"
```

This will generate a test audio file using the AllTalk TTS engine with RVC voice conversion.

## Troubleshooting

### AllTalk TTS Server Not Running

If you encounter an error about the AllTalk TTS server not running, make sure the server is running at the specified URL (default: `http://127.0.0.1:7851`).

### RVC Model Not Found

If you encounter an error about the RVC model not being found, make sure the model is available in the AllTalk TTS server. You can check the available RVC models by running:

```bash
curl http://127.0.0.1:7851/api/rvcmodels
```

### Other Issues

If you encounter other issues, please check the logs for error messages and refer to the documentation for the specific TTS engine:

- [AllTalk TTS](https://github.com/erew123/alltalk_tts)
- [Kokoro-82M on Hugging Face](https://huggingface.co/hexgrad/Kokoro-82M)
- [RVC (Retrieval-based Voice Conversion)](https://github.com/RVC-Project/Retrieval-based-Voice-Conversion-WebUI)

## References

- [Kokoro-82M on Hugging Face](https://huggingface.co/hexgrad/Kokoro-82M)
- [AllTalk TTS](https://github.com/erew123/alltalk_tts)
- [RVC (Retrieval-based Voice Conversion)](https://github.com/RVC-Project/Retrieval-based-Voice-Conversion-WebUI)
