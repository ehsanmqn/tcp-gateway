def decode_health_data(data):
    # Check if the data length is valid
    if len(data) < 12:
        return None  # Data is too short

    data = data[10:]
    try:
        # Extract timestamp as a 4-byte hexadecimal value (little-endian)
        message_type = data[:2]
        timestamp_hex = data[2:10]
        print(">>>> ", message_type, timestamp_hex)
        timestamp = int.from_bytes(timestamp_hex, byteorder='little')
        print(">>>> ", timestamp)
        # Extract the content length as a single byte
        content_length = data[10:12]

        # Initialize a dictionary to store the decoded values
        decoded_data = {}

        # Loop through the remaining data to decode ID and values
        index = 5
        while index < len(data):
            # Extract ID and value length as a single byte
            id_and_length = data[index]
            print(">>> ", id_and_length)
            id_type = (id_and_length & 0xF8) >> 4
            value_length = id_and_length & 0x07

            print(">>>> Type: {} Length: {} bytes".format(id_type, value_length))
            # Extract the value based on the length
            value_hex = data[index + 1:index + 1 + value_length]

            # Convert the value from hexadecimal to integer
            value = int.from_bytes(value_hex, byteorder='big')

            # Add the decoded ID and value to the dictionary
            decoded_data[id_type] = value

            # Move the index to the next ID
            index += 1 + value_length

        return {
            "timestamp": timestamp,
            "content_length": content_length,
            "data": decoded_data
        }

    except Exception as e:
        print(">>>> ", e)
        return None  # Error occurred during decoding


# Example usage:
data_bytes = b'003b7cf5640f000a58091166315a39801a6e0122500198bdbdbdbdf901020000640000580900003b7cf564'
data_bytes = b'BDBDBDBD3200B3C4F2630F000A1E00114B314A39711A4A0122BC0012'
decoded_data = decode_health_data(data_bytes)

if decoded_data:
    print("Decoded Health Data:")
    print(f"Timestamp: {decoded_data['timestamp']}")
    print(f"Content Length: {decoded_data['content_length']}")
    print("Decoded Data:")
    for id_type, value in decoded_data['data'].items():
        print(f"ID {id_type}: {value}")
else:
    print("Failed to decode Health Data.")
