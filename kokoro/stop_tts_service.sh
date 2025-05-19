#!/bin/bash

# Stop the TTS Service

# Function to log messages
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Change to the TTS Service directory
cd tts_service || {
    log "Error: tts_service directory not found."
    exit 1
}

# Stop the TTS Service
log "Stopping the TTS Service..."
docker-compose down

# Check if the service was stopped
if [ $? -eq 0 ]; then
    log "TTS Service stopped successfully."
else
    log "Error: Failed to stop the TTS Service."
    exit 1
fi
