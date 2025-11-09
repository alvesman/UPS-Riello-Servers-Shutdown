# UPS Riello Servers Shutdown

A Python-based P2P client-server system for UPS monitoring and server shutdown coordination.

## Overview

This system allows multiple clients on a local network to discover and connect to a central server. The server can then send commands (like shutdown instructions) to all connected clients.

## Features

- **Automatic Server Discovery**: Clients automatically discover the server on the local network using UDP broadcasts
- **Robust Connection**: Clients retry connection with linear backoff (10s → 60s)
- **Heartbeat Monitoring**: Clients send periodic heartbeats (every 30-60 seconds) to maintain connection
- **Hostname Identification**: Each client identifies itself using its system hostname
- **Message Broadcasting**: Server can send messages to individual clients or broadcast to all

## Requirements

- Python 3.13 (via conda environment)
- Ubuntu Server (or compatible Linux distribution)
- Local network connectivity

## Installation

1. Create and activate the conda environment:
```bash
conda create -n UPS python=3.13 -y
conda activate UPS
```

2. Navigate to the project directory:
```bash
cd /path/to/UPS-Riello-Servers-Shutdown
```

## Usage

### Running the Server

```bash
conda activate UPS
python server/server.py
```

The server will:
- Listen for UDP discovery broadcasts on port 5225
- Accept TCP connections on port 5226
- Track connected clients and monitor their heartbeats

### Running the Client

```bash
conda activate UPS
python client/client.py
```

The client will:
- Broadcast UDP discovery messages every 10 seconds (with linear backoff up to 60s)
- Connect to the server when discovered
- Send heartbeats every 30-60 seconds
- Listen for messages from the server

## Network Ports

- **UDP 5225**: Discovery broadcast port
- **TCP 5226**: Client-server communication port

## Architecture

### Server (`server/server.py`)

The server runs three main threads:
1. **UDP Listener**: Listens for client discovery broadcasts and responds with server information
2. **TCP Server**: Accepts client connections and manages communication
3. **Client Monitor**: Monitors client heartbeats and removes dead connections

### Client (`client/client.py`)

The client runs multiple threads:
1. **Discovery Loop**: Broadcasts discovery messages until server is found
2. **Heartbeat Loop**: Sends periodic heartbeats to maintain connection
3. **Message Receiver**: Listens for messages from the server

## Message Protocol

All messages are JSON-formatted and newline-delimited.

### Client → Server Messages

**Identification** (on connect):
```json
{
    "hostname": "client-hostname",
    "timestamp": 1234567890.123
}
```

**Heartbeat**:
```json
{
    "type": "heartbeat",
    "timestamp": 1234567890.123
}
```

### Server → Client Messages

**Welcome**:
```json
{
    "status": "connected",
    "message": "Welcome to UPS Server"
}
```

**Heartbeat Acknowledgment**:
```json
{
    "type": "heartbeat_ack"
}
```

**Command** (example):
```json
{
    "type": "shutdown",
    "reason": "UPS power failure"
}
```

## Retry Logic

- **Initial retry interval**: 10 seconds
- **Linear backoff**: Increases by 10 seconds per failed attempt
- **Maximum retry interval**: 60 seconds
- After reaching maximum, continues retrying every 60 seconds

## Heartbeat Mechanism

- **Base interval**: 30 seconds
- **Random component**: 1-30 seconds (added to base)
- **Total interval**: 31-60 seconds between heartbeats
- **Server timeout**: 90 seconds (allows for network delays)

## Development Status

### Phase 1 - Completed ✓

- [x] Python 3.13 conda environment
- [x] UDP broadcast-based server discovery
- [x] TCP-based client-server communication
- [x] Client retry with linear backoff
- [x] Heartbeat keepalive mechanism
- [x] Hostname-based client identification
- [x] Server can send messages to clients

## License

See LICENSE file for details.
