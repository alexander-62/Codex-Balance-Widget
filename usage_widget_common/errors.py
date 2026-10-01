from __future__ import annotations


class FetchError(RuntimeError):
    """Generic, retryable-aware fetch exception.

    Generalizes `probe_wham_usage.ProbeError` (Phase 1/2 of
    codex_balance_widget): any fetch operation raises this on failure.
    `retryable` (keyword-only, default False) distinguishes transient
    failures (network error, timeout, HTTP 429) — which a caller may safely
    retry once — from permanent failures (401/403, malformed payload) which
    should not be retried.
    """

    def __init__(self, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.retryable = retryable
