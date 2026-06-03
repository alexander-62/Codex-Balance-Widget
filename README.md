# Codex Balance Widget

[Русский](README.ru.md)

A small Windows widget for monitoring Codex Usage limits. It opens
`https://chatgpt.com/codex/cloud/settings/analytics#usage` in your installed
Google Chrome and displays the remaining quota in a compact window and the
system tray.

## Features

- 5-hour and weekly limits, reset times, and credits
- color-coded tray icon with a large tens digit
- tooltip with exact values
- local weekly usage burndown chart
- configurable refresh interval, always-on-top mode, and interface language
- separate Chrome profile: your primary browser profile is not used

## Requirements

- Windows
- Python 3.10 or newer with Windows Python Launcher
- Google Chrome
- access to the Codex Usage page in your ChatGPT account

## Install and Run

1. Run `install.bat`.
2. Run `run.bat`.
3. On the first launch, sign in to ChatGPT in the Chrome window that opens.

The app uses your system Google Chrome. It does not download Playwright
Chromium.

For debugging, run:

```bat
py -3 codex_balance_widget_chrome.py
```

## System Tray

The tray icon background reflects the remaining 5-hour limit:

- green: `51–100%`
- orange: `21–50%`
- red: `0–20%`
- gray with `?`: data has not been loaded yet

The same color scale is used everywhere remaining percentages are shown:
tray icon, numeric values, progress bars, and weekly burndown segments.

The icon shows a large tens digit: for example, `87%` is displayed as `8`.
`100%` is displayed as `✓`. Hover over the icon to see exact values, reset
times, credits, the last update time, and the current status.

Right-click the icon to show or hide the window, refresh data, open the Codex
Usage page, access settings and diagnostics, open the log, or exit.

Closing the window with the title-bar button hides it in the tray. Use `Exit`
from the tray menu to stop the app.

## Local Data and Privacy

The app creates a separate local Chrome profile:

```text
codex_chrome_profile
```

This profile stores a dedicated ChatGPT session for the widget. The profile,
settings, usage history, lock file, logs, and diagnostic snapshots are excluded
from Git through `.gitignore`. Do not publish or share the profile directory.

## Settings

The settings window lets you change:

- interface language: English or Русский
- always-on-top mode
- weekly burndown visibility
- refresh interval

English is the default language. Restart the app after changing the language.

## Chrome Path

If Chrome is not detected automatically, set `CHROME_PATH`:

```bat
set CHROME_PATH=C:\Program Files\Google\Chrome\Application\chrome.exe
py -3 codex_balance_widget_chrome.py
```

## Diagnostics

Use the settings menu or tray menu to open diagnostics and `widget_launch.log`.
If hidden startup cannot find Python, make sure Windows Python Launcher is
installed: `run_hidden.vbs` uses `pyw.exe -3`.

## Disclaimer

This is an unofficial community tool and is not affiliated with OpenAI. It
reads visible text from the Codex Usage page. If the page layout changes, the
parser may need an update.

## License

[MIT License](LICENSE)
