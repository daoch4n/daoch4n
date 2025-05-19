#!/bin/bash

# This script tests different voices available in the Kokoro-82M model

# Set up the symbolic link to the Kokoro-82M model files
echo "Setting up symbolic link to Kokoro-82M model files..."
./setup_kokoro_symlink.sh

# Fix the virtual environment
echo "Fixing virtual environment..."
./fix_kokoro_env.sh

# Activate the virtual environment
echo "Activating virtual environment..."
source .venv/kokoro-env/bin/activate

# Function to test a voice
test_voice() {
    local voice=$1
    local text=$2
    local output="voice_${voice}"

    echo "Testing voice: $voice"
    echo "Text: $text"
    echo "Output file: cache/${output}.wav"

    # Make sure the cache directory exists
    mkdir -p cache

    # Run the test script with the specified voice
    python tests/test_kokoro_tts.py --no-play --voice "$voice" --text "$text" --output "$output"

    # Verify the file was created
    if [ -f "cache/${output}.wav" ]; then
        echo "Successfully generated audio file: cache/${output}.wav"
    else
        echo "ERROR: Failed to generate audio file: cache/${output}.wav"
    fi

    echo "-----------------------------------"
}

# Check if the user wants to list available voices
if [ "$1" == "--list" ] || [ "$1" == "-l" ]; then
    python tests/test_kokoro_tts.py --list-voices
    exit 0
fi

# Check if a specific voice is requested
if [ -n "$1" ]; then
    voice=$1
    text=${2:-"Hello, I'm testing the $voice voice from Kokoro-82M. [joy:0.8]"}
    test_voice "$voice" "$text"
    exit 0
fi

# Default behavior: test all Japanese female voices
echo "Testing all Japanese female voices..."
echo "-----------------------------------"

test_voice "jf_alpha" "こんにちは、私はアルファです。よろしくお願いします。[joy:0.8]"
test_voice "jf_gongitsune" "こんにちは、私はゴンギツネです。よろしくお願いします。[joy:0.8]"
test_voice "jf_nezumi" "こんにちは、私はネズミです。よろしくお願いします。[joy:0.8]"
test_voice "jf_tebukuro" "こんにちは、私はテブクロです。よろしくお願いします。[joy:0.8]"

echo "All voice tests completed!"
echo "Audio files are saved in the cache directory."

# Deactivate the virtual environment
deactivate
