#!/usr/bin/env python3
import RPi.GPIO as GPIO
from mfrc522 import SimpleMFRC522
import spidev
import os

print("--- Deep Diagnostic Tool ---")

# 1. Check SPI Device
if not os.path.exists("/dev/spidev0.0"):
    print("[FAIL] /dev/spidev0.0 not found!")
    print("       Enable SPI in raspi-config and reboot.")
    exit(1)
print("[PASS] SPI device found.")

# 2. Check Connection
try:
    reader = SimpleMFRC522()
    # Access the low-level MFRC522 object
    raw_reader = reader.READER
    
    # Read the Version Register (0x37)
    # The library might name it differently, but command is Read_MFRC522(addr)
    # 0x37 is the VersionReg
    version = raw_reader.Read_MFRC522(0x37)
    
    print(f"[INFO] Version Register Value: {hex(version)}")
    
    if version == 0x00 or version == 0xFF:
        print("[FAIL] Communication Failed (Value is 0x00 or 0xFF)")
        print("       Check wiring: SDA(24), SCK(23), MOSI(19), MISO(21)")
        print("       Check Power: 3.3V(17), GND(20)")
        print("       Check RST: GPIO 25 (Pin 22)")
    elif version in [0x91, 0x92]:
        print(f"[PASS] Hardware Detected! (Version v{hex(version)})")
        print("       If 'read()' still hangs, try moving the card closer/further.")
    else:
        print(f"[WARN] Unknown Version: {hex(version)}. Connection might be weak.")

except Exception as e:
    print(f"[ERROR] Exception during check: {e}")

finally:
    GPIO.cleanup()
