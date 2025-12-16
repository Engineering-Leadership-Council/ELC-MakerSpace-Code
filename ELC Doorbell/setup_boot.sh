#!/bin/bash

# setup_boot.sh
# This script sets up the pi_doorbell.py script to run automatically on boot using systemd.

# Define variables
SERVICE_NAME="doorbell.service"
SCRIPT_NAME="pi_doorbell.py"
USER_NAME=$(whoami)
WORK_DIR=$(pwd)
SCRIPT_PATH="$WORK_DIR/$SCRIPT_NAME"
PYTHON_PATH=$(which python3)

# Check if the python script exists
if [ ! -f "$SCRIPT_PATH" ]; then
    echo "Error: $SCRIPT_NAME not found in the current directory."
    echo "Please make sure you are in the same directory as $SCRIPT_NAME."
    exit 1
fi

# --- INSTALL DEPENDENCIES ---
echo "Installing dependencies..."
sudo apt-get update
sudo apt-get install -y python3-gpiozero python3-requests
# ----------------------------

echo "Setting up $SERVICE_NAME..."
echo "User: $USER_NAME"
echo "Script: $SCRIPT_PATH"
echo "Python: $PYTHON_PATH"

# --- CLEANUP START ---
echo "Cleaning up any existing $SERVICE_NAME..."
# Stop the service if it's running (ignore errors if it doesn't exist)
sudo systemctl stop $SERVICE_NAME 2>/dev/null || true
# Disable the service
sudo systemctl disable $SERVICE_NAME 2>/dev/null || true
# Remove the service file
if [ -f "/etc/systemd/system/$SERVICE_NAME" ]; then
    sudo rm "/etc/systemd/system/$SERVICE_NAME"
    echo "Removed old service file."
fi
# Reload daemon to apply removal
sudo systemctl daemon-reload

# Check for other common startup methods and WARN the user
if grep -q "$SCRIPT_NAME" /etc/rc.local 2>/dev/null; then
    echo "WARNING: Found $SCRIPT_NAME in /etc/rc.local. You should remove it to avoid running twice."
fi
if crontab -l 2>/dev/null | grep -q "$SCRIPT_NAME"; then
    echo "WARNING: Found $SCRIPT_NAME in user crontab. You should remove it to avoid running twice."
fi
# --- CLEANUP END ---

# Create the systemd service file
# We use 'sudo tee' to write to /etc/systemd/system/ which requires root privileges
sudo tee /etc/systemd/system/$SERVICE_NAME > /dev/null <<EOF
[Unit]
Description=Doorbell Python Script
After=network.target

[Service]
ExecStart=$PYTHON_PATH -u $SCRIPT_PATH
WorkingDirectory=$WORK_DIR
StandardOutput=inherit
StandardError=inherit
Restart=always
User=$USER_NAME

[Install]
WantedBy=multi-user.target
EOF

echo "Service file created at /etc/systemd/system/$SERVICE_NAME"

# Reload systemd to recognize the new service
echo "Reloading systemd daemon..."
sudo systemctl daemon-reload

# Enable the service to start on boot
echo "Enabling $SERVICE_NAME to start on boot..."
sudo systemctl enable $SERVICE_NAME

# Start the service immediately
echo "Starting $SERVICE_NAME now..."
sudo systemctl start $SERVICE_NAME

# Check status
echo "Checking service status..."
sudo systemctl status $SERVICE_NAME --no-pager

echo "---------------------------------------------------"
echo "Setup Complete!"
echo "The doorbell script is now running and will start automatically on reboot."
echo "To check logs: sudo journalctl -u $SERVICE_NAME -f"
echo "To stop: sudo systemctl stop $SERVICE_NAME"
echo "---------------------------------------------------"
