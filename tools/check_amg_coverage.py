#!/usr/bin/env python3
import sqlite3, json, sys

db = sys.argv[1] if len(sys.argv) > 1 else '/home/jrwest/projects/steelcity/logs/bridge.db'
con = sqlite3.connect(db)
cur = con.cursor()
print('amg_raw_count=', cur.execute("select count(*) from events where msg='amg_raw'").fetchone()[0])
print('data_contains_amg_key_count=', cur.execute("select count(*) from events where data_json like '%\"amg\"%'").fetchone()[0])
print('\nSample amg_raw rows:')
for row in cur.execute("select data_json from events where msg='amg_raw' limit 5"):
    try:
        print(json.loads(row[0]))
    except Exception:
        print('<invalid json>')
print('\nSample events with data.amg key:')
for row in cur.execute("select data_json from events where data_json like '%\\"amg\\"%' limit 5"):
    try:
        print(json.loads(row[0]))
    except Exception:
        print('<invalid json>')
con.close()
