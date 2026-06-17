# Codebase Concerns

**Analysis Date:** 2026-06-17

## Tech Debt

**Single-file application core:**
- Issue: UI construction, tray integration, browser automation, persistence, parsing, diagnostics, Windows single-instance behavior, and process startup all live in one 2,119-line module.
- Files: `codex_balance_widget_chrome.py`
- Impact: Changes in one area require loading the whole application context, increase regression risk, and make targeted testing hard. Parser or browser fixes can accidentally affect Tk lifecycle or tray behavior.
- Fix approach: Split by responsibility into parser, stores, browser client, tray/UI, and Windows process helpers. Keep `codex_balance_widget_chrome.py` as a thin entry point that wires these modules together.

**Regex parser tied to exact page copy:**
- Issue: Usage extraction depends on exact English/Russian visible text and reset labels instead of a stable data contract.
- Files: `codex_balance_widget_chrome.py:491`, `codex_balance_widget_chrome.py:555`, `codex_balance_widget_chrome.py:563`, `codex_balance_widget_chrome.py:595`, `README.md:112`
- Impact: Any ChatGPT/Codex Usage page wording, language, accessibility text, or layout change can make the widget show stale data or "Data not recognized" even when the account is valid.
- Fix approach: Add parser fixture tests from captured `body.inner_text()` samples, isolate selectors/text extraction from `BalanceParser`, and prefer stable DOM landmarks if available.

**Unpinned dependency range:**
- Issue: Runtime dependencies use minimum versions only.
- Files: `requirements.txt`, `install.bat:4`
- Impact: A new `playwright`, `pystray`, or `Pillow` release can change browser launch, tray behavior, or image/font rendering without a repository change.
- Fix approach: Pin tested versions or add a lock/constraints file. Update via deliberate dependency maintenance with a smoke test against startup, tray rendering, and a mocked usage-page parse.

**Global runtime paths rooted in repository directory:**
- Issue: Chrome profile, settings, history, lock, and logs are written beside the source tree.
- Files: `codex_balance_widget_chrome.py:52`, `codex_balance_widget_chrome.py:54`, `codex_balance_widget_chrome.py:55`, `codex_balance_widget_chrome.py:56`, `codex_balance_widget_chrome.py:57`, `codex_balance_widget_chrome.py:58`, `.gitignore`
- Impact: Running from a protected, synced, shared, or archived directory can fail writes, sync sensitive browser state, or make source cleanup riskier.
- Fix approach: Move runtime state under a per-user application data directory by default and keep a migration path for existing `codex_chrome_profile`, settings, and history.

**Hidden startup path depends on global Python environment:**
- Issue: `install.bat` installs into whatever `py -3` resolves, and `run_hidden.vbs` starts `pyw.exe -3` without validating the interpreter or dependency set.
- Files: `install.bat:4`, `run_hidden.vbs:7`, `codex_balance_widget_launcher.pyw:24`, `README.md:104`
- Impact: Multiple Python installations or missing PATH/Python Launcher setup can produce a silent failure where double-clicking appears to do nothing.
- Fix approach: Use a local virtual environment launcher or validate interpreter/dependencies before hidden startup. Show a visible error path when the launcher cannot start Python or import dependencies.

## Known Bugs

**Hidden launcher swallows visible startup failures:**
- Symptoms: If imports, file permissions, Tk startup, or Playwright setup fail before the window is created, the hidden `.pyw` path logs the traceback but does not show the user an error.
- Files: `codex_balance_widget_launcher.pyw:21`, `codex_balance_widget_launcher.pyw:25`, `run_hidden.vbs:7`
- Trigger: Start via `run.bat` or `run_hidden.vbs` with a broken interpreter, missing dependency, unreadable script, or runtime exception before Tk is visible.
- Workaround: Run `py -3 codex_balance_widget_chrome.py` directly from a terminal and inspect `widget_launch.log`.

**Background refresh failure can leave users on stale data:**
- Symptoms: The widget keeps displaying the last saved balance when headless refresh returns `browser_error`, `not_ready`, `login_required`, or unrecognized page text.
- Files: `codex_balance_widget_chrome.py:838`, `codex_balance_widget_chrome.py:862`, `codex_balance_widget_chrome.py:2045`, `codex_balance_widget_chrome.py:2058`
- Trigger: ChatGPT session expiration, Usage page copy/layout changes, Chrome launch failures, network delays beyond 45 seconds, or parser misses.
- Workaround: Use manual Refresh to open visible Chrome for inspection, then re-authenticate or update parser patterns.

