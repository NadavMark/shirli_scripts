@echo off
echo Testing Google Sheets connection...
echo.

REM Check if virtual environment exists
if not exist "music_env\Scripts\activate.bat" (
    echo ERROR: Virtual environment not found!
    echo Please run setup_windows.bat first
    pause
    exit /b 1
)

REM Activate virtual environment and test connection
call music_env\Scripts\activate.bat

echo Creating quick connection test...
python -c "
import gspread
from google.oauth2.service_account import Credentials
import json

try:
    # Load credentials
    with open('credentials.json', 'r') as f:
        creds_data = json.load(f)
    
    print('✅ Credentials file loaded')
    print(f'📧 Service account email: {creds_data.get(\"client_email\", \"Not found\")}')
    
    # Test connection
    scopes = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive.file',
        'https://www.googleapis.com/auth/drive'
    ]
    
    creds = Credentials.from_service_account_file('credentials.json', scopes=scopes)
    client = gspread.authorize(creds)
    
    print('✅ Authorization successful')
    print('📋 You can now run the main script!')
    
except FileNotFoundError:
    print('❌ credentials.json not found')
    print('Please make sure the file is in this folder')
except Exception as e:
    print(f'❌ Error: {e}')
    print('Please check the setup guide')
"

echo.
pause
