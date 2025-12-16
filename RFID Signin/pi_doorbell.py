import tkinter as tk
from tkinter import messagebox, ttk, simpledialog
import socket
import threading
import json
import time
import datetime
import os
import ctypes
import csv
import sys
from pathlib import Path

# --- Configuration ---
LOG_FILE = "rfid_logs_client.txt"
BACKUP_CSV = "daily_backup.csv"
DEFAULT_PORT = 65432
LAST_IP_FILE = "last_ip.txt"
ADMIN_PASSCODE = "1234" # Simple passcode

# --- Colors & Styles ---
MCC_GOLD = "#C99700"
MCC_BLACK = "#1A1A1A"  # Main background
HEADER_BLACK = "#000000"  # Header background
TEXT_WHITE = "#F0F0F0"
ERROR_RED = "#FF4444"
SUCCESS_GREEN = "#00C851"
ACTION_BLUE = "#33b5e5"

class NetworkClient:
    def __init__(self, callback_read, callback_write_result):
        self.socket = None
        self.connected = False
        self.callback_read = callback_read
        self.callback_write_result = callback_write_result
        self.stop_event = threading.Event()

    def connect(self, ip):
        self.disconnect()
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(5)
            self.socket.connect((ip, DEFAULT_PORT))
            self.connected = True
            self.stop_event.clear()
            
            # Start listener thread
            self.thread = threading.Thread(target=self.listen_loop, daemon=True)
            self.thread.start()
            return True, "Connected"
        except Exception as e:
            return False, str(e)

    def disconnect(self):
        self.connected = False
        self.stop_event.set()
        if self.socket:
            try: self.socket.close()
            except: pass
        self.socket = None

    def send_write(self, text):
        if not self.connected:
            return False
        try:
            cmd = {"action": "write", "content": text}
            msg = json.dumps(cmd) + "\n"
            self.socket.sendall(msg.encode('utf-8'))
            return True
        except Exception as e:
            self.disconnect()
            return False

    def listen_loop(self):
        buffer = ""
        while not self.stop_event.is_set():
            try:
                data = self.socket.recv(1024)
                if not data:
                    break # Server closed
                
                buffer += data.decode('utf-8')
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    if not line: continue
                    self.process_msg(line)
            except socket.timeout:
                continue
            except Exception as e:
                print(f"Network Error: {e}")
                break
        
        self.connected = False
        # If we broke out of loop, connection died

    def process_msg(self, line):
        try:
            msg = json.loads(line)
            mtype = msg.get("type")
            
            if mtype == "READ":
                data = msg.get("data", "")
                self.callback_read(data)
            elif mtype == "WRITE_RESULT":
                success = msg.get("success")
                text = msg.get("msg")
                self.callback_write_result(success, text)
                
        except json.JSONDecodeError:
            pass

