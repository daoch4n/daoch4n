#!/bin/bash
# Script to start the TTS service directly on the system

# Create output and cache directories if they don't exist
mkdir -p output
mkdir -p cache

# Check if the service is already running
if pgrep -f "python app.py" > /dev/null; then
    echo "TTS service is already running."
    exit 0
fi

# Start the TTS service in the background
echo "Starting the TTS service..."
nohup python3 app.py > tts_service.log 2>&1 &

# Save the PID to a file for later use
echo $! > tts_service.pid

# Wait for the service to start
echo "Waiting for the TTS service to start..."
sleep 5

# Check if the service is running
if curl -s http://localhost:5000/health > /dev/null; then
    echo "TTS service is running."
    echo "You can access the service at http://localhost:5000"
    echo "To stop the service, run ./stop_service.sh"
else
    echo "TTS service failed to start. Check the logs in tts_service.log."
    exit 1
fi
