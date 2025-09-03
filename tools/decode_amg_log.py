
import struct
import json
import sys

def decode_amg_shot(raw_hex):
    payload = bytes.fromhex(raw_hex)
    if len(payload) < 7 or payload[0] != 0x01:
        return None
    shot_time = struct.unpack_from("<I", payload, 1)[0]
    tail_flag = payload[-1]
    mid_section = payload[5:-1].hex()
    return {
        "shot_time": shot_time,
        "tail_flag": tail_flag,
        "mid_section": mid_section,
        "raw_hex": raw_hex
    }

def process_log(ndjson_path):
    with open(ndjson_path) as f:
        for line in f:
            try:
                event = json.loads(line)
            except Exception:
                continue
            if event.get("msg") == "SHOT_RAW" and "raw" in event.get("data", {}):
                decoded = decode_amg_shot(event["data"]["raw"])
                if decoded:
                    print(f"SHOT_RAW: time={decoded['shot_time']} tail=0x{decoded['tail_flag']:02x} mid={decoded['mid_section']} raw={decoded['raw_hex']}")
            elif event.get("msg") in ("AMG_CONNECTED", "Timer_START_BTN", "Timer_T0", "Timer_SESSION_END"):
                print(f"{event['msg']}: {event.get('data')}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 tools/decode_amg_log.py logs/bridge_*.ndjson")
        sys.exit(1)
    process_log(sys.argv[1])
