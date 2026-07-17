"""Standalone stdlib probe for the Codex ChatGPT backend `wham/usage` endpoint.

Reads the OAuth access token from $CODEX_HOME/auth.json (the same session
file Codex CLI itself maintains), sends a single
`GET https://chatgpt.com/backend-api/wham/usage` request with a Bearer
token, classifies rate-limit windows by `limit_window_seconds` (never by
primary/secondary position — see 01-RESEARCH.md), extracts fields for the
`Balance` model used by codex_balance_widget_chrome.py, prints a redacted
pretty-printed JSON payload plus the extracted fields, and writes a
redacted fixture file.

The access token is never printed, logged, or included in any error
message, including under --debug.

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


class ProbeError(RuntimeError):
    """Human-readable (Russian) diagnostic message — the only output on failure."""


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
    rate_limit = payload.get("rate_limit") or {}
    for slot in ("primary_window", "secondary_window"):
        window = rate_limit.get(slot)
        if isinstance(window, dict):
            out.append(window)
    for extra in payload.get("additional_rate_limits") or []:
        inner = (extra or {}).get("rate_limit") or {}
        for slot in ("primary_window", "secondary_window"):
            window = inner.get(slot)
            if isinstance(window, dict):
                out.append({**window, "limit_name": (extra or {}).get("limit_name")})
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

    Keys matched: REDACT_KEYS plus any key containing the substring
    "token" (case-insensitive). Returns a new structure — never mutates
    the input.
    """
    if isinstance(obj, dict):
        result: dict[Any, Any] = {}
        for key, value in obj.items():
            if isinstance(key, str) and (key in REDACT_KEYS or "token" in key.lower()):
                result[key] = "<redacted>"
            else:
                result[key] = redact(value)
        return result
    if isinstance(obj, list):
        return [redact(item) for item in obj]
    return obj


def redaction_clean(text: str) -> bool:
    """Post-check: redacted text must contain neither a JWT prefix nor '@'."""
    return "eyJ" not in text and "@" not in text


# NOTE: HTTP layer, fixture writer and CLI entry point are added in Task 2
# (build_headers / fetch_usage / write_fixture / main), following the same
# TDD RED -> GREEN sequence.
