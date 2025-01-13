import tkinter as tk
import serial
import time
import re
import random
from luhn import append, verify

# Standardized timeout value
DEFAULT_TIMEOUT = 5  # Set the timeout to 5 seconds

def connect_device():
    """Connect to the MSR206 device."""
    try:
        device = serial.Serial(port='/dev/ttyUSB0', baudrate=9600, timeout=DEFAULT_TIMEOUT)
        print("Device connected successfully.")  # Debug log
        return device
    except Exception as e:
        print(f"Connection error: {e}")  # Debug log
        return None

def send_command(device, command):
    """Send a command to the MSR206 device."""
    if device:
        print(f"Sending command: {command.encode().hex()}")  # Debug log
        device.write(command.encode())
        time.sleep(0.1)
        response = device.read_all()  # Return raw bytes
        print(f"Raw response: {response.hex()}")  # Debug log
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
        print("Response ends with status byte \x1B0, indicating success.")  # Debug log
        return "Operation successful."
    elif response.startswith(b'\x1B') and len(response) > 2:
        status = response[-1:]  # Extract the last byte as the status
        print(f"Parsed status: {status}")  # Debug log
        return status_codes.get(status, f"Unknown status: {status.hex()}")
    print("No valid response received.")  # Debug log
    return "No valid response received."

def read_until_complete(device):
    """Continuously read from the device until all data is captured."""
    data = b""
    timeout = DEFAULT_TIMEOUT
    start_time = time.time()
    while time.time() - start_time < timeout:
        chunk = device.read(1024)  # Read up to 1024 bytes at a time
        if chunk:
            print(f"Read chunk: {chunk.hex()}")  # Debug log
            data += chunk
        else:
            break  # No more data available
    return data

def read_card():
    """Read data from a magnetic card."""
    device = connect_device()
    if not device:
        return

    print("Please swipe your card.")  # Prompt replaced with a console message

    send_command(device, '\x1Br')  # Send read command
    response = read_until_complete(device)

    if response:
        print(f"Raw Response: {response}")  # Debugging raw response
        try:
            # Decode response to string and remove control characters
            decoded_response = response.decode()
            print(f"Decoded response: {decoded_response}")  # Debug log
            
            # Remove unnecessary control sequences using regex
            cleaned_response = re.sub(r'\x1B[^\x1B[^\x20-\x7E]*', '', decoded_response)
            print(f"Cleaned response: {cleaned_response}")  # Debug log
            
            # Split into tracks
            tracks = cleaned_response.split('?')
            if len(tracks) >= 1:
                track1_var.set(tracks[0].strip())
            if len(tracks) >= 2:
                track2_var.set(tracks[1].strip())
            if len(tracks) >= 3:
                track3_var.set(tracks[2].strip())
        except UnicodeDecodeError:
            print(f"Failed to decode the response. Raw data: {response.hex()}")  # Error message logged
    else:
        print("No data received from the card.")  # Warning logged
    device.close()

def write_card():
    """Write data to a magnetic card."""
    device = connect_device()
    if not device:
        return

    print("Please swipe your card for writing.")  # Prompt replaced with a console message

    track1 = track1_var.get()
    track2 = track2_var.get()
    track3 = track3_var.get()

    command = f'\x1Bw\x1Bs\x1B\x01{track1}\x1B\x02{track2}\x1B\x03{track3}?\x1C'  # Build write command
    print(f"Write command: {command.encode().hex()}")  # Debug log
    response = send_command(device, command)
    status_message = parse_response(response)
    
    if "successful" in status_message:
        print("Data written successfully.")
    else:
        print(f"Error: {status_message}")

    device.close()

def generate_credit_card():
    """Generate credit card data and populate Track 1 and Track 2."""
    prefixes = {
        "Visa": ["4"],
        "MasterCard": ["51", "52", "53", "54", "55"],
        "American Express": ["34", "37"],
        "Discover": ["6011", "622126", "622127", "622128", "622129", "62213", "62214", "62215", "62216", "62217", "62218", "62219", "6222", "6223", "6224", "6225", "6226", "6227", "6228", "62290", "62291", "622920", "622921", "622922", "622923", "622924", "622925"],
    }
    lengths = {
        "Visa": 16,
        "MasterCard": 16,
        "American Express": 15,
        "Discover": 16,
    }

    card_type = "Visa"  # Default to Visa; adjust as needed
    prefix = random.choice(prefixes[card_type])
    length = lengths[card_type]

    remaining_length = length - len(prefix) - 1
    partial_number = prefix + ''.join(random.choice('0123456789') for _ in range(remaining_length))
    card_number = append(partial_number)

    if verify(card_number):
        name = "CARDHOLDER"  # Example name for Track 1
        expiry = f"{random.randint(23, 30):02}{random.randint(1, 12):02}"  # YYMM format
        service_code = "101"  # Example service code

        track1 = f"%B{card_number}^{name}/{expiry}^{service_code}?"
        track2 = f";{card_number}={expiry}{service_code}?"

        track1_var.set(track1)
        track2_var.set(track2)
        print("Generated Credit Card:")
        print(f"Card Number: {card_number}")
        print(f"Track 1: {track1}")
        print(f"Track 2: {track2}")
    else:
        print("Failed to generate valid credit card data.")

