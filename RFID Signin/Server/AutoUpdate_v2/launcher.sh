#!/bin/bash

# Configuration
REPO_URL="https://raw.githubusercontent.com/Engineering-Leadership-Council/ELC-MakerSpace-Code/main/RFID%20Signin/Server/rpi_rfid_server.py"
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
TARGET_FILE="$SCRIPT_DIR/rpi_rfid_server.py"
LOG_FILE="$SCRIPT_DIR/launcher.log"

echo "--- RFID Server Launcher Started: $(date) ---" | tee -a "$LOG_FILE"

# 1. Wait for Internet Connection
echo "Waiting for internet..." | tee -a "$LOG_FILE"
max_retries=30
count=0
while ! ping -c 1 -W 1 google.com &> /dev/null; do
    echo "Waiting for network... ($count/$max_retries)" | tee -a "$LOG_FILE"
    sleep 2
    ((count++))
    if [ $count -ge $max_retries ]; then
        echo "Network timed out. proceeding without update..." | tee -a "$LOG_FILE"
        break
    fi
done

# 2. Update Process
if ping -c 1 -W 1 google.com &> /dev/null; then
    echo "Network connected. Checking for updates..." | tee -a "$LOG_FILE"
    
    # Check if we can reach the repo
    if wget --spider --quiet "$REPO_URL"; then
        echo "Update found. Removing old file..." | tee -a "$LOG_FILE"
        rm -f "$TARGET_FILE"
        
        echo "Downloading new version..." | tee -a "$LOG_FILE"
        wget -O "$TARGET_FILE" "$REPO_URL"
        
        if [ $? -eq 0 ]; then
            echo "Download successful." | tee -a "$LOG_FILE"
        else
            echo "Download failed! (wget error)" | tee -a "$LOG_FILE"
        fi
    else
        echo "Cannot reach GitHub repo. Skipping update." | tee -a "$LOG_FILE"
    fi
else
    echo "No internet connection. Skipping update." | tee -a "$LOG_FILE"
fi

# 3. Launch Server
if [ -f "$TARGET_FILE" ]; then
    echo "Starting Server..." | tee -a "$LOG_FILE"
    python3 "$TARGET_FILE"
else
    echo "CRITICAL: Server script not found!" | tee -a "$LOG_FILE"
fi
