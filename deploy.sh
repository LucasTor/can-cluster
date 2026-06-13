#!/usr/bin/env bash
#
# deploy.sh — push this repo to the can-cluster Raspberry Pi and manage its
# read-only (overlay) root filesystem.
#
# Why read-only: in the car the Pi loses power the instant the ignition is cut.
# An ext4 root mounted read-write can corrupt on an unclean power loss. Armbian's
# overlay root (the `overlayroot` package) mounts the real SD card read-only and
# sends all writes to a tmpfs in RAM, which is simply discarded on power loss —
# so the system can never be corrupted by yanking power.
#
# How the toggle works: the overlay is switched on/off purely by the presence of
# an `overlayroot=tmpfs` token in /boot/firmware/cmdline.txt. That file lives on
# the FAT firmware partition, which is ALWAYS mounted read-write (it is never part
# of the overlay), so we can flip the mode from either state and it always sticks.
# A reboot is required for a change to take effect. If a deploy ever leaves the Pi
# unbootable, you can recover by mounting the SD card's boot partition on any
# computer and deleting the `overlayroot=tmpfs` token from cmdline.txt.
#
# Usage:
#   ./deploy.sh             Full deploy: make writable -> copy files -> read-only
#   ./deploy.sh --rw        Just switch the Pi to read-WRITE (for manual work)
#   ./deploy.sh --ro        Just switch the Pi to read-ONLY
#   ./deploy.sh --no-ro     Deploy files but leave the Pi writable (iterating)
#   ./deploy.sh --status    Report current filesystem mode and exit
#
# Connection settings (override via environment if they change):
#   PI_HOST=192.168.0.153 PI_USER=lucas PI_PASS=lucas ./deploy.sh
#
# NOTE: the password is used via sshpass for convenience. For a hardened setup,
# copy an SSH key (ssh-copy-id) and the sshpass calls become passwordless.

set -euo pipefail

PI_HOST="${PI_HOST:-192.168.0.153}"
PI_USER="${PI_USER:-lucas}"
PI_PASS="${PI_PASS:-lucas}"
PI_DEST="${PI_DEST:-/home/lucas/can-cluster}"
PI_LAUNCHER="${PI_LAUNCHER:-/usr/local/bin/start-can-cluster.sh}"
PI_SERVICE="${PI_SERVICE:-can-cluster.service}"
REBOOT_WAIT="${REBOOT_WAIT:-240}"   # seconds to wait for the Pi to come back

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SSH_OPTS=(-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=10)

export SSHPASS="$PI_PASS"

# --- low-level helpers -------------------------------------------------------

# Run ssh, retrying ONLY on connection/auth failures (ssh exit code 255).
# A reboot leaves sshd briefly unavailable and a burst of reconnects can get a
# transient "Permission denied", so we retry those; a real remote command exit
# code (anything other than 255) is returned as-is.
_ssh() {
  local tries=0 rc=0
  while :; do
    sshpass -e ssh "${SSH_OPTS[@]}" "$PI_USER@$PI_HOST" "$@"
    rc=$?
    [ "$rc" -ne 255 ] && return "$rc"
    tries=$((tries + 1))
    [ "$tries" -ge 6 ] && return "$rc"
    echo "  (ssh connection hiccup, retry $tries/6)" >&2
    sleep 5
  done
}

# Run a command on the Pi as the normal user; stdout/exit code propagate.
pi() { _ssh "$@"; }

# Run a bash script (read from stdin) on the Pi as root. Robust against sudo
# credential caching (the password is the only thing on sudo's stdin) and against
# transient ssh failures (the whole staged-and-run unit is retried on exit 255).
# The remote scripts must be idempotent, since a retry may re-run them.
pi_sudo() {
  local script tries=0 rc=0 remote
  script="$(cat)"
  while :; do
    remote="/tmp/.deploy.$$.$RANDOM.sh"
    printf '%s' "$script" | sshpass -e ssh "${SSH_OPTS[@]}" "$PI_USER@$PI_HOST" "cat > $remote" \
      && printf '%s\n' "$PI_PASS" | sshpass -e ssh "${SSH_OPTS[@]}" "$PI_USER@$PI_HOST" \
           "sudo -S -p '' bash $remote; r=\$?; rm -f $remote; exit \$r"
    rc=$?
    [ "$rc" -eq 0 ] && return 0
    [ "$rc" -ne 255 ] && return "$rc"
    tries=$((tries + 1))
    [ "$tries" -ge 6 ] && return "$rc"
    echo "  (ssh connection hiccup, retry $tries/6)" >&2
    sleep 5
  done
}

