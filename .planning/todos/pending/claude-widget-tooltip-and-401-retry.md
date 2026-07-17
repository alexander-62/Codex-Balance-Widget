---
title: "Claude-виджет: обрезка tooltip до 127 и быстрый ретрай после 401"
date: 2026-07-17
priority: high
project: d:\00_Projects\claude_balance_widget_v1
---

Два подтверждённых логом бага в `claude_balance_widget.py`:

1. **Tray tooltip падает.** Лог: `Tray update failed: ValueError: string too long (142, maximum length 128)`.
   Причина: `build_tray_tooltip()` обрезает до 160 символов (`tooltip[:160]`, строка ~709),
   а лимит Windows/pystray — 128. Фикс: `tooltip[:127]`.

2. **401 держит баннер «обновить не удалось» весь интервал (5 мин).**
   Лог: `Fetch failed: RuntimeError: Авторизация Claude Code истекла` при старте,
   восстановление только на следующем цикле, когда Claude Code сам обновил токен
   в `.credentials.json`. Виджет читает accessToken и не рефрешит его сам.
   Фикс: после 401 (и сетевых ошибок) быстрый повтор через 30–60 сек с backoff
   (например 30 → 60 → 120 сек, потом обычный интервал), а не ждать полный refresh_seconds.
