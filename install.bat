@echo off
chcp 65001 >nul
echo Installing Python dependencies...
py -3 -m pip install -r requirements.txt
echo.
if not exist "%~dp0..\usage_widget_common\" (
    echo WARNING: usage_widget_common not found at "%~dp0..\usage_widget_common".
    echo This app requires the usage_widget_common shared package as a
    echo sibling directory of this repo ^(same parent folder^) before
    echo run.bat will work. It is a local, unpublished package with no
    echo public git remote or PyPI listing -- it cannot be obtained via
    echo "git clone". See README.md / README.ru.md for how to get it.
    echo.
)
echo Done. This Chrome edition does not install Playwright Chromium.
pause
