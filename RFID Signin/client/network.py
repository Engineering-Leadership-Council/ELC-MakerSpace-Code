import socket
import threading
import json
from .config import DEFAULT_PORT

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
