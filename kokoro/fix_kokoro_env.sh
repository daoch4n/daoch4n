#!/bin/bash

# This script fixes the Kokoro virtual environment by ensuring all required packages are installed
VERBOSE=${VERBOSE:-false}

# Function to log messages
log() {
    if [ "$VERBOSE" = true ]; then
        echo "$1"
    else
        # Only show important messages in non-verbose mode
        if [[ "$1" != "Package"* ]]; then
            echo "$1"
        fi
    fi
}

log "Fixing Kokoro virtual environment..."

# Activate the virtual environment
source .venv/kokoro-env/bin/activate

# Check and fix MeCab configuration
check_mecab_config

# Function to check if a Python package is installed
is_package_installed() {
    python -c "import $1" &> /dev/null
    return $?
}

# Function to check and fix MeCab configuration
check_mecab_config() {
    log "Checking MeCab configuration..."

    # Check if MeCab is installed
    if ! command -v mecab &> /dev/null; then
        log "MeCab is not installed. Installing..."
        sudo apt-get update && sudo apt-get install -y mecab libmecab-dev mecab-ipadic-utf8
    fi

    # Check if MeCab configuration file exists
    if [ ! -f "/usr/local/etc/mecabrc" ]; then
        log "MeCab configuration file not found. Creating..."
        sudo mkdir -p /usr/local/etc
        echo "dicdir = /var/lib/mecab/dic/ipadic-utf8" | sudo tee /usr/local/etc/mecabrc
    fi

    # Test MeCab
    if ! echo "テスト" | mecab &> /dev/null; then
        log "MeCab test failed. Trying to fix..."
        # Try to find the dictionary directory
        DICT_DIR=$(find /var/lib/mecab -name "ipadic*" -type d | head -n 1)
        if [ -n "$DICT_DIR" ]; then
            log "Found dictionary at $DICT_DIR. Updating configuration..."
            echo "dicdir = $DICT_DIR" | sudo tee /usr/local/etc/mecabrc
        else
            log "Could not find MeCab dictionary. Please install it manually."
        fi
    else
        log "MeCab is working correctly."
    fi
}

# Ensure pip is installed
log "Checking pip installation..."
python -m ensurepip --upgrade

# Install required packages if not already installed
install_if_needed() {
    package=$1
    import_name=${2:-$1}

    if ! is_package_installed "$import_name"; then
        log "Installing package: $package"
        python -m pip install $package
    else
        log "Package $import_name is already installed, skipping."
    fi
}

# Install required packages
install_if_needed sounddevice
install_if_needed soundfile
install_if_needed pyyaml yaml

# Install Misaki tokenizer for Japanese language support if not already installed
if ! is_package_installed "misaki"; then
    log "Installing Misaki tokenizer..."
    python -m pip install git+https://github.com/hexgrad/misaki.git
else
    log "Misaki tokenizer is already installed, skipping."
fi

# Install pyopenjtalk for Japanese voice support
if ! is_package_installed "pyopenjtalk"; then
    log "Installing pyopenjtalk for Japanese voice support..."
    python -m pip install pyopenjtalk
else
    log "pyopenjtalk is already installed, skipping."
fi

# Install MeCab and fugashi for Japanese text processing
if ! is_package_installed "fugashi"; then
    log "Installing MeCab and fugashi for Japanese text processing..."
    # Run the setup_mecab.sh script
    ./setup_mecab.sh
else
    log "fugashi is already installed, skipping."
fi

# Patch misaki.cutlet to use GenericTagger
log "Patching misaki.cutlet to use GenericTagger..."
python patch_misaki.py

# Install jaconv for Japanese text conversion
if ! is_package_installed "jaconv"; then
    log "Installing jaconv for Japanese text conversion..."
    python -m pip install jaconv
else
    log "jaconv is already installed, skipping."
fi

# Install mojimoji for Japanese character conversion
if ! is_package_installed "mojimoji"; then
    log "Installing mojimoji for Japanese character conversion..."
    python -m pip install mojimoji
else
    log "mojimoji is already installed, skipping."
fi

# Install the project in development mode if not already installed
if ! is_package_installed "open_llm_vtuber"; then
    log "Installing project in development mode..."
    python -m pip install -e .
else
    log "Project is already installed in development mode, skipping."
fi

log "Virtual environment fixed successfully!"

# Deactivate the virtual environment
deactivate
