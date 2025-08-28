#!/usr/bin/env python3
# VERSION: amg_live_decode v0.4
import asyncio, argparse, datetime as dt, csv, os
from bleak import BleakScanner, BleakClient

def now_ms(): return dt.datetime.utcnow().isoformat(timespec="milliseconds")+"Z"
def le16(b): return int.from_bytes(b,"little")
def parse(b: bytes):
    if len(b)!=14: return None
    return dict(
        b0=b[0], b1=b[1], b2=b[2], b3=b[3], b4=b[4],
        p1=le16(b[5:7]), p2=le16(b[7:9]), p3=le16(b[9:11]), p4=le16(b[11:13]),
        mid_zero = (b[5:13] == b"\x00"*8),
        secs_le = int.from_bytes(b[1:5], "little"),
        tail=b[13], hex=b.hex()
    )

def is_shot(f):            # shot frames (matches your captures)
    return f["b1"]==0x03 and f["b2"]==f["b3"] and f["p1"]>0

def is_start_frame(f):     # “Standby/Start” we’ve seen: tag 0x01, mids zero, secs 5 or 8
    return f["b0"]==0x01 and f["mid_zero"] and f["secs_le"] in (5,8)

async def main():
    print("[version] amg_live_decode v0.4")
    ap=argparse.ArgumentParser()
    g=ap.add_mutually_exclusive_group(); g.add_argument("--mac"); g.add_argument("--name", default="AMG")
    ap.add_argument("--adapter", default="hci0")
    ap.add_argument("--ctl", default="6e400003-b5a3-f393-e0a9-e50e24dcca9e")
    ap.add_argument("--secs", type=float, default=300)
    ap.add_argument("--csv", default="shot_summary.csv")
    args=ap.parse_args()

    header_needed = not os.path.exists(args.csv) or os.stat(args.csv).st_size==0
    fcsv = open(args.csv, "a", newline="")
    w = csv.writer(fcsv)
    if header_needed:
        w.writerow(["utc_iso","type","tail_hex","shot_idx","T_s","split_s","first_s","reason","hex"]); fcsv.flush()

    if args.mac:
        dev = await BleakScanner.find_device_by_address(args.mac, cb=dict(use_bdaddr=False))
    else:
        dev = None
        for d in await BleakScanner.discover(adapter=args.adapter, timeout=8.0):
            if (args.name or "").lower() in (d.name or "").lower():
                dev = d; break
    if not dev: raise SystemExit("device not found")

    print(f"[ble] connect {dev.address} ({dev.name}) …")
    async with BleakClient(dev, timeout=20.0, device=args.adapter) as client:
        ctl = args.ctl.lower()

        # string bookkeeping
        seen = set()               # (tail, shot_idx) to dedupe retransmits
        current_tail = None
        shots_in_string = 0

        def end_string(reason:str, fobj=None, next_tail=None):
            nonlocal current_tail, shots_in_string
            if current_tail is None and shots_in_string==0:
                return
            tail_hex = f"0x{current_tail:02x}" if current_tail is not None else ""
            print(f"--- string end [{tail_hex}] reason={reason} shots={shots_in_string} next_tail={('0x%02x'%next_tail) if next_tail is not None else '-'}")
            w.writerow([now_ms(),"string_end",tail_hex,"","","","",reason,(fobj['hex'] if fobj else "")]); fcsv.flush()
            current_tail = None
            shots_in_string = 0

        def on_frame(_, data: bytearray):
            nonlocal current_tail, shots_in_string
            fobj = parse(bytes(data))
            if not fobj:
                return

            # If tail changes on any frame (not just shot), close the previous string.
            if current_tail is not None and fobj["tail"] != current_tail:
                end_string("tail_change", fobj=fobj, next_tail=fobj["tail"])

            # Start pressed => close previous string (even without Arrow)
            if is_start_frame(fobj):
                end_string("start_btn", fobj=fobj)
                return

            # Shot frames
            if is_shot(fobj):
                tail = fobj["tail"]
                if current_tail is None:
                    current_tail = tail
                key = (tail, fobj["b2"])
                if key in seen:          # duplicate
                    return
                seen.add(key)

                T, dT, T1 = fobj["p1"]/100.0, fobj["p2"]/100.0, fobj["p3"]/100.0
                tail_hex = f"0x{tail:02x}"
                shots_in_string += 1
                print(f"[tail {tail_hex}] shot {fobj['b2']:2d}:  T={T:.2f}s  split={dT:.2f}s  first={T1:.2f}s  {fobj['hex'][:12]}…")
                w.writerow([now_ms(),"shot",tail_hex,fobj["b2"],f"{T:.3f}",f"{dT:.3f}",f"{T1:.3f}","",fobj["hex"]]); fcsv.flush()

        print(f"[sub] {ctl} (notify)")
        await client.start_notify(ctl, on_frame)
        print("[live] decoding shots… press Start/Beep/Shoot/Arrow on the timer. (Ctrl+C to stop)")
        try:
            await asyncio.sleep(args.secs)
        except (KeyboardInterrupt, asyncio.CancelledError):
            pass
        finally:
            end_string("session_end")
            try:
                await client.stop_notify(ctl)
            except:
                pass
            fcsv.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
