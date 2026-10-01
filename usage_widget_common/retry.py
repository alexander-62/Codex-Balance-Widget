from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from .errors import FetchError


@dataclass
class RetryOutcome:
    status: str  # "ok" | "error"
    value: Any | None = None
    error: str | None = None
    retried: bool = False


async def fetch_with_retry_once(
    fetch_once: Callable[[], Awaitable[Any]], *, retry_delay: float = 1.0
) -> RetryOutcome:
    """At-most-2-attempt retry-once wrapper around any async fetch callable.

    Mirrors `json_usage_provider.JsonUsageProvider._fetch_with_retry` (Phase
    2 of codex_balance_widget); now the single shared implementation any
    widget calls. An immediate try, then (only for `FetchError(retryable=
    True)` failures) one retry after `retry_delay` seconds. Non-`FetchError`
    exceptions are always treated as non-retryable. The first attempt's
    error message is preserved and chained onto the second attempt's message
    if both fail, so neither failure is silently discarded.
    """
    first_error: str | None = None
    for attempt in range(2):
        if attempt == 1:
            await asyncio.sleep(retry_delay)
        try:
            value = await fetch_once()
            return RetryOutcome("ok", value=value, retried=attempt == 1)
        except FetchError as exc:
            error_text = str(exc)
            retryable = exc.retryable
        except Exception as exc:  # unexpected error - do not crash the loop
            error_text = f"{type(exc).__name__}: {exc}"
            retryable = False

        if attempt == 0 and retryable:
            first_error = error_text
            continue
        if first_error is not None:
            error_text = f"{first_error}; retry: {error_text}"
        return RetryOutcome("error", error=error_text, retried=attempt == 1)

    # Unreachable: attempt 0 either returns or `continue`s into attempt 1,
    # and attempt 1 always returns. Kept only to satisfy static analysis.
    return RetryOutcome("error", error=first_error, retried=True)
