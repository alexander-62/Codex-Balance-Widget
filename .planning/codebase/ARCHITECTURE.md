<!-- refreshed: 2026-06-17 -->
# Architecture

**Analysis Date:** 2026-06-17

## System Overview

```text
┌─────────────────────────────────────────────────────────────┐
│                  Windows Launch Layer                        │
├──────────────────┬──────────────────┬───────────────────────┤
│  install.bat     │  run.bat         │  run_hidden.vbs       │
│ `install.bat`    │ `run.bat`        │ `run_hidden.vbs`      │
└────────┬─────────┴────────┬─────────┴──────────┬────────────┘
         │                  │                     │
         ▼                  ▼                     ▼
┌─────────────────────────────────────────────────────────────┐
│                 Python Launcher / Main Module                │
│ `codex_balance_widget_launcher.pyw` ->                       │
│ `codex_balance_widget_chrome.py`                             │
└──────────────────────────────┬──────────────────────────────┘
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                 Widget Orchestration Layer                   │
│ `CodexBalanceWidget` in `codex_balance_widget_chrome.py`      │
├──────────────────┬──────────────────┬───────────────────────┤
│  Tkinter UI      │  pystray tray     │  asyncio worker       │
│  `ProgressBar`   │  tray image funcs │  `refresh_loop()`     │
└────────┬─────────┴────────┬─────────┴──────────┬────────────┘
         │                  │                     │
         ▼                  ▼                     ▼
┌─────────────────────────────────────────────────────────────┐
│                Browser Fetch / Parse Layer                   │
│ `CodexUsageBrowser` + `BalanceParser`                        │
│ `codex_balance_widget_chrome.py`                             │
└──────────────────────────────┬──────────────────────────────┘
                               ▼
┌─────────────────────────────────────────────────────────────┐
│               Local State and External Page                  │
│ `codex_chrome_profile/`, `codex_balance_history.json`,        │
│ `codex_balance_widget_settings.json`, ChatGPT Usage page      │
└─────────────────────────────────────────────────────────────┘
```

## Component Responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| Windows installer | Installs Python dependencies from `requirements.txt` with the Windows Python launcher. | `install.bat` |
| Visible launcher | Starts the hidden VBS launcher through `wscript.exe`. | `run.bat` |
| Hidden launcher | Starts `codex_balance_widget_launcher.pyw` through `pyw.exe -3` without a console window. | `run_hidden.vbs` |
| Python launcher | Logs startup crashes before the main module can initialize and runs the main module as `__main__`. | `codex_balance_widget_launcher.pyw` |
| Main process guard | Enforces a single running instance with `codex_balance_widget.lock` and a Windows activation event. | `codex_balance_widget_chrome.py:234`, `codex_balance_widget_chrome.py:247`, `codex_balance_widget_chrome.py:2104` |
| Widget controller | Owns Tk root setup, state variables, refresh scheduling, tray integration, and shutdown. | `codex_balance_widget_chrome.py:1265` |
| Browser adapter | Opens system Chrome through Playwright using the dedicated persistent profile and returns page text/status. | `codex_balance_widget_chrome.py:826` |
| Usage parser | Converts visible Usage page text into `Balance` fields for 5-hour percent, weekly percent, credits, and reset text. | `codex_balance_widget_chrome.py:491` |
| Settings store | Loads, validates, and atomically saves UI/runtime preferences. | `codex_balance_widget_chrome.py:653` |
| History store | Keeps recent local balance samples and restores the latest saved balance on startup. | `codex_balance_widget_chrome.py:726` |
| Tk UI widgets | Draw progress bars and weekly burndown canvas views. | `codex_balance_widget_chrome.py:941`, `codex_balance_widget_chrome.py:996` |
| Tray UI | Builds tray tooltip, icon image, menu callbacks, and update path. | `codex_balance_widget_chrome.py:1181`, `codex_balance_widget_chrome.py:1217`, `codex_balance_widget_chrome.py:1493` |

## Pattern Overview

**Overall:** Single-file desktop application with adapter-style boundaries inside one Python module.

**Key Characteristics:**
- Keep application logic in `codex_balance_widget_chrome.py`; the rest of the repository is launch, install, assets, and docs.
- Treat `CodexBalanceWidget` as the composition root. It wires the UI, browser adapter, local stores, background event loop, and tray.
- Keep Playwright access isolated in `CodexUsageBrowser`; UI code should not call Playwright directly.
- Keep persistent JSON access isolated in `SettingsStore` and `HistoryStore`; UI code should use those stores instead of opening JSON files directly.
- Use dataclasses (`Balance`, `FetchResult`, `UsageWaitResult`) for internal message passing between browser, parser, and UI.

