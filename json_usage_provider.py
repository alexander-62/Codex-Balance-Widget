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

Uses stdlib and the bundled usage_widget_common package. No UI dependency.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

import probe_wham_usage

from usage_widget_common.retry import fetch_with_retry_once

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
        # Delegates to the shared retry-once engine (usage_widget_common.retry,
        # Phase 3 extraction of this method's former manual loop).
        # probe_wham_usage.ProbeError is an alias for
        # usage_widget_common.errors.FetchError, so the shared engine's
        # `except FetchError` classification (retryable vs not) still applies
        # unchanged to every error this closure can raise.
        async def _do_fetch() -> dict:
            payload = await self._fetch_payload(access_token, account_id)
            return probe_wham_usage.extract_fields(payload)

        outcome = await fetch_with_retry_once(_do_fetch, retry_delay=self.retry_delay)
        return JsonFetchResult(
            outcome.status, fields=outcome.value, error=outcome.error, retried=outcome.retried
        )

    async def _fetch_payload(self, access_token: str, account_id: str | None) -> dict:
        _, payload = await asyncio.to_thread(
            probe_wham_usage.fetch_usage, access_token, account_id, self.timeout
        )
        return payload
