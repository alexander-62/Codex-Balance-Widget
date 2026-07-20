---
phase: 01-json-endpoint-probe
reviewed: 2026-07-20T00:00:00Z
depth: standard
files_reviewed: 3
files_reviewed_list:
  - probe_wham_usage.py
  - test_probe_wham_usage.py
  - wham_usage_fixture.json
findings:
  critical: 2
  warning: 3
  info: 3
  total: 8
status: issues_found
---

# Phase 01: Code Review Report

**Reviewed:** 2026-07-20T00:00:00Z
**Depth:** standard
**Files Reviewed:** 3
**Status:** issues_found

## Summary

Reviewed the stdlib-only `wham/usage` probe (`probe_wham_usage.py`), its unit tests (`test_probe_wham_usage.py`), and the checked-in redacted fixture (`wham_usage_fixture.json`).

The redaction design is thoughtful (deny-list + substring match + a `redaction_clean()` post-check), and most defensive coding around missing/null JSON keys is solid and well-tested. However, the safety-net pattern is applied **inconsistently**: the fixture-write path verifies redaction before writing to disk, but the stdout print path — which the module docstring explicitly promises is safe "including under --debug" — has no equivalent verification. Separately, `collect_windows()` assumes `rate_limit` and each `additional_rate_limits[]` entry are dicts once they're truthy; a non-dict value in either position raises an uncaught `AttributeError` that escapes the single `except ProbeError` handler in `main()`, defeating the tool's "one Russian diagnostic message on any failure" contract. Test coverage for the unhappy paths (`fetch_usage()` HTTP error branches, `main()` end-to-end) is entirely absent, and one existing assertion is too weak to catch a formatting regression.

## Critical Issues

### CR-01: Redacted payload printed to stdout without the `redaction_clean()` safety-net check

**File:** `probe_wham_usage.py:365-366`
**Issue:** `write_fixture()` (lines 324-336) treats `redact()` as fallible: it re-serializes the redacted payload and runs `redaction_clean(text)` before writing anything to disk, refusing to write if a stray `eyJ`/`@` slipped through. The stdout path does not apply this same check — `main()` calls `redact(payload)` and immediately `print()`s the JSON dump with no verification step:

```python
redacted_payload = redact(payload)
print(json.dumps(redacted_payload, ensure_ascii=False, indent=2))
```

`redact()` only strips values whose **key** exactly matches `REDACT_KEYS` or contains the substring `"token"`. Any new/renamed field in a future API response (e.g. `owner_email`, `bearer`, `id_token_jwt` vs. an unexpected wrapper key) would sail through unredacted and be printed straight to the terminal/logs — exactly the leak class the fixture path was hardened against. The module docstring's stated guarantee ("kept out of stdout, logs and any error message, including under --debug") is only actually enforced for one of the two output paths.

**Fix:** Reuse the same guard for stdout, e.g.:
```python
redacted_payload = redact(payload)
text = json.dumps(redacted_payload, ensure_ascii=False, indent=2)
if not redaction_clean(text):
    raise ProbeError(
        "Редакция вывода не прошла пост-проверку (eyJ/@) — вывод скрыт."
    )
print(text)
```

### CR-02: `collect_windows()` crashes on non-dict `rate_limit` / `additional_rate_limits[]` entries, escaping the single-error-message contract

**File:** `probe_wham_usage.py:129, 134-139`
**Issue:** The docstring claims collection is "Defensive against nulls/missing keys at every level," and `payload.get("rate_limit") or {}` does guard against `None`/missing — but not against a **truthy non-dict** value:

```python
rate_limit = payload.get("rate_limit") or {}
for slot in ("primary_window", "secondary_window"):
    window = rate_limit.get(slot)   # AttributeError if rate_limit is e.g. a string/list
```

Same pattern for `additional_rate_limits`:
```python
for extra in payload.get("additional_rate_limits") or []:
    inner = (extra or {}).get("rate_limit") or {}   # AttributeError if extra is not a dict
```

