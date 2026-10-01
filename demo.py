"""Offline preview using the real widget UI and synthetic data only."""
from __future__ import annotations

import argparse
import ctypes
import json
from datetime import datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

import codex_balance_widget_chrome as widget


class DemoWidget(widget.CodexBalanceWidget):
    def _start_single_instance_listener(self) -> None:
        # Leave the real widget's instance and listening port alone.
        pass

    def setup_tray_icon(self) -> None:
        pass

    def schedule_refresh(self) -> None:
        self.manual_refresh()

    def manual_refresh(self) -> None:
        now = datetime.now()
        reset = now + timedelta(days=3, hours=8)
        self.history = [
            {"timestamp": (now - timedelta(hours=hours)).isoformat(), "weekly_percent": percent}
            for hours, percent in [(88, 100), (72, 95), (56, 88), (40, 78), (24, 67), (12, 60), (0, 54)]
        ]
        self.apply_balance_ui(
            widget.Balance(
                five_hour_percent="78", weekly_percent="54", credits="120",
                reset_credits_available="2", reset_credits_applicable="1",
                five_hour_reset_text=(now + timedelta(hours=3, minutes=42)).isoformat(sep=" "),
                weekly_reset_text=reset.isoformat(sep=" "),
            ),
            append_history=False, updated_at=now,
        )
        self.status_var.set(widget.tr(self.language, "Demo: sample data, offline", "Демо: пример данных, без сети"))

    async def fetch_once(self) -> None:
        # Defense in depth: even a future UI action must not read credentials.
        self.manual_refresh()

    def open_usage_site(self) -> None:
        self.status_var.set(widget.tr(self.language, "Demo: browser disabled", "Демо: браузер отключён"))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--language", choices=("en", "ru"), default="en")
    parser.add_argument("--screenshot", type=Path, help="Save this window as PNG and exit (Pillow 11.2.1+).")
    args = parser.parse_args()
    # All settings, history and diagnostics stay in an isolated temporary folder.
    with TemporaryDirectory(prefix="codex-widget-demo-") as directory:
        base = Path(directory)
        widget.SETTINGS_PATH = base / "settings.json"
        widget.HISTORY_PATH = base / "history.json"
        widget.LOG_PATH = base / "demo.log"
        widget.PROFILE_DIR = base / "chrome"
        widget.SETTINGS_PATH.write_text(json.dumps({
            "language": args.language, "geometry": "420x430+100+100",
            "always_on_top": False, "show_burndown": True,
        }), encoding="utf-8")
        app = DemoWidget()
        app.root.title("Codex Balance Widget - Demo")
        app.manual_refresh()
        capture_errors = []
        if args.screenshot:
            def capture() -> None:
                try:
                    from PIL import ImageGrab
                    app.root.update_idletasks()
                    # Capture only our own window, not the desktop or other apps.
                    get_parent = ctypes.windll.user32.GetParent
                    get_parent.argtypes = [ctypes.c_void_p]
                    get_parent.restype = ctypes.c_void_p
                    handle = get_parent(app.root.winfo_id())
                    args.screenshot.parent.mkdir(parents=True, exist_ok=True)
                    ImageGrab.grab(window=handle).save(args.screenshot)
                except Exception as exc:
                    capture_errors.append(exc)
                finally:
                    app.exit_app()
            app.root.after(1200, capture)
        app.run()
        app.worker.join(timeout=2)
        if not app.loop.is_running():
            app.loop.close()
        if capture_errors:
            raise capture_errors[0]


if __name__ == "__main__":
    main()
