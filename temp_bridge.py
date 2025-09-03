
from __future__ import annotations
import asyncio, time
from typing import List, Optional
from .config import AppCfg, load_config, DetectorCfg
from .logs import NdjsonLogger
from .detector import HitDetector, DetectorParams
from .ble.amg import AmgClient
from .ble.witmotion_bt50 import Bt50Client
from .ble.wtvb_parse import parse_5561

class Bridge:
    def __init__(self, cfg: AppCfg):
        self.cfg = cfg
        self.logger = NdjsonLogger(cfg.logging.dir, cfg.logging.file_prefix)
        # Apply logging mode and whitelist from config if present
        try:
            if hasattr(cfg.logging, 'mode'):
                self.logger.mode = cfg.logging.mode or self.logger.mode
            if hasattr(cfg.logging, 'verbose_whitelist') and cfg.logging.verbose_whitelist:
                self.logger.verbose_whitelist.update(cfg.logging.verbose_whitelist)
        except Exception:
            pass
        self.t0_ns: Optional[int] = None
        self._last_amg_ns: Optional[int] = None
        self._pending_session: bool = False
        self.amg: Optional[AmgClient] = None
        self.bt_clients: List[Bt50Client] = []
        self.detectors = {}
        self._stream_stats = {}
        self._stop = False
        self._bt_tasks: List[asyncio.Task] = []

    async def start(self):
        # Start AMG listener with reconnect/backoff loop
        async def _amg_loop():
            backoff = max(0.0, float(self.cfg.amg.reconnect_initial_sec))
            max_b = max(backoff, float(self.cfg.amg.reconnect_max_sec))
            jitter = max(0.0, float(self.cfg.amg.reconnect_jitter_sec))
            while not self._stop:
                self.amg = AmgClient(
                    self.cfg.amg.adapter,
                    self.cfg.amg.mac or self.cfg.amg.name,
                    self.cfg.amg.start_uuid,
                    self.cfg.amg.write_uuid,
                    self.cfg.amg.commands,
                )
                self.amg.on_t0(self._on_t0)
                # Optional raw dump for debugging
                self.amg.on_raw(lambda ts, raw: self._on_amg_raw(ts, raw))
                # Structured signals
                self.amg.on_signal(lambda ts, name, raw: self._on_amg_signal(ts, name, raw))
                try:
                    # Log intent to connect
                    self.logger.write({
                        "type": "info",
                        "msg": "Timer_connecting",
                        "data": {
                            "adapter": self.cfg.amg.adapter,
                            "target": self.cfg.amg.mac or self.cfg.amg.name,
                            "start_uuid": self.cfg.amg.start_uuid,
                        },
                    })
                    await self.amg.start()
                    # Log AMG connection info (subscription started)
                    self.logger.write({
                        "type": "info",
                        "msg": "Timer_connected",
                        "data": {
                            "adapter": self.cfg.amg.adapter,
                            "mac": self.cfg.amg.mac,
                            "device_category": "Smart Timer",
                            "device_id": self.cfg.amg.mac[-5:].replace(":", ""),
                            "start_uuid": self.cfg.amg.start_uuid,
                            "subscribed": True,
                        },
                    })
                    # Optional initial commands
                    try:
                        cmds = (self.cfg.amg.init_cmds or [])
                        for cmd in cmds:
                            if not isinstance(cmd, dict):
                                continue
                            delay_ms = int(cmd.get("delay_ms", 0)) if hasattr(cmd, "get") else 0
                            if delay_ms > 0:
                                await asyncio.sleep(delay_ms/1000.0)
                            payload: Optional[bytes] = None
                            if hasattr(cmd, "get") and cmd.get("text") is not None:
                                payload = str(cmd.get("text")).encode("utf-8")
                            elif hasattr(cmd, "get") and cmd.get("hex") is not None:
                                hx = str(cmd.get("hex")).replace(" ", "").replace("-", ":").replace(",", ":")
                                parts = [p for p in hx.split(":") if p]
                                try:
                                    payload = bytes(int(p, 16) for p in parts)
                                except Exception:
                                    payload = None
                            if payload:
                                try:
                                    await self.amg.write_cmd(payload, response=True)
                                    self.logger.write({"type":"debug","msg":"amg_write_init","data":{"len": len(payload), "hex": payload.hex()}})
                                except Exception as e:
                                    self.logger.write({"type":"error","msg":"amg_write_failed","data":{"error": str(e)}})
                    except Exception as e:
                        self.logger.write({"type":"error","msg":"amg_init_cmds_error","data":{"error": str(e)}})

                    # Wait indefinitely until AMG disconnects
                    try:
                        await self.amg.wait_disconnect()  # type: ignore[attr-defined]
                    except Exception:
                        pass
                    # Log disconnect state (normal or error path will also come here)
                    self.logger.write({
                        "type": "info",
                        "msg": "Timer_disconnected",
                        "data": {"adapter": self.cfg.amg.adapter, "target": self.cfg.amg.mac or self.cfg.amg.name},
                    })
                except Exception as e:
                    # Proceed even if AMG is not available; BT50 can still stream
                    self.logger.write({
                        "type": "error",
                        "msg": "Timer_connect_failed",
                        "data": {"adapter": self.cfg.amg.adapter, "mac": self.cfg.amg.mac, "error": str(e)}
                    })
                finally:
                    try:
                        if self.amg:
                            await self.amg.stop()
                    except Exception:
                        pass
                # Backoff before retry
                if self._stop:
                    break
                # simple exponential backoff with cap and small jitter
                await asyncio.sleep(min(max_b, backoff) + (jitter if jitter > 0 else 0))
                backoff = min(max_b, max(1.0, backoff * 1.7))

        asyncio.create_task(_amg_loop())

        # Start BT50 sensor loops (with reconnect)
        for s in self.cfg.sensors:
            task = asyncio.create_task(self._bt50_loop(s.plate, s.adapter, s.mac, s.notify_uuid, s.config_uuid))
            self._bt_tasks.append(task)

        # Periodic status
        asyncio.create_task(self._status_task())

    async def _status_task(self):
        while True:
            self.logger.write({
                "type":"status",
                "t_rel_ms": None if self.t0_ns is None else (time.monotonic_ns()-self.t0_ns)/1e6,
                "msg":"alive",
                "data":{"sensors": list(self.detectors.keys())}
            })
            await asyncio.sleep(5)

    async def _bt50_loop(self, sensor_id: str, adapter: str, mac: str, notify_uuid: str, config_uuid: Optional[str]):
        """Maintain a BT50 connection with reconnects."""
        # Pull per-sensor config for backoff and keepalive/idle
        scfg = None
        for s in self.cfg.sensors:
            if s.plate == sensor_id and s.mac == mac:
                scfg = s
                break
        reconnect_initial = float(getattr(scfg, "reconnect_initial_sec", 2.0) if scfg else 2.0)
        reconnect_max = float(getattr(scfg, "reconnect_max_sec", 20.0) if scfg else 20.0)
        reconnect_jitter = float(getattr(scfg, "reconnect_jitter_sec", 1.0) if scfg else 1.0)
        backoff = max(0.0, reconnect_initial)
        while not self._stop:
            cli = Bt50Client(adapter, mac, notify_uuid, config_uuid)
            # apply tunables
            if scfg:
                cli.idle_reconnect_sec = float(getattr(scfg, "idle_reconnect_sec", cli.idle_reconnect_sec))
                cli.keepalive_batt_sec = float(getattr(scfg, "keepalive_batt_sec", cli.keepalive_batt_sec))
            cli.on_packet(lambda ts, data, p=sensor_id: self._on_bt50_packet(p, ts, data))
            # Log intent to connect
            self.logger.write({"type": "info", "msg": "Sensor_connecting", "data": {"sensor_id": sensor_id, "adapter": adapter, "mac": mac}})
            try:
                await cli.start()
            except Exception as e:
                self.logger.write({"type": "error", "msg": "Sensor_connect_failed", "data": {"sensor_id": sensor_id, "adapter": adapter, "mac": mac, "error": str(e)}})
                # backoff then retry
                await asyncio.sleep(min(reconnect_max, backoff) + reconnect_jitter)
                backoff = min(reconnect_max, max(1.0, backoff * 1.7))
                continue

            if cli not in self.bt_clients:
                self.bt_clients.append(cli)
            if sensor_id not in self.detectors:
                self.detectors[sensor_id] = HitDetector(DetectorParams(**self.cfg.detector.__dict__))
            # Log connection details
            self.logger.write({"type": "info", "msg": "Sensor_connected", "data": {"sensor_id": sensor_id, "adapter": adapter, "mac": mac, "notify_uuid": notify_uuid}})
            # reset backoff on success
            backoff = reconnect_initial
            # Snapshot battery and services (best-effort)
            try:
                batt = await cli.read_battery_level()
            except Exception:
                batt = None
            self.logger.write({"type": "info", "msg": "Sensor_battery", "data": {"sensor_id": sensor_id, "battery_pct": batt}})
            try:
                svcs = await cli.list_services()
            except Exception:
                svcs = []
            if svcs:
                self.logger.write({"type": "info", "msg": "Sensor_services", "data": {"sensor_id": sensor_id, "services": svcs[:12]}})

            # Wait for disconnect
            try:
                await cli.wait_disconnect()
            except Exception:
                pass
            self.logger.write({"type": "info", "msg": "Sensor_disconnected", "data": {"sensor_id": sensor_id}})
            try:
                await cli.stop()
            except Exception:
                pass
            await asyncio.sleep(min(reconnect_max, backoff) + reconnect_jitter)
            backoff = min(reconnect_max, max(1.0, backoff * 1.7))

    def _on_t0(self, t0_ns: int, raw: bytes):
        # If we haven't already marked a session start, infer a start button at T0
        if not self._pending_session:
            self._pending_session = True
            self.logger.write({
                "type": "event",
                "msg": "Timer_START_BTN",
                "data": {"raw": raw.hex(), "method": "inferred_at_t0"}
            })
        self.t0_ns = t0_ns
        self.logger.write({"type":"event","t_rel_ms":0.0,"msg":"T0","data":{"raw": raw.hex()}})

    def _on_amg_raw(self, ts_ns: int, raw: bytes):
        if getattr(self.amg, "debug_raw", False):
            self.logger.write({"type":"debug","msg":"Shot_raw","data":{"raw": raw.hex()}})
        # Track last AMG activity to help infer start button prior to T0
        self._last_amg_ns = ts_ns

    def _on_amg_signal(self, ts_ns: int, name: str, raw: bytes):
        # Generic structured AMG signal event; specific T0 handling remains in _on_t0 for t0_ns state.
        if name == "T0":
            self.logger.write({"type":"event","msg":f"Timer_T0","data":{"raw": raw.hex()}})
        elif name == "ARROW_END":
            self.logger.write({"type":"event","msg":f"String_END","data":{"raw": raw.hex()}})
        elif name == "TIMEOUT_END":
            self.logger.write({"type":"event","msg":f"String_TIMEOUT_END","data":{"raw": raw.hex()}})
        else:
            self.logger.write({"type":"event","msg":f"Timer_{name}","data":{"raw": raw.hex()}})
        # If explicit end signals appear, close the session
        if name in ("ARROW_END", "TIMEOUT_END"):
            reason = "arrow" if name == "ARROW_END" else "timeout"
            self.logger.write({"type":"event","msg":"Timer_SESSION_END","data":{"reason": reason}})
            # Clear t0; optionally we could rotate session_id if desired in the logger
            self.t0_ns = None
            # Reset pending-session marker so next T0 can infer a new start
            self._pending_session = False

    def _on_bt50_packet(self, sensor_id: str, ts_ns: int, payload: bytes):
        # Prefer structured parse per WTVB01-BT50 manual (HDR 0x55, FLAG 0x61)
        # Fallback to byte-energy heuristic if parse fails.
        if not payload:
            return
        pkt = parse_5561(payload)
        if pkt is not None:
            # Use velocity magnitude (mm/s) as amplitude proxy
            vx, vy, vz = pkt['VX'], pkt['VY'], pkt['VZ']
            amp = (vx*vx + vy*vy + vz*vz) ** 0.5
        else:
            s = sum(b*b for b in payload) / len(payload)
            amp = float(s**0.5)  # pseudo-RMS of payload bytes

        det = self.detectors[sensor_id]
        hit = det.update(amp, dt_ms=10.0)  # BT50 at 100 Hz
        if hit and self.t0_ns is not None:
            t_rel_ms = (ts_ns - self.t0_ns)/1e6
            self.logger.write({"type":"event","sensor_id":sensor_id,"t_rel_ms":t_rel_ms,"msg":"Sensor_HIT","data":hit})

        # Periodic telemetry to confirm streaming and help calibrate
        st = self._stream_stats.get(plate)
        if st is None:
            st = {"n": 0, "sum": 0.0, "last_ns": ts_ns}
            self._stream_stats[plate] = st
        st["n"] += 1
        st["sum"] += amp
        if st["n"] >= 200 or (ts_ns - st["last_ns"]) > 2_000_000_000:
            avg = st["sum"] / max(1, st["n"])
            data = {"plate": plate, "samples": st["n"], "avg_amp": round(avg, 3)}
            # Include a snapshot of parsed fields occasionally if parse succeeded recently
            if pkt is not None:
                # keep it compact: only a few fields
                data.update({"avg_vx": pkt['VX'], "avg_vy": pkt['VY'], "avg_vz": pkt['VZ'], "temp_c": pkt['TEMP']})
            self.logger.write({"type":"info","msg":"bt50_stream","data": data})
            st["n"] = 0
            st["sum"] = 0.0
            st["last_ns"] = ts_ns

    async def stop(self):
        self._stop = True
        for t in self._bt_tasks:
            t.cancel()
            try:
                await t
            except Exception:
                pass
        for cli in self.bt_clients:
            try:
                await cli.stop()
            except Exception:
                pass
        if self.amg:
            try:
                await self.amg.stop()
            except Exception:
                pass

async def run(config_path: str):
    cfg = load_config(config_path)
    br = Bridge(cfg)
    await br.start()
    try:
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        pass
    finally:
        await br.stop()
