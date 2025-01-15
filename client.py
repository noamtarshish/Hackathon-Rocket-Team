import threading
import time
import struct
import sys
import socket
from constants import *

print_lock = threading.Lock()

class SpeedTestClient:
    def __init__(self):
        self.server_ip = None
        self.udp_port = None
        self.tcp_port = None

    def print_safe(self, message):
        with print_lock:
            print(message)

    def listen_offers(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

            # Get local IP address
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            self.print_safe(f"Client running on IP: {local_ip}")

            # Bind to empty string to receive broadcasts
            sock.bind(("", BROADCAST_PORT))
            self.print_safe("Client is active, listening for server offers...")

            while True:
                try:
                    data, addr = sock.recvfrom(RECEIVE_SIZE)
                    self.print_safe(f"Received data from {addr}, length: {len(data)} bytes")

                    if len(data) < 8:  # Minimum size for magic cookie and message type
                        continue

                    magic_cookie, message_type, udp_port, tcp_port = struct.unpack("!IBHH", data)
                    self.print_safe(
                        f"Unpacked data - Magic: {hex(magic_cookie)}, Type: {message_type}, UDP: {udp_port}, TCP: {tcp_port}")

                    if magic_cookie == MAGIC_COOKIE and message_type == TYPE_OFFER:
                        self.server_ip = addr[0]
                        self.udp_port = udp_port
                        self.tcp_port = tcp_port
                        self.print_safe(
                            f"Offer received from {self.server_ip}. UDP: {self.udp_port}, TCP: {self.tcp_port}")
                        return
                    else:
                        self.print_safe("Received invalid packet format")
                except Exception as e:
                    self.print_safe(f"Error receiving server offer: {e}")
                    time.sleep(0.1)  # Add small delay to prevent CPU spinning

    def start_tcp_server(self, connection_id):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect((self.server_ip, self.tcp_port))
                request_packet = struct.pack("!IBQ1s", MAGIC_COOKIE, TYPE_REQUEST, self.file_size, b"\n")
                sock.sendall(request_packet)

                bytes_received = 0
                total_segments = 1
                current_segment = 0
                start_time = time.time()

                while current_segment < total_segments:
                    data = sock.recv(self.file_size + HEADER_SIZE)
                    (magic, msg_type, total_segments, received_segment) = struct.unpack('!IBQQ', data[:HEADER_SIZE])

                    if magic != MAGIC_COOKIE or msg_type != TYPE_PAYLOAD:
                        raise ValueError("Invalid TCP payload received")

                    if received_segment != current_segment + 1:
                        raise ValueError("Unexpected segment received")

                    current_segment = received_segment
                    bytes_received += len(data[HEADER_SIZE:])

                elapsed_time = time.time() - start_time
                speed = (bytes_received * 8) / elapsed_time if elapsed_time > 0 else 0
                self.print_safe(f"TCP #{connection_id}: Completed in {elapsed_time:.2f}s, speed: {speed:.2f} bps")
        except (ConnectionResetError, socket.error) as e:
            self.print_safe(f"Error during TCP test #{connection_id}: {e}")

    def handle_udp_requests(self, connection_id):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                request_packet = struct.pack("!IBQ", MAGIC_COOKIE, TYPE_REQUEST, self.file_size)
                sock.sendto(request_packet, (self.server_ip, self.udp_port))
                sock.settimeout(1.0)

                packets_received = 0
                packets_total = 0
                total_segments = 1
                current_segment = 0
                start_time = time.time()

                try:
                    while current_segment < total_segments:
                        data, _ = sock.recvfrom(4096)
                        packets_total += 1
                        magic_cookie, msg_type, total_segments, received_segment = struct.unpack("!IBQQ", data[:HEADER_SIZE])

                        if magic_cookie != MAGIC_COOKIE or msg_type != TYPE_PAYLOAD:
                            raise ValueError("Invalid UDP payload received")

                        if total_segments == 1:
                            total_segments = total_segments

                        if received_segment == current_segment + 1:
                            current_segment = received_segment
                            packets_received += 1

                except socket.timeout:
                    pass

                elapsed_time = time.time() - start_time
                speed = (packets_received * 8 * RECEIVE_SIZE) / elapsed_time if elapsed_time > 0 else 0
                packet_loss = 100 - (packets_received / packets_total * 100 if packets_total > 0 else 0)
                self.print_safe(f"UDP #{connection_id}: Completed in {elapsed_time:.2f}s, speed: {speed:.2f} bps, loss: {packet_loss:.2f}%")
        except (ConnectionResetError, socket.error) as e:
            self.print_safe(f"Error during UDP test #{connection_id}: {e}")

    def manage_threads(self):
        threads = []
        self.print_safe("Starting tests...")

        for i in range(1, self.tcp_connections + 1):
            thread = threading.Thread(target=self.start_tcp_server, args=(i,))
            threads.append(thread)
            thread.start()

        for i in range(1, self.udp_connections + 1):
            thread = threading.Thread(target=self.handle_udp_requests, args=(i,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        self.print_safe("All tests completed, listening for more offers.")

    def run(self):
        self.file_size = int(input("Enter the file size in bytes: "))
        self.tcp_connections = int(input("Enter the number of TCP connections: "))
        self.udp_connections = int(input("Enter the number of UDP connections: "))
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
