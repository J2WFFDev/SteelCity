# Project Inventory — SteelCity

Generated: 2025-09-03

This document inventories repository documentation, helper scripts, and key runtime scripts. Each entry has a short description, purpose, and relationships to other files. Use this as a quick orientation and handoff reference.

## How to use this file
- Scan the sections `Docs`, `Top-level scripts`, `scripts/`, and `src & tools pointers` for the items you need.
- For running or testing, see the `Quick commands` section at the end.

---

## Docs (doc/)

- `doc/HANDOFF.md`
  - Purpose: Primary runbook and operational handoff for the Raspberry Pi bridge. Contains milestone status, runtime instructions, configuration and verification steps, troubleshooting, and roadmaps.
  - Related to: `config.example.yaml`, `scripts/*`, `etc/*`, `doc/INGEST.md` (reporting), `README.md` (high-level).
  - Notes: Good first read for operators and for setting up the Pi.

- `doc/INGEST.md`
  - Purpose: Describes streaming ingestion into SQLite and usage of the ingest follower and batch tools.
  - Related to: `tools/ingest_follow.py`, `tools/ingest_sqlite.py`, `tools/sqlite_reports.py`, `scripts/install_ingest_service.sh`, `etc/ingest.user.service`.
  - Notes: Explains schema and idempotency expectations for NDJSON -> DB.

- `doc/HANDOFF_20250901.md`
  - Purpose: Snapshot handoff describing a change on Sep 1, 2025 (AMG individual-shot support, venv compatibility notes, test results).
  - Related to: `src/steelcity_impact_bridge/bridge.py` and `tests`.
  - Notes: Contains immediate next steps and the critical venv compatibility discovery.

- `doc/AMG_SIGNALS.md`
  - Purpose: AMG signal mapping and discovery plan; defines how T0, start button, arrow-end, and timeout are inferred and how to collect raw frames for reverse engineering.
  - Related to: `src/steelcity_impact_bridge/ble/amg.py`, `scripts/watch_amg.sh`, `tools/watch_amg.py`.

- `doc/project context.md`
  - Purpose: High-level project context and goals (audience, hardware, expected behaviors).
  - Related to: `README.md`, `doc/HANDOFF.md`.

- `doc/VENV_SETUP.md`
  - Purpose: Notes on virtual environment setup, particularly for BT50 compatibility and issues found during testing.
  - Related to: `scripts/run_bridge.sh`, `scripts/install_user_service.sh`, `requirements` in `pyproject.toml`.

- `doc/schema_v1.json`
  - Purpose: JSON Schema for NDJSON v1 event lines produced by the bridge. Describes required fields and types.
  - Related to: `tools/validate_logs.py`, `tools/sqlite_reports.py`, `src/steelcity_impact_bridge/logs.py`.

## Top-level documentation and runbooks

- `README.md`
  - Purpose: Primary repository landing document with quickstart and project overview.
  - Related to: everything; points to `doc/` and `scripts/` for operational detail.

- `QUICK_REFERENCE.md`
  - Purpose: Short operational cheat-sheet — commands and common flows (start, stop, tail logs, install user service).
  - Related to: `scripts/*.sh`, `doc/HANDOFF.md`.

- `TESTING_PROTOCOL.md` and `BRIDGE_TEST.md`
  - Purpose: Formalized testing protocols for the bridge (BT50-only, combined tests, expected event sequences).
  - Related to: `tools/*`, `scripts/timed_bridge_run.sh`, `doc/HANDOFF.md`.

- `HANDOFF_SESSION.md` and `HANDOFF_2025-09-03.md`
  - Purpose: Session-specific handoff notes and change logs. Useful for tracking operational findings and what changed between sessions.

---

## scripts/ (helper scripts)

All scripts in `scripts/` are intended to be run from the project root. Many assume an activated venv (`.venv`) and `PYTHONPATH=src`.

- `scripts/run_bridge.sh`
  - Purpose: Start the bridge process in background (creates `logs/bridge.pid` and `logs/bridge_run.out`). Activates `.venv` if present.
  - Related to: `scripts/run_bridge.py`, `scripts/stop_bridge.sh`, `logs/`.

- `scripts/stop_bridge.sh`
  - Purpose: Stop the bridge process using the pidfile, with fallback using process search.
  - Related to: `scripts/run_bridge.sh`.

- `scripts/timed_bridge_run.sh`
  - Purpose: Start the bridge, wait a specified duration, stop it, then tail NDJSON and stdout. Useful for controlled recordings.
  - Related to: `scripts/run_bridge.sh`, `scripts/stop_bridge.sh`, `scripts/timed_session_and_ingest.sh`.

- `scripts/timed_session_and_ingest.sh`
  - Purpose: Higher-level helper that runs a timed capture, ingests the resulting session to SQLite, and writes a small report.
  - Related to: `tools/ingest_sqlite.py`, `tools/sqlite_reports.py`, `logs/`.

