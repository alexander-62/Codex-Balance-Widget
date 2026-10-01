"""Packaging regression: imports must work without a sibling checkout."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


def test_imports_use_bundled_library_from_standalone_copy(tmp_path):
    source = Path(__file__).resolve().parent
    project = tmp_path / "standalone"
    project.mkdir()
    for name in ("codex_balance_widget_chrome.py", "json_usage_provider.py", "probe_wham_usage.py", "demo.py"):
        shutil.copy2(source / name, project / name)
    shutil.copytree(source / "usage_widget_common", project / "usage_widget_common", ignore=shutil.ignore_patterns("__pycache__"))
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    result = subprocess.run(
        [sys.executable, "-c", "import json, pathlib; import codex_balance_widget_chrome, json_usage_provider, probe_wham_usage, demo, usage_widget_common; print(json.dumps(str(pathlib.Path(usage_widget_common.__file__).resolve())))"],
        cwd=project, env=env, capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert Path(json.loads(result.stdout)).parent == project / "usage_widget_common"
    assert not (tmp_path / "usage_widget_common").exists()
