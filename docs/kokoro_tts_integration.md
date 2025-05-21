# Kokoro-82M TTS Integration with Live2D Character (Daoko)

This document describes the integration of the Kokoro-82M speech synthesis model with the Live2D character (Daoko) in the project, primarily focusing on the **recommended TTS Microservice approach**.

The Kokoro-82M model is an open-weight TTS model. This integration allows Daoko to speak using the Kokoro-82M voice model, with appropriate emotional inflections.

For details on direct integration (legacy/alternative method), refer to the [Kokoro TTS Setup Guide](kokoro_tts_setup.md).

## Overview of Integration Methods
1.  **TTS Microservice (Recommended):** Involves running Kokoro TTS as a separate service. The main application communicates with this service. This is the preferred method for stability and ease of use.
2.  **Direct Integration (Legacy/Alternative):** Involves integrating the Kokoro TTS library directly into the main application. Setup and details for this method are covered in [Kokoro TTS Setup Guide](kokoro_tts_setup.md).

This document will now focus on the **TTS Microservice** integration.

The Kokoro-82M model is an open-weight TTS model with 82 million parameters. Despite its lightweight architecture, it delivers comparable quality to larger models while being significantly faster and more cost-efficient. With Apache-licensed weights, Kokoro can be deployed anywhere from production environments to personal projects.

This integration allows Daoko to speak using the Kokoro-82M voice model, with appropriate emotional inflections that match her current emotional state.

## Features

- High-quality speech synthesis with the Kokoro-82M model
- Emotion-aware speech synthesis that matches Daoko's emotional state
- Integration with the existing emotion system for facial expressions and body motions
- Support for multiple languages (primarily English)
- Efficient performance suitable for real-time applications

## TTS Microservice: Installation and Setup

This section details how to set up and run the Kokoro TTS microservice.

### Prerequisites for Running the Microservice

1.  **Docker and Docker Compose:** Required to build and run the microservice. Installation instructions can be found on the official Docker website.
2.  **Kokoro-82M Model Files:** The microservice needs access to the Kokoro-82M model files.
    *   Ensure Git LFS is installed:
        ```bash
        sudo apt-get update && sudo apt-get install -y git-lfs
        git lfs install
        ```
    *   The model files should be located at `~/alltalk_tts/models/kokoro/`. If you have downloaded them via Hugging Face caching to a different location, you may need to create symbolic links. The `docs/kokoro_tts_setup.md` document refers to a `./setup_kokoro_symlink.sh` script that can help manage this by linking from the Hugging Face cache to the expected directory. It's recommended to ensure the model files are correctly placed or linked at `~/alltalk_tts/models/kokoro/` for the microservice to access them.

### Running the TTS Microservice

1.  **Start the TTS Service:**
    A script is provided to manage the TTS service:
    ```bash
    ./start_tts_service.sh
    ```
    This script typically handles building the Docker image (if not already built) and running the service using `docker-compose`. Refer to the script's contents or `tts_service/docker-compose.yml` for more details if needed.

## TTS Microservice: Configuration

To use the TTS microservice, the main application needs to be configured to communicate with it. This is typically done in the main application's configuration file (e.g., `conf.yaml`).

### Configuring the Main Application to Use the TTS Microservice

Set the following parameters in your application's configuration:
```yaml
tts_config:
  tts_model: 'tts_service' # Specifies that the microservice should be used

  # TTS Service configuration (client-side)
  tts_service:
    base_url: "http://localhost:5000"  # URL of the running TTS Microservice
    # Other client-specific parameters can be added here if needed
```

---

## Legacy / Alternative: Direct Integration

For information on directly integrating the Kokoro TTS library into the main application (without a separate microservice), please refer to the [Kokoro TTS Setup Guide](kokoro_tts_setup.md). This guide covers:
- Detailed installation of necessary Python packages (`kokoro`, `misaki`, etc.)
- System dependencies for direct integration
- Configuration within the main application's `conf.yaml` for direct use (e.g., setting `tts_model: 'kokoro_tts'`)
- Usage patterns for direct library calls.

The following sections provide a brief overview of legacy configuration and usage for quick reference.

### Legacy Configuration (Direct Integration Overview)

