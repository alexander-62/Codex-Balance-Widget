"""Async, thin wrapper over probe_wham_usage's wham/usage client.

Implements the "one retry on transient error, otherwise immediate
fallback signal" policy (see 02-CONTEXT.md D-02/D-03):

- load_tokens failure -> immediate JsonFetchResult(status="error"), no
  retry (auth/config problems never self-heal within a single fetch).
- fetch_usage failure with ProbeError.retryable=False (401/403/other
  non-transient HTTP codes, bad content-type, malformed JSON) ->
  immediate JsonFetchResult(status="error"), no retry (D-02).
- fetch_usage failure with ProbeError.retryable=True (429, network
  error, timeout) -> exactly one retry after a short delay, then give
  up regardless of the outcome (D-03).

Only stdlib is used (asyncio, dataclasses) plus probe_wham_usage itself.
No Tk/UI dependency — this module is safe to import from any caller,
sync or async, without side effects on import.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

import probe_wham_usage

RETRY_DELAY_SECONDS = 1.0


@dataclass
class JsonFetchResult:
    status: str  # "ok" | "error"
    fields: dict | None = None
    error: str | None = None
    retried: bool = False


class JsonUsageProvider:
    def __init__(
        self,
        timeout: float = probe_wham_usage.REQUEST_TIMEOUT_SECONDS,
        retry_delay: float = RETRY_DELAY_SECONDS,
    ) -> None:
        self.timeout = timeout
        self.retry_delay = retry_delay

    async def fetch(self) -> JsonFetchResult:
        try:
            access_token, account_id = await asyncio.to_thread(
                probe_wham_usage.load_tokens, probe_wham_usage.auth_json_path()
            )
        except probe_wham_usage.ProbeError as exc:
            return JsonFetchResult("error", error=str(exc))

        return await self._fetch_with_retry(access_token, account_id)

    async def _fetch_with_retry(self, access_token: str, account_id: str | None) -> JsonFetchResult:
        # At most 2 attempts: an immediate try, then (for retryable failures
        # only) one retry after a short delay. Both attempts share this loop
        # so a future fix only has to be applied in one place (see 02-REVIEW
        # WR-01). `first_error` keeps the first attempt's failure message
        # around so it isn't silently discarded if the retry also fails
        # (02-REVIEW WR-02).
        first_error: str | None = None
        for attempt in range(2):
            if attempt == 1:
                await asyncio.sleep(self.retry_delay)
            try:
                payload = await self._fetch_payload(access_token, account_id)
                return JsonFetchResult(
                    "ok", fields=probe_wham_usage.extract_fields(payload), retried=attempt == 1
                )
            except probe_wham_usage.ProbeError as exc:
                error_text = str(exc)
                retryable = exc.retryable
            except Exception as exc:  # unexpected schema/encoding/IO error - do not crash the loop
                error_text = f"{type(exc).__name__}: {exc}"
                retryable = False

            if attempt == 0 and retryable:
                first_error = error_text
                continue
            if first_error is not None:
                error_text = f"{first_error}; retry: {error_text}"
            return JsonFetchResult("error", error=error_text, retried=attempt == 1)

        # Unreachable: attempt 0 either returns or `continue`s into attempt 1,
        # and attempt 1 always returns. Kept only to satisfy static analysis.
        return JsonFetchResult("error", error=first_error, retried=True)

    async def _fetch_payload(self, access_token: str, account_id: str | None) -> dict:
        _, payload = await asyncio.to_thread(
            probe_wham_usage.fetch_usage, access_token, account_id, self.timeout
        )
        return payload
