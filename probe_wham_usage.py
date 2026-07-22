"""Standalone stdlib probe for the Codex ChatGPT backend `wham/usage` endpoint.

Reads the OAuth access token from $CODEX_HOME/auth.json (the same session
file Codex CLI itself maintains), sends a single
`GET https://chatgpt.com/backend-api/wham/usage` request with a Bearer
token, classifies rate-limit windows by `limit_window_seconds` (never by
primary/secondary position — see 01-RESEARCH.md), extracts fields for the
`Balance` model used by codex_balance_widget_chrome.py, prints a redacted
pretty-printed JSON payload plus the extracted fields, and writes a
redacted fixture file.

The access token is kept out of stdout, logs and any error message,
including under --debug.

Only stdlib is used: json, os, sys, base64, argparse, urllib.request,
urllib.error, datetime, pathlib.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import traceback
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any

_SIBLING_COMMON = Path(__file__).resolve().parent.parent / "usage_widget_common"
if str(_SIBLING_COMMON) not in sys.path:
    sys.path.insert(0, str(_SIBLING_COMMON))

from usage_widget_common.errors import FetchError
from usage_widget_common.redaction import redact as _redact_generic, redaction_clean

USAGE_URL = "https://chatgpt.com/backend-api/wham/usage"
FIVE_HOUR_SECONDS = 18000
WEEKLY_SECONDS = 604800
WINDOW_TOLERANCE_SECONDS = 1200
REQUEST_TIMEOUT_SECONDS = 15

REDACT_KEYS = frozenset(
    {
        "user_id",
        "account_id",
        "email",
        "chatgpt_user_id",
        "session_id",
        "individual_limit",
    }
)


# Alias for usage_widget_common.errors.FetchError (Phase 3 extraction) — the
# identical class object, so every existing ProbeError(...) construction,
# isinstance(x, ProbeError) check, and except ProbeError clause (in this
# file and in both test files) keeps working unchanged.
ProbeError = FetchError


def auth_json_path() -> Path:
    """Return $CODEX_HOME/auth.json, defaulting CODEX_HOME to ~/.codex."""
    codex_home = Path(os.environ.get("CODEX_HOME") or (Path.home() / ".codex"))
    return codex_home / "auth.json"


def load_tokens(path: Path) -> tuple[str, str | None]:
    """Read tokens.access_token (+ optional account_id) from auth.json.

    Never reads or returns refresh_token. Raises ProbeError with a Russian
    diagnostic message on any failure (missing file, unreadable file,
    apikey-only auth_mode, missing/empty access_token).
    """
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ProbeError(
            f"Не найден файл auth.json ({path}). Установите/запустите Codex CLI "
            "и выполните codex login."
        ) from exc
    except OSError as exc:
        raise ProbeError(f"Не удалось прочитать файл auth.json ({path}).") from exc

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ProbeError(
            f"Файл auth.json ({path}) повреждён и не разбирается как JSON."
        ) from exc

    tokens = data.get("tokens") if isinstance(data, dict) else None
    if not isinstance(tokens, dict):
        raise ProbeError(
            "auth.json без ChatGPT-токенов (auth_mode=apikey). "
            "Выполните codex login через ChatGPT-аккаунт."
        )

    access_token = tokens.get("access_token")
    if not isinstance(access_token, str) or not access_token.strip():
        raise ProbeError(
            "auth.json без ChatGPT-токенов (auth_mode=apikey). "
            "Выполните codex login через ChatGPT-аккаунт."
        )

    account_id = tokens.get("account_id")
    account_id = account_id if isinstance(account_id, str) and account_id.strip() else None

    return access_token.strip(), account_id


def jwt_exp(token: str) -> datetime | None:
    """Decode (without verifying) the JWT payload and return its exp claim.

    Returns None on any parse error or when the exp claim is absent.
    """
    try:
        payload_b64 = token.split(".")[1]
        payload_b64 += "=" * (-len(payload_b64) % 4)
        claims = json.loads(base64.urlsafe_b64decode(payload_b64))
        if "exp" not in claims:
            return None
        return datetime.fromtimestamp(claims["exp"])
    except Exception:
        return None


def collect_windows(payload: dict) -> list[dict]:
    """Collect all rate-limit windows present in the payload.

    Looks at rate_limit.primary_window / secondary_window, plus every
    additional_rate_limits[].rate_limit.{primary,secondary}_window (tagged
    with limit_name). Defensive against nulls/missing keys at every level.
    """
    out: list[dict] = []
    rate_limit = payload.get("rate_limit")
    if not isinstance(rate_limit, dict):
        rate_limit = {}
    for slot in ("primary_window", "secondary_window"):
        window = rate_limit.get(slot)
        if isinstance(window, dict):
            out.append(window)
    for extra in payload.get("additional_rate_limits") or []:
        if not isinstance(extra, dict):
            continue
        inner = extra.get("rate_limit")
        if not isinstance(inner, dict):
            inner = {}
        for slot in ("primary_window", "secondary_window"):
            window = inner.get(slot)
            if isinstance(window, dict):
                out.append({**window, "limit_name": extra.get("limit_name")})
    return out


def pick_window(
    windows: list[dict], target_seconds: int, tol: int = WINDOW_TOLERANCE_SECONDS
) -> dict | None:
    """Find the window whose limit_window_seconds is within tol of target."""
    for window in windows:
        try:
            seconds = int(window.get("limit_window_seconds", -(10**9)))
        except (TypeError, ValueError):
            continue
        if abs(seconds - target_seconds) <= tol:
            return window
    return None


def _reset_text(window: dict | None) -> str | None:
    if not window:
        return None
    reset_at = window.get("reset_at")
    if not isinstance(reset_at, (int, float)) or isinstance(reset_at, bool):
        return None
    try:
        return datetime.fromtimestamp(reset_at).strftime("%Y-%m-%d %H:%M")
    except (OverflowError, OSError, ValueError):
        return None


def _remaining_percent(window: dict | None) -> str | None:
    if not window:
        return None
    used = window.get("used_percent")
    if not isinstance(used, (int, float)) or isinstance(used, bool):
        return None
    return str(100 - int(used))


def _credits_text(credits_obj: Any) -> str | None:
    if not isinstance(credits_obj, dict):
        return None
    if credits_obj.get("unlimited"):
        return "unlimited"
    balance = credits_obj.get("balance")
    if isinstance(balance, str):
        return balance
    if isinstance(balance, (int, float)) and not isinstance(balance, bool):
        return str(balance)
    return None


def extract_fields(payload: dict) -> dict:
    """Map the raw wham/usage payload onto the Balance model's terms.

    Window classification is strictly by limit_window_seconds — an absent
    5h window is a valid result, not an error (see RESEARCH Pitfall 1).
    """
    windows = collect_windows(payload)
    five_hour = pick_window(windows, FIVE_HOUR_SECONDS)
    weekly = pick_window(windows, WEEKLY_SECONDS)

    fields = {
        "five_hour_percent": _remaining_percent(five_hour),
        "weekly_percent": _remaining_percent(weekly),
        "credits": _credits_text(payload.get("credits")),
        "five_hour_reset_text": _reset_text(five_hour),
        "weekly_reset_text": _reset_text(weekly),
        "windows": windows,
    }

    missing = [
        name
        for name, key in (
            ("five_hour", "five_hour_percent"),
            ("weekly", "weekly_percent"),
            ("credits", "credits"),
        )
        if fields[key] is None
    ]
    fields["missing"] = missing
    return fields


def redact(obj: Any) -> Any:
    """Recursively replace sensitive values with "<redacted>".

    Keys matched: REDACT_KEYS (see usage_widget_common.redaction.redact for
    the generic traversal + "token"-substring rule).
    """
    return _redact_generic(obj, REDACT_KEYS)


def build_headers(access_token: str, account_id: str | None) -> dict[str, str]:
    """Build request headers. The Bearer value is kept out of stdout entirely."""
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
        "User-Agent": "probe-wham-usage/0.1",
    }
    if account_id:
        headers["ChatGPT-Account-Id"] = account_id
    return headers


def fetch_usage(access_token: str, account_id: str | None, timeout: float) -> tuple[int, dict]:
    """GET wham/usage and return (status, payload) or raise ProbeError.

    Every failure branch maps to a single Russian diagnostic string.
    Request headers (including the Bearer token) are never included in
    any error message.
    """
    request = urllib.request.Request(
        USAGE_URL, method="GET", headers=build_headers(access_token, account_id)
    )

    content_type = ""
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status = int(getattr(response, "status", 200))
            content_type = response.headers.get("Content-Type", "") or ""
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        body = b""
        try:
            body = exc.read()
        except Exception:
            pass
        error_content_type = ""
        if exc.headers is not None:
            error_content_type = exc.headers.get("Content-Type", "") or ""

        if exc.code == 401:
            raise ProbeError(
                "Токен Codex истёк или недействителен (HTTP 401). Запустите "
                "любую команду codex — CLI обновит auth.json — и повторите."
            ) from exc
        if exc.code == 403:
            if "html" in error_content_type.lower():
                snippet = body.decode("utf-8", errors="replace")[:200]
                raise ProbeError(
                    "Cloudflare-заслон (HTTP 403, HTML). Повторите позже.\n"
                    f"{snippet}"
                ) from exc
            raise ProbeError(
                "Доступ запрещён (HTTP 403). Проверьте ChatGPT-Account-Id и "
                "доступность эндпоинта wham/usage для этого аккаунта."
            ) from exc
        if exc.code == 429:
            raise ProbeError(
                "Слишком много запросов (HTTP 429). Повторите позже.", retryable=True
            ) from exc
        raise ProbeError(f"wham/usage вернул HTTP {exc.code}.") from exc
    except urllib.error.URLError as exc:
        raise ProbeError(
            f"Нет соединения с chatgpt.com: {exc.reason}", retryable=True
        ) from exc
    except TimeoutError as exc:
        raise ProbeError(
            f"chatgpt.com не ответил за {timeout} с.", retryable=True
        ) from exc

    if "json" not in content_type.lower():
        raise ProbeError(f"Ответ не является JSON (Content-Type: {content_type}).")

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ProbeError("Ответ не является JSON.") from exc
    if not isinstance(payload, dict):
        raise ProbeError("wham/usage вернул данные неожиданного формата.")

    return status, payload


def write_fixture(payload: dict, path: Path) -> None:
    """Redact payload, verify the redaction, then write the fixture file.

    If the post-check fails (redacted text still contains 'eyJ' or '@'),
    raises ProbeError and does NOT write the file.
    """
    redacted = redact(payload)
    text = json.dumps(redacted, ensure_ascii=False, indent=2, sort_keys=True)
    if not redaction_clean(text):
        raise ProbeError(
            "Редакция фикстуры не прошла пост-проверку (eyJ/@) — файл не записан."
        )
    path.write_text(text, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Проба эндпоинта wham/usage Codex")
    parser.add_argument("--fixture", default="wham_usage_fixture.json")
    parser.add_argument("--no-fixture", action="store_true")
    parser.add_argument("--timeout", type=float, default=REQUEST_TIMEOUT_SECONDS)
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args(argv)

    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    try:
        access_token, account_id = load_tokens(auth_json_path())

        expires_at = jwt_exp(access_token)
        if expires_at is not None and expires_at < datetime.now():
            print(
                f"JWT истёк {expires_at:%Y-%m-%d %H:%M} — запрос всё равно "
                "будет выполнен"
            )

        status, payload = fetch_usage(access_token, account_id, args.timeout)
        print(f"HTTP status: {status}")

        redacted_payload = redact(payload)
        text = json.dumps(redacted_payload, ensure_ascii=False, indent=2)
        if not redaction_clean(text):
            raise ProbeError(
                "Редакция вывода не прошла пост-проверку (eyJ/@) — вывод скрыт."
            )
        print(text)

        fields = extract_fields(payload)
        print("Extracted fields (Balance):")
        for label in (
            "five_hour_percent",
            "weekly_percent",
            "credits",
            "five_hour_reset_text",
            "weekly_reset_text",
        ):
            value = fields.get(label)
            print(f"  {label}: {value if value is not None else 'отсутствует в ответе'}")
        for window in fields.get("windows", []):
            seconds = window.get("limit_window_seconds")
            used = window.get("used_percent")
            reset_text = _reset_text(window) or "?"
            print(f"  window {seconds}s: used {used}%, reset {reset_text}")

        if not args.no_fixture:
            fixture_path = Path(args.fixture)
            write_fixture(payload, fixture_path)
            print(f"Фикстура записана: {fixture_path}")

        return 0
    except ProbeError as exc:
        print(str(exc))
        if args.debug:
            traceback.print_exc()
        return 1
    except Exception as exc:
        message = f"Непредвиденная ошибка: {exc}"
        if not redaction_clean(message):
            message = (
                "Непредвиденная ошибка (сообщение скрыто по соображениям "
                "безопасности)."
            )
        print(message)
        if args.debug:
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