When Kokoro TTS is integrated directly, it's configured in the main `conf.yaml` file.

**Key Configuration Parameters (for Direct Integration):**

- `tts_model`: Set to "kokoro_tts" to use the Kokoro TTS engine directly
- `voice`: The voice to use (recommended: "jf_alpha" for Daoko)
- `language`: The language code (recommended: "ja" for Japanese)
- `device`: The device to use for inference ("cuda" or "cpu")
- `emotion_mapping`: Mapping from emotion tags to Kokoro voice styles

Example configuration:
```yaml
tts_config:
  tts_model: 'kokoro_tts'

  kokoro_tts:
    voice: "jf_alpha"  # Japanese female voice for Daoko
    language: "ja"     # Japanese language
    device: "cpu"      # Use CPU to avoid CUDA version conflicts
    cache_dir: "cache"
    sample_rate: 24000
    output_format: "wav"
    emotion_mapping:
      joy: "happy"
      sadness: "sad"
      anger: "angry"
      fear: "fearful"
      surprise: "surprised"
      disgust: "disgusted"
      neutral: "neutral"
      smirk: "happy"
```


(Details on dependencies for direct integration can be found in [Kokoro TTS Setup Guide](kokoro_tts_setup.md).)

## TTS Microservice: Usage

Using the TTS microservice involves two main steps:

1.  **Ensure the TTS Microservice is Running:**
    As described in the "Installation and Setup" section, use:
    ```bash
    ./start_tts_service.sh
    ```

2.  **Configure the Main Application:**
    Ensure your main application's configuration points to the TTS microservice as shown in the "Configuration" section (i.e., `tts_model: 'tts_service'` and the correct `base_url`).

The main application will then automatically route TTS requests to the microservice.

---

### Legacy Usage (Direct Integration Overview)

To use the Kokoro TTS engine directly with Daoko (legacy method), set the TTS engine to "kokoro_tts" in your configuration file and provide the necessary parameters as detailed in [Kokoro TTS Setup Guide](kokoro_tts_setup.md). The main application then calls the Kokoro library functions directly.

### Emotion-Aware Speech Synthesis (TTS Microservice)

The TTS Microservice processes emotion tags (e.g., `[joy:0.8]`) found in the input text to modify speech characteristics. Here's how it works:

1.  **Tag Extraction:** The service identifies the first emotion tag in the text and extracts the emotion (e.g., "joy") and its intensity (e.g., 0.8). If no intensity is specified, it defaults to 1.0. All emotion tags are then removed from the text before it's sent to the Kokoro engine for phonemization and synthesis.
2.  **Speech Speed Adjustment:** The primary parameter affected is **speech speed**.
    *   The service uses an `emotion_mapping` in its configuration (see `kokoro/tts_service/app.py` for defaults, or configure via its `/config` endpoint). This mapping defines speed multipliers for different emotions (e.g., `joy: 1.2` means 20% faster, `sadness: 0.8` means 20% slower).
    *   An intensity threshold of `0.3` is applied. If the tag's intensity is below this, the speed is not changed.
    *   For intensities `0.3` and above, the effect is scaled. For example, `[joy:0.8]` would result in a speed closer to the full `1.2x` multiplier than `[joy:0.4]`.
3.  **Voice Style/Pitch:** The TTS Microservice **does not** currently change voice style (e.g., to a "happy voice") or pitch directly based on these emotion tags. The underlying Kokoro engine might have its own interpretation of any tags passed to it if they were not removed, but the service's explicit emotion handling is focused on speed.

The `emotion_mapping` for speed can be customized via the TTS service's `/config` endpoint. This allows fine-tuning how emotions translate to speech rate.

### Available Voices

The Kokoro-82M model comes with several built-in voices. For Daoko, we recommend using the Japanese female voices:

#### Japanese Female Voices (Recommended for Daoko)
- `jf_alpha` (Japanese female voice - recommended for Daoko)
- `jf_gongitsune` (Japanese female voice)
- `jf_nezumi` (Japanese female voice)
- `jf_tebukuro` (Japanese female voice)

#### Chinese Female Voices
- `zf_xiaobei` (Chinese female voice)
- `zf_xiaoni` (Chinese female voice)
- `zf_xiaoxiao` (Chinese female voice)
- `zf_xiaoyi` (Chinese female voice)

