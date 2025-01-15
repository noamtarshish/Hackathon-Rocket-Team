# 🚀 Team Rocket Network Speed Test

*"Prepare for trouble, and make it double-speed!"*

## 📋 Project Overview

This project implements a network speed testing application as part of a Intro to Data Communications Hackathon Course. The main objective is to create a client-server system that compares TCP and UDP performance under shared network conditions. 
### Core Objectives
- Compare TCP and UDP download performance
- Analyze how protocols share network resources
- Ensure cross-compatibility with other teams' implementations
- Demonstrate understanding of network programming concepts

## 🌟 Features

- **Protocol Comparison**: 
  - Simultaneous TCP and UDP testing
  - Performance metrics for both protocols
  - Analysis of network resource sharing

- **Universal Compatibility**:
  - Standardized communication protocol
  - Consistent packet formats
  - Common broadcast discovery mechanism
  - Shared port configurations

- **Performance Metrics**: 
  - TCP throughput measurements
  - UDP packet loss statistics
  - Connection establishment times
  - Real-time performance reporting

## 🛠️ Technical Specifications

### Network Protocol
- UDP broadcast on port 13117 for server discovery
- Dynamic TCP/UDP ports for testing
- Standardized message formats:
  - Magic cookie: 0xabcddcba
  - Message types: OFFER(0x2), REQUEST(0x3), PAYLOAD(0x4)

### Requirements
- Python 3.7+
- Network with broadcast capability
- Open firewall for UDP port 13117
- Configurable TCP/UDP ports for testing

## 📦 Installation

1. Clone the repository:
```bash
git clone https://github.com/your-username/rocket-network-speedtest.git
cd rocket-network-speedtest
```

2. No additional dependencies required - uses Python standard library only!

## 🚀 Usage

### Server
```bash
python server.py
```
The server will:
- Start broadcasting its presence
- Accept connections from any compatible client
- Handle multiple simultaneous tests
- Provide test data for both TCP and UDP

### Client
```bash
python client.py
```
The client will:
1. Prompt for test parameters:
   - File size (bytes)
   - Number of TCP connections
   - Number of UDP connections
2. Discover available servers
3. Execute parallel protocol tests
4. Display comparative performance results

## 📊 Example Output

```
Client is active, listening for server offers...
Offer received from 192.168.1.100. UDP: 25123, TCP: 35456
Starting tests...
TCP #1: Completed in 1.23s, speed: 8.45 Mbps
UDP #1: Completed in 1.45s, speed: 7.89 Mbps, loss: 0.5%
All tests completed, listening for more offers.
```

## 🏗️ Project Structure

```
rocket-network-speedtest/
├── README.md
├── constants.py    # Shared protocol constants
├── server.py      # Server implementation
└── client.py      # Client implementation
```

## 💡 Implementation Notes

- **Code Documentation**: Extensive commenting for readability and understanding
- **Error Handling**: Robust handling of network issues
- **Thread Safety**: Proper synchronization for concurrent connections
- **Standardization**: Adherence to course protocol specifications

## 👥 Team Rocket Members

- [Noam Tarshish]
- [Nofar Selouk]

---
*"Blasting off at the speed of light! ⭐"*
