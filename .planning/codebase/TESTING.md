# Testing Patterns

**Analysis Date:** 2026-06-17

## Test Framework

**Runner:**
- Not detected. There is no `pytest.ini`, `pyproject.toml`, `tox.ini`, `setup.cfg`, `unittest` suite, or `tests/` directory.
- `requirements.txt` includes `playwright>=1.40`, `pystray>=0.19.5`, and `Pillow>=10.0.0`, but no test-only packages.

**Assertion Library:**
- Not detected. Use Python's built-in `assert` if adding `pytest`, or `unittest.TestCase` assertions if staying in the standard library.

**Run Commands:**
```bash
# No automated test command is configured.
py -3 codex_balance_widget_chrome.py              # Manual foreground smoke run from `README.md`
install.bat                                      # Install runtime dependencies from `requirements.txt`
run.bat                                          # User-facing hidden launch path through `run_hidden.vbs`
```

## Test File Organization

**Location:**
- No test files are present. Add automated tests under a new `tests/` directory at repository root.
- Keep tests repo-root importable against `codex_balance_widget_chrome.py`, because the application currently has no package directory.

**Naming:**
- Use `test_*.py` for future Python tests: `tests/test_parser.py`, `tests/test_settings_store.py`, `tests/test_history_store.py`, `tests/test_browser_status.py`.

**Structure:**
```text
tests/
├── test_parser.py          # `BalanceParser`, `parse_reset_datetime`, `format_countdown`
├── test_settings_store.py  # `SettingsStore` validation and atomic save behavior
├── test_history_store.py   # `HistoryStore` retention, dedupe, latest balance
└── test_browser_status.py  # `looks_like_login_page` and browser status decisions with mocks
```

## Test Structure

**Suite Organization:**
```python
from datetime import datetime

from codex_balance_widget_chrome import BalanceParser, parse_reset_datetime, safe_int


def test_safe_int_clamps_percentages():
    assert safe_int("-5") == 0
    assert safe_int("42") == 42
    assert safe_int("120") == 100


def test_parse_reset_datetime_accepts_english_absolute_date():
    parsed = parse_reset_datetime("Reset Jun 7, 2026 18:33")
    assert parsed == datetime(2026, 6, 7, 18, 33)


def test_balance_parser_extracts_usage_values():
    balance = BalanceParser.parse(
        "5-hour usage limit 87% remaining Weekly usage limit 42% remaining Credits remaining 12"
    )
    assert balance.five_hour_percent == "87"
    assert balance.weekly_percent == "42"
    assert balance.credits == "12"
```

**Patterns:**
- Prefer pure unit tests for helpers in `codex_balance_widget_chrome.py` before UI or browser tests.
- Pass deterministic `now=` values into `parse_reset_datetime` and `format_countdown`-adjacent tests where time affects output.
- Use temporary paths and monkeypatching for `SETTINGS_PATH`, `HISTORY_PATH`, and `LOG_PATH` when testing `SettingsStore` and `HistoryStore`.
- Avoid launching Tkinter or Chrome in unit tests. Test `CodexBalanceWidget` behavior through extracted helpers where possible.

## Mocking

**Framework:** Not detected. If adding `pytest`, use `monkeypatch` and `tmp_path`; if using only the standard library, use `unittest.mock`.

**Patterns:**
```python
from codex_balance_widget_chrome import HistoryStore, Balance


def test_history_append_uses_temp_history_file(monkeypatch, tmp_path):
    history_path = tmp_path / "history.json"
    monkeypatch.setattr("codex_balance_widget_chrome.HISTORY_PATH", history_path)

    items = HistoryStore.append_balance(Balance(weekly_percent="50"))

    assert len(items) == 1
    assert items[0]["weekly_percent"] == 50
```

**What to Mock:**
- Mock `codex_balance_widget_chrome.HISTORY_PATH`, `SETTINGS_PATH`, and `LOG_PATH` for file-based tests.
- Mock `codex_balance_widget_chrome.has_saved_chrome_session` and Playwright calls for `CodexUsageBrowser` behavior tests.
- Mock `CodexUsageBrowser.fetch` when testing `CodexBalanceWidget.fetch_once` without a real browser.
- Mock Tkinter components or avoid constructing `CodexBalanceWidget` for non-UI tests.

