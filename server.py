import socket
import time
import struct
import threading
import multiprocessing
import random
from scapy.all import get_if_addr
from constants import *

def broadcast_offers():
    """
    Broadcast 'offer' messages to clients over UDP every second.
    """
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    # Prepare the offer message
    offer_packet = struct.pack('!IbHH', MAGIC_COOKIE, MESSAGE_TYPE_OFFER, UDP_PORT, TCP_PORT)

    print("Server started, broadcasting offers...")

    try:
        while True:
            udp_socket.sendto(offer_packet, ('<broadcast>', UDP_PORT))
            print(f"Broadcast sent on UDP port {UDP_PORT}")
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nBroadcasting stopped.")
    finally:
        udp_socket.close()


def handle_client(client_socket, client_address):
    """
    Handle a single client connection and transfer a file.
    """
    print(f"Connected to client at {client_address}")
    try:
        # Receive file size request
        file_size = struct.unpack('!Q', client_socket.recv(8))[0]
        print(f"Client requested file size: {file_size} bytes")

        # Simulate file transfer
        data = b'a' * min(file_size, 1024)  # Send chunks of 1024 bytes
        bytes_sent = 0
        while bytes_sent < file_size:
            client_socket.sendall(data)
            bytes_sent += len(data)
        print(f"File transfer to {client_address} completed ({bytes_sent} bytes sent)")
    except Exception as e:
        print(f"Error with client {client_address}: {e}")
    finally:
        client_socket.close()
        print(f"Connection with client {client_address} closed.")



def start_tcp_server():
    """
    Start the TCP server to handle client connections.
    """
    tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp_socket.bind(('', TCP_PORT))
    tcp_socket.listen()
    print(f"TCP server listening on port {TCP_PORT}...")

    while True:
        # Accept incoming client connections
        print(f"Waiting for client connections on TCP port {TCP_PORT}...")
        client_socket, client_address = tcp_socket.accept()
        print(f"Accepted connection from {client_address}")
        # Spawn a new thread to handle the client
        threading.Thread(target=handle_client, args=(client_socket, client_address)).start()


def handle_udp_requests():
    """
    Handle incoming UDP requests from clients.
    """
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.bind(('', UDP_PORT))
    print(f"Server listening for UDP requests on port {UDP_PORT}...")

    while True:
        data, addr = udp_socket.recvfrom(1024)
        magic_cookie, message_type, file_size = struct.unpack('!IbQ', data)

        # Validate the request
        if magic_cookie == MAGIC_COOKIE and message_type == MESSAGE_TYPE_REQUEST:
            print(f"Received file size request: {file_size} bytes from {addr}")
            # Send acknowledgment
            response = struct.pack('!Ib', MAGIC_COOKIE, MESSAGE_TYPE_REQUEST)
            udp_socket.sendto(response, addr)
            print(f"Sent acknowledgment to {addr}")


if __name__ == "__main__":
    # Start broadcasting offers in a separate thread
    broadcast_thread = threading.Thread(target=broadcast_offers)
    broadcast_thread.start()

    # Start the TCP server
    start_tcp_server()

