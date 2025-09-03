#!/usr/bin/env python3
"""Inspect the events DB and print counts and sample rows containing 'amg'.
Usage: python inspect_db.py /path/to/logs/bridge.db
"""
import sys, sqlite3, json

if len(sys.argv) < 2:
    print('Usage: inspect_db.py /path/to/bridge.db')
    sys.exit(2)

db = sys.argv[1]
conn = sqlite3.connect(db)
cur = conn.cursor()
print('Type counts:')
for row in cur.execute('select type, count(*) from events group by type'):
    print(' ', row[0], row[1])
print('\nTop messages:')
for row in cur.execute("select msg, count(*) as cnt from events group by msg order by cnt desc limit 20"):
    print(' ', row[0], row[1])
print('\nSample AMG-containing data_json rows:')
for row in cur.execute("select data_json from events where data_json like '%amg%' limit 10"):
    try:
        j = json.loads(row[0])
        print(' ', json.dumps(j, separators=(',',':')))
    except Exception:
        print('  <invalid json>')
