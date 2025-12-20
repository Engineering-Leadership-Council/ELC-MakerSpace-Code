#!/bin/bash

echo "--- ELC MakerSpace RFID Server Setup (AutoExec V2) ---"

# 1. Install Dependencies
echo "[1/3] Installing Python Libraries..."
if command -v pip3 &> /dev/null; then
    sudo pip3 install mfrc522 adafruit-circuitpython-neopixel RPi.GPIO --break-system-packages || sudo pip3 install mfrc522 adafruit-circuitpython-neopixel RPi.GPIO
else
    echo "pip3 not found. Installing python3-pip..."
    sudo apt-get update
    sudo apt-get install -y python3-pip
    sudo pip3 install mfrc522 adafruit-circuitpython-neopixel RPi.GPIO --break-system-packages || sudo pip3 install mfrc522 adafruit-circuitpython-neopixel RPi.GPIO
fi

# 2. Determine Paths
# Assumes this script is in the same directory as launcher.sh
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
LAUNCHER_SCRIPT="$SCRIPT_DIR/launcher.sh"
SERVICE_FILE="/etc/systemd/system/rfid_server_v2.service"

echo "Detected Launcher Path: $LAUNCHER_SCRIPT"

# Make launcher executable
chmod +x "$LAUNCHER_SCRIPT"

# 3. Create Systemd Service
echo "[2/3] Configuring Startup Service..."
sudo bash -c "cat > $SERVICE_FILE" <<EOF
[Unit]
Description=ELC RFID Server V2 (Auto-Update)
After=network-online.target
Wants=network-online.target

[Service]
ExecStart=/bin/bash "$LAUNCHER_SCRIPT"
WorkingDirectory=$SCRIPT_DIR
StandardOutput=journal
StandardError=journal
Restart=always
# Root is required for GPIO/NeoPixel access
User=root

[Install]
WantedBy=multi-user.target
EOF

# 4. Enable and Start
echo "[3/3] Enabling and Starting Service..."
sudo systemctl daemon-reload
sudo systemctl enable rfid_server_v2.service
sudo systemctl restart rfid_server_v2.service

echo "----------------------------------------"
echo "Setup Complete!"
echo "Check status with: sudo systemctl status rfid_server_v2.service"
echo "View logs with:    sudo journalctl -u rfid_server_v2.service -f"
echo "----------------------------------------"
