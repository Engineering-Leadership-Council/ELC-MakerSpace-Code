import tkinter as tk
from tkinter import messagebox
import requests
import threading


WEBHOOK_URL = "https://discord.com/api/webhooks/1445861126955991130/oAQmu_vk43ctLwTHYmQR2LH-GSv7hVtASORYfcg9X1XxGl4R-vmCsz69ukjFp7WG-IGP"

ROLE_ID = "1015756793852477520" 

DISCORD_MESSAGE = {
    "content": f"This should ping people now! <@&{ROLE_ID}>",
    "username": "Mr Doorbell"
}

def send_ping_background():
    """Sends the request in a background thread to keep the GUI responsive."""
    try:
        if WEBHOOK_URL == "YOUR_WEBHOOK_URL_GOES_HERE" or WEBHOOK_URL == "":
            status_label.config(text="Error: Config URL missing", fg="red")
            messagebox.showerror("Configuration Error", "Please open the script and paste your Webhook URL.")
            return

        status_label.config(text="Sending...", fg="orange")
        
        response = requests.post(WEBHOOK_URL, json=DISCORD_MESSAGE)
        
        if response.status_code == 204:
            status_label.config(text="Message Sent!", fg="green")
            root.after(2000, lambda: status_label.config(text="Ready"))
        else:
            status_label.config(text="Failed", fg="red")
            messagebox.showerror("Error", f"Failed to send: {response.status_code}\n{response.text}")

    except requests.exceptions.MissingSchema:
        status_label.config(text="Config Error", fg="red")
        messagebox.showerror("Configuration Error", "Invalid Webhook URL format.\nPlease check the URL in the script.")
    except requests.exceptions.RequestException as e:
        status_label.config(text="Network Error", fg="red")
        messagebox.showerror("Network Error", f"Check your internet connection.\n{e}")

def on_button_click():
    """Wrapper to start the sending function in a thread."""
    send_button.config(state="disabled")
    
    threading.Thread(target=send_ping_background, daemon=True).start()

    root.after(1000, lambda: send_button.config(state="normal"))

# GUI SETUP

root = tk.Tk()
root.title("Discord Pinger")
root.geometry("300x200")
root.resizable(False, False)

title_label = tk.Label(root, text="Discord Notifier", font=("Helvetica", 16, "bold"))
title_label.pack(pady=20)

send_button = tk.Button(root, text="PUSH TO PING", font=("Arial", 14, "bold"), 
                        bg="#7289da", fg="white", height=2, width=15, 
                        command=on_button_click)
send_button.pack(pady=10)

status_label = tk.Label(root, text="Ready", font=("Arial", 10), fg="gray")
status_label.pack(side="bottom", pady=10)

root.mainloop()