- `scripts/install_user_service.sh`
  - Purpose: Installs and starts a per-user systemd unit for the bridge (`etc/bridge.user.service`).
  - Related to: `etc/bridge.user.service`, `scripts/run_bridge.sh`.

- `scripts/install_ingest_service.sh`
  - Purpose: Installs and starts the ingest follower user service (`etc/ingest.user.service`).
  - Related to: `doc/INGEST.md`, `tools/ingest_follow.py`.

- `scripts/discover_bt50.py`
  - Purpose: BLE scanner helper using `bleak` to locate BT50 or other devices; prints potential characteristic UUIDs and manufacturer data.
  - Related to: `config.example.yaml` (populate MACs/UUIDs), `scripts/run_bridge.sh`.

- `scripts/reset_ble.sh`
  - Purpose: Reset local Bluetooth stack on the Pi (restart service, power cycle adapter) to recover from stuck states.
  - Related to: `scripts/run_bridge.sh`, Pi maintenance tasks.

- `scripts/tail_latest.sh` and `scripts/grep_latest.sh`
  - Purpose: Tail the newest NDJSON files or grep for patterns in the most recent NDJSON. Useful for quick QA.

- `scripts/watch_amg.sh` and `scripts/watch_amg_live.sh`
  - Purpose: Wrappers to run Python tools that pretty-print AMG signals from an NDJSON or live notifications.

---

## src & tools pointers (not exhaustive)

NOTE: I inspected many `src` and `tools` files referenced by docs. The following are principal code entry points and tools that will be most relevant to operators:

- `src/steelcity_impact_bridge/bridge.py` (multiple variants present)
  - Purpose: Core bridge orchestration; wires AMG client and BT50 clients, timestamps events relative to T0, writes NDJSON.
  - Related to: `src/steelcity_impact_bridge/ble/*`, `src/steelcity_impact_bridge/logs.py`, `config.yaml`.

- `src/steelcity_impact_bridge/logs.py`
  - Purpose: NDJSON writer with sequence numbers, suppression rules for noisy debug messages, and rotation behavior.
  - Related to: `doc/schema_v1.json`, `tools/validate_logs.py`, `scripts/*`.

- `src/steelcity_impact_bridge/ble/witmotion_bt50.py` and `ble/amg.py`
  - Purpose: BLE clients for the BT50 sensor and AMG timer, respectively (connect, subscribe, parse notifications).
  - Related to: `scripts/discover_bt50.py`, `config.example.yaml`.

- `tools/` (various)
  - `ingest_follow.py`, `ingest_sqlite.py`, `sqlite_reports.py`: streaming and reporting tools for the NDJSON -> SQLite workflow.
  - `beautify_ndjson.py`, `summarize_ndjson.py`, `last_session.py`: quick analysis helpers referenced by docs.
  - `wtvb_live_decode.py`, `real_bt50_capture.py`: tools for parsing raw BT50 frames and collecting capture files for tuning detectors.

---

## tools/ (complete list and one-line purpose)

Below is an expanded list of files under `tools/` with a short description for each to help you locate the functionality you need.

