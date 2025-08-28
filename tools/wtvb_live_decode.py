#!/usr/bin/env python3
# WTVB01-BT50 live decoder (BLE FFE4 notify)
import asyncio, argparse, datetime as dt, struct
from bleak import BleakScanner, BleakClient

HDR = 0x55
FLAG = 0x61
FRAME_DATA_LEN = 28  # 0x55 + 0x61 + 26 data bytes = 28; BLE often pads to 32

def now(): return dt.datetime.utcnow().isoformat(timespec="milliseconds")+"Z"

def parse_5561(payload: bytes):
    # accepts 28..32 bytes, only decodes the first 28
    if len(payload) < FRAME_DATA_LEN: return None
    b = payload[:FRAME_DATA_LEN]
    if b[0] != HDR or b[1] != FLAG: return None
    # unpack 13 little-endian uint16 after the 2-byte header
    vals = struct.unpack_from('<' + 'H'*13, b, 2)
    (VXL,VYL,VZL, ADXL,ADYL,ADZL, TEMPL,
     DXL,DYL,DZL, HZXL,HZYL,HZZL) = vals

    def s16(u): return struct.unpack('<h', struct.pack('<H', u))[0]  # signed
    VX,VY,VZ = s16(VXL), s16(VYL), s16(VZL)        # mm/s
    ADX,ADY,ADZ = (s16(ADXL)/32768*180,
                   s16(ADYL)/32768*180,
                   s16(ADZL)/32768*180)            # degrees
    TEMP = s16(TEMPL)/100.0                         # °C
    DX,DY,DZ = s16(DXL), s16(DYL), s16(DZL)        # µm
    HZX,HZY,HZZ = s16(HZXL), s16(HZYL), s16(HZZL)  # Hz (per docs)

    return dict(VX=VX, VY=VY, VZ=VZ,
                ADX=ADX, ADY=ADY, ADZ=ADZ,
                TEMP=TEMP, DX=DX, DY=DY, DZ=DZ,
                HZX=HZX, HZY=HZY, HZZ=HZZ)

async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--adapter", default="hci0")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--mac"); g.add_argument("--name")
    ap.add_argument("--ctl", default="0000ffe4-0000-1000-8000-00805f9a34fb")
    ap.add_argument("--secs", type=float, default=60)
    args = ap.parse_args()

    if args.mac:
        dev = await BleakScanner.find_device_by_address(args.mac, cb=dict(use_bdaddr=False))
    else:
        dev = next((d for d in await BleakScanner.discover(adapter=args.adapter, timeout=8.0)
                    if args.name.lower() in (d.name or "").lower()), None)
    if not dev: raise SystemExit("device not found")

    print("[live] connect", dev.address, "(", dev.name, ") …")
    async with BleakClient(dev, timeout=20.0, device=args.adapter) as client:
        print("[sub] ", args.ctl, "(notify)")
        def on(data: bytearray):
            b = bytes(data)
            pkt = parse_5561(b)
            if pkt:
                print(f"{now()} VX={pkt['VX']:>5} VY={pkt['VY']:>5} VZ={pkt['VZ']:>5} mm/s | "
                      f"DX={pkt['DX']:>6} DY={pkt['DY']:>6} DZ={pkt['DZ']:>6} µm | "
                      f"Hz=({pkt['HZX']:>4},{pkt['HZY']:>4},{pkt['HZZ']:>4}) | "
                      f"ADX={pkt['ADX']:5.2f} ADY={pkt['ADY']:5.2f} ADZ={pkt['ADZ']:5.2f}° | "
                      f"T={pkt['TEMP']:4.1f}°C")
            else:
                # show raw header & trailing to help reverse-engineer padding/CRC
                print(f"{now()} [raw] len={len(b)} {b.hex()}")
        await client.start_notify(args.ctl, lambda _, d: on(d))
        print("[live] printing parsed data… (Ctrl+C to stop)")
        try:
            await asyncio.sleep(args.secs)
        except KeyboardInterrupt:
            pass

if __name__ == "__main__":
    asyncio.run(main())
