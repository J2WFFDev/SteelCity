
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

@dataclass
class LoggingCfg:
    dir: str = "./logs"
    file_prefix: str = "bridge"

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
    sensors = [SensorCfg(**s) for s in raw.get("sensors", [])]
    det = DetectorCfg(**raw.get("detector", {}))
    log = LoggingCfg(**raw.get("logging", {}))
    return AppCfg(amg=amg, sensors=sensors, detector=det, logging=log)
