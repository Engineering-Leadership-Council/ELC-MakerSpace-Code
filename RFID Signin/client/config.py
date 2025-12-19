import os

# Try to import dotenv, but don't crash if missing (simpler portability)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # Manual simple parse if dotenv missing
    try:
        if os.path.exists(".env"):
            with open(".env", "r") as f:
                for line in f:
                    if line.strip() and not line.startswith("#") and "=" in line:
                        k, v = line.strip().split("=", 1)
                        os.environ[k] = v
    except:
        pass

# --- Configuration ---
LOG_FILE = "rfid_logs_client.txt"
BACKUP_CSV = "daily_backup.csv"
DEFAULT_PORT = 65432
LAST_IP_FILE = "last_ip.txt"
OFFICERS_FILE = "officers.json"

# Secrets (Load from Env or Default)
ADMIN_PASSCODE = os.getenv("ADMIN_PASSCODE", "1234") 
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")
OFFICER_DATA_JSON = os.getenv("OFFICER_DATA", "[]")
LAST_IP = os.getenv("LAST_IP", "192.168.1.100")


# --- Colors & Styles ---
MCC_GOLD = "#C99700"
MCC_BLACK = "#1A1A1A"  # Main background
HEADER_BLACK = "#000000"  # Header background
TEXT_WHITE = "#F0F0F0"
ERROR_RED = "#FF4444"
SUCCESS_GREEN = "#00C851"
ACTION_BLUE = "#33b5e5"
