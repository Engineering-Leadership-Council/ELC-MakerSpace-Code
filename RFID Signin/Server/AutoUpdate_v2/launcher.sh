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
    
    # Try downloading with wget first
    echo "Attempting download with wget from: $REPO_URL" | tee -a "$LOG_FILE"
    wget -O "$TARGET_FILE" "$REPO_URL" 2>> "$LOG_FILE"
    
    # If wget failed, try curl
    if [ $? -ne 0 ]; then
        echo "wget failed. Attempting download with curl..." | tee -a "$LOG_FILE"
        curl -L -o "$TARGET_FILE" "$REPO_URL" 2>> "$LOG_FILE"
        
        if [ $? -ne 0 ]; then
            echo "ERROR: Both wget and curl failed to download update." | tee -a "$LOG_FILE"
            echo "Detailed error info should be above (in $LOG_FILE)." | tee -a "$LOG_FILE"
        else
            echo "Download successful (via curl)." | tee -a "$LOG_FILE"
        fi
    else
        echo "Download successful (via wget)." | tee -a "$LOG_FILE"
    fi
else
    echo "No internet connection (ping google.com failed). Skipping update." | tee -a "$LOG_FILE"
fi

# 3. Launch Server
if [ -f "$TARGET_FILE" ]; then
    echo "Starting Server..." | tee -a "$LOG_FILE"
    python3 "$TARGET_FILE"
else
    echo "CRITICAL: Server script not found!" | tee -a "$LOG_FILE"
fi
