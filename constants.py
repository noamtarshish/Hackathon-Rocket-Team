import sys
# Ports
UDP_PORT = 13117
TCP_PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 2115

# Packet Magic Cookie
MAGIC_COOKIE = 0xabcddcba

# Message Types
MESSAGE_TYPE_OFFER = 0x2
MESSAGE_TYPE_REQUEST = 0x3
MESSAGE_TYPE_PAYLOAD = 0x4