- `tools/__init__.py` — package marker for `tools` and common imports (minimal).
- `tools/amg_control.py` — CLI to send named commands (from `config.yaml`) or raw writes to the AMG timer (write UUID helper).
- `tools/amg_commander.py` — utilities for AMG commander interactions (higher-level control and sequences).
- `tools/amg_live_decode.py` — live AMG packet decoding helper (pretty-prints AMG notification frames).
- `tools/amg_offline_decode.py` — decode AMG frames from saved captures or NDJSON for analysis.
- `tools/amg_print_frames.py` — simple printer of AMG frame byte streams for reverse-engineering.
- `tools/amg_recorder.py` — record AMG notifications into NDJSON or files for offline analysis.
- `tools/amg_send.py` — small helper to write a hex/text command to AMG (ad-hoc writes for debugging).
- `tools/amg_sniffer.py` — interactive BLE sniffer to find AMG notify characteristics and subscribe, prints hex and text when notifications arrive.
- `tools/amg_sniff_all.py` — broader AMG sniffing across multiple devices and services (batch scan + subscribe).
- `tools/amg_uuid_probe.py` — probe discovered devices for interesting service/characteristic UUIDs (helpful when UUIDs are unknown).
- `tools/amg_wtvb_capture.py` — tool to capture synchronized AMG and WTVB (BT50) data for correlation/analysis.
- `tools/amg_wtvb_features.py` — compute combined AMG + WTVB feature vectors for ML or offline analysis.
- `tools/amg_wtvb_join.py` — join AMG and WTVB event streams by timestamps/session for reports or ML datasets.
- `tools/analyze_ndjson_log.py` — general NDJSON analysis tool (summaries, counts, filters).
- `tools/analyze_shot_log.py` — shot-centric analysis (per-shot metrics, splits, counts) using NDJSON or CSV exports.
- `tools/beautify_ndjson.py` — pretty-printer for NDJSON (colors, concise summaries, optional stats). Useful for operators.
- `tools/bt50_buffer_capture.py` — capture raw BT50 frame buffers to disk on high-amplitude triggers for offline analysis.
- `tools/ble_connect_test.py` — verify BLE connectivity to a device (AMG or BT50) and basic read/write checks.
- `tools/ble_ls.py` — list nearby BLE devices and adv properties (alternative to `discover_bt50.py` script).
- `tools/check_amg_coverage.py` — compute AMG coverage and missed shots across sessions; reporting helper.
- `tools/compute_offsets.py` — calculate timing offsets between AMG T0 events and BT50 impacts for correlation reports.
- `tools/decode_amg_log.py` — decode saved AMG logs (NDJSON raw entries) into CSV or human-readable form.
- `tools/dump_t0_hit.py` — extract T0/HIT pairs from NDJSON logs for quick verification and CSV export.
- `tools/events_from_csv.py` — convert CSV exports back into NDJSON events or normalize CSV to expected schema.
- `tools/generate_offsets.py` (not present) — (if present) would generate offset tables; otherwise use `compute_offsets.py`.
- `tools/grep_amg.py` — search NDJSON logs for AMG-specific patterns, times, or raw bytes.
- `tools/ingest_follow.py` — long-running follower process that tails daily NDJSON and writes lines into `logs/bridge.db` in near real-time (installed as a user service).
- `tools/ingest_sqlite.py` — one-shot batch ingest of an NDJSON file into SQLite (idempotent via INSERT OR IGNORE).
- `tools/inspect_db.py` — quick DB inspection helper (counts, min/max timestamps, table info).
- `tools/last_session.py` — print last seen `session_id` or path to latest NDJSON — used by scripts and CI.
- `tools/normalize_ndjson.py` — normalize legacy NDJSON variations into schema v1 (field renames, fill-missing, reformatting).
- `tools/pretty_ndjson.ps1` — PowerShell wrapper to run the pretty NDJSON formatting on Windows terminals.
- `tools/pi_sync.ps1` — PowerShell helper to sync repo/artefacts to a Pi (scp/ssh wrapper for Windows users).
- `tools/provision_sensors.py` — helper to send configuration writes to sensors (BT50 config UUID writes) to provision settings.
- `tools/quick_log_summary.py` — produce a small textual summary of the latest NDJSON for quick triage.
- `tools/README_TIMING_REPORT.md` — README detailing how to run the timing correlation reports and interpretation of results.
- `tools/rtvb` (or `tools/wtvb` directory) — collection of offline helpers for BT50 frame decoding and transforms.
- `tools/simple_amg_test.ps1` — PowerShell script to exercise AMG connections from Windows for quick tests.
- `tools/summarize_ndjson.py` — produce session-level summaries (counts, durations, hit distributions) from NDJSON.
- `tools/summarize_amg_csv.py` — create AMGs specific summaries from CSV-extracted logs.
- `tools/timing_correlation_report.py` — core report generator that matches T0 -> HIT events, computes offsets, and emits CSV/summary (used by tests).
- `tools/test_amg_connect.py` — small connectivity test harness for AMG devices.
- `tools/validate_logs.py` — validate NDJSON lines against `doc/schema_v1.json` and report schema violations.
- `tools/wtvb_analyze.py` — offline analysis for WTVB/BT50 frame collections (feature extraction, peak detection).
- `tools/wtvb_decode_5561.py` — decode WTVB frames encoded as the 0x55/0x61 5561 format.
- `tools/wtvb_decode_guess.py` — heuristics to guess BT50 payload formats for unknown devices.
- `tools/wtvb_extract_wit_frames.py` — extract raw WIT frames from raw logs for reprocessing.
- `tools/wtvb_live_decode.py` — subscribe to BT50 notify char and print decoded frames live (used for manual calibration and captures).
- `tools/wtvb_live_watch.py` — wrapper to continuously watch BT50 frames and optionally write to NDJSON.
- `tools/wtvb_live_words.py` — higher-level live parser that attempts to map frames to named events/words.
- `tools/wtvb_offline_decode.py` — offline decode of a saved BT50 capture into human-readable table or CSV.
- `tools/wtvb_offline_dump.py` — dump binary captures to hex/text for transfer or sharing.
- `tools/wtvb_send.py` — send test payloads to WTVB/BT50 devices (if supported) for calibration.
- `tools/wtvb_wait_and_run.py` — helper that waits for a device then runs a capture/analysis sequence.
- `tools/wtvb_wait_and_run.py` — (duplicate entry) same as above — there may be duplicates/variants in the tools set.
- `tools/wtvb_words.py` — (if present) mapping of parsed frames to textual 'words' or named events.
- `tools/wtvb_offline_*` helpers — various offline tooling for decoding or dumping BT50 captures.
- `tools/watch_events.py` — watch an NDJSON file and print events matching filters.
- `tools/watch_spikes.sh` — small shell wrapper to watch logs for spikes in amplitude.
- `tools/watch_amg.py` — pretty-watch AMG-related events from NDJSON or live file and show a concise timeline.
- `tools/validate_logs.py` — (listed again) ensures logs conform to schema v1.
- `tools/sqlite_reports.py` — generate CSV/console reports from `logs/bridge.db` (sessions, hits, gaps, export).
- `tools/sqlite_inspect.py` — light DB inspection convenience tools.
- `tools/wtvb_wait_and_run.py` — orchestrate waiting for WTVB device then running test capture/analysis.

