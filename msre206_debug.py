import tkinter as tk
import serial
import time
import re
import random
from luhn import verify

# Standardized timeout value
DEFAULT_TIMEOUT = 5  # Set the timeout to 5 seconds

def log_debug_message(message):
    """Append a debug message to the debug window."""
    debug_text.config(state=tk.NORMAL)  # Enable the Text widget to modify its contents
    debug_text.insert(tk.END, message + "\n")
    debug_text.yview(tk.END)  # Auto-scroll to the bottom
    debug_text.config(state=tk.DISABLED)  # Disable the Text widget again

def connect_device():
    """Connect to the MSR206 device."""
    try:
        device = serial.Serial(port='/dev/ttyUSB0', baudrate=9600, timeout=DEFAULT_TIMEOUT)
        log_debug_message("Device connected successfully.")
        return device
    except Exception as e:
        log_debug_message(f"Connection error: {e}")
        return None

def send_command(device, command):
    """Send a command to the MSR206 device."""
    if device:
        log_debug_message(f"Sending command: {command.encode().hex()}")
        device.write(command.encode())
        time.sleep(0.1)
        response = device.read_all()  # Return raw bytes
        log_debug_message(f"Raw response: {response.hex()}")
        return response
    return b""

def parse_response(response):
    """Parse and display the status response from the MSR206 device."""
    status_codes = {
        b'0': "Operation successful.",
        b'1': "Write or read error.",
        b'2': "Command format error.",
        b'4': "Invalid command.",
        b'9': "Invalid card swipe when in write mode.",
    }
    if response.startswith(b'\x1B') and response.endswith(b'\x1B0'):
        log_debug_message("Response ends with status byte \x1B0, indicating success.")
        return "Operation successful."
    elif response.startswith(b'\x1B') and len(response) > 2:
        status = response[-1:]  # Extract the last byte as the status
        log_debug_message(f"Parsed status: {status}")
        return status_codes.get(status, f"Unknown status: {status.hex()}")
    log_debug_message("No valid response received.")
    return "No valid response received."

def read_until_complete(device):
    """Continuously read from the device until all data is captured."""
    data = b""
    timeout = DEFAULT_TIMEOUT
    start_time = time.time()
    while time.time() - start_time < timeout:
        chunk = device.read(1024)  # Read up to 1024 bytes at a time
        if chunk:
            log_debug_message(f"Read chunk: {chunk.hex()}")
            data += chunk
        else:
            break  # No more data available
    return data

def generate_credit_card(card_type):
    """Generate a valid credit card number for the given type."""
    prefixes = {
        "visa": ["4"],
        "mastercard": ["51", "52", "53", "54", "55"],
        "american_express": ["34", "37"],
        "discover": ["6011", "65"],
    }

    if card_type not in prefixes:
        raise ValueError("Unsupported card type.")

    prefix = random.choice(prefixes[card_type])
    length = 16 if card_type != "american_express" else 15

    while True:
        card_number = prefix + "".join(str(random.randint(0, 9)) for _ in range(length - len(prefix) - 1))
        checksum = sum(int(d) if i % 2 == 0 else sum(divmod(int(d) * 2, 10))
                       for i, d in enumerate(reversed(card_number))) % 10
        card_number += str((10 - checksum) % 10)
        if verify(card_number):
            return card_number

def generate_card_tracks(card_number, card_type):
    """Generate track 1 and track 2 data for a given card number and type."""
    name = "CARDHOLDER/NAME"  # Placeholder name
    expiration_date = "2512"  # MMYY format for expiration (placeholder)
    service_code = "101"  # Standard service code (placeholder)

    track1 = f"%B{card_number}^{name}^{expiration_date}{service_code}?"
    track2 = f";{card_number}={expiration_date}{service_code}?"

    return track1, track2

def write_card_with_generated_number():
    """Write a generated credit card number to the MSR206 device and display tracks."""
    card_type = card_type_var.get().lower()
    try:
        card_number = generate_credit_card(card_type)
        log_debug_message(f"Generated {card_type.capitalize()} card number: {card_number}")

        track1, track2 = generate_card_tracks(card_number, card_type)
        track1_var.set(track1)
        track2_var.set(track2)

        device = connect_device()
        if not device:
            return

        command = f'\x1Bw\x1Bs\x1B\x01{track1}\x1B\x02{track2}\x1C'  # Build write command with tracks
        log_debug_message(f"Write command: {command.encode().hex()}")
        response = send_command(device, command)
        status_message = parse_response(response)

        if "successful" in status_message:
            log_debug_message("Card number written successfully.")
        else:
            log_debug_message(f"Error: {status_message}")

        device.close()
    except ValueError as e:
        log_debug_message(f"Error: {e}")

def read_card():
    """Read data from a magnetic card."""
    device = connect_device()
    if not device:
        return

    log_debug_message("Please swipe your card.")

    send_command(device, '\x1Br')  # Send read command
    response = read_until_complete(device)

    if response:
        log_debug_message(f"Raw Response: {response}")
        try:
            decoded_response = response.decode()
            log_debug_message(f"Decoded response: {decoded_response}")
            
            cleaned_response = re.sub(r'\x1B[^␛x1B[^\x1B[^ x1B[^\x20-\x7E]*', '', decoded_response)
            log_debug_message(f"Cleaned response: {cleaned_response}")
            
            tracks = cleaned_response.split('?')
            if len(tracks) >= 1:
                track1_var.set(tracks[0].strip())
            if len(tracks) >= 2:
                track2_var.set(tracks[1].strip())
            if len(tracks) >= 3:
                track3_var.set(tracks[2].strip())
        except UnicodeDecodeError:
            log_debug_message(f"Failed to decode the response. Raw data: {response.hex()}")
    else:
        log_debug_message("No data received from the card.")
    device.close()

