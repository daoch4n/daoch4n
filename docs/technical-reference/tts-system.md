# TTS System Documentation

This document provides comprehensive information about the Text-to-Speech (TTS) system integrations within the Open LLM VTuber project, focusing on the Kokoro-82M model via a dedicated microservice and its integration with AllTalk TTS for advanced voice conversion.

## Overview of TTS Integration Methods

The project utilizes the Kokoro-82M speech synthesis model, an open-weight TTS model with 82 million parameters, known for its quality, speed, and efficiency. There are two primary methods for integrating TTS:

1.  **TTS Microservice (Recommended for Kokoro-82M):** This involves running Kokoro TTS as a separate, containerized Flask application. The main application communicates with this service via HTTP requests, offloading TTS processing and dependency management. This is the preferred method for stability and ease of use, especially for Japanese voice synthesis.
2.  **AllTalk TTS Integration (for RVC Voice Conversion):** This method uses Kokoro-82M through the AllTalk TTS server, primarily to enable RVC (Retrieval-based Voice Conversion) functionality for specific characters like Daoko. AllTalk TTS provides a consistent API for different TTS engines and allows for voice conversion and emotion-aware speech.

This document will detail both approaches, with a primary focus on the recommended TTS Microservice.

## Kokoro-82M TTS Microservice Guide

This section is the primary guide for integrating the Kokoro-82M speech synthesis model using the **TTS Microservice approach**. This method is the recommended and standardized way to use Kokoro TTS within this project.

The TTS Microservice runs Kokoro TTS as a separate, containerized Flask application. The main application communicates with this service via HTTP requests, simplifying the main application by offloading TTS processing and dependency management.

### Features

-   High-quality speech synthesis using the Kokoro-82M model via a dedicated microservice.
-   Emotion-aware speech synthesis: The microservice adjusts speech **speed and volume** based on emotion tags in the text and its internal configuration.
-   Centralized TTS functionality, isolating complex dependencies.
-   Efficient performance with in-memory audio streaming.
-   Configurable via API for runtime adjustments.
-   Support for multiple Japanese female voices (jf_alpha, jf_gongitsune, jf_nezumi, jf_tebukuro).
-   Improved phoneme processing with MeCab integration.
-   Robust error handling and fallback mechanisms.
-   Simple start/stop scripts for service management.

### TTS Microservice: Installation and Setup

This section details how to set up and run the Kokoro TTS microservice.

1.  **Docker and Docker Compose:** Required to build and run the microservice using the recommended script-based approach. Installation instructions can be found on the official Docker website.
2.  **Kokoro-82M Model Files:** The microservice needs access to the Kokoro-82M model files.
    *   Ensure Git LFS is installed on your system:
        ```bash
        sudo apt-get update && sudo apt-get install -y git-lfs
        git lfs install
        ```
    *   The model files should be available at `~/alltalk_tts/models/kokoro/`. If you have downloaded them via Hugging Face caching to a different location, you may need to create symbolic links. The `./setup_kokoro_symlink.sh` script (located in the `kokoro` directory of this project) can help manage this.

#### Running the TTS Microservice (Docker - Recommended)

The easiest way to run the service is using the provided shell scripts from the project root directory:

