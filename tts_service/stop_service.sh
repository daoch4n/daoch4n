#!/bin/bash
# Script to stop the TTS service

# Check if the PID file exists
if [ -f tts_service.pid ]; then
    # Get the PID from the file
    PID=$(cat tts_service.pid)

    # Check if the process is running
    if ps -p $PID > /dev/null; then
        echo "Stopping TTS service (PID: $PID)..."
        kill $PID

        # Wait for the process to stop
        sleep 2

        # Check if the process is still running
        if ps -p $PID > /dev/null; then
            echo "Process is still running. Forcing termination..."
            kill -9 $PID
        fi

        echo "TTS service stopped."
    else
        echo "TTS service is not running (PID: $PID)."
    fi

    # Remove the PID file
    rm tts_service.pid
else
    # Try to find the process by name
    PID=$(pgrep -f "python3 app.py")

    if [ -n "$PID" ]; then
        echo "Stopping TTS service (PID: $PID)..."
        kill $PID

        # Wait for the process to stop
        sleep 2

        # Check if the process is still running
        if ps -p $PID > /dev/null; then
            echo "Process is still running. Forcing termination..."
            kill -9 $PID
        fi

        echo "TTS service stopped."
    else
        echo "TTS service is not running."
    fi
fi
