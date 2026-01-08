#!/bin/bash
# Install Google APIs Dependencies (Gmail & Drive)
# This script installs Google Auth and API client libraries

echo "============================================"
echo "Installing Google APIs Dependencies"
echo "============================================"

echo ""
echo "[1/2] Installing Python packages..."
python3 -m pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client

echo ""
echo "[2/2] Verifying installation..."
python3 -c "import google.auth; import googleapiclient.discovery; print('✓ Google APIs installed successfully!')"

echo ""
echo "============================================"
echo "Installation complete!"
echo "============================================"
echo ""
echo "Next steps:"
echo "1. Set up Google Cloud project (see docs/google-apis-setup.md)"
echo "2. Download OAuth2 credentials"
echo "3. Save credentials as config/google_credentials.json"
echo "4. Run first-time authentication"
echo ""
echo "You can now use Gmail and Google Drive APIs:"
echo "- List and read emails"
echo "- Search emails"
echo "- Send emails"
echo "- List Drive files"
echo "- Download/upload files"
echo ""
