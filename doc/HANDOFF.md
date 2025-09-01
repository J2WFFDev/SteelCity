# SteelCity Impact Bridge — Handoff

Date: 2025-08-29

This document consolidates the current working code paths, runbook, Raspberry Pi setup, and roadmap/status for the product path.

## Milestone status (2025-08-29)

- Bridge reliably connects to AMG (NUS) and BT50, logs NDJSON with `session_id`, and detects `T0` + `HIT`.
- Per-user systemd service available; helper scripts for start/stop/timed runs.
- Streaming ingest follower writes NDJSON lines into SQLite (`logs/bridge.db`) in near real time with idempotent inserts.
- SQL reporting CLI (`tools/sqlite_reports.py`) provides sessions/types/hits/gaps/recent and CSV export.
- Verified runs today include a ~40-minute session with 25 hits; CSVs exported for review.

Artifacts of interest:
- NDJSON: `logs/bridge_YYYYMMDD.ndjson` (source of truth)
- SQLite: `logs/bridge.db`
- CSV exports: `logs/runYYYYMMDD_HHMMSS.csv`

## Repository layout

- `src/steelcity_impact_bridge/`
  - `bridge.py`: orchestrates AMG + BT50, logs NDJSON, hit detection.
  - `ble/amg.py`: AMG Smart Timer BLE client; emits T0 events.
  - `ble/witmotion_bt50.py`: WitMotion BT50 BLE client; streams packets.
  - `config.py`: typed config and YAML loader.
  - `logs.py`: NDJSON logger.
- `scripts/`
  - `run_bridge.py`: entrypoint (`python -m scripts.run_bridge`).
  - `discover_bt50.py`: BT50 device discovery helper.
  - `run_bridge.sh`: start the bridge on the Pi (creates `logs/bridge.pid`, logs to `logs/bridge_run.out`).
  - `stop_bridge.sh`: stop the bridge using the pidfile with fallbacks.
  - `timed_bridge_run.sh`: start → wait for PID → sleep → stop → tail latest NDJSON and stdout.
  - `install_user_service.sh`: install/enable per‑user systemd service.
  - `tail_latest.sh`: show the last N lines (default 50) from the latest NDJSON.
  - `grep_latest.sh`: grep the latest NDJSON for `bt50_*`, `amg_*`, `HIT`, or custom patterns.
- `tools/`: standalone utilities for decode, sniffing, and analysis.
- `etc/bridge.service`: optional system systemd unit for auto-start on Pi.
- `etc/bridge.user.service`: per‑user systemd unit (recommended) that uses the helper scripts.
- `etc/bridge.env.example`: example environment overrides file.
- `config.yaml`: runtime configuration (copy from example and edit).
- `logs/`: NDJSON output files `bridge_YYYYMMDD.ndjson` on the Pi.

## Runtime environment (Raspberry Pi)

- Host: Raspberry Pi 4B, Debian Bookworm aarch64
- BLE stack: BlueZ (`hci0`)
- Python: 3.11 venv at `~/projects/steelcity/.venv`
- Project checkout: `~/projects/steelcity`

Create venv and install:

```bash
sudo apt-get update
sudo apt-get install -y python3-venv bluetooth bluez bluez-tools
cd ~/projects/steelcity
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e ".[dev]"
```

Ensure the repo is located at `~/projects/steelcity` and `PYTHONPATH=src` is set when running.

## Configuration

Copy and edit `config.yaml`:

```bash
cp config.example.yaml config.yaml
vi config.yaml
```

- AMG:
  - `adapter: "hci0"`
  - `mac: "60:09:C3:1F:DC:1A"`
  - `start_uuid: "6e400003-b5a3-f393-e0a9-e50e24dcca9e"`
- BT50 sensor (plate `P1`):
  - `adapter: "hci0"`
  - `mac: "F8:FE:92:31:12:E3"`
  - `notify_uuid: "0000ffe4-0000-1000-8000-00805f9a34fb"`
  - `config_uuid: "0000ffe9-0000-1000-8000-00805f9a34fb"` (optional write)

## Running locally on the Pi (foreground)

```bash
cd ~/projects/steelcity
source .venv/bin/activate
PYTHONPATH=src python -m scripts.run_bridge --config config.yaml
```

Outputs NDJSON to `logs/bridge_YYYYMMDD.ndjson`. Process stdout is minimal.

## SQL reports and CSV export

Quick reads on the Pi:

