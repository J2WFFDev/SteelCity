#!/usr/bin/env python3
import argparse, asyncio, os, subprocess, sys, time, shlex
from bleak import BleakScanner

def main():
    ap = argparse.ArgumentParser(description="Wait for WTVB01-BT50 then run live decode")
    ap.add_argument("--mac", required=True)
    ap.add_argument("--adapter", default="hci0")
    ap.add_argument("--secs", type=float, default=120)
    ap.add_argument("--timeout", type=float, default=180, help="max seconds to wait for device")
    ap.add_argument("--out", default="logs/wit_live.out", help="stdout file for decoder")
    args = ap.parse_args()

    mac = args.mac
    adapter = args.adapter
    deadline = time.time() + args.timeout

    async def wait_for_dev():
        # Try MAC resolution quickly; if not present, discovery loop
        while time.time() < deadline:
            try:
                dev = await BleakScanner.find_device_by_address(mac, cb=dict(use_bdaddr=False), timeout=6.0)  # type: ignore[arg-type]
            except TypeError:
                dev = await BleakScanner.find_device_by_address(mac, timeout=6.0)
            if dev:
                return True
            # Discovery fallback
            try:
                found = any((d.address or "").lower() == mac.lower()
                            for d in (await BleakScanner.discover(adapter=adapter, timeout=6.0)))
            except TypeError:
                try:
                    found = any((d.address or "").lower() == mac.lower()
                                for d in (await BleakScanner.discover(device=adapter, timeout=6.0)))  # type: ignore[call-arg]
                except TypeError:
                    found = any((d.address or "").lower() == mac.lower()
                                for d in (await BleakScanner.discover(timeout=6.0)))
            if found:
                return True
            time.sleep(2)
        return False

    print(f"[wait] looking for {mac} up to {int(args.timeout)}s on {adapter}…", flush=True)
    ok = asyncio.run(wait_for_dev())
    if not ok:
        print("[timeout] device not found", file=sys.stderr, flush=True)
        sys.exit(1)

    print("[start] launching wtvb_live_decode.py", flush=True)
    os.makedirs(os.path.dirname(args.out or "logs"), exist_ok=True)
    # Use the same interpreter we were launched with (expected to be the venv python)
    py = shlex.quote(sys.executable)
    cmd = (
        f"cd ~/projects/steelcity && nohup {py} tools/wtvb_live_decode.py "
        f"--mac {mac} --adapter {adapter} --secs {int(args.secs)} > {args.out} 2>&1 & echo $! > logs/wit_live.pid && cat logs/wit_live.pid"
    )
    subprocess.Popen(["bash", "-lc", cmd])

if __name__ == "__main__":
    main()
