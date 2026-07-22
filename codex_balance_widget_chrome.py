"""
Codex Balance Widget - Chrome edition

Windows mini widget for Codex Usage limits.

How it works:
- Uses a separate local Chrome profile in ./codex_chrome_profile.
- Refreshes in hidden Chrome when an authenticated profile is already present.
- Opens visible Chrome only when manual login is needed.
- Never asks for credentials inside the widget.
"""

from __future__ import annotations

import asyncio
import atexit
import json
import msvcrt
import os
import re
import shutil
import sys
import threading
import tkinter as tk
import traceback
import webbrowser
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from tkinter import messagebox

from playwright.async_api import (
    Error as PlaywrightError,
    TimeoutError as PlaywrightTimeoutError,
    async_playwright,
)

try:
    import pystray
    from PIL import Image, ImageDraw, ImageFont
    TRAY_IMPORT_ERROR: str | None = None
except Exception as exc:  # Tray is optional: widget must still work without extra packages.
    pystray = None
    Image = None
    ImageDraw = None
    ImageFont = None
    TRAY_IMPORT_ERROR = f"{type(exc).__name__}: {exc}"

import json_usage_provider

_SIBLING_COMMON = Path(__file__).resolve().parent.parent / "usage_widget_common"
if str(_SIBLING_COMMON) not in sys.path:
    sys.path.insert(0, str(_SIBLING_COMMON))

from usage_widget_common.fetch_decision import decide_fetch_source

APP_VERSION = "v13-zero-seconds-weekly-block"
APP_DIR = Path(__file__).resolve().parent
CODEX_USAGE_URL = "https://chatgpt.com/codex/cloud/settings/analytics#usage"
PROFILE_DIR = APP_DIR / "codex_chrome_profile"
LOG_PATH = APP_DIR / "widget_launch.log"
APP_LOCK_PATH = APP_DIR / "codex_balance_widget.lock"
SETTINGS_PATH = APP_DIR / "codex_balance_widget_settings.json"
HISTORY_PATH = APP_DIR / "codex_balance_history.json"
SETTINGS_ICON_PATH = APP_DIR / "settings_icon.png"
CHROME_CACHE_LIMIT_BYTES = 10 * 1024 * 1024
CHROME_MEDIA_CACHE_LIMIT_BYTES = 1024 * 1024
PROFILE_CACHE_DIRS = [
    ("BrowserMetrics",),
    ("GrShaderCache",),
    ("ShaderCache",),
    ("GraphiteDawnCache",),
    ("GPUPersistentCache",),
    ("Default", "Cache"),
    ("Default", "Code Cache"),
    ("Default", "GPUCache"),
    ("Default", "DawnWebGPUCache"),
    ("Default", "DawnGraphiteCache"),
    ("Default", "ShaderCache"),
    ("Default", "Shared Dictionary"),
    ("Default", "Service Worker", "CacheStorage"),
    ("component_crx_cache",),
    ("extensions_crx_cache",),
]
BLANK_WINDOW_ICON_PNG = (
    "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAAJUlEQVR4nGP8//8/IwMFgIkSzaMGQAATA4WAadQAhtEwYKA8DABnpgMeG0xQggAAAABJRU5ErkJggg=="
)

REFRESH_SECONDS = 300
COUNTDOWN_REFRESH_MS = 1_000
TRAY_COUNTDOWN_REFRESH_MS = 30_000
BACKGROUND_WAIT_SECONDS = 45
LOGIN_WAIT_SECONDS = 300
POLL_SECONDS = 2
WINDOW_TITLE = "Codex balance"

DEFAULT_GEOMETRY = "360x360+80+80"
MIN_WIDTH = 320
MIN_HEIGHT = 310

BG = "#F5F6F8"
CARD_BG = "#FFFFFF"
TEXT = "#1F2937"
MUTED = "#6B7280"
BORDER = "#D9DEE7"
TRACK = "#E8ECF2"
GREEN = "#12B76A"
ORANGE = "#F79009"
RED = "#D92D20"
BLUE = "#2E90FA"
GRID = "#EEF2F7"
MAX_TRAY_TOOLTIP_LENGTH = 120

DEFAULT_LANGUAGE = "en"
LANGUAGES = {"en", "ru"}


def tr(language: str, en: str, ru: str) -> str:
    return ru if language == "ru" else en


MONTHS_RU = {
    "января": 1,
    "янв": 1,
    "янв.": 1,
    "февраля": 2,
    "фев": 2,
    "фев.": 2,
    "марта": 3,
    "мар": 3,
    "мар.": 3,
    "апреля": 4,
    "апр": 4,
    "апр.": 4,
    "мая": 5,
    "май": 5,
    "июня": 6,
    "июн": 6,
    "июн.": 6,
    "июля": 7,
    "июл": 7,
    "июл.": 7,
    "августа": 8,
    "авг": 8,
    "авг.": 8,
    "сентября": 9,
    "сен": 9,
    "сен.": 9,
    "сент": 9,
    "сент.": 9,
    "октября": 10,
    "окт": 10,
    "окт.": 10,
    "ноября": 11,
    "ноя": 11,
    "ноя.": 11,
    "декабря": 12,
    "дек": 12,
    "дек.": 12,
}

MONTHS_EN = {
    "january": 1,
    "jan": 1,
    "jan.": 1,
    "february": 2,
    "feb": 2,
    "feb.": 2,
    "march": 3,
    "mar": 3,
    "mar.": 3,
    "april": 4,
    "apr": 4,
    "apr.": 4,
    "may": 5,
    "june": 6,
    "jun": 6,
    "jun.": 6,
    "july": 7,
    "jul": 7,
    "jul.": 7,
    "august": 8,
    "aug": 8,
    "aug.": 8,
    "september": 9,
    "sep": 9,
    "sep.": 9,
    "sept": 9,
    "sept.": 9,
    "october": 10,
    "oct": 10,
    "oct.": 10,
    "november": 11,
    "nov": 11,
    "nov.": 11,
    "december": 12,
    "dec": 12,
    "dec.": 12,
}


@dataclass
class Balance:
    five_hour_percent: str | None = None
    weekly_percent: str | None = None
    credits: str | None = None
    five_hour_reset_text: str | None = None
    weekly_reset_text: str | None = None

    @property
    def has_usage_data(self) -> bool:
        return any([self.five_hour_percent, self.weekly_percent, self.credits])


@dataclass
class FetchResult:
    status: str
    text: str | None = None
    error: str | None = None


def write_log(message: str) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with LOG_PATH.open("a", encoding="utf-8") as log_file:
            log_file.write(f"[{timestamp}] {message}\n")
    except OSError:
        pass


def acquire_app_lock():
    lock_file = APP_LOCK_PATH.open("w", encoding="utf-8")
    try:
        msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
    except OSError:
        lock_file.close()
        return None

    lock_file.write(str(os.getpid()))
    lock_file.flush()
    return lock_file


def find_chrome_executable() -> str | None:
    env_path = os.environ.get("CHROME_PATH")
    if env_path and Path(env_path).exists():
        return env_path

    candidates = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        str(Path.home() / r"AppData\Local\Google\Chrome\Application\chrome.exe"),
    ]

    return next((path for path in candidates if Path(path).exists()), None)


def has_saved_chrome_session() -> bool:
    """A lightweight signal that the dedicated profile may still be authenticated."""
    default_dir = PROFILE_DIR / "Default"
    return any(
        path.exists()
        for path in [
            default_dir / "Cookies",
            default_dir / "Network" / "Cookies",
        ]
    )


def prune_chrome_profile_cache() -> None:
    """Remove Chrome cache folders without touching cookies or login storage."""
    if not PROFILE_DIR.exists():
        return

    profile_root = PROFILE_DIR.resolve()
    removed = 0
    for parts in PROFILE_CACHE_DIRS:
        path = PROFILE_DIR.joinpath(*parts)
        try:
            resolved = path.resolve()
        except OSError:
            continue

        if not resolved.is_relative_to(profile_root) or not path.exists():
            continue

        try:
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
            removed += 1
        except OSError as exc:
            write_log(f"Could not prune Chrome cache {path}: {type(exc).__name__}: {exc}")

    if removed:
        write_log(f"Pruned {removed} Chrome profile cache folder(s)")


