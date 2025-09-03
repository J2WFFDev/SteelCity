#!/usr/bin/env python3
"""Quick NDJSON summary for a log file: counts, top messages, macs, sensor_ids, normalized count."""
import sys, json, collections

def summarize(path, n=10):
    total = 0
    types = collections.Counter()
    msgs = collections.Counter()
    macs = collections.Counter()
    sensor_ids = collections.Counter()
    normalized = 0
    plates = collections.Counter()
    with open(path, 'r', encoding='utf-8') as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            total += 1
            try:
                obj = json.loads(line)
            except Exception:
                continue
            types.update([obj.get('type')])
            msgs.update([obj.get('msg')])
            if obj.get('normalized'):
                normalized += 1
            data = obj.get('data') if isinstance(obj.get('data'), dict) else {}
            mac = data.get('mac')
            if mac:
                macs.update([mac.upper()])
            sid = data.get('sensor_id') or obj.get('sensor_id')
            if sid:
                sensor_ids.update([sid])
            plate = obj.get('plate') or data.get('plate')
            if plate:
                plates.update([plate])
    print(f"File: {path}")
    print(f"Total lines: {total}")
    print("Types:")
    for k,v in types.most_common():
        print(f"  {k}: {v}")
    print("Top messages:")
    for k,v in msgs.most_common(n):
        print(f"  {k}: {v}")
    print("Top MACs:")
    for k,v in macs.most_common(n):
        print(f"  {k}: {v}")
    print("Top Sensor IDs:")
    for k,v in sensor_ids.most_common(n):
        print(f"  {k}: {v}")
    print(f"Normalized count: {normalized}")
    print("Top plates:")
    for k,v in plates.most_common(n):
        print(f"  {k}: {v}")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: quick_log_summary.py <path> [top_n]")
        sys.exit(2)
    path = sys.argv[1]
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    summarize(path, n)
