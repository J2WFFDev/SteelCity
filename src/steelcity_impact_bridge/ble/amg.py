
from __future__ import annotations
import asyncio, re, time
from typing import Optional, Callable, Any, Dict
import os
from bleak import BleakScanner, BleakClient
from .util import scan_lock, bluez_scan_off
from .amg_signals import classify_signals


def _is_start_frame(b: bytes) -> bool:
    # Per field findings and external reference, a start/beep event is signaled
    # by leading bytes 0x01 0x05. Keep our previous 14-byte heuristic as a fallback
    # (older firmware variants observed), but prefer the explicit subtype check.
    if not b:
        return False
    if b[0] == 0x01:
        # Explicit start subtype (more robust and matches Android reference impl)
        if len(b) >= 2 and b[1] == 0x05:
            return True
        # Legacy 14-byte frame with zeroed mid segment (observed in the wild)
        if len(b) == 14 and b[5:13] == b"\x00" * 8:
            return True
    return False


class AmgClient:
    def __init__(self, adapter: str, mac_or_name: Optional[str], start_uuid: str, write_uuid: Optional[str] = None, commands: Optional[Dict[str, Any]] = None):
        self.adapter = adapter
        self.target = mac_or_name
        self.start_uuid = start_uuid
        # Nordic UART write characteristic (default)
        self.write_uuid = write_uuid or "6e400002-b5a3-f393-e0a9-e50e24dcca9e"
        self.commands = commands or {}
        self.client: Optional[BleakClient] = None
        self._on_t0: Optional[Callable[[int, bytes], None]] = None
        self._on_raw: Optional[Callable[[int, bytes], None]] = None
        self._on_signal: Optional[Callable[[int, str, bytes], None]] = None
        # Optional debug logging of all raw notifications (env toggle)
        self.debug_raw = os.getenv("AMG_DEBUG_RAW", "0") not in (None, "", "0", "false", "False")
        # Disconnect event to support reconnect loops upstream
        self._disconnected_evt: Optional[asyncio.Event] = None

    def on_t0(self, fn: Callable[[int, bytes], None]):
        self._on_t0 = fn

    def on_raw(self, fn: Callable[[int, bytes], None]):
        self._on_raw = fn

    def on_signal(self, fn: Callable[[int, str, bytes], None]):
        """Structured signal callback: (ts_ns, name, raw_bytes)."""
        self._on_signal = fn

    async def start(self):
        # Ensure adapter isn't in active scan state (BlueZ InProgress otherwise)
        try:
            await bluez_scan_off()
        except Exception:
            pass

        # Try fast-path by MAC address if provided
        target = (self.target or "").strip()
        found = None

        is_mac = bool(re.fullmatch(r"[0-9a-fA-F]{2}(:[0-9a-fA-F]{2}){5}", target))
        if is_mac:
            # Attempt direct connection without pre-scan (BlueZ supports this)
            # Bleak 1.x: use adapter= for Linux/BlueZ
            direct_client = BleakClient(target, adapter=self.adapter)
            try:
                # Retry a few times on transient InProgress
                last_err = None
                for _ in range(3):
                    try:
                        await direct_client.connect(timeout=20.0)
                        last_err = None
                        break
                    except Exception as e:
                        if "InProgress" in str(e):
                            await asyncio.sleep(1.0)
                            continue
                        last_err = e
                        break
                if last_err:
                    raise last_err
                self.client = direct_client
                self._disconnected_evt = asyncio.Event()
                try:
                    self.client.set_disconnected_callback(lambda _c: self._disconnected_evt and self._disconnected_evt.set())  # type: ignore[attr-defined]
                except Exception:
                    pass
                # Set up notify and return
                def cb_direct(_, data: bytearray):
                    if self._on_t0:
                        b = bytes(data)
                        if self.debug_raw and self._on_raw:
                            try:
                                self._on_raw(time.monotonic_ns(), b)
                            except Exception:
                                pass
                        # Structured signals
                        ts = time.monotonic_ns()
                        sigs = classify_signals(b)
                        for s in sigs:
                            if s == "T0":
                                self._on_t0(ts, b)
                            if self._on_signal:
                                try:
                                    self._on_signal(ts, s, b)
                                except Exception:
                                    pass
                await self.client.start_notify(self.start_uuid, cb_direct)
                return
            except Exception:
                # If direct connect fails, fall back to discovery paths
                try:
                    await direct_client.disconnect()
                except Exception:
                    pass

            # As a secondary MAC path, try to resolve device by address (some stacks require it)
            # Some bleak versions support cb={"use_bdaddr": False} on Linux
            try:
                async with scan_lock:
                    found = await BleakScanner.find_device_by_address(target, cb=dict(use_bdaddr=False), timeout=10.0)  # type: ignore[arg-type]
            except TypeError:
                # Older/newer bleak may not support cb kwarg; retry without it
                async with scan_lock:
                    found = await BleakScanner.find_device_by_address(target, timeout=10.0)

        # Fallback to passive discovery list
        if not found:
            try:
                async with scan_lock:
                    discovered = await BleakScanner.discover(adapter=self.adapter, timeout=12.0)
            except TypeError:
                # In case the adapter kwarg differs across bleak versions
                try:
                    async with scan_lock:
                        discovered = await BleakScanner.discover(device=self.adapter, timeout=12.0)  # type: ignore[call-arg]
                except TypeError:
                    async with scan_lock:
                        discovered = await BleakScanner.discover(timeout=12.0)
            t_lc = target.lower()
            for d in discovered:
                name = (d.name or "").lower()
                addr = (d.address or "").lower()
                if not target:
                    if ("amg" in name) or ("commander" in name):
                        found = d
                        break
                else:
                    if t_lc == addr or t_lc in name:
                        found = d
                        break

        # Last resort: live scan with detection callback for ~15s
        if not found:
            def _match(dev) -> bool:
                name = (dev.name or "").lower()
                addr = (getattr(dev, "address", None) or "").lower()
                if not target:
                    return ("amg" in name) or ("commander" in name)
                t_lc2 = target.lower()
                return (t_lc2 == addr) or (t_lc2 in name)

            def _on_detect(dev, adv):
                nonlocal found
                if found is None and _match(dev):
                    found = dev

            # Ensure any existing scan is off before starting a new scanner
            await bluez_scan_off()
            async with scan_lock:
                async with BleakScanner(detection_callback=_on_detect, adapter=self.adapter):
                    for _ in range(30):  # 30 * 0.5s = 15s
                        if found:
                            break
                        await asyncio.sleep(0.5)

        if not found:
            raise RuntimeError("AMG Commander not found")

    # Connect using adapter kwarg (Bleak 1.x)
        self.client = BleakClient(found, adapter=self.adapter)
        # Retry on transient InProgress
        last_err = None
        for _ in range(3):
            try:
                await self.client.connect(timeout=20.0)
                last_err = None
                break
            except Exception as e:
                if "InProgress" in str(e):
                    await asyncio.sleep(1.0)
                    continue
                last_err = e
                break
        if last_err:
            raise last_err

        def cb(_, data: bytearray):
            b = bytes(data)
            ts = time.monotonic_ns()
            if self.debug_raw and self._on_raw:
                try:
                    self._on_raw(ts, b)
                except Exception:
                    pass
            sigs = classify_signals(b)
            for s in sigs:
                if s == "T0" and self._on_t0:
                    self._on_t0(ts, b)
                if self._on_signal:
                    try:
                        self._on_signal(ts, s, b)
                    except Exception:
                        pass

        await self.client.start_notify(self.start_uuid, cb)
        self._disconnected_evt = asyncio.Event()
        try:
            self.client.set_disconnected_callback(lambda _c: self._disconnected_evt and self._disconnected_evt.set())  # type: ignore[attr-defined]
        except Exception:
            pass

    async def stop(self):
        if self.client:
            try:
                await self.client.disconnect()
            finally:
                self.client = None
                self._disconnected_evt = None

    async def write_cmd(self, data: bytes, *, response: bool = True):
        """Write raw bytes to the AMG write characteristic (Nordic UART TX).

        Contract:
        - Requires an active connection (self.client is not None and is connected).
        - Uses `self.write_uuid` (defaults to NUS write char).
        - `response=True` requests a response where supported.
        """
        if not self.client:
            raise RuntimeError("AMG client not connected")
        await self.client.write_gatt_char(self.write_uuid, data, response=response)

    async def wait_disconnect(self):
        if not self._disconnected_evt:
            return
        try:
            await self._disconnected_evt.wait()
        except Exception:
            pass

    # ---------- Convenience commands (optional) ----------
    def _render_hex_template(self, tpl: str, **kwargs) -> bytes:
        """Render a simple hex template like "AA-{level:02X}-55" into bytes."""
        # Replace {name:fmt} occurrences using kwargs
        import re
        def repl(m):
            key = m.group(1)
            fmt = m.group(2) or "X"
            val = kwargs.get(key)
            if val is None:
                raise KeyError(f"Missing template key: {key}")
            return format(int(val), fmt)
        # Compute string with values embedded (without separators normalization yet)
        s = re.sub(r"\{(\w+)(?::([^}]+))?\}", repl, tpl)
        # Normalize separators and parse hex bytes
        s = s.replace(" ", "").replace("-", ":").replace(",", ":")
        parts = [p for p in s.split(":") if p]
        return bytes(int(p, 16) for p in parts)

    async def beep(self):
        spec = self.commands.get("beep") if isinstance(self.commands, dict) else None
        if not spec:
            raise RuntimeError("No 'beep' command configured")
        if "hex" in spec:
            data = self._render_hex_template(spec["hex"])  # treat as static hex
        elif "text" in spec:
            data = str(spec["text"]).encode("utf-8")
        else:
            raise RuntimeError("Unsupported 'beep' spec; expected hex or text")
        await self.write_cmd(data)

    async def set_sensitivity(self, level: int):
        spec = self.commands.get("set_sensitivity") if isinstance(self.commands, dict) else None
        if not spec:
            raise RuntimeError("No 'set_sensitivity' command configured")
        if "hex_template" in spec:
            data = self._render_hex_template(spec["hex_template"], level=level)
        elif "text_template" in spec:
            txt = str(spec["text_template"]).format(level=level)
            data = txt.encode("utf-8")
        else:
            raise RuntimeError("Unsupported 'set_sensitivity' spec; expected hex_template or text_template")
        await self.write_cmd(data)
