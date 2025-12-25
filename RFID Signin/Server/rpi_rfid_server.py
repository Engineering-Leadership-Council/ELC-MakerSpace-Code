#!/usr/bin/env python3
import socket
import threading
import json
import time
import sys
import queue
import os

# --- Hardware Imports ---
import RPi.GPIO as GPIO
from mfrc522 import SimpleMFRC522

# --- Configuration ---
HOST = '0.0.0.0'
PORT = 65432

class RFIDServer:
    def __init__(self):
        self.running = True
        self.client_socket = None
        self.lock = threading.Lock()
        self.command_queue = queue.Queue()
        self.reader = SimpleMFRC522()

    def check_hardware_connection(self):
        try:
            version = self.reader.READER.Read_MFRC522(0x37)
            print(f"[STARTUP] MFRC522 Version: {hex(version)}")
            if version == 0x00 or version == 0xFF:
                return False, f"Invalid Version {hex(version)} (Check Wiring!)"
            elif version in [0x90, 0x91, 0x92]:
                return True, "Connection OK"
            else:
                return True, f"Unknown Version {hex(version)} (Might work)"
        except Exception as e:
            return False, str(e)

    def start(self):
        ok, msg = self.check_hardware_connection()
        if not ok:
            print(f"[CRITICAL ERROR] {msg}")
            sys.exit(1)
        else:
            print(f"[HARDWARE] {msg}")

        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            self.server_socket.bind((HOST, PORT))
            self.server_socket.listen()
            print(f"[SERVER] Listening on {HOST}:{PORT}")
        except Exception as e:
            print(f"[ERROR] Bind failed: {e}")
            sys.exit(1)

        self.hw_thread = threading.Thread(target=self.hardware_loop, daemon=True)
        self.hw_thread.start()

        print("[READY] System is live.")

        while self.running:
            try:
                conn, addr = self.server_socket.accept()
                with self.lock:
                    self.client_socket = conn
                print(f"[SERVER] Client Connected: {addr}")
                self.handle_client(conn)
            except KeyboardInterrupt:
                self.stop()
            except Exception as e:
                print(f"[ERROR] Connection loop: {e}")
                time.sleep(1)

    def stop(self):
        self.running = False
        GPIO.cleanup()
        sys.exit(0)

    def handle_client(self, conn):
        buffer = ""
        try:
            while self.running:
                data = conn.recv(1024)
                if not data: break
                buffer += data.decode('utf-8')
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    if not line: continue
                    self.process_command(line)
        except:
            pass
        finally:
            print("[SERVER] Client disconnected.")
            with self.lock:
                self.client_socket = None
            conn.close()

    def process_command(self, line):
        try:
            cmd = json.loads(line)
            action = cmd.get("action")
            if action == "write":
                content = cmd.get("content", "")
                print(f"[CMD] Queuing Write request...")
                self.command_queue.put(content)
        except json.JSONDecodeError:
            pass

    def send_to_client(self, payload):
        with self.lock:
            if self.client_socket:
                try:
                    msg = json.dumps(payload) + "\n"
                    self.client_socket.sendall(msg.encode('utf-8'))
                except:
                    pass

    def hardware_loop(self):
        while self.running:
            if not self.command_queue.empty():
                try:
                    text_to_write = self.command_queue.get_nowait()
                    self.perform_write(text_to_write)
                except queue.Empty:
                    pass
            else:
                self.perform_scan()
            time.sleep(0.1)

    def blink_onboard_led(self):
        """Blinks the Raspberry Pi onboard ACT LED."""
        led_path = None
        # Common paths for Pi LEDs
        for path in ["/sys/class/leds/ACT", "/sys/class/leds/led0"]:
            if os.path.exists(path):
                led_path = path
                break
        
        if not led_path:
            return 

        try:
            # Save current trigger
            prev_trigger = "mmc0" # Default safe assumption
            try:
                with open(f"{led_path}/trigger", "r") as f:
                    content = f.read().strip()
                    # Trigger file format is like: none [mmc0] heartbeat
                    if "[" in content:
                        prev_trigger = content.split("[")[1].split("]")[0]
                    else:
                        prev_trigger = content
            except:
                pass # Use default if read fails

            # Sequence: Off -> On -> Off -> On -> Restore
            # Set to none to control brightness manually
            with open(f"{led_path}/trigger", "w") as f:
                f.write("none")
            
            # Blink pattern
            for _ in range(2):
                with open(f"{led_path}/brightness", "w") as f:
                    f.write("1")
                time.sleep(0.1)
                with open(f"{led_path}/brightness", "w") as f:
                    f.write("0")
                time.sleep(0.1)

            # Restore trigger
            with open(f"{led_path}/trigger", "w") as f:
                f.write(prev_trigger)
                
        except Exception as e:
            print(f"[HW] LED Blink Warning: {e}")

    def perform_write(self, text):
        print(f"[HW] Writing: '{text}' (Place card within 15s)")
        start_time = time.time()
        success = False
        msg = "Timed out"
        
        while (time.time() - start_time) < 15:
            uid = self.check_card_presence()
            if uid:
                try:
                    print(f"[HW] Card found {uid}. Writing...")
                    self.reader.write(text)
                    success = True
                    msg = "Write Successful"
                    print("[HW] Write Complete!")
                    self.blink_onboard_led()
                    break
                except Exception as e:
                    # Catch Auth Error specifically if possible, logic is generic here
                    err_str = str(e)
                    print(f"[HW] Write Error: {err_str}")
                    if "auth" in err_str.lower() or "0x8" in err_str:
                        print("     -> Hint: Try holding card still or use a new card.")
                    time.sleep(0.5)
            time.sleep(0.1)
            
        self.send_to_client({"type": "WRITE_RESULT", "success": success, "msg": msg})
        if success: time.sleep(2)

    def perform_scan(self):
        uid = self.check_card_presence()
        if uid:
            try:
                id, text = self.reader.read()
                data = text.strip()
                print(f"[HW] Read: {data}")
                self.blink_onboard_led()
                self.send_to_client({"type": "READ", "data": data})
                time.sleep(2)
            except Exception as e:
                err_str = str(e)
                # Filter out spammy errors mostly
                if "auth" in err_str.lower():
                     print("[HW] Read Auth Error: Authentication Failed (Bad Key or Bad Read)")
                else:
                     print(f"[HW] Read Error: {e}")
                time.sleep(1)

    def check_card_presence(self):
        try:
            reader = self.reader.READER
            (status, TagType) = reader.MFRC522_Request(reader.PICC_REQIDL)
            if status != reader.MI_OK: return None
            (status, uid) = reader.MFRC522_Anticoll()
            if status != reader.MI_OK: return None
            return uid
        except:
            return None

if __name__ == "__main__":
    server = RFIDServer()
    server.start()
