import csv
import subprocess
from .conftest import data_path


def test_decode_stream_smoke(tmp_path):
    in_csv = data_path("wtvb_stream.csv")
    out_csv = tmp_path / "decoded.csv"
    res = subprocess.run([
        "python", "tools/wtvb_decode_5561.py", in_csv, str(out_csv)
    ], capture_output=True, text=True)
    assert res.returncode == 0, res.stderr
    rows = list(csv.DictReader(open(out_csv, newline="")))
    # basic checks
    assert rows, "no rows decoded"
    # Check columns presence
    first = rows[0]
    for col in [
        "utc_iso","type_hex","w08","w09","w10","d08","d09","d10","mag"
    ]:
        assert col in first


def test_decode_contains_known_spike(tmp_path):
    in_csv = data_path("wtvb_stream.csv")
    out_csv = tmp_path / "decoded.csv"
    res = subprocess.run([
        "python", "tools/wtvb_decode_5561.py", in_csv, str(out_csv)
    ], capture_output=True, text=True)
    assert res.returncode == 0, res.stderr
    rows = list(csv.DictReader(open(out_csv, newline="")))

    # look for a magnitude around 347.2 (±0.2 tolerance)
    found = False
    for r in rows:
        try:
            mag = float(r["mag"])
        except Exception:
            continue
        if abs(mag - 347.2) <= 0.2:
            found = True
            break
    assert found, "expected spike mag≈347.2 not found"