## Layers

**Launch Layer:**
- Purpose: Start the widget on Windows, optionally hidden, and install runtime dependencies.
- Location: `install.bat`, `run.bat`, `run_hidden.vbs`, `codex_balance_widget_launcher.pyw`
- Contains: Batch/VBS wrappers, Python crash-logging launcher.
- Depends on: Windows Script Host, `py.exe`, `pyw.exe`, local `requirements.txt`.
- Used by: End users and README installation instructions in `README.md`.

**Composition and Process Layer:**
- Purpose: Enforce single-instance behavior, create activation event, initialize the app, and enter Tk mainloop.
- Location: `codex_balance_widget_chrome.py:2104`
- Contains: `acquire_app_lock()`, `signal_existing_instance()`, `create_activate_event()`, `CodexBalanceWidget(...)`, `app.run()`.
- Depends on: `msvcrt`, Windows `kernel32` through `ctypes`, `atexit`.
- Used by: Direct `py -3 codex_balance_widget_chrome.py` runs and `codex_balance_widget_launcher.pyw`.

**UI and Orchestration Layer:**
- Purpose: Own all user-visible state, Tk widgets, menu actions, tray actions, background scheduling, and shutdown.
- Location: `codex_balance_widget_chrome.py:1265`
- Contains: `CodexBalanceWidget`, `_build_ui()`, `show_settings()`, `show_diagnostics()`, `manual_refresh()`, `schedule_refresh()`, `exit_app()`.
- Depends on: `tkinter`, `pystray`, `Pillow`, `asyncio`, `threading`, `SettingsStore`, `HistoryStore`, `CodexUsageBrowser`.
- Used by: The process entry point in `codex_balance_widget_chrome.py:2104`.

**Browser Fetch Layer:**
- Purpose: Fetch Usage page text from ChatGPT using installed Google Chrome and a dedicated persistent profile.
- Location: `codex_balance_widget_chrome.py:826`
- Contains: `CodexUsageBrowser.fetch()`, `_fetch_visible()`, `_fetch_once()`, `_wait_for_usage_text()`.
- Depends on: `playwright.async_api`, `PROFILE_DIR`, `CODEX_USAGE_URL`, `BalanceParser`.
- Used by: `CodexBalanceWidget.fetch_once()` in `codex_balance_widget_chrome.py:2019`.

**Parsing and Formatting Layer:**
- Purpose: Normalize raw page text, parse reset dates, format countdowns, and assign usage colors.
- Location: `codex_balance_widget_chrome.py:311`, `codex_balance_widget_chrome.py:345`, `codex_balance_widget_chrome.py:459`, `codex_balance_widget_chrome.py:491`
- Contains: `safe_int()`, `usage_color()`, `parse_reset_datetime()`, `format_countdown()`, `BalanceParser`.
- Depends on: `re`, `datetime`, localized month lookup tables.
- Used by: Browser wait logic, UI update logic, tray tooltip logic, and history serialization.

**Persistence Layer:**
- Purpose: Load and save local settings/history and avoid corrupting files with partial writes.
- Location: `codex_balance_widget_chrome.py:653`, `codex_balance_widget_chrome.py:726`
- Contains: `SettingsStore`, `HistoryStore`.
- Depends on: `SETTINGS_PATH`, `HISTORY_PATH`, `json`, `Path.replace()`.
- Used by: Startup restore, settings dialog, window hide/show, balance updates, diagnostics.

**Drawing Layer:**
- Purpose: Render progress bars, weekly burndown chart, and tray icon bitmap.
- Location: `codex_balance_widget_chrome.py:941`, `codex_balance_widget_chrome.py:996`, `codex_balance_widget_chrome.py:1217`
- Contains: `ProgressBar`, `WeeklyBurndownCanvas`, `create_tray_image()`, `build_tray_tooltip()`.
- Depends on: `tkinter.Canvas`, `Pillow`, usage color helpers, history samples.
- Used by: `CodexBalanceWidget._build_ui()`, `update_weekly_chart()`, `setup_tray_icon()`, `update_tray_icon()`.

## Data Flow

### Primary Refresh Path