class RFIDClientApp:
    def __init__(self, root):
        self.root = root
        self.root.title("ELC Doorbell Client")
        self.root.geometry("700x650")
        self.root.configure(bg=MCC_BLACK)
        
        # Apply Windows Dark Title Bar
        try:
            self.root.update()
            # DWMWA_USE_IMMERSIVE_DARK_MODE = 20
            set_window_attribute = ctypes.windll.dwmapi.DwmSetWindowAttribute
            get_parent = ctypes.windll.user32.GetParent
            hwnd = get_parent(self.root.winfo_id())
            value = ctypes.c_int(2)
            set_window_attribute(hwnd, 20, ctypes.byref(value), ctypes.sizeof(value))
        except Exception as e:
            print(f"Failed to set dark title bar: {e}")

        # Set Icon
        try:
            if os.path.exists("icon.png"):
                icon_img = tk.PhotoImage(file="icon.png")
                self.root.iconphoto(False, icon_img)
        except Exception as e:
            print(f"Failed to load icon: {e}")
        
        self.client = NetworkClient(self.on_rfid_read, self.on_write_result)
        self.mode = "READ"
        self.scan_action = "SIGN IN" # Default action
        self.log_data = [] # List to hold dictionaries of daily scans
        self.last_export_date = None

        # Load last IP
        self.last_ip = "192.168.1.100"
        if os.path.exists(LAST_IP_FILE):
            with open(LAST_IP_FILE, "r") as f:
                self.last_ip = f.read().strip()

        self.setup_styles()
        self.setup_ui()
        
        # Check for unsaved backup CSV and load it if needed (optional advanced feature, simplified here)
        # For now, we start fresh memory, but append to backup csv
        
        # Auto-connect silently on startup
        self.root.after(500, self.silent_connect)
        
        # Start Auto-Export Scheduler
        self.check_auto_export()

        # Handle Window Close Explicity
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def on_close(self):
        """ Cleanup threads and connections on exit """
        try:
            if self.client:
                self.client.disconnect()
        except:
            pass
        self.root.destroy()
        sys.exit(0)

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')  # 'clam' allows for better color customization
        
        # General Frame
        style.configure('TFrame', background=MCC_BLACK)
        
        # Labels
        style.configure('TLabel', background=MCC_BLACK, foreground=TEXT_WHITE, font=('Segoe UI', 11))
        style.configure('Header.TLabel', background=HEADER_BLACK, foreground=MCC_GOLD, font=('Segoe UI', 20, 'bold'))
        style.configure('SubHeader.TLabel', background=MCC_BLACK, foreground=MCC_GOLD, font=('Segoe UI', 14, 'bold'))
        style.configure('Status.TLabel', background=HEADER_BLACK, foreground="gray", font=('Segoe UI', 10))
        
        # Buttons
        style.configure('TButton', 
                        font=('Segoe UI', 11, 'bold'), 
                        background=MCC_GOLD, 
                        foreground="black", 
                        borderwidth=0, 
                        focuscolor=MCC_GOLD)
        style.map('TButton', background=[('active', '#FFCA28'), ('disabled', '#555')]) # Lighter gold on hover
        
        # Toggle Button Style (Sign In / Sign Out)
        style.configure('Toggle.TButton', 
                        font=('Segoe UI', 12, 'bold'),
                        background=SUCCESS_GREEN,
                        foreground="white")
        
        # Radiobuttons
        style.configure('TRadiobutton', background=MCC_BLACK, foreground=TEXT_WHITE, font=('Segoe UI', 11))
        style.map('TRadiobutton', indicatorcolor=[('selected', MCC_GOLD)])
        
        # Checkbuttons
        style.configure('TCheckbutton', background=MCC_BLACK, foreground=TEXT_WHITE, font=('Segoe UI', 11))
        style.map('TCheckbutton', indicatorcolor=[('selected', MCC_GOLD)])
        
        # Labelframe
        style.configure('TLabelframe', background=MCC_BLACK, foreground=MCC_GOLD)
        style.configure('TLabelframe.Label', background=MCC_BLACK, foreground=MCC_GOLD, font=('Segoe UI', 10, 'bold'))

    def setup_ui(self):
        # Header
        header_frame = tk.Frame(self.root, bg=HEADER_BLACK, padx=20, pady=15)
        header_frame.pack(fill="x")
        
        # Title with Gold color
        lbl_title = ttk.Label(header_frame, text="ELC MakerSpace RFID", style='Header.TLabel', background=HEADER_BLACK)
        lbl_title.pack(side="left")
        
        # Connection Status
        conn_frame = tk.Frame(header_frame, bg=HEADER_BLACK)
        conn_frame.pack(side="right")
        self.lbl_connection = ttk.Label(conn_frame, text="Disconnected", style='Status.TLabel', foreground=ERROR_RED)
        self.lbl_connection.pack(anchor="e")
        
        # Divider
        tk.Frame(self.root, bg=MCC_GOLD, height=2).pack(fill="x")

        # Mode Selection
        self.mode_frame = ttk.Frame(self.root, padding=(0, 20))
        self.mode_frame.pack()
        
        self.mode_var = tk.StringVar(value="READ")
        
        self.rb_read = ttk.Radiobutton(self.mode_frame, text="READ MODE", variable=self.mode_var, value="READ", command=self.change_mode)
        self.rb_write = ttk.Radiobutton(self.mode_frame, text="ADMIN PANEL", variable=self.mode_var, value="WRITE", command=self.change_mode)
        
        self.rb_read.pack(side="left", padx=30)
        self.rb_write.pack(side="left", padx=30)

        # Content Area
        self.content_frame = ttk.Frame(self.root, padding=20)
        self.content_frame.pack(fill="both", expand=True)

        self.setup_read_view()

    def silent_connect(self):
        if self.last_ip:
            self.lbl_connection.config(text=f"Connecting to {self.last_ip}...", foreground=MCC_GOLD)
            self.root.update()
            success, msg = self.client.connect(self.last_ip)
            if success:
                self.lbl_connection.config(text=f"Connected to {self.last_ip}", foreground=SUCCESS_GREEN)
            else:
                self.lbl_connection.config(text=f"Disconnected", foreground=ERROR_RED)

    def prompt_connection(self):
        ip = simpledialog.askstring("Connect to Pi", "Enter Raspberry Pi IP Address:", initialvalue=self.last_ip)
        if ip:
            self.last_ip = ip
            with open(LAST_IP_FILE, "w") as f:
                f.write(ip)
                
            self.lbl_connection.config(text=f"Connecting to {ip}...", foreground=MCC_GOLD)
            self.root.update()
            
            success, msg = self.client.connect(ip)
            if success:
                self.lbl_connection.config(text=f"Connected to {ip}", foreground=SUCCESS_GREEN)
            else:
                self.lbl_connection.config(text=f"Failed: {msg}", foreground=ERROR_RED)
                messagebox.showerror("Connection Error", f"Could not connect to {ip}.\n{msg}")

    def change_mode(self):
        new_mode = self.mode_var.get()
        
        if new_mode == "WRITE":
            pwd = simpledialog.askstring("Admin Access", "Enter Admin Passcode:", show='*')
            if pwd != ADMIN_PASSCODE:
                messagebox.showerror("Access Denied", "Incorrect passcode.")
                self.mode_var.set("READ")
                return 

        self.mode = new_mode
        for widget in self.content_frame.winfo_children():
            widget.destroy()
            
        if self.mode == "READ":
            self.setup_read_view()
        else:
            self.setup_write_view()

    # --- READ VIEW & LOGIC ---
    def setup_read_view(self):
        center_frame = ttk.Frame(self.content_frame)
        center_frame.pack(expand=True, fill='both')

        # Action Toggle
        self.btn_action = tk.Button(center_frame, text="CURRENTLY: SIGN IN", 
                                    font=('Segoe UI', 14, 'bold'),
                                    bg=SUCCESS_GREEN, fg="white",
                                    command=self.toggle_action,
                                    width=24, height=2, relief="flat")
        self.btn_action.pack(pady=(0, 40))
        
        # Welcome Message Area
        self.lbl_welcome_header = ttk.Label(center_frame, 
                                            text="Welcome to the\nEngineering Leadership Council MakerSpace", 
                                            foreground=MCC_GOLD, 
                                            background=MCC_BLACK,
                                            font=('Segoe UI', 24, 'bold'),
                                            justify="center")
        self.lbl_welcome_header.pack(pady=20)

        # Dynamic Name Label
        self.lbl_name = ttk.Label(center_frame, 
                                  text="Please Scan Card", 
                                  foreground="white", 
                                  background=MCC_BLACK,
                                  font=('Segoe UI', 32, 'bold'),
                                  justify="center")
        self.lbl_name.pack(pady=20)

        # Time/Status Label
        self.lbl_status_msg = ttk.Label(center_frame, 
                                        text="", 
                                        foreground="gray", 
                                        background=MCC_BLACK,
                                        font=('Segoe UI', 18),
                                        justify="center")
        self.lbl_status_msg.pack(pady=10)
        
        ttk.Label(center_frame, text="* Logs auto-export to Excel at 11:59 PM", foreground="gray", font=('Segoe UI', 9, 'italic')).pack(side="bottom", pady=20)
        
        # Manual Export Button (optional)
        ttk.Button(center_frame, text="Force Export Log", command=self.export_to_excel).pack(side="bottom", pady=5)

    def toggle_action(self):
        if self.scan_action == "SIGN IN":
            self.scan_action = "SIGN OUT"
            self.btn_action.config(text="CURRENTLY: SIGN OUT", bg=ACTION_BLUE) # Blue for leaving? Or Orange.
        else:
            self.scan_action = "SIGN IN"
            self.btn_action.config(text="CURRENTLY: SIGN IN", bg=SUCCESS_GREEN)

    def process_scan_data(self, data):
        # Format expected: email_user,fname,lname,officer
        # If simple UID (e.g. 12345678), log as unknown or raw
        
        timestamp = datetime.datetime.now().strftime("%I:%M:%S %p")
        date_str = datetime.datetime.now().strftime("%Y-%m-%d")
        
        parsed_record = {}
        display_msg = ""
        
        parts = data.split(',')
        if len(parts) >= 3:
            # Assume it's our formatted data
            email_user = parts[0].strip()
            fname = parts[1].strip()
            lname = parts[2].strip()
            # Construct full email
            if "@" not in email_user:
                email_full = f"{email_user}@student.monroecc.edu"
            else:
                email_full = email_user
            
            parsed_record = {
                "Date": date_str,
                "Time": timestamp,
                "Action": self.scan_action,
                "First Name": fname,
                "Last Name": lname,
                "Email": email_full,
                "Raw Data": data
            }
            display_msg = f"{self.scan_action}: {fname} {lname} ({email_full})"
        else:
            # Raw UID or unformatted
            parsed_record = {
                "Date": date_str,
                "Time": timestamp,
                "Action": self.scan_action,
                "First Name": "Unknown",
                "Last Name": "Unknown",
                "Email": "N/A",
                "Raw Data": data
            }
            display_msg = f"{self.scan_action}: Unknown Card [{data}]"

        # Add to memory log
        self.log_data.append(parsed_record)
        
        # OPTIMIZED: Append to Backup CSV using standard I/O (Lightweight)
        try:
            file_exists = os.path.exists(BACKUP_CSV)
            with open(BACKUP_CSV, 'a', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=["Date", "Time", "Action", "First Name", "Last Name", "Email", "Raw Data"])
                if not file_exists:
                    writer.writeheader()
                writer.writerow(parsed_record)
        except Exception as e:
            print(f"Backup CSV error: {e}")

        return display_msg

    def _update_read_log(self, data):
        if self.mode == "READ":
            # Process data (returns display_msg, but we want the struct)
            self.process_scan_data(data)
            
            # Get the record we just added
            if self.log_data:
                record = self.log_data[-1]
                fname = record.get("First Name", "Unknown")
                lname = record.get("Last Name", "")
                action = record.get("Action", "Scan")
                timestamp = record.get("Time", "")
                
                # Update UI
                if fname != "Unknown":
                    self.lbl_welcome_header.config(text=f"Welcome {fname} {lname} to the\nEngineering Leadership Council MakerSpace")
                    self.lbl_name.config(text=f"{fname} {lname}", foreground=SUCCESS_GREEN)
                else:
                    self.lbl_welcome_header.config(text="Welcome to the\nEngineering Leadership Council MakerSpace")
                    self.lbl_name.config(text="Unknown Card", foreground=ERROR_RED)

                self.lbl_status_msg.config(text=f"{action} Recorded at {timestamp}")
                
            # Clear logic after delay? For now leaving it static until next scan.

    # --- EXPORT LOGIC ---
    def check_auto_export(self):
        now = datetime.datetime.now()
        # Check if it's 11:59 PM (23:59)
        if now.hour == 23 and now.minute == 59:
            today_str = now.strftime("%Y-%m-%d")
            if self.last_export_date != today_str:
                self.export_to_excel()
                self.last_export_date = today_str
        
        # Check every 30 seconds
        self.root.after(30000, self.check_auto_export)

    def export_to_excel(self):
        if not self.log_data:
            print("No data to export.")
            return

        try:
            # OPTIMIZATION: Import pandas only when needed for export (Saves Memory)
            import pandas as pd
            
            now = datetime.datetime.now()
            year_folder = now.strftime("%Y")
            month_folder = now.strftime("%B") # Full month name e.g. January
            date_file_name = now.strftime("%d_attendance.xlsx")

            # Create path: logs/2025/December/
            base_path = Path("logs")
            full_path = base_path / year_folder / month_folder
            full_path.mkdir(parents=True, exist_ok=True)
            
            file_path = full_path / date_file_name

            df = pd.DataFrame(self.log_data)
            
            # Reorder columns nicely
            cols = ["Date", "Time", "Action", "First Name", "Last Name", "Email", "Raw Data"]
            df = df[cols]

            df.to_excel(file_path, index=False)
            print(f"Exported to {file_path}")
            
            # Clear memory log after successful export
            self.log_data = []
            
            # Optional: Rotate backup csv
            if os.path.exists(BACKUP_CSV):
                os.remove(BACKUP_CSV) # Start fresh for next day

            if self.mode == "READ":
                 messagebox.showinfo("Auto-Export", f"Daily log exported successfully to:\n{file_path}")

        except Exception as e:
            print(f"Export failed: {e}")
            if self.mode == "READ":
                messagebox.showerror("Export Failed", str(e))

    # --- ADMIN VIEW ---
    def setup_write_view(self):
        net_frame = ttk.LabelFrame(self.content_frame, text="Network Configuration", padding=15)
        net_frame.pack(fill="x", pady=(0, 20))
        
        ttk.Label(net_frame, text=f"Current Target IP: {self.last_ip}").pack(side="left", padx=(0, 10))
        ttk.Button(net_frame, text="Change IP & Connect", command=self.prompt_connection, width=20).pack(side="left")
        
        form_frame = ttk.LabelFrame(self.content_frame, text="Write User Data to Card", padding=15)
        form_frame.pack(fill="both", expand=True)

        center_form = ttk.Frame(form_frame)
        center_form.pack(expand=True)

        entry_width = 35
        ttk.Label(center_form, text="First Name:").grid(row=1, column=0, sticky="e", padx=10, pady=10)
        self.entry_fname = ttk.Entry(center_form, width=entry_width, font=('Segoe UI', 10))
        self.entry_fname.grid(row=1, column=1, pady=10)

        ttk.Label(center_form, text="Last Name:").grid(row=2, column=0, sticky="e", padx=10, pady=10)
        self.entry_lname = ttk.Entry(center_form, width=entry_width, font=('Segoe UI', 10))
        self.entry_lname.grid(row=2, column=1, pady=10)

        ttk.Label(center_form, text="Email Username:").grid(row=3, column=0, sticky="e", padx=10, pady=10)
        self.entry_email = ttk.Entry(center_form, width=entry_width, font=('Segoe UI', 10))
        self.entry_email.grid(row=3, column=1, pady=10)

        ttk.Label(center_form, text="Is Officer:").grid(row=4, column=0, sticky="e", padx=10, pady=10)
        self.var_officer = tk.BooleanVar()
        self.chk_officer = ttk.Checkbutton(center_form, variable=self.var_officer, text="Yes, grant officer privileges")
        self.chk_officer.grid(row=4, column=1, sticky="w", pady=10)

        self.btn_write = ttk.Button(center_form, text="WRITE DATA TO CARD", command=self.handle_write, width=25)
        self.btn_write.grid(row=5, column=0, columnspan=2, pady=30)
        
        self.write_status = ttk.Label(center_form, text="", foreground=MCC_GOLD)
        self.write_status.grid(row=6, column=0, columnspan=2)

    def handle_write(self):
        if not self.client.connected:
            messagebox.showerror("Error", "Not connected to Raspberry Pi.")
            return

        fname = self.entry_fname.get().strip()
        lname = self.entry_lname.get().strip()
        email = self.entry_email.get().strip()
        officer = str(self.var_officer.get())

        if not (fname and lname and email):
            messagebox.showwarning("Input Error", "Please fill in all text fields.")
            return

        data_str = f"{email},{fname},{lname},{officer}"
        
        self.btn_write.config(state="disabled")
        self.write_status.config(text="Sending command... Place card on Reader.", foreground=MCC_GOLD)
        self.root.update()
        self.client.send_write(data_str)

    # --- Callbacks ---
    def on_rfid_read(self, data):
        self.root.after(0, lambda: self._update_read_log(data))

    def on_write_result(self, success, msg):
        self.root.after(0, lambda: self._update_write_status(success, msg))

    def _update_write_status(self, success, msg):
        if self.mode == "WRITE":
            self.btn_write.config(state="normal")
            if success:
                self.write_status.config(text=f"Success: {msg}", foreground=SUCCESS_GREEN)
                messagebox.showinfo("Write Success", msg)
                self.entry_fname.delete(0, tk.END)
                self.entry_lname.delete(0, tk.END)
                self.entry_email.delete(0, tk.END)
                self.var_officer.set(False)
            else:
                self.write_status.config(text=f"Failed: {msg}", foreground=ERROR_RED)
                messagebox.showerror("Write Failed", msg)

