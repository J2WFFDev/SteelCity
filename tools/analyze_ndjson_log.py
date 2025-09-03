import json
import sys
from collections import Counter

if len(sys.argv) < 2:
    print('Usage: analyze_ndjson_log.py <path>')
    sys.exit(2)

p = sys.argv[1]
try:
    tot = 0
    debug = 0
    missing_ca = 0
    le = 0
    gt = 0
    msgs = Counter()
    with open(p, 'r', encoding='utf-8') as f:
        for l in f:
            l = l.strip()
            if not l:
                continue
            try:
                o = json.loads(l)
            except Exception:
                continue
            tot += 1
            t = o.get('type')
            m = o.get('msg')
            msgs[m] += 1
            if t == 'debug':
                debug += 1
                data = o.get('data') if isinstance(o.get('data'), dict) else {}
                ca = data.get('current_amp')
                if ca is None:
                    missing_ca += 1
                else:
                    try:
                        v = float(ca)
                        if abs(v) <= 0.001:
                            le += 1
                        else:
                            gt += 1
                    except Exception:
                        missing_ca += 1
    print(f"total_lines: {tot}")
    print(f"debug_lines: {debug}")
    print(f"debug_current_amp<=0.001: {le}")
    print(f"debug_current_amp>0.001: {gt}")
    print(f"debug_missing_current_amp: {missing_ca}")
    print('\nTop 12 messages:')
    for k, v in msgs.most_common(12):
        print(f"{k}: {v}")
except FileNotFoundError:
    print('MISSING FILE', p)
    sys.exit(1)
