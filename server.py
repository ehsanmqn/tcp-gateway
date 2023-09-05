import datetime
import socket
import threading
import requests
import binascii
import struct
import json
import logging

# Configure the root logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Define the address and port to listen on
HOST = '0.0.0.0'  # Listen on all available network interfaces
PORT = 2205

# Define the REST API URL where you want to send the data
API_URL = 'http://192.168.200.72:9000/api/lorawan/webhook/uplink/gsm'

# Dictionary to store client IMEI as identifiers
client_identifiers = {}

message_types = {
    "f0": "Request Connection",
    "f1": "Connection Reply",
    "02": "Alarm Data Upload",
    "65": "Heartrate Upload",
    "c2": "Heartrate and Blood Upload",
    "16": "Alarm Information",
    "f9": "Heartbeat Packet",
    "a4": "WiFi and Signal Information",
    "f3": "SIM ICCID",
    "c5": "Device Sleep Analysis",
    "ba": "Multi Temperature",
    "c6": "Blood Oxygen",
    "bb": "Software Version",
    "LBE": "Bluetooth Positioning",
    "c0": "Downlink Feedback",
    "28": "Message Status Reporting",
    "32": "Health Data"
}


def generate_little_endian_timestamp():
    """
    Generate a 4-byte little-endian timestamp.

    Returns:
    bytes: The generated timestamp as bytes.
    """
    # Get the current local time
    current_time = datetime.datetime.utcnow() - datetime.timedelta(hours=1)

    # Convert the current time to a Unix timestamp (seconds since epoch)
    timestamp = int(current_time.timestamp())

    # Convert the timestamp to little-endian bytes
    timestamp_bytes = struct.pack("<I", timestamp)
    return timestamp_bytes


def calculate_checksum(data):
    """
    Calculate the checksum for the given data buffer.

    Args:
    data (bytes): The data buffer for which to calculate the checksum.

    Returns:
    int: The calculated checksum value.
    """
    ck_sum = 0
    for byte in data:
        ck_sum = (ck_sum + byte) % 0x100
    ck_sum = 0xFF - ck_sum
    return ck_sum


def create_lnklin_buffer():
    """
    Function to create the liklin buffer
    :return:
    """
    timestamp = generate_little_endian_timestamp()
    message_id = b'\xF1'
    payload = b'\xBD\xBD\xBD\xBD'
    data_buffer = timestamp + message_id + payload
    checksum = calculate_checksum(data_buffer)
    data_buffer = timestamp + message_id + payload + bytes([checksum])
    return data_buffer


def create_periodic_upload_buffer():
    """
    Function to create the periodic upload buffer
    :return:
    """
    message_id = b'\x17'
    header = b'\xBD\xBD\xBD\xBD'
    payload = b'\x01\x01\x00\x00\x00\x17\x3b\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    data_buffer = header + message_id + payload
    checksum = calculate_checksum(data_buffer)
    data_buffer = data_buffer + bytes([checksum])
    return data_buffer


def create_heartbeat_response_buffer():
    """
    Function to create the heartbeat response buffer
    :return:
    """
    message_id = b'\xF9'
    header = b'\xBD\xBD\xBD\xBD'
    payload = b'\x01'
    data_buffer = header + message_id + payload
    checksum = calculate_checksum(data_buffer)
    data_buffer = data_buffer + bytes([checksum])
    return data_buffer


def send_data_to_api(data, imei):
    """
    Function to send data to the REST API
    :param data:
    :param imei:
    :return:
    """
    try:
        hex_data = str(binascii.hexlify(data))[2:-1]
        json_payload = json.dumps({
            "data": {
                "hex": [hex_data[i:i + 2] for i in range(0, len(hex_data), 2)]
            },
            "imei": str(imei)
        })

        headers = {
            'Content-Type': 'application/json',
            "X-IMEI": str(imei)
        }

        response = requests.post(API_URL, data=json_payload, headers=headers)
        if response.status_code < 300:
            logging.info(f"Sent data to REST API from IMEI: {imei}")
        else:
            logging.error(
                f"Failed to send data to REST API. Status code: {response.status_code} from data: {hex_data}")
    except Exception as e:
        logging.error(f"Failed to send data to REST API: {str(e)} from IMEI: {imei}")


