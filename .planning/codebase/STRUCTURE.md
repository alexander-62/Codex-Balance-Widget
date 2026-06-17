# Codebase Structure

**Analysis Date:** 2026-06-17

## Directory Layout

```text
Codex-Balance-Widget/
├── .git/                              # Git repository metadata
├── .planning/                         # GSD planning and codebase maps
│   └── codebase/                      # Generated repository analysis docs
├── .gitignore                         # Ignores Python caches, local editor files, and widget runtime state
├── codex_balance_widget_chrome.py      # Main Windows Tkinter/Playwright widget implementation
├── codex_balance_widget_launcher.pyw   # Hidden Python launcher with early crash logging
├── install.bat                        # Windows dependency installer
├── LICENSE                            # MIT license
├── README.md                          # English usage and operations docs
├── README.ru.md                       # Russian usage and operations docs
├── requirements.txt                   # Python runtime dependencies
├── run.bat                            # User-facing hidden launch wrapper
├── run_hidden.vbs                     # VBS launcher that starts pyw.exe hidden
└── settings_icon.png                  # Settings button bitmap asset
```

## Directory Purposes

**Repository Root (`.`):**
- Purpose: Contains the whole application; there is no `src/` package.
- Contains: Python implementation, Windows launch scripts, dependency manifest, docs, license, image asset.
- Key files: `codex_balance_widget_chrome.py`, `codex_balance_widget_launcher.pyw`, `requirements.txt`, `README.md`, `run.bat`, `run_hidden.vbs`, `install.bat`, `settings_icon.png`.

**`.planning/`:**
- Purpose: Planning artifacts and codebase maps consumed by GSD workflows.
- Contains: `.planning/codebase/` and generated Markdown analysis.
- Key files: `.planning/codebase/ARCHITECTURE.md`, `.planning/codebase/STRUCTURE.md`.

**`.planning/codebase/`:**
- Purpose: Repository intelligence documents for future planning and execution agents.
- Contains: Codebase mapping Markdown files.
- Key files: `.planning/codebase/ARCHITECTURE.md`, `.planning/codebase/STRUCTURE.md`.

**`.git/`:**
- Purpose: Git metadata.
- Contains: Repository object database, refs, index, config.
- Key files: Not application code; do not place project files here.

## Key File Locations

**Entry Points:**
- `run.bat`: User-facing launcher. Starts `run_hidden.vbs` with `wscript.exe`.
- `run_hidden.vbs`: Hidden launcher. Resolves repo directory and runs `codex_balance_widget_launcher.pyw` with `pyw.exe -3`.
- `codex_balance_widget_launcher.pyw`: Python launcher. Logs startup/crashes and runs `codex_balance_widget_chrome.py` as `__main__`.
- `codex_balance_widget_chrome.py`: Direct debug entry point and main app entry at `if __name__ == "__main__"` (`codex_balance_widget_chrome.py:2104`).

**Configuration:**
- `requirements.txt`: Runtime Python dependencies: Playwright, pystray, Pillow.
- `.gitignore`: Ignores Python caches, virtual environments, editor files, Chrome profile, JSON runtime state, lock/log files, and diagnostic snapshots.
- `codex_balance_widget_chrome.py`: Module-level app configuration for URL, paths, refresh timings, UI colors, dimensions, language constants, and Windows activation event (`codex_balance_widget_chrome.py:47`).

**Core Logic:**
- `codex_balance_widget_chrome.py`: All implementation code lives here.
- `codex_balance_widget_chrome.py:199`: `Balance` dataclass.
- `codex_balance_widget_chrome.py:212`: `FetchResult` dataclass.
- `codex_balance_widget_chrome.py:219`: `UsageWaitResult` dataclass.
- `codex_balance_widget_chrome.py:491`: `BalanceParser`.
- `codex_balance_widget_chrome.py:653`: `SettingsStore`.
- `codex_balance_widget_chrome.py:726`: `HistoryStore`.
- `codex_balance_widget_chrome.py:826`: `CodexUsageBrowser`.
- `codex_balance_widget_chrome.py:941`: `ProgressBar`.
- `codex_balance_widget_chrome.py:996`: `WeeklyBurndownCanvas`.
- `codex_balance_widget_chrome.py:1265`: `CodexBalanceWidget`.

