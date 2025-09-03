import sys
import json
from statistics import median

path = sys.argv[1]
threshold = float(sys.argv[2]) if len(sys.argv) > 2 else 0.001

counts = {}
msg_counts = {}
amps = []
examples = {"Timer_START_BTN": [], "Sensor_Initialized": [], "SHOT_RAW": [], "HIT": [], "bt50_buffer_status": []}

with open(path, 'r', encoding='utf-8') as f:
    for i, line in enumerate(f):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except Exception as e:
            print(f"LINE {i+1} JSONERR: {e}")
            continue
        t = obj.get('type')
        counts[t] = counts.get(t, 0) + 1
        m = obj.get('msg')
        if m:
            msg_counts[m] = msg_counts.get(m, 0) + 1
            if m in examples and len(examples[m]) < 3:
                examples[m].append(obj)
        # collect bt50 amps
        if m == 'bt50_buffer_status' or (t == 'debug' and m == 'bt50_buffer_status'):
            examples['bt50_buffer_status'].append(obj)
        # try capture current_amp
        data = obj.get('data', {})
        ca = data.get('current_amp') if isinstance(data, dict) else None
        if ca is not None:
            try:
                amps.append(float(ca))
            except Exception:
                pass

print('file:', path)
print('total_lines:', sum(counts.values()))
print('counts by type:')
for k in sorted(counts.keys()):
    print(f'  {k}: {counts[k]}')
print('top messages:')
for m, c in sorted(msg_counts.items(), key=lambda x: -x[1])[:20]:
    print(f'  {m}: {c}')

if amps:
    amps_sorted = sorted(amps)
    print('current_amp stats: min', min(amps_sorted), 'median', median(amps_sorted), 'max', max(amps_sorted))
    # bucket counts
    buckets = {'<=0.001':0, '<=1':0, '<=5':0, '<=10':0, '<=50':0, '>50':0}
    for a in amps_sorted:
        if a <= 0.001:
            buckets['<=0.001'] += 1
        elif a <= 1:
            buckets['<=1'] += 1
        elif a <= 5:
            buckets['<=5'] += 1
        elif a <= 10:
            buckets['<=10'] += 1
        elif a <= 50:
            buckets['<=50'] += 1
        else:
            buckets['>50'] += 1
    print('amp buckets:')
    for k,v in buckets.items():
        print(' ', k, v)
else:
    print('no numeric current_amp found')

print('\nExamples:')
for k, arr in examples.items():
    if not arr:
        continue
    print('---', k, '---')
    for ex in arr[:3]:
        print(json.dumps(ex, ensure_ascii=False))

