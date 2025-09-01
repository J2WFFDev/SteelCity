#!/usr/bin/env python3
import sys, json, argparse, time, os


def _pretty_print(rec: dict) -> bool:
    typ = rec.get("type")
    msg = rec.get("msg", "") or ""
    if typ == "info" and msg == "amg_connected":
        data = rec.get("data", {}) or {}
        mac = data.get("mac")
        adapter = data.get("adapter")
        print(f"AMG connected (adapter={adapter}, mac={mac})")
        return True
    if typ == "event" and msg == "T0":
        print("Beep (T0)")
        return True
    if typ == "event" and msg.startswith("AMG_"):
        name = msg.replace("AMG_", "")
        # Normalize names
        label = {
            "START_BTN": "Start button",
            "ARROW_END": "End (arrow press)",
            "TIMEOUT_END": "End (timeout)",
        }.get(name, name)
        print(label)
        return True
    if typ == "event" and msg == "SESSION_END":
        reason = (rec.get("data", {}) or {}).get("reason")
        print(f"Session end (reason={reason})")
        return True
    if typ == "event" and msg == "HIT":
        # Keep concise, show relative time if available
        t_rel = rec.get("t_rel_ms")
        if isinstance(t_rel, (int, float)):
            print(f"Hit at {t_rel/1000.0:.3f}s")
        else:
            print("Hit")
        return True
    return False


def _process_stream(it, *, pretty: bool, include_raw: bool):
    for line in it:
        try:
            rec = json.loads(line)
        except Exception:
            continue
        typ = rec.get("type")
        msg = rec.get("msg", "") or ""
        if pretty:
            shown = _pretty_print(rec)
            if shown:
                continue
        if typ == "event" and (msg == "T0" or msg.startswith("AMG_") or msg == "SESSION_END" or msg == "HIT"):
            print(line, end="")
            sys.stdout.flush()
        elif typ == "info" and msg == "amg_connected":
            print(line, end="")
            sys.stdout.flush()
        elif include_raw and typ == "debug" and msg == "amg_raw":
            print(line, end="")
            sys.stdout.flush()


def main():
    ap = argparse.ArgumentParser(description="Filter NDJSON for AMG/T0/session events")
    ap.add_argument("--raw", action="store_true", help="Include amg_raw debug frames if present")
    ap.add_argument("--pretty", action="store_true", help="Print concise human-readable lines")
    ap.add_argument("--file", help="Path to NDJSON file to follow (reads stdin if not provided)")
    ap.add_argument("--from-start", action="store_true", help="If using --file, start at beginning instead of end")
    args = ap.parse_args()

    if args.pretty:
        print("READY: Watching for AMG events... Turn on AMG now.")
        sys.stdout.flush()

    # If a file is provided, follow it directly to avoid external tail/quoting issues
    if args.file:
        path = args.file
        # Ensure directory exists and file eventually appears
        while not os.path.exists(path):
            time.sleep(0.2)
        with open(path, "r", encoding="utf-8") as fh:
            if not args.from_start:
                fh.seek(0, os.SEEK_END)
            while True:
                pos = fh.tell()
                line = fh.readline()
                if not line:
                    time.sleep(0.1)
                    fh.seek(pos)
                    continue
                _process_stream([line], pretty=args.pretty, include_raw=args.raw)
    else:
        _process_stream(sys.stdin, pretty=args.pretty, include_raw=args.raw)


if __name__ == "__main__":
    main()