if __name__ == "__main__":
    root = tk.Tk()
    app = RFIDClientApp(root)
    root.mainloop()

BACKUP_CSV = "daily_backup.csv"
DEFAULT_PORT = 65432
LAST_IP_FILE = "last_ip.txt"
ADMIN_PASSCODE = "1234" # Simple passcode

# --- Colors & Styles ---
MCC_GOLD = "#C99700"
MCC_BLACK = "#1A1A1A"  # Main background
HEADER_BLACK = "#000000"  # Header background
TEXT_WHITE = "#F0F0F0"
ERROR_RED = "#FF4444"
SUCCESS_GREEN = "#00C851"
ACTION_BLUE = "#33b5e5"

class NetworkClient:
    def __init__(self, callback_read, callback_write_result):
        self.socket = None
        self.connected = False
        self.callback_read = callback_read
        self.callback_write_result = callback_write_result
        self.stop_event = threading.Event()

    def connect(self, ip):
        self.disconnect()
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(5)
            self.socket.connect((ip, DEFAULT_PORT))
            self.connected = True
            self.stop_event.clear()
            
            # Start listener thread
            self.thread = threading.Thread(target=self.listen_loop, daemon=True)
            self.thread.start()
            return True, "Connected"
        except Exception as e:
            return False, str(e)

    def disconnect(self):
        self.connected = False
        self.stop_event.set()
        if self.socket:
            try: self.socket.close()
            except: pass
        self.socket = None

    def send_write(self, text):
        if not self.connected:
            return False
        try:
            cmd = {"action": "write", "content": text}
            msg = json.dumps(cmd) + "\n"
            self.socket.sendall(msg.encode('utf-8'))
            return True
        except Exception as e:
            self.disconnect()
            return False

    def listen_loop(self):
        buffer = ""
        while not self.stop_event.is_set():
            try:
                data = self.socket.recv(1024)
                if not data:
                    break # Server closed
                
                buffer += data.decode('utf-8')
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    if not line: continue
                    self.process_msg(line)
            except socket.timeout:
                continue
            except Exception as e:
                print(f"Network Error: {e}")
                break
        
        self.connected = False
        # If we broke out of loop, connection died

    def process_msg(self, line):
        try:
            msg = json.loads(line)
            mtype = msg.get("type")
            
            if mtype == "READ":
                data = msg.get("data", "")
                self.callback_read(data)
            elif mtype == "WRITE_RESULT":
                success = msg.get("success")
                text = msg.get("msg")
                self.callback_write_result(success, text)
                
        except json.JSONDecodeError:
            pass