1. The application starts from `codex_balance_widget_chrome.py:2104`; the entry point acquires `codex_balance_widget.lock`, creates the activation event, instantiates `CodexBalanceWidget`, and calls `run()`.
2. `CodexBalanceWidget.__init__()` loads settings/history, builds Tk UI, starts an asyncio worker thread, starts the tray icon, and schedules refresh callbacks (`codex_balance_widget_chrome.py:1266`).
3. `schedule_refresh()` submits `refresh_loop()` to the worker event loop (`codex_balance_widget_chrome.py:1727`, `codex_balance_widget_chrome.py:2062`).
4. `fetch_once()` guards against overlapping refreshes, calls `CodexUsageBrowser.fetch()`, records fetch status/error, and passes successful page text to `BalanceParser.parse()` (`codex_balance_widget_chrome.py:2019`).
5. `CodexUsageBrowser.fetch()` chooses headless Chrome when a saved profile exists, visible Chrome when login/debug is needed, and launches a persistent Chrome context using `PROFILE_DIR` (`codex_balance_widget_chrome.py:832`, `codex_balance_widget_chrome.py:869`).
6. `_wait_for_usage_text()` polls page body text until `BalanceParser` recognizes usage data, a login page is detected, or timeout occurs (`codex_balance_widget_chrome.py:904`).
7. `update_balance_ui()` marshals the parsed `Balance` back to the Tk thread with `root.after()` and calls `apply_balance_ui()` (`codex_balance_widget_chrome.py:1678`, `codex_balance_widget_chrome.py:1642`).
8. `apply_balance_ui()` updates StringVars, progress bars, chart visibility, countdown text, history file, and tray icon (`codex_balance_widget_chrome.py:1642`).

### Hidden Windows Launch Path

1. `run.bat` starts `run_hidden.vbs` with `wscript.exe` (`run.bat:2`).
2. `run_hidden.vbs` resolves the repo directory and runs `pyw.exe -3 codex_balance_widget_launcher.pyw` hidden (`run_hidden.vbs:7`).
3. `codex_balance_widget_launcher.pyw` prepends the app directory to `sys.path`, logs startup, and executes `codex_balance_widget_chrome.py` via `runpy.run_path(..., run_name="__main__")` (`codex_balance_widget_launcher.pyw:22`, `codex_balance_widget_launcher.pyw:24`).
4. Any early exception is appended to `widget_launch.log` by `codex_balance_widget_launcher.pyw` (`codex_balance_widget_launcher.pyw:25`).

### Manual Refresh / Debug Path

1. The Tk button calls `manual_refresh()` from `_build_ui()` (`codex_balance_widget_chrome.py:1360`, `codex_balance_widget_chrome.py:1730`).
2. `manual_refresh()` submits `fetch_once(allow_visible_debug=True)` to the asyncio loop (`codex_balance_widget_chrome.py:1730`).
3. If a previous headless refresh flagged `needs_visible_debug`, `CodexUsageBrowser.fetch()` opens visible Chrome for inspection (`codex_balance_widget_chrome.py:832`).
4. The same parse/update path as the primary refresh flow applies after visible Chrome returns Usage page text.

### Tray Interaction Path

1. `setup_tray_icon()` creates a `pystray.Icon`, menu items, and a daemon tray thread (`codex_balance_widget_chrome.py:1493`).
2. Tray callbacks use `_run_on_ui()` to dispatch work onto Tk's thread with `root.after()` (`codex_balance_widget_chrome.py:1544`).
3. Show/hide saves or restores geometry through `SettingsStore.save_geometry()` and updates the tray tooltip/icon (`codex_balance_widget_chrome.py:1571`, `codex_balance_widget_chrome.py:1577`, `codex_balance_widget_chrome.py:1587`).

**State Management:**
- Runtime UI state lives on the `CodexBalanceWidget` instance in `codex_balance_widget_chrome.py:1265`.
- Tk display state is held in `tk.StringVar` objects created in `CodexBalanceWidget.__init__()` (`codex_balance_widget_chrome.py:1295`).
- Durable settings are stored in `codex_balance_widget_settings.json` through `SettingsStore` (`codex_balance_widget_chrome.py:57`, `codex_balance_widget_chrome.py:653`).
- Durable balance history is stored in `codex_balance_history.json` through `HistoryStore` (`codex_balance_widget_chrome.py:58`, `codex_balance_widget_chrome.py:726`).
- Authentication/session state is delegated to Chrome's persistent profile at `codex_chrome_profile/` (`codex_balance_widget_chrome.py:54`, `codex_balance_widget_chrome.py:877`).

## Key Abstractions

**`Balance`:**
- Purpose: Canonical in-memory representation of the values extracted from the Usage page.
- Examples: `codex_balance_widget_chrome.py:199`, `codex_balance_widget_chrome.py:491`, `codex_balance_widget_chrome.py:1642`
- Pattern: Dataclass DTO with computed `has_usage_data` property.

