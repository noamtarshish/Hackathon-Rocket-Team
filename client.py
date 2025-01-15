import socket
import struct
import threading
import time
from constants import *

def discover_servers():
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    udp_socket.bind(("", UDP_PORT))

    print("Listening for server offers...")
    servers = []
    udp_socket.settimeout(5)  # Stop discovery after 5 seconds

    try:
        while True:
            try:
                data, server_address = udp_socket.recvfrom(1024)
                if len(data) == struct.calcsize('!IbHH'):  # Validate packet size
                    magic_cookie, message_type, udp_port, tcp_port = struct.unpack('!IbHH', data)
                    if magic_cookie == MAGIC_COOKIE and message_type == MESSAGE_TYPE_OFFER:
                        print(f"Received offer from {server_address[0]}: UDP {udp_port}, TCP {tcp_port}")
                        if (server_address[0], tcp_port) not in servers:
                            servers.append((server_address[0], tcp_port))
            except socket.timeout:
                print("Discovery phase complete.")  # Stop after timeout
                break
            except Exception as e:
                print(f"Error during server discovery: {e}")
    finally:
        udp_socket.close()

    return servers


def handle_tcp_connection(server_ip, server_port, file_size, connection_number):
    """
    Handle a single TCP file transfer.
    """
    try:
        tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcp_socket.connect((server_ip, server_port))
        start_time = time.time()

        tcp_socket.sendall(struct.pack('!Q', file_size))
        total_received = 0
        while total_received < file_size:
            data = tcp_socket.recv(1024)
            total_received += len(data)

        end_time = time.time()
        transfer_time = end_time - start_time
        speed = total_received / transfer_time if transfer_time > 0 else 0
        print(f"TCP transfer #{connection_number} finished: {transfer_time:.2f}s, {speed:.2f} bytes/second")
    except Exception as e:
        print(f"Error in TCP transfer #{connection_number}: {e}")
    finally:
        tcp_socket.close()

def handle_udp_connection(server_ip, file_size, connection_number):
    """
    Handle a single UDP file transfer.
    """
    try:
        udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp_socket.settimeout(1)
        request_packet = struct.pack('!IbQ', MAGIC_COOKIE, MESSAGE_TYPE_REQUEST, file_size)
        udp_socket.sendto(request_packet, (server_ip, UDP_PORT))

        total_received = 0
        sequence_number = 0
        start_time = time.time()

        while True:
            try:
                data, _ = udp_socket.recvfrom(1024)
                seq = struct.unpack('!I', data[:4])[0]
                if seq == sequence_number:
                    total_received += len(data[4:])
                    sequence_number += 1
            except socket.timeout:
                break

        end_time = time.time()
        transfer_time = end_time - start_time
        packet_loss = 100 - (sequence_number / (file_size / 1020)) * 100
        speed = total_received / transfer_time if transfer_time > 0 else 0
        print(f"UDP transfer #{connection_number} finished: {transfer_time:.2f}s, {speed:.2f} bytes/second, {100 - packet_loss:.2f}% packets received")
    except Exception as e:
        print(f"Error in UDP transfer #{connection_number}: {e}")
    finally:
        udp_socket.close()

def initiate_transfer(server):
    server_ip, tcp_port = server
    file_size = int(input("Enter file size to request (bytes): "))
    protocol = input("Enter protocol for transfer (TCP/UDP): ").strip().upper()

    # TCP Transfer
    if protocol == "TCP":
        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.connect((server_ip, tcp_port))

            # Send file size to server
            client_socket.sendall(f"{file_size}\n".encode())

            # Measure transfer time
            start_time = time.time()
            total_received = 0
            while total_received < file_size:
                data = client_socket.recv(1024)
                total_received += len(data)
            end_time = time.time()

            transfer_time = end_time - start_time
            speed = total_received / transfer_time
            print(f"TCP transfer finished, total time: {transfer_time:.2f} seconds, speed: {speed:.2f} bytes/second")
        except Exception as e:
            print(f"Error during TCP transfer: {e}")
        finally:
            client_socket.close()

    # UDP Transfer
    elif protocol == "UDP":
        try:
            udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            udp_socket.sendto(
                struct.pack('!IbQ', MAGIC_COOKIE, MESSAGE_TYPE_REQUEST, file_size),
                (server_ip, UDP_PORT)
            )

            # Start receiving data
            start_time = time.time()
            total_received = 0
            expected_segments = None
            received_segments = set()

            while True:
                udp_socket.settimeout(1)
                try:
                    data, _ = udp_socket.recvfrom(2048)
                    header_size = struct.calcsize('!IbQQ')
                    if len(data) >= header_size:
                        magic_cookie, message_type, total_segments, current_segment = struct.unpack('!IbQQ', data[:header_size])
                        if magic_cookie == MAGIC_COOKIE and message_type == MESSAGE_TYPE_PAYLOAD:
                            payload = data[header_size:]
                            total_received += len(payload)
                            received_segments.add(current_segment)
                            if expected_segments is None:
                                expected_segments = total_segments
                except socket.timeout:
                    break  # Exit when no data received for 1 second

            end_time = time.time()
            transfer_time = end_time - start_time
            speed = total_received / transfer_time
            packet_loss = 0
            if expected_segments is not None:
                packet_loss = 100 * (1 - len(received_segments) / expected_segments)

            print(f"UDP transfer finished, total time: {transfer_time:.2f} seconds, speed: {speed:.2f} bytes/second, packet loss: {packet_loss:.2f}%")
        except Exception as e:
            print(f"Error during UDP transfer: {e}")
        finally:
            udp_socket.close()
    else:
        print("Invalid protocol. Please choose TCP or UDP.")

def main():
    while True:
        print("Discovering servers...")
        servers = discover_servers()
        if not servers:
            print("No servers discovered. Would you like to retry? (yes/no)")
            retry = input().strip().lower()
            if retry != "yes":
                return
            continue

        print("Available servers:")
        for i, (ip, port) in enumerate(servers):
            print(f"{i + 1}. {ip}:{port}")

        try:
            choice = int(input("Select a server by number: ")) - 1
            if choice < 0 or choice >= len(servers):
                print("Invalid selection. Please try again.")
                continue
        except ValueError:
            print("Invalid input. Please enter a number.")
            continue

        server_ip, server_port = servers[choice]
        print(f"Selected server: {server_ip}:{server_port}")

        initiate_transfer((server_ip, server_port))

        print("All transfers complete, listening to offer requests.")
        break


if __name__ == "__main__":
    main()