For a complete list of available voices, refer to the [Kokoro-82M documentation](https://huggingface.co/hexgrad/Kokoro-82M/blob/main/VOICES.md).

## Integration with Emotion System (TTS Microservice)

When using the TTS Microservice, the process integrates with Daoko's emotion system as follows:

1.  The main application sends text potentially containing emotion tags (e.g., `Hello [joy:0.8]!`) to the TTS Microservice.
2.  The TTS Microservice:
    *   Extracts the emotion (e.g., "joy") and intensity (e.g., 0.8).
    *   Adjusts the **speech speed** based on this emotion and intensity, using its configured `emotion_mapping`.
    *   Removes the emotion tags from the text.
    *   Generates audio from the cleaned text using the adjusted speed with the selected Kokoro voice.
3.  The main application receives the audio from the TTS Microservice.
4.  Separately, the main application likely parses the same emotion tags from the original text to control Daoko's facial expressions and body motions concurrently with audio playback.

This creates a cohesive experience where Daoko's speech rate and visual emotional display are synchronized. Note that the "emotional inflection" in the speech from the TTS service is primarily a change in speed.

This creates a cohesive experience where Daoko's speech, facial expressions, and body motions all match the emotional content of the conversation.

## Troubleshooting

This section is now prioritized for the TTS Microservice. For troubleshooting direct integration, please refer to [Kokoro TTS Setup Guide](kokoro_tts_setup.md).

### TTS Microservice Troubleshooting

(For common issues related to direct integration, such as CUDA errors, Python package dependencies, or general audio quality adjustments not specific to the microservice, please refer to the troubleshooting section in the [Kokoro TTS Setup Guide](kokoro_tts_setup.md).)

#### Model Files Not Found by Microservice
If the microservice logs indicate issues loading model files:
- Verify that the Kokoro-82M model files are present at `~/alltalk_tts/models/kokoro/`.
- If you use a different download location (e.g., Hugging Face cache), ensure symbolic links are correctly set up to point to `~/alltalk_tts/models/kokoro/`. The `./setup_kokoro_symlink.sh` script mentioned in `docs/kokoro_tts_setup.md` can be useful.
- Check the `docker-compose.yml` for the TTS service to see how it mounts or expects model files. Ensure these paths align with your setup.

#### TTS Service Issues

(MeCab and detailed Japanese text processing issues are primarily relevant to direct integration setup or development of the service itself. Please refer to the troubleshooting section in the [Kokoro TTS Setup Guide](kokoro_tts_setup.md) for guidance on these topics.)

If you encounter issues with the TTS Service (e.g., it's not responding, errors in speech generation):

(The `./test_tts.sh` script is primarily for testing direct Kokoro library integration. For testing the running TTS service, use the `tts_service/test_service.py` script as shown below.)

#### Testing the TTS Service

```bash
# List available voices
./test_tts.sh --list-voices

# Test with Japanese female alpha voice (recommended for Daoko)
./test_tts.sh --voice jf_alpha

# Test with a specific text
./test_tts.sh --voice jf_alpha --text "こんにちは、私はダオコです。よろしくお願いします。[joy:0.8]"
```

### New Troubleshooting (Microservice Approach)

#### TTS Service Issues

If you encounter issues with the TTS Service, check the Docker logs:

```bash
docker-compose -f tts_service/docker-compose.yml logs
```

#### Testing the TTS Service

You can test the TTS Service using the provided test script:

```bash
cd tts_service
python test_service.py --text "こんにちは、私はダオコです。よろしくお願いします。[joy:0.8]"
```

#### Checking TTS Service Health

You can check if the TTS Service is healthy:

```bash
curl http://localhost:5000/health
```

#### Logs

Check the logs for any error messages related to the TTS Service. The logs can provide valuable information for troubleshooting issues.

## References

- [Kokoro-82M on Hugging Face](https://huggingface.co/hexgrad/Kokoro-82M)
- [Kokoro GitHub Repository](https://github.com/hexgrad/kokoro)
- [StyleTTS 2 Paper](https://arxiv.org/abs/2306.07691)
- [ISTFTNet Paper](https://arxiv.org/abs/2203.02395)
