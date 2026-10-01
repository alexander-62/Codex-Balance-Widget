@echo off
setlocal
cd /d "%~dp0"
echo Installing Python dependencies...
py -3 -m pip install -r requirements.txt
if errorlevel 1 (
    echo Installation failed. Check that Python 3.10+ and Windows Python Launcher are installed.
    pause
    exit /b 1
)
echo.
echo Done. Run run.bat to start the widget.
echo The shared library is included. Playwright Chromium is not required.
pause
