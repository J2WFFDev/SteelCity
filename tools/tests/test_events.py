import csv
import subprocess
from .conftest import data_path


def test_events_from_csv_smoke(tmp_path):
    decoded = data_path("wtvb_decoded.csv")
    out_csv = tmp_path / "events.csv"
    res = subprocess.run([
        "python", "tools/events_from_csv.py", decoded, str(out_csv), "120", "0.20"
    ], capture_output=True, text=True)
    assert res.returncode == 0, res.stderr
    rows = list(csv.DictReader(open(out_csv, newline="")))
    assert len(rows) == 10, f"expected 10 events, got {len(rows)}"


def test_watch_events_offline(tmp_path):
    decoded = data_path("wtvb_decoded.csv")
    res = subprocess.run([
        "python", "tools/watch_events.py", decoded, "--thr", "120", "--gap-s", "0.20", "--hz", "25", "--from-start", "--exit-on-eof"
    ], capture_output=True, text=True)
    assert res.returncode == 0, res.stderr
    lines = [ln for ln in res.stdout.splitlines() if ln and not ln.startswith("start_utc,")]
    assert len(lines) == 10, f"expected 10 event lines, got {len(lines)}"
    # ensure one line contains ~347.2 in column 5 (max_mag)
    found = any(
        (len(line.split(",")) >= 5 and abs(float(line.split(",")[4]) - 347.2) <= 0.2)
        for line in lines
    )
    assert found, "expected event with max_mag≈347.2 not found"
