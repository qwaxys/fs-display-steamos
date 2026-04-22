#!/bin/bash
set -e

INSTALL_DIR="$HOME/fs-display-steamos"
REPO_URL="https://github.com/qwaxys/fs-display-steamos.git"
LIB_REPO_URL="https://github.com/mathoudebine/turing-smart-screen-python.git"

echo "=== WeAct FS Display Installer ==="

# Check for required system packages
MISSING=""
command -v python3 >/dev/null 2>&1 || MISSING="$MISSING python"
command -v git >/dev/null 2>&1 || MISSING="$MISSING git"
python3 -c "import venv" 2>/dev/null || MISSING="$MISSING python-virtualenv"

if [ -n "$MISSING" ]; then
    echo "Installing missing packages:$MISSING"
    sudo steamos-readonly disable
    sudo pacman -Sy --noconfirm $MISSING
    sudo steamos-readonly enable
fi

# Clone or update the project
if [ -d "$INSTALL_DIR/.git" ]; then
    echo "Updating existing installation..."
    cd "$INSTALL_DIR"
    git pull
else
    echo "Cloning project..."
    git clone "$REPO_URL" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

# Clone or update the display library
if [ -d "$INSTALL_DIR/lib/.git" ]; then
    echo "Updating display library..."
    cd "$INSTALL_DIR/lib"
    git pull
    cd "$INSTALL_DIR"
else
    echo "Cloning display library..."
    git clone "$LIB_REPO_URL" "$INSTALL_DIR/lib"
fi

# Create venv and install Python dependencies
echo "Setting up Python environment..."
python3 -m venv "$INSTALL_DIR/venv"
"$INSTALL_DIR/venv/bin/pip" install --upgrade pip
"$INSTALL_DIR/venv/bin/pip" install pyserial Pillow numpy psutil

# Update service file with correct user and paths
echo "Configuring service..."
CURRENT_USER=$(whoami)
sed -e "s|User=deck|User=$CURRENT_USER|" \
    -e "s|/home/deck/fs-display-steamos|$INSTALL_DIR|g" \
    "$INSTALL_DIR/config/weact-display.service" > /tmp/weact-display.service

# Install system files (requires root)
echo "Installing system files (sudo required)..."
sudo steamos-readonly disable

sudo cp "$INSTALL_DIR/config/weact-display.rules" /etc/udev/rules.d/
sudo cp /tmp/weact-display.service /etc/systemd/system/
rm /tmp/weact-display.service

# Preserve files across SteamOS updates
sudo mkdir -p /etc/atomic-update.conf.d
sudo cp "$INSTALL_DIR/config/fs-display-keep.conf" /etc/atomic-update.conf.d/

sudo steamos-readonly enable

# Add user to dialout group for serial access
if ! groups "$CURRENT_USER" | grep -q dialout; then
    echo "Adding $CURRENT_USER to dialout group..."
    sudo usermod -aG dialout "$CURRENT_USER"
    echo "NOTE: Log out and back in for group change to take effect."
fi

# Reload and enable
sudo udevadm control --reload-rules
sudo systemctl daemon-reload

echo ""
echo "=== Installation complete ==="
echo "Plug in the display and it will start automatically."
echo "Manual commands:"
echo "  sudo systemctl start weact-display    # start now"
echo "  sudo systemctl status weact-display   # check status"
echo "  sudo systemctl stop weact-display     # stop"
