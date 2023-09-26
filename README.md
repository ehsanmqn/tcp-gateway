# TCP Server for Receiving Data from W200P 4G Watch

This Python script implements a TCP server for receiving data from a W200P 4G watch. It listens on a specified port, processes incoming data, and sends it to a REST API. The primary use case is to connect a W200P 4G watch to the Thingsboard IoT platform.

## Prerequisites

Before running the script, ensure you have the following prerequisites installed:

- Python 3.x
- Required Python libraries: `requests`, `binascii`, `struct`, `json`, `logging`

You can install the required libraries using pip:

```bash
pip install -r requirements.txt
```

## Configuration
Modify the following variables in the script to match your specific setup:

- HOST: The network interface to listen on (default is '0.0.0.0' to listen on all available interfaces).
- PORT: The port on which the server listens for incoming connections.
- API_URL: The URL of the REST API where the data should be sent.

## Usage
Run the script using Python:
```bash
python server.py
```
1. The server will start listening for incoming connections on the specified port.

2. When a connection is established with a W200P 4G watch, the server receives data, processes it, and sends it to the configured REST API.

3. The script also handles various message types defined in the message_types dictionary. You can customize the handling of different message types as needed.

4. Logging is provided to keep track of incoming data and server activities. You can adjust the logging configuration by modifying the logging.basicConfig call.

5. The server handles multiple client connections concurrently by using threading.

Contributing
If you want to contribute to this project or have suggestions for improvements, please feel free to create a pull request or open an issue.

License
This project is licensed under the MIT License - see the LICENSE file for details.