> Note: Many `wtvb_*` tools are variations on decode/capture/analyze. If you want, I can create a separate `doc/TOOLS_WTVB.md` that documents their exact CLI args and most important output files.

---

## tests/ (high-level)

Repository top-level `tests/` contains unit tests for core components. There are additional tests under `tools/tests/` which validate the analysis tooling.

Top-level tests (brief):

- `tests/test_detector.py` — unit tests for `HitDetector` (detector logic: trigger thresholds, ring detection, dead-time behavior). Verifies false-positive suppression and multi-hit behavior.
- `tests/test_ndjson_logger.py` — tests for `NdjsonLogger` suppression rules, `current_amp_threshold`, and verbose whitelist behavior.
- `tests/test_wtvb_parse.py` — tests that validate parsing of the BT50 0x55/0x61 payload (signed conversions, scaling, header checks).
- `tests/test_timing_correlation.py` — tests timing correlation utilities that match AMG T0 events to sensor HIT events and compute offsets (used by `tools/timing_correlation_report.py`).
- `tests/test_amg_signals.py` — tests for AMG signal classification heuristics (T0, arrow end, timeout end patterns).

Tooling tests (`tools/tests/`):
- `tools/tests/test_events.py` — tests for event generation and some tools-level processing.
- `tools/tests/test_decode.py` — tests for decoding routines used by tools (AMG/WTBV decoders).
- `tools/tests/conftest.py` — pytest fixtures for tools tests.

---

## Next actions I can take (choose any)
- Expand each `tools/` entry into a short subsection with CLI flags, environment variables, example invocations, and output locations.
- Add a dedicated `doc/TOOLS_WTVB.md` documenting the BT50/WTVB tooling (arg-by-arg) and recommended capture sequences.
- Run `pytest` in the workspace (will require a Python environment). I can attempt to run tests and report failures/tracebacks if you want.

---

## Quick commands (copy/paste)

- Start bridge in foreground (venv recommended):

```pwsh
cd C:\sandbox\TargetSensor\SteelCity
# On Pi (bash): source .venv/bin/activate
# then from project root on Pi:
PYTHONPATH=src python -m scripts.run_bridge --config config.yaml
```

- Start bridge in background (from project root on Pi):

```bash
./scripts/run_bridge.sh
```

- Stop bridge:

```bash
./scripts/stop_bridge.sh
```

- Tail latest NDJSON:

```bash
./scripts/tail_latest.sh 50
```

- Discover nearby BT devices (useful to find MAC/UUID):

```bash
python -m scripts.discover_bt50 --adapter hci0 --name WIT
```

---

## Suggested next steps and notes

- Add ownership lines to key docs (who to contact for AMGs, BT50s, and ops) if you want this inventory to drive on-call/hand-off.
- Consider adding a short `doc/INVENTORY_CHANGELOG.md` (or embed a table) to capture notable edits to docs and scripts over time.
- If you want deeper granularity (parameter-by-parameter explanation per script), tell me and I will expand each script's inventory entry to include expected args, env vars, and example outputs.

---

End of inventory.

---

## Detailed: Priority tools

Below are expanded descriptions for high-priority tools (CLI flags, env vars, examples, outputs, and related files). I started with BT50/WTVB, ingestion, reporting, and pretty-printing utilities useful for day-to-day ops.

### `tools/wtvb_live_decode.py`
- Purpose: Subscribe to a BT50/WTVB device notify characteristic and decode incoming 0x55/0x61 frames live, printing parsed fields (accelerations, temperature, counters) and summary energy metrics.
- Typical CLI flags (common patterns across tools):
  - `--address` / `--mac` : Bluetooth device MAC or address to connect to (optional; otherwise scans and picks).
  - `--char` : Notify characteristic UUID (default configured in code, commonly `0000ffe4-...`).
  - `--adapter` : BLE adapter (e.g., `hci0`).
  - `--raw` : Print raw hex frames instead of parsed fields.
