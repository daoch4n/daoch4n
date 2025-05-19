#!/bin/bash

# Start the TTS Service using Docker Compose

# Function to log messages
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    log "Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    log "Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Change to the TTS Service directory
cd tts_service || {
    log "Error: tts_service directory not found."
    exit 1
}

# Build and start the TTS Service
log "Building and starting the TTS Service..."
docker-compose up -d --build

# Check if the service is running
if [ $? -eq 0 ]; then
    log "TTS Service started successfully."
    log "The service is available at http://localhost:5000"
    log "You can test it with: python test_service.py"
else
    log "Error: Failed to start the TTS Service."
    exit 1
fi