class RFIDClientApp:
    def __init__(self, root):
        self.root = root
        self.root.title("ELC Doorbell Client")
        self.root.geometry("700x650")
        self.root.configure(bg=MCC_BLACK)
        
        # Apply Windows Dark Title Bar
        try:
            self.root.update()
            # DWMWA_USE_IMMERSIVE_DARK_MODE = 20
            set_window_attribute = ctypes.windll.dwmapi.DwmSetWindowAttribute
            get_parent = ctypes.windll.user32.GetParent
            hwnd = get_parent(self.root.winfo_id())
            value = ctypes.c_int(2)
            set_window_attribute(hwnd, 20, ctypes.byref(value), ctypes.sizeof(value))
        except Exception as e:
            print(f"Failed to set dark title bar: {e}")

        # Set Icon
        try:
            if os.path.exists("icon.png"):
                icon_img = tk.PhotoImage(file="icon.png")
                self.root.iconphoto(False, icon_img)
        except Exception as e:
            print(f"Failed to load icon: {e}")
        
        self.client = NetworkClient(self.on_rfid_read, self.on_write_result)
        self.mode = "READ"
        self.scan_action = "SIGN IN" # Default action
        self.log_data = [] # List to hold dictionaries of daily scans
        self.last_export_date = None

        # Load last IP
        self.last_ip = "192.168.1.100"
        if os.path.exists(LAST_IP_FILE):
            with open(LAST_IP_FILE, "r") as f:
                self.last_ip = f.read().strip()

        self.setup_styles()
        self.setup_ui()
        
        # Check for unsaved backup CSV and load it if needed (optional advanced feature, simplified here)
        # For now, we start fresh memory, but append to backup csv
        
        # Auto-connect silently on startup
        self.root.after(500, self.silent_connect)
        
        # Start Auto-Export Scheduler
        self.check_auto_export()

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')  # 'clam' allows for better color customization
        
        # General Frame
        style.configure('TFrame', background=MCC_BLACK)
        
        # Labels
        style.configure('TLabel', background=MCC_BLACK, foreground=TEXT_WHITE, font=('Segoe UI', 11))
        style.configure('Header.TLabel', background=HEADER_BLACK, foreground=MCC_GOLD, font=('Segoe UI', 20, 'bold'))
        style.configure('SubHeader.TLabel', background=MCC_BLACK, foreground=MCC_GOLD, font=('Segoe UI', 14, 'bold'))
        style.configure('Status.TLabel', background=HEADER_BLACK, foreground="gray", font=('Segoe UI', 10))
        
        # Buttons
        style.configure('TButton', 
                        font=('Segoe UI', 11, 'bold'), 
                        background=MCC_GOLD, 
                        foreground="black", 
                        borderwidth=0, 
                        focuscolor=MCC_GOLD)
        style.map('TButton', background=[('active', '#FFCA28'), ('disabled', '#555')]) # Lighter gold on hover
        
        # Toggle Button Style (Sign In / Sign Out)
        style.configure('Toggle.TButton', 
                        font=('Segoe UI', 12, 'bold'),
                        background=SUCCESS_GREEN,
                        foreground="white")
        
        # Radiobuttons
        style.configure('TRadiobutton', background=MCC_BLACK, foreground=TEXT_WHITE, font=('Segoe UI', 11))
        style.map('TRadiobutton', indicatorcolor=[('selected', MCC_GOLD)])
        
        # Checkbuttons
        style.configure('TCheckbutton', background=MCC_BLACK, foreground=TEXT_WHITE, font=('Segoe UI', 11))
        style.map('TCheckbutton', indicatorcolor=[('selected', MCC_GOLD)])
        
        # Labelframe
        style.configure('TLabelframe', background=MCC_BLACK, foreground=MCC_GOLD)
        style.configure('TLabelframe.Label', background=MCC_BLACK, foreground=MCC_GOLD, font=('Segoe UI', 10, 'bold'))

    def setup_ui(self):
        # Header
        header_frame = tk.Frame(self.root, bg=HEADER_BLACK, padx=20, pady=15)
        header_frame.pack(fill="x")
        
        # Title with Gold color
        lbl_title = ttk.Label(header_frame, text="ELC MakerSpace RFID", style='Header.TLabel', background=HEADER_BLACK)
        lbl_title.pack(side="left")
        
        # Connection Status
        conn_frame = tk.Frame(header_frame, bg=HEADER_BLACK)
        conn_frame.pack(side="right")
        self.lbl_connection = ttk.Label(conn_frame, text="Disconnected", style='Status.TLabel', foreground=ERROR_RED)
        self.lbl_connection.pack(anchor="e")
        
        # Divider
        tk.Frame(self.root, bg=MCC_GOLD, height=2).pack(fill="x")

        # Mode Selection
        self.mode_frame = ttk.Frame(self.root, padding=(0, 20))
        self.mode_frame.pack()
        
        self.mode_var = tk.StringVar(value="READ")
        
        self.rb_read = ttk.Radiobutton(self.mode_frame, text="READ MODE", variable=self.mode_var, value="READ", command=self.change_mode)
        self.rb_write = ttk.Radiobutton(self.mode_frame, text="ADMIN PANEL", variable=self.mode_var, value="WRITE", command=self.change_mode)
        
        self.rb_read.pack(side="left", padx=30)
        self.rb_write.pack(side="left", padx=30)

        # Content Area
        self.content_frame = ttk.Frame(self.root, padding=20)
        self.content_frame.pack(fill="both", expand=True)

        self.setup_read_view()

    def silent_connect(self):
        if self.last_ip:
            self.lbl_connection.config(text=f"Connecting to {self.last_ip}...", foreground=MCC_GOLD)
            self.root.update()
            success, msg = self.client.connect(self.last_ip)
            if success:
                self.lbl_connection.config(text=f"Connected to {self.last_ip}", foreground=SUCCESS_GREEN)
            else:
                self.lbl_connection.config(text=f"Disconnected", foreground=ERROR_RED)

    def prompt_connection(self):
        ip = simpledialog.askstring("Connect to Pi", "Enter Raspberry Pi IP Address:", initialvalue=self.last_ip)
        if ip:
            self.last_ip = ip
            with open(LAST_IP_FILE, "w") as f:
                f.write(ip)
                
            self.lbl_connection.config(text=f"Connecting to {ip}...", foreground=MCC_GOLD)
            self.root.update()
            
            success, msg = self.client.connect(ip)
            if success:
                self.lbl_connection.config(text=f"Connected to {ip}", foreground=SUCCESS_GREEN)
            else:
                self.lbl_connection.config(text=f"Failed: {msg}", foreground=ERROR_RED)
                messagebox.showerror("Connection Error", f"Could not connect to {ip}.\n{msg}")

    def change_mode(self):
        new_mode = self.mode_var.get()
        
        if new_mode == "WRITE":
            pwd = simpledialog.askstring("Admin Access", "Enter Admin Passcode:", show='*')
            if pwd != ADMIN_PASSCODE:
                messagebox.showerror("Access Denied", "Incorrect passcode.")
                self.mode_var.set("READ")
                return 

        self.mode = new_mode
        for widget in self.content_frame.winfo_children():
            widget.destroy()
            
        if self.mode == "READ":
            self.setup_read_view()
        else:
            self.setup_write_view()

    # --- READ VIEW & LOGIC ---
    def setup_read_view(self):
        center_frame = ttk.Frame(self.content_frame)
        center_frame.pack(expand=True, fill='both')

        # Action Toggle
        self.btn_action = tk.Button(center_frame, text="CURRENTLY: SIGN IN", 
                                    font=('Segoe UI', 14, 'bold'),
                                    bg=SUCCESS_GREEN, fg="white",
                                    command=self.toggle_action,
                                    width=24, height=2, relief="flat")
        self.btn_action.pack(pady=(0, 20))
        
        lbl = ttk.Label(center_frame, text="Waiting for Card Scan...", style='SubHeader.TLabel', foreground=MCC_GOLD)
        lbl.pack(pady=(0, 10))
        
        self.log_display = tk.Text(center_frame, height=15, width=65, state="disabled",
                                   bg="#2A2A2A", fg="white", font=("Consolas", 10),
                                   insertbackground="white", relief="flat", padx=10, pady=10)
        self.log_display.pack(pady=10, expand=True, fill='both')
        
        ttk.Label(center_frame, text="* Logs auto-export to Excel at 11:59 PM", foreground="gray", font=('Segoe UI', 9, 'italic')).pack()
        
        # Manual Export Button (optional, but good for testing)
        ttk.Button(center_frame, text="Force Export Log", command=self.export_to_excel).pack(pady=5)

    def toggle_action(self):
        if self.scan_action == "SIGN IN":
            self.scan_action = "SIGN OUT"
            self.btn_action.config(text="CURRENTLY: SIGN OUT", bg=ACTION_BLUE) # Blue for leaving? Or Orange.
        else:
            self.scan_action = "SIGN IN"
            self.btn_action.config(text="CURRENTLY: SIGN IN", bg=SUCCESS_GREEN)

    def process_scan_data(self, data):
        # Format expected: email_user,fname,lname,officer
        # If simple UID (e.g. 12345678), log as unknown or raw
        
        timestamp = datetime.datetime.now().strftime("%I:%M:%S %p")
        date_str = datetime.datetime.now().strftime("%Y-%m-%d")
        
        parsed_record = {}
        display_msg = ""
        
        parts = data.split(',')
        if len(parts) >= 3:
            # Assume it's our formatted data
            email_user = parts[0].strip()
            fname = parts[1].strip()
            lname = parts[2].strip()
            # Construct full email
            if "@" not in email_user:
                email_full = f"{email_user}@student.monroecc.edu"
            else:
                email_full = email_user
            
            parsed_record = {
                "Date": date_str,
                "Time": timestamp,
                "Action": self.scan_action,
                "First Name": fname,
                "Last Name": lname,
                "Email": email_full,
                "Raw Data": data
            }
            display_msg = f"{self.scan_action}: {fname} {lname} ({email_full})"
        else:
            # Raw UID or unformatted
            parsed_record = {
                "Date": date_str,
                "Time": timestamp,
                "Action": self.scan_action,
                "First Name": "Unknown",
                "Last Name": "Unknown",
                "Email": "N/A",
                "Raw Data": data
            }
            display_msg = f"{self.scan_action}: Unknown Card [{data}]"

        # Add to memory log
        self.log_data.append(parsed_record)
        
        # Add to Backup CSV immediately
        try:
            df = pd.DataFrame([parsed_record])
            header = not os.path.exists(BACKUP_CSV)
            df.to_csv(BACKUP_CSV, mode='a', header=header, index=False)
        except Exception as e:
            print(f"Backup CSV error: {e}")

        return display_msg

    def _update_read_log(self, data):
        if self.mode == "READ":
            display_msg = self.process_scan_data(data)
            timestamp = datetime.datetime.now().strftime("%H:%M:%S")
            
            self.log_display.config(state="normal")
            self.log_display.insert(tk.END, f"[{timestamp}] {display_msg}\n")
            self.log_display.see(tk.END)
            self.log_display.config(state="disabled")

    # --- EXPORT LOGIC ---
    def check_auto_export(self):
        now = datetime.datetime.now()
        # Check if it's 11:59 PM (23:59)
        if now.hour == 23 and now.minute == 59:
            today_str = now.strftime("%Y-%m-%d")
            if self.last_export_date != today_str:
                self.export_to_excel()
                self.last_export_date = today_str
        
        # Check every 30 seconds
        self.root.after(30000, self.check_auto_export)

    def export_to_excel(self):
        if not self.log_data:
            print("No data to export.")
            return

        try:
            now = datetime.datetime.now()
            year_folder = now.strftime("%Y")
            month_folder = now.strftime("%B") # Full month name e.g. January
            date_file_name = now.strftime("%d_attendance.xlsx")

            # Create path: logs/2025/December/
            base_path = Path("logs")
            full_path = base_path / year_folder / month_folder
            full_path.mkdir(parents=True, exist_ok=True)
            
            file_path = full_path / date_file_name

            df = pd.DataFrame(self.log_data)
            
            # Reorder columns nicely
            cols = ["Date", "Time", "Action", "First Name", "Last Name", "Email", "Raw Data"]
            df = df[cols]

            df.to_excel(file_path, index=False)
            print(f"Exported to {file_path}")
            
            # Clear memory log after successful export
            self.log_data = []
            
            # Optional: Rotate backup csv
            if os.path.exists(BACKUP_CSV):
                os.remove(BACKUP_CSV) # Start fresh for next day

            if self.mode == "READ":
                 messagebox.showinfo("Auto-Export", f"Daily log exported successfully to:\n{file_path}")

        except Exception as e:
            print(f"Export failed: {e}")
            if self.mode == "READ":
                messagebox.showerror("Export Failed", str(e))

    # --- ADMIN VIEW ---
    def setup_write_view(self):
        net_frame = ttk.LabelFrame(self.content_frame, text="Network Configuration", padding=15)
        net_frame.pack(fill="x", pady=(0, 20))
        
        ttk.Label(net_frame, text=f"Current Target IP: {self.last_ip}").pack(side="left", padx=(0, 10))
        ttk.Button(net_frame, text="Change IP & Connect", command=self.prompt_connection, width=20).pack(side="left")
        
        form_frame = ttk.LabelFrame(self.content_frame, text="Write User Data to Card", padding=15)
        form_frame.pack(fill="both", expand=True)

        center_form = ttk.Frame(form_frame)
        center_form.pack(expand=True)

        entry_width = 35
        ttk.Label(center_form, text="First Name:").grid(row=1, column=0, sticky="e", padx=10, pady=10)
        self.entry_fname = ttk.Entry(center_form, width=entry_width, font=('Segoe UI', 10))
        self.entry_fname.grid(row=1, column=1, pady=10)

        ttk.Label(center_form, text="Last Name:").grid(row=2, column=0, sticky="e", padx=10, pady=10)
        self.entry_lname = ttk.Entry(center_form, width=entry_width, font=('Segoe UI', 10))
        self.entry_lname.grid(row=2, column=1, pady=10)

        ttk.Label(center_form, text="Email Username:").grid(row=3, column=0, sticky="e", padx=10, pady=10)
        self.entry_email = ttk.Entry(center_form, width=entry_width, font=('Segoe UI', 10))
        self.entry_email.grid(row=3, column=1, pady=10)

        ttk.Label(center_form, text="Is Officer:").grid(row=4, column=0, sticky="e", padx=10, pady=10)
        self.var_officer = tk.BooleanVar()
        self.chk_officer = ttk.Checkbutton(center_form, variable=self.var_officer, text="Yes, grant officer privileges")
        self.chk_officer.grid(row=4, column=1, sticky="w", pady=10)

        self.btn_write = ttk.Button(center_form, text="WRITE DATA TO CARD", command=self.handle_write, width=25)
        self.btn_write.grid(row=5, column=0, columnspan=2, pady=30)
        
        self.write_status = ttk.Label(center_form, text="", foreground=MCC_GOLD)
        self.write_status.grid(row=6, column=0, columnspan=2)

    def handle_write(self):
        if not self.client.connected:
            messagebox.showerror("Error", "Not connected to Raspberry Pi.")
            return

        fname = self.entry_fname.get().strip()
        lname = self.entry_lname.get().strip()
        email = self.entry_email.get().strip()
        officer = str(self.var_officer.get())

        if not (fname and lname and email):
            messagebox.showwarning("Input Error", "Please fill in all text fields.")
            return

        data_str = f"{email},{fname},{lname},{officer}"
        
        self.btn_write.config(state="disabled")
        self.write_status.config(text="Sending command... Place card on Reader.", foreground=MCC_GOLD)
        self.root.update()
        self.client.send_write(data_str)

    # --- Callbacks ---
    def on_rfid_read(self, data):
        self.root.after(0, lambda: self._update_read_log(data))

    def on_write_result(self, success, msg):
        self.root.after(0, lambda: self._update_write_status(success, msg))

    def _update_write_status(self, success, msg):
        if self.mode == "WRITE":
            self.btn_write.config(state="normal")
            if success:
                self.write_status.config(text=f"Success: {msg}", foreground=SUCCESS_GREEN)
                messagebox.showinfo("Write Success", msg)
                self.entry_fname.delete(0, tk.END)
                self.entry_lname.delete(0, tk.END)
                self.entry_email.delete(0, tk.END)
                self.var_officer.set(False)
            else:
                self.write_status.config(text=f"Failed: {msg}", foreground=ERROR_RED)
                messagebox.showerror("Write Failed", msg)

