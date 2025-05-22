# Kokoro TTS Microservice

This directory contains the Flask-based Kokoro TTS microservice. It provides an HTTP API for generating speech using the Kokoro-82M TTS engine, primarily for Japanese.

For detailed information on features, API endpoints, setup, configuration, emotion handling, and client usage, please refer to the main project documentation:

*   **[Kokoro TTS Integration Guide](../../docs/kokoro_tts_integration.md)**

## Quick Start

### Using Docker (Recommended)

The service is designed to be run with Docker using the shell scripts located in the project's `kokoro` directory (one level above this `tts_service` directory):

*   **Start the service:**
    ```bash
    # From the project root directory
    ./kokoro/start_tts_service.sh 
    # Or, if you are in the kokoro directory: ./start_tts_service.sh
    ```
    This script builds the Docker image if necessary and starts the container. The service will typically be available at `http://localhost:5000` (or the port specified by the `TTS_SERVICE_PORT` environment variable).
*   **Stop the service:**
    ```bash
    # From the project root directory
    ./kokoro/stop_tts_service.sh
    ```
*   **View logs:**
    ```bash
    # Check docker-compose.yml if you customized the service name from the default 'kokoro_tts_service'
    docker logs kokoro_tts_service
    ```

### Running Manually (for Development)

1.  **Prerequisites:**
    *   Python 3.8+
    *   MeCab (Japanese morphological analyzer) and its dictionaries (e.g., `ipadic-utf8` or `unidic-lite`). Ensure MeCab is correctly configured on your system.
    *   System dependencies like `swig` might be required for some Python packages.
    (See the main `docs/kokoro_tts_integration.md` for more detailed MeCab setup examples).

2.  **Install Python Dependencies:**
    Navigate to this directory (`kokoro/tts_service`) and run:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Environment Variables (Optional):**
    The service can be configured using these environment variables:
    *   `FLASK_DEBUG`: Set to `True` for Flask debug mode, or `False` for production mode. Defaults to `True`. **Important: Set to `False` in production.**
    *   `TTS_SERVICE_PORT`: The port on which the service will listen. Defaults to `5000`.

4.  **Run the Service:**
    From this `kokoro/tts_service` directory:
    ```bash
    python app.py
    ```
    The service will start on `0.0.0.0` at the configured port.

## API and Configuration

All details regarding API endpoints (`/tts`, `/voices`, `/health`, `/config`), request/response formats, emotion handling, configuration options, and client usage examples are centralized in:

*   **[Kokoro TTS Integration Guide](../../docs/kokoro_tts_integration.md)**

Please consult that document for comprehensive information.

**Security Note for `/config` endpoint:** As mentioned in the main documentation, the POST functionality of the `/config` endpoint should be secured or disabled in production environments.

## Testing the Service

A test script is provided in this directory to interact with the service's API:
```bash
python test_service.py --text "こんにちは、テストです。[joy:0.8]"
```
Use `python test_service.py --help` for more options.

## Client Library Example
A Python client library (`TTSServiceClient`) is available in the main application for programmatic interaction:

```python
from open_llm_vtuber.tts.tts_service_client import TTSServiceClient

# Create a client
client = TTSServiceClient(base_url="http://localhost:5000")

# Check if the service is healthy
if client.health_check():
    # Get available voices
    voices = client.get_available_voices()
    print(f"Available voices: {voices}")
    
    # Generate speech
    output_path = client.generate_speech(
        text="こんにちは、私はダオコです。[joy:0.8]",
        voice="jf_alpha"
    )
    print(f"Generated audio file: {output_path}") # Note: TTSServiceClient saves to file by default.
```

## Troubleshooting

For troubleshooting tips, including MeCab issues, Docker log inspection, and manual run issues, please refer to the troubleshooting sections in the:

*   **[Kokoro TTS Integration Guide](../../docs/kokoro_tts_integration.md)**

If you encounter issues with MeCab, make sure it's properly installed and the dictionary is available:

```bash
# Check MeCab installation
mecab -v

# Check MeCab dictionary
mecab -D
```

### Audio Generation Issues

If you encounter issues with audio generation, check the logs:

```bash
docker-compose logs
```

Or if running manually:

```bash
cat tts_service.log
```
