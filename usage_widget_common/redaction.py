from __future__ import annotations

from typing import Any

REDACTED_PLACEHOLDER = "<redacted>"
DEFAULT_FORBIDDEN_SUBSTRINGS: tuple[str, ...] = ("eyJ", "@")


def redact(obj: Any, *, keys: frozenset[str]) -> Any:
    """Recursively replace sensitive values with `REDACTED_PLACEHOLDER`.

    Generalizes `probe_wham_usage.redact` (Phase 1): the caller supplies its
    OWN domain-specific denylist via `keys` (e.g. field names like `user_id`,
    `account_id`, `email`); this function only owns the generic traversal
    plus the fixed, shared `"token"`-substring rule (any key containing
    "token", case-insensitively, is redacted regardless of `keys`). This
    split is deliberate: it prevents a widget's domain-specific denylist
    from ever being centralized here, where it could silently drift out of
    sync with another widget's own payload schema (see this plan's threat
    model, T-3-02).

    Never mutates the input — always returns a new structure. Dicts are
    recursed key-by-key; lists are recursed element-by-element; any other
    value (str, int, None, ...) is returned unchanged.
    """
    if isinstance(obj, dict):
        result: dict[Any, Any] = {}
        for key, value in obj.items():
            if isinstance(key, str) and (key in keys or "token" in key.lower()):
                result[key] = REDACTED_PLACEHOLDER
            else:
                result[key] = redact(value, keys=keys)
        return result
    if isinstance(obj, list):
        return [redact(item, keys=keys) for item in obj]
    return obj


def redaction_clean(
    text: str, forbidden_substrings: tuple[str, ...] = DEFAULT_FORBIDDEN_SUBSTRINGS
) -> bool:
    """Post-check: `text` must contain none of `forbidden_substrings`.

    Generalizes `probe_wham_usage.redaction_clean` (Phase 1) — by default
    guards against a leaked JWT prefix (`eyJ`) or an email address (`@`)
    slipping past `redact()`'s key-based redaction.
    """
    return all(s not in text for s in forbidden_substrings)
