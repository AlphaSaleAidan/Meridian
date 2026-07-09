#!/usr/bin/env bash
# Meridian Vision Agent — one-command installer for Linux (systemd) and macOS (launchd).
# Installs the frozen agent bundle as a boot service and writes the pairing config.
#
# Usage (run as root/sudo):
#   sudo ./install-unix.sh <PAIRING_CODE> [MERIDIAN_API]
# or set MERIDIAN_PAIRING_CODE in the environment and run with no args.
set -euo pipefail

API="${2:-${MERIDIAN_API:-https://api.meridian.tips}}"
CODE="${1:-${MERIDIAN_PAIRING_CODE:-}}"

if [ "$(id -u)" -ne 0 ]; then
  echo "Please run as root (sudo)." >&2
  exit 1
fi
if [ -z "$CODE" ]; then
  printf "Paste the pairing code from the portal 'Connect cameras' wizard: "
  read -r CODE
fi
if [ -z "$CODE" ]; then
  echo "No pairing code provided." >&2
  exit 2
fi

# The installer script sits next to the unpacked 'meridian-agent' bundle dir.
HERE="$(cd "$(dirname "$0")" && pwd)"
BUNDLE_SRC="$HERE/meridian-agent"
if [ ! -d "$BUNDLE_SRC" ]; then
  echo "Bundle not found next to installer ($BUNDLE_SRC). Unpack the release first." >&2
  exit 3
fi

OS="$(uname -s)"
case "$OS" in
  Linux)
    INSTALL_DIR=/opt/meridian-agent
    CONF_DIR=/etc/meridian
    ;;
  Darwin)
    INSTALL_DIR=/usr/local/meridian-agent
    CONF_DIR=/usr/local/etc/meridian
    ;;
  *) echo "Unsupported OS: $OS" >&2; exit 4 ;;
esac

echo "Installing to $INSTALL_DIR ..."
rm -rf "$INSTALL_DIR"
mkdir -p "$INSTALL_DIR" "$CONF_DIR"
cp -R "$BUNDLE_SRC/." "$INSTALL_DIR/"
chmod +x "$INSTALL_DIR/meridian-agent" 2>/dev/null || true

umask 077
cat > "$CONF_DIR/agent.conf" <<EOF
# Meridian Vision Agent config — keep private.
MERIDIAN_PAIRING_CODE=$CODE
MERIDIAN_API=$API
EOF
echo "Wrote $CONF_DIR/agent.conf"

if [ "$OS" = "Linux" ]; then
  install -m 0644 "$HERE/linux/meridian-agent.service" /etc/systemd/system/meridian-agent.service
  systemctl daemon-reload
  systemctl enable --now meridian-agent
  echo "Service started. Logs: journalctl -u meridian-agent -f"
else
  mkdir -p /usr/local/var/log
  install -m 0644 "$HERE/macos/com.meridian.agent.plist" /Library/LaunchDaemons/com.meridian.agent.plist
  launchctl unload /Library/LaunchDaemons/com.meridian.agent.plist 2>/dev/null || true
  launchctl load -w /Library/LaunchDaemons/com.meridian.agent.plist
  echo "Daemon loaded. Logs: tail -f /usr/local/var/log/meridian-agent.log"
fi

echo "Done. Cameras should appear in your Meridian portal within a minute."