**`FetchResult` and `UsageWaitResult`:**
- Purpose: Small status/result carriers between Playwright operations and widget orchestration.
- Examples: `codex_balance_widget_chrome.py:212`, `codex_balance_widget_chrome.py:219`, `codex_balance_widget_chrome.py:832`, `codex_balance_widget_chrome.py:904`
- Pattern: Dataclass DTOs with string statuses such as `ok`, `login_required`, `not_ready`, `browser_error`.

**`BalanceParser`:**
- Purpose: Encapsulates regex-based extraction of usage fields and reset text from page body text.
- Examples: `codex_balance_widget_chrome.py:491`
- Pattern: Static parser class. Add new Usage page text variants by extending patterns inside `BalanceParser.parse()` and helper methods.

**`CodexUsageBrowser`:**
- Purpose: Adapts Playwright/Chrome behavior into a single `fetch()` call that returns page text or a status.
- Examples: `codex_balance_widget_chrome.py:826`
- Pattern: Adapter with public orchestration method plus private visible/headless helper methods.

**`SettingsStore` and `HistoryStore`:**
- Purpose: Keep JSON persistence rules in one place.
- Examples: `codex_balance_widget_chrome.py:653`, `codex_balance_widget_chrome.py:726`
- Pattern: Static store classes using validated defaults and atomic temp-file replacement.

**`ProgressBar` and `WeeklyBurndownCanvas`:**
- Purpose: Self-contained Tk canvas drawing components for quota visualization.
- Examples: `codex_balance_widget_chrome.py:941`, `codex_balance_widget_chrome.py:996`
- Pattern: Stateful widgets with `set_value()`/`set_data()` methods followed by `redraw()`.

## Entry Points

**Hidden user launch:**
- Location: `run.bat`
- Triggers: User double-clicks `run.bat`.
- Responsibilities: Starts `run_hidden.vbs` with `wscript.exe` and exits.

**Hidden Python launch:**
- Location: `run_hidden.vbs`
- Triggers: `run.bat`.
- Responsibilities: Runs `codex_balance_widget_launcher.pyw` using `pyw.exe -3` with no visible console.

**Crash-logging Python launcher:**
- Location: `codex_balance_widget_launcher.pyw`
- Triggers: `run_hidden.vbs`.
- Responsibilities: Logs startup path/crashes to `widget_launch.log` and executes `codex_balance_widget_chrome.py` as `__main__`.

**Direct debug launch:**
- Location: `codex_balance_widget_chrome.py`
- Triggers: `py -3 codex_balance_widget_chrome.py`, as documented in `README.md`.
- Responsibilities: Runs the same app with a visible console for debugging.

**Main process entry:**
- Location: `codex_balance_widget_chrome.py:2104`
- Triggers: Python module executed as `__main__`.
- Responsibilities: Enforces single instance, creates activation event, registers cleanup, creates `CodexBalanceWidget`, starts Tk mainloop.

## Architectural Constraints

- **Threading:** Tkinter runs on the main thread. An asyncio event loop runs on a daemon worker thread (`codex_balance_widget_chrome.py:1617`). Tray icon code runs on another daemon thread (`codex_balance_widget_chrome.py:1519`). Cross-thread UI work must use `root.after()` through `_run_on_ui()` or existing UI update methods (`codex_balance_widget_chrome.py:1544`, `codex_balance_widget_chrome.py:1678`).
- **Global state:** Module-level constants define paths, colors, timings, language tables, and Windows event names in `codex_balance_widget_chrome.py:47`. Treat these as shared configuration for the whole app.
- **Platform:** The app targets Windows. Single-instance locking uses `msvcrt` and activation uses `kernel32` via `ctypes` (`codex_balance_widget_chrome.py:77`, `codex_balance_widget_chrome.py:234`, `codex_balance_widget_chrome.py:247`).
- **Browser dependency:** The app uses installed Google Chrome, not bundled Playwright Chromium. Chrome discovery checks `CHROME_PATH` and common Windows install paths (`codex_balance_widget_chrome.py:285`).
- **Profile isolation:** Browser automation must use `PROFILE_DIR` (`codex_balance_widget_chrome.py:54`) so the user's primary Chrome profile is not used.
- **Circular imports:** Not applicable. There is one implementation module, `codex_balance_widget_chrome.py`, plus a thin launcher that imports only standard library modules.
- **Generated runtime files:** `codex_chrome_profile/`, `codex_balance_history.json`, `codex_balance_widget_settings.json`, `codex_balance_widget.lock`, and `widget_launch.log` are runtime state and are ignored by `.gitignore`.

