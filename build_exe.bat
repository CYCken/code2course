@echo off
setlocal enabledelayedexpansion

echo === Code2Course Windows Build Script ===

REM Check for Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found. Please install Python 3.
    pause
    exit /b 1
)

REM Setup virtual environment for building
set "VENV_DIR=.pyinstaller_venv"
if not exist "%VENV_DIR%" (
    echo [1/5] Creating build virtual environment...
    python -m venv %VENV_DIR%
)

echo [2/5] Activating virtual environment...
call %VENV_DIR%\Scripts\activate.bat

echo [3/5] Installing PyInstaller and dependencies...
pip install -q pyinstaller
pip install -q -r requirements.txt

REM Check for ffmpeg
ffmpeg -version >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARNING] ffmpeg not found in PATH.
    echo Please make sure ffmpeg is installed and available in your PATH.
    echo You can download it from https://ffmpeg.org/download.html
) else (
    for /f "tokens=*" %%i in ('where ffmpeg') do set "FFMPEG_PATH=%%i"
    echo [OK] Found ffmpeg: !FFMPEG_PATH!
)

REM Create dist directory
if not exist "dist" mkdir dist

REM Clean old build files
echo [4/5] Cleaning old builds...
if exist "build" rd /s /q build
if exist "dist\code2course.exe" del /q dist\code2course.exe
if exist "dist\code2course" del /q dist\code2course

echo [5/5] Starting PyInstaller build...
pyinstaller --onefile ^
    --console ^
    --name code2course ^
    --add-data "code2course_config.example.json;." ^
    --add-data "code2course_style.example.json;." ^
    --add-data "code2course_prompt.example.txt;." ^
    --hidden-import google.generativeai ^
    --hidden-import questionary ^
    --hidden-import python_pptx ^
    --hidden-import moviepy ^
    --hidden-import moviepy.editor ^
    --hidden-import imageio ^
    --hidden-import imageio_ffmpeg ^
    --hidden-import numpy ^
    --hidden-import decorator ^
    --hidden-import requests ^
    --hidden-import urllib3 ^
    --hidden-import certifi ^
    --hidden-import charset_normalizer ^
    --hidden-import idna ^
    --hidden-import PIL ^
    --hidden-import pillow ^
    --hidden-import websockets ^
    --hidden-import aiohttp ^
    --hidden-import python_dotenv ^
    --hidden-import pydub ^
    --collect-all moviepy ^
    --collect-all edge_tts ^
    --collect-all imageio ^
    --collect-all python_dotenv ^
    main.py

echo [DONE] Build finished!

REM Copy config files
copy code2course_config.example.json dist\code2course_config.json
copy code2course_style.example.json dist\code2course_style.json

REM Create run scripts
echo Creating run.bat...
(
echo @echo off
echo chcp 65001 ^>nul
echo cd /d "%%~dp0"
echo echo === Code2Course Runner ===
echo set "EXE_NAME=code2course.exe"
echo set "EXE_PATH=%%~dp0%%EXE_NAME%%"
echo if not exist "%%EXE_PATH%%" ^(
echo     set "EXE_NAME=code2course"
echo     set "EXE_PATH=%%~dp0code2course"
echo ^)
echo if exist "%%EXE_PATH%%" ^(
echo     echo [OK] Found executable: %%EXE_NAME%%
echo     echo [RUN] Starting program...
echo     "%%EXE_PATH%%" %%*
echo ^) else ^(
echo     echo [ERROR] Could not find executable: code2course.exe or code2course
echo     echo Please make sure you are running this from the extracted dist folder.
echo     pause
echo     exit /b 1
echo ^)
echo pause
) > dist\run.bat

echo [SUCCESS] Distribution files are in the 'dist' folder.
pause
