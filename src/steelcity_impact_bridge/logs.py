
from __future__ import annotations
import os, json, time, pathlib, uuid
from typing import Optional, IO

class NdjsonLogger:
    def __init__(self, directory: str, file_prefix: str, *, dual_file: bool = False, debug_subdir: Optional[str] = None):
        self.dir = pathlib.Path(directory)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.prefix = file_prefix
        # Dual-file config
        self.dual_file = bool(dual_file)
        self.debug_subdir = debug_subdir or "debug"
        self._debug_dir: Optional[pathlib.Path] = None
        self.seq = 0
        self._fh: Optional[IO[str]] = None
        self._rot_day: Optional[str] = None
        self._path: Optional[pathlib.Path] = None
        self._debug_fh: Optional[IO[str]] = None
        self._debug_path: Optional[pathlib.Path] = None
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
        # NOTE: This logger no longer emits machine timestamps (`ts_ms` or
        # `t_iso`). Only the human-friendly `hms` field is written for each
        # record. Configuration flags to include/exclude those fields were
        # removed to keep logs compact and consistent across all record types.
    self.rotate()

    def rotate(self):
        # Close previous handle
        if self._fh:
            try:
                self._fh.close()
            except Exception:
                pass
            self._fh = None
        # Close debug handle if present
        if self._debug_fh:
            try:
                self._debug_fh.close()
            except Exception:
                pass
            self._debug_fh = None

        # Create a time-coded filename, e.g., bridge_YYYYMMDD_HHMMSS.ndjson
        now = time.time()
        stamp = time.strftime("%Y%m%d_%H%M%S", time.localtime(now))
        day = stamp[:8]
        path = self.dir / f"{self.prefix}_{stamp}.ndjson"
        self._fh = open(path, "a", buffering=1, encoding="utf-8")
        self._path = path
        # Prepare debug path/handle when dual_file enabled
        if self.dual_file:
            # Debug directory under base dir
            self._debug_dir = self.dir / self.debug_subdir
            try:
                self._debug_dir.mkdir(parents=True, exist_ok=True)
            except Exception:
                self._debug_dir = self.dir
            dpath = self._debug_dir / f"{self.prefix}_debug_{stamp}.ndjson"
            try:
                self._debug_fh = open(dpath, "a", buffering=1, encoding="utf-8")
                self._debug_path = dpath
            except Exception:
                self._debug_fh = None
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
        # Also create debug alias if dual file
        if self.dual_file and self._debug_path:
            try:
                debug_alias = self._debug_dir / f"{self.prefix}_debug_{day}.ndjson"
                if debug_alias.exists() or debug_alias.is_symlink():
                    try:
                        debug_alias.unlink()
                    except Exception:
                        pass
                try:
                    os.link(self._debug_path, debug_alias)
                except Exception:
                    try:
                        os.symlink(str(self._debug_path), debug_alias)
                    except Exception:
                        with open(debug_alias, "a", encoding="utf-8"):
                            pass
            except Exception:
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
                    # If it's greater than the threshold, allow the event regardless of whitelist.
                    if ca is not None:
                        try:
                            if abs(float(ca)) <= float(self.current_amp_threshold):
                                return
                            else:
                                # non-zero meaningful amplitude -> allow regardless of whitelist
                                # Skip further whitelist checks by proceeding to write.
                                pass
                        except Exception:
                            # fall through to whitelist logic if conversion fails
                            pass

                    # If we get here, either no numeric current_amp was present or conversion failed:
                    # only allow if whitelisted.
                    if ca is None:
                        if not (msg and (msg in self.verbose_whitelist)):
                            return
        except Exception:
            # If filtering fails for any reason, fall back to writing the event
            pass
    # If the event contains a raw hex payload from the AMG/timer, try to
        # decode it into friendly fields so logs are easier to consume.
        try:
            data = obj.get("data") if isinstance(obj.get("data"), dict) else {}
            hex_payload = data.get("hex") or data.get("payload")
            if isinstance(hex_payload, str) and hex_payload:
                try:
                    # Prefer absolute import; fall back to relative if needed.
                    try:
                        from steelcity_impact_bridge.amg import parse_frame_hex
                    except Exception:
                        from .amg import parse_frame_hex
                    f = parse_frame_hex(hex_payload)
                    if f:
                        amg = {
                            "shot_idx": int(f.get("b2")),
                            "T_s": float(f.get("p1", 0)) / 100.0,
                            "split_s": float(f.get("p2", 0)) / 100.0,
                            "first_s": float(f.get("p3", 0)) / 100.0,
                            "tail_hex": f"0x{int(f.get('tail')):02x}",
                            "raw_hex": f.get("hex"),
                        }
                        # Attach decoded AMG data under data['amg'] and keep raw hex
                        data["amg"] = amg
                        obj["data"] = data
                except Exception:
                    # Non-fatal: if AMG parsing fails, continue and write raw event
                    pass
        except Exception:
            pass

    self.seq += 1
        # Monotonic clock (ms) for stable deltas
        # Allow suppression of ts_ms/t_iso for event records when configured
        now = time.time()
        lt = time.localtime(now)
        msec = int((now % 1.0) * 1000)
        # Always include human-friendly local time for readability
        hms = time.strftime("%H:%M:%S", lt) + f".{msec:03d}"
        obj.setdefault("hms", hms)
        # Never include machine timestamps in any record. If callers have
        # accidentally attached `ts_ms` or `t_iso`, remove them to ensure
        # logs do not contain those fields.
        obj.pop("ts_ms", None)
        obj.pop("t_iso", None)
        # Sequence and identity
        obj.setdefault("seq", self.seq)
        obj.setdefault("schema", "v1")
        obj.setdefault("session_id", self.session_id)
        obj.setdefault("pid", self.pid)
        # If rotation day changed, rotate handles (this will also reopen debug fh)
        if time.strftime("%Y%m%d") != self._rot_day:
            self.rotate()

        # Always write full record to debug file when enabled
        try:
            if self.dual_file and self._debug_fh:
                # Write a copy to debug (full, except ts_ms/t_iso already removed)
                self._debug_fh.write(json.dumps(obj) + "\n")
        except Exception:
            # non-fatal
            pass

        # Write to main file only if filtering allowed it (we already applied filters above)
        try:
            if self._fh:
                self._fh.write(json.dumps(obj) + "\n")
        except Exception:
            pass
