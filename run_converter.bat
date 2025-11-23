@echo off
title CAPPS XML Converter for AIMsi

echo ========================================
echo    CAPPS XML Converter for AIMsi POS
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.6 or later from python.org
    echo.
    pause
    exit /b 1
)

REM Run the GUI application
echo Starting CAPPS Converter...
pythonw capps_converter_gui.py

if errorlevel 1 (
    echo.
    echo ERROR: Failed to start the converter
    echo Make sure all required files are in the same folder:
    echo   - capps_converter_gui.py
    echo   - csv_to_capps_xml.py
    echo.
    pause
)
