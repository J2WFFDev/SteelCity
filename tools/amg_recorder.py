#!/usr/bin/env python3
import asyncio, argparse, csv, datetime as dt, os, sys
from collections import Counter, defaultdict
from typing import Optional, List, Tuple
from bleak import BleakScanner, BleakClient

# ---------- utilities ----------
def now_iso():
    return dt.datetime.utcnow().isoformat(timespec="milliseconds")+"Z"

def bhex(b: bytes) -> str:
    return b.hex()

def split_bytes(b: bytes) -> List[str]:
    return [f"{x:02x}" for x in b]

def le32(x: bytes) -> int:
    return int.from_bytes(x, "little", signed=False)

def le16(x: bytes) -> int:
    return int.from_bytes(x, "little", signed=False)

def parse_frame(b: bytes):
    if len(b) != 14:
        return None
    tag = b[0]
    return {
        "tag": tag,                                # b0
        "secs_le": le32(b[1:5]),                   # b1..b4
        "mid_zero": all(v == 0 for v in b[5:13]),  # b5..b12 all zero?
        "p1": le16(b[5:7]),                        # b5..b6
        "p2": le16(b[7:9]),                        # b7..b8
        "p3": le16(b[9:11]),                       # b9..b10
        "p4": le16(b[11:13]),                      # b11..b12
        "tail": b[13],                             # b13
        "hex": bhex(b),
        "bytes": split_bytes(b)
    }

# ---------- recorder ----------
class Recorder:
    def __init__(self, csv_path: str, trace: bool, echo_ms: float, auto_detect: bool):
        self.csv_path = csv_path
        self.trace = trace
        self.echo = echo_ms / 1000.0
        self.auto_detect = auto_detect
        self._csv = None
        self._w = None
        self.start_time = None
        self.running = False
        self.beep_t0 = None
        self.prev_mid = None
        self.tail_hist = Counter()
        self.mid_transitions = Counter()  # (prev_mid, curr_mid)
        self.shot_idx = 0

    def open(self):
        header_needed = not os.path.exists(self.csv_path) or os.stat(self.csv_path).st_size == 0
        self._csv = open(self.csv_path, "a", newline="")
        self._w = csv.writer(self._csv)
PYmod +x amg_recorder.py":pt:csv, args.trace, args.echo_ms, args.auto_detect, args.secs))seconds")ransitions")loat]):)['p2']},
-bash: PY: command not found
(.venv) jrwest@Pitts:~/projects/steelcity/tools $ chmod +x amg_recorder.py
(.venv) jrwest@Pitts:~/projects/steelcity/tools $ rm -f ~/projects/steelcity/amg_log.csv

./amg_recorder.py --adapter hci0 --mac 60:09:C3:1F:DC:1A \
  --ctl 6e400003-b5a3-f393-e0a9-e50e24dcca9e \
  --csv ~/projects/steelcity/amg_log.csv \
  --trace --auto-detect --echo-ms 10
[ble] connect 60:09:C3:1F:DC:1A (AMG Lab COMM DC1A) …
[sub] 6e400003-b5a3-f393-e0a9-e50e24dcca9e
[rec] logging… (q to quit)

[controls] type: p=power_on, t=start_btn, b=beep, s=shot, a=arrow, x=power_off, m <text>=mark, q=quit

