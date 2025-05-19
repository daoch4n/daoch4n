#!/bin/bash

# Unified TTS testing script for Open-LLM-VTuber
# This script consolidates functionality from multiple test scripts and adds
# command-line flags for different functionalities.

# Default values
TTS_ENGINE="kokoro"
VOICE=""
TEXT=""
OUTPUT=""
LIST_VOICES=false
PLAY_AUDIO=true
VERBOSE=false
HELP=false
RVC_ENABLED=false
RVC_MODEL=""
RVC_PITCH=0

# Parse command-line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --engine|-e)
            TTS_ENGINE="$2"
            shift 2
            ;;
        --voice|-v)
            VOICE="$2"
            shift 2
            ;;
        --text|-t)
            TEXT="$2"
            shift 2
            ;;
        --output|-o)
            OUTPUT="$2"
            shift 2
            ;;
        --list-voices|-l)
            LIST_VOICES=true
            shift
            ;;
        --no-play|-n)
            PLAY_AUDIO=false
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --rvc-enabled)
            RVC_ENABLED=true
            shift
            ;;
        --rvc-model)
            RVC_MODEL="$2"
            shift 2
            ;;
        --rvc-pitch)
            RVC_PITCH="$2"
            shift 2
            ;;
        --help|-h)
            HELP=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Display help message
if [ "$HELP" = true ]; then
    echo "Unified TTS Testing Script for Open-LLM-VTuber"
    echo ""
    echo "Usage: ./test_tts.sh [options]"
    echo ""
    echo "Options:"
    echo "  --engine, -e ENGINE    TTS engine to use (kokoro, alltalk) [default: kokoro]"
    echo "  --voice, -v VOICE      Voice to use for TTS"
    echo "  --text, -t TEXT        Text to synthesize"
    echo "  --output, -o OUTPUT    Output file name (without extension)"
    echo "  --list-voices, -l      List available voices and exit"
    echo "  --no-play, -n          Don't attempt to play the audio"
    echo "  --verbose              Show verbose output"
    echo "  --rvc-enabled          Enable RVC voice conversion (for alltalk engine)"
    echo "  --rvc-model MODEL      RVC model to use for voice conversion"
    echo "  --rvc-pitch PITCH      Pitch adjustment for RVC voice conversion [default: 0]"
    echo "  --help, -h             Show this help message and exit"
    echo ""
    echo "Examples:"
    echo "  ./test_tts.sh --list-voices                  # List all available voices"
    echo "  ./test_tts.sh --voice jf_alpha               # Test Japanese female alpha voice (recommended for Daoko)"
    echo "  ./test_tts.sh --voice jf_gongitsune          # Test Japanese female gongitsune voice"
    echo "  ./test_tts.sh --voice zf_xiaobei             # Test Chinese female xiaobei voice"
    echo "  ./test_tts.sh --engine alltalk --rvc-enabled --rvc-model \"daoko[24]_16hs_1bs_SPLICED_NPROC_40k_v1\" # Test with RVC"
    echo ""
    exit 0
fi

# Function to log messages
log() {
    if [ "$VERBOSE" = true ]; then
        echo "$1"
    fi
}

# Function to check if a Python package is installed
is_package_installed() {
    python -c "import $1" &> /dev/null
    return $?
}

# Function to set up Kokoro TTS
setup_kokoro() {
    # Check if symlinks already exist
    HF_CACHE_DIR="/home/vi/.cache/huggingface/hub"
    MODEL_DIR="models--hexgrad--Kokoro-82M"
    SNAPSHOT_HASH="496dba118d1a58f5f3db2efc88dbdc216e0483fc89fe6e47ee1f2c53f18ad1e4"

    if [ -d "$HF_CACHE_DIR/$MODEL_DIR/snapshots/$SNAPSHOT_HASH" ]; then
        log "Kokoro model symlinks already exist, skipping setup."
    else
        log "Setting up symbolic links to Kokoro-82M model files..."
        ./setup_kokoro_symlink.sh
    fi

    # Check if we're using the main environment or the kokoro-specific environment
    if [ -d ".venv/bin" ]; then
        log "Using main virtual environment..."
        source .venv/bin/activate

        # Check if required packages are installed
        if ! is_package_installed "kokoro"; then
            log "Installing Kokoro package..."
            uv pip install kokoro
        fi

        if ! is_package_installed "misaki"; then
            log "Installing Misaki tokenizer..."
            uv pip install git+https://github.com/hexgrad/misaki.git

            # Install additional dependencies for Misaki
            uv pip install spacy
            python -m spacy download en_core_web_sm
        fi

        # Install pyopenjtalk for Japanese voice support
        if ! is_package_installed "pyopenjtalk"; then
            log "Installing pyopenjtalk for Japanese voice support..."
            uv pip install pyopenjtalk
        fi

        # Install fugashi for Japanese text processing
        if ! is_package_installed "fugashi"; then
            log "Installing fugashi for Japanese text processing..."
            uv pip install fugashi
        fi

        # Install jaconv for Japanese text conversion
        if ! is_package_installed "jaconv"; then
            log "Installing jaconv for Japanese text conversion..."
            uv pip install jaconv
        fi

        # Install mojimoji for Japanese character conversion
        if ! is_package_installed "mojimoji"; then
            log "Installing mojimoji for Japanese character conversion..."
            uv pip install mojimoji
        fi

        # Install the project in development mode if needed
        if ! is_package_installed "open_llm_vtuber"; then
            log "Installing project in development mode..."
            uv pip install -e .
        fi
    else
        # Use the kokoro-specific environment
        if [ ! -d ".venv/kokoro-env" ]; then
            log "Creating Kokoro-specific virtual environment..."
            python -m venv .venv/kokoro-env
        fi

        log "Activating Kokoro-specific virtual environment..."
        source .venv/kokoro-env/bin/activate

        # Check if required packages are installed
        if ! is_package_installed "kokoro" || ! is_package_installed "misaki"; then
            log "Installing required packages..."
            ./fix_kokoro_env.sh
        fi
    fi
}

