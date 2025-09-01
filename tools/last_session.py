import argparse
import glob
import json
import time
from pathlib import Path
from typing import Optional


def latest_ndjson_path(repo_root: Path) -> Optional[Path]:
    logs_dir = repo_root / "logs"
    candidates = sorted(logs_dir.glob("bridge_*.ndjson"), key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0] if candidates else None


def extract_last_session_id(path: Path) -> Optional[str]:
    last_sid: Optional[str] = None
    try:
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    rec = json.loads(line)
                except Exception:
                    continue
                sid = rec.get("session_id")
                if isinstance(sid, str) and sid:
                    last_sid = sid
    except FileNotFoundError:
        return None
    return last_sid


def main() -> None:
    ap = argparse.ArgumentParser(description="Print latest session_id and/or latest NDJSON path")
    ap.add_argument("--path", type=Path, default=None, help="Explicit NDJSON path; if omitted, use latest under logs/")
    ap.add_argument("--print-path", action="store_true", help="Print the NDJSON path instead of session_id")
    ap.add_argument("--wait-sec", type=int, default=0, help="Wait up to N seconds for session_id to appear (polling)")
    args = ap.parse_args()

    repo = Path.cwd()
    target = args.path or latest_ndjson_path(repo)
    if not target:
        print("")
        return

    if args.print_path:
        print(str(target))
        return

    # else print session_id, optionally waiting
    deadline = time.time() + max(0, int(args.wait_sec))
    sid: Optional[str] = None
    while time.time() <= deadline:
        sid = extract_last_session_id(target)
        if sid:
            break
        time.sleep(1)
    print(sid or "")


if __name__ == "__main__":
    main()
