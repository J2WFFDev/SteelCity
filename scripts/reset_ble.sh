#!/usr/bin/env bash
set -euo pipefail

echo "[reset] Stopping Bluetooth service..."
sudo systemctl stop bluetooth || true

echo "[reset] Killing any lingering bluetoothctl..."
sudo pkill -f bluetoothctl || true

echo "[reset] Unblocking rfkill..."
sudo rfkill unblock bluetooth || true

echo "[reset] Powering adapter hci0 off via btmgmt..."
sudo btmgmt -i hci0 power off || true
sleep 2

echo "[reset] Starting Bluetooth service..."
sudo systemctl start bluetooth || true
sleep 2

echo "[reset] Powering adapter hci0 on via btmgmt..."
sudo btmgmt -i hci0 power on || true
sleep 1

echo "[reset] Forcing scan off..."
bluetoothctl --timeout 1 scan off || true

echo "[status] bluetoothctl show:"
bluetoothctl show || true

echo "[status] btmgmt info:"
btmgmt info || true

echo "[status] Recent bluetoothd logs:"
journalctl -u bluetooth -n 40 --no-pager || true

echo "[done] Reset complete."
