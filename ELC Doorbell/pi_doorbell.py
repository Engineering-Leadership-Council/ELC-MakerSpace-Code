import requests
from gpiozero import Button
from signal import pause
import time

# Default is GPIO 17 (Physical Pin 11)
BUTTON_PIN = 17

WEBHOOK_URL = "https://discord.com/api/webhooks/1445861126955991130/oAQmu_vk43ctLwTHYmQR2LH-GSv7hVtASORYfcg9X1XxGl4R-vmCsz69ukjFp7WG-IGP"

ROLE_ID = "1015756793852477520" 

DISCORD_MESSAGE = {
    "content": f"The ELC MakerSpace is Open! (Room 3-132) <@&{ROLE_ID}>",
    "username": "Mr Doorbell"
}

def send_ping():
    """Sends the request to Discord when the button is pressed."""
    print("Button pressed! Sending message...")
    
    try:
        if WEBHOOK_URL == "YOUR_WEBHOOK_URL_GOES_HERE" or WEBHOOK_URL == "":
            print("Error: Config URL missing. Please edit the script.")
            return

        response = requests.post(WEBHOOK_URL, json=DISCORD_MESSAGE)
        
        if response.status_code == 204:
            print("Message Sent Successfully!")
        else:
            print(f"Failed to send: {response.status_code}")
            print(response.text)

    except requests.exceptions.MissingSchema:
        print("Error: Invalid Webhook URL format.")
    except requests.exceptions.RequestException as e:
        print(f"Network Error: {e}")

def main():
    print(f"Doorbell System Active.")
    print(f"Monitoring Button on GPIO {BUTTON_PIN}...")
    print("Press Ctrl+C to exit.")

    # Initialize the button
    # bounce_time prevents multiple signals from a single press (debouncing)
    button = Button(BUTTON_PIN, bounce_time=0.1)
    
    # Assign the function to run when the button is pressed
    button.when_pressed = send_ping

    # Keep the script running to listen for events
    pause()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nExiting...")