**Startup lock file can be truncated by a second instance:**
- Symptoms: A second process opens the lock file in write mode before acquiring the nonblocking lock, so the PID text from the active instance can be overwritten even though the lock itself remains effective.
- Files: `codex_balance_widget_chrome.py:234`, `codex_balance_widget_chrome.py:235`, `codex_balance_widget_chrome.py:237`, `codex_balance_widget_chrome.py:242`
- Trigger: Launch a second instance while the first instance is already running.
- Workaround: Operationally harmless for single-instance enforcement, but diagnostics may show an empty or misleading `codex_balance_widget.lock`.

## Security Considerations

**Local Chrome profile stores authenticated session material:**
- Risk: The dedicated Chrome profile contains cookies/session data for ChatGPT and can grant access if copied from the machine.
- Files: `codex_balance_widget_chrome.py:54`, `codex_balance_widget_chrome.py:300`, `codex_balance_widget_chrome.py:876`, `.gitignore`, `README.md:73`
- Current mitigation: The profile uses a separate directory from the user's primary Chrome profile and is excluded from Git via `.gitignore`.
- Recommendations: Store the profile under per-user app data with clear permissions, add an explicit "clear session/profile" action, and keep warnings in docs and diagnostics.

**Diagnostics expose local paths and account-derived usage data:**
- Risk: Copying diagnostics can reveal absolute filesystem paths, Chrome path, history file state, last fetch errors, usage percentages, reset text, and credits.
- Files: `codex_balance_widget_chrome.py:1914`, `codex_balance_widget_chrome.py:1964`, `codex_balance_widget_chrome.py:1965`, `codex_balance_widget_chrome.py:1974`, `codex_balance_widget_chrome.py:1978`, `codex_balance_widget_chrome.py:1982`, `codex_balance_widget_chrome.py:1986`
- Current mitigation: Diagnostics are local-only and copied manually by the user.
- Recommendations: Add a redacted copy mode that omits absolute paths, account-derived values, and detailed exception messages unless explicitly requested.

**Log file has no redaction or rotation:**
- Risk: Browser exceptions and tracebacks are appended indefinitely and may include URLs, local paths, and environment-specific details.
- Files: `codex_balance_widget_chrome.py:225`, `codex_balance_widget_chrome.py:896`, `codex_balance_widget_chrome.py:900`, `codex_balance_widget_launcher.pyw:15`, `codex_balance_widget_launcher.pyw:25`
- Current mitigation: `widget_launch.log` is ignored by Git via `.gitignore`.
- Recommendations: Add size-based rotation and redact known sensitive values before writing browser exceptions or startup traces.

## Performance Bottlenecks

**Full Chrome context launch on every refresh:**
- Problem: Each refresh starts a persistent Chrome context, navigates to the Usage page, waits for network idle/body text, then closes the context.
- Files: `codex_balance_widget_chrome.py:868`, `codex_balance_widget_chrome.py:876`, `codex_balance_widget_chrome.py:882`, `codex_balance_widget_chrome.py:904`, `codex_balance_widget_chrome.py:2062`
- Cause: The app uses browser automation as the data source and has no lower-cost API or cached DOM data path.
- Improvement path: Keep this as the correctness fallback, but measure refresh duration and resource use. If stable enough, reuse a browser context across refreshes or add a narrower extraction path with timeout telemetry.

**Log growth is unbounded:**
- Problem: Every startup, browser failure, tray failure, and unexpected exception appends to one log file.
- Files: `codex_balance_widget_chrome.py:225`, `codex_balance_widget_launcher.pyw:15`, `.gitignore`
- Cause: `write_log` always opens `widget_launch.log` in append mode and no cleanup path exists.
- Improvement path: Rotate or cap `widget_launch.log`, and expose current size in diagnostics with a "clear log" action.

**History is fully loaded and rewritten for every append:**
- Problem: History append reads the entire JSON file, filters it, appends one item, and rewrites the full file.
- Files: `codex_balance_widget_chrome.py:726`, `codex_balance_widget_chrome.py:741`, `codex_balance_widget_chrome.py:750`
- Cause: History is a single JSON array with atomic temp-file replacement.
- Improvement path: This is acceptable at the current 21-day retention window. If retention increases, switch to JSONL or SQLite and keep a compaction policy.

## Fragile Areas

**Browser automation and login detection:**
- Files: `codex_balance_widget_chrome.py:826`, `codex_balance_widget_chrome.py:838`, `codex_balance_widget_chrome.py:904`, `codex_balance_widget_chrome.py:630`
- Why fragile: The flow relies on `body.inner_text()`, URL heuristics, login marker words, and page readiness timing from a private web app.
- Safe modification: Add captured page-text fixtures before changing `looks_like_login_page`, `_wait_for_usage_text`, or `BalanceParser`. Keep visible-debug fallback working for every non-OK status.
- Test coverage: No automated tests are detected for parser fixtures, login detection, or browser fallback behavior.