- Environment variables:
  - None required; `BLEAK_LOG_LEVEL` can be set to control Bleak verbosity.
- Example invocations:
  - `python -m tools.wtvb_live_decode --address AA:BB:CC:DD:EE:FF`
  - `python tools/wtvb_live_decode.py --adapter hci0`
- Expected output: Human-readable decoded frames to stdout. Useful for tuning detector thresholds or when collecting training captures.
- Related files: `tools/wtvb_decode_5561.py`, `tools/wtvb_live_watch.py`, `tools/bt50_buffer_capture.py`.

### `tools/bt50_buffer_capture.py`
- Purpose: Maintain a rolling buffer of BT50 frames and write a detailed buffer file when amplitude crosses a configured threshold. The detailed files are used for offline debugging and detector tuning.
- Typical CLI flags:
  - `--threshold` : amplitude threshold to trigger detailed write.
  - `--outdir` : directory to write buffer files (default `logs/`).
  - `--max-buffer-ms` : how much recent data to keep in the rolling buffer.
- Environment variables:
  - `BT50_CAPTURE_DIR` (optional) to override output dir from environment in some wrappers.
- Example:
  - `python tools/bt50_buffer_capture.py --threshold 0.6 --outdir logs/`
- Expected output: `logs/buffer_detail_<ts>_<sensor>.txt` files containing the recent sequence of frames around the trigger and metadata (avg amp, peak index, timestamps).
- Related files: `src/steelcity_impact_bridge/bridge.py` (similar buffer write logic), `tools/wtvb_offline_dump.py`.

### `tools/ingest_follow.py`
- Purpose: Long-running follower that tails daily NDJSON (`logs/bridge_YYYYMMDD.ndjson`) and ingests lines into `logs/bridge.db` in near real-time. Designed to run as a user service.
- CLI flags:
  - `--log-dir` : directory containing NDJSON logs (default `logs/`).
  - `--db-path` : path to SQLite DB (default `logs/bridge.db`).
  - `--poll-ms` : polling interval in milliseconds for checking new lines.
  - `--from-start` : ingest from the start of the current daily file rather than tailing new entries only.
- Environment variables:
  - `INGEST_DB_PATH` : alternative way to set DB path.
- Example:
  - `python tools/ingest_follow.py --log-dir logs --db-path logs/bridge.db`
- Expected behavior and outputs:
  - Inserts NDJSON records into `events` table in `logs/bridge.db` with idempotency using `INSERT OR IGNORE(session_id, seq)` semantics.
  - Handles day rollover: automatically switches to new daily file when date changes.
  - Graceful shutdown on SIGINT/SIGTERM.
- Related files: `doc/INGEST.md`, `tools/ingest_sqlite.py`, `etc/ingest.user.service`.

### `tools/ingest_sqlite.py`
- Purpose: One-shot batch ingest of an NDJSON file into SQLite. Useful for backfills and one-off ingests.
- CLI flags:
  - `--infile` : path to NDJSON file to ingest.
  - `--db` : path to SQLite DB file (default `logs/bridge.db`).
  - `--session` : optional session id to force on imported rows.
- Environment variables:
  - `INGEST_DB_PATH` : alternative DB path.
- Example invocation:
  - `python tools/ingest_sqlite.py --infile logs/bridge_20250903.ndjson --db logs/bridge.db`
- Expected outputs:
  - Updated `logs/bridge.db` with rows from the NDJSON file. The tool creates `events` table and indexes if missing.
  - Prints counts of inserted vs skipped (due to existing keys).
- Related files: `tools/sqlite_reports.py`, `tools/inspect_db.py`.

### `tools/sqlite_reports.py`
- Purpose: Generate CSV or console reports from the SQLite `bridge.db`. Reports include per-session summaries, missing AMG coverage, T0->HIT match rates, and export helpers.
- CLI flags:
  - `--db` : path to DB (default `logs/bridge.db`).
  - `--report` : named report type (`sessions`, `t0_hits`, `gaps`, `export_csv`).
  - `--out` : path to write CSV output for `export_csv`.
- Environment variables: None required.
- Example:
  - `python tools/sqlite_reports.py --db logs/bridge.db --report sessions`
- Outputs: CSV or console tables summarizing sessions, hit counts, offsets, and coverage metrics.
- Related: `doc/INGEST.md`, `tools/timing_correlation_report.py`.

### `tools/beautify_ndjson.py`
- Purpose: Pretty-print NDJSON with color, concise one-line summaries, and optional statistics. Useful for live debugging and reading logs on terminals.
- CLI flags:
  - `--file` : NDJSON file to read (default: stdin).
  - `--filter` : simple filter expressions (e.g., `type==HIT`).
  - `--stats` : print aggregated stats at end.
  - `--no-color` : disable colorized output for logs or Windows consoles.
- Environment variables:
  - `TERM` / terminal emulator controls color support indirectly.