if __name__ == "__main__":
    root = tk.Tk()
    app = RFIDClientApp(root)
    root.mainloop()


    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')  # 'clam' allows for better color customization
        
        # General Frame
        style.configure('TFrame', background=MCC_BLACK)
        
        # Labels
        style.configure('TLabel', background=MCC_BLACK, foreground=TEXT_WHITE, font=('Segoe UI', 11))
        style.configure('Header.TLabel', background=HEADER_BLACK, foreground=MCC_GOLD, font=('Segoe UI', 20, 'bold'))
        style.configure('SubHeader.TLabel', background=MCC_BLACK, foreground=MCC_GOLD, font=('Segoe UI', 14, 'bold'))
        style.configure('Status.TLabel', background=HEADER_BLACK, foreground="gray", font=('Segoe UI', 10))
        
        # Buttons
        style.configure('TButton', 
                        font=('Segoe UI', 11, 'bold'), 
                        background=MCC_GOLD, 
                        foreground="black", 
                        borderwidth=0, 
                        focuscolor=MCC_GOLD)
        style.map('TButton', background=[('active', '#FFCA28'), ('disabled', '#555')]) # Lighter gold on hover
        
        # Radiobuttons
        style.configure('TRadiobutton', background=MCC_BLACK, foreground=TEXT_WHITE, font=('Segoe UI', 11))
        style.map('TRadiobutton', indicatorcolor=[('selected', MCC_GOLD)])
        
        # Checkbuttons
        style.configure('TCheckbutton', background=MCC_BLACK, foreground=TEXT_WHITE, font=('Segoe UI', 11))
        style.map('TCheckbutton', indicatorcolor=[('selected', MCC_GOLD)])
        
        # Labelframe
        style.configure('TLabelframe', background=MCC_BLACK, foreground=MCC_GOLD)
        style.configure('TLabelframe.Label', background=MCC_BLACK, foreground=MCC_GOLD, font=('Segoe UI', 10, 'bold'))

    def setup_ui(self):
        # Header
        header_frame = tk.Frame(self.root, bg=HEADER_BLACK, padx=20, pady=15)
        header_frame.pack(fill="x")
        
        # Title with Gold color
        lbl_title = ttk.Label(header_frame, text="ELC MakerSpace RFID", style='Header.TLabel', background=HEADER_BLACK)
        lbl_title.pack(side="left")
        
        # Connection Status Panel (Right side of header)
        conn_frame = tk.Frame(header_frame, bg=HEADER_BLACK)
        conn_frame.pack(side="right")
        
        self.lbl_connection = ttk.Label(conn_frame, text="Disconnected", style='Status.TLabel', foreground=ERROR_RED)
        self.lbl_connection.pack(anchor="e")
        
        # Note: 'Connect IP' button removed from header. Access via Admin Panel.

        # Divider
        tk.Frame(self.root, bg=MCC_GOLD, height=2).pack(fill="x")

        # Mode Selection
        self.mode_frame = ttk.Frame(self.root, padding=(0, 20))
        self.mode_frame.pack()
        
        self.mode_var = tk.StringVar(value="READ")
        
        self.rb_read = ttk.Radiobutton(self.mode_frame, text="READ MODE", variable=self.mode_var, value="READ", command=self.change_mode)
        self.rb_write = ttk.Radiobutton(self.mode_frame, text="ADMIN PANEL", variable=self.mode_var, value="WRITE", command=self.change_mode)
        
        self.rb_read.pack(side="left", padx=30)
        self.rb_write.pack(side="left", padx=30)

        # Content Area
        self.content_frame = ttk.Frame(self.root, padding=20)
        self.content_frame.pack(fill="both", expand=True)

        self.setup_read_view()

    def silent_connect(self):
        if self.last_ip:
            self.lbl_connection.config(text=f"Connecting to {self.last_ip}...", foreground=MCC_GOLD)
            self.root.update()
            success, msg = self.client.connect(self.last_ip)
            if success:
                self.lbl_connection.config(text=f"Connected to {self.last_ip}", foreground=SUCCESS_GREEN)
            else:
                self.lbl_connection.config(text=f"Disconnected", foreground=ERROR_RED)
                # Don't popup error, just stay disconnected until Admin fixes it

    def prompt_connection(self):
        ip = simpledialog.askstring("Connect to Pi", "Enter Raspberry Pi IP Address:", initialvalue=self.last_ip)
        if ip:
            self.last_ip = ip
            with open(LAST_IP_FILE, "w") as f:
                f.write(ip)
                
            self.lbl_connection.config(text=f"Connecting to {ip}...", foreground=MCC_GOLD)
            self.root.update()
            
            success, msg = self.client.connect(ip)
            if success:
                self.lbl_connection.config(text=f"Connected to {ip}", foreground=SUCCESS_GREEN)
            else:
                self.lbl_connection.config(text=f"Failed: {msg}", foreground=ERROR_RED)
                messagebox.showerror("Connection Error", f"Could not connect to {ip}.\n{msg}")

    def change_mode(self):
        new_mode = self.mode_var.get()
        
        if new_mode == "WRITE":
            pwd = simpledialog.askstring("Admin Access", "Enter Admin Passcode:", show='*')
            if pwd != ADMIN_PASSCODE:
                messagebox.showerror("Access Denied", "Incorrect passcode.")
                self.mode_var.set("READ")
                return # Do not change view or mode

        self.mode = new_mode
        # Clear frame
        for widget in self.content_frame.winfo_children():
            widget.destroy()
            
        if self.mode == "READ":
            self.setup_read_view()
        else:
            self.setup_write_view()

    def setup_read_view(self):
        # Container to center content
        center_frame = ttk.Frame(self.content_frame)
        center_frame.pack(expand=True, fill='both')

        lbl = ttk.Label(center_frame, text="Waiting for Card Scan...", style='SubHeader.TLabel', foreground=SUCCESS_GREEN)
        lbl.pack(pady=(0, 15))
        
        # Customizing Text widget for dark mode
        self.log_display = tk.Text(center_frame, height=15, width=60, state="disabled",
                                   bg="#2A2A2A", fg=MCC_GOLD, font=("Consolas", 10),
                                   insertbackground="white", relief="flat", padx=10, pady=10)
        self.log_display.pack(pady=10, expand=True, fill='both')
        
        ttk.Label(center_frame, text="* Scanned data saved to rfid_logs_client.txt", foreground="gray", font=('Segoe UI', 9, 'italic')).pack()

    def setup_write_view(self):
        # This is now the Admin Panel
        
        # --- Network Settings Section ---
        net_frame = ttk.LabelFrame(self.content_frame, text="Network Configuration", padding=15)
        net_frame.pack(fill="x", pady=(0, 20))
        
        ttk.Label(net_frame, text=f"Current Target IP: {self.last_ip}").pack(side="left", padx=(0, 10))
        ttk.Button(net_frame, text="Change IP & Connect", command=self.prompt_connection, width=20).pack(side="left")
        
        
        # --- Write Data Section ---
        form_frame = ttk.LabelFrame(self.content_frame, text="Write User Data to Card", padding=15)
        form_frame.pack(fill="both", expand=True)

        # Container for form to center it
        center_form = ttk.Frame(form_frame)
        center_form.pack(expand=True)

        # Style for entries
        entry_width = 35

        # Inputs
        ttk.Label(center_form, text="First Name:").grid(row=1, column=0, sticky="e", padx=10, pady=10)
        self.entry_fname = ttk.Entry(center_form, width=entry_width, font=('Segoe UI', 10))
        self.entry_fname.grid(row=1, column=1, pady=10)

        ttk.Label(center_form, text="Last Name:").grid(row=2, column=0, sticky="e", padx=10, pady=10)
        self.entry_lname = ttk.Entry(center_form, width=entry_width, font=('Segoe UI', 10))
        self.entry_lname.grid(row=2, column=1, pady=10)

        ttk.Label(center_form, text="Email Username:").grid(row=3, column=0, sticky="e", padx=10, pady=10)
        self.entry_email = ttk.Entry(center_form, width=entry_width, font=('Segoe UI', 10))
        self.entry_email.grid(row=3, column=1, pady=10)

        ttk.Label(center_form, text="Is Officer:").grid(row=4, column=0, sticky="e", padx=10, pady=10)
        self.var_officer = tk.BooleanVar()
        self.chk_officer = ttk.Checkbutton(center_form, variable=self.var_officer, text="Yes, grant officer privileges")
        self.chk_officer.grid(row=4, column=1, sticky="w", pady=10)

        self.btn_write = ttk.Button(center_form, text="WRITE DATA TO CARD", command=self.handle_write, width=25)
        self.btn_write.grid(row=5, column=0, columnspan=2, pady=30)
        
        self.write_status = ttk.Label(center_form, text="", foreground=MCC_GOLD)
        self.write_status.grid(row=6, column=0, columnspan=2)

    def handle_write(self):
        if not self.client.connected:
            messagebox.showerror("Error", "Not connected to Raspberry Pi.")
            return

        fname = self.entry_fname.get().strip()
        lname = self.entry_lname.get().strip()
        email = self.entry_email.get().strip()
        officer = str(self.var_officer.get())

        if not (fname and lname and email):
            messagebox.showwarning("Input Error", "Please fill in all text fields.")
            return

        data_str = f"{email},{fname},{lname},{officer}"
        
        self.btn_write.config(state="disabled")
        self.write_status.config(text="Sending command... Place card on Reader.", foreground=MCC_GOLD)
        self.root.update() # Force update
        self.client.send_write(data_str)

    # --- Callbacks ---
    def on_rfid_read(self, data):
        # Called from network thread, need to schedule UI update
        self.root.after(0, lambda: self._update_read_log(data))

    def _update_read_log(self, data):
        if self.mode == "READ":
            timestamp = datetime.datetime.now().strftime("%H:%M:%S")
            entry = f"[{timestamp}] READ: {data}"
            
            self.log_display.config(state="normal")
            self.log_display.insert(tk.END, entry + "\n")
            self.log_display.see(tk.END)
            self.log_display.config(state="disabled")
            
            # Log to file
            with open(LOG_FILE, "a") as f:
                f.write(f"{datetime.datetime.now()},{data}\n")

    def on_write_result(self, success, msg):
        self.root.after(0, lambda: self._update_write_status(success, msg))

    def _update_write_status(self, success, msg):
        if self.mode == "WRITE":
            self.btn_write.config(state="normal")
            if success:
                self.write_status.config(text=f"Success: {msg}", foreground=SUCCESS_GREEN)
                messagebox.showinfo("Write Success", msg)
                self.entry_fname.delete(0, tk.END)
                self.entry_lname.delete(0, tk.END)
                self.entry_email.delete(0, tk.END)
                self.var_officer.set(False)
            else:
                self.write_status.config(text=f"Failed: {msg}", foreground=ERROR_RED)
                messagebox.showerror("Write Failed", msg)