```bash
# Recent sessions with counts and durations
./.venv/bin/python -m tools.sqlite_reports --db logs/bridge.db sessions --limit 10

# Type counts and hits for a given session
./.venv/bin/python -m tools.sqlite_reports --db logs/bridge.db types --session <SESSION_ID>
./.venv/bin/python -m tools.sqlite_reports --db logs/bridge.db hits  --session <SESSION_ID>

# Gap analysis (>10s) within session
./.venv/bin/python -m tools.sqlite_reports --db logs/bridge.db gaps --session <SESSION_ID> --threshold-sec 10

# Export a session to CSV
./.venv/bin/python -m tools.sqlite_reports --db logs/bridge.db export --session <SESSION_ID> --out logs/<SESSION_ID>.csv
```

See also: `doc/INGEST.md` → Reports.

## Running via helper scripts (background)

From the Pi:

```bash
cd ~/projects/steelcity
chmod +x scripts/*.sh
# Start in background, stop cleanly, and do a timed run with raw AMG frames enabled
./scripts/run_bridge.sh
./scripts/stop_bridge.sh
AMG_DEBUG_RAW=1 ./scripts/timed_bridge_run.sh 90
./scripts/tail_latest.sh 50
./scripts/grep_latest.sh
```

This avoids shell quoting issues when starting from Windows.

## Running under systemd (optional)

```bash
cd ~/projects/steelcity
sudo cp etc/bridge.service /etc/systemd/system/bridge.service
sudo systemctl daemon-reload
sudo systemctl enable --now bridge
journalctl -u bridge -f
```

The unit uses `PYTHONPATH=src` and the venv python. Adjust paths if your checkout differs.

### User service (recommended)

```bash
cd ~/projects/steelcity
chmod +x scripts/install_user_service.sh
./scripts/install_user_service.sh
cp -n etc/bridge.env.example etc/bridge.env || true
loginctl enable-linger "$USER"
systemctl --user status bridge.user.service --no-pager
journalctl --user -u bridge.user.service -f --no-pager
```

## Verifying BT50 and AMG

- BT50 discovery (if MAC is unknown):

```bash
cd ~/projects/steelcity
source .venv/bin/activate
PYTHONPATH=src python -m scripts.discover_bt50 --adapter hci0 --name WIT
```

- Check NDJSON for milestones:

```bash
cd ~/projects/steelcity
latest=$(ls -t logs/bridge_*.ndjson | head -n 1)
tail -n 50 "$latest"
# Look for: bt50_connecting, bt50_connected, bt50_stream, amg_connected, T0
```

## Known good code paths (as of 2025-08-28)
## Logging and rotation

- NDJSON files are written to `logs/bridge_YYYYMMDD.ndjson` and rotate automatically at midnight (calendar day change).
- Writes are line-buffered; each JSON line is flushed on write. Files are properly closed on rotation/stop.
- The `seq` counter increments per event and continues across midnight while the process runs; it resets on process restart. `ts_ms` is process‑relative (monotonic) milliseconds.
- `logs/bridge_run.out` receives process stdout/stderr when using `run_bridge.sh`.
- Planned enhancement: size‑based NDJSON rotation and per‑run `session_id` in filenames and records; option to rely solely on journald under the user service.

## Device timeouts and reconnection

- AMG Commander: known idle timeout around 30 minutes; the bridge reconnects when disconnects occur. Watch NDJSON for `amg_connected` and reconnect attempts.
- WitMotion BT50: timeouts vary by firmware; evaluate by inspecting continuity of `bt50_stream` summaries and connection state lines.
- Recommendation: timed captures (30–60 minutes) to reveal timeout behavior and inform next steps.

## Roadmap and status

Completed:
- Reliable edge capture: synchronized AMG + BT50 logging, T0 + raw frames, hit detection, heartbeats.
- Helper scripts: pidfile‑based start/stop, timed runs.
- User service: per‑user systemd unit with optional environment overrides.

Next steps:
- Lock NDJSON schema v1 and keep validator alongside (`tools/validate_logs.py`) — DONE.
- Enhance rotation (optional size‑based) and include per‑run `session_id` in filenames — PARTIAL (session_id in records; filenames later).
- Streaming SQLite ingest — DONE (`tools/ingest_follow.py` + user service).
- SQL reporting — DONE (`tools/sqlite_reports.py`).
- Edge API (FastAPI) for status/recent events and simple dashboards — TODO.
- Cloud ingest with retention policies — TODO.

