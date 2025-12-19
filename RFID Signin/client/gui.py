import tkinter as tk
from tkinter import messagebox, ttk, simpledialog
import os
import ctypes
import sys
import datetime

from .config import (
    MCC_BLACK, HEADER_BLACK, MCC_GOLD, TEXT_WHITE, ERROR_RED, SUCCESS_GREEN, ACTION_BLUE,
    ADMIN_PASSCODE, BACKUP_CSV, LAST_IP
)
from .network import NetworkClient
from .theme import apply_styles
from .logic import OfficerManager, process_scan_data, append_to_backup, export_logs_to_excel, update_last_ip


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
        self.officer_manager = OfficerManager()

        self.mode = "READ"
        self.scan_action = "SIGN IN" 
        self.log_data = [] 
        self.last_export_date = None
        self.clear_timer = None

        # Load last IP
        self.last_ip = LAST_IP


        apply_styles()
        self.setup_ui()
        
        # Auto-connect silently on startup
        self.root.after(500, self.silent_connect)
        
        # Start Auto-Export Scheduler
        self.check_auto_export()

        # Handle Window Close Explicity
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def on_close(self):
        """ Cleanup threads and connections on exit """
        self.officer_manager.cleanup()
        self.client.disconnect()
        self.root.destroy()
        sys.exit(0)

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
        
        self.mode_var = tk.StringVar(value="READ MODE")
        
        self.mode_combo = ttk.Combobox(self.mode_frame, textvariable=self.mode_var, 
                                       values=["READ MODE", "ADMIN PANEL"], state="readonly", font=('Segoe UI', 12))
        self.mode_combo.pack(padx=30, pady=5)
        self.mode_combo.bind("<<ComboboxSelected>>", self.change_mode)

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
            update_last_ip(ip) # Update .env
                
            self.lbl_connection.config(text=f"Connecting to {ip}...", foreground=MCC_GOLD)

            self.root.update()
            
            success, msg = self.client.connect(ip)
            if success:
                self.lbl_connection.config(text=f"Connected to {ip}", foreground=SUCCESS_GREEN)
            else:
                self.lbl_connection.config(text=f"Failed: {msg}", foreground=ERROR_RED)
                messagebox.showerror("Connection Error", f"Could not connect to {ip}.\n{msg}")

    def change_mode(self, event=None):
        selection = self.mode_var.get()
        new_mode = "READ" if selection == "READ MODE" else "WRITE"

        if self.mode == new_mode:
            return

        if new_mode == "WRITE":
            pwd = simpledialog.askstring("Admin Access", "Enter Admin Passcode:", show='*')
            if pwd != ADMIN_PASSCODE:
                messagebox.showerror("Access Denied", "Incorrect passcode.")
                self.mode_var.set("READ MODE")
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

    def toggle_action(self):
        if self.scan_action == "SIGN IN":
            self.scan_action = "SIGN OUT"
            self.btn_action.config(text="CURRENTLY: SIGN OUT", bg=ACTION_BLUE) 
        else:
            self.scan_action = "SIGN IN"
            self.btn_action.config(text="CURRENTLY: SIGN IN", bg=SUCCESS_GREEN)

    def _update_read_log(self, data):
        if self.mode == "READ":
            # State Management: Parse Data
            # Note: process_scan_data handles parsing. Officer Manager handles checks.
            record = process_scan_data(data, self.scan_action)
            
            # Logic: Check Officer
            if self.officer_manager.check_and_welcome(record['Email']):
                pass # Triggered in check

            # Memory & File Log
            self.log_data.append(record)
            append_to_backup(record)
            
            # Update UI
            fname = record.get("First Name", "Unknown")
            lname = record.get("Last Name", "")
            action = record.get("Action", "Scan")
            timestamp = record.get("Time", "")
            
            if fname != "Unknown":
                self.lbl_welcome_header.config(text=f"Welcome {fname} {lname} to the\nEngineering Leadership Council MakerSpace")
                self.lbl_name.config(text=f"{fname} {lname}", foreground=SUCCESS_GREEN)
            else:
                self.lbl_welcome_header.config(text="Welcome to the\nEngineering Leadership Council MakerSpace")
                self.lbl_name.config(text="Unknown Card", foreground=ERROR_RED)

            self.lbl_status_msg.config(text=f"{action} Recorded at {timestamp}")
            
            # Reset Timer
            if self.clear_timer:
                self.root.after_cancel(self.clear_timer)
            self.clear_timer = self.root.after(5000, self.clear_display)

    def clear_display(self):
        """ Resets the display to waiting state """
        if self.mode == "READ":
            self.lbl_welcome_header.config(text="Welcome to the\nEngineering Leadership Council MakerSpace")
            self.lbl_name.config(text="Please Scan Card", foreground="white")
            self.lbl_status_msg.config(text="")
            self.clear_timer = None

    # --- EXPORT LOGIC ---
    def check_auto_export(self):
        now = datetime.datetime.now()
        # Check if it's 11:59 PM (23:59)
        if now.hour == 23 and now.minute == 59:
            today_str = now.strftime("%Y-%m-%d")
            if self.last_export_date != today_str:
                self.manual_export()
                self.last_export_date = today_str
        
        # Check every 30 seconds
        self.root.after(30000, self.check_auto_export)

    def manual_export(self):
        success, msg = export_logs_to_excel(self.log_data)
        if success:
            self.log_data = [] # Clear memory
            if os.path.exists(BACKUP_CSV):
                os.remove(BACKUP_CSV)
            if self.mode == "READ":
                 messagebox.showinfo("Auto-Export", f"Daily log exported successfully to:\n{msg}")
        else:
            print(f"Export Log: {msg}")
            if self.mode == "READ" and msg != "No data to export.":
                 messagebox.showerror("Export Failed", msg)

    # --- ADMIN VIEW ---
    def setup_write_view(self):
        net_frame = ttk.LabelFrame(self.content_frame, text="Network Configuration", padding=15)
        net_frame.pack(fill="x", pady=(0, 20))
        
        ttk.Label(net_frame, text=f"Current Target IP: {self.last_ip}").pack(side="left", padx=(0, 10))
        ttk.Button(net_frame, text="Change IP & Connect", command=self.prompt_connection, width=20).pack(side="left", padx=5)
        ttk.Button(net_frame, text="Force Export Log", command=self.manual_export, width=20).pack(side="left", padx=5)
        
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
