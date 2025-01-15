import socket
import struct
import threading
import time
from constants import *

def broadcast_offers():
    """
    Continuously broadcast offer packets via UDP every second.
    """
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) # Reuse address
    udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    offer_packet = struct.pack('!IbHH', MAGIC_COOKIE, MESSAGE_TYPE_OFFER, UDP_PORT, TCP_PORT)

    print(f"Server started, broadcasting offers on IP: {socket.gethostbyname(socket.gethostname())}")

    try:
        while True:
            udp_socket.sendto(offer_packet, ('<broadcast>', UDP_PORT))
            print(f"Broadcast sent on UDP port {UDP_PORT}")
            time.sleep(1)
    except KeyboardInterrupt:
        print("Server shutting down.")
    finally:
        udp_socket.close()

def handle_tcp_connection(client_socket, client_address):
    """
    Handle TCP client connection and simulate file transfer.
    """
    print(f"TCP connection established with {client_address}")
    try:
        # Receive file size from client
        file_size = struct.unpack('!Q', client_socket.recv(8))[0]
        print(f"Received file size request: {file_size} bytes")

        # Simulate file transfer by sending chunks of data
        data = b'a' * 1024
        bytes_sent = 0
        while bytes_sent < file_size:
            client_socket.sendall(data)
            bytes_sent += len(data)

        print(f"TCP file transfer to {client_address} completed. Bytes sent: {bytes_sent}")
    except Exception as e:
        print(f"Error handling TCP connection with {client_address}: {e}")
    finally:
        client_socket.close()

def start_tcp_server():
    """
    Start the TCP server to handle client requests.
    """
    tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp_socket.bind(('', TCP_PORT))
    tcp_socket.listen()
    print(f"TCP server listening on port {TCP_PORT}...")

    while True:
        client_socket, client_address = tcp_socket.accept()
        threading.Thread(target=handle_tcp_connection, args=(client_socket, client_address)).start()

def handle_udp_requests():
    """
    Handle UDP requests and simulate packet transfers.
    """
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.bind(('', UDP_PORT))
    print(f"Server listening for UDP requests on port {UDP_PORT}...")

    try:
        while True:
            data, addr = udp_socket.recvfrom(1024)
            magic_cookie, message_type, file_size = struct.unpack('!IbQ', data)

            if magic_cookie == MAGIC_COOKIE and message_type == MESSAGE_TYPE_REQUEST:
                print(f"Received UDP request for file size {file_size} bytes from {addr}")

                # Simulate sending UDP packets with sequence numbers
                sequence_number = 0
                bytes_sent = 0
                packet_size = 1024
                while bytes_sent < file_size:
                    payload = struct.pack('!I', sequence_number) + b'a' * (packet_size - 4)
                    udp_socket.sendto(payload, addr)
                    sequence_number += 1
                    bytes_sent += len(payload)

                print(f"UDP file transfer to {addr} completed. Bytes sent: {bytes_sent}")
    except Exception as e:
        print(f"Error handling UDP requests: {e}")
    finally:
        udp_socket.close()

def main():
    """
    Main function to start the server with broadcasting, TCP, and UDP handling.
    """
    threads = [
        threading.Thread(target=broadcast_offers, daemon=True),
        threading.Thread(target=start_tcp_server, daemon=True),
        threading.Thread(target=handle_udp_requests, daemon=True)
    ]

    for thread in threads:
        thread.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Server shutting down.")

if __name__ == "__main__":
    main()
