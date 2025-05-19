#!/bin/bash

# This script creates a symbolic link from the Hugging Face cache directory
# to our downloaded Kokoro-82M model files.

# Define paths
HF_CACHE_DIR="/home/vi/.cache/huggingface/hub"
MODEL_DIR="models--hexgrad--Kokoro-82M"
SNAPSHOT_HASH="496dba118d1a58f5f3db2efc88dbdc216e0483fc89fe6e47ee1f2c53f18ad1e4"
SOURCE_MODEL_DIR="$(pwd)/models/kokoro"
ORIGINAL_MODEL_DIR="$HOME/alltalk_tts/models/kokoro"
VERBOSE=${VERBOSE:-false}

# Function to log messages
log() {
    if [ "$VERBOSE" = true ]; then
        echo "$1"
    else
        # Only show important messages in non-verbose mode
        if [[ "$1" == "Error:"* || "$1" == "Symbolic links created"* ]]; then
            echo "$1"
        fi
    fi
}

# Check if symlinks already exist and are valid
if [ -d "$HF_CACHE_DIR/$MODEL_DIR/snapshots/$SNAPSHOT_HASH" ] && [ -f "$HF_CACHE_DIR/$MODEL_DIR/snapshots/$SNAPSHOT_HASH/config.json" ]; then
    log "Kokoro model symlinks already exist and appear valid. Skipping setup."
    exit 0
fi

# Check if the original model files exist
if [ ! -d "$ORIGINAL_MODEL_DIR" ]; then
    log "Error: Original Kokoro-82M model files not found at $ORIGINAL_MODEL_DIR"
    log "Please ensure the model files are downloaded to ~/alltalk_tts/models/kokoro/"
    exit 1
fi

# Create the models directory if it doesn't exist
if [ ! -d "$SOURCE_MODEL_DIR" ]; then
    log "Creating models directory and setting up symbolic links..."
    mkdir -p "$(pwd)/models/kokoro"
    ln -sf "$ORIGINAL_MODEL_DIR"/* "$(pwd)/models/kokoro/"
else
    log "Models directory already exists, checking for files..."
    # Check if we need to update the symlinks
    if [ ! "$(ls -A "$SOURCE_MODEL_DIR")" ]; then
        log "Models directory is empty, creating symlinks..."
        ln -sf "$ORIGINAL_MODEL_DIR"/* "$(pwd)/models/kokoro/"
    fi
fi

# Create the directory structure
mkdir -p "$HF_CACHE_DIR/$MODEL_DIR/snapshots/$SNAPSHOT_HASH"

# Create the refs.json file
if [ ! -f "$HF_CACHE_DIR/$MODEL_DIR/refs.json" ]; then
    log "Creating refs.json file..."
    echo "{\"snapshots\": {\"refs/main\": {\"sha\": \"$SNAPSHOT_HASH\"}}}" > "$HF_CACHE_DIR/$MODEL_DIR/refs.json"
fi

# Create symbolic links for all files in the source directory
log "Creating symbolic links for model files..."
for file in "$SOURCE_MODEL_DIR"/*; do
    if [ -f "$file" ]; then
        target="$HF_CACHE_DIR/$MODEL_DIR/snapshots/$SNAPSHOT_HASH/$(basename "$file")"
        if [ ! -L "$target" ] || [ ! -e "$target" ]; then
            ln -sf "$file" "$target"
            log "Linked $(basename "$file")"
        else
            log "Link for $(basename "$file") already exists, skipping."
        fi
    fi
done

# Link the voices directory
if [ -d "$SOURCE_MODEL_DIR/voices" ]; then
    mkdir -p "$HF_CACHE_DIR/$MODEL_DIR/snapshots/$SNAPSHOT_HASH/voices"
    log "Creating symbolic links for voice files..."
    for voice_file in "$SOURCE_MODEL_DIR/voices"/*; do
        if [ -f "$voice_file" ]; then
            target="$HF_CACHE_DIR/$MODEL_DIR/snapshots/$SNAPSHOT_HASH/voices/$(basename "$voice_file")"
            if [ ! -L "$target" ] || [ ! -e "$target" ]; then
                ln -sf "$voice_file" "$target"
                log "Linked voices/$(basename "$voice_file")"
            else
                log "Link for voices/$(basename "$voice_file") already exists, skipping."
            fi
        fi
    done
fi

log "Symbolic links created successfully!"
log "The Kokoro-82M model files are now accessible to the Kokoro package."