Immediate next 3 actions (when you resume):
1) AMG signals mapping: capture raw (`AMG_DEBUG_RAW=1`) for start/random-delay/arrow/timeout/power-off; add classifiers and emit structured events; document in `doc/AMG_SIGNALS.md`.
2) Session semantics: emit `SESSION_END` with `reason` (timeout/arrow/power-off) and optional session_id rotation; update schema v1 notes and reports to summarize session end reasons.
3) Reporting add-ons: per-plate “last seen” and stream cadence; error summaries over a window; top N gaps list with timestamps.

- `src/steelcity_impact_bridge/ble/witmotion_bt50.py` — normalized to LF line endings (previous CRLF caused `IndentationError` on Pi). Uses Bleak 1.x patterns and `device='hci0'` connect.
- `src/steelcity_impact_bridge/bridge.py` — logs `bt50_connecting`, `bt50_connected`, `bt50_battery`, `bt50_services`, periodic `bt50_stream`; proceeds even if AMG isn’t available.
- `src/steelcity_impact_bridge/ble/amg.py` — filters for strict start-frame; emits `amg_connected` and T0 events.

## Git and sync workflow

From Windows (this repo):

```powershell
cd C:\sandbox\TargetSensor\SteelCity
git add -A
git commit -m "<message>"
git push
```

On the Raspberry Pi:

```bash
cd ~/projects/steelcity
git pull --rebase
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

If you edited files directly on the Pi, commit them there and push:

```bash
cd ~/projects/steelcity
git add -A
git commit -m "Pi changes: <summary>"
git push
```

If the Pi has a separate remote name or branch, set upstream accordingly:

```bash
git remote -v
# If needed:
# git remote add origin <your-repo-url>
# git branch --set-upstream-to=origin/main main
```

## Remote and branch verification

Use these to verify and repair your git setup on both Windows and the Pi.

Windows (PowerShell):

```powershell
cd C:\sandbox\TargetSensor\SteelCity
git remote -v
git branch -vv
# If origin is missing:
# git remote add origin https://github.com/<you>/<repo>.git
# If your local main has no upstream:
# git branch --set-upstream-to=origin/main main
# Or set upstream on first push:
# git push -u origin main
```

Raspberry Pi (bash):

```bash
cd ~/projects/steelcity
git remote -v
git branch -vv
# If origin is missing, add it:
# git remote add origin https://github.com/<you>/<repo>.git
git fetch origin
# Ensure you're on main and tracking origin/main:
git checkout -B main origin/main
# From now on, use:
git pull --rebase
```

## Troubleshooting

- Multiple bridge instances: stop them before restarting

```bash
pkill -f scripts.run_bridge || true
```

- No BT50 logs in NDJSON: verify venv and PYTHONPATH

```bash
source .venv/bin/activate
python -c 'import sys; print(sys.executable); sys.path.insert(0, "src"); import steelcity_impact_bridge.ble.witmotion_bt50 as m; print(m.__file__)'
```

- BT50 in use: detach from other hosts and re-scan with `bluetoothctl`.

```bash
bluetoothctl info F8:FE:92:31:12:E3
bluetoothctl disconnect F8:FE:92:31:12:E3 || true
bluetoothctl remove F8:FE:92:31:12:E3 || true
bluetoothctl scan on
```

- AMG Commander not present: bridge continues; you’ll see `amg_connect_failed`. Once available, press Start and look for `{"type":"event","msg":"T0"}`.

## Acceptance checklist

- [ ] `logs/bridge_*.ndjson` contains `bt50_connecting` then recurring `bt50_stream`.
- [ ] `amg_connected` appears when AMG is present; `T0` when Start is pressed.
- [ ] Single bridge instance running (via systemd or foreground).
- [ ] Pi and GitHub are in sync (`git status` clean on both).

## Quick start tomorrow (checklist)

1) Ensure services healthy and storage ok:
  - `systemctl --user status ingest.user.service --no-pager`
  - `systemctl --user status bridge.user.service --no-pager`
  - `df -h ~ | sed -n 1,5p`
2) Start a 10–15 min timed run and trigger a few hits:
  - `AMG_DEBUG_RAW=1 ./scripts/timed_bridge_run.sh 900`
3) Inspect NDJSON and DB in real time:
  - `./scripts/tail_latest.sh 50`
  - `./.venv/bin/python -m tools.sqlite_reports --db logs/bridge.db recent --window-sec 600`
4) Export that session to CSV for sharing:
  - `SID=$(./.venv/bin/python -m tools.last_session)`
  - `./.venv/bin/python -m tools.sqlite_reports --db logs/bridge.db export --session "$SID" --out logs/$SID.csv`


