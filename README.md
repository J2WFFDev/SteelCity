
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

Systemd:
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

## Notes

- BT50 has no timestamp/RTC; the bridge timestamps on packet receipt.
- Set BT50 detection cycle to **100 Hz** when Armed (we expose a config UUID in YAML; bytes TBD).
- For sub-ms timing, switch to a dedicated high-g accelerometer node later.

Generated 2025-08-27.
