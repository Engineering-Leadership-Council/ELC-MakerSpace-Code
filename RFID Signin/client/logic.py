import os
import json
import threading
import requests
import pyttsx3
import csv
import datetime
from pathlib import Path
from .config import DISCORD_WEBHOOK_URL, BACKUP_CSV, OFFICER_DATA_JSON

class OfficerManager:
    def __init__(self):
        self.officers = []
        self.load_officers()
        try:
            self.tts_engine = pyttsx3.init()
        except:
            print("TTS Init Failed")
            self.tts_engine = None

    def load_officers(self):
        try:
            self.officers = json.loads(OFFICER_DATA_JSON)
        except json.JSONDecodeError:
            print("Failed to parse OFFICER_DATA from environment")
            self.officers = []


    def check_and_welcome(self, email):
        for officer in self.officers:
            if officer.get("email") == email:
                self.trigger_officer_welcome(officer)
                return True
        return False

    def trigger_officer_welcome(self, officer):
        # 1. TTS Welcome
        title = officer.get("title", "")
        name = officer.get("name", "")
        
        welcome_text = f"Welcome {title} {name}"
        print(f"Speaking: {welcome_text}")
        
        if self.tts_engine:
            try:
                threading.Thread(target=self._speak, args=(welcome_text,), daemon=True).start()
            except Exception as e:
                print(f"TTS Error: {e}")

        # 2. Discord Ping
        discord_msg = officer.get("discord_message", "")
        if discord_msg and DISCORD_WEBHOOK_URL:
             threading.Thread(target=self._send_discord, args=(discord_msg,), daemon=True).start()

    def _speak(self, text):
        try:
            # Re-init in thread to be safe if the global one fails
            engine = pyttsx3.init()
            engine.say(text)
            engine.runAndWait()
        except Exception as e:
            print(f"Thread TTS Error: {e}")

    def _send_discord(self, message):
        try:
            payload = {"content": message, "username": "Doorbell Access"}
            requests.post(DISCORD_WEBHOOK_URL, json=payload)
        except Exception as e:
             print(f"Discord Error: {e}")
    
    def cleanup(self):
        try:
            if self.tts_engine:
                self.tts_engine.stop()
        except: pass

def process_scan_data(data, action):
    # Format expected: email_user,fname,lname,officer
    timestamp = datetime.datetime.now().strftime("%I:%M:%S %p")
    date_str = datetime.datetime.now().strftime("%Y-%m-%d")
    
    parts = data.split(',')
    if len(parts) >= 3:
        email_user = parts[0].strip()
        fname = parts[1].strip()
        lname = parts[2].strip()
        
        if "@" not in email_user:
            email_full = f"{email_user}@student.monroecc.edu"
        else:
            email_full = email_user
        
        parsed_record = {
            "Date": date_str,
            "Time": timestamp,
            "Action": action,
            "First Name": fname,
            "Last Name": lname,
            "Email": email_full,
            "Raw Data": data
        }
    else:
        parsed_record = {
            "Date": date_str,
            "Time": timestamp,
            "Action": action,
            "First Name": "Unknown",
            "Last Name": "Unknown",
            "Email": "N/A",
            "Raw Data": data
        }
        
    return parsed_record

def append_to_backup(record):
    try:
        file_exists = os.path.exists(BACKUP_CSV)
        with open(BACKUP_CSV, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=["Date", "Time", "Action", "First Name", "Last Name", "Email", "Raw Data"])
            if not file_exists:
                writer.writeheader()
            writer.writerow(record)
    except Exception as e:
        print(f"Backup CSV error: {e}")

def export_logs_to_excel(log_data):
    if not log_data:
        return False, "No data to export."

    try:
        import pandas as pd
        
        now = datetime.datetime.now()
        year_folder = now.strftime("%Y")
        month_folder = now.strftime("%B") 
        date_file_name = now.strftime("%d_attendance.xlsx")

        base_path = Path("logs")
        full_path = base_path / year_folder / month_folder
        full_path.mkdir(parents=True, exist_ok=True)
        
        file_path = full_path / date_file_name

        df = pd.DataFrame(log_data)
        cols = ["Date", "Time", "Action", "First Name", "Last Name", "Email", "Raw Data"]
        df = df[cols]

        df.to_excel(file_path, index=False)
        return True, str(file_path)

    except Exception as e:
        return False, str(e)