if __name__ == "__main__":
    root = tk.Tk()
    # Optional: Set icon if available
    # root.iconbitmap("icon.ico") 
    app = RFIDClientApp(root)
    root.mainloop()

DEFAULT_PORT = 65432
LAST_IP_FILE = "last_ip.txt"
ADMIN_PASSCODE = "1234" # Simple passcode

# --- Colors & Styles ---
MCC_GOLD = "#C99700"
MCC_BLACK = "#1A1A1A"  # Main background
HEADER_BLACK = "#000000"  # Header background
TEXT_WHITE = "#F0F0F0"
ERROR_RED = "#FF4444"
SUCCESS_GREEN = "#00C851"

class NetworkClient:
    def __init__(self, callback_read, callback_write_result):
        self.socket = None
        self.connected = False
        self.callback_read = callback_read
        self.callback_write_result = callback_write_result
        self.stop_event = threading.Event()

    def connect(self, ip):
        self.disconnect()
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(5)
            self.socket.connect((ip, DEFAULT_PORT))
            self.connected = True
            self.stop_event.clear()
            
            # Start listener thread
            self.thread = threading.Thread(target=self.listen_loop, daemon=True)
            self.thread.start()
            return True, "Connected"
        except Exception as e:
            return False, str(e)

    def disconnect(self):
        self.connected = False
        self.stop_event.set()
        if self.socket:
            try: self.socket.close()
            except: pass
        self.socket = None

    def send_write(self, text):
        if not self.connected:
            return False
        try:
            cmd = {"action": "write", "content": text}
            msg = json.dumps(cmd) + "\n"
            self.socket.sendall(msg.encode('utf-8'))
            return True
        except Exception as e:
            self.disconnect()
            return False

    def listen_loop(self):
        buffer = ""
        while not self.stop_event.is_set():
            try:
                data = self.socket.recv(1024)
                if not data:
                    break # Server closed
                
                buffer += data.decode('utf-8')
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    if not line: continue
                    self.process_msg(line)
            except socket.timeout:
                continue
            except Exception as e:
                print(f"Network Error: {e}")
                break
        
        self.connected = False
        # If we broke out of loop, connection died

    def process_msg(self, line):
        try:
            msg = json.loads(line)
            mtype = msg.get("type")
            
            if mtype == "READ":
                data = msg.get("data", "")
                self.callback_read(data)
            elif mtype == "WRITE_RESULT":
                success = msg.get("success")
                text = msg.get("msg")
                self.callback_write_result(success, text)
                
        except json.JSONDecodeError:
            pass

