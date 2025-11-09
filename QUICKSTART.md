# Quick Start Guide

## Phase 1 - Basic P2P Communication System

This guide will help you quickly set up and test the UPS monitoring system.

## Prerequisites

- Ubuntu Server (or compatible Linux distribution)
- Conda package manager installed
- Python 3.13 (will be installed via conda)

## Step 1: Environment Setup

```bash
# Navigate to project directory
cd /home/manuel/UPS-Riello-Servers-Shutdown

# The conda environment 'UPS' with Python 3.13 should already be created
# If not, create it:
conda create -n UPS python=3.13 -y

# Activate the environment
conda activate UPS
```

## Step 2: Verify Installation

```bash
# Check Python version (should be 3.13.x)
python --version

# Run the integration test
python test_integration.py
```

If the test passes, your installation is working correctly!

## Step 3: Running in Production

### On the Server Machine:

```bash
conda activate UPS
python server/server.py
```

The server will:
- Listen for client discovery broadcasts on UDP port 5225
- Accept client connections on TCP port 5226
- Display log messages showing client connections and heartbeats

### On Client Machines:

```bash
conda activate UPS
python client/client.py
```

Each client will:
- Broadcast discovery messages to find the server
- Connect automatically when the server is found
- Send heartbeats every 30-60 seconds
- Listen for messages from the server

## Step 4: Monitoring

### Server Logs

The server logs will show:
```
INFO - Starting UPS Server...
INFO - UDP listener started on port 5225
INFO - TCP server started on port 5226
INFO - Client connected: client-hostname from ('192.168.1.100', 54321)
DEBUG - Heartbeat from client-hostname
```

### Client Logs

The client logs will show:
```
INFO - Starting UPS Client (hostname: client-hostname)...
INFO - Attempting to discover server...
INFO - Server found at ('192.168.1.1', 5226)
INFO - Connected to server at ('192.168.1.1', 5226)
DEBUG - Heartbeat sent
```

## Testing on a Single Machine

You can test both server and client on the same machine:

### Terminal 1 (Server):
```bash
conda activate UPS
python server/server.py
```

### Terminal 2 (Client):
```bash
conda activate UPS
python client/client.py
```

You should see the client discover and connect to the server!

## Firewall Configuration

If clients can't discover the server, ensure these ports are open:

```bash
# Allow UDP broadcast on port 5225
sudo ufw allow 5225/udp

# Allow TCP connections on port 5226
sudo ufw allow 5226/tcp

# Or, if using iptables:
sudo iptables -A INPUT -p udp --dport 5225 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 5226 -j ACCEPT
```

## Troubleshooting

### Client can't discover server

1. Check firewall rules (see above)
2. Verify both machines are on the same subnet
3. Check that the server is running and listening
4. Try pinging between machines to verify network connectivity

### Connection drops

1. Check network stability
2. Verify heartbeat timeout settings (default: 90 seconds)
3. Check server logs for error messages

### Server won't start

1. Check if ports 5225 and 5226 are already in use:
   ```bash
   sudo netstat -tulpn | grep 522
   ```
2. If ports are in use, stop the conflicting service or change the ports in the code

## What's Working (Phase 1)

✓ Automatic server discovery via UDP broadcast  
✓ Client retry with linear backoff (10s → 60s)  
✓ TCP-based persistent connections  
✓ Heartbeat keepalive (30-60 second intervals)  
✓ Hostname-based client identification  
✓ Server can send messages to clients  
✓ Automatic reconnection on connection loss  

## Next Steps

Phase 2 and beyond will add:
- Actual UPS monitoring integration
- Shutdown command implementation
- Configuration files
- Systemd service files for auto-start
- Enhanced security (authentication, encryption)
- Web dashboard for monitoring

## Getting Help

Check the main README.md for detailed architecture information and message protocol documentation.