t[frame] mid=1 secs=     5 tail=0x01 p1..p4=0,0,0,0 hex=0105000000000000000000000001
[mark] auto_beep elapsed=-0.010s
[frame] mid=0 secs= 65795 tail=0x01 p1..p4=229,229,229,229 hex=0103010100e500e500e500e50001
b[frame] mid=0 secs= 65800 tail=0x01 p1..p4=229,229,229,229 hex=0108010100e500e500e500e50001
[frame] mid=0 secs= 65541 tail=0x02 p1..p4=0,0,229,229 hex=010500010000000000e500e50002
[frame] mid=0 secs= 65795 tail=0x02 p1..p4=180,180,180,180 hex=0103010100b400b400b400b40002
[frame] mid=0 secs=16908803 tail=0x02 p1..p4=92,168,436,92 hex=01030202015c00a800b4015c0002
[frame] mid=0 secs=16908808 tail=0x02 p1..p4=92,168,436,92 hex=01080202015c00a800b4015c0002
[frame] mid=0 secs=131077 tail=0x03 p1..p4=0,0,436,92 hex=010500020000000000b4015c0003
[frame] mid=0 secs= 65795 tail=0x03 p1..p4=58,58,58,58 hex=01030101003a003a003a003a0003
[frame] mid=0 secs=131587 tail=0x03 p1..p4=73,15,58,73 hex=010302020049000f003a00490003
[frame] mid=0 secs=197379 tail=0x03 p1..p4=168,95,58,168 hex=0103030300a8005f003a00a80003
[frame] mid=0 secs=263171 tail=0x03 p1..p4=229,61,58,229 hex=0103040400e5003d003a00e50003
[frame] mid=0 secs=263176 tail=0x03 p1..p4=229,61,58,229 hex=0108040400e5003d003a00e50003
[frame] mid=0 secs=262149 tail=0x04 p1..p4=0,0,58,229 hex=0105000400000000003a00e50004
[frame] mid=0 secs= 65795 tail=0x04 p1..p4=73,73,73,73 hex=0103010100490049004900490004
[frame] mid=0 secs=131587 tail=0x04 p1..p4=128,55,73,128 hex=0103020200800037004900800004
[frame] mid=0 secs=197379 tail=0x04 p1..p4=184,56,73,184 hex=0103030300b80038004900b80004
[frame] mid=0 secs=17040387 tail=0x04 p1..p4=81,153,329,81 hex=0103040401510099004901510004
[frame] mid=0 secs=17106179 tail=0x04 p1..p4=96,15,329,96 hex=010305050160000f004901600004
[frame] mid=0 secs=17106184 tail=0x04 p1..p4=96,15,329,96 hex=010805050160000f004901600004
[frame] mid=0 secs=327685 tail=0x05 p1..p4=0,0,329,96 hex=0105000500000000004901600005
[frame] mid=0 secs= 65795 tail=0x05 p1..p4=116,116,116,116 hex=0103010100740074007400740005
[frame] mid=0 secs=131587 tail=0x05 p1..p4=171,55,116,171 hex=0103020200ab0037007400ab0005
[frame] mid=0 secs=197379 tail=0x05 p1..p4=234,63,116,234 hex=0103030300ea003f007400ea0005
[frame] mid=0 secs=17040387 tail=0x05 p1..p4=34,56,372,34 hex=0103040401220038007401220005
[frame] mid=0 secs=17106179 tail=0x05 p1..p4=180,146,372,180 hex=0103050501b40092007401b40005
[frame] mid=0 secs=17171971 tail=0x05 p1..p4=252,72,372,252 hex=0103060601fc0048007401fc0005
[frame] mid=0 secs=17171976 tail=0x05 p1..p4=252,72,372,252 hex=0108060601fc0048007401fc0005
q
[mark] tbq elapsed=78.335s
^C
--- Tail histogram ---
tail 0x01: 3
tail 0x02: 4
tail 0x03: 6
tail 0x04: 7
tail 0x05: 8

--- mid_zero transitions ---
0 -> 0 : 26
1 -> 0 : 1
^C
(.venv) jrwest@Pitts:~/projects/steelcity/tools $ awk -F, 'NR>1 && $3=="frame"{print $27}' ~/projects/steelcity/amg_log.csv | sort | uniq -c
      1 0
      3 116
      1 180
      3 229
      4 329
      4 372
      3 436
      6 58
      3 73
(.venv) jrwest@Pitts:~/projects/steelcity/tools $ awk -F, 'NR>1 && $3=="frame"{print $23}' ~/projects/steelcity/amg_log.csv | \
  awk 'BEGIN{prev=""}{ if(prev!=""){print prev "->" $1} prev=$1 }' | sort | uniq -c
      1 131077->65795
      3 131587->197379
      1 16908803->16908808
      1 16908808->131077
      2 17040387->17106179
      1 17106179->17106184
      1 17106179->17171971
      1 17106184->327685
      1 17171971->17171976
      2 197379->17040387
      1 197379->263171
      1 262149->65795
      1 263171->263176
      1 263176->262149
      1 327685->65795
      1 5->65795
      1 65541->65795
      3 65795->131587
      1 65795->16908803
      1 65795->65800
      1 65800->65541