class RFIDClientApp:
    def __init__(self, root):
        self.root = root
        self.root.title("ELC Doorbell Client")
        self.root.geometry("700x600")
        self.root.configure(bg=MCC_BLACK)
        
        self.client = NetworkClient(self.on_rfid_read, self.on_write_result)
        self.mode = "READ"

        # Load last IP
        self.last_ip = "192.168.1.100"
        if os.path.exists(LAST_IP_FILE):
            with open(LAST_IP_FILE, "r") as f:
                self.last_ip = f.read().strip()

        self.setup_styles()
        self.setup_ui()
        
        # Auto-connect prompt
        self.root.after(500, self.prompt_connection)

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')  # 'clam' allows for better color customization
        
        # General Frame
        style.configure('TFrame', background=MCC_BLACK)
        
        # Labels
        style.configure('TLabel', background=MCC_BLACK, foreground=TEXT_WHITE, font=('Segoe UI', 11))
        style.configure('Header.TLabel', background=HEADER_BLACK, foreground=MCC_GOLD, font=('Segoe UI', 20, 'bold'))
        style.configure('SubHeader.TLabel', background=MCC_BLACK, foreground=MCC_GOLD, font=('Segoe UI', 14, 'bold'))
        style.configure('Status.TLabel', background=HEADER_BLACK, foreground="gray", font=('Segoe UI', 10))
        
        # Buttons
        style.configure('TButton', 
                        font=('Segoe UI', 11, 'bold'), 
                        background=MCC_GOLD, 
                        foreground="black", 
                        borderwidth=0, 
                        focuscolor=MCC_GOLD)
        style.map('TButton', background=[('active', '#FFCA28'), ('disabled', '#555')]) # Lighter gold on hover
        
        # Radiobuttons
        style.configure('TRadiobutton', background=MCC_BLACK, foreground=TEXT_WHITE, font=('Segoe UI', 11))
        style.map('TRadiobutton', indicatorcolor=[('selected', MCC_GOLD)])
        
        # Checkbuttons
        style.configure('TCheckbutton', background=MCC_BLACK, foreground=TEXT_WHITE, font=('Segoe UI', 11))
        style.map('TCheckbutton', indicatorcolor=[('selected', MCC_GOLD)])
        
        # Labelframe
        style.configure('TLabelframe', background=MCC_BLACK, foreground=MCC_GOLD)
        style.configure('TLabelframe.Label', background=MCC_BLACK, foreground=MCC_GOLD, font=('Segoe UI', 10, 'bold'))

    def setup_ui(self):
        # Header
        header_frame = tk.Frame(self.root, bg=HEADER_BLACK, padx=20, pady=15)
        header_frame.pack(fill="x")
        
        # Title with Gold color
        lbl_title = ttk.Label(header_frame, text="ELC MakerSpace RFID", style='Header.TLabel', background=HEADER_BLACK)
        lbl_title.pack(side="left")
        
        # Connection Status Panel (Right side of header)
        conn_frame = tk.Frame(header_frame, bg=HEADER_BLACK)
        conn_frame.pack(side="right")
        
        self.lbl_connection = ttk.Label(conn_frame, text="Disconnected", style='Status.TLabel', foreground=ERROR_RED)
        self.lbl_connection.pack(anchor="e")
        
        btn_connect = ttk.Button(conn_frame, text="Connect IP", command=self.prompt_connection, width=12)
        btn_connect.pack(anchor="e", pady=(5, 0))

        # Divider
        tk.Frame(self.root, bg=MCC_GOLD, height=2).pack(fill="x")

        # Mode Selection
        self.mode_frame = ttk.Frame(self.root, padding=(0, 20))
        self.mode_frame.pack()
        
        self.mode_var = tk.StringVar(value="READ")
        
        self.rb_read = ttk.Radiobutton(self.mode_frame, text="READ MODE", variable=self.mode_var, value="READ", command=self.change_mode)
        self.rb_write = ttk.Radiobutton(self.mode_frame, text="WRITE MODE (Admin)", variable=self.mode_var, value="WRITE", command=self.change_mode)
        
        self.rb_read.pack(side="left", padx=30)
        self.rb_write.pack(side="left", padx=30)

        # Content Area
        self.content_frame = ttk.Frame(self.root, padding=20)
        self.content_frame.pack(fill="both", expand=True)

        self.setup_read_view()

    def prompt_connection(self):
        # Custom dialog style would be nice, but simpledialog is stuck with OS style. 
        # minimal impact for this step.
        ip = simpledialog.askstring("Connect to Pi", "Enter Raspberry Pi IP Address:", initialvalue=self.last_ip)
        if ip:
            self.last_ip = ip
            with open(LAST_IP_FILE, "w") as f:
                f.write(ip)
                
            self.lbl_connection.config(text=f"Connecting to {ip}...", foreground=MCC_GOLD)
            self.root.update()
            
            success, msg = self.client.connect(ip)
            if success:
                self.lbl_connection.config(text=f"Connected to {ip}", foreground=SUCCESS_GREEN)
            else:
                self.lbl_connection.config(text=f"Failed: {msg}", foreground=ERROR_RED)
                messagebox.showerror("Connection Error", f"Could not connect to {ip}.\n{msg}")

    def change_mode(self):
        new_mode = self.mode_var.get()
        
        if new_mode == "WRITE":
            pwd = simpledialog.askstring("Admin Access", "Enter Admin Passcode:", show='*')
            if pwd != ADMIN_PASSCODE:
                messagebox.showerror("Access Denied", "Incorrect passcode.")
                self.mode_var.set("READ")
                return # Do not change view or mode

        self.mode = new_mode
        # Clear frame
        for widget in self.content_frame.winfo_children():
            widget.destroy()
            
        if self.mode == "READ":
            self.setup_read_view()
        else:
            self.setup_write_view()

    def setup_read_view(self):
        # Container to center content
        center_frame = ttk.Frame(self.content_frame)
        center_frame.pack(expand=True, fill='both')

        lbl = ttk.Label(center_frame, text="Waiting for Card Scan...", style='SubHeader.TLabel', foreground=SUCCESS_GREEN)
        lbl.pack(pady=(0, 15))
        
        # Customizing Text widget for dark mode
        self.log_display = tk.Text(center_frame, height=15, width=60, state="disabled",
                                   bg="#2A2A2A", fg=MCC_GOLD, font=("Consolas", 10),
                                   insertbackground="white", relief="flat", padx=10, pady=10)
        self.log_display.pack(pady=10, expand=True, fill='both')
        
        ttk.Label(center_frame, text="* Scanned data saved to rfid_logs_client.txt", foreground="gray", font=('Segoe UI', 9, 'italic')).pack()

    def setup_write_view(self):
        # Container
        form_frame = ttk.Frame(self.content_frame)
        form_frame.pack(expand=True)

        ttk.Label(form_frame, text="Write User Data", style='SubHeader.TLabel').grid(row=0, column=0, columnspan=2, pady=(0, 20))

        # Style for entries
        entry_width = 35

        # Inputs
        ttk.Label(form_frame, text="First Name:").grid(row=1, column=0, sticky="e", padx=10, pady=10)
        self.entry_fname = ttk.Entry(form_frame, width=entry_width, font=('Segoe UI', 10))
        self.entry_fname.grid(row=1, column=1, pady=10)

        ttk.Label(form_frame, text="Last Name:").grid(row=2, column=0, sticky="e", padx=10, pady=10)
        self.entry_lname = ttk.Entry(form_frame, width=entry_width, font=('Segoe UI', 10))
        self.entry_lname.grid(row=2, column=1, pady=10)

        ttk.Label(form_frame, text="Email Username:").grid(row=3, column=0, sticky="e", padx=10, pady=10)
        self.entry_email = ttk.Entry(form_frame, width=entry_width, font=('Segoe UI', 10))
        self.entry_email.grid(row=3, column=1, pady=10)

        ttk.Label(form_frame, text="Is Officer:").grid(row=4, column=0, sticky="e", padx=10, pady=10)
        self.var_officer = tk.BooleanVar()
        self.chk_officer = ttk.Checkbutton(form_frame, variable=self.var_officer, text="Yes, grant officer privileges")
        self.chk_officer.grid(row=4, column=1, sticky="w", pady=10)

        self.btn_write = ttk.Button(form_frame, text="WRITE DATA TO CARD", command=self.handle_write, width=25)
        self.btn_write.grid(row=5, column=0, columnspan=2, pady=30)
        
        self.write_status = ttk.Label(form_frame, text="", foreground=MCC_GOLD)
        self.write_status.grid(row=6, column=0, columnspan=2)

    def handle_write(self):
        if not self.client.connected:
            messagebox.showerror("Error", "Not connected to Raspberry Pi.")
            return

        fname = self.entry_fname.get().strip()
        lname = self.entry_lname.get().strip()
        email = self.entry_email.get().strip()
        officer = str(self.var_officer.get())

        if not (fname and lname and email):
            messagebox.showwarning("Input Error", "Please fill in all text fields.")
            return

        data_str = f"{email},{fname},{lname},{officer}"
        
        self.btn_write.config(state="disabled")
        self.write_status.config(text="Sending command... Place card on Reader.", foreground=MCC_GOLD)
        self.root.update() # Force update
        self.client.send_write(data_str)

    # --- Callbacks ---
    def on_rfid_read(self, data):
        # Called from network thread, need to schedule UI update
        self.root.after(0, lambda: self._update_read_log(data))

    def _update_read_log(self, data):
        if self.mode == "READ":
            timestamp = datetime.datetime.now().strftime("%H:%M:%S")
            entry = f"[{timestamp}] READ: {data}"
            
            self.log_display.config(state="normal")
            self.log_display.insert(tk.END, entry + "\n")
            self.log_display.see(tk.END)
            self.log_display.config(state="disabled")
            
            # Log to file
            with open(LOG_FILE, "a") as f:
                f.write(f"{datetime.datetime.now()},{data}\n")

    def on_write_result(self, success, msg):
        self.root.after(0, lambda: self._update_write_status(success, msg))

    def _update_write_status(self, success, msg):
        if self.mode == "WRITE":
            self.btn_write.config(state="normal")
            if success:
                self.write_status.config(text=f"Success: {msg}", foreground=SUCCESS_GREEN)
                messagebox.showinfo("Write Success", msg)
                self.entry_fname.delete(0, tk.END)
                self.entry_lname.delete(0, tk.END)
                self.entry_email.delete(0, tk.END)
                self.var_officer.set(False)
            else:
                self.write_status.config(text=f"Failed: {msg}", foreground=ERROR_RED)
                messagebox.showerror("Write Failed", msg)

if __name__ == "__main__":
    root = tk.Tk()
    # Optional: Set icon if available
    # root.iconbitmap("icon.ico") 
    app = RFIDClientApp(root)
    root.mainloop()

