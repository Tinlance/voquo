@echo off
echo ============================================================
echo   AI VIDEO FACTORY - Windows 11 Setup
echo ============================================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Install from https://python.org
    pause
    exit /b 1
)
echo [OK] Python found

REM Check pip
pip --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] pip not found
    pause
    exit /b 1
)
echo [OK] pip found

REM Check FFmpeg
ffmpeg -version >nul 2>&1
if errorlevel 1 (
    echo.
    echo [WARNING] FFmpeg not found in PATH
    echo.
    echo  Please install FFmpeg manually:
    echo  1. Go to: https://www.gyan.dev/ffmpeg/builds/
    echo  2. Download: ffmpeg-release-essentials.zip
    echo  3. Extract to: C:\ffmpeg\
    echo  4. Add C:\ffmpeg\bin to your Windows PATH:
    echo     - Search "Environment Variables" in Start Menu
    echo     - Edit PATH variable
    echo     - Add new entry: C:\ffmpeg\bin
    echo  5. Restart this terminal and run setup.bat again
    echo.
    pause
    exit /b 1
)
echo [OK] FFmpeg found

echo.
echo Installing Python dependencies...
echo.

pip install kokoro-onnx soundfile numpy --quiet
echo [OK] kokoro-onnx installed

pip install openai-whisper --quiet
echo [OK] openai-whisper installed

pip install pytest --quiet
echo [OK] pytest installed

echo.
echo Creating required folders...
if not exist "backgrounds" mkdir backgrounds
if not exist "music" mkdir music
if not exist "output" mkdir output
if not exist "output\audio" mkdir output\audio
if not exist "output\sync" mkdir output\sync
if not exist "output\scenes" mkdir output\scenes
if not exist "tests" mkdir tests
echo [OK] Folders ready

echo.
echo ============================================================
echo   SETUP COMPLETE
echo ============================================================
echo.
echo NEXT STEPS:
echo.
echo  1. Add background videos to: backgrounds\
echo     Download free dark abstract loops:
echo     https://www.pexels.com/search/videos/dark%%20abstract/
echo.
echo  2. Add drone music to: music\
echo     Download free atmospheric tracks:
echo     https://www.youtube.com/audiolibrary
echo     (Search: "ambient drone" or "dark atmospheric")
echo.
echo  3. Run the pipeline:
echo     python pipeline.py
echo.
echo  4. Run tests first (recommended):
echo     python pipeline.py --test
echo.
echo  5. Your final video will be at:
echo     output\final.mp4
echo.
pause
