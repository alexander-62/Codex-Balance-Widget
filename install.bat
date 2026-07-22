@echo off
chcp 65001 >nul
echo Installing Python dependencies...
py -3 -m pip install -r requirements.txt
echo.
if not exist "%~dp0..\usage_widget_common\" (
    echo WARNING: usage_widget_common not found at "%~dp0..\usage_widget_common".
    echo This app requires the usage_widget_common repo to be cloned as a
    echo sibling of this repo ^(same parent folder^) before run.bat will work.
    echo See README.md / README.ru.md for details.
    echo.
)
echo Done. This Chrome edition does not install Playwright Chromium.
pause
