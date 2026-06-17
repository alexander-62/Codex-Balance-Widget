# Coding Conventions

**Analysis Date:** 2026-06-17

## Naming Patterns

**Files:**
- Use lowercase snake_case for Python entry points: `codex_balance_widget_chrome.py`, `codex_balance_widget_launcher.pyw`.
- Use simple Windows launcher script names for user-facing commands: `install.bat`, `run.bat`, `run_hidden.vbs`.
- Runtime state files use the `codex_balance_*.json` / `widget_launch.log` naming pattern and are excluded by `.gitignore`: `codex_balance_widget_settings.json`, `codex_balance_history.json`, `widget_launch.log`.

**Functions:**
- Use lowercase snake_case for module-level helpers in `codex_balance_widget_chrome.py`: `write_log`, `safe_int`, `parse_reset_datetime`, `format_countdown`, `find_chrome_executable`.
- Use verb-oriented names for actions and side effects in `codex_balance_widget_chrome.py`: `acquire_app_lock`, `signal_existing_instance`, `create_tray_image`, `build_tray_tooltip`.
- Use private helper prefixes for implementation details inside classes: `BalanceParser._first_match`, `BalanceParser._reset_matches`, `CodexUsageBrowser._fetch_once`, `CodexBalanceWidget._build_ui`.
- Async functions are named by operation, not by transport: `CodexUsageBrowser.fetch`, `CodexUsageBrowser._fetch_visible`, `CodexBalanceWidget.fetch_once`, `CodexBalanceWidget.refresh_loop`.

**Variables:**
- Use uppercase module constants for configuration, paths, UI colors, timeouts, and Windows API constants in `codex_balance_widget_chrome.py`: `APP_VERSION`, `PROFILE_DIR`, `REFRESH_SECONDS`, `BACKGROUND_WAIT_SECONDS`, `GREEN`, `WAIT_TIMEOUT`.
- Use lowercase snake_case locals and attributes: `weekly_percent`, `five_hour_reset_dt`, `last_successful_update`, `refresh_in_progress`.
- Tkinter-bound variables use a `_var` suffix in `CodexBalanceWidget.__init__`: `status_var`, `five_hour_value_var`, `weekly_reset_var`, `updated_var`.
- Path objects use `_PATH` or `_DIR` constants: `LOG_PATH`, `SETTINGS_PATH`, `HISTORY_PATH`, `APP_DIR`.

**Types:**
- Use PascalCase for dataclasses and classes: `Balance`, `FetchResult`, `UsageWaitResult`, `BalanceParser`, `SettingsStore`, `HistoryStore`, `CodexUsageBrowser`, `CodexBalanceWidget`.
- Dataclasses in `codex_balance_widget_chrome.py` represent small data transfer objects and keep optional fields typed with `str | None`.
- Store classes use static methods and no instance state: `SettingsStore` and `HistoryStore` in `codex_balance_widget_chrome.py`.

## Code Style

**Formatting:**
- No formatter configuration is detected. There is no `.prettierrc`, `pyproject.toml`, `setup.cfg`, `ruff.toml`, or `black` configuration in the repository.
- Follow the existing Python style in `codex_balance_widget_chrome.py`: 4-space indentation, blank lines between top-level definitions, parenthesized multiline calls, and trailing commas in multiline argument lists.
- Keep line length practical but not strictly enforced. Several Tkinter text/status calls in `codex_balance_widget_chrome.py` are long; new code should prefer wrapping nested calls for readability.
- Use `from __future__ import annotations` in Python entry points. Both `codex_balance_widget_chrome.py` and `codex_balance_widget_launcher.pyw` use it.

**Linting:**
- No lint tool is configured. There is no `ruff`, `flake8`, `pylint`, or `mypy` configuration in the repository.
- Maintain type annotations on public helpers and methods when adding code to `codex_balance_widget_chrome.py`.
- Preserve optional dependency handling for tray support in `codex_balance_widget_chrome.py`: imports of `pystray` and `PIL` are wrapped in `try`/`except` and expose `TRAY_IMPORT_ERROR`.

## Import Organization

**Order:**
1. Future imports: `from __future__ import annotations` in `codex_balance_widget_chrome.py` and `codex_balance_widget_launcher.pyw`.
2. Standard library imports: `asyncio`, `atexit`, `ctypes`, `json`, `threading`, `tkinter`, `dataclasses`, `datetime`, `pathlib`.
3. Third-party imports: `playwright.async_api` in `codex_balance_widget_chrome.py`.
4. Optional third-party imports inside guarded blocks: `pystray`, `PIL.Image`, `PIL.ImageDraw`, `PIL.ImageFont` in `codex_balance_widget_chrome.py`.

