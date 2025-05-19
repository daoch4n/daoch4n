#!/bin/bash

# This script creates a symbolic link from the Hugging Face cache directory
# to our downloaded Kokoro-82M model files.

# Define paths
HF_CACHE_DIR="/home/vi/.cache/huggingface/hub"
MODEL_DIR="models--hexgrad--Kokoro-82M"
SNAPSHOT_HASH="496dba118d1a58f5f3db2efc88dbdc216e0483fc89fe6e47ee1f2c53f18ad1e4"
SOURCE_MODEL_DIR="$(pwd)/models/kokoro"
ORIGINAL_MODEL_DIR="$HOME/alltalk_tts/models/kokoro"

# Check if the original model files exist
if [ ! -d "$ORIGINAL_MODEL_DIR" ]; then
    echo "Error: Original Kokoro-82M model files not found at $ORIGINAL_MODEL_DIR"
    echo "Please ensure the model files are downloaded to ~/alltalk_tts/models/kokoro/"
    exit 1
fi

# Create the models directory if it doesn't exist
if [ ! -d "$SOURCE_MODEL_DIR" ]; then
    echo "Creating models directory and setting up symbolic links..."
    mkdir -p "$(pwd)/models/kokoro"
    ln -sf "$ORIGINAL_MODEL_DIR"/* "$(pwd)/models/kokoro/"
fi

# Create the directory structure
mkdir -p "$HF_CACHE_DIR/$MODEL_DIR/snapshots/$SNAPSHOT_HASH"

# Create the refs.json file
echo "{\"snapshots\": {\"refs/main\": {\"sha\": \"$SNAPSHOT_HASH\"}}}" > "$HF_CACHE_DIR/$MODEL_DIR/refs.json"

# Create symbolic links for all files in the source directory
for file in "$SOURCE_MODEL_DIR"/*; do
    if [ -f "$file" ]; then
        ln -sf "$file" "$HF_CACHE_DIR/$MODEL_DIR/snapshots/$SNAPSHOT_HASH/$(basename "$file")"
        echo "Linked $(basename "$file")"
    fi
done

# Link the voices directory
if [ -d "$SOURCE_MODEL_DIR/voices" ]; then
    mkdir -p "$HF_CACHE_DIR/$MODEL_DIR/snapshots/$SNAPSHOT_HASH/voices"
    for voice_file in "$SOURCE_MODEL_DIR/voices"/*; do
        if [ -f "$voice_file" ]; then
            ln -sf "$voice_file" "$HF_CACHE_DIR/$MODEL_DIR/snapshots/$SNAPSHOT_HASH/voices/$(basename "$voice_file")"
            echo "Linked voices/$(basename "$voice_file")"
        fi
    done
fi

echo "Symbolic links created successfully!"
echo "The Kokoro-82M model files are now accessible to the Kokoro package."
