#!/bin/bash

# Configuration
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
TARGET_FILE="$SCRIPT_DIR/rpi_rfid_server.py"
LOG_FILE="$SCRIPT_DIR/launcher.log"

echo "--- RFID Server Launcher Started: $(date) ---" | tee -a "$LOG_FILE"

# Function to wait for internet
wait_for_internet() {
    echo "Waiting for internet..." | tee -a "$LOG_FILE"
    max_retries=30
    count=0
    while ! ping -c 1 -W 1 google.com &> /dev/null; do
        echo "Waiting for network... ($count/$max_retries)" | tee -a "$LOG_FILE"
        sleep 2
        ((count++))
        if [ $count -ge $max_retries ]; then
            echo "Network timed out. Proceeding offline..." | tee -a "$LOG_FILE"
            return 1
        fi
    done
    echo "Network connected." | tee -a "$LOG_FILE"
    return 0
}

# Main Loop
while true; do
    echo "--- Starting Lifecycle Loop ---" | tee -a "$LOG_FILE"
    
    # 1. Update Check (Git Pull)
    if wait_for_internet; then
        echo "Checking for updates (git pull)..." | tee -a "$LOG_FILE"
        cd "$SCRIPT_DIR"
        
        # Capture output to log
        if git pull >> "$LOG_FILE" 2>&1; then
             echo "Git pull completed." | tee -a "$LOG_FILE"
        else
             echo "Git pull failed." | tee -a "$LOG_FILE"
        fi
    else
        echo "Skipping update check (offline)." | tee -a "$LOG_FILE"
    fi

    # 2. Launch Server
    if [ -f "$TARGET_FILE" ]; then
        echo "Starting Server..." | tee -a "$LOG_FILE"
        
        # Run the server. It will block here until the server exits.
        python3 "$TARGET_FILE"
        
        EXIT_CODE=$?
        echo "Server exited with code $EXIT_CODE." | tee -a "$LOG_FILE"
        
        # If server exited intentionally (e.g. for update), we loop and restart.
        # If it crashed, we also loop and restart, but maybe add a delay.
        echo "Restarting in 5 seconds..." | tee -a "$LOG_FILE"
        sleep 5
    else
        echo "CRITICAL: Server script not found at $TARGET_FILE!" | tee -a "$LOG_FILE"
        echo "Retrying in 60 seconds..." | tee -a "$LOG_FILE"
        sleep 60
    fi
done
