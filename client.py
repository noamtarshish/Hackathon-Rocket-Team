import socket
import struct
from constants import *

def listen_for_offers():
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.bind(('', UDP_PORT))

    print("Listening for server offers...")
    while True:
        data, addr = udp_socket.recvfrom(1024)
        magic_cookie, message_type, udp_port, tcp_port = struct.unpack('!IbHH', data)
        if magic_cookie == MAGIC_COOKIE and message_type == MESSAGE_TYPE_OFFER:
            print(f"Received offer from {addr[0]}: UDP {udp_port}, TCP {tcp_port}")
            print(f"Calling connect_to_server({addr[0]}, {tcp_port})")
            connect_to_server(addr[0], tcp_port, 1024) # Connect to the server


def connect_to_server(server_ip, server_port, file_size):
    """
    Connect to the server via TCP, send a file transfer request, and receive the file.
    """
    try:
        tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcp_socket.connect((server_ip, server_port))
        print(f"Connected to server at {server_ip}:{server_port}")

        # Send file size request
        tcp_socket.sendall(struct.pack('!Q', file_size))
        print(f"Requested file size: {file_size} bytes")

        # Receive file data
        total_received = 0
        while total_received < file_size:
            data = tcp_socket.recv(1024)
            if not data:
                break
            total_received += len(data)
        print(f"File transfer complete. Total bytes received: {total_received}")

        tcp_socket.close()
    except Exception as e:
        print(f"Error connecting to server: {e}")


def send_udp_request(server_ip, file_size):
    """
    Send a file size request to the server via UDP.
    """
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        request_packet = struct.pack('!IbQ', MAGIC_COOKIE, MESSAGE_TYPE_REQUEST, file_size)
        udp_socket.sendto(request_packet, (server_ip, UDP_PORT))
        print(f"Sent file size request ({file_size} bytes) to {server_ip}:{UDP_PORT}")

        # Wait for acknowledgment
        data, addr = udp_socket.recvfrom(1024)
        magic_cookie, message_type = struct.unpack('!Ib', data)
        if magic_cookie == MAGIC_COOKIE and message_type == MESSAGE_TYPE_REQUEST:
            print(f"Acknowledgment received from {addr}")
    finally:
        udp_socket.close()



if __name__ == "__main__":
    listen_for_offers()
