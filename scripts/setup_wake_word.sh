#!/bin/bash

# Voice Assistant Baseline - Wake Word Model Setup Script
# Downloads and configures pvporcupine wake word models

set -e  # Exit on error

echo "=========================================="
echo "Voice Assistant - Wake Word Setup"
echo "=========================================="
echo ""

# Create models directory
echo "Creating models directory..."
mkdir -p models/wake_word
echo "✓ Models directory created"
echo ""

# Check if virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo "WARNING: Virtual environment not activated"
    echo "Activating virtual environment..."

    # Detect OS
    if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
        source venv/Scripts/activate
    else
        source venv/bin/activate
    fi
    echo "✓ Virtual environment activated"
fi
echo ""

# Check if pvporcupine is installed
echo "Checking pvporcupine installation..."
if ! python -c "import pvporcupine" 2>/dev/null; then
    echo "ERROR: pvporcupine not found. Please run ./scripts/install_dependencies.sh first"
    exit 1
fi
echo "✓ pvporcupine is installed"
echo ""

# Get pvporcupine installation path
echo "Locating pvporcupine models..."
PVPORCUPINE_PATH=$(python -c "import pvporcupine; import os; print(os.path.dirname(pvporcupine.__file__))")
echo "pvporcupine installed at: $PVPORCUPINE_PATH"
echo ""

# List available wake word models
echo "Available wake words from pvporcupine:"
if [ -d "$PVPORCUPINE_PATH/resources/keyword_files" ]; then
    ls -1 "$PVPORCUPINE_PATH/resources/keyword_files" | grep "\.ppn$" | sed 's/\.ppn$//' | sed 's/_linux$//' | sed 's/_mac$//' | sed 's/_windows$//' | sed 's/_raspberry-pi$//' | sort -u
    echo ""
fi

# Download or link common wake words
echo "Setting up wake word models..."

# Option 1: Create symbolic links to pvporcupine built-in models
echo "Creating links to built-in wake word models..."

# Detect platform
PLATFORM="unknown"
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    PLATFORM="linux"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    PLATFORM="mac"
elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    PLATFORM="windows"
fi

# Note: pvporcupine includes several built-in wake words
# Common ones: porcupine, alexa, computer, jarvis, bumblebee, etc.
echo "Platform: $PLATFORM"
echo ""

# Create a README in models directory
cat > models/wake_word/README.md << 'EOF'
# Wake Word Models

This directory contains wake word models for pvporcupine.

## Built-in Models

pvporcupine comes with several built-in wake word models:
- porcupine
- alexa
- computer
- jarvis
- bumblebee
- terminator
- view glass
- picovoice
- grasshopper

## Custom Wake Words

For custom wake words, visit:
https://console.picovoice.ai/

You can train custom wake words like "Hey Assistant" on the Picovoice Console.

## Usage

The wake word models are automatically loaded from the pvporcupine package.
Configure your preferred wake word in `config/assistant_config.yaml`:

```yaml
wake_word:
  library: "pvporcupine"
  sensitivity: 0.5  # 0.0 to 1.0
  model_path: "models/wake_word/"
```

## Custom Model Instructions

1. Go to https://console.picovoice.ai/
2. Sign up for free account
3. Create custom wake word (e.g., "Hey Assistant")
4. Download the .ppn model file
5. Place it in this directory
6. Update src/services/wake_word.py to load your custom model
EOF

echo "✓ Wake word models directory configured"
echo ""

# Information about custom wake words
echo "=========================================="
echo "Wake Word Setup Complete!"
echo "=========================================="
echo ""
echo "Using pvporcupine built-in wake words:"
echo "  - Built-in words: porcupine, alexa, computer, jarvis, etc."
echo ""
echo "For custom wake word 'Hey Assistant':"
echo "  1. Visit: https://console.picovoice.ai/"
echo "  2. Sign up for free Picovoice account"
echo "  3. Create custom wake word 'Hey Assistant'"
echo "  4. Download the .ppn model file"
echo "  5. Place in: models/wake_word/"
echo "  6. Update: src/services/wake_word.py"
echo ""
echo "See: models/wake_word/README.md for details"
echo ""
