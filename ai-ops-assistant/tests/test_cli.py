import json
import subprocess
import sys


def test_evaluation_cli_has_utf8_json_on_windows():
    completed = subprocess.run([sys.executable, "-m", "ai_ops.evaluate"], check=True,
                               capture_output=True, timeout=15)
    report = json.loads(completed.stdout.decode("utf-8"))
    assert report["positive_cases"] == 20
    assert any("バックアップ" in case["query"] for case in report["cases"])

