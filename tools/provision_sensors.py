#!/usr/bin/env python3
from __future__ import annotations
import argparse, asyncio, re, sys
from typing import List, Dict, Any, Optional

import yaml
from bleak import BleakScanner

# Simple helpers ---------------------------------------------------------------

def _is_mac(s: str) -> bool:
    return bool(re.fullmatch(r"[0-9A-Fa-f]{2}(:[0-9A-Fa-f]{2}){5}", s.strip()))


def _fmt_dev(d) -> str:
    addr = getattr(d, "address", None) or "?"
    name = getattr(d, "name", None) or "?"
    rssi = getattr(d, "rssi", None)
    return f"{addr:<17}  {name:<24}  RSSI={rssi}" if rssi is not None else f"{addr:<17}  {name:<24}"


async def scan_devices(adapter: Optional[str], timeout: float = 8.0) -> List[Any]:
    try:
        if adapter:
            return await BleakScanner.discover(adapter=adapter, timeout=timeout)
        else:
            return await BleakScanner.discover(timeout=timeout)
    except TypeError:
        # bleak variants
        if adapter:
            return await BleakScanner.discover(device=adapter, timeout=timeout)  # type: ignore[call-arg]
        else:
            return await BleakScanner.discover(timeout=timeout)


# Selection logic --------------------------------------------------------------

def select_by_name(devs: List[Any], name_pattern: str) -> List[Any]:
    rx = re.compile(name_pattern, re.IGNORECASE)
    out = []
    for d in devs:
        name = (getattr(d, "name", None) or "")
        if rx.search(name):
            out.append(d)
    return out


def choose_interactive(devs: List[Any], prompt: str, limit: int) -> List[Any]:
    if not devs:
        return []
    print(prompt)
    for i, d in enumerate(devs, start=1):
        print(f"  [{i}] {_fmt_dev(d)}")
    print(f"Enter up to {limit} numbers separated by space (or press Enter to skip): ", end="", flush=True)
    line = sys.stdin.readline().strip()
    if not line:
        return []
    idxs: List[int] = []
    for tok in re.split(r"[ ,]+", line):
        if tok.isdigit():
            v = int(tok)
            if 1 <= v <= len(devs):
                idxs.append(v)
    # de-dupe and cap
    picks = []
    for i in idxs:
        if len(picks) >= limit:
            break
        d = devs[i - 1]
        if d not in picks:
            picks.append(d)
    return picks


def load_yaml(path: str) -> Dict[str, Any]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        return {}


def dump_yaml(path: str, data: Dict[str, Any]):
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False)


# Main -------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description="Provision AMG + up to N BT50 sensors into config.yaml")
    ap.add_argument("--config", default="config.yaml", help="Path to config.yaml")
    ap.add_argument("--adapter", default="hci0", help="BlueZ adapter (e.g., hci0)")
    ap.add_argument("--bt50-name", default="WIT|BT50|WTVB|WT|IMU", help="Regex to match BT50 names")
    ap.add_argument("--amg-name", default="AMG|Commander", help="Regex to match AMG names")
    ap.add_argument("--limit", type=int, default=5, help="Max BT50 sensors to select")
    ap.add_argument("--auto", action="store_true", help="Auto-pick top-N strongest BT50 and first AMG (no prompts)")
    ap.add_argument("--replace", action="store_true", help="Replace sensors list instead of merging")
    ap.add_argument("--dry-run", action="store_true", help="Do not write config; just show proposed changes")
    args = ap.parse_args()

    cfg = load_yaml(args.config)
    sensors_existing = cfg.get("sensors", []) if isinstance(cfg.get("sensors"), list) else []

    print(f"Scanning adapter {args.adapter} for ~8s...")
    devs = asyncio.run(scan_devices(args.adapter, timeout=8.0))
    if not devs:
        print("No BLE devices discovered. Ensure devices are advertising and near the Pi.")
        sys.exit(2)
    print(f"Discovered {len(devs)} devices:")
    for d in devs:
        print("  ", _fmt_dev(d))

    # Select AMG (single)
    amg_cand = select_by_name(devs, args.amg_name)
    amg_pick = None
    if args.auto:
        amg_pick = amg_cand[0] if amg_cand else None
    else:
        amg_sel = choose_interactive(amg_cand, "Select AMG (choose one index):", limit=1)
        amg_pick = amg_sel[0] if amg_sel else None

    # Select up to N BT50
    bt50_cand = select_by_name(devs, args.bt50_name)
    # Sort by RSSI desc if available
    bt50_cand.sort(key=lambda d: (getattr(d, "rssi", -9999) or -9999), reverse=True)
    if args.auto:
        bt50_pick = bt50_cand[: max(0, args.limit)]
    else:
        bt50_pick = choose_interactive(bt50_cand, f"Select up to {args.limit} BT50 sensors:", limit=args.limit)

    # Build new sensors list entries (preserve notify_uuid/config_uuid from first existing entry if available)
    def _default_notify() -> str:
        if sensors_existing:
            return str(sensors_existing[0].get("notify_uuid", ""))
        return ""

    def _default_config_char() -> Optional[str]:
        if sensors_existing:
            return sensors_existing[0].get("config_uuid")
        return None

    new_sensors: List[Dict[str, Any]] = []
    for i, d in enumerate(bt50_pick, start=1):
        mac = getattr(d, "address", None) or ""
        name = getattr(d, "name", None) or f"P{i}"
        plate = f"P{i}"
        ent = {
            "plate": plate,
            "adapter": args.adapter,
            "mac": mac,
            "notify_uuid": _default_notify(),
            "config_uuid": _default_config_char(),
            # Provide sane reconnect defaults; user can edit later
            "idle_reconnect_sec": 15.0,
            "keepalive_batt_sec": 60.0,
            "reconnect_initial_sec": 2.0,
            "reconnect_max_sec": 20.0,
            "reconnect_jitter_sec": 1.0,
        }
        new_sensors.append(ent)

    # Update AMG portion
    if amg_pick is not None:
        amg_addr = getattr(amg_pick, "address", None)
        # Maintain existing write_uuid/start_uuid if present
        amg = cfg.get("amg", {}) if isinstance(cfg.get("amg"), dict) else {}
        amg.update({
            "adapter": args.adapter,
            "mac": amg_addr,
        })
        cfg["amg"] = amg

    # Update sensors
    if args.replace:
        cfg["sensors"] = new_sensors
    else:
        # merge (avoid duplicates by MAC)
        seen = {str(s.get("mac")).lower() for s in sensors_existing if isinstance(s, dict)}
        merged = list(sensors_existing)
        for s in new_sensors:
            if str(s.get("mac", "")).lower() not in seen:
                merged.append(s)
        cfg["sensors"] = merged

    print("\nProposed config changes:")
    print(yaml.safe_dump(cfg, sort_keys=False))

    if args.dry_run:
        print("(dry-run) Not writing file.")
        return

    dump_yaml(args.config, cfg)
    print(f"Wrote {args.config}. You can adjust notify/config UUIDs if needed.")


if __name__ == "__main__":
    main()