*   **Start the service:**
    ```bash
    ./start_tts_service.sh
    ```
    This script typically handles building the Docker image (if it doesn't exist) and starting the container (usually via `docker-compose` from the `kokoro/tts_service` directory). The service will generally be available at `http://localhost:5000` or the port specified by the `TTS_SERVICE_PORT` environment variable.
*   **Stop the service:**
    ```bash
    ./stop_service.sh
    ```
*   **View logs:**
    Consult the `docker-compose.yml` in `kokoro/tts_service` if you need to check the service name for direct `docker logs <service_name>` commands, or use:
    ```bash
    docker logs kokoro_tts_service
    # (Or the specific name if start_service.sh uses a different one)
    ```

#### Running the TTS Microservice Manually (e.g., for Development)

If you need to run the service directly without Docker (e.g., for development or debugging the service itself):

1.  **Prerequisites for Manual Run:**
    *   Python 3.8+
    *   MeCab (Japanese morphological analyzer) and its dictionaries (e.g., `ipadic-utf8` or `unidic-lite`). Ensure MeCab is correctly configured. The service uses a utility (`open_llm_vtuber.utils.mecab_utils.get_mecab_tagger`) that attempts to find the dictionary via `mecabrc` or common fallback paths.
    *   System dependencies like `swig` might be required for some Python packages.
    *   Example for Debian/Ubuntu to install MeCab:
        ```bash
        sudo apt-get update && sudo apt-get install -y mecab libmecab-dev mecab-ipadic-utf8 swig
        ```

2.  **Install Python Dependencies:**
    Navigate to the `kokoro/tts_service` directory and install requirements:
    ```bash
    cd kokoro/tts_service
    pip install -r requirements.txt
    ```
    > **Note on versions:** The TTS service has been tested with `numpy==1.22.3`, `scipy==1.10.1`, and `torch==2.0.1`. If you encounter issues, ensure compatibility or use a virtual environment.

3.  **Environment Variables (Optional):**
    The service's behavior (`kokoro/tts_service/app.py`) can be modified with these environment variables:
    *   `FLASK_DEBUG`: Set to `True` for Flask debug mode, or `False` for production mode. Defaults to `True`. **Important: Set to `False` in production.**
    *   `TTS_SERVICE_PORT`: The port on which the service will listen. Defaults to `5000`.

4.  **Run the Application:**
    From the `kokoro/tts_service` directory:
    ```bash
    python app.py
    ```
    The service will start on `0.0.0.0` at the configured port.

### TTS Microservice: Main Application Configuration

To use the Kokoro TTS microservice, the main application needs to be configured to communicate with it. This is done in the main application's configuration file (e.g., `conf.yaml`):

```yaml
tts_config:
  tts_model: 'tts_service' # Specifies that the microservice should be used

  # TTS Service configuration (client-side)
  tts_service:
    base_url: "http://localhost:5000"  # URL of the running TTS Microservice
    # Other client-specific parameters like timeout can be added here if needed
```

### TTS Microservice API Details

The Kokoro TTS microservice provides the following HTTP endpoints:

#### 1. `/tts`

*   **Method:** `POST`
*   **Description:** Generates speech from input text.
*   **Request Body (JSON):**
    *   `text` (string, required): The text to be synthesized. Can include emotion tags like `[joy:0.8]`.
    *   `voice` (string, optional): The voice to use (e.g., "jf_alpha"). Defaults to "jf_alpha" or the service's configured default.
    *   `speed` (float, optional): Speech speed multiplier (e.g., 1.0 is normal, 0.5 is half speed, 2.0 is double speed). If provided, this value overrides any speed adjustment derived from emotion tags in the text.
    *   `volume` (float, optional): Speech volume multiplier (e.g., 1.0 is normal, 0.5 is half volume, 1.5 is 50% louder). If provided, this value overrides any volume adjustment derived from emotion tags.
*   **Response:**
    *   `200 OK`: WAV audio stream (`audio/wav`). The audio is streamed directly from memory.
    *   `400 Bad Request`: If the `text` parameter is missing or other input validation fails. JSON error response.
    *   `500 Internal Server Error`: If speech generation fails. JSON error response.
*   **Note on Streaming:** The service generates audio and streams it directly from memory, reducing disk I/O for faster responses.

#### 2. `/voices`

*   **Method:** `GET`
*   **Description:** Lists available voices that the service is configured to use (typically Japanese female voices like "jf_alpha").
*   **Response:**
    *   `200 OK`: JSON object with a "voices" array (e.g., `["jf_alpha", "jf_gongitsune"]`) and a "default" voice.
    *   `500 Internal Server Error`: If the TTS engine is not initialized or voice information cannot be retrieved.

#### 3. `/health`

*   **Method:** `GET`
*   **Description:** Provides a simple health check of the service.
*   **Response:**
    *   `200 OK`: JSON object `{"status": "ok"}` if the service is running.

#### 4. `/config`

*   **Method:** `GET`, `POST`
*   **Description:**
    *   `GET`: Retrieves the current configuration of the TTS service, including `device`, `repo_id`, `sample_rate`, `output_format`, and `emotion_mapping`.
    *   `POST`: Updates the TTS service configuration. The service will re-initialize the TTS pipeline if necessary after a configuration update.
*   **Request Body (JSON for POST):** A JSON object containing keys to be updated. Example:
    ```json
    {
        "device": "cuda",
        "emotion_mapping": {
            "joy": {"speed": 1.3, "volume": 1.1},
            "sadness": {"speed": 0.7, "volume": 0.8}
        }
    }
    ```
    Refer to `DEFAULT_CONFIG` in `kokoro/tts_service/app.py` for all configurable keys and the structure of `emotion_mapping`.
*   **Response:**
    *   `GET (200 OK)`: JSON object of the current configuration.
    *   `POST (200 OK)`: JSON object confirming the update and showing the new configuration.
    *   `POST (400 Bad Request)`: If POST data is missing.
    *   `POST (500 Internal Server Error)`: If the configuration update fails.
*   **Security Note:** In a production environment, it is **highly recommended to secure or disable the POST functionality of this endpoint** to prevent unauthorized changes to the service configuration.

### TTS Microservice: Client Usage

Interaction with the TTS microservice from the main application is typically handled by the `TTSServiceClient` (in `src/open_llm_vtuber/tts/tts_service_client.py`) or through the `TTSFactory`.

#### 1. Ensure the TTS Microservice is Running

Follow the steps in the "Running the TTS Microservice" section above.

#### 2. Configure the Main Application

Ensure your main application's `conf.yaml` (or equivalent configuration) points to the TTS microservice as detailed in the "TTS Microservice: Main Application Configuration" section.

#### 3. Client Examples

##### Using `TTSServiceClient` directly:

```python
from open_llm_vtuber.tts.tts_service_client import TTSServiceClient

client = TTSServiceClient(base_url="http://localhost:5000") # Or your configured service URL

if client.health_check():
    print("TTS Service is healthy.")
    voices = client.get_available_voices()
    print(f"Available voices: {voices}")

    # Example: Generate speech with an emotion tag
    # Note: TTSServiceClient.generate_speech saves to file by default.
    # For streaming/raw bytes, the client would need adjustment or direct requests used.
    audio_file_path = client.generate_speech(
        text="こんにちは、テストです。[joy:0.8]",
        voice="jf_alpha" # Optional, uses service default if not provided
    )
    if audio_file_path:
        print(f"Generated audio (saved to file): {audio_file_path}")
else:
    print("TTS Service is not responding.")
```
*(Note: The `TTSServiceClient.generate_speech` method currently saves to a file. For direct in-memory audio handling as the service now provides, the client would need adjustment or direct `requests` calls would be used by the application if raw bytes are needed.)*

##### Using `TTSFactory`:

The `TTSFactory` will automatically instantiate and use the `TTSServiceClient` when `tts_model` is set to `'tts_service'` in the main application configuration.

```python
from open_llm_vtuber.tts.tts_factory import TTSFactory
# Assuming main_app_config is loaded from conf.yaml

tts_engine_params = main_app_config.get("tts_config", {}).get("tts_service", {})
# TTSFactory expects engine_type as the first argument if not using config object directly
tts_engine = TTSFactory.get_tts_engine("tts_service", **tts_engine_params)

output_path = tts_engine.generate_audio("こんにちは、テストです.[joy:0.8]")
print(f"Generated audio (saved to file by default by client): {output_path}")
```

### Emotion-Aware Speech Synthesis (via TTS Microservice)

The TTS Microservice processes emotion tags (e.g., `[joy:0.8]`) found in the input text to modify speech characteristics:

1.  **Tag Extraction:** The service identifies the first emotion tag in the text, extracting the emotion (e.g., "joy") and intensity (e.g., 0.8). All emotion tags are then removed from the text before it's sent to the Kokoro engine.
2.  **Speech Parameter Adjustment (Speed and Volume):**
    *   The service uses an `emotion_mapping` in its configuration (viewable via `/config` GET endpoint; structure is `emotion: {"speed": X, "volume": Y}`). This mapping defines base `speed` and `volume` multipliers.
    *   An intensity threshold of `0.3` is applied. Below this, default speed (1.0) and volume (1.0) are used.
    *   For intensities `0.3` and above, the effect of the multipliers is scaled.
    *   These calculated speed and volume values can be **overridden** by explicit `speed` and/or `volume` parameters in the `/tts` API request.
3.  **Voice Style/Pitch:** The TTS Microservice **does not** currently change other voice style aspects or pitch based on these emotion tags beyond the described speed and volume adjustments.

The `emotion_mapping` for speed and volume can be customized via the TTS service's `/config` POST endpoint.

### SSML Support Status

The Kokoro TTS engine, as utilized through the current KPipeline library, **does not directly support SSML (Speech Synthesis Markup Language)**. The TTS service expects plain text, optionally augmented with the `[emotion:intensity]` tags as described. Implementing full SSML parsing and mapping its tags to available controls would require separate feature development within the TTS service itself.

### Available Voices (from Kokoro-82M via Microservice)

The Kokoro-82M model provides several voices. The TTS microservice typically exposes Japanese female voices by default:
- `jf_alpha` (Japanese female voice - often the default for Daoko)
- `jf_gongitsune` (Japanese female voice)
- `jf_nezumi` (Japanese female voice)
- `jf_tebukuro` (Japanese female voice)

Other voices available in the Kokoro-82M model (e.g., Chinese female voices like `zf_xiaobei`) could potentially be configured for use in the service if needed. For a complete list of base model voices, refer to the [Kokoro-82M documentation](https://huggingface.co/hexgrad/Kokoro-82M/blob/main/VOICES.md). The `/voices` endpoint of the service will list currently configured and available voices.

### Integration with Emotion System (using the TTS Microservice)

When using the TTS Microservice, the process integrates with a character's (e.g., Daoko) emotion system as follows:

1.  The main application sends text potentially containing emotion tags (e.g., `Hello [joy:0.8]!`) to the TTS Microservice. This request can also include explicit `speed` and `volume` parameters if direct control is desired, overriding emotion-derived values.
2.  The TTS Microservice:
    *   Extracts the emotion and intensity if tags are present.
    *   Determines the target speech speed and volume based on API parameters or (if not provided) the extracted emotion/intensity and the service's `emotion_mapping`.
    *   Removes the emotion tags from the text.
    *   Generates audio from the cleaned text using the determined speed and volume with the selected Kokoro voice.
3.  The main application receives the audio stream from the TTS Microservice.
4.  Separately, the main application likely parses the same emotion tags from the original text to control the character's facial expressions and body motions concurrently with audio playback.

This creates a cohesive experience where the character's speech characteristics (speed, volume) and visual emotional display are synchronized.

### Troubleshooting the TTS Microservice

#### Common Service Issues

*   **Service Not Responding / Health Check Fails (`curl http://localhost:5000/health`):**
    *   Ensure the service is running (using `./start_tts_service.sh` or `python kokoro/tts_service/app.py`).
    *   Check Docker logs (`docker logs kokoro_tts_service`) or the `tts_service.log` file in `kokoro/tts_service/` if running manually.
    *   **Port Conflicts:** Verify that the port the service is configured to use (default 5000, or via `TTS_SERVICE_PORT` env var) is not already in use by another application.
*   **Model Loading Errors (Service Side):**
    *   If service logs indicate issues loading model files (e.g., "FileNotFoundError"), verify that the Kokoro-82M model files are correctly located at `~/alltalk_tts/models/kokoro/`.
    *   If using symlinks (e.g., via `./setup_kokoro_symlink.sh`), ensure they point to the correct Hugging Face cache location.
    *   If running in Docker, check the volume mount configuration in `kokoro/tts_service/docker-compose.yml` to ensure it correctly maps the host model directory to the container's expected path.
*   **MeCab/Phonemization Issues (Service Side):**
    *   If Japanese text results in poor quality or errors, and service logs indicate "MeCab tagger could not be initialized" or similar, it means the service's MeCab setup (via `open_llm_vtuber.utils.mecab_utils.get_mecab_tagger`) failed.
    *   Ensure MeCab and a compatible dictionary (e.g., `ipadic-utf8` or `unidic-lite`) are correctly installed on the system where the service is running (or within the Docker container if it's not pre-configured).
    *   The service will fall back to a basic phoneme map if MeCab fails, which can reduce quality.
*   **Networking/Firewall:** If the main application cannot reach the TTS service (especially if on different machines or complex Docker networks), check firewall rules and network configurations.

#### Testing the Service

You can directly test the running TTS microservice using its dedicated test script:

```bash
cd kokoro/tts_service
python test_service.py --text "こんにちは、テストです.[joy:0.8] --speed 1.1 --volume 0.9"
# Use --help for more options on test_service.py
```
This script interacts with the service's HTTP API endpoints and can help diagnose issues.

#### Dependency Issues (Manual Setup)

If running the service manually (not via Docker) and encountering errors:
*   Ensure all Python packages listed in `kokoro/tts_service/requirements.txt` are installed in your Python environment.
*   Pay attention to specific versions if noted (e.g., `numpy==1.22.3`, `scipy==1.10.1`, `torch==2.0.1`). Create a virtual environment if needed.

### Related Files (TTS Microservice)

-   `src/open_llm_vtuber/tts/tts_service_client.py`: Python client library for communicating with the TTS Service.
-   `kokoro/tts_service/app.py`: Main Flask application for the TTS Service.
-   `kokoro/tts_service/docker-compose.yml`: Docker Compose configuration for the TTS Service.
-   `kokoro/tts_service/requirements.txt`: Python dependencies for the TTS Service.
-   `kokoro/tts_service/test_service.py`: Script for testing the TTS Service API.
-   `conf.yaml`: Main application configuration file.

## Kokoro-82M Integration with AllTalk TTS for Daoko

This section describes how to use the Kokoro-82M speech synthesis model through AllTalk TTS with RVC voice conversion for the Daoko Live2D character.

The Kokoro-82M model is used through AllTalk TTS to enable RVC (Retrieval-based Voice Conversion) functionality for Daoko. This approach provides several benefits:

1.  **Voice Conversion**: RVC allows us to convert the base voice to sound more like Daoko.
2.  **Emotion-Aware Speech**: The integration supports emotion tags for expressive speech.
3.  **Consistent API**: AllTalk TTS provides a consistent API for different TTS engines.

### Prerequisites (AllTalk TTS)

1.  **AllTalk TTS Server**: You need to have the AllTalk TTS server running locally.
2.  **Kokoro-82M Model**: The model files should be available at `~/alltalk_tts/models/kokoro/`.
3.  **RVC Model for Daoko**: The RVC model for Daoko should be available in the AllTalk TTS server.

### Configuration (AllTalk TTS)

To use Kokoro-82M through AllTalk TTS, you need to use the `alltalk_tts` engine in your configuration file. A sample configuration file is provided at `docs/conf/kokoro_alltalk_daoko.yaml`.

#### Key Configuration Parameters

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

### Emotion-Aware Speech Synthesis (via AllTalk TTS)

The AllTalk TTS integration supports emotion-aware speech synthesis by mapping emotion tags in the text to appropriate voice styles and pitch adjustments. For example, if the text contains the emotion tag `[joy:0.8]`, the AllTalk TTS engine will use a happy voice style with a higher pitch for that text.

The emotion mapping is defined in the configuration file and can be customized as needed.

#### How Emotions Affect Speech

Different emotions affect speech parameters in the following ways:

-   **Joy/Happiness**: Higher pitch (+2 semitones at maximum intensity), slightly faster speech.
-   **Sadness**: Lower pitch (-2 semitones at maximum intensity), slightly slower speech.
-   **Anger**: Slightly lower pitch (-1 semitone at maximum intensity).
-   **Fear**: Higher pitch (+3 semitones at maximum intensity).
-   **Surprise**: Higher pitch (+4 semitones at maximum intensity).
-   **Disgust**: Slightly lower pitch (-1 semitone at maximum intensity).
-   **Neutral**: Default pitch and speed.

#### RVC Pitch Adjustment

The pitch adjustment in RVC is measured in semitones (half-steps in musical terms):

-   **+12 semitones**: Raises the pitch by one octave (often used to convert a male voice to a female-sounding voice).
-   **-12 semitones**: Lowers the pitch by one octave (often used to convert a female voice to a male-sounding voice).
-   **0 semitones**: Keeps the pitch unchanged (suitable for same-gender conversions).

Since the RVC model is already trained on Daoko's voice, we use 0 as the base pitch and only apply subtle adjustments (between -2 and +4 semitones) for emotional variations.

#### Emotion Intensity

The intensity of the emotion (e.g., `[joy:0.8]` vs `[joy:0.3]`) affects how much these parameters are adjusted:

-   Intensities below 0.3 don't trigger pitch adjustments.
-   Intensities from 0.3 to 1.0 are mapped to proportional pitch adjustments.
-   Higher intensity values result in more pronounced adjustments.

For example, `[joy:1.0]` would apply the full +2 semitone adjustment, while `[joy:0.65]` would apply a +1 semitone adjustment (approximately).

### Troubleshooting (AllTalk TTS)

#### AllTalk TTS Server Not Running

If you encounter an error about the AllTalk TTS server not running, make sure the server is running at the specified URL (default: `http://127.0.0.1:7851`).

#### RVC Model Not Found

If you encounter an error about the RVC model not being found, make sure the model is available in the AllTalk TTS server. You can check the available RVC models by running:

```bash
curl http://127.0.0.1:7851/api/rvcmodels
```

#### Other Issues

If you encounter other issues, please check the logs for error messages and refer to the documentation for the specific TTS engine:

-   [AllTalk TTS](https://github.com/erew123/alltalk_tts)
-   [Kokoro-82M on Hugging Face](https://huggingface.co/hexgrad/Kokoro-82M)
-   [RVC (Retrieval-based Voice Conversion)](https://github.com/RVC-Project/Retrieval-based-Voice-Conversion-WebUI)

## Unified TTS Testing Guide

The project includes a unified TTS testing script (`test_tts.sh`) that consolidates functionality from multiple test scripts and adds command-line flags for different functionalities. This script makes it easy to test different TTS engines and voices without having to remember the specific commands for each engine.

### Usage

```bash
./test_tts.sh [options]
```

#### Options

-   `--engine, -e ENGINE`: TTS engine to use (e.g., alltalk) [default: alltalk]
-   `--voice, -v VOICE`: Voice to use for TTS (specific to the chosen engine)
-   `--text, -t TEXT`: Text to synthesize
-   `--output, -o OUTPUT`: Output file name (without extension)
-   `--list-voices, -l`: List available voices and exit
-   `--no-play, -n`: Don't attempt to play the audio
-   `--verbose`: Show verbose output
-   `--help, -h`: Show help message and exit

#### Examples

List all available voices:

```bash
./test_tts.sh --list-voices
```

Test AllTalk TTS with a specific voice:

```bash
./test_tts.sh --engine alltalk --voice en_US-ljspeech-high.onnx --text "Hello world"
```

Test AllTalk TTS with RVC:

```bash
./test_tts.sh --engine alltalk --voice en_US-ljspeech-high.onnx --rvc-enabled --rvc-model "your_rvc_model_name" --text "Testing RVC."
```

### Available TTS Engines (for `test_tts.sh`)

This script primarily supports engines that have a command-line interface or a test script that can be wrapped by `test_tts.sh`.

#### AllTalk TTS

The AllTalk TTS engine is a local text-to-speech system that supports voice cloning and RVC voice conversion.

##### Available Voices

-   `en_US-ljspeech-high.onnx` (default): English US voice
-   Other voices depend on your AllTalk TTS installation

### Emotion Tags (for `test_tts.sh`)

Emotion tags are generally handled by the specific TTS engine being called. This script passes the text through. For AllTalk TTS, it may interpret emotion tags based on its own configuration. Emotion tags are specified in square brackets and can include an optional intensity value:

```
Hello, I'm happy! [joy:0.8]
```

Available emotions:
- `joy`: Happy/excited
- `sadness`: Sad/downcast
- `anger`: Angry/frustrated
- `fear`: Fearful/anxious
- `surprise`: Surprised
- `disgust`: Disgusted
- `neutral`: Neutral (default)
- `smirk`: Mischievous/playful

### Output Files (for `test_tts.sh`)

Generated audio files are saved in the `cache` directory with the specified output name (or a default name if not specified) and the appropriate file extension (e.g., `.wav` or as specified by the underlying engine being tested).

### Troubleshooting (for `test_tts.sh`)

#### Package Installation Issues

If you encounter package installation issues when trying to run the script or a specific engine through it, ensure all dependencies for that engine are correctly installed. Try running the script with the `--verbose` flag to see more detailed output:

```bash
VERBOSE=true ./test_tts.sh --engine alltalk --text "Testing"
```

#### Other Issues

If you encounter other issues, please check the logs for error messages and refer to the documentation for the specific TTS engine you are attempting to test (e.g., AllTalk TTS).

## References

-   [Kokoro-82M on Hugging Face](https://huggingface.co/hexgrad/Kokoro-82M)
-   [Kokoro GitHub Repository (Original Engine)](https://github.com/hexgrad/kokoro)
-   [Misaki Tokenizer (Used with MeCab)](https://github.com/hexgrad/misaki)
-   [StyleTTS 2 Paper (Related Research)](https://arxiv.org/abs/2306.07691)
-   [ISTFTNet Paper (Related Research)](https://arxiv.org/abs/2203.02395)
-   [AllTalk TTS](https://github.com/erew123/alltalk_tts)
-   [RVC (Retrieval-based Voice Conversion)](https://github.com/RVC-Project/Retrieval-based-Voice-Conversion-WebUI)