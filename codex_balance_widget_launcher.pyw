from __future__ import annotations

import runpy
import sys
import traceback
from datetime import datetime
from pathlib import Path


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
except Exception:
    write_log("Widget crashed before startup:")
    with LOG_PATH.open("a", encoding="utf-8") as log_file:
        traceback.print_exc(file=log_file)