DEFAULT_PORT = 65432
# Default IP - can be changed in GUI or saved
LAST_IP_FILE = "last_ip.txt"

class NetworkClient:
    def __init__(self, callback_read, callback_write_result):
        self.socket = None
        self.connected = False
        self.callback_read = callback_read
        self.callback_write_result = callback_write_result
        self.stop_event = threading.Event()

    def connect(self, ip):
        self.disconnect()
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(5)
            self.socket.connect((ip, DEFAULT_PORT))
            self.connected = True
            self.stop_event.clear()
            
            # Start listener thread
            self.thread = threading.Thread(target=self.listen_loop, daemon=True)
            self.thread.start()
            return True, "Connected"
        except Exception as e:
            return False, str(e)

    def disconnect(self):
        self.connected = False
        self.stop_event.set()
        if self.socket:
            try: self.socket.close()
            except: pass
        self.socket = None

    def send_write(self, text):
        if not self.connected:
            return False
        try:
            cmd = {"action": "write", "content": text}
            msg = json.dumps(cmd) + "\n"
            self.socket.sendall(msg.encode('utf-8'))
            return True
        except Exception as e:
            self.disconnect()
            return False

    def listen_loop(self):
        buffer = ""
        while not self.stop_event.is_set():
            try:
                data = self.socket.recv(1024)
                if not data:
                    break # Server closed
                
                buffer += data.decode('utf-8')
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    if not line: continue
                    self.process_msg(line)
            except socket.timeout:
                continue
            except Exception as e:
                print(f"Network Error: {e}")
                break
        
        self.connected = False
        # If we broke out of loop, connection died

    def process_msg(self, line):
        try:
            msg = json.loads(line)
            mtype = msg.get("type")
            
            if mtype == "READ":
                data = msg.get("data", "")
                self.callback_read(data)
            elif mtype == "WRITE_RESULT":
                success = msg.get("success")
                text = msg.get("msg")
                self.callback_write_result(success, text)
                
        except json.JSONDecodeError:
            pass

class RFIDClientApp:
    def __init__(self, root):
        self.root = root
        self.root.title("ELC Doorbell Client")
        self.root.geometry("600x550")
        
        self.client = NetworkClient(self.on_rfid_read, self.on_write_result)
        self.mode = "READ"

        # Load last IP
        self.last_ip = "192.168.1.100"
        if os.path.exists(LAST_IP_FILE):
            with open(LAST_IP_FILE, "r") as f:
                self.last_ip = f.read().strip()

        self.setup_ui()
        
        # Auto-connect prompt
        self.root.after(500, self.prompt_connection)

    def setup_ui(self):
        # Header
        header_frame = tk.Frame(self.root, bg="#333")
        header_frame.pack(fill="x")
        
        tk.Label(header_frame, text="ELC MakerSpace RFID", font=("Helvetica", 16, "bold"), bg="#333", fg="white").pack(pady=10)
        
        self.lbl_connection = tk.Label(header_frame, text="Disconnected", font=("Arial", 10), bg="#333", fg="red")
        self.lbl_connection.pack(pady=(0, 10))
        
        btn_connect = tk.Button(header_frame, text="Connect IP", font=("Arial", 8), command=self.prompt_connection)
        btn_connect.pack(anchor="e", padx=10, pady=(0, 10))

        # Mode Selection
        self.mode_frame = tk.Frame(self.root)
        self.mode_frame.pack(pady=10)
        
        self.mode_var = tk.StringVar(value="READ")
        style = ttk.Style()
        style.configure('TButton', font=('Arial', 10))
        
        self.rb_read = ttk.Radiobutton(self.mode_frame, text="READ MODE", variable=self.mode_var, value="READ", command=self.change_mode)
        self.rb_write = ttk.Radiobutton(self.mode_frame, text="WRITE MODE", variable=self.mode_var, value="WRITE", command=self.change_mode)
        self.rb_read.pack(side="left", padx=20)
        self.rb_write.pack(side="left", padx=20)

        # Content Area
        self.content_frame = tk.Frame(self.root, padx=20, pady=20)
        self.content_frame.pack(fill="both", expand=True)

        self.setup_read_view()

    def prompt_connection(self):
        ip = simpledialog.askstring("Connect to Pi", "Enter Raspberry Pi IP Address:", initialvalue=self.last_ip)
        if ip:
            self.last_ip = ip
            with open(LAST_IP_FILE, "w") as f:
                f.write(ip)
                
            self.lbl_connection.config(text=f"Connecting to {ip}...", fg="orange")
            self.root.update()
            
            success, msg = self.client.connect(ip)
            if success:
                self.lbl_connection.config(text=f"Connected to {ip}", fg="green")
            else:
                self.lbl_connection.config(text=f"Failed: {msg}", fg="red")
                messagebox.showerror("Connection Error", f"Could not connect to {ip}.\n{msg}")

    def change_mode(self):
        self.mode = self.mode_var.get()
        # Clear frame
        for widget in self.content_frame.winfo_children():
            widget.destroy()
            
        if self.mode == "READ":
            self.setup_read_view()
        else:
            self.setup_write_view()

    def setup_read_view(self):
        lbl = tk.Label(self.content_frame, text="Waiting for Scans...", font=("Helvetica", 14), fg="green")
        lbl.pack(pady=20)
        
        self.log_display = tk.Text(self.content_frame, height=12, width=55, state="disabled")
        self.log_display.pack(pady=10)
        
        tk.Label(self.content_frame, text="Scanned data logs to rfid_logs_client.txt", fg="gray").pack()

    def setup_write_view(self):
        tk.Label(self.content_frame, text="Write User Data to Card", font=("Helvetica", 12, "bold")).grid(row=0, column=0, columnspan=2, pady=10)

        # Inputs
        tk.Label(self.content_frame, text="First Name:").grid(row=1, column=0, sticky="e", padx=5, pady=5)
        self.entry_fname = ttk.Entry(self.content_frame, width=30)
        self.entry_fname.grid(row=1, column=1, pady=5)

        tk.Label(self.content_frame, text="Last Name:").grid(row=2, column=0, sticky="e", padx=5, pady=5)
        self.entry_lname = ttk.Entry(self.content_frame, width=30)
        self.entry_lname.grid(row=2, column=1, pady=5)

        tk.Label(self.content_frame, text="Email Username:").grid(row=3, column=0, sticky="e", padx=5, pady=5)
        self.entry_email = ttk.Entry(self.content_frame, width=30)
        self.entry_email.grid(row=3, column=1, pady=5)

        tk.Label(self.content_frame, text="Is Officer:").grid(row=4, column=0, sticky="e", padx=5, pady=5)
        self.var_officer = tk.BooleanVar()
        self.chk_officer = ttk.Checkbutton(self.content_frame, variable=self.var_officer, text="Yes")
        self.chk_officer.grid(row=4, column=1, sticky="w", pady=5)

        self.btn_write = ttk.Button(self.content_frame, text="SEND WRITE COMMAND", command=self.handle_write)
        self.btn_write.grid(row=5, column=0, columnspan=2, pady=20)
        
        self.write_status = tk.Label(self.content_frame, text="", fg="blue")
        self.write_status.grid(row=6, column=0, columnspan=2)

    def handle_write(self):
        if not self.client.connected:
            messagebox.showerror("Error", "Not connected to Raspberry Pi.")
            return

        fname = self.entry_fname.get().strip()
        lname = self.entry_lname.get().strip()
        email = self.entry_email.get().strip()
        officer = str(self.var_officer.get())

        if not (fname and lname and email):
            messagebox.showwarning("Input Error", "Please fill in all text fields.")
            return

        data_str = f"{email},{fname},{lname},{officer}"
        
        self.btn_write.config(state="disabled")
        self.write_status.config(text="Sending command... Place card on Pi now.", fg="orange")
        self.client.send_write(data_str)

    # --- Callbacks ---
    def on_rfid_read(self, data):
        # Called from network thread, need to schedule UI update
        self.root.after(0, lambda: self._update_read_log(data))

    def _update_read_log(self, data):
        if self.mode == "READ":
            timestamp = datetime.datetime.now().strftime("%H:%M:%S")
            entry = f"[{timestamp}] READ: {data}"
            
            self.log_display.config(state="normal")
            self.log_display.insert(tk.END, entry + "\n")
            self.log_display.see(tk.END)
            self.log_display.config(state="disabled")
            
            # Log to file
            with open(LOG_FILE, "a") as f:
                f.write(f"{datetime.datetime.now()},{data}\n")

    def on_write_result(self, success, msg):
        self.root.after(0, lambda: self._update_write_status(success, msg))

    def _update_write_status(self, success, msg):
        if self.mode == "WRITE":
            self.btn_write.config(state="normal")
            if success:
                self.write_status.config(text=f"Success: {msg}", fg="green")
                messagebox.showinfo("Write Success", msg)
                self.entry_fname.delete(0, tk.END)
                self.entry_lname.delete(0, tk.END)
                self.entry_email.delete(0, tk.END)
                self.var_officer.set(False)
            else:
                self.write_status.config(text=f"Failed: {msg}", fg="red")
                messagebox.showerror("Write Failed", msg)

if __name__ == "__main__":
    root = tk.Tk()
    app = RFIDClientApp(root)
    root.mainloop()