def safe_int(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        parsed = int(str(value).strip())
    except ValueError:
        return None
    return max(0, min(100, parsed))


USAGE_COLOR_POLICY: tuple[tuple[int, str], ...] = (
    (20, RED),
    (50, ORANGE),
    (100, GREEN),
)


def usage_color(percent: int | float | None) -> str:
    """Single color scale for tray, percent labels, progress bars, and burndown."""
    if percent is None:
        return MUTED
    for upper_bound, color in USAGE_COLOR_POLICY:
        if percent <= upper_bound:
            return color
    return GREEN


def is_weekly_limit_exhausted(balance: Balance) -> bool:
    """Codex is unavailable when the weekly limit is exhausted, even if 5h still shows percent."""
    return safe_int(balance.weekly_percent) == 0


def effective_codex_percent(balance: Balance) -> int | None:
    """Availability indicator: weekly 0 blocks Codex regardless of the 5-hour value."""
    if is_weekly_limit_exhausted(balance):
        return 0
    return safe_int(balance.five_hour_percent)


def normalize_reset_text(text: str | None) -> str | None:
    if not text:
        return None
    compact = re.sub(r"\s+", " ", text).strip()
    return compact.rstrip(".,; ")


def parse_reset_datetime(reset_text: str | None, *, now: datetime | None = None) -> datetime | None:
    """Parse reset text from the Usage page into local datetime when possible."""
    text = normalize_reset_text(reset_text)
    if not text:
        return None

    now = now or datetime.now()
    lower = text.lower()
    lower = re.sub(r"^(сброс|reset)\s+", "", lower).strip()
    lower = lower.replace(" at ", " ")
    lower = re.sub(r"\s+г\.", " г.", lower)

    # Russian absolute date: 7 июн. 2026 г. 18:33 / 7 июня 2026 г. 18:33
    ru_match = re.search(
        r"(?P<day>\d{1,2})\s+(?P<month>[а-яё]+\.?)\s+(?P<year>\d{4})\s*(?:г\.)?\s+(?P<hour>\d{1,2}):(?P<minute>\d{2})",
        lower,
        flags=re.IGNORECASE,
    )
    if ru_match:
        month_name = ru_match.group("month").lower()
        month = MONTHS_RU.get(month_name)
        if month:
            try:
                return datetime(
                    int(ru_match.group("year")),
                    month,
                    int(ru_match.group("day")),
                    int(ru_match.group("hour")),
                    int(ru_match.group("minute")),
                )
            except ValueError:
                return None

    # English absolute date: Jun 7, 2026 18:33 / June 7 2026 8:33 PM
    en_match = re.search(
        r"(?P<month>[a-z]+\.?)\s+(?P<day>\d{1,2}),?\s+(?P<year>\d{4})\s+(?P<hour>\d{1,2}):(?P<minute>\d{2})\s*(?P<ampm>am|pm)?",
        lower,
        flags=re.IGNORECASE,
    )
    if en_match:
        month = MONTHS_EN.get(en_match.group("month").lower())
        if month:
            hour = int(en_match.group("hour"))
            ampm = en_match.group("ampm")
            if ampm == "pm" and hour < 12:
                hour += 12
            if ampm == "am" and hour == 12:
                hour = 0
            try:
                return datetime(
                    int(en_match.group("year")),
                    month,
                    int(en_match.group("day")),
                    hour,
                    int(en_match.group("minute")),
                )
            except ValueError:
                return None

    # ISO date (from probe_wham_usage._reset_text): 2026-07-27 18:33
    iso_match = re.search(
        r"(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})\s+(?P<hour>\d{1,2}):(?P<minute>\d{2})",
        lower,
    )
    if iso_match:
        try:
            return datetime(
                int(iso_match.group("year")),
                int(iso_match.group("month")),
                int(iso_match.group("day")),
                int(iso_match.group("hour")),
                int(iso_match.group("minute")),
            )
        except ValueError:
            return None

    # Relative English date: today 18:33 / tomorrow at 8:33 PM
    relative_match = re.search(
        r"(?P<dayword>today|tomorrow)\s+(?P<hour>\d{1,2}):(?P<minute>\d{2})\s*(?P<ampm>am|pm)?",
        lower,
        flags=re.IGNORECASE,
    )
    if relative_match:
        base = now.date() + timedelta(days=1 if relative_match.group("dayword") == "tomorrow" else 0)
        hour = int(relative_match.group("hour"))
        ampm = relative_match.group("ampm")
        if ampm == "pm" and hour < 12:
            hour += 12
        if ampm == "am" and hour == 12:
            hour = 0
        try:
            return datetime.combine(base, datetime.min.time()).replace(
                hour=hour,
                minute=int(relative_match.group("minute")),
            )
        except ValueError:
            return None

    # Time only: 20:48. Treat it as next occurrence of this time.
    time_match = re.search(r"(?P<hour>\d{1,2}):(?P<minute>\d{2})\s*(?P<ampm>am|pm)?", lower, flags=re.IGNORECASE)
    if time_match:
        hour = int(time_match.group("hour"))
        ampm = time_match.group("ampm")
        if ampm == "pm" and hour < 12:
            hour += 12
        if ampm == "am" and hour == 12:
            hour = 0
        try:
            candidate = now.replace(hour=hour, minute=int(time_match.group("minute")), second=0, microsecond=0)
        except ValueError:
            return None
        if candidate <= now - timedelta(minutes=1):
            candidate += timedelta(days=1)
        return candidate

    return None


def format_target_time(reset_dt: datetime | None, reset_text: str | None) -> str:
    if reset_dt is None:
        cleaned = normalize_reset_text(reset_text)
        if not cleaned:
            return ""
        return cleaned.replace("Сброс ", "").replace("Reset ", "")

    now = datetime.now()
    if reset_dt.date() == now.date():
        return reset_dt.strftime("%H:%M")
    return reset_dt.strftime("%d.%m.%Y %H:%M")


def format_countdown(reset_dt: datetime | None, reset_text: str | None, language: str = DEFAULT_LANGUAGE) -> str:
    cleaned = normalize_reset_text(reset_text)
    if not cleaned:
        return tr(language, "Reset: not found", "Сброс: не найден")

    if reset_dt is None:
        return cleaned

    remaining = reset_dt - datetime.now()
    total_seconds = int(remaining.total_seconds())
    target = format_target_time(reset_dt, cleaned)

    if total_seconds <= 0:
        return tr(language, f"Reset soon - {target}", f"Сброс скоро - {target}")

    minutes = max(1, total_seconds // 60)
    days, rest_minutes = divmod(minutes, 24 * 60)
    hours, mins = divmod(rest_minutes, 60)

    if days > 0:
        if hours > 0:
            duration = tr(language, f"{days}d {hours}h", f"{days} д {hours} ч")
        else:
            duration = tr(language, f"{days}d", f"{days} д")
    elif hours > 0:
        duration = tr(language, f"{hours}h {mins}m" if mins else f"{hours}h", f"{hours} ч {mins} мин" if mins else f"{hours} ч")
    else:
        duration = tr(language, f"{mins}m", f"{mins} мин")

    return tr(language, f"Reset in {duration} - {target}", f"Сброс через {duration} - {target}")


def format_compact_countdown(reset_dt: datetime | None, language: str = DEFAULT_LANGUAGE) -> str | None:
    """Compact large countdown for the main value field when a blocking limit is exhausted."""
    if reset_dt is None:
        return None

    remaining = reset_dt - datetime.now()
    total_seconds = int(remaining.total_seconds())
    if total_seconds <= 0:
        return "0:00:00"

    days, rest_seconds = divmod(total_seconds, 24 * 60 * 60)
    hours, rest_seconds = divmod(rest_seconds, 60 * 60)
    minutes, seconds = divmod(rest_seconds, 60)

    if days > 0:
        day_suffix = tr(language, "d", "д")
        return f"{days}{day_suffix} {hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{hours}:{minutes:02d}:{seconds:02d}"


def build_balance_from_json_fields(fields: dict) -> Balance:
    """Map probe_wham_usage.extract_fields() output onto Balance, no text parsing."""
    return Balance(
        five_hour_percent=fields.get("five_hour_percent"),
        weekly_percent=fields.get("weekly_percent"),
        credits=fields.get("credits"),
        five_hour_reset_text=normalize_reset_text(fields.get("five_hour_reset_text")),
        weekly_reset_text=normalize_reset_text(fields.get("weekly_reset_text")),
    )


@dataclass
class FetchOutcome:
    source: str
    balance: Balance | None
    status_message: str
    log_line: str


def plan_fetch_outcome(
    *,
    json_status: str,
    json_fields: dict | None,
    json_error: str | None,
    chrome_attempted: bool,
    chrome_status: str | None,
    chrome_error: str | None,
    chrome_text: str | None,
    has_existing_data: bool,
    language: str,
) -> FetchOutcome:
    """Decide what to show/log for a fetch attempt (JSON primary, Chrome fallback).

    Pure decision function mirroring fetch_once's current branching so the
    async orchestrator (Plan 02-03) can become a thin wrapper around this.
    """
    if json_status == "ok":
        balance = build_balance_from_json_fields(json_fields or {})
        if balance.has_usage_data:
            if is_weekly_limit_exhausted(balance):
                message = tr(language, "Codex unavailable: weekly limit exhausted", "Codex недоступен: недельный лимит исчерпан")
            else:
                message = tr(language, "Data is up to date", "Данные актуальны")
            return FetchOutcome("json", balance, message, "Balance updated (source: json)")
        # Valid JSON but no recognizable usage fields -- treat like a JSON error so the
        # Chrome-fallback / "keep last good data" logic below still applies.
        json_status = "error"
        json_error = "json response had no recognizable usage fields"

    if not chrome_attempted:
        message = tr(language, "Google Chrome not found. Set CHROME_PATH.", "Google Chrome не найден. Укажите CHROME_PATH.")
        log_line = f"JSON fetch failed ({json_error}); Chrome unavailable"
        return FetchOutcome("none", None, message, log_line)

    suffix = f" · {tr(language, 'Chrome fallback', 'Chrome-фолбэк')}"
    fallback_log = f"JSON fetch failed ({json_error}); Chrome fallback status={chrome_status} error={chrome_error or ''}"

    # Delegate the 3-way primary/fallback/retain-existing choice to the
    # shared usage_widget_common.fetch_decision.decide_fetch_source (Phase 3
    # extraction). primary_ok is always False here: this branch is only
    # reached once json_status has already been established as failed above.
    # Chrome's own source-specific statuses (browser_error/login_required)
    # stay local -- they are sub-branches of the "none" decision, not part
    # of the shared 3-way skeleton.
    chrome_balance = BalanceParser.parse(chrome_text) if (chrome_status == "ok" and chrome_text) else None
    fallback_ok = chrome_balance is not None and chrome_balance.has_usage_data
    decision = decide_fetch_source(primary_ok=False, fallback_ok=fallback_ok, has_existing_data=has_existing_data)

    if decision.source == "fallback":
        balance = chrome_balance
        if is_weekly_limit_exhausted(balance):
            message = tr(language, "Codex unavailable: weekly limit exhausted", "Codex недоступен: недельный лимит исчерпан") + suffix
        else:
            message = tr(language, "Data is up to date", "Данные актуальны") + suffix
        return FetchOutcome("chrome", balance, message, "Balance updated (source: chrome)")

    if decision.source == "retain_existing":
        if chrome_balance is not None:
            message = tr(language, "Showing last saved data · new data not recognized", "Показаны последние данные · новые не распознаны") + suffix
        else:
            message = tr(language, "Showing last saved data · refresh failed", "Показаны последние данные · обновить не удалось") + suffix
        return FetchOutcome("none", None, message, fallback_log)

    # decision.source == "none" (has_existing_data is False)
    if chrome_balance is not None:
        message = tr(language, "Data not recognized", "Данные не распознаны") + suffix
    elif chrome_status == "browser_error":
        message = tr(language, "Chrome failed to start. See widget_launch.log", "Chrome не запустился. Подробности в widget_launch.log")
    elif chrome_status == "login_required":
        message = tr(language, "Sign in to ChatGPT. Click Refresh to open Chrome.", "Нужен вход в ChatGPT. Нажмите Обновить, чтобы открыть Chrome.")
    else:
        message = tr(language, "Usage data timed out. Click Refresh.", "Не дождался данных Usage. Нажмите Обновить.") + suffix
    return FetchOutcome("none", None, message, fallback_log)


class BalanceParser:
    @staticmethod
    def parse(text: str) -> Balance:
        normalized = re.sub(r"\s+", " ", text)

        five_hour = BalanceParser._first_match(
            normalized,
            [
                r"Лимит использования 5 часов\s+(\d{1,3})\s*%\s*остал",
                r"5\s*час(?:ов|а)?\s+(\d{1,3})\s*%\s*остал",
                r"5-hour usage limit\s+(\d{1,3})\s*%\s*(?:remaining|left)",
                r"5 hour usage limit\s+(\d{1,3})\s*%\s*(?:remaining|left)",
            ],
        )

        weekly = BalanceParser._first_match(
            normalized,
            [
                r"Еженедельный лимит использования\s+(\d{1,3})\s*%\s*остал",
                r"Недельный лимит использования\s+(\d{1,3})\s*%\s*остал",
                r"недельн\w* лимит\w* использования\s+(\d{1,3})\s*%\s*остал",
                r"Weekly usage limit\s+(\d{1,3})\s*%\s*(?:remaining|left)",
            ],
        )

        credits = BalanceParser._first_match(
            normalized,
            [
                r"Осталось кредитов\s+([0-9]+(?:[.,][0-9]+)?)",
                r"кредитов\s+([0-9]+(?:[.,][0-9]+)?)",
                r"Credits remaining\s+([0-9]+(?:[.,][0-9]+)?)",
                r"Remaining credits\s+([0-9]+(?:[.,][0-9]+)?)",
            ],
        )

        reset_matches = BalanceParser._reset_matches(normalized)
        warning_reset = BalanceParser._limit_warning_reset(normalized)
        five_hour_reset = BalanceParser._reset_after(
            normalized,
            [r"Лимит использования 5 часов", r"5-hour usage limit", r"5 hour usage limit"],
            stop_labels=[r"Еженедельный лимит использования", r"Недельный лимит использования", r"Weekly usage limit"],
        )
        weekly_reset = BalanceParser._reset_after(
            normalized,
            [r"Еженедельный лимит использования", r"Недельный лимит использования", r"Weekly usage limit"],
            stop_labels=[r"Осталось кредитов", r"Credits remaining", r"Remaining credits"],
        )

        if not five_hour_reset and warning_reset:
            five_hour_reset = warning_reset
        if not five_hour_reset and reset_matches and (not weekly_reset or reset_matches[0] != weekly_reset):
            five_hour_reset = reset_matches[0]
        if not weekly_reset and len(reset_matches) > 1:
            weekly_reset = reset_matches[1]

        return Balance(
            five_hour_percent=five_hour,
            weekly_percent=weekly,
            credits=credits,
            five_hour_reset_text=normalize_reset_text(five_hour_reset),
            weekly_reset_text=normalize_reset_text(weekly_reset),
        )

    @staticmethod
    def _first_match(text: str, patterns: list[str]) -> str | None:
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                return match.group(1)
        return None

    @staticmethod
    def _reset_matches(text: str) -> list[str]:
        month_ru = r"[а-яё]+\.?"
        patterns = [
            rf"(Сброс\s+\d{{1,2}}\s+{month_ru}\s+\d{{4}}\s+г\.\s+\d{{1,2}}:\d{{2}})",
            rf"(Сброс\s+\d{{1,2}}\s+{month_ru}\s+\d{{4}}\s+\d{{1,2}}:\d{{2}})",
            r"(Сброс\s+\d{1,2}:\d{2})",
            r"(Reset\s+(?:on\s+)?[A-Za-z]+\.?\s+\d{1,2},?\s+\d{4}(?:\s+at)?\s+\d{1,2}:\d{2}(?:\s*[AP]M)?)",
            r"(Reset\s+(?:today|tomorrow)\s+(?:at\s+)?\d{1,2}:\d{2}(?:\s*[AP]M)?)",
            r"(Reset\s+\d{1,2}:\d{2}(?:\s*[AP]M)?)",
            r"(Reset\s+[^.]{5,80})",
        ]
        for pattern in patterns:
            matches = [normalize_reset_text(item) for item in re.findall(pattern, text, flags=re.IGNORECASE)]
            matches = [item for item in matches if item]
            if matches:
                return matches
        return []

    @staticmethod
    def _limit_warning_reset(text: str) -> str | None:
        patterns = [
            r"лимит\s+будет\s+сброшен\s+(\d{1,2}\s+[а-яё]+\.?\s+\d{4}\s+г\.\s+\d{1,2}:\d{2})",
            r"limit\s+will\s+reset\s+(?:on\s+)?([A-Za-z]+\.?\s+\d{1,2},?\s+\d{4}(?:\s+at)?\s+\d{1,2}:\d{2}(?:\s*[AP]M)?)",
            r"limit\s+will\s+reset\s+((?:today|tomorrow)\s+(?:at\s+)?\d{1,2}:\d{2}(?:\s*[AP]M)?)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                return f"Сброс {match.group(1).strip()}"
        return None

    @staticmethod
    def _reset_after(text: str, labels: list[str], stop_labels: list[str] | None = None) -> str | None:
        reset_ru = (
            r"Сброс\s+(?:\d{1,2}:\d{2}|"
            r"\d{1,2}\s+[а-яё]+\.?\s+\d{4}\s+(?:г\.)?\s+\d{1,2}:\d{2})"
        )
        reset_en = (
            r"Reset\s+(?:(?:today|tomorrow)\s+(?:at\s+)?\d{1,2}:\d{2}(?:\s*[AP]M)?|"
            r"\d{1,2}:\d{2}(?:\s*[AP]M)?|"
            r"[A-Za-z]+\.?\s+\d{1,2},?\s+\d{4}(?:\s+at)?\s+\d{1,2}:\d{2}(?:\s*[AP]M)?|"
            r"[^.]{5,80})"
        )
        for label in labels:
            label_match = re.search(label, text, flags=re.IGNORECASE)
            if not label_match:
                continue

            section_start = label_match.end()
            section_end = min(len(text), section_start + 320)
            for stop_label in stop_labels or []:
                stop_match = re.search(stop_label, text[section_start:section_end], flags=re.IGNORECASE)
                if stop_match:
                    section_end = min(section_end, section_start + stop_match.start())

            section = text[section_start:section_end]
            reset_match = re.search(rf"({reset_ru}|{reset_en})", section, flags=re.IGNORECASE)
            if reset_match:
                return normalize_reset_text(reset_match.group(1))
        return None


def parse_balance(text: str) -> Balance:
    """Compatibility wrapper for quick ad-hoc tests."""
    return BalanceParser.parse(text)


def looks_like_login_page(text: str) -> bool:
    normalized = text.lower()
    login_markers = [
        "log in",
        "login",
        "sign up",
        "sign in",
        "войти",
        "зарегистрироваться",
    ]
    usage_markers = [
        "5-hour usage limit",
        "weekly usage limit",
        "credits remaining",
        "remaining credits",
        "лимит использования",
        "кредит",
    ]
    return any(marker in normalized for marker in login_markers) and not any(
        marker in normalized for marker in usage_markers
    )


class SettingsStore:
    DEFAULTS = {
        "geometry": DEFAULT_GEOMETRY,
        "always_on_top": True,
        "show_burndown": True,
        "refresh_seconds": REFRESH_SECONDS,
        "language": DEFAULT_LANGUAGE,
        "version": APP_VERSION,
    }

    @staticmethod
    def load() -> dict:
        data: dict = {}
        try:
            raw = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                data = raw
        except (OSError, json.JSONDecodeError):
            data = {}

        settings = dict(SettingsStore.DEFAULTS)
        settings.update(data)

        geometry = settings.get("geometry")
        if not isinstance(geometry, str) or not re.match(r"^\d+x\d+[+-]\d+[+-]\d+$", geometry):
            settings["geometry"] = DEFAULT_GEOMETRY

        settings["always_on_top"] = bool(settings.get("always_on_top", True))
        settings["show_burndown"] = bool(settings.get("show_burndown", True))
        settings["language"] = settings.get("language") if settings.get("language") in LANGUAGES else DEFAULT_LANGUAGE

        try:
            refresh_seconds = int(settings.get("refresh_seconds", REFRESH_SECONDS))
        except (TypeError, ValueError):
            refresh_seconds = REFRESH_SECONDS
        settings["refresh_seconds"] = max(60, min(3600, refresh_seconds))

        return settings

    @staticmethod
    def save(settings: dict) -> None:
        data = dict(SettingsStore.DEFAULTS)
        data.update(settings)
        data["version"] = APP_VERSION

        geometry = data.get("geometry")
        if not isinstance(geometry, str) or not re.match(r"^\d+x\d+[+-]\d+[+-]\d+$", geometry):
            data["geometry"] = DEFAULT_GEOMETRY

        data["always_on_top"] = bool(data.get("always_on_top", True))
        data["show_burndown"] = bool(data.get("show_burndown", True))
        data["language"] = data.get("language") if data.get("language") in LANGUAGES else DEFAULT_LANGUAGE
        try:
            data["refresh_seconds"] = max(60, min(3600, int(data.get("refresh_seconds", REFRESH_SECONDS))))
        except (TypeError, ValueError):
            data["refresh_seconds"] = REFRESH_SECONDS

        try:
            tmp_path = SETTINGS_PATH.with_suffix(".tmp")
            tmp_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            tmp_path.replace(SETTINGS_PATH)
        except OSError as exc:
            write_log(f"Could not save settings: {exc}")

    @staticmethod
    def save_geometry(geometry: str) -> None:
        if not re.match(r"^\d+x\d+[+-]\d+[+-]\d+$", geometry):
            return
        settings = SettingsStore.load()
        settings["geometry"] = geometry
        SettingsStore.save(settings)


class HistoryStore:
    @staticmethod
    def load() -> list[dict]:
        try:
            data = json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return []
        except (OSError, json.JSONDecodeError) as exc:
            write_log(f"Could not read history, starting empty: {exc}")
            return []
        if not isinstance(data, list):
            return []
        return [item for item in data if isinstance(item, dict)]

    @staticmethod
    def save(items: list[dict]) -> None:
        try:
            tmp_path = HISTORY_PATH.with_suffix(".tmp")
            tmp_path.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
            tmp_path.replace(HISTORY_PATH)
        except OSError as exc:
            write_log(f"Could not save history: {exc}")

    @staticmethod
    def append_balance(balance: Balance) -> list[dict]:
        weekly_percent = safe_int(balance.weekly_percent)
        five_hour_percent = safe_int(balance.five_hour_percent)
        if weekly_percent is None and five_hour_percent is None:
            return HistoryStore.load()

        now = datetime.now()
        weekly_reset_dt = parse_reset_datetime(balance.weekly_reset_text, now=now)
        five_hour_reset_dt = parse_reset_datetime(balance.five_hour_reset_text, now=now)

        items = HistoryStore.load()
        cutoff = now - timedelta(days=21)
        kept: list[dict] = []
        for item in items:
            timestamp = parse_iso_datetime(item.get("timestamp"))
            if timestamp and timestamp >= cutoff:
                kept.append(item)

        new_item = {
            "timestamp": now.isoformat(timespec="seconds"),
            "weekly_percent": weekly_percent,
            "five_hour_percent": five_hour_percent,
            "credits": balance.credits,
            "weekly_reset_text": normalize_reset_text(balance.weekly_reset_text),
            "weekly_reset_datetime": weekly_reset_dt.isoformat(timespec="seconds") if weekly_reset_dt else None,
            "five_hour_reset_text": normalize_reset_text(balance.five_hour_reset_text),
            "five_hour_reset_datetime": five_hour_reset_dt.isoformat(timespec="seconds") if five_hour_reset_dt else None,
        }

        if kept:
            last = kept[-1]
            last_timestamp = parse_iso_datetime(last.get("timestamp"))
            last_weekly = last.get("weekly_percent")
            last_five_hour = last.get("five_hour_percent")
            last_weekly_reset = last.get("weekly_reset_datetime")
            last_old_enough = not last_timestamp or (now - last_timestamp) >= timedelta(minutes=30)
            meaningful_change = (
                last_weekly != weekly_percent
                or last_five_hour != five_hour_percent
                or last_weekly_reset != new_item["weekly_reset_datetime"]
            )
            if not last_old_enough and not meaningful_change:
                return kept

        kept.append(new_item)
        HistoryStore.save(kept)
        return kept

    @staticmethod
    def latest_balance() -> tuple[Balance, datetime | None] | None:
        for item in reversed(HistoryStore.load()):
            five_hour_percent = safe_int(item.get("five_hour_percent"))
            weekly_percent = safe_int(item.get("weekly_percent"))
            if five_hour_percent is None and weekly_percent is None and not item.get("credits"):
                continue
            timestamp = parse_iso_datetime(item.get("timestamp"))
            balance = Balance(
                five_hour_percent=str(five_hour_percent) if five_hour_percent is not None else None,
                weekly_percent=str(weekly_percent) if weekly_percent is not None else None,
                credits=str(item.get("credits")) if item.get("credits") is not None else None,
                five_hour_reset_text=item.get("five_hour_reset_text") if isinstance(item.get("five_hour_reset_text"), str) else None,
                weekly_reset_text=item.get("weekly_reset_text") if isinstance(item.get("weekly_reset_text"), str) else None,
            )
            return balance, timestamp
        return None


def parse_iso_datetime(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


class CodexUsageBrowser:
    def __init__(self, chrome_path: str, set_status):
        self.chrome_path = chrome_path
        self.set_status = set_status

    async def fetch(self) -> FetchResult:
        if has_saved_chrome_session():
            self.set_status("Обновляю в фоновом Chrome...")
            background_result = await self._fetch_once(visible=False, wait_for_login=False)
            if background_result.status == "ok":
                return background_result
            write_log(
                f"Background fetch did not complete: {background_result.status} "
                f"{background_result.error or ''}"
            )

        self.set_status("Открою Chrome для входа или проверки сессии...")
        return await self._fetch_once(visible=True, wait_for_login=True)

    async def _fetch_once(self, *, visible: bool, wait_for_login: bool) -> FetchResult:
        try:
            prune_chrome_profile_cache()
            async with async_playwright() as playwright:
                launch_args = [
                    "--disable-blink-features=AutomationControlled",
                    f"--disk-cache-size={CHROME_CACHE_LIMIT_BYTES}",
                    f"--media-cache-size={CHROME_MEDIA_CACHE_LIMIT_BYTES}",
                ]
                if not visible:
                    launch_args.extend([
                        "--window-position=-32000,-32000",
                        "--window-size=1280,900",
                    ])

                context = await playwright.chromium.launch_persistent_context(
                    user_data_dir=str(PROFILE_DIR),
                    executable_path=self.chrome_path,
                    headless=False,
                    viewport={"width": 1280, "height": 900},
                    args=launch_args,
                )
                try:
                    page = context.pages[0] if context.pages else await context.new_page()
                    await page.goto(CODEX_USAGE_URL, wait_until="domcontentloaded", timeout=60_000)
                    text = await self._wait_for_usage_text(
                        page,
                        visible=visible,
                        wait_for_login=wait_for_login,
                    )
                    if text:
                        return FetchResult("ok", text=text)
                    return FetchResult("login_required" if not visible else "not_ready")
                finally:
                    await context.close()
                    prune_chrome_profile_cache()
        except PlaywrightError as exc:
            mode = "background" if not visible else "visible"
            write_log(f"{mode.capitalize()} Chrome failed:\n{exc}")
            return FetchResult("browser_error", error=f"{type(exc).__name__}: {exc}")
        except Exception as exc:
            write_log("Unexpected browser error:\n" + "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)))
            return FetchResult("browser_error", error=f"{type(exc).__name__}: {exc}")

    async def _wait_for_usage_text(self, page, *, visible: bool, wait_for_login: bool) -> str | None:
        timeout_seconds = LOGIN_WAIT_SECONDS if wait_for_login else BACKGROUND_WAIT_SECONDS
        deadline = asyncio.get_running_loop().time() + timeout_seconds

        while True:
            try:
                await page.wait_for_load_state("networkidle", timeout=8_000)
            except PlaywrightTimeoutError:
                pass

            try:
                body_text = await page.locator("body").inner_text(timeout=8_000)
            except PlaywrightTimeoutError:
                body_text = ""

            balance = BalanceParser.parse(body_text)
            if balance.has_usage_data:
                return body_text

            if looks_like_login_page(body_text):
                if not wait_for_login:
                    return None
                remaining = max(0, int(deadline - asyncio.get_running_loop().time()))
                self.set_status(f"Войдите в ChatGPT в открытом Chrome. Жду: {remaining} сек.")
            elif "chatgpt.com" in page.url and CODEX_USAGE_URL not in page.url:
                self.set_status("Возвращаюсь на страницу Usage...")
                await page.goto(CODEX_USAGE_URL, wait_until="domcontentloaded", timeout=60_000)
            else:
                mode = "фоновом Chrome" if not visible else "открытом Chrome"
                self.set_status(f"Жду страницу Usage в {mode}...")

            if asyncio.get_running_loop().time() >= deadline:
                return None

            await page.wait_for_timeout(POLL_SECONDS * 1000)


class ProgressBar(tk.Canvas):
    def __init__(self, master, height: int = 8, **kwargs):
        super().__init__(master, height=height, bg=CARD_BG, bd=0, highlightthickness=0, **kwargs)
        self.percent: int | None = None
        self.color = MUTED
        self.bind("<Configure>", lambda _event: self.redraw())

    def set_value(self, percent: int | None, color: str | None = None) -> None:
        self.percent = percent
        self.color = color or usage_color(percent)
        self.redraw()

    def redraw(self) -> None:
        self.delete("all")
        width = max(1, self.winfo_width())
        height = max(1, self.winfo_height())
        radius = max(2, height // 2)
        self.create_round_rect(0, 0, width, height, radius=radius, fill=TRACK, outline="")
        if self.percent is None:
            return
        filled = int(width * max(0, min(100, self.percent)) / 100)
        if filled <= 0:
            return
        self.create_round_rect(0, 0, filled, height, radius=radius, fill=self.color, outline="")

    def create_round_rect(self, x1, y1, x2, y2, radius=8, **kwargs):
        points = [
            x1 + radius,
            y1,
            x2 - radius,
            y1,
            x2,
            y1,
            x2,
            y1 + radius,
            x2,
            y2 - radius,
            x2,
            y2,
            x2 - radius,
            y2,
            x1 + radius,
            y2,
            x1,
            y2,
            x1,
            y2 - radius,
            x1,
            y1 + radius,
            x1,
            y1,
        ]
        return self.create_polygon(points, smooth=True, **kwargs)


class WeeklyBurndownCanvas(tk.Canvas):
    def __init__(self, master, height: int = 58, **kwargs):
        super().__init__(master, height=height, bg=CARD_BG, bd=0, highlightthickness=0, **kwargs)
        self.points: list[dict] = []
        self.week_start: datetime | None = None
        self.week_end: datetime | None = None
        self.bind("<Configure>", lambda _event: self.redraw())

    def set_data(
        self,
        *,
        history: list[dict],
        weekly_percent: int | None,
        weekly_reset_dt: datetime | None,
    ) -> bool:
        if weekly_percent is None or weekly_reset_dt is None:
            self.points = []
            self.week_start = None
            self.week_end = None
            self.redraw()
            return False

        self.week_end = weekly_reset_dt
        self.week_start = weekly_reset_dt - timedelta(days=7)
        filtered: list[dict] = []
        for item in history:
            timestamp = parse_iso_datetime(item.get("timestamp"))
            value = item.get("weekly_percent")
            if timestamp is None or value is None:
                continue
            try:
                value_int = int(value)
            except (TypeError, ValueError):
                continue
            if self.week_start <= timestamp <= self.week_end:
                filtered.append({"timestamp": timestamp, "value": max(0, min(100, value_int))})

        # Add current visual point even when history was just written or skipped.
        now = datetime.now()
        if self.week_start <= now <= self.week_end:
            if not filtered or filtered[-1]["timestamp"] < now - timedelta(seconds=5):
                filtered.append({"timestamp": now, "value": weekly_percent})

        filtered.sort(key=lambda item: item["timestamp"])
        self.points = filtered
        self.redraw()
        return len(filtered) >= 2

    @staticmethod
    def _interpolate_point(
        start: tuple[float, float, int],
        end: tuple[float, float, int],
        value: float,
    ) -> tuple[float, float, float]:
        start_x, start_y, start_value = start
        end_x, end_y, end_value = end
        if end_value == start_value:
            return start_x, start_y, float(start_value)
        ratio = (value - start_value) / (end_value - start_value)
        x = start_x + (end_x - start_x) * ratio
        y = start_y + (end_y - start_y) * ratio
        return x, y, value

    def _draw_colored_segment(
        self,
        start: tuple[float, float, int],
        end: tuple[float, float, int],
    ) -> None:
        start_value = start[2]
        end_value = end[2]
        thresholds = [upper_bound for upper_bound, _color in USAGE_COLOR_POLICY[:-1]]
        crossed = [
            threshold
            for threshold in thresholds
            if min(start_value, end_value) < threshold < max(start_value, end_value)
        ]
        crossed.sort(reverse=start_value > end_value)

        points: list[tuple[float, float, float]] = [
            (start[0], start[1], float(start_value)),
            *(self._interpolate_point(start, end, threshold) for threshold in crossed),
            (end[0], end[1], float(end_value)),
        ]

        for first, second in zip(points, points[1:]):
            average_value = (first[2] + second[2]) / 2
            self.create_line(
                first[0],
                first[1],
                second[0],
                second[1],
                fill=usage_color(average_value),
                width=2,
            )

    def redraw(self) -> None:
        self.delete("all")
        width = max(1, self.winfo_width())
        height = max(1, self.winfo_height())
        padding_x = 4
        padding_y = 6
        chart_w = max(1, width - padding_x * 2)
        chart_h = max(1, height - padding_y * 2)

        if not self.week_start or not self.week_end:
            return

        # Day separators.
        for day in range(8):
            x = padding_x + chart_w * day / 7
            self.create_line(x, padding_y, x, padding_y + chart_h, fill=GRID, width=1)

        # Top and bottom guides.
        self.create_line(padding_x, padding_y, padding_x + chart_w, padding_y, fill="#F3F5F9", width=1)
        self.create_line(padding_x, padding_y + chart_h, padding_x + chart_w, padding_y + chart_h, fill="#F3F5F9", width=1)

        if len(self.points) < 2:
            return

        total = max(1, (self.week_end - self.week_start).total_seconds())
        coords: list[tuple[float, float, int]] = []
        for item in self.points:
            x_ratio = (item["timestamp"] - self.week_start).total_seconds() / total
            x_ratio = max(0, min(1, x_ratio))
            value = max(0, min(100, int(item["value"])))
            x = padding_x + chart_w * x_ratio
            y = padding_y + chart_h * (1 - value / 100)
            coords.append((x, y, value))

        # Split into segments when a new cycle or reset-like jump appears.
        segments: list[list[tuple[float, float, int]]] = [[]]
        for point in coords:
            if segments[-1]:
                previous = segments[-1][-1]
                if point[2] - previous[2] > 35:
                    segments.append([])
            segments[-1].append(point)

        for segment in segments:
            if len(segment) < 2:
                continue
            for start, end in zip(segment, segment[1:]):
                self._draw_colored_segment(start, end)

        last_x, last_y, last_value = coords[-1]
        self.create_oval(
            last_x - 2.5,
            last_y - 2.5,
            last_x + 2.5,
            last_y + 2.5,
            fill=usage_color(last_value),
            outline="",
        )


def hex_to_rgb(color: str) -> tuple[int, int, int]:
    color = color.lstrip("#")
    return tuple(int(color[index:index + 2], 16) for index in (0, 2, 4))  # type: ignore[return-value]


def format_tray_reset(reset_text: str | None, language: str = DEFAULT_LANGUAGE) -> str:
    reset_dt = parse_reset_datetime(reset_text)
    cleaned = normalize_reset_text(reset_text)
    if not cleaned:
        return tr(language, "reset not found", "сброс не найден")
    if reset_dt is None:
        return cleaned.lower()

    remaining = reset_dt - datetime.now()
    total_seconds = int(remaining.total_seconds())
    if total_seconds <= 0:
        return tr(language, "reset soon", "сброс скоро")

    minutes = max(1, total_seconds // 60)
    days, rest_minutes = divmod(minutes, 24 * 60)
    hours, mins = divmod(rest_minutes, 60)
    if days > 0:
        duration = tr(language, f"{days}d {hours}h" if hours else f"{days}d", f"{days} д {hours} ч" if hours else f"{days} д")
    elif hours > 0:
        duration = tr(language, f"{hours}h {mins}m" if mins else f"{hours}h", f"{hours} ч {mins} мин" if mins else f"{hours} ч")
    else:
        duration = tr(language, f"{mins}m", f"{mins} мин")
    return tr(language, f"reset in {duration}", f"сброс через {duration}")


def build_tray_tooltip(balance: Balance, last_successful_update: datetime | None, status: str | None, language: str = DEFAULT_LANGUAGE) -> str:
    five_hour = safe_int(balance.five_hour_percent)
    weekly = safe_int(balance.weekly_percent)
    credits = balance.credits or tr(language, "not found", "не найдено")
    blocked_by_weekly = weekly == 0

    if blocked_by_weekly:
        availability_text = tr(language, "Codex: unavailable, weekly 0%", "Codex: недоступен, неделя 0%")
        five_text = tr(language, "blocked", "блок")
    else:
        availability_text = tr(language, "Codex: available", "Codex: доступен")
        five_text = f"{five_hour}%" if five_hour is not None else tr(language, "not found", "не найдено")

    weekly_text = f"{weekly}%" if weekly is not None else tr(language, "not found", "не найдено")
    updated_text = last_successful_update.strftime("%H:%M") if last_successful_update else tr(language, "no", "нет")
    status_text = status or tr(language, "no status", "нет статуса")

    tooltip = (
        "Codex balance\n"
        f"{availability_text}\n"
        f"{tr(language, '5h', '5ч')}: {five_text}, {format_tray_reset(balance.five_hour_reset_text, language)}\n"
        f"{tr(language, 'Week', 'Нед')}: {weekly_text}, {format_tray_reset(balance.weekly_reset_text, language)}\n"
        f"{tr(language, 'Cr', 'Кр')}: {credits} | {tr(language, 'Upd', 'Обн')}: {updated_text}\n"
        f"{status_text}"
    )
    if len(tooltip) > MAX_TRAY_TOOLTIP_LENGTH:
        tooltip = tooltip[:MAX_TRAY_TOOLTIP_LENGTH - 3].rstrip() + "..."
    return tooltip


def load_tray_font(size: int):
    if ImageFont is None:
        return None
    for font_name in ["seguibl.ttf", "segoeuib.ttf", "arialbd.ttf", "seguisb.ttf", "arial.ttf"]:
        try:
            return ImageFont.truetype(font_name, size)
        except Exception:
            pass
    try:
        return ImageFont.load_default()
    except Exception:
        return None


def create_tray_image(percent: int | None):
    if Image is None or ImageDraw is None:
        return None

    size = 64
    bg_color = usage_color(percent) if percent is not None else MUTED
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((2, 2, size - 2, size - 2), radius=14, fill=hex_to_rgb(bg_color) + (255,))

    if percent is None:
        label = "?"
    else:
        percent = max(0, min(100, percent))
        label = "✓" if percent == 100 else str(percent // 10)
    font_size_candidates = [52, 49, 46, 43, 40, 37]
    font = None
    bbox = None
    for font_size in font_size_candidates:
        candidate = load_tray_font(font_size)
        if candidate is None:
            continue
        candidate_bbox = draw.textbbox((0, 0), label, font=candidate)
        text_w = candidate_bbox[2] - candidate_bbox[0]
        text_h = candidate_bbox[3] - candidate_bbox[1]
        if text_w <= 60 and text_h <= 52:
            font = candidate
            bbox = candidate_bbox
            break
    if font is None:
        font = load_tray_font(18)
        bbox = draw.textbbox((0, 0), label, font=font) if font else (0, 0, 0, 0)

    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x = (size - text_w) / 2 - bbox[0]
    y = (size - text_h) / 2 - bbox[1] - 1
    draw.text(
        (x, y),
        label,
        fill=(255, 255, 255, 255),
        font=font,
        stroke_width=1,
        stroke_fill=(255, 255, 255, 255),
    )
    return image


class CodexBalanceWidget:
    def __init__(self):
        self.chrome_path = find_chrome_executable()
        self.browser = CodexUsageBrowser(self.chrome_path, self.set_status) if self.chrome_path else None
        self.json_provider = json_usage_provider.JsonUsageProvider()
        self.refresh_in_progress = False
        self.current_balance = Balance()
        self.history = HistoryStore.load()
        self.app_settings = SettingsStore.load()
        self.always_on_top = bool(self.app_settings.get("always_on_top", True))
        self.show_burndown = bool(self.app_settings.get("show_burndown", True))
        self.refresh_seconds = int(self.app_settings.get("refresh_seconds", REFRESH_SECONDS))
        self.language = str(self.app_settings.get("language", DEFAULT_LANGUAGE))
        self.last_successful_update: datetime | None = None
        self.last_fetch_status: str | None = None
        self.last_fetch_error: str | None = None
        self.last_usage_text_length: int | None = None
        self.tray_icon = None
        self.tray_thread: threading.Thread | None = None
        self.tray_enabled = False
        self.last_countdown_tray_update: datetime | None = None
        self.is_exiting = False
        self.window_visible = True
        self.last_visible_geometry = str(self.app_settings.get("geometry", DEFAULT_GEOMETRY))

        self.root = tk.Tk()
        self.root.title(" ")
        self.root.geometry(str(self.app_settings.get("geometry", DEFAULT_GEOMETRY)))
        self.root.minsize(MIN_WIDTH, MIN_HEIGHT)
        self.root.configure(bg=BG)
        self.root.attributes("-topmost", self.always_on_top)
        self._install_blank_icon()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.status_var = tk.StringVar(value=tr(self.language, "Starting...", "Запуск..."))
        self.five_hour_title_var = tk.StringVar(value=tr(self.language, "5 hours", "5 часов"))
        self.five_hour_value_var = tk.StringVar(value="...%")
        self.weekly_title_var = tk.StringVar(value=tr(self.language, "Week", "Неделя"))
        self.weekly_value_var = tk.StringVar(value="...%")
        self.credits_var = tk.StringVar(value=tr(self.language, "Credits: ...", "Кредиты: ..."))
        self.five_hour_reset_var = tk.StringVar(value=tr(self.language, "Reset: not found", "Сброс: не найден"))
        self.weekly_reset_var = tk.StringVar(value=tr(self.language, "Reset: not found", "Сброс: не найден"))
        self.updated_var = tk.StringVar(value="")

        self.settings_icon_image: tk.PhotoImage | None = None
        self._build_ui()
        self.restore_latest_history()

        self.loop = asyncio.new_event_loop()
        self.worker = threading.Thread(target=self._run_loop, daemon=True)
        self.worker.start()
        self.setup_tray_icon()
        self.root.after(300, self.schedule_refresh)
        self.root.after(COUNTDOWN_REFRESH_MS, self.update_countdowns)

    def _install_blank_icon(self) -> None:
        try:
            # Windows renders a fully transparent Tk icon handle as a black square.
            # A nearly transparent PNG keeps the title-bar slot visually empty.
            blank = tk.PhotoImage(data=BLANK_WINDOW_ICON_PNG)
            self.root.iconphoto(True, blank)
            self._blank_icon = blank
        except tk.TclError:
            pass

    def _build_ui(self) -> None:
        outer = tk.Frame(self.root, bg=BG)
        outer.pack(fill="both", expand=True, padx=12, pady=10)

        header = tk.Frame(outer, bg=BG)
        header.pack(fill="x", pady=(0, 8))
        tk.Label(header, text="Codex balance", font=("Segoe UI", 15, "bold"), bg=BG, fg=TEXT).pack(side="left")
        tk.Label(header, textvariable=self.updated_var, font=("Segoe UI", 8), bg=BG, fg=MUTED).pack(side="right", anchor="s", pady=(5, 0))

        self.five_hour_progress = None
        self.five_hour_card = self._build_limit_card(
            outer,
            title_var=self.five_hour_title_var,
            value_var=self.five_hour_value_var,
            reset_var=self.five_hour_reset_var,
            use_chart=False,
        )
        self.five_hour_progress = self.five_hour_card["progress"]

        self.weekly_card = self._build_limit_card(
            outer,
            title_var=self.weekly_title_var,
            value_var=self.weekly_value_var,
            reset_var=self.weekly_reset_var,
            use_chart=True,
        )
        self.weekly_progress = self.weekly_card["progress"]
        self.weekly_chart = self.weekly_card["chart"]

        credits_card = tk.Frame(outer, bg=CARD_BG, highlightbackground=BORDER, highlightthickness=1)
        credits_card.pack(fill="x", pady=(0, 8))
        tk.Label(credits_card, textvariable=self.credits_var, font=("Segoe UI", 10, "bold"), bg=CARD_BG, fg=TEXT).pack(anchor="w", padx=10, pady=8)

        buttons = tk.Frame(outer, bg=BG)
        buttons.pack(fill="x", pady=(2, 0))
        self._flat_button(buttons, tr(self.language, "Refresh", "Обновить"), self.manual_refresh).pack(side="left")
        self._flat_button(buttons, tr(self.language, "Open site", "Открыть сайт"), self.open_usage_site).pack(side="left", padx=(8, 0))
        self.tools_button = self._settings_button(buttons, self.show_tools_menu)
        self.tools_button.pack(side="right")

        tk.Label(outer, textvariable=self.status_var, font=("Segoe UI", 8), bg=BG, fg=MUTED).pack(anchor="w", pady=(8, 0))

    def _build_limit_card(self, master, *, title_var: tk.StringVar, value_var: tk.StringVar, reset_var: tk.StringVar, use_chart: bool) -> dict:
        card = tk.Frame(master, bg=CARD_BG, highlightbackground=BORDER, highlightthickness=1)
        card.pack(fill="x", pady=(0, 8))

        top = tk.Frame(card, bg=CARD_BG)
        top.pack(fill="x", padx=10, pady=(8, 4))
        tk.Label(top, textvariable=title_var, font=("Segoe UI", 10, "bold"), bg=CARD_BG, fg=TEXT).pack(side="left")
        value_label = tk.Label(top, textvariable=value_var, font=("Segoe UI", 12, "bold"), bg=CARD_BG, fg=TEXT)
        value_label.pack(side="right")

        progress = ProgressBar(card, height=8)
        progress.pack(fill="x", padx=10, pady=(0, 6))

        chart = None
        if use_chart:
            chart = WeeklyBurndownCanvas(card, height=58)
            # It is packed only after enough weekly history is available.

        reset_label = tk.Label(card, textvariable=reset_var, font=("Segoe UI", 8), bg=CARD_BG, fg=MUTED)
        reset_label.pack(anchor="w", padx=10, pady=(0, 8))

        return {
            "card": card,
            "value_label": value_label,
            "progress": progress,
            "chart": chart,
            "reset_label": reset_label,
        }

    def _flat_button(self, master, text: str, command):
        button = tk.Button(
            master,
            text=text,
            command=command,
            font=("Segoe UI", 9),
            bg=CARD_BG,
            fg=TEXT,
            activebackground="#F0F3F8",
            activeforeground=TEXT,
            relief="flat",
            bd=0,
            padx=10,
            pady=5,
            cursor="hand2",
            highlightthickness=1,
            highlightbackground=BORDER,
            highlightcolor=BORDER,
        )
        button.bind("<Enter>", lambda _event: button.configure(bg="#F8FAFC"))
        button.bind("<Leave>", lambda _event: button.configure(bg=CARD_BG))
        return button

    def _settings_button(self, master, command):
        options = dict(
            command=command,
            bg=CARD_BG,
            activebackground="#F0F3F8",
            relief="flat",
            bd=0,
            width=28,
            height=28,
            padx=0,
            pady=0,
            cursor="hand2",
            highlightthickness=1,
            highlightbackground=BORDER,
            highlightcolor=BORDER,
        )

        try:
            if SETTINGS_ICON_PATH.exists():
                self.settings_icon_image = tk.PhotoImage(file=str(SETTINGS_ICON_PATH))
                button = tk.Button(master, image=self.settings_icon_image, **options)
            else:
                button = tk.Button(
                    master,
                    text="⚙",
                    font=("Segoe UI Symbol", 11),
                    fg=TEXT,
                    activeforeground=TEXT,
                    **options,
                )
        except tk.TclError:
            button = tk.Button(
                master,
                text="⚙",
                font=("Segoe UI Symbol", 11),
                fg=TEXT,
                activeforeground=TEXT,
                **options,
            )

        button.bind("<Enter>", lambda _event: button.configure(bg="#F8FAFC"))
        button.bind("<Leave>", lambda _event: button.configure(bg=CARD_BG))
        return button

    def show_tools_menu(self) -> None:
        menu = tk.Menu(
            self.root,
            tearoff=0,
            bg=CARD_BG,
            fg=TEXT,
            activebackground="#F0F3F8",
            activeforeground=TEXT,
            relief="flat",
            bd=1,
        )
        menu.add_command(label=tr(self.language, "Settings...", "Настройки..."), command=self.show_settings)
        menu.add_separator()
        menu.add_command(label=tr(self.language, "Diagnostics", "Диагностика"), command=self.show_diagnostics)
        menu.add_command(label=tr(self.language, "Open log", "Открыть лог"), command=self.open_log_file)
        menu.add_separator()
        menu.add_command(label=tr(self.language, "Help", "Помощь"), command=self.show_help)

        try:
            x = self.tools_button.winfo_rootx()
            y = self.tools_button.winfo_rooty() + self.tools_button.winfo_height() + 2
            menu.tk_popup(x, y)
        finally:
            menu.grab_release()

    def setup_tray_icon(self) -> None:
        if pystray is None or Image is None or ImageDraw is None:
            self.tray_enabled = False
            write_log(f"Tray icon disabled: {TRAY_IMPORT_ERROR or 'pystray/Pillow unavailable'}")
            return

        try:
            menu = pystray.Menu(
                pystray.MenuItem(tr(self.language, "Show / hide window", "Показать / скрыть окно"), self._tray_toggle_window, default=True),
                pystray.MenuItem(tr(self.language, "Refresh", "Обновить"), self._tray_manual_refresh),
                pystray.MenuItem(tr(self.language, "Open site", "Открыть сайт"), self._tray_open_usage_site),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem(tr(self.language, "Settings...", "Настройки..."), self._tray_show_settings),
                pystray.MenuItem(tr(self.language, "Diagnostics", "Диагностика"), self._tray_show_diagnostics),
                pystray.MenuItem(tr(self.language, "Open log", "Открыть лог"), self._tray_open_log_file),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem(tr(self.language, "Exit", "Выход"), self._tray_exit_app),
            )
            icon_image = create_tray_image(effective_codex_percent(self.current_balance))
            self.tray_icon = pystray.Icon(
                "codex_balance_widget",
                icon_image,
                build_tray_tooltip(self.current_balance, self.last_successful_update, self.status_var.get(), self.language),
                menu,
            )
            self.tray_thread = threading.Thread(target=self._run_tray_icon, name="CodexBalanceTray", daemon=True)
            self.tray_thread.start()
            self.tray_enabled = True
            write_log("Tray icon started")
        except Exception as exc:
            self.tray_icon = None
            self.tray_enabled = False
            write_log("Tray icon failed:\n" + "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)))

    def _run_tray_icon(self) -> None:
        if not self.tray_icon:
            return
        try:
            self.tray_icon.run(setup=self._setup_visible_tray_icon)
        except Exception as exc:
            self.tray_enabled = False
            write_log("Tray icon thread failed:\n" + "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)))

    def _setup_visible_tray_icon(self, icon) -> None:
        try:
            icon.visible = True
            write_log(f"Tray icon visible={getattr(icon, 'visible', None)}")
        except Exception as exc:
            self.tray_enabled = False
            write_log(f"Could not make tray icon visible: {type(exc).__name__}: {exc}")

    def update_tray_icon(self) -> None:
        if not self.tray_icon or pystray is None or Image is None:
            return
        try:
            percent = effective_codex_percent(self.current_balance)
            icon_image = create_tray_image(percent)
            if icon_image is not None:
                    self.tray_icon.icon = icon_image
            self.tray_icon.title = build_tray_tooltip(
                self.current_balance,
                self.last_successful_update,
                self.status_var.get(),
                self.language,
            )
            if not getattr(self.tray_icon, "visible", False):
                self.tray_icon.visible = True
        except Exception as exc:
            write_log(f"Could not update tray icon: {type(exc).__name__}: {exc}")

    def _run_on_ui(self, callback) -> None:
        try:
            self.root.after(0, callback)
        except RuntimeError:
            pass

    def _tray_toggle_window(self, _icon=None, _item=None) -> None:
        self._run_on_ui(self.toggle_window_visibility)

    def _tray_manual_refresh(self, _icon=None, _item=None) -> None:
        self._run_on_ui(self.manual_refresh)

    def _tray_open_usage_site(self, _icon=None, _item=None) -> None:
        self._run_on_ui(self.open_usage_site)

    def _tray_show_settings(self, _icon=None, _item=None) -> None:
        self._run_on_ui(lambda: (self.show_window_from_tray(), self.show_settings()))

    def _tray_show_diagnostics(self, _icon=None, _item=None) -> None:
        self._run_on_ui(lambda: (self.show_window_from_tray(), self.show_diagnostics()))

    def _tray_open_log_file(self, _icon=None, _item=None) -> None:
        self._run_on_ui(self.open_log_file)

    def _tray_exit_app(self, _icon=None, _item=None) -> None:
        self._run_on_ui(self.exit_app)

    def toggle_window_visibility(self) -> None:
        if self.window_visible and self.root.state() != "withdrawn":
            self.hide_window_to_tray()
        else:
            self.show_window_from_tray()

    def hide_window_to_tray(self) -> None:
        try:
            self.last_visible_geometry = self.root.geometry()
            SettingsStore.save_geometry(self.last_visible_geometry)
        except tk.TclError:
            pass
        self.window_visible = False
        self.root.withdraw()
        self.update_tray_icon()

    def show_window_from_tray(self) -> None:
        self.window_visible = True
        self.root.deiconify()
        try:
            if self.last_visible_geometry:
                self.root.geometry(self.last_visible_geometry)
            self.root.attributes("-topmost", self.always_on_top)
            self.root.lift()
            self.root.focus_force()
        except tk.TclError:
            pass
        self.update_tray_icon()

    def _run_loop(self) -> None:
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def set_status(self, value: str) -> None:
        compact_value = re.sub(r"\s+", " ", value).strip()
        if len(compact_value) > 120:
            compact_value = compact_value[:117] + "..."

        def apply() -> None:
            self.status_var.set(compact_value)
            self.update_tray_icon()

        if hasattr(self, "root"):
            self.root.after(0, apply)

    def restore_latest_history(self) -> None:
        latest = HistoryStore.latest_balance()
        if latest is None:
            return
        balance, timestamp = latest
        self.last_successful_update = timestamp
        self.apply_balance_ui(balance, append_history=False, updated_at=timestamp, from_history=True)
        self.set_status(tr(self.language, "Last saved data · updating...", "Данные из истории · обновление..."))

    def update_five_hour_value_display(self) -> None:
        five_hour_percent = safe_int(self.current_balance.five_hour_percent)
        weekly_percent = safe_int(self.current_balance.weekly_percent)
        reset_dt = parse_reset_datetime(self.current_balance.five_hour_reset_text)
        value_label = self.five_hour_card["value_label"]

        if weekly_percent == 0:
            self.five_hour_value_var.set(tr(self.language, "Blocked", "Блок"))
            value_label.configure(fg=RED, font=("Segoe UI", 15, "bold"))
            return

        if five_hour_percent == 0:
            compact_countdown = format_compact_countdown(reset_dt, self.language)
            if compact_countdown:
                self.five_hour_value_var.set(compact_countdown)
                value_label.configure(fg=RED, font=("Segoe UI", 16, "bold"))
                return

        self.five_hour_value_var.set(
            f"{five_hour_percent}%" if five_hour_percent is not None else tr(self.language, "not found", "не найдено")
        )
        value_label.configure(fg=usage_color(five_hour_percent), font=("Segoe UI", 12, "bold"))

    def update_weekly_value_display(self) -> None:
        weekly_percent = safe_int(self.current_balance.weekly_percent)
        reset_dt = parse_reset_datetime(self.current_balance.weekly_reset_text)
        value_label = self.weekly_card["value_label"]

        if weekly_percent == 0:
            compact_countdown = format_compact_countdown(reset_dt, self.language)
            if compact_countdown:
                self.weekly_value_var.set(compact_countdown)
                value_label.configure(fg=RED, font=("Segoe UI", 15, "bold"))
                return

        self.weekly_value_var.set(
            f"{weekly_percent}%" if weekly_percent is not None else tr(self.language, "not found", "не найдено")
        )
        value_label.configure(fg=usage_color(weekly_percent), font=("Segoe UI", 12, "bold"))

    def apply_balance_ui(
        self,
        balance: Balance,
        *,
        append_history: bool,
        updated_at: datetime | None = None,
        from_history: bool = False,
    ) -> None:
        self.current_balance = balance
        five_hour_percent = safe_int(balance.five_hour_percent)
        weekly_percent = safe_int(balance.weekly_percent)
        credits = balance.credits or tr(self.language, "not found", "не найдено")

        self.update_five_hour_value_display()
        self.update_weekly_value_display()
        self.credits_var.set(tr(self.language, f"Credits: {credits}", f"Кредиты: {credits}"))

        self.five_hour_progress.set_value(0 if weekly_percent == 0 else five_hour_percent)
        self.weekly_progress.set_value(weekly_percent)

        if append_history:
            self.history = HistoryStore.append_balance(balance)
        self.update_countdowns(schedule_next=False)
        self.update_weekly_chart()

        if from_history:
            prefix = tr(self.language, "From history: ", "Из истории: ")
            stamp = updated_at.strftime("%H:%M:%S") if updated_at else tr(self.language, "time unknown", "время неизвестно")
        else:
            prefix = tr(self.language, "Updated: ", "Обновлено: ")
            stamp = (updated_at or datetime.now()).strftime("%H:%M:%S")
        self.updated_var.set(prefix + stamp)
        self.update_tray_icon()

    def update_balance_ui(self, balance: Balance) -> None:
        def apply() -> None:
            self.apply_balance_ui(balance, append_history=True, updated_at=datetime.now())
            write_log(
                "Parsed balance: "
                f"5h={balance.five_hour_percent!r}, 5h_reset={balance.five_hour_reset_text!r}, "
                f"week={balance.weekly_percent!r}, week_reset={balance.weekly_reset_text!r}, credits={balance.credits!r}"
            )

        self.root.after(0, apply)

    def update_weekly_chart(self) -> None:
        weekly_percent = safe_int(self.current_balance.weekly_percent)
        weekly_reset_dt = parse_reset_datetime(self.current_balance.weekly_reset_text)
        can_show_chart = False
        if self.weekly_chart and self.show_burndown:
            can_show_chart = self.weekly_chart.set_data(
                history=self.history,
                weekly_percent=weekly_percent,
                weekly_reset_dt=weekly_reset_dt,
            )
        elif self.weekly_chart:
            self.weekly_chart.points = []
            self.weekly_chart.redraw()

        progress_packed = bool(self.weekly_progress.winfo_manager())
        chart_packed = bool(self.weekly_chart and self.weekly_chart.winfo_manager())

        if can_show_chart and self.weekly_chart:
            if progress_packed:
                self.weekly_progress.pack_forget()
            if not chart_packed:
                self.weekly_chart.pack(fill="x", padx=10, pady=(0, 6), before=self.weekly_card["reset_label"])
        else:
            if chart_packed and self.weekly_chart:
                self.weekly_chart.pack_forget()
            if not progress_packed:
                self.weekly_progress.pack(fill="x", padx=10, pady=(0, 6), before=self.weekly_card["reset_label"])

    def update_countdowns(self, *, schedule_next: bool = True) -> None:
        five_hour_dt = parse_reset_datetime(self.current_balance.five_hour_reset_text)
        weekly_dt = parse_reset_datetime(self.current_balance.weekly_reset_text)
        if is_weekly_limit_exhausted(self.current_balance):
            self.five_hour_reset_var.set(tr(self.language, "Blocked by weekly limit", "Заблокировано недельным лимитом"))
        else:
            self.five_hour_reset_var.set(format_countdown(five_hour_dt, self.current_balance.five_hour_reset_text, self.language))
        self.weekly_reset_var.set(format_countdown(weekly_dt, self.current_balance.weekly_reset_text, self.language))
        self.update_five_hour_value_display()
        self.update_weekly_value_display()
        self.update_weekly_chart()
        now = datetime.now()
        if (
            self.last_countdown_tray_update is None
            or (now - self.last_countdown_tray_update).total_seconds() * 1000 >= TRAY_COUNTDOWN_REFRESH_MS
        ):
            self.last_countdown_tray_update = now
            self.update_tray_icon()
        if schedule_next:
            self.root.after(COUNTDOWN_REFRESH_MS, self.update_countdowns)

    def schedule_refresh(self) -> None:
        asyncio.run_coroutine_threadsafe(self.refresh_loop(), self.loop)

    def manual_refresh(self) -> None:
        if self.refresh_in_progress:
            self.set_status(tr(self.language, "Refresh already in progress...", "Обновление уже идет..."))
            return
        future = asyncio.run_coroutine_threadsafe(self.fetch_once(), self.loop)
        future.add_done_callback(self._log_manual_refresh_exception)

    def _log_manual_refresh_exception(self, future: "asyncio.Future") -> None:
        try:
            exc = future.exception()
        except asyncio.CancelledError:
            return
        if exc is not None:
            write_log("manual_refresh: unexpected error:\n" + "".join(
                traceback.format_exception(type(exc), exc, exc.__traceback__)
            ))

    def open_usage_site(self) -> None:
        webbrowser.open(CODEX_USAGE_URL, new=2)

    def open_log_file(self) -> None:
        try:
            if not LOG_PATH.exists():
                LOG_PATH.write_text("", encoding="utf-8")
            if hasattr(os, "startfile"):
                os.startfile(str(LOG_PATH))  # type: ignore[attr-defined]
            else:
                webbrowser.open(LOG_PATH.resolve().as_uri(), new=2)
            self.set_status(tr(self.language, "Opened log", "Открыл лог"))
        except OSError as exc:
            self.set_status(tr(self.language, "Could not open log", "Не удалось открыть лог"))
            messagebox.showerror(tr(self.language, "Log", "Лог"), tr(self.language, f"Could not open log:\n{exc}", f"Не удалось открыть лог:\n{exc}"))

    def show_settings(self) -> None:
        window = tk.Toplevel(self.root)
        window.title(tr(self.language, "Settings", "Настройки"))
        window.configure(bg=BG)
        window.geometry("400x310")
        window.minsize(360, 290)
        window.transient(self.root)
        window.grab_set()

        container = tk.Frame(window, bg=BG)
        container.pack(fill="both", expand=True, padx=14, pady=14)

        tk.Label(
            container,
            text=tr(self.language, "Widget settings", "Настройки виджета"),
            font=("Segoe UI", 13, "bold"),
            bg=BG,
            fg=TEXT,
        ).pack(anchor="w", pady=(0, 10))

        always_var = tk.BooleanVar(value=self.always_on_top)
        burndown_var = tk.BooleanVar(value=self.show_burndown)
        minutes_var = tk.StringVar(value=str(max(1, int(round(self.refresh_seconds / 60)))))
        language_var = tk.StringVar(value=self.language)

        def make_check(text: str, variable: tk.BooleanVar) -> tk.Checkbutton:
            return tk.Checkbutton(
                container,
                text=text,
                variable=variable,
                font=("Segoe UI", 10),
                bg=BG,
                fg=TEXT,
                activebackground=BG,
                activeforeground=TEXT,
                selectcolor=BG,
                anchor="w",
            )

        make_check(tr(self.language, "Always on top", "Поверх окон"), always_var).pack(fill="x", pady=(0, 6))
        make_check(tr(self.language, "Show weekly burndown", "Показывать недельный burndown"), burndown_var).pack(fill="x", pady=(0, 12))

        language_row = tk.Frame(container, bg=BG)
        language_row.pack(fill="x", pady=(0, 10))
        tk.Label(language_row, text=tr(self.language, "Language:", "Язык:"), font=("Segoe UI", 10), bg=BG, fg=TEXT).pack(side="left")
        tk.Radiobutton(language_row, text="English", variable=language_var, value="en", bg=BG, fg=TEXT, selectcolor=BG).pack(side="left", padx=(8, 0))
        tk.Radiobutton(language_row, text="Русский", variable=language_var, value="ru", bg=BG, fg=TEXT, selectcolor=BG).pack(side="left", padx=(8, 0))

        interval_row = tk.Frame(container, bg=BG)
        interval_row.pack(fill="x", pady=(0, 4))
        tk.Label(interval_row, text=tr(self.language, "Refresh interval:", "Интервал обновления:"), font=("Segoe UI", 10), bg=BG, fg=TEXT).pack(side="left")
        spin = tk.Spinbox(
            interval_row,
            from_=1,
            to=60,
            textvariable=minutes_var,
            width=5,
            font=("Segoe UI", 10),
            relief="flat",
            highlightthickness=1,
            highlightbackground=BORDER,
            highlightcolor=BORDER,
        )
        spin.pack(side="left", padx=(8, 4))
        tk.Label(interval_row, text=tr(self.language, "min", "мин"), font=("Segoe UI", 10), bg=BG, fg=TEXT).pack(side="left")

        tk.Label(
            container,
            text=tr(self.language, "Changes apply after restart. The interval is used for future refreshes.", "Изменения языка применятся после перезапуска. Интервал — для следующих автообновлений."),
            font=("Segoe UI", 8),
            bg=BG,
            fg=MUTED,
        ).pack(anchor="w", pady=(0, 12))

        button_row = tk.Frame(container, bg=BG)
        button_row.pack(fill="x", side="bottom")

        def save_settings() -> None:
            try:
                minutes = int(str(minutes_var.get()).strip())
            except ValueError:
                messagebox.showerror(tr(self.language, "Settings", "Настройки"), tr(self.language, "Refresh interval must be a number of minutes.", "Интервал обновления должен быть числом минут."), parent=window)
                return
            minutes = max(1, min(60, minutes))

            self.always_on_top = bool(always_var.get())
            self.show_burndown = bool(burndown_var.get())
            self.refresh_seconds = minutes * 60
            selected_language = language_var.get() if language_var.get() in LANGUAGES else DEFAULT_LANGUAGE
            self.root.attributes("-topmost", self.always_on_top)

            self.app_settings = SettingsStore.load()
            self.app_settings.update({
                "geometry": self.root.geometry(),
                "always_on_top": self.always_on_top,
                "show_burndown": self.show_burndown,
                "refresh_seconds": self.refresh_seconds,
                "language": selected_language,
            })
            SettingsStore.save(self.app_settings)
            self.update_weekly_chart()
            self.set_status(tr(self.language, "Settings saved. Restart to apply language changes.", "Настройки сохранены. Перезапустите приложение для смены языка."))
            window.destroy()

        self._flat_button(button_row, tr(self.language, "Save", "Сохранить"), save_settings).pack(side="left")
        self._flat_button(button_row, tr(self.language, "Cancel", "Отмена"), window.destroy).pack(side="left", padx=(8, 0))

    def show_diagnostics(self) -> None:
        window = tk.Toplevel(self.root)
        window.title("Диагностика")
        window.configure(bg=BG)
        window.geometry("560x520")
        window.minsize(420, 360)
        window.transient(self.root)

        container = tk.Frame(window, bg=BG)
        container.pack(fill="both", expand=True, padx=12, pady=12)

        tk.Label(
            container,
            text="Диагностика виджета",
            font=("Segoe UI", 13, "bold"),
            bg=BG,
            fg=TEXT,
        ).pack(anchor="w", pady=(0, 8))

        text = tk.Text(
            container,
            wrap="word",
            font=("Consolas", 9),
            bg=CARD_BG,
            fg=TEXT,
            relief="flat",
            bd=0,
            highlightthickness=1,
            highlightbackground=BORDER,
            padx=10,
            pady=10,
        )
        text.pack(fill="both", expand=True)
        text.insert("1.0", self.build_diagnostics_text())
        text.configure(state="disabled")

        button_row = tk.Frame(container, bg=BG)
        button_row.pack(fill="x", pady=(10, 0))
        self._flat_button(button_row, "Обновить данные", lambda: self._refresh_diagnostics_text(text)).pack(side="left")
        self._flat_button(button_row, "Скопировать", lambda: self.copy_diagnostics_text(text)).pack(side="left", padx=(8, 0))
        self._flat_button(button_row, "Открыть лог", self.open_log_file).pack(side="left", padx=(8, 0))
        self._flat_button(button_row, "Закрыть", window.destroy).pack(side="right")

    def _refresh_diagnostics_text(self, text_widget: tk.Text) -> None:
        text_widget.configure(state="normal")
        text_widget.delete("1.0", "end")
        text_widget.insert("1.0", self.build_diagnostics_text())
        text_widget.configure(state="disabled")

    def copy_diagnostics_text(self, text_widget: tk.Text) -> None:
        content = text_widget.get("1.0", "end").strip()
        self.root.clipboard_clear()
        self.root.clipboard_append(content)
        self.set_status("Диагностика скопирована")

    def build_diagnostics_text(self) -> str:
        now = datetime.now()
        balance = self.current_balance
        five_hour_percent = safe_int(balance.five_hour_percent)
        weekly_percent = safe_int(balance.weekly_percent)
        five_hour_dt = parse_reset_datetime(balance.five_hour_reset_text, now=now)
        weekly_dt = parse_reset_datetime(balance.weekly_reset_text, now=now)
        history_items = HistoryStore.load()
        current_week_points = 0
        if weekly_dt:
            week_start = weekly_dt - timedelta(days=7)
            for item in history_items:
                timestamp = parse_iso_datetime(item.get("timestamp"))
                if timestamp and week_start <= timestamp <= weekly_dt:
                    current_week_points += 1

        def yes_no(value: bool) -> str:
            return "да" if value else "нет"

        def path_state(path: Path) -> str:
            try:
                if path.exists():
                    if path.is_file():
                        return f"есть, {path.stat().st_size} байт"
                    return "есть"
                return "нет"
            except OSError as exc:
                return f"ошибка доступа: {exc}"

        def dt_text(value: datetime | None) -> str:
            return value.strftime("%Y-%m-%d %H:%M:%S") if value else "нет"

        lines = [
            f"Версия: {APP_VERSION}",
            f"Время диагностики: {now.strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "Настройки",
            f"Поверх окон: {yes_no(self.always_on_top)}",
            f"Показывать burndown: {yes_no(self.show_burndown)}",
            f"Интервал обновления: {self.refresh_seconds // 60} мин",
            f"Геометрия окна: {self.root.geometry()}",
            f"Окно видимо: {yes_no(self.window_visible and self.root.state() != 'withdrawn')}",
            "",
            "Трей",
            f"pystray/Pillow доступны: {yes_no(pystray is not None and Image is not None)}",
            f"Ошибка импорта трея: {TRAY_IMPORT_ERROR or 'нет'}",
            f"Трей запущен: {yes_no(self.tray_enabled)}",
            "",
            "Браузер и сессия",
            f"Chrome найден: {yes_no(bool(self.chrome_path))}",
            f"Chrome path: {self.chrome_path or 'нет'}",
            f"Профиль Chrome: {PROFILE_DIR}",
            f"Профиль Chrome существует: {yes_no(PROFILE_DIR.exists())}",
            f"Сохраненная сессия найдена: {yes_no(has_saved_chrome_session())}",
            "",
            "Последнее обновление",
            f"Последний успешный апдейт: {dt_text(self.last_successful_update)}",
            f"Последний статус fetch: {self.last_fetch_status or 'нет'}",
            f"Последняя ошибка fetch: {self.last_fetch_error or 'нет'}",
            f"Размер текста Usage: {self.last_usage_text_length if self.last_usage_text_length is not None else 'нет'}",
            "",
            "Распознавание данных",
            f"5 часов найдено: {yes_no(five_hour_percent is not None)} ({five_hour_percent if five_hour_percent is not None else 'нет'})",
            f"Сброс 5 часов текст: {balance.five_hour_reset_text or 'нет'}",
            f"Сброс 5 часов дата: {dt_text(five_hour_dt)}",
            f"Неделя найдена: {yes_no(weekly_percent is not None)} ({weekly_percent if weekly_percent is not None else 'нет'})",
            f"Сброс недели текст: {balance.weekly_reset_text or 'нет'}",
            f"Сброс недели дата: {dt_text(weekly_dt)}",
            f"Кредиты найдены: {yes_no(bool(balance.credits))} ({balance.credits or 'нет'})",
            "",
            "История и график",
            f"Файл истории: {HISTORY_PATH}",
            f"Файл истории: {path_state(HISTORY_PATH)}",
            f"Точек истории всего: {len(history_items)}",
            f"Точек текущего недельного цикла: {current_week_points}",
            f"Недельный график сейчас: {yes_no(bool(self.weekly_chart and self.weekly_chart.winfo_manager()))}",
            "",
            "Служебные файлы",
            f"Папка приложения: {APP_DIR}",
            f"Файл настроек: {path_state(SETTINGS_PATH)}",
            f"Файл лога: {path_state(LOG_PATH)}",
            f"Файл lock: {path_state(APP_LOCK_PATH)}",
        ]
        return "\n".join(lines)

    def show_help(self) -> None:
        chrome_info = self.chrome_path or "Chrome не найден автоматически"
        messagebox.showinfo(
            "Помощь",
            f"Версия виджета: {APP_VERSION}\n\n"
            "Виджет использует отдельный профиль Chrome в папке codex_chrome_profile.\n\n"
            f"Chrome:\n{chrome_info}\n\n"
            "Если профиль пустой или вход слетел, виджет откроет Chrome. "
            "Войдите в ChatGPT вручную, дальше обновления будут идти скрыто.\n\n"
            "Недельный график строится по локальной истории, пока виджет запущен. "
            "Если истории мало или дата сброса не распознана, показывается обычный прогресс-бар.\n\n"
            "Настройки, диагностика, лог и помощь доступны через кнопку настроек. "
            "В настройках можно менять режим поверх окон, недельный burndown и интервал обновления. "
            "Диагностика показывает состояние Chrome, парсера, истории и служебных файлов.\n\n"
            "Если установлены pystray и Pillow, виджет работает в трее: крестик прячет окно, "
            "двойной клик или меню трея возвращают его, а пункт Выход завершает программу.",
        )

    async def fetch_once(self) -> None:
        if self.refresh_in_progress:
            self.set_status(tr(self.language, "Refresh already in progress...", "Обновление уже идет..."))
            return

        self.refresh_in_progress = True
        try:
            json_result = await self.json_provider.fetch()

            # A JSON "ok" status only counts as a real success if it actually carried
            # recognizable usage fields; otherwise it must fall through to the Chrome
            # fallback below (CR-01), just like a genuine JSON fetch error would.
            json_ok_with_data = False
            if json_result.status == "ok":
                json_ok_with_data = build_balance_from_json_fields(json_result.fields or {}).has_usage_data

            if json_ok_with_data:
                outcome = plan_fetch_outcome(
                    json_status="ok",
                    json_fields=json_result.fields,
                    json_error=None,
                    chrome_attempted=False,
                    chrome_status=None,
                    chrome_error=None,
                    chrome_text=None,
                    has_existing_data=self.current_balance.has_usage_data,
                    language=self.language,
                )
                self.last_fetch_status = "ok"
                self.last_fetch_error = None
                self.last_usage_text_length = None
            elif not self.browser:
                json_error = (
                    json_result.error
                    if json_result.status != "ok"
                    else "json response had no recognizable usage fields"
                )
                outcome = plan_fetch_outcome(
                    json_status="error",
                    json_fields=None,
                    json_error=json_error,
                    chrome_attempted=False,
                    chrome_status="chrome_not_found",
                    chrome_error=None,
                    chrome_text=None,
                    has_existing_data=self.current_balance.has_usage_data,
                    language=self.language,
                )
                self.last_fetch_status = "chrome_not_found"
                self.last_fetch_error = tr(self.language, "Google Chrome not found", "Google Chrome не найден")
            else:
                result = await self.browser.fetch()
                self.last_fetch_status = result.status
                self.last_fetch_error = result.error
                self.last_usage_text_length = len(result.text) if result.text else None
                json_error = (
                    json_result.error
                    if json_result.status != "ok"
                    else "json response had no recognizable usage fields"
                )
                outcome = plan_fetch_outcome(
                    json_status="error",
                    json_fields=None,
                    json_error=json_error,
                    chrome_attempted=True,
                    chrome_status=result.status,
                    chrome_error=result.error,
                    chrome_text=result.text,
                    has_existing_data=self.current_balance.has_usage_data,
                    language=self.language,
                )

            if outcome.balance is not None:
                self.last_successful_update = datetime.now()
                self.update_balance_ui(outcome.balance)
            self.set_status(outcome.status_message)
            write_log(outcome.log_line)
        finally:
            self.refresh_in_progress = False

    async def refresh_loop(self) -> None:
        while True:
            try:
                await self.fetch_once()
            except Exception as exc:
                write_log("refresh_loop: unexpected error, continuing:\n" + "".join(
                    traceback.format_exception(type(exc), exc, exc.__traceback__)
                ))
            await asyncio.sleep(self.refresh_seconds)

    def on_close(self) -> None:
        if self.tray_enabled and not self.is_exiting:
            self.hide_window_to_tray()
            return
        self.exit_app()

    def exit_app(self) -> None:
        if self.is_exiting:
            return
        self.is_exiting = True
        try:
            if self.root.state() != "withdrawn":
                self.last_visible_geometry = self.root.geometry()
            SettingsStore.save_geometry(self.last_visible_geometry)
        except tk.TclError:
            pass

        if self.tray_icon is not None:
            try:
                self.tray_icon.stop()
            except Exception as exc:
                write_log(f"Could not stop tray icon: {type(exc).__name__}: {exc}")

        try:
            self.loop.call_soon_threadsafe(self.loop.stop)
        except RuntimeError:
            pass

        try:
            self.root.destroy()
        except tk.TclError:
            pass

    def run(self) -> None:
        self.root.mainloop()


if __name__ == "__main__":
    app_lock = acquire_app_lock()
    if not app_lock:
        messagebox.showinfo(WINDOW_TITLE, "Виджет уже запущен.")
        raise SystemExit

    atexit.register(app_lock.close)
    write_log(f"Starting widget {APP_VERSION} via {os.sys.executable}")
    app = CodexBalanceWidget()
    app.run()
