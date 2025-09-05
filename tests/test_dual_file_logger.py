import json
from steelcity_impact_bridge.logs import NdjsonLogger


def test_dual_file_writes(tmp_path):
    base = tmp_path / "logs"
    base.mkdir()
    # Enable dual-file and place debug files under debug/ subdir
    logger = NdjsonLogger(str(base), "bridge_test", dual_file=True, debug_subdir="debug")

    # Write an info and a debug entry (debug may be filtered from main in regular mode)
    logger.mode = "regular"
    logger.write({"type": "info", "msg": "op_info", "data": {"a": 1}})
    logger.write({"type": "debug", "msg": "op_debug", "data": {"a": 2}})

    # Find main file
    mains = list(base.glob("bridge_test_*.ndjson"))
    assert mains, "main log file missing"
    main_text = mains[0].read_text(encoding="utf-8")
    main_lines = [l for l in main_text.splitlines() if l.strip()]
    # In regular mode the debug line should be filtered from the main file
    assert any("op_info" in l for l in main_lines)
    assert not any("op_debug" in l for l in main_lines)

    # Debug file should exist under debug/ and contain both entries
    debug_dir = base / "debug"
    assert debug_dir.exists()
    debug_files = list(debug_dir.glob("bridge_test_debug_*.ndjson"))
    assert debug_files, "debug file missing"
    dbg_text = debug_files[0].read_text(encoding="utf-8")
    dbg_lines = [l for l in dbg_text.splitlines() if l.strip()]
    assert any("op_info" in l for l in dbg_lines)
    assert any("op_debug" in l for l in dbg_lines)