def read_raw_data():
    """Read raw data from a magnetic card."""
    device = connect_device()
    if not device:
        return

    send_command(device, '\x1Bm')  # Send read raw data command
    response = read_until_complete(device)

    if response:
        print(f"Raw Response: {response}")  # Debugging raw response
        raw_data_var.set(response.hex())  # Display raw data as hex string
    else:
        print("No data received from the card.")  # Warning logged
    device.close()

def write_raw_data():
    """Write raw data to a magnetic card."""
    device = connect_device()
    if not device:
        return

    raw_data = raw_data_var.get()

    command = f'\x1Bn{raw_data}\x1C'  # Build write raw data command
    print(f"Write raw data command: {command.encode().hex()}")  # Debug log
    response = send_command(device, command)
    status_message = parse_response(response)

    if "successful" in status_message:
        print("Raw data written successfully.")
    else:
        print(f"Error: {status_message}")

    device.close()

def set_lo_co():
    """Set the device to LO-CO mode."""
    device = connect_device()
    if not device:
        return

    response = send_command(device, '\x1By')  # Send LO-CO command
    status_message = parse_response(response)
    if "successful" in status_message:
        print("Set to LO-CO successfully.")
    else:
        print(f"Error: {status_message}")

    device.close()

def set_hi_co():
    """Set the device to HI-CO mode."""
    device = connect_device()
    if not device:
        return

    response = send_command(device, '\x1Bx')  # Send HI-CO command
    status_message = parse_response(response)
    if "successful" in status_message:
        print("Set to HI-CO successfully.")
    else:
        print(f"Error: {status_message}")

    device.close()

def reset_device():
    """Reset the MSR206 device."""
    device = connect_device()
    if not device:
        return

    response = send_command(device, '\x1Ba')  # Reset command
    if response:
        print("Device reset successfully.")
    else:
        print("Failed to reset the device.")

    device.close()

# Create the main GUI window
root = tk.Tk()
root.title("MSR206 Magnetic Card Reader/Writer with Generator")

# Variables to hold track data
track1_var = tk.StringVar()
track2_var = tk.StringVar()
track3_var = tk.StringVar()
raw_data_var = tk.StringVar()

# Layout
tk.Label(root, text="Track 1:").grid(row=0, column=0, sticky="w")
tk.Entry(root, textvariable=track1_var, width=40).grid(row=0, column=1)

tk.Label(root, text="Track 2:").grid(row=1, column=0, sticky="w")
tk.Entry(root, textvariable=track2_var, width=40).grid(row=1, column=1)

tk.Label(root, text="Track 3:").grid(row=2, column=0, sticky="w")
tk.Entry(root, textvariable=track3_var, width=40).grid(row=2, column=1)

tk.Label(root, text="Raw Data:").grid(row=3, column=0, sticky="w")
tk.Entry(root, textvariable=raw_data_var, width=40).grid(row=3, column=1)

# Buttons
tk.Button(root, text="Read Card", command=read_card).grid(row=4, column=0, pady=10)
tk.Button(root, text="Write Card", command=write_card).grid(row=4, column=1, pady=10)

tk.Button(root, text="Read Raw Data", command=read_raw_data).grid(row=5, column=0, pady=10)
tk.Button(root, text="Write Raw Data", command=write_raw_data).grid(row=5, column=1, pady=10)

tk.Button(root, text="Generate Credit Card", command=generate_credit_card).grid(row=6, column=0, columnspan=2, pady=10)

tk.Button(root, text="Set LO-CO", command=set_lo_co).grid(row=7, column=0, pady=10)
tk.Button(root, text="Set HI-CO", command=set_hi_co).grid(row=7, column=1, pady=10)

tk.Button(root, text="Reset Device", command=reset_device).grid(row=8, column=0, pady=10)

root.mainloop()

