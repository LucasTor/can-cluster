#!/usr/bin/env bash
#
# logs.sh — tail the can-cluster service logs from the Pi over SSH.
#
# Usage:
#   ./logs.sh            Follow all cluster logs live (Ctrl-C to stop)
#   ./logs.sh gpio       Follow only the [gpio] pin lines (find your wiring)
#   ./logs.sh canrt      Follow only the [canrt] FTCAN real-time broadcast lines
#   ./logs.sh 100        Show the last 100 lines and exit (any number works)
#   ./logs.sh <args...>  Pass arbitrary args straight to journalctl
#
# Connection settings (override via environment if they change):
#   PI_HOST=192.168.0.153 PI_USER=lucas PI_PASS=lucas ./logs.sh
#
# Needs sshpass (macOS: brew install sshpass). With an SSH key set up
# (ssh-copy-id), it works passwordless and sshpass is unnecessary.

set -euo pipefail

PI_HOST="${PI_HOST:-192.168.0.153}"
PI_USER="${PI_USER:-lucas}"
PI_PASS="${PI_PASS:-lucas}"
PI_SERVICE="${PI_SERVICE:-can-cluster.service}"

SSH_OPTS=(-t -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=10)
export SSHPASS="$PI_PASS"

ARG="${1:-}"
if [ "$ARG" = "gpio" ]; then
  REMOTE="journalctl -u $PI_SERVICE -f -g '\\[gpio\\]'"
elif [ "$ARG" = "canrt" ] || [ "$ARG" = "can" ]; then
  REMOTE="journalctl -u $PI_SERVICE -f -g '\\[canrt\\]'"
elif [ -z "$ARG" ] || [ "$ARG" = "-f" ] || [ "$ARG" = "follow" ]; then
  REMOTE="journalctl -u $PI_SERVICE -f"
elif [[ "$ARG" =~ ^[0-9]+$ ]]; then
  REMOTE="journalctl -u $PI_SERVICE -n $ARG --no-pager"
else
  REMOTE="journalctl -u $PI_SERVICE $*"
fi

command -v sshpass >/dev/null 2>&1 || {
  echo "ERROR: sshpass not found (macOS: brew install sshpass)." >&2; exit 1; }

exec sshpass -e ssh "${SSH_OPTS[@]}" "$PI_USER@$PI_HOST" "$REMOTE"
