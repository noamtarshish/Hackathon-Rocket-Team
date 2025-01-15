import threading
import time
import struct
import random
import socket
from constants import *

print_lock = threading.Lock()
udp_lock = threading.Lock()

class SpeedTestServer:
    def __init__(self):
        self.udp_port = random.randint(20000, 30000)
        self.tcp_port = random.randint(30001, 40000)
        self.running = True

    def safe_print(self, message, color_code="\033[0m"):
        with print_lock:
            print(f"{color_code}{message}\033[0m")

    def get_IP(self):
        # Get all network interfaces
        interfaces = socket.getaddrinfo(socket.gethostname(), None)
        # Filter for IPv4 addresses
        ipv4_addresses = [addr[4][0] for addr in interfaces if addr[0] == socket.AF_INET]
        # Return the first non-localhost IPv4 address
        for ip in ipv4_addresses:
            if not ip.startswith('127.'):
                return ip
        return '127.0.0.1'  # fallback to localhost if no other IP found

    def broadcast_offers(self):
        """Send periodic UDP broadcast messages to announce server availability."""
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            server_ip = self.get_IP()
            self.safe_print(
                f"Server is running on IP: {server_ip}, UDP Port: {self.udp_port}, TCP Port: {self.tcp_port}")

            offer_packet = struct.pack("!IBHH", MAGIC_COOKIE, TYPE_OFFER, self.udp_port, self.tcp_port)

            # Get broadcast address
            network = '.'.join(server_ip.split('.')[:-1] + ['255'])
            self.safe_print(f"Broadcasting to address: {network}", "\033[92m")  # Green

            while self.running:
                try:
                    sock.sendto(offer_packet, (network, BROADCAST_PORT))
                    sock.sendto(offer_packet, ('<broadcast>', BROADCAST_PORT))
                    self.safe_print(f"Broadcast sent on UDP port {BROADCAST_PORT}", "\033[93m")
                except Exception as e:
                    self.safe_print(f"Broadcast error: {e}")
                time.sleep(1)  # Broadcast every second

    def handle_tcp(self, conn, addr):
        """Process incoming TCP requests."""
        try:
            data = conn.recv(1024)
            (magic, msg_type, file_size, endline_char) = struct.unpack('!IBQ1s', data)
            if magic != MAGIC_COOKIE or msg_type != TYPE_REQUEST or endline_char != b"\n":
                raise ValueError("Invalid TCP request format")
            self.safe_print(f"Received TCP request from {addr}, file size: {file_size} bytes", "\033[92m")  # Green

            payload = struct.pack("!IBQQ", MAGIC_COOKIE, TYPE_PAYLOAD, 1, 1) + b"x" * file_size
            conn.send(payload)

            self.safe_print(f"TCP transfer to {addr} completed successfully", "\033[92m")  # Green
        except Exception as e:
            self.safe_print(f"Error during TCP request from {addr}: {e}", "\033[91m")  # Red
        finally:
            conn.close()

    def handle_udp(self, sock, addr, file_size):
        """Process incoming UDP requests."""
        try:
            self.safe_print(f"Received UDP request from {addr}, file size: {file_size} bytes", "\033[92m")  # Green

            total_segments = (file_size + 1023) // 1024

            for segment in range(total_segments):
                payload_size = min(file_size, 1024)
                packet = struct.pack("!IBQQ", MAGIC_COOKIE, TYPE_PAYLOAD, total_segments, segment + 1) + b"x" * payload_size
                file_size -= 1024
                with udp_lock:
                    sock.sendto(packet, addr)

            self.safe_print(f"UDP transfer to {addr} completed successfully", "\033[92m")  # Green
        except Exception as e:
            self.safe_print(f"Error during UDP request from {addr}: {e}", "\033[91m")  # Red

    def listen_requests(self):
        """Listen for TCP and UDP client requests."""
        self.safe_print("Server is waiting for client connections...", "\033[94m")  # Blue
        tcp_thread = threading.Thread(target=self.listen_tcp)
        udp_thread = threading.Thread(target=self.listen_udp)

        try:
            tcp_thread.start()
            udp_thread.start()
        except Exception as e:
            self.safe_print(f"Error while listening for connections: {e}", "\033[91m")  # Red

    def listen_tcp(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as tcp_sock:
            tcp_sock.bind(("", self.tcp_port))
            while self.running:
                tcp_sock.listen()
                conn, addr = tcp_sock.accept()
                threading.Thread(target=self.handle_tcp, args=(conn, addr)).start()

    def listen_udp(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_sock:
            udp_sock.bind(("", self.udp_port))
            while self.running:
                data, addr = udp_sock.recvfrom(4096)
                try:
                    magic, msg_type, file_size = struct.unpack("!IBQ", data[:13])
                    if magic == MAGIC_COOKIE and msg_type == TYPE_REQUEST:
                        threading.Thread(target=self.handle_udp, args=(udp_sock, addr, file_size)).start()
                except Exception as e:
                    self.safe_print(f"Invalid UDP request from {addr}: {e}", "\033[91m")  # Red

    def start_server(self):
        """Start the server."""
        broadcast_thread = threading.Thread(target=self.broadcast_offers)
        broadcast_thread.start()

        self.listen_requests()

if __name__ == "__main__":
    server = SpeedTestServer()
    try:
        server.start_server()
    except KeyboardInterrupt:
        server.running = False
        print("\033[91mShutting down the server...\033[0m")  # Red
