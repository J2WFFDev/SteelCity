#!/usr/bin/env bash
set -euo pipefail

# Install or update the user-level systemd unit for the SteelCity bridge
# Usage: ./scripts/install_user_service.sh

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "$ROOT_DIR"

mkdir -p "$HOME/.config/systemd/user"
cp -f etc/bridge.user.service "$HOME/.config/systemd/user/bridge.user.service"

systemctl --user daemon-reload
systemctl --user enable bridge.user.service

# If already running, restart to pick up updates; otherwise just start
if systemctl --user is-active --quiet bridge.user.service; then
  systemctl --user restart bridge.user.service
else
  systemctl --user start bridge.user.service
fi

echo "Installed/started user service: bridge.user.service"