- Examples:
  - `python tools/beautify_ndjson.py logs/bridge_20250903.ndjson`
  - `cat logs/bridge_20250903.ndjson | python tools/beautify_ndjson.py --filter type==HIT --stats`
- Output: Colorized human-readable stream of events and optional stats summary.
- Related: `scripts/tail_latest.sh`, `tools/pretty_ndjson.ps1`.

### `tools/amg_sniffer.py`
- Purpose: Scan BLE devices, pick an AMG-like device, subscribe to candidate notify characteristics, and print raw hex/text payloads for reverse engineering.
- CLI flags:
  - `--scan-time` : duration to scan for devices before picking one.
  - `--mac` / `--address` : explicitly connect to a given device instead of scanning/picking.
  - `--list` : list services/characteristics and exit.
- Environment variables: None required.
- Examples:
  - `python tools/amg_sniffer.py --scan-time 5`
  - `python tools/amg_sniffer.py --mac 12:34:56:78:9A:BC --list`
- Output: Prints discovered devices, chosen UUIDs, and hexadecimal payloads from notifications. Helpful when exploring AMG firmware variations.
- Related files: `tools/amg_live_decode.py`, `tools/amg_recorder.py`, `doc/AMG_SIGNALS.md`.

### `tools/last_session.py`
- Purpose: Utility to print the last seen `session_id` or NDJSON path. Used by scripts to find the latest session quickly.
- CLI flags:
  - `--logs` : path to logs directory (default `logs/`).
  - `--poll` : poll until a session is available (useful in automation).
- Example:
  - `python tools/last_session.py --logs logs --poll`
- Output: prints session id or path to stdout.
- Related: `scripts/timed_session_and_ingest.sh`, `tools/ingest_sqlite.py`.

### `tools/timing_correlation_report.py`
- Purpose: Match AMG T0 events to BT50 HIT events, compute per-session offsets, and emit CSV suitable for calibration and aggregate statistics.
- CLI flags:
  - `--db` : optional DB input; if omitted reads NDJSON and computes matches in-memory.
  - `--out` : path to write CSV matches.
  - `--min-confidence` : threshold for accepting a T0->HIT match.
- Examples:
  - `python tools/timing_correlation_report.py --db logs/bridge.db --out reports/offsets.csv`
- Output: CSV of matches with columns: `session_id`, `t0_ts`, `hit_ts`, `offset_ms`, `sensor_id`, `confidence`.
- Related: `tools/compute_offsets.py`, `tools/sqlite_reports.py`, `tests/test_timing_correlation.py`.

---

I applied the priority set of tool expansions. I will now mark the first todo item completed and set the next todo in-progress if you want me to continue expanding the remaining tools.

---

## Full SteelCity/ folder listing (selected files, exclusions: `.vscode`, `.gitignore`)

Below is a file-by-file inventory for the `SteelCity/` folder (top-level and subfolders). Each entry has a one-line description; where relevant I note relationships to scripts/tools.

- `config_bt50_only.yaml` — config variant for BT50-only operation (used to run bridge without AMG).
- `config_clean.yaml` — cleaned config used for reproducible runs and examples.
- `config_bt50only.yaml` — alternate BT50-only config (duplicate name variants present).
- `config.yaml` — active default runtime configuration file read by the bridge.
- `config.example.yaml` — example configuration showing expected fields, device addresses, and UUIDs.
- `capture_real_frames.py` — script to capture raw frames from devices for offline analysis.
- `config_working92.yaml` — a working config snapshot used during development/testing.
- `BRIDGE_TEST.md` — manual test protocol or notes for validating bridge behavior.
- `bridge.py` — a top-level bridge variant (older or alternative entry point to `src` bridge code).
- `README.md` — repository landing page and quickstart.
- `QUICK_REFERENCE.md` — operational cheat-sheet with the most common commands and flows.
- `pyproject.toml` — project metadata and dev dependencies used for building/testing locally.
- `Makefile` — convenience targets for linting, packaging, or common commands.
- `HANDOFF_SESSION.md` — session-specific handoff notes.
- `HANDOFF_2025-09-03.md` — recent handoff notes capturing current status and decisions.
- `TESTING_PROTOCOL.md` — formalized testing procedures and expected outcomes.
- `temp_bridge.py` — experimental or temporary bridge script used for debugging.
- `steelcity.code-workspace` — VS Code workspace settings (ignore for ops).
- `scripts/timed_bridge_run.sh` — run bridge for a fixed duration and collect logs (useful for controlled captures).
- `scripts/tail_latest.sh` — tail the most recent NDJSON for quick live checks.
- `scripts/stop_bridge.sh` — stop background bridge process by pidfile or fallback search.
- `scripts/run_bridge.sh` — start bridge in background with pidfile management and venv activation.
- `scripts/run_bridge.py` — Python runner helper to start the bridge programmatically.
- `scripts/reset_ble.sh` — reset local BlueZ adapter and services (recover from stuck devices).
- `scripts/install_user_service.sh` — install and enable per-user systemd service for bridge.
- `scripts/install_ingest_service.sh` — install and enable per-user systemd service for ingest follower.
- `scripts/grep_latest.sh` — grep across the latest NDJSON logs.
- `scripts/discover_bt50.py` — BLE discovery helper to find BT50 or WIT devices and their UUIDs.
- `scripts/watch_amg.sh` — wrapper script to monitor AMG live events.
- `scripts/timed_session_and_ingest.sh` — orchestrated run to capture a timed session and ingest it to DB.
- `scripts/watch_amg_live.sh` — wrapper to run AMG live watch tools.