**Path Aliases:**
- Not applicable. The repository has no package layout, no import aliases, and no `src/` directory.
- Import sibling code through direct execution rather than package imports: `codex_balance_widget_launcher.pyw` uses `runpy.run_path(str(SCRIPT_PATH), run_name="__main__")`.

## Error Handling

**Patterns:**
- For recoverable local file I/O failures, catch `OSError` and either ignore noncritical logging failures or write a diagnostic to `widget_launch.log` through `write_log` in `codex_balance_widget_chrome.py`.
- For malformed JSON, fall back to defaults or empty lists: `SettingsStore.load` catches `OSError` and `json.JSONDecodeError`; `HistoryStore.load` catches `FileNotFoundError`, `OSError`, and `json.JSONDecodeError`.
- For user-facing browser failures, return typed status objects instead of raising: `CodexUsageBrowser._fetch_once` returns `FetchResult("browser_error", error=...)`; `_wait_for_usage_text` returns `UsageWaitResult("login_required")` or `UsageWaitResult("not_ready")`.
- For invalid parser inputs, return `None` or empty values rather than raising: `safe_int`, `parse_reset_datetime`, `parse_iso_datetime`, and `BalanceParser` helpers in `codex_balance_widget_chrome.py`.
- For Tkinter shutdown and window operations, catch `tk.TclError` where the UI may already be closing: `CodexBalanceWidget._install_blank_icon`, `CodexBalanceWidget.exit_app`.
- For launcher startup failures, log the full traceback to `widget_launch.log`: `codex_balance_widget_launcher.pyw`.

## Logging

**Framework:** custom file logging via `write_log`.

**Patterns:**
- Use `write_log(message: str)` in `codex_balance_widget_chrome.py` for operational diagnostics and recoverable failures.
- Use the separate `write_log(message: str)` in `codex_balance_widget_launcher.pyw` before and during launcher startup.
- Do not use `print()` for app diagnostics. The widget is commonly launched through `run_hidden.vbs` and `codex_balance_widget_launcher.pyw`, so console output is not visible.
- Keep log messages high level and avoid credentials or session data. Runtime profile and logs are ignored through `.gitignore`.

## Comments

**When to Comment:**
- Comment non-obvious platform or UI behavior. `CodexBalanceWidget._install_blank_icon` explains the Windows/Tk transparent icon workaround in `codex_balance_widget_chrome.py`.
- Comment parser branches where examples matter. `parse_reset_datetime` documents supported English and localized date text formats in `codex_balance_widget_chrome.py`.
- Avoid comments for simple assignments and Tkinter widget construction unless they explain a workaround or external behavior.

**JSDoc/TSDoc:**
- Not applicable. This repository is Python and Windows script based.
- Use Python docstrings for public parsing/compatibility helpers where behavior is not obvious: `BalanceParser.parse`, `parse_balance`, `usage_color`, and `parse_reset_datetime` in `codex_balance_widget_chrome.py`.

## Function Design

**Size:** Keep new pure helpers small and testable. Existing parsing and formatting helpers such as `safe_int`, `normalize_reset_text`, `parse_reset_datetime`, `format_countdown`, and `looks_like_login_page` in `codex_balance_widget_chrome.py` are the preferred model for new logic.

**Parameters:** Prefer typed parameters and keyword-only options for behavioral switches. Existing examples include `parse_reset_datetime(reset_text, *, now=None)`, `CodexUsageBrowser.fetch(*, allow_visible_debug=False)`, and `CodexUsageBrowser._fetch_once(*, visible, wait_for_login)`.

**Return Values:** Prefer simple dataclasses or explicit nullable values instead of loosely shaped tuples. Use `Balance`, `FetchResult`, and `UsageWaitResult` from `codex_balance_widget_chrome.py` for new related data flow.

## Module Design

**Exports:** There is no formal package API. The useful importable surface in `codex_balance_widget_chrome.py` is the pure parser/formatter/storage helpers: `Balance`, `BalanceParser`, `parse_balance`, `safe_int`, `parse_reset_datetime`, `format_countdown`, `SettingsStore`, and `HistoryStore`.

**Barrel Files:** Not used. There is no package directory or `__init__.py`.

**Prescriptive Placement:**
- Add parser and formatting helpers near the existing helper block in `codex_balance_widget_chrome.py` before `BalanceParser`.
- Add persistence changes inside `SettingsStore` or `HistoryStore` in `codex_balance_widget_chrome.py`.
- Add browser automation changes inside `CodexUsageBrowser` in `codex_balance_widget_chrome.py`.
- Add Tkinter view behavior inside `CodexBalanceWidget` in `codex_balance_widget_chrome.py`.
- Keep startup orchestration in the `if __name__ == "__main__"` block of `codex_balance_widget_chrome.py`; keep hidden-launch crash handling in `codex_balance_widget_launcher.pyw`.

---

*Convention analysis: 2026-06-17*
