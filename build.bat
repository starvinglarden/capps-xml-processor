@echo off
title Building CAPPS Converter Executable
echo ========================================
echo    CAPPS Converter - Build Executable
echo ========================================
echo.

REM Check if PyInstaller is installed
python -c "import PyInstaller" >nul 2>&1
if errorlevel 1 (
    echo ERROR: PyInstaller is not installed
    echo Installing PyInstaller...
    pip install pyinstaller
    echo.
)

REM Clean previous builds
echo Cleaning previous builds...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist CAPPS-Converter.spec del CAPPS-Converter.spec
echo.

REM Build the executable
echo Building executable with PyInstaller...
echo This may take 1-2 minutes...
echo.

pyinstaller --onefile ^
    --windowed ^
    --name "CAPPS-Converter" ^
    --hidden-import csv_to_capps_xml ^
    --hidden-import tkinter ^
    --hidden-import queue ^
    --hidden-import threading ^
    capps_converter_gui.py

if errorlevel 1 (
    echo.
    echo ERROR: Build failed!
    echo Check the error messages above.
    pause
    exit /b 1
)

echo.
echo ========================================
echo    Build Complete!
echo ========================================
echo.
echo Executable location: dist\CAPPS-Converter.exe
echo File size:
dir dist\CAPPS-Converter.exe | find "CAPPS-Converter.exe"
echo.
echo Next steps:
echo 1. Test the executable: dist\CAPPS-Converter.exe
echo 2. If it works, upload to GitHub Release
echo 3. Send download link to GM
echo.
pause
