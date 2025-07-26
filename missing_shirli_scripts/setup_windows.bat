@echo off
echo Setting up Music Link Automation for Windows...
echo.

REM Create virtual environment
echo Creating virtual environment...
python -m venv music_env

REM Check if virtual environment was created successfully
if not exist "music_env\Scripts\activate.bat" (
    echo ERROR: Failed to create virtual environment
    echo Trying with py command instead...
    py -m venv music_env
)

if not exist "music_env\Scripts\activate.bat" (
    echo ERROR: Could not create virtual environment
    echo Please check your Python installation
    pause
    exit /b 1
)

echo Virtual environment created successfully!
echo.

REM Activate virtual environment
echo Activating virtual environment...
call music_env\Scripts\activate.bat

REM Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip

REM Install required packages
echo Installing required packages...
pip install gspread>=5.7.0
pip install google-auth>=2.16.0
pip install google-auth-oauthlib>=0.8.0
pip install google-auth-httplib2>=0.1.0
pip install spotipy>=2.22.1
pip install google-api-python-client>=2.70.0

echo.
echo Setup complete!
echo.
echo To activate the environment in the future, run:
echo music_env\Scripts\activate.bat
echo.
echo To run the music automation script:
echo python music_linker.py
echo.
pause
