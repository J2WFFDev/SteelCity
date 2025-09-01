#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, sys
from typing import Any, Dict, List, Optional

# Lightweight schema v1 (avoid heavy deps). Use jsonschema if installed.
SCHEMA = {
    "required": ["seq", "type", "ts_ms"],
    "type_values": {"event", "status", "info", "error", "debug"},
    # Optional fields: msg (str), data (object), plate (str), t_rel_ms (number), session_id (str), pid (int)
}


def validate_record(rec: Dict[str, Any], idx: int) -> Optional[str]:
    for k in SCHEMA["required"]:
        if k not in rec:
            return f"missing required field '{k}'"
    if not isinstance(rec["seq"], int) or rec["seq"] < 0:
        return "'seq' must be a non-negative integer"
    if rec["type"] not in SCHEMA["type_values"]:
        return f"'type' must be one of {sorted(SCHEMA['type_values'])}"
    # ts_ms can be float or int
    if not isinstance(rec["ts_ms"], (int, float)):
        return "'ts_ms' must be a number"
    if "t_rel_ms" in rec and not isinstance(rec["t_rel_ms"], (int, float, type(None))):
        return "'t_rel_ms' must be a number or null"
    if "msg" in rec and not isinstance(rec["msg"], str):
        return "'msg' must be a string"
    if "data" in rec and not isinstance(rec["data"], dict):
        return "'data' must be an object"
    if "plate" in rec and not isinstance(rec["plate"], str):
        return "'plate' must be a string"
    if "session_id" in rec and not isinstance(rec["session_id"], str):
        return "'session_id' must be a string"
    if "pid" in rec and not isinstance(rec["pid"], int):
        return "'pid' must be an integer"
    return None


def main():
    ap = argparse.ArgumentParser(description="Validate NDJSON log file against schema v1")
    ap.add_argument("file", help="Path to NDJSON log file")
    ap.add_argument("--max-errors", type=int, default=50, dest="max_errors")
    args = ap.parse_args()

    errors: List[str] = []
    with open(args.file, "r", encoding="utf-8") as f:
        for i, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception as e:
                errors.append(f"line {i}: invalid JSON: {e}")
                if len(errors) >= args.max_errors:
                    break
                continue
            err = validate_record(rec, i)
            if err:
                errors.append(f"line {i}: {err}")
                if len(errors) >= args.max_errors:
                    break

    if errors:
        print(f"FAIL: {len(errors)} validation error(s)")
        for e in errors:
            print(e)
        sys.exit(1)
    else:
        print("PASS: schema v1 validation ok")


if __name__ == "__main__":
    main()
