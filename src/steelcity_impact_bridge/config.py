
from __future__ import annotations
import dataclasses, yaml
from dataclasses import dataclass
from typing import Optional, List, Any, Dict

@dataclass
class AmgCfg:
    adapter: str = "hci0"
    mac: Optional[str] = None
    name: Optional[str] = None
    start_uuid: str = ""
    write_uuid: Optional[str] = None
    # Optional list of initial commands to send after connect.
    # Each item: {text: str} or {hex: str} and optional {delay_ms: int}
    init_cmds: Optional[List[Any]] = None
    # Optional named commands/templates, e.g.:
    # commands:
    #   beep: { hex: "A1-B2" }
    #   set_sensitivity: { hex_template: "AA-55-{level:02X}" }
    commands: Optional[Dict[str, Any]] = None
    # Reconnect/backoff tuning (used by the bridge AMG loop)
    reconnect_initial_sec: float = 2.0
    reconnect_max_sec: float = 20.0
    reconnect_jitter_sec: float = 1.0

@dataclass
class SensorCfg:
    plate: str = "P1"
    adapter: str = "hci0"
    mac: str = ""
    notify_uuid: str = ""
    config_uuid: Optional[str] = None
    # BT50 idle/keepalive and reconnect backoff tuning
    idle_reconnect_sec: float = 15.0
    keepalive_batt_sec: float = 60.0
    reconnect_initial_sec: float = 2.0
    reconnect_max_sec: float = 20.0
    reconnect_jitter_sec: float = 1.0

@dataclass
class DetectorCfg:
    triggerHigh: float = 8.0
    triggerLow: float = 2.0
    ring_min_ms: int = 30
    dead_time_ms: int = 100
    # warm-up time before arming detector (lets baseline settle)
    warmup_ms: int = 300
    # minimum baseline power required to consider ratio meaningful
    baseline_min: float = 1e-4
    # absolute minimum amplitude to consider (guards low-noise spikes)
    min_amp: float = 1.0

@dataclass
class LoggingCfg:
    dir: str = "./logs"
    file_prefix: str = "bridge"
    # Logging mode controls verbosity. 'regular' (default) filters debug
    # messages unless whitelisted; 'verbose' emits everything.
    mode: str = "regular"
    # Optional list of message names (strings) that should be emitted even in
    # regular mode. Example: ["Shot_raw","bt50_buffer_status"].
    verbose_whitelist: Optional[List[str]] = None

@dataclass
class AppCfg:
    amg: AmgCfg
    sensors: List[SensorCfg]
    detector: DetectorCfg
    logging: LoggingCfg

def load_config(path: str) -> AppCfg:
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    amg = AmgCfg(**raw.get("amg", {}))
    # Backwards-compat: older config files used the key 'sensor' for the
    # plate name. If present, map it to 'plate' so SensorCfg accepts it.
    sensors_raw = []
    for s in raw.get("sensors", []):
        if isinstance(s, dict) and "sensor" in s and "plate" not in s:
            s = dict(s)
            s["plate"] = s.pop("sensor")
        sensors_raw.append(s)
    sensors = [SensorCfg(**s) for s in sensors_raw]
    det = DetectorCfg(**raw.get("detector", {}))
    log = LoggingCfg(**raw.get("logging", {}))
    return AppCfg(amg=amg, sensors=sensors, detector=det, logging=log)
