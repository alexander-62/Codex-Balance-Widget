from __future__ import annotations

from dataclasses import dataclass


@dataclass
class FetchDecision:
    source: str  # "primary" | "fallback" | "retain_existing" | "none"


def decide_fetch_source(
    *, primary_ok: bool, fallback_ok: bool, has_existing_data: bool
) -> FetchDecision:
    """Pure fetch-decision skeleton: which source's data should be shown.

    Generalizes `codex_balance_widget_chrome.plan_fetch_outcome`'s 3-way
    choice ("primary source ok" / "primary source failed -> fallback" /
    "both failed -> retain existing data"). Callers define what "ok" means
    for their own primary/fallback source (e.g. "HTTP succeeded AND the
    response had recognizable data") — this function only expresses the
    3-way choice, not source-specific status parsing. Source-specific
    statuses (e.g. Chrome's `login_required`/`browser_error`) stay in the
    widget.
    """
    if primary_ok:
        return FetchDecision("primary")
    if fallback_ok:
        return FetchDecision("fallback")
    if has_existing_data:
        return FetchDecision("retain_existing")
    return FetchDecision("none")