If the API ever returns a malformed/partial payload shape (a real risk for a probe explicitly built to survive schema drift — see the module's own defensive framing and RESEARCH.md Pitfall 1), this raises an uncaught `AttributeError` inside `extract_fields()` (called from `main()` at line 368). `main()`'s `except` clause only catches `ProbeError`:
```python
except ProbeError as exc:
    print(str(exc))
    ...
```
so the `AttributeError` propagates as an unhandled exception with a raw Python traceback instead of the tool's documented single Russian diagnostic message — a crash on attacker/service-controlled input shape, not just a cosmetic issue.

**Fix:** Validate types the same way `isinstance(window, dict)` is already used a few lines later:
```python
rate_limit = payload.get("rate_limit")
rate_limit = rate_limit if isinstance(rate_limit, dict) else {}
...
for extra in payload.get("additional_rate_limits") or []:
    if not isinstance(extra, dict):
        continue
    inner = extra.get("rate_limit")
    inner = inner if isinstance(inner, dict) else {}
```

## Warnings

### WR-01: `main()` has no fallback for non-`ProbeError` exceptions

**File:** `probe_wham_usage.py:391-395`
**Issue:** Even after fixing CR-02, any future exception type raised inside the try block (e.g. a `KeyError`, `TypeError`, or a third-party edge case) will bypass the diagnostic contract entirely, since only `ProbeError` is caught. This is a structural gap independent of any single bug: the tool has no defense-in-depth against "something I didn't anticipate raised."
**Fix:** Add a catch-all fallback that still respects the "no secrets in output" contract:
```python
except ProbeError as exc:
    print(str(exc))
    if args.debug:
        traceback.print_exc()
    return 1
except Exception as exc:  # noqa: BLE001 - last-resort diagnostic, never leaks token
    print(f"Непредвиденная ошибка: {exc}")
    if args.debug:
        traceback.print_exc()
    return 1
```

### WR-02: Weak test assertion doesn't actually validate reset-time formatting

**File:** `test_probe_wham_usage.py:117`
**Issue:**
```python
self.assertIn("20", fields["weekly_reset_text"])
```
`reset_at = 1784792381` should format to a specific `YYYY-MM-DD HH:MM` string via `_reset_text()`. Asserting that the output merely contains the substring `"20"` is nearly tautological — it will pass for almost any date in the 2000s or any time containing `:20`, `20:` etc., and would silently pass even if the format string were broken (e.g. wrong separators, swapped month/day, wrong year). This test does not actually protect against a formatting regression.
**Fix:** Assert the full expected value computed the same way the code does:
```python
expected = datetime.fromtimestamp(1784792381).strftime("%Y-%m-%d %H:%M")
self.assertEqual(fields["weekly_reset_text"], expected)
```

### WR-03: No test coverage for `fetch_usage()` error branches or `main()`

**File:** `test_probe_wham_usage.py` (whole file)
**Issue:** The test suite thoroughly covers pure functions (`collect_windows`, `pick_window`, `extract_fields`, `redact`, `jwt_exp`, `load_tokens`, `write_fixture`), but `fetch_usage()` — which contains the most branch-heavy, highest-risk logic (401/403/429 handling, Cloudflare HTML detection, JSON content-type validation, timeout classification) — and `main()` (argument parsing, control flow, the CR-01 stdout path) have zero test coverage. This is exactly the code most likely to regress silently, since it's also the part most dependent on `urllib` exception semantics (see IN-01).
**Fix:** Mock `urllib.request.urlopen` (e.g. via `unittest.mock.patch`) to simulate each `HTTPError` code path and a non-JSON `Content-Type`, and add an integration-style test for `main()` using a fake `urlopen` plus a temp `CODEX_HOME`.

## Info

### IN-01: `except TimeoutError` branch in `fetch_usage()` may rarely trigger, and connection-timeout wording is imprecise

**File:** `probe_wham_usage.py:306-309`
**Issue:** `urllib.request.urlopen` typically wraps a connection-phase timeout as `URLError(reason=<TimeoutError>)`, which is caught by the earlier `except urllib.error.URLError` branch and reported as `"Нет соединения с chatgpt.com: {exc.reason}"` — a "no connection" message for what is actually a timeout. The dedicated `except TimeoutError` branch below it is reachable only for timeouts that occur outside `urlopen`'s own wrapping (e.g. certain read-phase timeouts), making its distinct, more accurate message ("chatgpt.com не ответил за N с") the less likely of the two to actually surface.
**Fix:** Not required to fix, but consider checking `isinstance(exc.reason, TimeoutError)` inside the `URLError` handler to route to the more accurate timeout message.

### IN-02: Reset timestamps rendered in naive local time with no timezone indicator

**File:** `probe_wham_usage.py:164, 383`
**Issue:** `_reset_text()` uses `datetime.fromtimestamp(reset_at).strftime("%Y-%m-%d %H:%M")`, which renders in the machine's local timezone but the output string gives no indication of which timezone that is. A user comparing this against another tool's UTC-labeled output could misread the reset time.
**Fix:** Consider appending a timezone abbreviation (`%Z`) or documenting that the time is local, e.g. `strftime("%Y-%m-%d %H:%M %Z")` (requires an aware datetime) or a trailing `" (local)"` suffix.

### IN-03: Success output and a later failure message can be mixed in the same stdout stream

**File:** `probe_wham_usage.py:365-388`
**Issue:** The redacted JSON dump and extracted fields are printed (lines 365-383) *before* `write_fixture()` runs (lines 385-388). If `write_fixture()` raises `ProbeError` (e.g. the CR-01-adjacent `redaction_clean` post-check fails on the fixture write), the outer handler prints an additional error line and the process exits with code 1 — but the earlier "successful-looking" JSON/fields output is already on stdout. A downstream consumer that only checks for JSON-shaped output (rather than the exit code) could be misled into thinking the run fully succeeded.
**Fix:** Consider deferring the JSON/fields print until after `write_fixture()` succeeds (or gating success-looking output strictly behind exit code 0 in any downstream consumer's contract).

---

_Reviewed: 2026-07-20T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
