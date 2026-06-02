@echo off
chcp 65001 >nul
echo Installing Python dependencies...
py -3 -m pip install -r requirements.txt
echo.
echo Done. This Chrome edition does not install Playwright Chromium.
pause
