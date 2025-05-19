#!/bin/bash

# This script installs and configures MeCab and fugashi for Japanese text processing

# Function to log messages
log() {
    echo "[setup_mecab] $1"
}

log "Setting up MeCab and fugashi for Japanese text processing..."

# Install MeCab and related packages
log "Installing MeCab and related packages..."
sudo apt-get update
sudo apt-get install -y mecab libmecab-dev mecab-ipadic-utf8 swig

# Create MeCab configuration directory if it doesn't exist
sudo mkdir -p /usr/local/etc

# Create a basic MeCab configuration file
log "Creating MeCab configuration file..."
echo "dicdir = /var/lib/mecab/dic/ipadic-utf8" | sudo tee /usr/local/etc/mecabrc

# Test MeCab
log "Testing MeCab..."
if echo "テスト" | mecab > /dev/null; then
    log "MeCab is working correctly."
else
    log "MeCab test failed. Trying to fix..."
    # Try to find the dictionary directory
    DICT_DIR=$(find /var/lib/mecab -name "ipadic*" -type d | head -n 1)
    if [ -n "$DICT_DIR" ]; then
        log "Found dictionary at $DICT_DIR. Updating configuration..."
        echo "dicdir = $DICT_DIR" | sudo tee /usr/local/etc/mecabrc
    else
        log "Could not find MeCab dictionary. Please install it manually."
    fi
fi

# Install fugashi with unidic-lite
log "Installing fugashi with unidic-lite..."
pip install fugashi[unidic-lite]
pip install unidic-lite

# Create a test script for fugashi
log "Creating test script for fugashi..."
cat > test_fugashi.py << 'EOF'
from fugashi import GenericTagger
import sys

# Initialize tagger with explicit dictionary type
tagger = GenericTagger('-d /var/lib/mecab/dic/ipadic-utf8')

# Test with a simple Japanese sentence
text = "こんにちは、私はダオコです。"
print("Testing fugashi with text:", text)

# Parse the text
words = tagger(text)

# Print the results
for word in words:
    print(f"Surface: {word.surface}, Feature: {word.feature}")

print("Fugashi test completed successfully!")
EOF

# Run the test script
log "Running fugashi test script..."
python test_fugashi.py

# If the test is successful, create a wrapper script for fugashi
log "Creating fugashi wrapper script..."
cat > fugashi_wrapper.py << 'EOF'
from fugashi import GenericTagger
import os

# Function to create a tagger with the correct dictionary
def create_tagger():
    # Try to find the MeCab dictionary
    mecabrc = "/usr/local/etc/mecabrc"
    if os.path.exists(mecabrc):
        with open(mecabrc, 'r') as f:
            for line in f:
                if line.startswith('dicdir'):
                    dicdir = line.split('=')[1].strip()
                    return GenericTagger(f'-d {dicdir}')
    
    # Fallback to ipadic-utf8
    return GenericTagger('-d /var/lib/mecab/dic/ipadic-utf8')

# Create a global tagger instance
tagger = create_tagger()

# Function to tokenize text
def tokenize(text):
    return tagger(text)
EOF

# Install the wrapper script
log "Installing fugashi wrapper script..."
sudo cp fugashi_wrapper.py /usr/local/lib/python3.10/dist-packages/

log "MeCab and fugashi setup completed successfully!"