def find_all_positions(data, substring):
    """
    Find all positions of a substring in binary data.

    Args:
    data (bytes): The binary data to search in.
    substring (bytes): The substring to find.

    Returns:
    list: A list of positions where the substring is found.
    """
    positions = []
    start = 0
    while True:
        index = data.find(substring, start)
        if index == -1:
            break
        positions.append(index)
        start = index + len(substring)
    return positions


def split_binary_data_by_indexes(data, indexes):
    """
    Split binary data based on a list of index positions and return a list of chunks.

    Args:
    data (bytes): The binary data to split.
    indexes (list): A list of index positions to split the data at.

    Returns:
    list: A list of binary chunks.
    """
    chunks = []
    start = 0
    for index in indexes:
        if index >= len(data):
            continue
        chunks.append(data[start:index])
        start = index
    # Add the last chunk from the last index to the end of the data
    chunks.append(data[start:])
    return chunks


# Function to handle a client connection
def handle_client(client_socket):
    try:
        # Receive the initial 0xF0 message with IMEI
        data = client_socket.recv(1024)

        # Separate the header, identifier, payload, and checksum
        header = data[:4]
        identifier = data[4:5]
        payload = data[5:-1]  # Exclude the last byte, which is the checksum
        checksum = data[-1:]

        if not header.startswith(b'\xBD\xBD\xBD\xBD'):
            client_socket.close()
            logging.error("Connection closed due to unrecognized device identifier!!!")
            return

        if not identifier.startswith(b'\xF0'):
            client_socket.close()
            logging.error("Connection closed due to invalid identifier!!!")
            return

        # Convert the little-endian bytes to an integer
        imei_bytes = payload[:-2]
        imei = int.from_bytes(imei_bytes, byteorder='little')
        client_identifiers[client_socket] = imei

        # Send data to api server
        send_data_to_api(data, imei)

        # Create the message components
        data_buffer = create_lnklin_buffer()
        client_socket.send(data_buffer)
        logging.info(f"Response has been sent to the device: {imei}")

        # Set periodic data on device
        data_buffer = create_periodic_upload_buffer()
        client_socket.send(data_buffer)
        logging.info(f"Periodic setting has been sent to the device: {imei}")

        while True:
            # Receive data from the client
            data = client_socket.recv(1024)

            if not data:
                break

            positions = find_all_positions(data, b'\xbd\xbd\xbd\xbd')

            if positions:
                chunks = split_binary_data_by_indexes(data, positions)

                # Print each chunk in hexadecimal format
                for chunk in chunks:
                    if len(chunk) > 0:
                        # Separate the header, identifier, payload, and checksum
                        header = chunk[:4]
                        identifier = chunk[4:5]
                        payload = chunk[5:-1]  # Exclude the last byte, which is the checksum
                        checksum = chunk[-1:]

                        # Check whether received data is heartbeat
                        if identifier.startswith(b'\xF9'):
                            data_buffer = create_heartbeat_response_buffer()
                            client_socket.send(data_buffer)
                            logging.info(f"Heartbeat response has been sent to the device: {imei}")

                        imei = client_identifiers.get(client_socket, "Unknown")

                        message_type = message_types[binascii.hexlify(identifier).decode()]
                        logging.info(f"[ {message_type} ] message received data from device: "
                                     f"{imei} "
                                     f"{binascii.hexlify(identifier)} "
                                     f"{binascii.hexlify(payload)}"
                                     )

                        # Send the received data to the REST API
                        try:
                            send_data_to_api(chunk, imei)
                        except Exception as e:
                            logging.error(f"Failed to send data to REST API: {str(e)} from IMEI: {imei}")
            else:
                continue

    except Exception as e:
        logging.error(f"Error: {str(e)}")
        # Remove the client from the identifiers dictionary and close the socket upon disconnect or error
        if client_socket in client_identifiers:
            del client_identifiers[client_socket]
        client_socket.close()


# Create a socket object and bind it to the specified host and port
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Enable the SO_REUSEADDR option
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

# Bind the socket to a specific address and port
server.bind((HOST, PORT))

# Listen for incoming connections
server.listen(5)
logging.info(f"Listening on {HOST}:{PORT}")

while True:
    # Accept a client connection
    client_sock, addr = server.accept()
    logging.info(f"Accepted connection from {addr[0]}:{addr[1]}")

    # Start a new thread to handle the client
    client_handler = threading.Thread(target=handle_client, args=(client_sock,))
    client_handler.start()
