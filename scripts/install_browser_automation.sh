#!/bin/bash
# Install Browser Automation Dependencies
# This script installs Playwright and necessary system automation libraries

echo "============================================"
echo "Installing Browser Automation Dependencies"
echo "============================================"

echo ""
echo "[1/3] Installing Python packages..."
python3 -m pip install playwright psutil pyautogui

echo ""
echo "[2/3] Installing Playwright browsers..."
echo "This will download Chromium, Firefox, and WebKit browsers"
playwright install

echo ""
echo "[3/3] Verifying installation..."
python3 -c "from playwright.sync_api import sync_playwright; print('Playwright installed successfully!')"

echo ""
echo "============================================"
echo "Installation complete!"
echo "============================================"
echo ""
echo "You can now use browser automation features:"
echo "- Navigate to websites"
echo "- Search Google"
echo "- Open Gmail and Google Drive"
echo "- Take screenshots"
echo "- Automate browser interactions"
echo ""