# Return 0 if the overlay (read-only) root is currently active.
overlay_active() { pi 'findmnt -nro FSTYPE / | grep -qx overlay'; }

# The kernel boot_id is a fresh random UUID every boot — we use it to confirm a
# reboot genuinely happened (rather than just seeing the still-up Pi answer).
_boot_id() { sshpass -e ssh "${SSH_OPTS[@]}" -o ConnectTimeout=5 "$PI_USER@$PI_HOST" \
               'cat /proc/sys/kernel/random/boot_id' 2>/dev/null; }

# Reboot the Pi and block until it has actually rebooted and ssh is back.
reboot_and_wait() {
  local before after t=0
  before="$(_ssh 'cat /proc/sys/kernel/random/boot_id')"
  echo "  rebooting (boot_id ${before:0:8}...); ensuring it goes down..."
  while [ "$t" -lt 4 ]; do
    printf '%s\n' "$PI_PASS" \
      | sshpass -e ssh "${SSH_OPTS[@]}" "$PI_USER@$PI_HOST" "sudo -S -p '' systemctl reboot" 2>/dev/null || true
    sleep 4
    sshpass -e ssh "${SSH_OPTS[@]}" -o ConnectTimeout=4 "$PI_USER@$PI_HOST" true 2>/dev/null || break
    t=$((t + 1))
  done
  echo "  waiting for $PI_HOST to come back (up to ${REBOOT_WAIT}s)..."
  sleep 12
  local deadline=$(( $(date +%s) + REBOOT_WAIT ))
  while [ "$(date +%s)" -lt "$deadline" ]; do
    after="$(_boot_id || true)"
    if [ -n "$after" ] && [ "$after" != "$before" ]; then
      echo "  back online (boot_id ${after:0:8}...)."; return 0
    fi
    printf '.'; sleep 5
  done
  echo ""; echo "ERROR: Pi did not reboot/return within ${REBOOT_WAIT}s." >&2; return 1
}

require_sshpass() {
  command -v sshpass >/dev/null 2>&1 || {
    echo "ERROR: sshpass not found. Install it (macOS: brew install sshpass)." >&2; exit 1; }
}

# --- read-only toggle (via /boot/firmware/cmdline.txt) -----------------------

# Remote snippet: ensure the overlayroot package is installed (provides the
# initramfs hook that reads the cmdline token). Safe to run repeatedly.
ensure_overlay_pkg() {
  pi_sudo <<'EOF'
set -e
if ! command -v overlayroot-chroot >/dev/null 2>&1; then
  export DEBIAN_FRONTEND=noninteractive
  apt-get update -qq || true
  apt-get install -y -o Dpkg::Options::="--force-confold" overlayroot cryptsetup cryptsetup-bin
fi
EOF
}

set_readonly() {  # add overlayroot=tmpfs to cmdline.txt
  pi_sudo <<'EOF'
set -e
CL=/boot/firmware/cmdline.txt
cp -n "$CL" "$CL.bak" || true
line=$(cat "$CL")
line=$(printf '%s' "$line" | sed -E 's/[[:space:]]*overlayroot=[^[:space:]]*//g')
line="$line overlayroot=tmpfs"
line=$(printf '%s' "$line" | tr -s ' ' | sed 's/^ //; s/ *$//')
printf '%s\n' "$line" > "$CL"
sync
[ "$(wc -l < "$CL")" = "1" ] || { echo "ERROR: cmdline.txt is not a single line" >&2; exit 1; }
grep -q 'overlayroot=tmpfs' "$CL"
echo "cmdline.txt -> $(cat "$CL")"
EOF
}

