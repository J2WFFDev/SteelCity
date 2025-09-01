#!/usr/bin/env python3
"""
AMG control helper: connect to AMG and send a named or ad-hoc command.

Usage examples:
  # Ad-hoc payloads
  python tools/amg_control.py --adapter hci0 --mac 60:09:C3:1F:DC:1A --text "BEEP\n"
  python tools/amg_control.py --adapter hci0 --name AMG --hex AA-55-01

  # From config.yaml command mappings
  python tools/amg_control.py --config config.yaml --beep
  python tools/amg_control.py --config config.yaml --set-sensitivity 3

Notes:
- This tool writes to the Nordic UART write characteristic (default 6e400002-...)
- It does not subscribe to notifications; use the bridge or sniff tools for reads.
"""
import argparse, asyncio, os, sys
from typing import Optional, Dict, Any

try:
    import yaml  # type: ignore
except Exception:
    yaml = None

from bleak import BleakScanner, BleakClient

NUS_WRITE = "6e400002-b5a3-f393-e0a9-e50e24dcca9e"


def parse_hex_to_bytes(s: str) -> bytes:
    s = s.strip().replace(" ", "").replace("-", ":").replace(",", ":")
    parts = [p for p in s.split(":") if p]
    return bytes(int(p, 16) for p in parts)


def render_hex_template(tpl: str, **kwargs) -> bytes:
    import re
    def repl(m):
        key = m.group(1)
        fmt = m.group(2) or "X"
        val = kwargs.get(key)
        if val is None:
            raise KeyError(f"Missing template key: {key}")
        return format(int(val), fmt)
    s = re.sub(r"\{(\w+)(?::([^}]+))?\}", repl, tpl)
    return parse_hex_to_bytes(s)


async def find_device(adapter: str, mac: Optional[str], name: Optional[str]):
    """
    Return either a MAC string (preferred fast path) or a discovered device.

    We avoid scanning when a MAC is provided to minimize BlueZ 'InProgress' errors.
    """
    if mac:
        return mac
    for d in await BleakScanner.discover(adapter=adapter, timeout=8.0):
        if name and name.lower() in (d.name or "").lower():
            return d
    raise SystemExit("No device matched by name. Try --mac or widen --name.")


def load_commands_from_config(path: str) -> Dict[str, Any]:
    if yaml is None:
        raise SystemExit("PyYAML not installed. pip install pyyaml")
    with open(path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    amg = (cfg or {}).get("amg", {}) or {}
    return amg.get("commands", {}) or {}


async def main():
    ap = argparse.ArgumentParser()
    src = ap.add_mutually_exclusive_group()
    src.add_argument("--mac")
    src.add_argument("--name", default="AMG")
    ap.add_argument("--adapter", default="hci0")
    ap.add_argument("--write-uuid", default=NUS_WRITE)
    ap.add_argument("--config", help="Path to config.yaml with amg.commands mapping")
    # Named actions
    ap.add_argument("--beep", action="store_true")
    ap.add_argument("--set-sensitivity", type=int)
    ap.add_argument("--command", help="Send an arbitrary named command from config.yaml (expects hex or text mapping)")
    # Ad-hoc data
    ad = ap.add_mutually_exclusive_group()
    ad.add_argument("--text")
    ad.add_argument("--hex")
    args = ap.parse_args()

    # Build payload
    payload = None
    if args.text is not None:
        payload = args.text.encode("utf-8")
    elif args.hex is not None:
        payload = parse_hex_to_bytes(args.hex)
    else:
        cmds: Dict[str, Any] = {}
        if args.config:
            cmds = load_commands_from_config(args.config)
        if args.beep:
            spec = cmds.get("beep") or {}
            if "hex" in spec:
                payload = parse_hex_to_bytes(spec["hex"])
            elif "text" in spec:
                payload = str(spec["text"]).encode("utf-8")
            else:
                raise SystemExit("No 'beep' mapping found in config (expected hex or text)")
        elif args.set_sensitivity is not None:
            spec = cmds.get("set_sensitivity") or {}
            if "hex_template" in spec:
                payload = render_hex_template(spec["hex_template"], level=args.set_sensitivity)
            elif "text_template" in spec:
                txt = str(spec["text_template"]).format(level=args.set_sensitivity)
                payload = txt.encode("utf-8")
            else:
                raise SystemExit("No 'set_sensitivity' mapping found (expected hex_template or text_template)")
        elif args.command:
            spec = cmds.get(args.command)
            if not spec:
                raise SystemExit(f"No mapping named '{args.command}' in config")
            if "hex" in spec:
                payload = parse_hex_to_bytes(spec["hex"])
            elif "text" in spec:
                payload = str(spec["text"]).encode("utf-8")
            else:
                raise SystemExit(f"Unsupported mapping for '{args.command}'; expected 'hex' or 'text'")
        else:
            raise SystemExit("Provide --text/--hex or use --config with --beep/--set-sensitivity")

    dev = await find_device(args.adapter, args.mac, args.name)
    # Normalize to MAC string for BleakClient fast-path if available
    dev_mac = dev if isinstance(dev, str) else getattr(dev, "address", None) or args.mac or args.name
    dev_name = getattr(dev, "name", None) if not isinstance(dev, str) else None
    if dev_name:
        print(f"[ble] Connecting to {dev_mac} ({dev_name}) …")
    else:
        print(f"[ble] Connecting to {dev_mac} …")
    async with BleakClient(dev_mac, timeout=20.0, device=args.adapter) as client:
        print(f"[write] {args.write_uuid}  len={len(payload)}  hex={payload.hex()}")
        await client.write_gatt_char(args.write_uuid, payload, response=True)
        print("[ok] write done")


if __name__ == "__main__":
    asyncio.run(main())
