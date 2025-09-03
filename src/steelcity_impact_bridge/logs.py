
from __future__ import annotations
import os, json, time, pathlib, uuid
from typing import Optional, IO

class NdjsonLogger:
    def __init__(self, directory: str, file_prefix: str):
        self.dir = pathlib.Path(directory)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.prefix = file_prefix
        self.seq = 0
        self._fh: Optional[IO[str]] = None
        self._rot_day: Optional[str] = None
        self._path: Optional[pathlib.Path] = None
        # Logging mode: 'regular' or 'verbose'. In regular mode, debug-level
        # events can be filtered unless explicitly whitelisted. This can be
        # configured via environment vars or by passing attributes after
        # construction (bridge passes config through).
        self.mode: str = os.getenv("LOG_MODE", "regular")
        # Whitelist of message names (obj['msg']) that should be emitted even
        # while in regular mode. Comma-separated env var or set directly.
        wl = os.getenv("LOG_VERBOSE_WHITELIST", "")
        self.verbose_whitelist = set([s.strip() for s in wl.split(",") if s.strip()])
        # Threshold under which a reported current_amp is treated as zero.
        # Can be overridden via env var LOG_CURRENT_AMP_THRESHOLD (e.g. 0.001).
        try:
            self.current_amp_threshold = float(os.getenv("LOG_CURRENT_AMP_THRESHOLD", "1e-6"))
        except Exception:
            self.current_amp_threshold = 1e-6
        # Observability: per-run identifiers
        self.session_id: str = os.getenv("SESSION_ID") or uuid.uuid4().hex[:12]
        try:
            self.pid: int = os.getpid()
        except Exception:
            self.pid = -1
        self.rotate()

    def rotate(self):
        # Close previous handle
        if self._fh:
            try:
                self._fh.close()
            except Exception:
                pass
            self._fh = None

        # Create a time-coded filename, e.g., bridge_YYYYMMDD_HHMMSS.ndjson
        now = time.time()
        stamp = time.strftime("%Y%m%d_%H%M%S", time.localtime(now))
        day = stamp[:8]
        path = self.dir / f"{self.prefix}_{stamp}.ndjson"
        self._fh = open(path, "a", buffering=1, encoding="utf-8")
        self._path = path
        self._rot_day = day

        # Maintain a daily alias so existing tools (expecting prefix_YYYYMMDD.ndjson) keep working
        alias = self.dir / f"{self.prefix}_{day}.ndjson"
        try:
            if alias.exists() or alias.is_symlink():
                try:
                    alias.unlink()
                except Exception:
                    pass
            # Prefer hardlink when possible (same filesystem); fallback to symlink
            try:
                os.link(path, alias)
            except Exception:
                try:
                    os.symlink(str(path), alias)  # absolute path for safety
                except Exception:
                    # As a last resort, create/truncate alias to exist (not kept in sync)
                    with open(alias, "a", encoding="utf-8"):
                        pass
        except Exception:
            # Non-fatal if alias creation fails
            pass

    def write(self, obj: dict):
        # Filtering: when in 'regular' mode, drop events that are debug-level
        # (type == 'debug') unless the message is explicitly whitelisted.
        try:
            # In regular mode we apply two kinds of suppression:
            # 1) suppress frequent empty heartbeat status lines: {"type":"status","msg":"alive","data":{"sensors": []}}
            # 2) suppress debug-level lines when they carry a "current_amp" that is effectively zero.
            if self.mode == "regular":
                typ = obj.get("type")
                msg = obj.get("msg")
                data = obj.get("data") if isinstance(obj.get("data"), dict) else {}

                # Suppress empty heartbeats (no sensors) to reduce noise in regular runs
                if typ == "status" and msg == "alive":
                    sensors = data.get("sensors")
                    if isinstance(sensors, list) and len(sensors) == 0:
                        return

                # For debug events apply whitelist *unless* a numeric current_amp is present and is zeroish.
                if typ == "debug":
                    ca = data.get("current_amp")

                    # Explicit suppression for high-rate bt50 buffer status messages in regular mode
                    # These are noisy by nature; allow only when explicitly whitelisted.
                    if msg == "bt50_buffer_status" and not (msg and (msg in self.verbose_whitelist)):
                        return

                    # If current_amp is present and numeric, treat values <= threshold as zero and suppress.
                    if ca is not None:
                        try:
                            if abs(float(ca)) <= float(self.current_amp_threshold):
                                return
                            else:
                                # non-zero meaningful amplitude -> allow regardless of whitelist
                                pass
                        except Exception:
                            # fall through to whitelist logic if conversion fails
                            pass

                    # If we get here, no numeric current_amp was present (or conversion failed): only allow if whitelisted
                    if not (msg and (msg in self.verbose_whitelist)):
                        return
        except Exception:
            # If filtering fails for any reason, fall back to writing the event
            pass
        self.seq += 1
        # Monotonic clock (ms) for stable deltas
        obj.setdefault("ts_ms", time.monotonic() * 1000.0)
        # Human-friendly local time HH:MM:SS.mmm
        now = time.time()
        lt = time.localtime(now)
        msec = int((now % 1.0) * 1000)
        hms = time.strftime("%H:%M:%S", lt) + f".{msec:03d}"
        obj.setdefault("hms", hms)
        # ISO UTC wall clock for cross-host correlation
        isoutc = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(now)) + f".{msec:03d}Z"
        obj.setdefault("t_iso", isoutc)
        # Sequence and identity
        obj.setdefault("seq", self.seq)
        obj.setdefault("schema", "v1")
        obj.setdefault("session_id", self.session_id)
        obj.setdefault("pid", self.pid)
        if time.strftime("%Y%m%d") != self._rot_day:
            self.rotate()
        self._fh.write(json.dumps(obj) + "\n")
