#!/usr/bin/env python3
"""Normalize NDJSON log fields: MACs, UUIDs, and sensor_id -> plate.

Usage: python tools/normalize_ndjson.py <in.ndjson> <out.ndjson>
"""
from __future__ import annotations
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict
import uuid


def normalize_mac(s: str) -> str:
    if not isinstance(s, str):
        return s
    # remove non-hex chars
    hexs = re.sub(r'[^0-9A-Fa-f]', '', s)
    if len(hexs) != 12:
        return s
    return ':'.join(hexs[i:i+2] for i in range(0, 12, 2)).upper()


def normalize_uuid(s: str) -> str:
    try:
        u = uuid.UUID(s)
        return str(u)
    except Exception:
        return s


def extract_plate(sensor_id: str) -> str | None:
    if not isinstance(sensor_id, str):
        return None
    # common pattern: Sensor_12E3 -> 12E3
    m = re.search(r'([0-9A-Fa-f]{2,})$', sensor_id)
    if m:
        return m.group(1).upper()
    return None


def normalize_obj(o: Dict[str, Any]) -> Dict[str, Any]:
    data = o.get('data') if isinstance(o.get('data'), dict) else {}

    # normalize mac fields in top-level and data
    for f in ('mac', 'adapter'):
        if f in o and isinstance(o[f], str):
            o[f] = normalize_mac(o[f])
    for f in ('mac', 'notify_uuid', 'config_uuid', 'start_uuid'):
        v = data.get(f)
        if isinstance(v, str):
            if 'uuid' in f or 'start_uuid' in f:
                data[f] = normalize_uuid(v)
            else:
                data[f] = normalize_mac(v)

    # sensor_id -> plate
    sid = o.get('sensor_id') or data.get('sensor_id')
    if sid:
        plate = extract_plate(sid)
        if plate:
            o['plate'] = plate
        # also normalize sensor_id to keep original style but upper hex portion
        if isinstance(sid, str):
            o['sensor_id'] = sid

    # Canonicalize hex-like payload fields into data['hex'] so downstream
    # consumers (AMG parser, reports) can rely on a single field.
    # Common names: 'hex', 'payload', 'frame', 'payload_hex', 'raw'
    for candidate in ('hex', 'payload', 'frame', 'payload_hex', 'raw'):
        v = data.get(candidate) or o.get(candidate)
        if isinstance(v, str) and v.strip():
            # normalize common 0x prefix and spaces
            s = v.strip()
            if s.lower().startswith('0x'):
                s = s[2:]
            s = s.replace(' ', '')
            # A reasonable hex payload length for AMG frames is 28 chars (14 bytes)
            # but we accept other lengths too; only keep if it looks hex-like.
            if all(c in '0123456789abcdefABCDEF' for c in s):
                data['hex'] = s
                break

    # write normalized flag for auditing
    o.setdefault('normalized', True)
    o['data'] = data
    return o


def main(argv=None):
    argv = argv or sys.argv[1:]
    if len(argv) < 2:
        print('Usage: normalize_ndjson.py in.ndjson out.ndjson')
        return 2
    inp = Path(argv[0])
    outp = Path(argv[1])
    outp.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with inp.open('r', encoding='utf-8') as inf, outp.open('w', encoding='utf-8') as outf:
        for line in inf:
            line = line.strip()
            if not line:
                continue
            try:
                o = json.loads(line)
            except Exception:
                continue
            o2 = normalize_obj(o)
            outf.write(json.dumps(o2) + '\n')
            n += 1
    print(f'Wrote {n} normalized lines to {outp}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
