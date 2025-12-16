#!/usr/bin/env python3
import RPi.GPIO as GPIO
from mfrc522 import SimpleMFRC522
import time

print("--- Hardware Test Script ---")
print("Press CTRL+C to stop.")

try:
    reader = SimpleMFRC522()
    print("Reader initialized. Please place a card...")
    
    while True:
        try:
            # simple read() blocks until a card is found
            id, text = reader.read()
            print(f"SUCCESS! ID: {id}")
            print(f"Data: {text}")
            print("-----------------------------")
            # Sleep a bit to prevent crazy scroll
            time.sleep(2)
        except Exception as e:
            print(f"Error reading: {e}")
            time.sleep(1)
            
except KeyboardInterrupt:
    print("\nTest stopped.")
finally:
    GPIO.cleanup()
