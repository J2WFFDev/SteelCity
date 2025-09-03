#!/usr/bin/env python3
import sqlite3
from collections import defaultdict
import sys

db = sys.argv[1] if len(sys.argv)>1 else 'logs/bridge.db'
con = sqlite3.connect(db)
cur = con.cursor()
rows = cur.execute("select session_id, seq, ts_ms, msg from events where msg in ('T0','HIT') order by ts_ms").fetchall()
per = defaultdict(lambda: {'t0': [], 'hit': []})
for sid, seq, ts, msg in rows:
    per[sid or ''][msg.lower()].append((seq, ts))
for sid, lists in per.items():
    print('SID>', repr(sid))
    print(' t0s:', lists['t0'])
    print(' hits:', lists['hit'])
    for t0seq, t0ts in lists['t0']:
        for hitseq, hitts in lists['hit']:
            if hitts > t0ts and (hitts - t0ts) <= 200:
                print('  MATCH:', t0seq, '->', hitseq, 'offset_ms=', hitts - t0ts)
