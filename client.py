import threading
import time
import struct
import sys
import socket
from constants import *

print_lock = threading.Lock()


class SpeedTestClient:
    """
    Represents a client application for testing network performance using UDP and TCP protocols.

    Attributes:
        server_ip (str): The IP address of the selected server.
        udp_port (int): The UDP port number of the selected server.
        tcp_port (int): The TCP port number of the selected server.
    """

    def __init__(self):
        """
        Initializes the SpeedTestClient instance with default attributes.

        Attributes:
            server_ip (str): The IP address of the selected server (default: None).
            udp_port (int): The UDP port number of the selected server (default: None).
            tcp_port (int): The TCP port number of the selected server (default: None).
        """
        self.server_ip = None
        self.udp_port = None
        self.tcp_port = None

    def print_safe(self, message, color_code="\033[0m"):
        """
            Safely prints a message to the console, ensuring thread-safe output.

            Args:
                message (str): The message to be printed.
        """
        with print_lock:
            print(f"{color_code}{message}\033[0m")

    def listen_offers(self):
        """
        Listens for server offers broadcasted via UDP, extracts and validates server details,
        and updates the client's IP, UDP, and TCP port attributes upon receiving a valid packet.
        """
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

            # Get local IP address
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            self.print_safe(f"Client running on IP: {local_ip}", "\033[94m")

            # Bind to empty string to receive broadcasts
            sock.bind(("", BROADCAST_PORT))
            self.print_safe("Client is active, listening for server offers...", "\033[92m")

            while True:
                try:
                    data, addr = sock.recvfrom(RECEIVE_SIZE)
                    self.print_safe(f"Received data from {addr}, length: {len(data)} bytes", "\033[93m")

                    if len(data) < 8:  # Minimum size for magic cookie and message type
                        continue

                    magic_cookie, message_type, udp_port, tcp_port = struct.unpack("!IBHH", data)
                    self.print_safe(
                        f"Unpacked data - Magic: {hex(magic_cookie)}, Type: {message_type}, UDP: {udp_port}, TCP: {tcp_port}",
                        "\033[96m"
                    )

                    if magic_cookie == MAGIC_COOKIE and message_type == TYPE_OFFER:
                        self.server_ip = addr[0]
                        self.udp_port = udp_port
                        self.tcp_port = tcp_port
                        self.print_safe(
                            f"Offer received from {self.server_ip}. UDP: {self.udp_port}, TCP: {self.tcp_port}",
                            "\033[92m"  # Green
                        )
                        return
                    else:
                        self.print_safe("Received invalid packet format", "\033[91m")
                except Exception as e:
                    self.print_safe(f"Error receiving server offer: {e}", "\033[91m")
                    time.sleep(0.1)  # Add small delay to prevent CPU spinning

    def start_tcp_server(self, connection_id):
        """
        Handles a TCP connection to request and receive a file.

        Args:
            connection_id (int): Identifier for the TCP connection.
        """
        try:
            # Create a TCP socket
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                # Connect to the server using the provided IP and TCP port
                sock.connect((self.server_ip, self.tcp_port))
                # Construct and send a request packet to the server
                request_packet = struct.pack("!IBQ1s", MAGIC_COOKIE, TYPE_REQUEST, self.file_size, b"\n")
                sock.sendall(request_packet)

                bytes_received = 0
                total_segments = 1  # Placeholder; updated when the first segment is received
                current_segment = 0
                start_time = time.time()  # Record the start time of the transfer

                # Loop to receive file segments
                while current_segment < total_segments:
                    # Receive a data segment from the server
                    data = sock.recv(self.file_size + HEADER_SIZE)
                    # Unpack the segment's header
                    (magic, msg_type, total_segments, received_segment) = struct.unpack('!IBQQ', data[:HEADER_SIZE])

                    # Validate the segment's integrity
                    if magic != MAGIC_COOKIE or msg_type != TYPE_PAYLOAD:
                        raise ValueError("Invalid TCP payload received")

                    # Ensure the segments are received in sequential order
                    if received_segment != current_segment + 1:
                        raise ValueError("Unexpected segment received")

                    current_segment = received_segment
                    bytes_received += len(data[HEADER_SIZE:])

                elapsed_time = time.time() - start_time
                speed = (bytes_received * 8) / elapsed_time if elapsed_time > 0 else 0
                # Log the results of the TCP transfer
                self.print_safe(f"TCP #{connection_id}: Completed in {elapsed_time:.2f}s, speed: {speed:.2f} bps", "\033[92m")
        except (ConnectionResetError, socket.error) as e:
            # Log errors that occur during the TCP connection
            self.print_safe(f"Error during TCP test #{connection_id}: {e}", "\033[91m")  # Red

    def handle_udp_requests(self, connection_id):
        """
        Handles a UDP connection to send a file request and receive file segments.

        Args:
            connection_id (int): Identifier for the UDP connection.
        """
        try:
            # Create a UDP socket
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                # Construct and send the request packet
                request_packet = struct.pack("!IBQ", MAGIC_COOKIE, TYPE_REQUEST, self.file_size)
                sock.sendto(request_packet, (self.server_ip, self.udp_port))
                sock.settimeout(1.0)  # Set a timeout of 1 second for receiving data

                packets_received = 0
                packets_total = 0
                total_segments = 1  # Placeholder, updated when the first packet is received
                current_segment = 0
                start_time = time.time()

                try:
                    # Loop to receive file segments until all segments are received
                    while current_segment < total_segments:
                        # Receive data from the server
                        data, _ = sock.recvfrom(4096)
                        packets_total += 1

                        # Unpack the header from the received packet
                        magic_cookie, msg_type, total_segments, received_segment = struct.unpack("!IBQQ",
                                                                                                 data[:HEADER_SIZE])

                        # Validate the packet's integrity
                        if magic_cookie != MAGIC_COOKIE or msg_type != TYPE_PAYLOAD:
                            raise ValueError("Invalid UDP payload received")

                        if received_segment == current_segment + 1:
                            current_segment = received_segment
                            packets_received += 1

                except socket.timeout:
                    # Exit the loop if no data is received within the timeout period
                    pass

                elapsed_time = time.time() - start_time
                speed = (packets_received * 8 * RECEIVE_SIZE) / elapsed_time if elapsed_time > 0 else 0
                packet_loss = 100 - (packets_received / packets_total * 100 if packets_total > 0 else 0)
                # Log the results of the UDP test
                self.print_safe(f"UDP #{connection_id}: Completed in {elapsed_time:.2f}s, speed: {speed:.2f} bps, loss: {packet_loss:.2f}%", "\033[92m")
        except (ConnectionResetError, socket.error) as e:
            # Log any connection or socket errors
            self.print_safe(f"Error during UDP test #{connection_id}: {e}", "\033[91m")

    def manage_threads(self):
        """
        Manages the creation and execution of threads for TCP and UDP tests.
        """
        # List to store all threads
        threads = []
        self.print_safe("Starting tests...", "\033[94m")

        # Create and start threads for TCP connections
        for i in range(1, self.tcp_connections + 1):
            # Each thread runs the TCP file transfer function
            thread = threading.Thread(target=self.start_tcp_server, args=(i,))
            threads.append(thread)
            thread.start()

        # Create and start threads for UDP connections
        for i in range(1, self.udp_connections + 1):
            # Each thread runs the UDP file transfer function
            thread = threading.Thread(target=self.handle_udp_requests, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to finish
        for thread in threads:
            thread.join()  # Block execution until the thread completes

        # Log that all tests have been completed
        self.print_safe("All tests completed, listening for more offers.", "\033[92m")

    def run(self):
        """
        Runs the client application, prompting for configuration and managing the workflow.
        """
        self.print_safe("Welcome to SpeedTestClient of Team Rocket and remember - Prepare for trouble, and make it double-speed!", "\033[96m")  # Cyan

        # Prompt the user to input the file size and connection details
        self.file_size = int(input("Enter the file size in bytes: ")) # File size for transfer
        self.tcp_connections = int(input("Enter the number of TCP connections: "))  # Number of TCP connections
        self.udp_connections = int(input("Enter the number of UDP connections: "))  # Number of UDP connections

        # Main loop to handle server discovery and performance tests
        while True:
            self.listen_offers()
            self.manage_threads()


if __name__ == "__main__":
    client = SpeedTestClient()
    try:
        client.run()
    except KeyboardInterrupt:
        print("Exiting the client...")
        sys.exit(0)
