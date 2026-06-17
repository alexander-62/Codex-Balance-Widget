# Technology Stack

**Analysis Date:** 2026-06-17

## Languages

**Primary:**
- Python 3.10+ - Windows desktop widget implementation in `codex_balance_widget_chrome.py` and hidden launcher wrapper in `codex_balance_widget_launcher.pyw`; the minimum version is documented in `README.md`.

**Secondary:**
- Windows Batch - Install and launch wrappers in `install.bat` and `run.bat`.
- VBScript - Hidden Windows Script Host launcher in `run_hidden.vbs`.
- Markdown - User documentation in `README.md` and `README.ru.md`.

## Runtime

**Environment:**
- Windows desktop runtime - The application uses Windows-specific Python modules and APIs in `codex_balance_widget_chrome.py`, including `msvcrt`, `ctypes.WinDLL("kernel32")`, `os.startfile`, and Tk window attributes.
- Python Launcher for Windows - `install.bat` runs `py -3 -m pip install -r requirements.txt`; `run_hidden.vbs` launches `pyw.exe -3` with `codex_balance_widget_launcher.pyw`.
- Google Chrome - Required external browser executable discovered by `find_chrome_executable()` in `codex_balance_widget_chrome.py`.

**Package Manager:**
- pip - Dependencies are installed from `requirements.txt` by `install.bat`.
- Lockfile: missing; `requirements.txt` uses minimum version constraints rather than pinned exact versions.

## Frameworks

**Core:**
- Tkinter - Built-in Python GUI toolkit used for the main widget window, settings window, diagnostics view, progress bars, and canvas charts in `codex_balance_widget_chrome.py`.
- Playwright Python `>=1.40` - Browser automation layer used from `playwright.async_api` in `codex_balance_widget_chrome.py` to control the user's installed Google Chrome.
- pystray `>=0.19.5` - Optional system tray integration used in `codex_balance_widget_chrome.py`; the widget continues without tray support when import fails.
- Pillow `>=10.0.0` - Optional tray icon rendering dependency used through `PIL.Image`, `PIL.ImageDraw`, and `PIL.ImageFont` in `codex_balance_widget_chrome.py`.

**Testing:**
- Not detected - No test framework dependency, test configuration, or test files are present in the repository.

**Build/Dev:**
- No build step - The app is run directly with Python via `py -3 codex_balance_widget_chrome.py`, `run.bat`, or `codex_balance_widget_launcher.pyw`.
- Playwright Chrome edition - `install.bat` explicitly states that Playwright Chromium is not installed; the app uses system Google Chrome.

## Key Dependencies

**Critical:**
- `playwright>=1.40` - Drives persistent Chrome sessions and reads visible page text from `https://chatgpt.com/codex/cloud/settings/analytics#usage` in `codex_balance_widget_chrome.py`.
- Google Chrome - The executable path is required by `playwright.chromium.launch_persistent_context()` in `codex_balance_widget_chrome.py`; detection checks `CHROME_PATH` and common Windows install paths.

**Infrastructure:**
- `pystray>=0.19.5` - Provides the tray menu, tray tooltip, and hide/show behavior in `codex_balance_widget_chrome.py`.
- `Pillow>=10.0.0` - Generates the dynamic tray icon image in `create_tray_image()` inside `codex_balance_widget_chrome.py`.
- Python standard library `asyncio` - Runs browser refresh work in a background event loop from `CodexBalanceWidget` in `codex_balance_widget_chrome.py`.
- Python standard library `json` - Persists settings and usage history to local JSON files through `SettingsStore` and `HistoryStore` in `codex_balance_widget_chrome.py`.
- Python standard library `webbrowser` - Opens the Codex usage page and fallback log URI from `codex_balance_widget_chrome.py`.
- Python standard library `ctypes` and `msvcrt` - Implement Windows single-instance locking and activation signaling in `codex_balance_widget_chrome.py`.

## Configuration

**Environment:**
- Optional `CHROME_PATH` - Overrides automatic Google Chrome discovery in `find_chrome_executable()` in `codex_balance_widget_chrome.py`; documented in `README.md`.
- Local settings JSON - `codex_balance_widget_settings.json` is read and written by `SettingsStore` in `codex_balance_widget_chrome.py`; it is ignored by Git in `.gitignore`.
- Local Chrome profile - `codex_chrome_profile/` stores the dedicated ChatGPT browser session; it is ignored by Git in `.gitignore`.
- Local history JSON - `codex_balance_history.json` stores sampled usage history through `HistoryStore` in `codex_balance_widget_chrome.py`; it is ignored by Git in `.gitignore`.
- Local log file - `widget_launch.log` is written by `write_log()` in `codex_balance_widget_chrome.py` and by `codex_balance_widget_launcher.pyw`; it is ignored by Git in `.gitignore`.

**Build:**
- `requirements.txt` - Python dependency manifest.
- `install.bat` - Installs Python dependencies with pip.
- `run.bat` - Starts the hidden WSH launcher.
- `run_hidden.vbs` - Runs `codex_balance_widget_launcher.pyw` with `pyw.exe -3`.
- `.gitignore` - Excludes virtual environments, Python bytecode, local Chrome profile, settings, history, lock file, logs, and diagnostic snapshots.
- Not detected - No `pyproject.toml`, `setup.py`, `tox.ini`, `pytest.ini`, formatter config, linter config, CI config, or packaging metadata is present.

## Platform Requirements

**Development:**
- Windows.
- Python 3.10 or newer with Windows Python Launcher, as documented in `README.md`.
- Google Chrome installed or `CHROME_PATH` configured.
- pip install from `requirements.txt`.
- ChatGPT account access to the Codex usage page at `https://chatgpt.com/codex/cloud/settings/analytics#usage`.

**Production:**
- Local Windows desktop execution only.
- No server deployment target is present.
- Runtime state remains on the local filesystem under files and directories listed in `.gitignore`.

---

*Stack analysis: 2026-06-17*