**Tk UI and async worker lifecycle:**
- Files: `codex_balance_widget_chrome.py:1312`, `codex_balance_widget_chrome.py:1313`, `codex_balance_widget_chrome.py:1727`, `codex_balance_widget_chrome.py:2062`, `codex_balance_widget_chrome.py:2073`, `codex_balance_widget_chrome.py:2091`
- Why fragile: A daemon thread runs the asyncio loop, `refresh_loop` is infinite, and shutdown stops the loop without cancelling in-flight tasks or joining the worker.
- Safe modification: Centralize task creation/cancellation, guard all UI callbacks after `root.destroy`, and add a shutdown smoke test that exits during idle and during an active fetch.
- Test coverage: No automated tests or scripted lifecycle checks are present.

**Runtime JSON persistence:**
- Files: `codex_balance_widget_chrome.py:653`, `codex_balance_widget_chrome.py:693`, `codex_balance_widget_chrome.py:726`, `codex_balance_widget_chrome.py:741`
- Why fragile: Corrupt settings are silently reset to defaults, corrupt history is discarded in memory, and no backup or user-facing recovery message is shown.
- Safe modification: Preserve a `.bad` copy before overwriting, log a concise recovery message, and show diagnostics when settings/history fail to parse.
- Test coverage: No tests cover corrupt JSON, unwritable runtime files, atomic replacement failures, or geometry validation.

**Tray integration is optional but broad:**
- Files: `codex_balance_widget_chrome.py:39`, `codex_balance_widget_chrome.py:1203`, `codex_balance_widget_chrome.py:1493`, `codex_balance_widget_chrome.py:1527`
- Why fragile: Tray behavior depends on `pystray`, `Pillow`, platform font availability, and cross-thread callbacks into Tk.
- Safe modification: Keep tray failures non-fatal, exercise both with-tray and no-tray paths, and verify close/minimize/exit behavior after changing tray menu callbacks.
- Test coverage: No automated or manual checklist artifact covers tray startup, tooltip rendering, or exit semantics.

## Scaling Limits

**Single account and single profile:**
- Current capacity: One dedicated Chrome profile at `codex_chrome_profile` and one global app instance per source directory.
- Files: `codex_balance_widget_chrome.py:54`, `codex_balance_widget_chrome.py:60`, `codex_balance_widget_chrome.py:234`, `codex_balance_widget_chrome.py:2105`
- Limit: Multiple ChatGPT accounts, multiple widgets, or separate workspaces cannot be configured without cloning directories or editing code.
- Scaling path: Add profile/account IDs to settings and derive profile, lock, event, history, and settings paths per configured account.

**History retention is fixed at 21 days:**
- Current capacity: History keeps recent points only and filters anything older than 21 days on append.
- Files: `codex_balance_widget_chrome.py:761`, `codex_balance_widget_chrome.py:768`, `codex_balance_widget_chrome.py:1032`
- Limit: Long-term usage trends, monthly analysis, and comparisons across multiple weekly cycles are unavailable.
- Scaling path: Make retention configurable and move chart aggregation out of raw history storage.

**Refresh cadence is local-only and coarse:**
- Current capacity: Settings allow 1 to 60 minutes, defaulting to 5 minutes.
- Files: `codex_balance_widget_chrome.py:68`, `codex_balance_widget_chrome.py:685`, `codex_balance_widget_chrome.py:706`, `codex_balance_widget_chrome.py:1838`
- Limit: There is no backoff after repeated failures, no jitter, and no awareness of reset times or app idle state.
- Scaling path: Add adaptive scheduling with failure backoff, reset-time refresh hints, and visible status for next scheduled refresh.

## Dependencies at Risk

**ChatGPT/Codex Usage page:**
- Risk: The app depends on a private web page rather than an official stable API.
- Files: `codex_balance_widget_chrome.py:53`, `codex_balance_widget_chrome.py:882`, `codex_balance_widget_chrome.py:914`, `README.md:112`
- Impact: Layout, copy, auth, bot-detection, or navigation changes can break refresh without dependency version changes.
- Migration plan: Track fixtures from known page states and move to an official API if one becomes available.

