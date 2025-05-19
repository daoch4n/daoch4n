#!/bin/bash

# This script tests the Kokoro TTS engine using the main environment

# Set up the symbolic link to the Kokoro-82M model files
echo "Setting up symbolic link to Kokoro-82M model files..."
./setup_kokoro_symlink.sh

# Check if the main virtual environment exists
if [ ! -d ".venv/bin" ]; then
    echo "Error: Main virtual environment not found at .venv/bin"
    echo "Please create the virtual environment first"
    exit 1
fi

# Activate the main virtual environment
echo "Activating main virtual environment..."
source .venv/bin/activate

# Check if the Kokoro package is installed
if ! python -c "import kokoro" &> /dev/null; then
    echo "Error: Kokoro package not found in the main environment"
    echo "Please install it with: pip install kokoro"
    deactivate
    exit 1
fi

# Check if the Misaki package is installed
if ! python -c "import misaki" &> /dev/null; then
    echo "Warning: Misaki package not found in the main environment"
    echo "Japanese text processing may be limited"
    echo "Consider installing it with: pip install git+https://github.com/hexgrad/misaki.git"
fi

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

# Parse command line arguments
if [ "$1" == "--list" ] || [ "$1" == "-l" ]; then
    python tests/test_kokoro_tts.py --list-voices
    deactivate
    exit 0
fi

# Check if a specific voice is requested
if [ -n "$1" ]; then
    voice=$1
    text=${2:-"Hello, I'm testing the $voice voice from Kokoro-82M. [joy:0.8]"}
    test_voice "$voice" "$text"
    deactivate
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