**What NOT to Mock:**
- Do not mock `BalanceParser.parse`, `safe_int`, `normalize_reset_text`, `parse_reset_datetime`, or `looks_like_login_page`; these are pure logic and should be tested directly.
- Do not use a real `codex_chrome_profile/` in automated tests. `.gitignore` marks it as runtime state, and it may contain authenticated browser session data.
- Do not write tests that depend on the live ChatGPT Codex Usage page for unit coverage. Use fixture text for parser behavior and reserve live browser checks for manual smoke testing.

## Fixtures and Factories

**Test Data:**
```python
from codex_balance_widget_chrome import Balance


def make_balance(
    five_hour_percent="80",
    weekly_percent="60",
    credits="10",
    weekly_reset_text="Reset Jun 14, 2026 18:33",
):
    return Balance(
        five_hour_percent=five_hour_percent,
        weekly_percent=weekly_percent,
        credits=credits,
        weekly_reset_text=weekly_reset_text,
    )
```

**Location:**
- No fixture directory exists. Put small fixtures inline in each test module until duplication justifies `tests/conftest.py`.
- Store representative page text fixtures in `tests/fixtures/` only if parser samples become large.

## Coverage

**Requirements:** None enforced. No coverage tool or threshold is configured.

**View Coverage:**
```bash
# Not configured.
# If coverage is introduced later:
py -3 -m pytest --cov=codex_balance_widget_chrome tests
```

## Test Types

**Unit Tests:**
- Primary missing coverage target. Add direct tests for pure helpers in `codex_balance_widget_chrome.py`: `safe_int`, `usage_color`, `normalize_reset_text`, `parse_reset_datetime`, `format_target_time`, `format_countdown`, `looks_like_login_page`, and `BalanceParser.parse`.
- Add file-isolated unit tests for `SettingsStore` and `HistoryStore` in `codex_balance_widget_chrome.py` using temporary JSON files.

**Integration Tests:**
- Not present. Add mocked integration tests for `CodexUsageBrowser.fetch` and `_wait_for_usage_text` in `codex_balance_widget_chrome.py` using fake page objects before adding live Playwright tests.
- A live Playwright smoke test may verify installed Chrome and the dedicated profile path, but it must be opt-in because it can open Chrome and depend on local authentication.

**E2E Tests:**
- Not used. Current end-to-end verification is manual through `install.bat`, `run.bat`, and the debug command from `README.md`.
- Manual smoke flow: run `py -3 codex_balance_widget_chrome.py`, sign in if needed, verify usage values render, verify tray menu actions, open diagnostics, and exit through the tray menu.

## Common Patterns

**Async Testing:**
```python
import pytest

from codex_balance_widget_chrome import CodexUsageBrowser, FetchResult


@pytest.mark.asyncio
async def test_fetch_returns_background_result_when_session_exists(monkeypatch):
    browser = CodexUsageBrowser("C:/Chrome/chrome.exe", lambda message: None)

    monkeypatch.setattr("codex_balance_widget_chrome.has_saved_chrome_session", lambda: True)

    async def fake_fetch_once(*, visible, wait_for_login):
        assert visible is False
        assert wait_for_login is False
        return FetchResult("ok", text="5-hour usage limit 90% remaining")

    monkeypatch.setattr(browser, "_fetch_once", fake_fetch_once)

    result = await browser.fetch()

    assert result.status == "ok"
```

**Error Testing:**
```python
from codex_balance_widget_chrome import parse_iso_datetime, safe_int, SettingsStore


def test_parse_iso_datetime_returns_none_for_invalid_text():
    assert parse_iso_datetime("not a date") is None


def test_settings_load_falls_back_for_invalid_json(monkeypatch, tmp_path):
    settings_path = tmp_path / "settings.json"
    settings_path.write_text("{not-json", encoding="utf-8")
    monkeypatch.setattr("codex_balance_widget_chrome.SETTINGS_PATH", settings_path)

    settings = SettingsStore.load()

    assert settings["geometry"] == "360x360+80+80"
```

---

*Testing analysis: 2026-06-17*
