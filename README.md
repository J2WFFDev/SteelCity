## Contents

- Streaming ingest to SQLite for near-real-time reporting
- Docs for ingest and AMG signal mapping

## Services

- Ingest follower service (streams NDJSON -> SQLite): see `etc/ingest.user.service`, installed by `scripts/install_ingest_service.sh`.

## Tools

- `tools/ingest_follow.py` — live follower that ingests as lines are appended
- `tools/sqlite_inspect.py` — quick DB row count and timestamp bounds
- `tools/last_session.py` — print latest `session_id` or NDJSON path

## Documentation

- `doc/INGEST.md` — ingest architecture and usage
- `doc/AMG_SIGNALS.md` — current AMG signal mapping and discovery plan

# SteelCity Impact Bridge

Raspberry Pi 4B BLE bridge to timestamp steel plate hits relative to **T₀** from the **AMG Commander**.
PoC sensor is the **WitMotion WTVB01-BT50** (BLE vibration).

## Quick start

```bash
cd ~/projects/steelcity
python -m pip install -e ".[dev]"
cp config.example.yaml config.yaml
# Discover UUIDs/MACs:
python -m scripts.discover_bt50 --adapter hci0 --name WIT
python tools/amg_sniffer.py --adapter hci0
# Edit config.yaml with:
#  - amg.start_uuid (the one that fires on START)
#  - sensors[0].mac and sensors[0].notify_uuid
pytest -q
python -m scripts.run_bridge --config config.yaml
```

Logs: NDJSON in `./logs/bridge_YYYYMMDD.ndjson`.

Edge helper scripts:
```bash
# Start bridge in background (creates logs/bridge.pid and logs/bridge_run.out)
./scripts/run_bridge.sh

# Stop bridge cleanly
./scripts/stop_bridge.sh

# Timed run (start → wait for PID → sleep N seconds → stop → tail logs)
AMG_DEBUG_RAW=1 ./scripts/timed_bridge_run.sh 90
```

User service (recommended on the Pi):
```bash
# Install and start a per-user systemd unit that runs the bridge
chmod +x scripts/install_user_service.sh
./scripts/install_user_service.sh

# Optional environment overrides (copy example then edit)
cp -n etc/bridge.env.example etc/bridge.env || true
sed -n '1,120p' etc/bridge.env

# Ensure user services run at boot (once per user)
loginctl enable-linger "$USER"

# Check status and logs
systemctl --user status bridge.user.service --no-pager
journalctl --user -u bridge.user.service -n 200 --no-pager
```

System service (optional):
```bash
sudo cp etc/bridge.service /etc/systemd/system/bridge.service
sudo systemctl daemon-reload
sudo systemctl enable --now bridge
journalctl -u bridge -f
```

## Event schema

One JSON line per record:
```json
{
  "seq":123,
  "type":"event|status|error",
  "ts_ms": 123456.7,
  "t_rel_ms": 842.3,
  "plate":"P1",
  "msg":"HIT|T0|...",
  "data":{"peak":12.3,"rms":2.0,"dur_ms":60.0}
}
```

Validate logs:

```bash
python tools/validate_logs.py logs/bridge_$(date +%Y%m%d).ndjson
```

## Notes

- BT50 has no timestamp/RTC; the bridge timestamps on packet receipt.
- Set BT50 detection cycle to **100 Hz** when Armed (we expose a config UUID in YAML; bytes TBD).
- For sub-ms timing, switch to a dedicated high-g accelerometer node later.

Generated 2025-08-27.

## Logging and rotation

- NDJSON files are written to `logs/bridge_YYYYMMDD.ndjson` and rotate automatically at midnight (calendar day change).
 - Dual-file mode: when enabled in `config.yaml` the bridge writes a compact operational log to `logs/` and a full debug log to `logs/debug/` (files named `<prefix>_debug_YYYYMMDD_HHMMSS.ndjson`). This keeps day-to-day logs concise while preserving verbose diagnostics for later analysis.
- Writes are line-buffered; each JSON line is flushed on write. Files are properly closed on rotation/stop.
- The `seq` counter increments per event and continues across midnight while the process runs; it resets on process restart. `ts_ms` is process‑relative (monotonic) milliseconds.
 - Note: the NDJSON writer no longer emits machine timestamps `ts_ms` or `t_iso` in new logs; only `hms` (human-local time) and `t_rel_ms` are present. Ingest tools in `tools/` have been updated to fallback from `ts_ms` to `t_rel_ms` or wall-clock time when building DB records.