## Anti-Patterns

### Direct UI Mutation From Worker Threads

**What happens:** Background fetch work runs on an asyncio loop in a worker thread (`codex_balance_widget_chrome.py:1617`).
**Why it's wrong:** Tkinter widgets and `StringVar` objects are owned by the main thread; direct mutation from the worker thread can crash or corrupt UI state.
**Do this instead:** Marshal callbacks with `root.after()` as done in `_run_on_ui()` and `update_balance_ui()` (`codex_balance_widget_chrome.py:1544`, `codex_balance_widget_chrome.py:1678`).

### Browser Logic Inside UI Handlers

**What happens:** `CodexBalanceWidget` owns button/menu events, while Playwright logic is isolated in `CodexUsageBrowser`.
**Why it's wrong:** Putting Playwright calls directly into Tk handlers would block the UI and duplicate visible/headless login handling.
**Do this instead:** Add browser behavior inside `CodexUsageBrowser` (`codex_balance_widget_chrome.py:826`) and call it through `fetch_once()` (`codex_balance_widget_chrome.py:2019`).

### Ad Hoc JSON Persistence

**What happens:** Settings and history each have validation, cleanup, and atomic write behavior.
**Why it's wrong:** Opening `codex_balance_widget_settings.json` or `codex_balance_history.json` directly from new UI code bypasses validation and risks partial writes.
**Do this instead:** Use `SettingsStore` and `HistoryStore` (`codex_balance_widget_chrome.py:653`, `codex_balance_widget_chrome.py:726`).

### Parsing Usage Text Outside `BalanceParser`

**What happens:** Fetch readiness and final UI updates both rely on `BalanceParser.parse()`.
**Why it's wrong:** Spreading regexes across the app makes Usage page changes harder to update consistently.
**Do this instead:** Add page text variations to `BalanceParser` and continue passing around `Balance` (`codex_balance_widget_chrome.py:491`).

## Error Handling

**Strategy:** Fail soft in the UI, log technical detail to `widget_launch.log`, preserve last known balance when possible, and prompt visible Chrome only when login/debug is required.

**Patterns:**
- Startup crashes before the main app loads are caught by `codex_balance_widget_launcher.pyw` and written to `widget_launch.log` (`codex_balance_widget_launcher.pyw:25`).
- Regular logs use `write_log()`, which ignores log write failures (`codex_balance_widget_chrome.py:225`).
- Settings/history reads fall back to defaults or empty history on missing/corrupt JSON (`codex_balance_widget_chrome.py:664`, `codex_balance_widget_chrome.py:728`).
- Settings/history saves write a `.tmp` file and replace the target path (`codex_balance_widget_chrome.py:711`, `codex_balance_widget_chrome.py:743`).
- Playwright errors return `FetchResult("browser_error", ...)` rather than raising into the UI (`codex_balance_widget_chrome.py:892`).
- Fetch failures keep existing `current_balance` visible when data is already loaded (`codex_balance_widget_chrome.py:2034`).

## Cross-Cutting Concerns

**Logging:** Use `write_log()` in `codex_balance_widget_chrome.py:225` for runtime diagnostics and `codex_balance_widget_launcher.pyw:14` for launcher diagnostics. Logs go to `widget_launch.log`.

**Validation:** Settings validation is centralized in `SettingsStore.load()` and `SettingsStore.save()` (`codex_balance_widget_chrome.py:664`, `codex_balance_widget_chrome.py:693`). Numeric usage values pass through `safe_int()` (`codex_balance_widget_chrome.py:311`). Reset text passes through `normalize_reset_text()` and `parse_reset_datetime()` (`codex_balance_widget_chrome.py:338`, `codex_balance_widget_chrome.py:345`).

**Authentication:** No credentials are collected by the app. Authentication is handled by the ChatGPT session inside the dedicated Chrome profile at `codex_chrome_profile/`, opened through Playwright persistent context (`codex_balance_widget_chrome.py:54`, `codex_balance_widget_chrome.py:877`).

**Internationalization:** UI text uses the `tr(language, en, ru)` helper and the selected language from `SettingsStore` (`codex_balance_widget_chrome.py:115`, `codex_balance_widget_chrome.py:653`). Add user-facing strings through `tr()` to preserve English/Russian behavior.

**Privacy:** The runtime Chrome profile, settings, history, lock, log, and diagnostic snapshots are ignored in `.gitignore`. Keep generated state out of version control and docs should mention paths without including contents.

---

*Architecture analysis: 2026-06-17*