clear_readonly() {  # remove any overlayroot token from cmdline.txt
  pi_sudo <<'EOF'
set -e
CL=/boot/firmware/cmdline.txt
cp -n "$CL" "$CL.bak" || true
line=$(cat "$CL")
line=$(printf '%s' "$line" | sed -E 's/[[:space:]]*overlayroot=[^[:space:]]*//g')
line=$(printf '%s' "$line" | tr -s ' ' | sed 's/^ //; s/ *$//')
printf '%s\n' "$line" > "$CL"
sync
[ "$(wc -l < "$CL")" = "1" ] || { echo "ERROR: cmdline.txt is not a single line" >&2; exit 1; }
! grep -q 'overlayroot=' "$CL"
echo "cmdline.txt -> $(cat "$CL")"
EOF
}

make_writable() {
  if overlay_active; then
    echo "==> Root is read-only. Switching to writable and rebooting..."
    clear_readonly
    reboot_and_wait
    if overlay_active; then echo "ERROR: still read-only after reboot." >&2; exit 1; fi
    echo "==> Root is now writable."
  else
    echo "==> Root is already writable."
  fi
}

make_readonly() {
  echo "==> Enabling read-only overlay and rebooting..."
  ensure_overlay_pkg
  set_readonly
  reboot_and_wait
  if overlay_active; then
    echo "==> Read-only overlay is ACTIVE. The SD card is now protected from power loss."
  else
    echo "ERROR: overlay not active after reboot." >&2; exit 1
  fi
}

# --- file deploy -------------------------------------------------------------

deploy_files() {
  echo "==> Syncing files to $PI_HOST:$PI_DEST ..."
  # Stage to a user-writable temp dir (no sudo needed for the network copy).
  # Retry on transient ssh failures (exit 255), same as the other helpers.
  local tries=0
  while :; do
    rsync -az --delete \
      --exclude '.git/' --exclude '__pycache__/' --exclude '*.pyc' --exclude '.DS_Store' \
      -e "sshpass -e ssh ${SSH_OPTS[*]}" \
      "$SCRIPT_DIR"/ "$PI_USER@$PI_HOST:/tmp/can-cluster-stage/" && break
    rc=$?
    tries=$((tries + 1))
    if [ "$tries" -ge 4 ]; then echo "ERROR: rsync failed (rc=$rc)" >&2; return "$rc"; fi
    echo "  (rsync hiccup, retry $tries/4)" >&2; sleep 5
  done

  # Move into place as root, preserving the existing .git directory, then make
  # sure the launcher runs in production mode (DEV=false) and restart the app.
  pi_sudo <<EOF
set -e
mkdir -p "$PI_DEST"
rsync -a --delete --exclude '.git/' /tmp/can-cluster-stage/ "$PI_DEST"/
chown -R root:root "$PI_DEST"
rm -rf /tmp/can-cluster-stage

# Production mode: DEV=false disables the keyboard-demo loop and uses the full
# window. Without this the app runs in dev mode and the demo fights real data.
L="$PI_LAUNCHER"
if [ -f "\$L" ]; then
  if grep -q '^export DEV=' "\$L"; then
    sed -i 's/^export DEV=.*/export DEV=false/' "\$L"
  else
    sed -i '1a export DEV=false' "\$L"
  fi
fi

systemctl restart "$PI_SERVICE" || true
echo "files deployed; $PI_SERVICE restarted"
EOF
}

print_status() {
  if overlay_active; then
    echo "Filesystem mode: READ-ONLY (overlay active) — safe to cut power."
  else
    echo "Filesystem mode: read-write — NOT power-loss safe."
  fi
}

# --- main --------------------------------------------------------------------

require_sshpass

case "${1:-}" in
  --status)
    print_status
    ;;
  --rw)
    make_writable
    print_status
    ;;
  --ro)
    make_readonly
    print_status
    ;;
  --no-ro)
    make_writable
    deploy_files
    echo "==> Done. Pi left WRITABLE (run './deploy.sh --ro' when finished iterating)."
    print_status
    ;;
  ""|--deploy)
    make_writable
    deploy_files
    make_readonly
    echo "==> Deploy complete."
    print_status
    ;;
  -h|--help)
    sed -n '2,40p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
    ;;
  *)
    echo "Unknown option: $1" >&2
    echo "Try: ./deploy.sh --help" >&2
    exit 1
    ;;
esac
