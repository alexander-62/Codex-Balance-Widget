from __future__ import annotations

import runpy
import sys
import traceback
from datetime import datetime
from pathlib import Path
from tkinter import messagebox


BASE_DIR = Path(__file__).resolve().parent
SCRIPT_PATH = BASE_DIR / "codex_balance_widget_chrome.py"
LOG_PATH = BASE_DIR / "widget_launch.log"


def write_log(message: str) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with LOG_PATH.open("a", encoding="utf-8") as log_file:
        log_file.write(f"[{timestamp}] {message}\n")


try:
    sys.path.insert(0, str(BASE_DIR))
    write_log(f"Starting widget via {sys.executable}")
    runpy.run_path(str(SCRIPT_PATH), run_name="__main__")
except SystemExit as exc:
    # A bare `raise SystemExit` (e.g. the "already running" app-lock case in
    # codex_balance_widget_chrome.py) already shows its own messagebox before
    # exiting, so only surface a dialog here when there is an actual message
    # (e.g. probe_wham_usage.py raising SystemExit when run as __main__).
    if exc.code not in (None, 0):
        # Log-write failure (unwritable path, disk full, locked file, etc.)
        # must never suppress the messagebox below (see 03-REVIEW.md WR-03,
        # iteration 3) — mirror write_log's own internal `except OSError`.
        try:
            write_log(f"Widget exited during startup: {exc.code}")
        except OSError:
            pass
        messagebox.showerror("Codex Balance Widget", f"Widget failed to start:\n\n{exc.code}")
except ModuleNotFoundError as exc:
    # The usage_widget_common sibling-repo bootstrap check (probe_wham_usage.py
    # / json_usage_provider.py / codex_balance_widget_chrome.py) raises this as
    # a plain, catchable exception rather than SystemExit so unittest/pytest
    # still report it cleanly as an import error (03-REVIEW.md WR-01,
    # iteration 2). Surface the same clean diagnostic to the GUI user here.
    try:
        write_log(f"Widget exited during startup: {exc}")
    except OSError:
        pass
    messagebox.showerror("Codex Balance Widget", f"Widget failed to start:\n\n{exc}")
except Exception:
    try:
        write_log("Widget crashed before startup:")
        with LOG_PATH.open("a", encoding="utf-8") as log_file:
            traceback.print_exc(file=log_file)
    except OSError:
        pass
    messagebox.showerror(
        "Codex Balance Widget",
        "Widget crashed before startup. See widget_launch.log for details.",
    )
