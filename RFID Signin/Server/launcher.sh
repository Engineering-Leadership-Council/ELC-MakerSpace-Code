#!/bin/bash

# Configuration
# Resolves to the directory where this script is located (RFID Signin/Server)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
# Repo root is 2 levels up from RFID Signin/Server
REPO_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
SERVER_SCRIPT="$SCRIPT_DIR/rpi_rfid_server.py"
LOG_FILE="$SCRIPT_DIR/launcher.log"

echo "--- RFID Server Launcher Started: $(date) ---" | tee -a "$LOG_FILE"
echo "Script Dir: $SCRIPT_DIR" | tee -a "$LOG_FILE"
echo "Repo Root: $REPO_ROOT" | tee -a "$LOG_FILE"

# Function to wait for internet
wait_for_internet() {
    echo "Waiting for internet..." | tee -a "$LOG_FILE"
    max_retries=60 # Wait up to 2 minutes
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
    # Only try to pull if we have internet
    if wait_for_internet; then
        echo "Checking for updates (git pull)..." | tee -a "$LOG_FILE"
        cd "$REPO_ROOT" || { echo "Failed to cd to $REPO_ROOT"; exit 1; }
        
        # Capture output to log
        if git pull >> "$LOG_FILE" 2>&1; then
             echo "Git pull completed." | tee -a "$LOG_FILE"
        else
             echo "Git pull failed." | tee -a "$LOG_FILE"
        fi
        
        # Return to script dir just in case
        cd "$SCRIPT_DIR"
    else
        echo "Skipping update check (offline)." | tee -a "$LOG_FILE"
    fi

    # 2. Launch Server with Timeout
    if [ -f "$SERVER_SCRIPT" ]; then
        echo "Starting Server with 6h timeout..." | tee -a "$LOG_FILE"
        
        # Run python script with a 6-hour timeout (21600 seconds)
        # We use 'timeout' command. It sends SIGTERM by default.
        timeout --preserve-status 21600s python3 "$SERVER_SCRIPT"
        
        EXIT_CODE=$?
        
        if [ $EXIT_CODE -eq 124 ]; then
            echo "Server reached 6h time limit. Restarting..." | tee -a "$LOG_FILE"
        else
            echo "Server exited (Code: $EXIT_CODE). Restarting in 5s..." | tee -a "$LOG_FILE"
            sleep 5
        fi
    else
        echo "CRITICAL: Server script not found at $SERVER_SCRIPT!" | tee -a "$LOG_FILE"
        echo "Retrying in 60 seconds..." | tee -a "$LOG_FILE"
        sleep 60
    fi
done
