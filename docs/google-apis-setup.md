# Google APIs Setup Guide (Gmail & Drive)

## Overview

Phase 2 adds **real** Gmail and Google Drive functionality via official Google APIs:
- **Gmail API**: Read, search, and send emails programmatically
- **Google Drive API**: List, search, download, and upload files
- **OAuth2**: Secure authentication with auto-refresh tokens

This guide walks you through setting up Google Cloud credentials and authenticating your Voice Assistant.

---

## Prerequisites

- Google Account (Gmail)
- Voice Assistant Phase 1 installed
- Internet connection

---

## Step 1: Install Google API Dependencies

```bash
# Windows
pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client

# macOS/Linux
pip3 install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client
```

---

## Step 2: Create Google Cloud Project

### 2.1 Go to Google Cloud Console
1. Visit: https://console.cloud.google.com/
2. Sign in with your Google Account
3. Click **"Select a project"** → **"New Project"**

### 2.2 Create Project
- **Project Name**: `Voice Assistant` (or your preferred name)
- Click **"CREATE"**
- Wait for project creation (~30 seconds)

---

## Step 3: Enable APIs

### 3.1 Enable Gmail API
1. In Google Cloud Console, go to **"APIs & Services"** → **"Library"**
2. Search for **"Gmail API"**
3. Click on **"Gmail API"**
4. Click **"ENABLE"**

### 3.2 Enable Google Drive API
1. In the API Library, search for **"Google Drive API"**
2. Click on **"Google Drive API"**
3. Click **"ENABLE"**

---

## Step 4: Create OAuth2 Credentials

### 4.1 Configure OAuth Consent Screen
1. Go to **"APIs & Services"** → **"OAuth consent screen"**
2. Select **"External"** (unless you have a Google Workspace account)
3. Click **"CREATE"**

4. Fill in required fields:
   - **App name**: `Voice Assistant`
   - **User support email**: Your email
   - **Developer contact email**: Your email
5. Click **"SAVE AND CONTINUE"**

6. **Scopes** (Click "ADD OR REMOVE SCOPES"):
   - Search and add:
     - `gmail.readonly`
     - `gmail.send`
     - `gmail.modify`
     - `drive.readonly`
     - `drive.file`
     - `drive.metadata.readonly`
   - Click **"UPDATE"**
   - Click **"SAVE AND CONTINUE"**

7. **Test Users** (Add yourself):
   - Click **"ADD USERS"**
   - Enter your Gmail address
   - Click **"ADD"**
   - Click **"SAVE AND CONTINUE"**

8. Review and click **"BACK TO DASHBOARD"**

### 4.2 Create OAuth2 Client ID
1. Go to **"APIs & Services"** → **"Credentials"**
2. Click **"+ CREATE CREDENTIALS"** → **"OAuth client ID"**
3. **Application type**: Select **"Desktop app"**
4. **Name**: `Voice Assistant Desktop`
5. Click **"CREATE"**

6. **Download credentials**:
   - In the popup, click **"DOWNLOAD JSON"**
   - Save the file

---

## Step 5: Install Credentials

### 5.1 Rename and Move Credentials File

```bash
# Windows (PowerShell)
Move-Item -Path "C:\Users\YourName\Downloads\client_secret_*.json" -Destination "F:\Voice_Assistant\config\google_credentials.json"

# macOS/Linux
mv ~/Downloads/client_secret_*.json ~/Voice_Assistant/config/google_credentials.json
```

**IMPORTANT**: The file **must** be named `google_credentials.json` and placed in the `config/` directory.

### 5.2 Verify File Placement

```bash
# Windows
dir F:\Voice_Assistant\config\google_credentials.json

# macOS/Linux
ls ~/Voice_Assistant/config/google_credentials.json
```

You should see the file listed. If not, check the download location and try again.

---

## Step 6: First-Time Authentication

### 6.1 Start Backend Server

```bash
# Terminal 1: Start backend
cd F:\Voice_Assistant
python -m uvicorn src.api.websocket_server:app --host 0.0.0.0 --port 8000
```

### 6.2 Trigger OAuth Flow

Use any Gmail or Drive command via voice or web interface:

```
Voice: "List my emails"
```

**OR** test via Python:

```python
cd F:\Voice_Assistant
python -c "from src.services.google_auth import get_google_auth; auth = get_google_auth(); auth.get_credentials()"
```

### 6.3 Complete OAuth Flow

