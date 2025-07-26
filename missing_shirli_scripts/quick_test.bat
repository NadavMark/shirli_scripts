@echo off
echo Quick Connection Test
echo ====================
echo.

REM Check if files exist
if not exist "credentials.json" (
    echo ❌ credentials.json not found
    echo Please make sure you have downloaded your Google credentials file
    echo and renamed it to "credentials.json"
    pause
    exit /b 1
)

if not exist "music_env\Scripts\activate.bat" (
    echo ❌ Virtual environment not found
    echo Please run setup_windows.bat first
    pause
    exit /b 1
)

echo ✅ Files found, testing connection...
echo.

call music_env\Scripts\activate.bat

python -c "
import json
import sys

try:
    # Show service account email
    with open('credentials.json', 'r') as f:
        creds = json.load(f)
    
    email = creds.get('client_email', 'Not found')
    print('📧 Your service account email is:')
    print(f'   {email}')
    print()
    print('🔧 To fix permission issues:')
    print('1. Open your Google Sheet')
    print('2. Click Share button')
    print('3. Add this email address')
    print('4. Give it Editor permission')
    print('5. Click Send')
    print()
    
except Exception as e:
    print(f'❌ Error reading credentials: {e}')
    sys.exit(1)

# Test basic import
try:
    import gspread
    from google.oauth2.service_account import Credentials
    print('✅ Required packages are installed')
except ImportError as e:
    print(f'❌ Missing package: {e}')
    print('Please run setup_windows.bat')
    sys.exit(1)
"

echo.
echo Test complete!
pause
