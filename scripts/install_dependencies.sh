#!/bin/bash

# Voice Assistant Baseline - Dependency Installation Script
# Cross-platform installation for Windows (Git Bash), macOS, and Linux

set -e  # Exit on error

echo "=========================================="
echo "Voice Assistant - Dependency Installation"
echo "=========================================="
echo ""

# Detect OS
OS="unknown"
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    OS="windows"
fi

echo "Detected OS: $OS"
echo ""

# Check Python version
echo "Checking Python version..."
PYTHON_VERSION=$(python --version 2>&1 | awk '{print $2}')
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 10 ]); then
    echo "ERROR: Python 3.10+ is required. Found: $PYTHON_VERSION"
    exit 1
fi

echo "✓ Python $PYTHON_VERSION detected"
echo ""

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python -m venv venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi
echo ""

# Activate virtual environment
echo "Activating virtual environment..."
if [ "$OS" == "windows" ]; then
    source venv/Scripts/activate
else
    source venv/bin/activate
fi
echo "✓ Virtual environment activated"
echo ""

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip setuptools wheel
echo "✓ pip upgraded"
echo ""

# Install system dependencies based on OS
echo "Installing system dependencies..."
if [ "$OS" == "linux" ]; then
    echo "Linux detected - installing portaudio and other dependencies..."
    if command -v apt-get &> /dev/null; then
        sudo apt-get update
        sudo apt-get install -y portaudio19-dev python3-pyaudio ffmpeg
    elif command -v yum &> /dev/null; then
        sudo yum install -y portaudio-devel python3-pyaudio ffmpeg
    else
        echo "WARNING: Could not detect package manager. Please install portaudio manually."
    fi
elif [ "$OS" == "macos" ]; then
    echo "macOS detected - installing portaudio and other dependencies..."
    if command -v brew &> /dev/null; then
        brew install portaudio ffmpeg
    else
        echo "WARNING: Homebrew not found. Please install portaudio manually."
        echo "Visit: https://brew.sh/"
    fi
elif [ "$OS" == "windows" ]; then
    echo "Windows detected - system dependencies should be installed via pip"
    echo "If you encounter audio issues, install ffmpeg manually:"
    echo "https://ffmpeg.org/download.html"
fi
echo "✓ System dependencies processed"
echo ""

# Install Python dependencies
echo "Installing Python dependencies from requirements.txt..."
pip install -r requirements.txt
echo "✓ Python dependencies installed"
echo ""

# Install Playwright browsers
echo "Installing Playwright browsers..."
playwright install chromium
echo "✓ Playwright chromium browser installed"
echo ""

# Create necessary directories
echo "Creating necessary directories..."
mkdir -p logs data models/wake_word
echo "✓ Directories created"
echo ""

# Copy environment template if .env doesn't exist
if [ ! -f "config/.env" ]; then
    echo "Creating .env file from template..."
    cp config/.env.template config/.env
    echo "✓ .env file created"
    echo ""
    echo "⚠️  IMPORTANT: Edit config/.env and add your API keys!"
else
    echo "✓ .env file already exists"
fi
echo ""

# Summary
echo "=========================================="
echo "Installation Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Edit config/.env and add your API keys"
echo "2. Run: ./scripts/setup_wake_word.sh"
echo "3. Activate virtual environment:"
if [ "$OS" == "windows" ]; then
    echo "   source venv/Scripts/activate"
else
    echo "   source venv/bin/activate"
fi
echo "4. Run: python src/cli/assistant.py"
echo ""
echo "For more information, see:"
echo "  - specs/001-voice-assistant-baseline/quickstart.md"
echo "  - README.md"
echo ""