# Function to set up AllTalk TTS
setup_alltalk() {
    # Check if we're using the main environment
    if [ -d ".venv/bin" ]; then
        log "Using main virtual environment..."
        source .venv/bin/activate
    else
        # Create and use a new virtual environment
        if [ ! -d ".venv/alltalk-env" ]; then
            log "Creating AllTalk-specific virtual environment..."
            python -m venv .venv/alltalk-env
        fi

        log "Activating AllTalk-specific virtual environment..."
        source .venv/alltalk-env/bin/activate

        # Install required packages
        log "Installing required packages..."
        pip install requests
        pip install -e .
    fi
}

# Function to test Kokoro TTS
test_kokoro() {
    # Make sure the cache directory exists
    mkdir -p cache

    # Set up default text if not provided
    if [ -z "$TEXT" ]; then
        if [[ "$VOICE" == jf_* ]]; then
            # Japanese text for Japanese voices
            TEXT="こんにちは、私はダオコです。よろしくお願いします。[joy:0.8]"
        elif [[ "$VOICE" == zf_* ]]; then
            # Chinese text for Chinese voices
            TEXT="你好，我是道子。很高兴认识你！[joy:0.8]"
        else
            # Default to Japanese text
            TEXT="こんにちは、私はダオコです。よろしくお願いします。[joy:0.8]"
        fi
    fi

    # Set up command-line arguments for the Python script
    ARGS=""

    if [ "$LIST_VOICES" = true ]; then
        ARGS="--list-voices"
    else
        if [ -n "$VOICE" ]; then
            ARGS="$ARGS --voice $VOICE"
        fi

        if [ -n "$TEXT" ]; then
            ARGS="$ARGS --text \"$TEXT\""
        fi

        if [ -n "$OUTPUT" ]; then
            ARGS="$ARGS --output $OUTPUT"
        fi

        if [ "$PLAY_AUDIO" = false ]; then
            ARGS="$ARGS --no-play"
        fi
    fi

    # Run the test script
    log "Running Kokoro TTS test with arguments: $ARGS"
    eval "python tests/test_kokoro_tts.py $ARGS"
}

# Function to test AllTalk TTS
test_alltalk() {
    # Make sure the cache directory exists
    mkdir -p cache

    # Set up default text if not provided
    if [ -z "$TEXT" ]; then
        TEXT="Hello, this is a test of the AllTalk TTS integration."
    fi

    # Set up command-line arguments for the Python script
    ARGS=""

    if [ -n "$VOICE" ]; then
        ARGS="$ARGS --voice $VOICE"
    fi

    if [ -n "$TEXT" ]; then
        ARGS="$ARGS --text \"$TEXT\""
    fi

    if [ -n "$OUTPUT" ]; then
        ARGS="$ARGS --output $OUTPUT"
    fi

    # Add RVC parameters if enabled
    if [ "$RVC_ENABLED" = true ]; then
        ARGS="$ARGS --rvc-enabled"

        if [ -n "$RVC_MODEL" ]; then
            # Remove quotes from RVC_MODEL for the command line
            RVC_MODEL_CLEAN=$(echo "$RVC_MODEL" | tr -d '"')
            ARGS="$ARGS --rvc-model \"$RVC_MODEL_CLEAN\""
        fi

        if [ -n "$RVC_PITCH" ]; then
            ARGS="$ARGS --rvc-pitch $RVC_PITCH"
        fi
    fi

    # Run the test script
    log "Running AllTalk TTS test with arguments: $ARGS"
    eval "python tests/test_alltalk_tts.py $ARGS"
}

# Main execution
log "Starting TTS test with engine: $TTS_ENGINE"

# Set up the appropriate TTS engine
case $TTS_ENGINE in
    kokoro)
        setup_kokoro
        test_kokoro
        ;;
    alltalk)
        setup_alltalk
        test_alltalk
        ;;
    *)
        echo "Unknown TTS engine: $TTS_ENGINE"
        echo "Supported engines: kokoro, alltalk"
        exit 1
        ;;
esac

# Deactivate the virtual environment
deactivate

log "TTS test completed successfully!"