### tools/
- `tools/amg_control.py` — write commands to AMG devices; helper for sending control writes.
- `tools/amg_commander.py` — higher-level AMG command sequences and orchestration helpers.
- `tools/amg_live_decode.py` — decode AMG packets live from notifications.
- `tools/amg_offline_decode.py` — decode saved AMG frames from NDJSON or capture files.
- `tools/amg_uuid_probe.py` — enumerate services/characteristics on a chosen device to find AMG UUIDs.
- `tools/amg_wtvb_capture.py` — capture synchronized AMG + WTVB traces for correlation studies.
- `tools/amg_wtvb_features.py` — compute combined feature vectors from AMG+WTVB streams for analysis.
- `tools/amg_sniff_all.py` — scan and attempt subscribes across many devices to find AMG notify endpoints.
- `tools/amg_sniffer.py` — interactive sniffer that subscribes to notifications and prints payloads.
- `tools/amg_send.py` — send ad-hoc hex or text commands to AMG (manual testing).
- `tools/amg_recorder.py` — recorder to capture AMG notifications into NDJSON.
- `tools/amg_print_frames.py` — simple printer for AMG raw byte frames.
- `tools/amg_wtvb_join.py` — join AMG and WTVB streams by timestamps or session id for reporting.
- `tools/analyze_ndjson_log.py` — general-purpose NDJSON analysis and filtering tool.
- `tools/analyze_shot_log.py` — shot-centric analysis of events (per-shot metrics and splits).
- `tools/beautify_ndjson.py` — pretty-printer for NDJSON logs (terminal-friendly views).
- `tools/bt50_buffer_capture.py` — capture BT50 frame buffers and write detailed buffer dumps on triggers.
- `tools/ble_connect_test.py` — quick BLE connectivity checks (read/write/notify basics).
- `tools/ble_ls.py` — list nearby BLE devices and advertisement data.
- `tools/check_amg_coverage.py` — compute coverage metrics and detect missing AMG T0s per session.
- `tools/compute_offsets.py` — helper to compute T0→HIT offsets (used by timing reports).
- `tools/decode_amg_log.py` — decode AMG event logs to CSV or human readable formats.
- `tools/dump_t0_hit.py` — extract T0/HIT pairs into CSV for manual inspection.
- `tools/events_from_csv.py` — convert CSV event exports back into NDJSON schema v1.
- `tools/grep_amg.py` — search NDJSON for AMG frame patterns and heuristics.
- `tools/ingest_follow.py` — long-running ingest follower (tailing NDJSON to SQLite DB).
- `tools/ingest_sqlite.py` — batch NDJSON -> SQLite ingest tool with idempotency guarantees.
- `tools/inspect_db.py` — quick DB inspection utilities (counts, time ranges, schema checks).
- `tools/last_session.py` — print the latest session id or path for automation scripts.
- `tools/normalize_ndjson.py` — normalize old/variant NDJSON lines to schema v1.
- `tools/pi_sync.ps1` — PowerShell helper to sync repo or artifacts to a Raspberry Pi.
- `tools/pretty_ndjson.ps1` — PowerShell wrapper for pretty-printing NDJSON on Windows.
- `tools/provision_sensors.py` — write configuration to sensors (BT50 provisioning writes).
- `tools/quick_log_summary.py` — short summaries for the latest NDJSON file (counts and quick stats).
- `tools/README_TIMING_REPORT.md` — instructions and interpretation notes for timing reports.
- `tools/rtvb/` — directory containing many WTVB/WTBV decoding and capture helpers (see `tools/wtvb_*`).
- `tools/summarize_ndjson.py` — session-level summary generator for NDJSON logs.
- `tools/summarize_amg_csv.py` — generate AMG-specific summaries from CSV exports.
- `tools/timing_correlation_report.py` — match T0→HIT and emit CSV of offsets and matches for calibration.
- `tools/test_amg_connect.py` — small connectivity test for AMG devices.
- `tools/validate_logs.py` — validate NDJSON events against `doc/schema_v1.json`.
- `tools/wtvb_analyze.py` — offline analysis and feature extraction for WTVB captures.
- `tools/wtvb_decode_5561.py` — decoder for 0x55/0x61 5561 BT50 frame format.
- `tools/wtvb_decode_guess.py` — heuristics to guess unknown BT50 payload encodings.
- `tools/wtvb_extract_wit_frames.py` — extract raw WIT frames from capture files for reprocessing.
- `tools/wtvb_live_decode.py` — live BT50 decoder for interactive sessions.
- `tools/wtvb_live_words.py` — attempt to map decoded BT50 frames to named events/words.
- `tools/wtvb_live_watch.py` — continuous watcher that optionally writes BT50 frames to NDJSON.
- `tools/wtvb_offline_decode.py` — offline decoding of BT50 captures to CSV/human tables.
- `tools/wtvb_offline_dump.py` — dump binary captures to hex/text for sharing or inspection.
- `tools/wtvb_send.py` — send test payloads to BT50 devices (if supported by hardware).
- `tools/wtvb_wait_and_run.py` — wait-for-device helper then run capture/analysis steps.
- `tools/wtvb_live_watch.py` — (duplicate) live watch wrapper variant.
- `tools/wtvb_words.py` — mapping layer from decoded frames to words/events (if present).
- `tools/watch_events.py` — tail and filter NDJSON events with simple predicates.
- `tools/watch_spikes.sh` — shell helper to alert on amplitude spikes in logs.
- `tools/watch_amg.py` — pretty watchers for AMG events (live or file-based).
- `tools/sqlite_reports.py` — reports generator from `logs/bridge.db` (sessions, gaps, exports).
- `tools/sqlite_inspect.py` — simple DB introspection helpers.
- `tools/wtvb_wait_and_run.py` — (duplicate) orchestrator for wait+run sequences for BT50 tests.