**Assets:**
- `settings_icon.png`: Settings button image loaded by `_settings_button()` when present (`codex_balance_widget_chrome.py:1443`).
- `codex_balance_widget_chrome.py`: Contains `BLANK_WINDOW_ICON_PNG` as an embedded base64 PNG for the window icon slot (`codex_balance_widget_chrome.py:65`).

**Documentation:**
- `README.md`: English install, usage, privacy, tray, settings, diagnostics, and disclaimer docs.
- `README.ru.md`: Russian install, usage, local data, settings, limitations, and license docs.
- `LICENSE`: MIT license.

**Testing:**
- Not detected. No `tests/` directory, `*_test.py`, `test_*.py`, or test config files are present in the repository.

## Naming Conventions

**Files:**
- Use lowercase snake_case for Python modules: `codex_balance_widget_chrome.py`, `codex_balance_widget_launcher.pyw`.
- Use simple Windows script names for launch/install wrappers: `install.bat`, `run.bat`, `run_hidden.vbs`.
- Use uppercase conventional repo documents: `README.md`, `README.ru.md`, `LICENSE`.
- Use lowercase generated runtime filenames matching the app prefix: `codex_balance_history.json`, `codex_balance_widget_settings.json`, `codex_balance_widget.lock`.
- Use descriptive asset names: `settings_icon.png`.

**Directories:**
- Runtime state uses lowercase snake_case directory names: `codex_chrome_profile/`.
- Planning artifacts use hidden dot directory names: `.planning/`, `.planning/codebase/`.
- Python virtual environments are expected as `.venv/` or `venv/` and ignored by `.gitignore`.

**Python Symbols:**
- Dataclasses and classes use PascalCase: `Balance`, `FetchResult`, `UsageWaitResult`, `BalanceParser`, `SettingsStore`, `HistoryStore`, `CodexUsageBrowser`, `CodexBalanceWidget`.
- Functions and methods use snake_case: `write_log()`, `find_chrome_executable()`, `parse_reset_datetime()`, `update_balance_ui()`.
- Constants use uppercase snake_case: `APP_VERSION`, `PROFILE_DIR`, `SETTINGS_PATH`, `REFRESH_SECONDS`, `DEFAULT_LANGUAGE`.
- Private helpers use a leading underscore: `_fetch_once()`, `_wait_for_usage_text()`, `_build_ui()`, `_run_on_ui()`.

## Where to Add New Code

**New Usage Page Parsing:**
- Primary code: Add or adjust regex patterns in `BalanceParser` inside `codex_balance_widget_chrome.py:491`.
- Related helpers: Use `normalize_reset_text()` and `parse_reset_datetime()` in `codex_balance_widget_chrome.py:338` and `codex_balance_widget_chrome.py:345`.
- Tests: No test structure exists. If adding tests, create a new `tests/` directory and add parser-focused unit tests for `BalanceParser.parse()`.

**New Browser Fetch Behavior:**
- Primary code: Add Playwright/session handling in `CodexUsageBrowser` inside `codex_balance_widget_chrome.py:826`.
- Caller code: Keep UI-triggered fetch orchestration in `CodexBalanceWidget.fetch_once()` (`codex_balance_widget_chrome.py:2019`).
- Do not put Playwright calls directly into Tk button handlers in `CodexBalanceWidget`.

**New Widget UI Control:**
- Primary code: Add layout in `CodexBalanceWidget._build_ui()` (`codex_balance_widget_chrome.py:1330`) or a helper method near `_build_limit_card()` (`codex_balance_widget_chrome.py:1372`).
- Settings dialog changes: Add controls in `show_settings()` (`codex_balance_widget_chrome.py:1752`) and persist values through `SettingsStore`.
- Tray menu changes: Add menu items in `setup_tray_icon()` (`codex_balance_widget_chrome.py:1493`) and dispatch to Tk through `_run_on_ui()` (`codex_balance_widget_chrome.py:1544`).

**New Persistent Setting:**
- Primary code: Add default and validation in `SettingsStore.DEFAULTS`, `SettingsStore.load()`, and `SettingsStore.save()` (`codex_balance_widget_chrome.py:653`).
- UI code: Read the value during `CodexBalanceWidget.__init__()` (`codex_balance_widget_chrome.py:1266`) and save through `SettingsStore.save()` from the relevant UI action.
- Runtime file: The value belongs in generated `codex_balance_widget_settings.json`, which is ignored by `.gitignore`.

