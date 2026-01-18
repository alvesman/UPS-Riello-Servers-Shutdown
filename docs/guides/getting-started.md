# Getting Started

This guide provides step-by-step instructions for deploying and configuring the Riello UPS Servers Shutdown system.

## Prerequisites

### Hardware Requirements

- **UPS Device**: Riello UPS with network connectivity and JSON API support
- **Server Machine**: Linux server to run UPS Server and Dashboard
- **Client Machines**: Any machines (Linux/macOS/Windows) that need automated shutdown

### Software Requirements

- **Python**: Version 3.6 or higher
- **Operating System**: Linux (recommended), macOS, or Windows (client only)
- **Network**: All machines on same network segment (for UDP discovery)

### Network Requirements

| Port | Protocol | Direction | Purpose |
|------|----------|-----------|---------|
| 5225 | UDP | Bidirectional | Server discovery |
| 5226 | TCP | Inbound to server | Client connections |
| 8080 | TCP | Inbound to server | Web dashboard |
| 443 | HTTPS | Outbound from server | UPS API access |

---

## Quick Start

### 1. Server Deployment

Deploy on the **last machine that should shut down** (typically your primary infrastructure server).

```bash
# Create installation directory
sudo mkdir -p /opt/UPSserver
cd /path/to/UPS-Riello-Servers-Shutdown

# Copy server files
sudo cp server/UPSserver.py /opt/UPSserver/
sudo cp server/UPSdashboard.py /opt/UPSserver/

# Copy service files
sudo cp server/UPSserver.service /etc/systemd/system/
sudo cp server/UPSdashboard.service /etc/systemd/system/

# Copy logrotate configurations
sudo cp server/UPSserver.logrotate /etc/logrotate.d/UPSserver
sudo cp server/UPSdashboard.logrotate /etc/logrotate.d/UPSdashboard

# Create log files
sudo touch /var/log/UPSserver.log /var/log/UPSserver_error.log
sudo touch /var/log/UPSdashboard.log /var/log/UPSdashboard_error.log
sudo chmod 644 /var/log/UPS*.log

# Enable and start services
sudo systemctl daemon-reload
sudo systemctl enable UPSserver.service UPSdashboard.service
sudo systemctl start UPSserver.service UPSdashboard.service

# Verify services are running
sudo systemctl status UPSserver.service
sudo systemctl status UPSdashboard.service
```

### 2. Client Deployment

Deploy on **each machine** that should be shut down automatically.

```bash
# Create installation directory
sudo mkdir -p /opt/UPSclient
cd /path/to/UPS-Riello-Servers-Shutdown

# Copy client files
sudo cp client/UPSclient.py /opt/UPSclient/

# Copy service file
sudo cp client/UPSclient.service /etc/systemd/system/

# Copy logrotate configuration
sudo cp client/UPSclient.logrotate /etc/logrotate.d/UPSclient

# Create log files
sudo touch /var/log/UPSclient.log /var/log/UPSclient_error.log
sudo chmod 644 /var/log/UPSclient.log /var/log/UPSclient_error.log

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable UPSclient.service
sudo systemctl start UPSclient.service

# Verify service is running
sudo systemctl status UPSclient.service
```

### 3. Configure via Dashboard

1. Open browser: `http://<server-ip>:8080`
2. Navigate to **Configuration** tab
3. Set **UPS_URL** to your Riello UPS JSON endpoint:
   ```
   https://<ups-ip>/json/live_data.json
   ```
4. Set **UPS_minimum_minutes** to desired battery threshold (e.g., `15`)
5. Navigate to **Client Connections** tab
6. Set **Shutdown Delay** for each client based on priority

---

## Detailed Configuration

### UPS URL Configuration

The UPS URL must point to the Riello UPS JSON API endpoint:

```
https://<UPS_IP_ADDRESS>/json/live_data.json
```

**Testing the UPS connection:**
```bash
# Test UPS API access (allow self-signed certificates)
curl -k https://192.168.155.55/json/live_data.json
```

**Expected response:**
```json
{
    "autonomy": 120,
    ...
}
```

The `autonomy` field contains the remaining battery time in minutes.

### Battery Threshold Configuration

Set `UPS_minimum_minutes` to control when shutdown is triggered:

| Value | Meaning |
|-------|---------|
| 5 | Shutdown when ≤5 minutes remain (aggressive) |
| 15 | Shutdown when ≤15 minutes remain (default) |
| 30 | Shutdown when ≤30 minutes remain (conservative) |