### etc/
- `etc/bridge.env.example` — example environment file for bridge systemd service.
- `etc/bridge.service` — systemd unit for system-wide bridge runs (not user service).
- `etc/bridge.user.service` — example per-user systemd unit for running the bridge.
- `etc/ingest.user.service` — per-user systemd unit for running `tools/ingest_follow.py`.

### src/
- `src/steelcity_impact_bridge/__init__.py` — package marker for the Python package.
- `src/steelcity_impact_bridge/logs.py` — NDJSON logging helper with suppression rules and sequence numbers.
- `src/steelcity_impact_bridge/detector.py` — `HitDetector` implementation and `DetectorParams` used by the bridge.
- `src/steelcity_impact_bridge/config.py` — config helpers and YAML parsing utilities.
- `src/steelcity_impact_bridge/bridge.py` — primary bridge implementation (core orchestration logic).
- `src/steelcity_impact_bridge/amg.py` — AMG BLE client, frame parsing, and signal classification helpers.
- `src/steelcity_impact_bridge/ble/wtvb_parse.py` — BT50 (WTVB) frame parsing helpers.
- `src/steelcity_impact_bridge/ble/witmotion_bt50.py` — BT50-specific BLE client wrapper used by the bridge.
- `src/steelcity_impact_bridge/ble/util.py` — BLE helper utilities used across clients.
- `src/steelcity_impact_bridge/ble/amg.py` — AMG BLE client implementation (notify characteristic handling).
- `src/steelcity_impact_bridge/ble/amg_signals.py` — AMG signal heuristics and classifiers used by tests.

### tests/
- `tests/test_wtvb_parse.py` — unit tests for the BT50 parse helpers.
- `tests/test_timing_correlation.py` — tests for timing match and offset logic.
- `tests/test_ndjson_logger.py` — tests for NDJSON logger suppression and sequence handling.
- `tests/test_detector.py` — tests for impact detector behavior and edge cases.
- `tests/test_amg_signals.py` — tests for AMG signal classification heuristics.

### tools/tests/
- `tools/tests/test_events.py` — tests for tools-level event generation.
- `tools/tests/test_decode.py` — tests for decoder helpers used by `tools`.
- `tools/tests/conftest.py` — pytest fixtures used by tools tests.

### docs and misc
- `doc/AMG_SIGNALS.md` — AMG signal mapping and reverse-engineering notes.
- `doc/INGEST.md` — ingestion architecture and SQLite schema notes.
- `doc/HANDOFF_20250901.md` — historical handoff snapshot.
- `doc/HANDOFF.md` — main handoff/runbook for operators.
- `doc/project context.md` — project goals, scope, and context document.
- `doc/VENV_SETUP.md` — venv/compatibility notes and known issues.
- `doc/schema_v1.json` — NDJSON v1 JSON Schema used by `tools/validate_logs.py`.
- `doc/INVENTORY.md` — this file (inventory).

---

I finished enumerating files and inserted the per-file one-line descriptions into `doc/INVENTORY.md`. Next, I will mark the todo item completed and run a readback to validate formatting.
