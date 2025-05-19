#!/bin/bash

# This script fixes the Kokoro virtual environment by ensuring all required packages are installed

echo "Fixing Kokoro virtual environment..."

# Activate the virtual environment
source .venv/kokoro-env/bin/activate

# Ensure pip is installed
python -m ensurepip --upgrade

# Install required packages
python -m pip install sounddevice
python -m pip install soundfile
python -m pip install pyyaml

# Install Misaki tokenizer for Japanese language support
python -m pip install git+https://github.com/hexgrad/misaki.git

# Install the project in development mode
python -m pip install -e .

echo "Virtual environment fixed successfully!"

# Deactivate the virtual environment
deactivate