Consider:
- Time needed for all machines to shut down
- Any additional margin for safety
- Typical UPS discharge rate under load

### Client Shutdown Priority

Configure `seconds_to_shutdown` for each client to control shutdown order:

| Priority | Delay | Examples |
|----------|-------|----------|
| First (expendable) | 0s | Development servers, non-critical VMs |
| Medium | 30-60s | Application servers, web servers |
| Later | 60-120s | Database servers |
| Last | Max + buffer | Server running UPSserver (automatic) |

**Example Configuration:**
```
web-server-01:     0 seconds (first)
web-server-02:     0 seconds (first)
app-server-01:    30 seconds
cache-server-01:  30 seconds
db-replica-01:    60 seconds
db-master-01:     90 seconds
(UPS Server):    120 seconds (auto: max + 30s buffer)
```

---

## Verification Steps

### 1. Verify UPS Server

```bash
# Check service status
sudo systemctl status UPSserver.service

# Check logs for UPS monitoring
tail -f /var/log/UPSserver.log

# Look for messages like:
# "UPS Server started successfully"
# "Successfully retrieved UPS autonomy: 120 minutes"
```

### 2. Verify Dashboard

```bash
# Check service status
sudo systemctl status UPSdashboard.service

# Access in browser
curl http://localhost:8080/api/ups_status
```

**Expected response:**
```json
{"total_minutes": 120, "status": "ok"}
```

### 3. Verify Client Connection

```bash
# On client machine, check service status
sudo systemctl status UPSclient.service

# Check logs for connection
tail -f /var/log/UPSclient.log

# Look for messages like:
# "Server found at ('192.168.1.100', 5226)"
# "Successfully connected to server"
```

### 4. Verify Client in Dashboard

Open the dashboard and check the **Client Connections** tab. You should see:
- Client hostname
- IP address
- Last connection time (recent)

---

## Troubleshooting

### Client Can't Find Server

**Symptoms:**
```
Server discovery failed
Retrying discovery in 10 seconds...
```

**Solutions:**
1. Verify server is running: `sudo systemctl status UPSserver.service`
2. Check UDP port 5225 is open on server
3. Verify machines are on same network segment
4. Check firewall rules allow UDP broadcast

### UPS API Connection Failed

**Symptoms:**
```
URL error accessing UPS at https://...: Connection refused
Failed to retrieve UPS total minutes
```

**Solutions:**
1. Verify UPS IP address is correct
2. Test with curl: `curl -k https://<ups-ip>/json/live_data.json`
3. Check network connectivity to UPS
4. Verify UPS has network interface enabled

### Dashboard Shows "Database not found"

**Symptoms:**
```
Database file 'ups_clients.db' does not exist
```

**Solutions:**
1. Start UPSserver first - it creates the database
2. Ensure UPSdashboard runs from `/opt/UPSserver/` directory
3. Check file permissions on `/opt/UPSserver/`

### Client Disconnects Frequently

**Symptoms:**
```
Client X timed out
Connection closed by server
```

**Solutions:**
1. Check network stability
2. Review server logs for errors
3. Ensure heartbeat interval (30-60s) < timeout (90s)

---

## Testing Shutdown (Safely)

### Test Without Actual Shutdown

1. Temporarily modify client code to log instead of shutdown:
   ```python
   def _execute_shutdown(self, seconds_to_shutdown: int):
       logger.critical(f"WOULD SHUTDOWN in {seconds_to_shutdown} seconds")
       # Comment out actual shutdown command
       # subprocess.run(['shutdown', '-h', 'now'], check=True)
   ```

2. Lower battery threshold in dashboard to current level + 1
3. Watch logs for shutdown commands being sent
4. Restore original code after testing

### Test with Manual Shutdown Trigger

If you have a test UPS or can simulate low battery:

1. Ensure all machines have test/backup power
2. Trigger low battery condition
3. Monitor shutdown sequence
4. Verify correct order and timing

---

## Production Checklist

- [ ] UPS URL configured and tested
- [ ] Battery threshold set appropriately
- [ ] All clients registered in dashboard
- [ ] Shutdown delays configured by priority
- [ ] Services enabled for auto-start on boot
- [ ] Log rotation configured
- [ ] Firewall rules allow required ports
- [ ] Network security reviewed (see [Authentication](../api/authentication.md))
- [ ] Tested shutdown sequence (safely)
- [ ] Monitoring/alerting configured for service failures

---

[← Back to Data Access](../data/data-access.md) | [Next: Use Cases →](use-cases.md)