(.venv) jrwest@Pitts:~/projects/steelcity/tools $ # Print rows around marks and show p1..p4 beside them (cols 24..27)
awk -F, 'NR==1 || $3=="mark" || ($3=="frame" && $24+$25+$26+$27>0)' ~/projects/steelcity/amg_log.csv | head -n 200
utc_iso,t_rel_ms,type,label,mac,uuid,len,hex,b0,b1,b2,b3,b4,b5,b6,b7,b8,b9,b10,b11,b12,b13,secs_le,mid_zero,p1,p2,p3,p4,tail_hex
2025-08-27T21:51:56.532Z,0,frame,,60:09:C3:1F:DC:1A,6e400003-b5a3-f393-e0a9-e50e24dcca9e,14,0105000000000000000000000001,01,05,00,00,00,00,00,00,00,00,00,00,00,01,5,1,0,0,0,0,0x01
2025-08-27T21:51:58.872Z,2340,mark,auto_beep,,,,,,,,,,,,,,,,,,,,,,,,
2025-08-27T21:51:58.873Z,2340,frame,,60:09:C3:1F:DC:1A,6e400003-b5a3-f393-e0a9-e50e24dcca9e,14,0103010100e500e500e500e50001,01,03,01,01,00,e5,00,e5,00,e5,00,e5,00,01,65795,0,229,229,229,229,0x01
2025-08-27T21:52:04.186Z,7654,frame,,60:09:C3:1F:DC:1A,6e400003-b5a3-f393-e0a9-e50e24dcca9e,14,0108010100e500e500e500e50001,01,08,01,01,00,e5,00,e5,00,e5,00,e5,00,01,65800,0,229,229,229,229,0x01
2025-08-27T21:52:10.280Z,13747,frame,,60:09:C3:1F:DC:1A,6e400003-b5a3-f393-e0a9-e50e24dcca9e,14,010500010000000000e500e50002,01,05,00,01,00,00,00,00,00,e5,00,e5,00,02,65541,0,0,0,229,229,0x02
2025-08-27T21:52:12.132Z,15600,frame,,60:09:C3:1F:DC:1A,6e400003-b5a3-f393-e0a9-e50e24dcca9e,14,0103010100b400b400b400b40002,01,03,01,01,00,b4,00,b4,00,b4,00,b4,00,02,65795,0,180,180,180,180,0x02
2025-08-27T21:52:13.789Z,17257,frame,,60:09:C3:1F:DC:1A,6e400003-b5a3-f393-e0a9-e50e24dcca9e,14,01030202015c00a800b4015c0002,01,03,02,02,01,5c,00,a8,00,b4,01,5c,00,02,16908803,0,92,168,436,92,0x02
2025-08-27T21:52:14.813Z,18281,frame,,60:09:C3:1F:DC:1A,6e400003-b5a3-f393-e0a9-e50e24dcca9e,14,01080202015c00a800b4015c0002,01,08,02,02,01,5c,00,a8,00,b4,01,5c,00,02,16908808,0,92,168,436,92,0x02
2025-08-27T21:52:19.640Z,23107,frame,,60:09:C3:1F:DC:1A,6e400003-b5a3-f393-e0a9-e50e24dcca9e,14,010500020000000000b4015c0003,01,05,00,02,00,00,00,00,00,b4,01,5c,00,03,131077,0,0,0,436,92,0x03
2025-08-27T21:52:20.274Z,23741,frame,,60:09:C3:1F:DC:1A,6e400003-b5a3-f393-e0a9-e50e24dcca9e,14,01030101003a003a003a003a0003,01,03,01,01,00,3a,00,3a,00,3a,00,3a,00,03,65795,0,58,58,58,58,0x03
2025-08-27T21:52:20.469Z,23936,frame,,60:09:C3:1F:DC:1A,6e400003-b5a3-f393-e0a9-e50e24dcca9e,14,010302020049000f003a00490003,01,03,02,02,00,49,00,0f,00,3a,00,49,00,03,131587,0,73,15,58,73,0x03
2025-08-27T21:52:21.395Z,24863,frame,,60:09:C3:1F:DC:1A,6e400003-b5a3-f393-e0a9-e50e24dcca9e,14,0103030300a8005f003a00a80003,01,03,03,03,00,a8,00,5f,00,3a,00,a8,00,03,197379,0,168,95,58,168,0x03
2025-08-27T21:52:21.980Z,25448,frame,,60:09:C3:1F:DC:1A,6e400003-b5a3-f393-e0a9-e50e24dcca9e,14,0103040400e5003d003a00e50003,01,03,04,04,00,e5,00,3d,00,3a,00,e5,00,03,263171,0,229,61,58,229,0x03
2025-08-27T21:52:22.809Z,26276,frame,,60:09:C3:1F:DC:1A,6e400003-b5a3-f393-e0a9-e50e24dcca9e,14,0108040400e5003d003a00e50003,01,08,04,04,00,e5,00,3d,00,3a,00,e5,00,03,263176,0,229,61,58,229,0x03
2025-08-27T21:52:26.660Z,30128,frame,,60:09:C3:1F:DC:1A,6e400003-b5a3-f393-e0a9-e50e24dcca9e,14,0105000400000000003a00e50004,01,05,00,04,00,00,00,00,00,3a,00,e5,00,04,262149,0,0,0,58,229,0x04
2025-08-27T21:52:27.440Z,30908,frame,,60:09:C3:1F:DC:1A,6e400003-b5a3-f393-e0a9-e50e24dcca9e,14,0103010100490049004900490004,01,03,01,01,00,49,00,49,00,49,00,49,00,04,65795,0,73,73,73,73,0x04
2025-08-27T21:52:27.976Z,31444,frame,,60:09:C3:1F:DC:1A,6e400003-b5a3-f393-e0a9-e50e24dcca9e,14,0103020200800037004900800004,01,03,02,02,00,80,00,37,00,49,00,80,00,04,131587,0,128,55,73,128,0x04
2025-08-27T21:52:28.512Z,31980,frame,,60:09:C3:1F:DC:1A,6e400003-b5a3-f393-e0a9-e50e24dcca9e,14,0103030300b80038004900b80004,01,03,03,03,00,b8,00,38,00,49,00,b8,00,04,197379,0,184,56,73,184,0x04
2025-08-27T21:52:30.121Z,33589,frame,,60:09:C3:1F:DC:1A,6e400003-b5a3-f393-e0a9-e50e24dcca9e,14,0103040401510099004901510004,01,03,04,04,01,51,00,99,00,49,01,51,00,04,17040387,0,81,153,329,81,0x04
2025-08-27T21:52:30.218Z,33686,frame,,60:09:C3:1F:DC:1A,6e400003-b5a3-f393-e0a9-e50e24dcca9e,14,010305050160000f004901600004,01,03,05,05,01,60,00,0f,00,49,01,60,00,04,17106179,0,96,15,329,96,0x04
2025-08-27T21:52:31.437Z,34905,frame,,60:09:C3:1F:DC:1A,6e400003-b5a3-f393-e0a9-e50e24dcca9e,14,010805050160000f004901600004,01,08,05,05,01,60,00,0f,00,49,01,60,00,04,17106184,0,96,15,329,96,0x04
2025-08-27T21:52:35.727Z,39195,frame,,60:09:C3:1F:DC:1A,6e400003-b5a3-f393-e0a9-e50e24dcca9e,14,0105000500000000004901600005,01,05,00,05,00,00,00,00,00,49,01,60,00,05,327685,0,0,0,329,96,0x05
2025-08-27T21:52:36.897Z,40365,frame,,60:09:C3:1F:DC:1A,6e400003-b5a3-f393-e0a9-e50e24dcca9e,14,0103010100740074007400740005,01,03,01,01,00,74,00,74,00,74,00,74,00,05,65795,0,116,116,116,116,0x05
2025-08-27T21:52:37.482Z,40950,frame,,60:09:C3:1F:DC:1A,6e400003-b5a3-f393-e0a9-e50e24dcca9e,14,0103020200ab0037007400ab0005,01,03,02,02,00,ab,00,37,00,74,00,ab,00,05,131587,0,171,55,116,171,0x05
2025-08-27T21:52:38.165Z,41632,frame,,60:09:C3:1F:DC:1A,6e400003-b5a3-f393-e0a9-e50e24dcca9e,14,0103030300ea003f007400ea0005,01,03,03,03,00,ea,00,3f,00,74,00,ea,00,05,197379,0,234,63,116,234,0x05
2025-08-27T21:52:38.652Z,42120,frame,,60:09:C3:1F:DC:1A,6e400003-b5a3-f393-e0a9-e50e24dcca9e,14,0103040401220038007401220005,01,03,04,04,01,22,00,38,00,74,01,22,00,05,17040387,0,34,56,372,34,0x05
2025-08-27T21:52:40.115Z,43582,frame,,60:09:C3:1F:DC:1A,6e400003-b5a3-f393-e0a9-e50e24dcca9e,14,0103050501b40092007401b40005,01,03,05,05,01,b4,00,92,00,74,01,b4,00,05,17106179,0,180,146,372,180,0x05
2025-08-27T21:52:40.895Z,44362,frame,,60:09:C3:1F:DC:1A,6e400003-b5a3-f393-e0a9-e50e24dcca9e,14,0103060601fc0048007401fc0005,01,03,06,06,01,fc,00,48,00,74,01,fc,00,05,17171971,0,252,72,372,252,0x05
2025-08-27T21:52:41.772Z,45240,frame,,60:09:C3:1F:DC:1A,6e400003-b5a3-f393-e0a9-e50e24dcca9e,14,0108060601fc0048007401fc0005,01,08,06,06,01,fc,00,48,00,74,01,fc,00,05,17171976,0,252,72,372,252,0x05
2025-08-27T21:53:17.218Z,80685,mark,tbq,,,,,,,,,,,,,,,,,,,,,,,,
(.venv) jrwest@Pitts:~/projects/steelcity/tools $PY