1. **Browser Opens Automatically** at `http://localhost:8080`
2. Click **"Choose an account"** → Select your Google Account
3. **Warning Screen**: Click **"Advanced"** → **"Go to Voice Assistant (unsafe)"**
   - *(This appears because the app isn't verified - it's YOUR app, so it's safe)*
4. **Permissions Screen**: Check all boxes → Click **"Continue"**
5. **Success**: Browser shows "Authentication successful! You can close this window."

### 6.4 Verify Token Saved

```bash
# Windows
dir F:\Voice_Assistant\config\google_token.json

# macOS/Linux
ls ~/Voice_Assistant/config/google_token.json
```

You should see `google_token.json` file created. This stores your access/refresh tokens.

---

## Step 7: Test Gmail & Drive

### Test Gmail

```bash
# Start services if not running
python -m uvicorn src.api.websocket_server:app --host 0.0.0.0 --port 8000

# In web interface (http://localhost:3000), say:
"List my emails"
"Search for emails from john"
"Read my latest email"
```

### Test Google Drive

```
Voice: "List my Drive files"
Voice: "Search for report.pdf in Drive"
Voice: "Download file from Drive"
```

---

## Voice Commands

### Gmail Commands

| Command | Action |
|---------|--------|
| "List my emails" | Lists 10 recent emails with subjects and senders |
| "Show unread emails" | Lists only unread messages |
| "Search for emails from john@example.com" | Searches emails from specific sender |
| "Search emails with subject invoice" | Searches by subject |
| "Read email" | Reads full email content |
| "Send email to john@example.com" | Composes and sends email (requires confirmation) |

### Google Drive Commands

| Command | Action |
|---------|--------|
| "List my Drive files" | Lists 10 most recent files |
| "Search for report.pdf in Drive" | Searches by filename |
| "Search for documents about project" | Full-text search |
| "Download file from Drive" | Downloads file (requires file ID) |
| "Upload file to Drive" | Uploads local file (requires confirmation) |

---

## Troubleshooting

### Issue: "Credentials file not found"

**Solution**:
1. Verify file is at `F:\Voice_Assistant\config\google_credentials.json`
2. Check filename is exactly `google_credentials.json`
3. Re-download from Google Cloud Console if needed

### Issue: "OAuth flow doesn't open browser"

**Solution**:
```python
# Manual OAuth flow
python -c "
from src.services.google_auth import get_google_auth
auth = get_google_auth()
creds = auth.get_credentials()
print('Authentication successful!')
"
```

### Issue: "Token expired"

**Solution**:
Tokens auto-refresh! If you see this error:
1. Delete `config/google_token.json`
2. Re-run OAuth flow (Step 6)

### Issue: "Access blocked: This app isn't verified"

**Solution**:
1. Click **"Advanced"**
2. Click **"Go to Voice Assistant (unsafe)"**
3. This is YOUR app on YOUR computer - it's safe!

### Issue: "Insufficient permissions"

**Solution**:
1. Go to Google Account settings: https://myaccount.google.com/permissions
2. Remove "Voice Assistant" access
3. Re-run OAuth flow with all scopes checked

---

## Security & Privacy

### Where are credentials stored?

- **Client credentials**: `config/google_credentials.json` (OAuth2 client ID/secret)
- **Access tokens**: `config/google_token.json` (auto-refreshing tokens)

### Can the assistant access all my emails?

**Scopes granted**:
- `gmail.readonly`: Read emails
- `gmail.send`: Send emails
- `gmail.modify`: Mark as read/unread

**What it CANNOT do**:
- ❌ Delete emails
- ❌ Modify email content
- ❌ Access contacts
- ❌ Change account settings

### Revoking access

```python
# Programmatic revocation
python -c "from src.services.google_auth import get_google_auth; auth = get_google_auth(); auth.revoke_credentials()"

# OR delete token manually
rm config/google_token.json  # Linux/macOS
del config\google_token.json  # Windows

# OR revoke via Google Account
# Visit: https://myaccount.google.com/permissions
```

---

## Advanced Configuration

### Custom Scopes

Edit `src/services/google_auth.py`:

```python
GMAIL_SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',  # Read-only
    # 'https://www.googleapis.com/auth/gmail.send',    # Uncomment to send
]

DRIVE_SCOPES = [
    'https://www.googleapis.com/auth/drive.readonly',  # Read-only
    # 'https://www.googleapis.com/auth/drive.file',    # Uncomment to upload
]
```

### Using Service Account (Advanced)

For automated/server environments:
1. Create Service Account in Google Cloud Console
2. Download JSON key
3. Update `google_auth.py` to use service account credentials

---

## Next Steps

1. ✅ Install dependencies
2. ✅ Create Google Cloud project
3. ✅ Enable APIs
4. ✅ Create OAuth2 credentials
5. ✅ Complete first-time auth
6. ✅ Test Gmail & Drive commands

**You're ready!** Try voice commands and enjoy programmatic Gmail/Drive access!

---

## Support

**Common Issues**:
1. Credentials file placement
2. OAuth consent screen configuration
3. Scope permissions

**Resources**:
- Google Cloud Console: https://console.cloud.google.com/
- Gmail API Docs: https://developers.google.com/gmail/api
- Drive API Docs: https://developers.google.com/drive/api

**Need Help?**
Check troubleshooting section above or create an issue in the project repository.
