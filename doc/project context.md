You are helping me build a Raspberry Pi 4B BLE bridge for steel-plate impact detection.

Environment:
- Raspberry Pi OS Lite (64-bit), Python 3.x
- Installed: bluez, bluetooth; pip: bleak, numpy, cbor2, sounddevice
- BLE adapter(s): hci0 (internal). May add hci1 (USB) later.
- Timer: AMG Commander over BLE. I will supply the characteristic UUID that fires on START (T0).
- Sensor for PoC: WitMotion WTVB01-BT50 (BLE vibration). We will set its detection cycle to 100 Hz. Exact GATT UUIDs may vary; code must allow configuring characteristic UUIDs in a YAML file.
- Time authority: the bridge. T0 from AMG; all events get t_rel_ms = now - T0.
- Goal: minimal, reliable bridge I can run as a systemd service. Logs to NDJSON with sequence numbers.

Non-goals:
- No GUI beyond a tiny HTTP “health” page later.
- No PractiScore integration in this pass.

Deliver a small, modern Python project with:
- pyproject.toml (ruff + black config ok), src/ layout
- src/impact_bridge/:
  - config.py (read YAML env/config)
  - detector.py (envelope + hysteresis + ring-min + dead-time)
  - ble/amg.py (subscribe to AMG T0 characteristic)
  - ble/witmotion_bt50.py (connect, write config, subscribe notifications)
  - bridge.py (wire amg + sensors, timestamp + log)
  - logs.py (NDJSON writer w/ seq, rotation by size/date)
- scripts/run_bridge.py (CLI entry)
- config.example.yaml (placeholders for UUIDs, device MACs, thresholds)
- tests/test_detector.py (unit test with synthetic waveforms to prove false-hit guard)
- etc/bridge.service (systemd unit, templated ExecStart)

Constraints:
- Use asyncio. One bleak client per device, with graceful reconnects and backoff.
- All timestamps from time.monotonic_ns().
- Log schema (one JSON per line):
  { "seq":int, "type":"event|status|error", "ts_ms":float, "t_rel_ms":float|null, "plate":"P1"|null, "msg":str, "data":{...} }
- For BT50, if we don’t know the write/notify UUIDs at build time, expose them in YAML and fail with a clear error that lists discovered GATT characteristics.

Acceptance:
- `pytest` passes locally.
- `python -m scripts.run_bridge --config config.yaml` connects to AMG (when UUID is provided) and waits for T0; before T0, it logs periodic “status” lines; after START it logs “event” lines on BT50 amplitude jumps.
- If AMG is absent, program runs and logs status; a future “mic” T0 can be added without changing the core API.
