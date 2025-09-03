import json
import sys
from pathlib import Path

import pytest


# Ensure the 'src' directory (where the package lives) is importable
REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from steelcity_impact_bridge.logs import NdjsonLogger


def _read_ndjson_lines(d: Path):
    files = list(d.glob("*.ndjson"))
    contents = []
    for f in files:
        with f.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    contents.append(json.loads(line))
    return contents


def test_suppresses_empty_heartbeat(tmp_path: Path):
    d = tmp_path / "logs"
    logger = NdjsonLogger(str(d), "testbridge")
    logger.mode = "regular"
    # heartbeat with empty sensors should be suppressed
    logger.write({"type": "status", "msg": "alive", "data": {"sensors": []}})
    lines = _read_ndjson_lines(d)
    assert len(lines) == 0


def test_bt50_buffer_status_whitelist_and_default(tmp_path: Path):
    d = tmp_path / "logs"
    # default: no whitelist -> suppressed
    logger = NdjsonLogger(str(d), "testbridge")
    logger.mode = "regular"
    logger.verbose_whitelist = set()
    logger.write({"type": "debug", "msg": "bt50_buffer_status", "data": {}})
    assert len(_read_ndjson_lines(d)) == 0

    # with whitelist -> allowed
    d2 = tmp_path / "logs2"
    logger2 = NdjsonLogger(str(d2), "testbridge")
    logger2.mode = "regular"
    logger2.verbose_whitelist = {"bt50_buffer_status"}
    logger2.write({"type": "debug", "msg": "bt50_buffer_status", "data": {}})
    lines = _read_ndjson_lines(d2)
    # Files may be hardlinked/aliased; ensure at least one unique entry with the expected msg exists
    unique = {json.dumps(l, sort_keys=True) for l in lines}
    assert any(json.loads(u).get("msg") == "bt50_buffer_status" for u in unique)


def test_current_amp_threshold_suppression(tmp_path: Path):
    d = tmp_path / "logs"
    logger = NdjsonLogger(str(d), "testbridge")
    logger.mode = "regular"
    logger.verbose_whitelist = set()
    # set a threshold so that tiny amps are suppressed
    logger.current_amp_threshold = 0.001

    # small amplitude -> suppressed
    logger.write({"type": "debug", "msg": "some_debug", "data": {"current_amp": 0.0}})
    assert len(_read_ndjson_lines(d)) == 0

    # larger amplitude -> allowed
    logger.write({"type": "debug", "msg": "some_debug", "data": {"current_amp": 0.01}})
    lines = _read_ndjson_lines(d)
    unique = {json.dumps(l, sort_keys=True) for l in lines}
    # Ensure at least one entry with the expected current_amp exists
    found = False
    for u in unique:
        obj = json.loads(u)
        data = obj.get("data") or {}
        ca = data.get("current_amp")
        try:
            if ca is not None and abs(float(ca) - 0.01) < 1e-6:
                found = True
                break
        except Exception:
            continue
    assert found, f"Expected to find an entry with current_amp ~0.01 in {unique}"
