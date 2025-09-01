#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "$ROOT_DIR"

mkdir -p "$HOME/.config/systemd/user"
cp -f etc/ingest.user.service "$HOME/.config/systemd/user/ingest.user.service"

systemctl --user daemon-reload
systemctl --user enable ingest.user.service
systemctl --user restart ingest.user.service

echo "Installed/started user service: ingest.user.service"