- Process stdout/stderr goes to `logs/bridge_run.out` when using `run_bridge.sh`.
- Planned enhancement: size‑based NDJSON rotation and a per‑run `session_id` included in filenames and records; optionally redirect process logs fully to journald under the user service.

## Device timeouts and reconnection

- AMG Commander: known idle timeout around 30 minutes. The bridge will reconnect when it sees disconnects. Look for `amg_connected` and any reconnect attempts in NDJSON.
- WitMotion BT50: timeout behavior varies by firmware; evaluate by reviewing gaps between `bt50_stream` summaries and any connection status lines in NDJSON.
- Recommended: run a timed capture (e.g., 30–60 minutes) and inspect NDJSON for reconnection patterns and stream continuity.

## AMG control (beep, sensitivity)

We use Nordic UART (NUS) to read notifications and optionally write commands.

- Notify UUID: `6e400003-b5a3-f393-e0a9-e50e24dcca9e` (configure as `amg.start_uuid`).
- Write UUID: `6e400002-b5a3-f393-e0a9-e50e24dcca9e` (configure as `amg.write_uuid`).

Enable optional AMG writes via `config.yaml`:

```yaml
amg:
  adapter: hci0
  mac: 60:09:C3:1F:DC:1A
  start_uuid: "6e400003-b5a3-f393-e0a9-e50e24dcca9e"
  write_uuid: "6e400002-b5a3-f393-e0a9-e50e24dcca9e"
  init_cmds: []
  commands:
    beep:
      text: "BEEP"
    test_raw_aa10:
      hex: "AA-10"
```

After AMG connects, the bridge sends `init_cmds` (if any). You can also use named commands via the helper tool:

```bash
# Ad-hoc writes (direct MAC path to avoid scans)
python tools/amg_send.py --adapter hci0 --mac 60:09:C3:1F:DC:1A --text BEEP
python tools/amg_send.py --adapter hci0 --mac 60:09:C3:1F:DC:1A --hex AA-10

# Named commands using config.yaml mappings
python tools/amg_control.py --adapter hci0 --mac 60:09:C3:1F:DC:1A --config config.yaml --beep
python tools/amg_control.py --adapter hci0 --mac 60:09:C3:1F:DC:1A --config config.yaml --command test_raw_aa10
```

For reverse‑engineering, run with raw logging enabled and interact with the timer:

```bash
AMG_DEBUG_RAW=1 python -m scripts.run_bridge --config config.yaml
```
Then `grep` the NDJSON for `amg_raw` events to see raw bytes.

## Reconnect tuning

`config.yaml` supports backoff and keepalive tuning:

```yaml
amg:
  reconnect_initial_sec: 2.0
  reconnect_max_sec: 20.0
  reconnect_jitter_sec: 1.0
sensors:
  - plate: P1
    idle_reconnect_sec: 15.0
    keepalive_batt_sec: 60.0
    reconnect_initial_sec: 2.0
    reconnect_max_sec: 20.0
    reconnect_jitter_sec: 1.0
```

## Windows → Pi workflow (no Live Share)

When editing locally on Windows in this repo and running on the Raspberry Pi:

1) Push from Windows as usual:
```pwsh
cd C:\sandbox\TargetSensor\SteelCity
git add -A
git commit -m "change"
git push
```

2) From VS Code (Ctrl+Shift+P → Tasks: Run Task), use the provided tasks:
- `Pi: Pull latest (origin/main)` — updates the Pi checkout (`~/projects/steelcity`).
- `Pi: Install deps` — installs/upgrades dependencies on the Pi (`pip install -e .[dev]`).
- `Pi: Run discover BT50` — scans for the WitMotion BT50 (BLE).
- `Pi: Run bridge (config.yaml)` — runs the bridge with `config.yaml`.
- `Pi: Tail logs (journalctl bridge)` — follows the systemd service logs.
- `Pi: Restart bridge service (sudo)` — restarts the service.

SSH host `raspberrypi` must be defined locally (see `Host raspberrypi.txt`).

## Handoff and Operations Guide

See `doc/HANDOFF.md` for a complete runbook covering:
- Pi environment setup and venv
- Configuration (UUIDs/MACs)
- Foreground and systemd runs
- Verifying BT50/AMG milestones
- Git/GitHub sync between Windows and Pi

