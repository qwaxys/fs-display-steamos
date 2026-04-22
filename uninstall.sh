#!/bin/bash
set -e

INSTALL_DIR="$HOME/fs-display-steamos"

echo "=== WeAct FS Display Uninstaller ==="

echo "Stopping service..."
sudo systemctl stop weact-display 2>/dev/null || true

echo "Removing system files (sudo required)..."
sudo steamos-readonly disable

sudo rm -f /etc/udev/rules.d/weact-display.rules
sudo rm -f /etc/systemd/system/weact-display.service
sudo rm -f /etc/atomic-update.conf.d/fs-display-keep.conf

sudo steamos-readonly enable

sudo udevadm control --reload-rules
sudo systemctl daemon-reload

echo "Removing installation directory..."
rm -rf "$INSTALL_DIR"

echo ""
echo "=== Uninstall complete ==="