**Playwright with system Chrome:**
- Risk: The app intentionally does not install Playwright Chromium and instead launches the locally installed Google Chrome.
- Files: `requirements.txt`, `install.bat:6`, `codex_balance_widget_chrome.py:285`, `codex_balance_widget_chrome.py:876`, `README.md:45`
- Impact: Chrome path differences, enterprise policies, profile locking, or browser updates can break automation.
- Migration plan: Keep `CHROME_PATH` support, add clearer detection diagnostics, and consider an optional managed browser install for users who prefer reproducibility.

**pystray/Pillow tray stack:**
- Risk: Tray and icon rendering are optional runtime dependencies with platform-specific behavior.
- Files: `requirements.txt`, `codex_balance_widget_chrome.py:39`, `codex_balance_widget_chrome.py:1203`, `codex_balance_widget_chrome.py:1493`
- Impact: Tray icon startup or rendering can fail while the main Tk window still works.
- Migration plan: Maintain tray as optional, keep no-tray UX complete, and pin/test known-good versions on Windows.

## Missing Critical Features

**Automated tests:**
- Problem: No test files, test runner config, parser fixtures, or smoke scripts are present.
- Blocks: Safe parser changes, dependency upgrades, lifecycle refactors, and regression checks for settings/history recovery.
- Files: `codex_balance_widget_chrome.py`, `requirements.txt`

**Structured diagnostics export with redaction:**
- Problem: Diagnostics are a manually copied text blob with local paths and usage data.
- Blocks: Safe support sharing and automated issue triage.
- Files: `codex_balance_widget_chrome.py:1859`, `codex_balance_widget_chrome.py:1914`

**Packaged install/update path:**
- Problem: Installation is a one-step global `pip install` and runtime uses scripts in the source directory.
- Blocks: Reproducible installs, user-level upgrades, rollback, and reliable startup on machines with multiple Python versions.
- Files: `install.bat`, `run.bat`, `run_hidden.vbs`, `codex_balance_widget_launcher.pyw`

## Test Coverage Gaps

**Parser and reset-date handling:**
- What's not tested: English/Russian usage labels, reset text variants, time-only reset parsing, malformed text, and fallback ordering between five-hour and weekly reset matches.
- Files: `codex_balance_widget_chrome.py:345`, `codex_balance_widget_chrome.py:491`, `codex_balance_widget_chrome.py:563`, `codex_balance_widget_chrome.py:595`
- Risk: UI can silently show stale or missing data after page-copy changes.
- Priority: High

**Browser fetch state machine:**
- What's not tested: Saved-session detection, headless failure fallback, visible-login flow, timeout handling, redirect back to Usage, and `needs_visible_debug`.
- Files: `codex_balance_widget_chrome.py:300`, `codex_balance_widget_chrome.py:838`, `codex_balance_widget_chrome.py:868`, `codex_balance_widget_chrome.py:904`
- Risk: Users can get stuck in stale-data or hidden-failure states without a reliable recovery path.
- Priority: High

**Persistence and corruption recovery:**
- What's not tested: Invalid settings JSON, invalid history JSON, unwritable files, temp-file replacement failure, geometry validation, and retention filtering.
- Files: `codex_balance_widget_chrome.py:653`, `codex_balance_widget_chrome.py:693`, `codex_balance_widget_chrome.py:726`, `codex_balance_widget_chrome.py:741`, `codex_balance_widget_chrome.py:750`
- Risk: User settings/history can be reset or discarded without clear user feedback.
- Priority: Medium

**Windows startup and single-instance behavior:**
- What's not tested: `run_hidden.vbs`, `.pyw` launcher logging, lock acquisition failure, activation event signaling, and stale lock file presentation.
- Files: `run.bat`, `run_hidden.vbs`, `codex_balance_widget_launcher.pyw`, `codex_balance_widget_chrome.py:234`, `codex_balance_widget_chrome.py:247`, `codex_balance_widget_chrome.py:267`, `codex_balance_widget_chrome.py:2105`
- Risk: Desktop startup failures are hard to diagnose and duplicate launches may not reliably foreground the existing window.
- Priority: Medium

**Tray/UI lifecycle:**
- What's not tested: No-tray mode, tray menu callbacks, close-to-tray behavior, exit cleanup, countdown updates, and cross-thread UI scheduling after shutdown.
- Files: `codex_balance_widget_chrome.py:1493`, `codex_balance_widget_chrome.py:1544`, `codex_balance_widget_chrome.py:1571`, `codex_balance_widget_chrome.py:1717`, `codex_balance_widget_chrome.py:2067`, `codex_balance_widget_chrome.py:2073`
- Risk: UI can fail only on end-user machines where tray dependencies, fonts, and Windows shell behavior differ.
- Priority: Medium

---

*Concerns audit: 2026-06-17*