**New History Field or Chart Data:**
- Primary code: Add serialization/deserialization in `HistoryStore.append_balance()` and `HistoryStore.latest_balance()` (`codex_balance_widget_chrome.py:750`, `codex_balance_widget_chrome.py:799`).
- Chart code: Add visualization behavior in `WeeklyBurndownCanvas` (`codex_balance_widget_chrome.py:996`) or `CodexBalanceWidget.update_weekly_chart()` (`codex_balance_widget_chrome.py:1689`).
- Runtime file: The value belongs in generated `codex_balance_history.json`, which is ignored by `.gitignore`.

**New Drawing Component:**
- Implementation: Add a new Tk `Canvas` component near `ProgressBar` and `WeeklyBurndownCanvas` in `codex_balance_widget_chrome.py:941`.
- Integration: Instantiate it in `_build_ui()` and update it from `apply_balance_ui()` or a focused update method.

**New Launch/Install Behavior:**
- Dependency install behavior: Update `install.bat` and `requirements.txt`.
- Hidden launch behavior: Update `run_hidden.vbs` and `codex_balance_widget_launcher.pyw`.
- Visible/debug launch behavior: Update `README.md` and `README.ru.md` when commands change.

**Utilities:**
- Shared helpers: Place small pure helpers near similar helpers in `codex_balance_widget_chrome.py`:
  - Parsing/date helpers near `parse_reset_datetime()` (`codex_balance_widget_chrome.py:345`).
  - UI color/format helpers near `usage_color()` and `format_countdown()` (`codex_balance_widget_chrome.py:328`, `codex_balance_widget_chrome.py:459`).
  - Tray helpers near `build_tray_tooltip()` and `create_tray_image()` (`codex_balance_widget_chrome.py:1181`, `codex_balance_widget_chrome.py:1217`).

## Special Directories

**`codex_chrome_profile/`:**
- Purpose: Dedicated persistent Chrome profile for the widget's ChatGPT session.
- Generated: Yes, by Playwright persistent context in `CodexUsageBrowser._fetch_once()` (`codex_balance_widget_chrome.py:877`).
- Committed: No, ignored by `.gitignore`.

**`.venv/` and `venv/`:**
- Purpose: Optional local Python virtual environments.
- Generated: Yes, by developer environment setup.
- Committed: No, ignored by `.gitignore`.

**`__pycache__/`:**
- Purpose: Python bytecode cache.
- Generated: Yes, by Python.
- Committed: No, ignored by `.gitignore`.

**`.planning/`:**
- Purpose: GSD planning/codebase intelligence artifacts.
- Generated: Yes, by planning/mapping workflows.
- Committed: Depends on project workflow; current write scope for this mapping is `.planning/codebase/ARCHITECTURE.md` and `.planning/codebase/STRUCTURE.md`.

## Runtime Files

**`codex_balance_widget_settings.json`:**
- Purpose: Stores geometry, always-on-top mode, burndown visibility, refresh interval, language, and version.
- Owner: `SettingsStore` in `codex_balance_widget_chrome.py:653`.
- Generated: Yes.
- Committed: No, ignored by `.gitignore`.

**`codex_balance_history.json`:**
- Purpose: Stores recent balance samples used for restoring last data and weekly chart generation.
- Owner: `HistoryStore` in `codex_balance_widget_chrome.py:726`.
- Generated: Yes.
- Committed: No, ignored by `.gitignore`.

**`codex_balance_widget.lock`:**
- Purpose: Single-instance lock file used by `acquire_app_lock()` (`codex_balance_widget_chrome.py:234`).
- Generated: Yes.
- Committed: No, ignored by `.gitignore`.

**`widget_launch.log`:**
- Purpose: Startup/runtime diagnostic log used by `write_log()` and the launcher (`codex_balance_widget_chrome.py:225`, `codex_balance_widget_launcher.pyw:14`).
- Generated: Yes.
- Committed: No, ignored by `.gitignore`.

**`Codex*.mhtml`:**
- Purpose: Local diagnostic snapshots.
- Generated: Yes.
- Committed: No, ignored by `.gitignore`.

---

*Structure analysis: 2026-06-17*