def write_card():
    """Write data to a magnetic card."""
    device = connect_device()
    if not device:
        return

    log_debug_message("Please swipe your card for writing.")

    track1 = track1_var.get()
    track2 = track2_var.get()
    track3 = track3_var.get()

    command = f'\x1Bw\x1Bs\x1B\x01{track1}\x1B\x02{track2}\x1B\x03{track3}?\x1C'  # Build write command
    log_debug_message(f"Write command: {command.encode().hex()}")
    response = send_command(device, command)
    status_message = parse_response(response)
    
    if "successful" in status_message:
        log_debug_message("Data written successfully.")
    else:
        log_debug_message(f"Error: {status_message}")

    device.close()

def read_raw_data():
    """Read raw data from a magnetic card."""
    device = connect_device()
    if not device:
        return

    send_command(device, '\x1Bm')  # Send read raw data command
    response = read_until_complete(device)

    if response:
        log_debug_message(f"Raw Response: {response}")
        raw_data_var.set(response.hex())
    else:
        log_debug_message("No data received from the card.")
    device.close()

def write_raw_data():
    """Write raw data to a magnetic card."""
    device = connect_device()
    if not device:
        return

    raw_data = raw_data_var.get()

    command = f'\x1Bn{raw_data}\x1C'  # Build write raw data command
    log_debug_message(f"Write raw data command: {command.encode().hex()}")
    response = send_command(device, command)
    status_message = parse_response(response)

    if "successful" in status_message:
        log_debug_message("Raw data written successfully.")
    else:
        log_debug_message(f"Error: {status_message}")

    device.close()

def set_lo_co():
    """Set the device to LO-CO mode."""
    device = connect_device()
    if not device:
        return

    response = send_command(device, '\x1By')  # Send LO-CO command
    status_message = parse_response(response)
    if "successful" in status_message:
        log_debug_message("Set to LO-CO successfully.")
    else:
        log_debug_message(f"Error: {status_message}")

    device.close()

def set_hi_co():
    """Set the device to HI-CO mode."""
    device = connect_device()
    if not device:
        return

    response = send_command(device, '\x1Bx')  # Send HI-CO command
    status_message = parse_response(response)
    if "successful" in status_message:
        log_debug_message("Set to HI-CO successfully.")
    else:
        log_debug_message(f"Error: {status_message}")

    device.close()

def reset_device():
    """Reset the MSR206 device."""
    device = connect_device()
    if not device:
        return

    response = send_command(device, '\x1Ba')  # Reset command
    if response:
        log_debug_message("Device reset successfully.")
    else:
        log_debug_message("Failed to reset the device.")

    device.close()

# Create the main GUI window
root = tk.Tk()
root.title("MSR206 Magnetic Card Reader/Writer")

# Variables to hold track data
track1_var = tk.StringVar()
track2_var = tk.StringVar()
track3_var = tk.StringVar()
raw_data_var = tk.StringVar()
card_type_var = tk.StringVar(value="visa")

# Layout
tk.Label(root, text="Track 1:").grid(row=0, column=0, sticky="w")
tk.Entry(root, textvariable=track1_var, width=40).grid(row=0, column=1)

tk.Label(root, text="Track 2:").grid(row=1, column=0, sticky="w")
tk.Entry(root, textvariable=track2_var, width=40).grid(row=1, column=1)

tk.Label(root, text="Track 3:").grid(row=2, column=0, sticky="w")
tk.Entry(root, textvariable=track3_var, width=40).grid(row=2, column=1)

tk.Label(root, text="Raw Data:").grid(row=3, column=0, sticky="w")
tk.Entry(root, textvariable=raw_data_var, width=40).grid(row=3, column=1)

tk.Label(root, text="Card Type:").grid(row=4, column=0, sticky="w")
tk.OptionMenu(root, card_type_var, "visa", "mastercard", "american_express", "discover").grid(row=4, column=1)

# Debug window
debug_text = tk.Text(root, height=15, width=80, wrap=tk.WORD, state=tk.DISABLED)
debug_text.grid(row=5, column=0, columnspan=2, pady=10)

# Buttons
tk.Button(root, text="Read Card", command=read_card).grid(row=6, column=0, pady=10)
tk.Button(root, text="Write Card", command=write_card).grid(row=6, column=1, pady=10)

tk.Button(root, text="Read Raw Data", command=read_raw_data).grid(row=7, column=0, pady=10)
tk.Button(root, text="Write Raw Data", command=write_raw_data).grid(row=7, column=1, pady=10)

tk.Button(root, text="Generate and Write Card", command=write_card_with_generated_number).grid(row=8, column=0, pady=10, columnspan=2)

tk.Button(root, text="Set LO-CO", command=set_lo_co).grid(row=9, column=0, pady=10)
tk.Button(root, text="Set HI-CO", command=set_hi_co).grid(row=9, column=1, pady=10)

tk.Button(root, text="Reset Device", command=reset_device).grid(row=10, column=0, pady=10)

# Exit button
tk.Button(root, text="Exit", command=root.quit).grid(row=10, column=1, pady=10)

root.mainloop()
