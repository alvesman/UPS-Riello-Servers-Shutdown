# [Riello UPS](https://www.riello-ups.com/) Servers Shutdown quick README

This is a **distributed UPS (Uninterruptible Power Supply) monitoring and automated shutdown system** designed for Riello UPS units. It protects multiple servers/machines by gracefully shutting them down when the UPS battery reaches critical (configurable) levels.

## Architecture

The system consists of three main components:

### 1. **UPS Server** (`UPSserver.py`)
- Should run on the **last machine to be shut down**, ideally the server other servers depend on, but has no dependencies on the others.
- Monitors a Riello UPS device via HTTPS JSON API (`https://UPS_DASHBOARD_IP/json/live_data.json`)
- Polls the UPS every 60 seconds to check battery autonomy (remaining minutes)
- Manages client connections via UDP discovery (port 5225) and TCP communication (port 5226)
- Stores client inforvmation and configuration in SQLite database (`ups_clients.db`)
- When battery drops below threshold (default: 15 minutes):
  - Sends shutdown commands to all connected clients with configurable delays
  - Shuts itself down last (after max client delay + 30s buffer)
- Tracks client heartbeats (90-second timeout) to detect disconnections

### 2. **UPS Dashboard** (`UPSdashboard.py`)
- Web-based management interface (default port 8080)
- Provides real-time monitoring of:
  - Connected clients with hostnames, IPs, and last connection times
  - UPS configuration (URL, minimum battery threshold)
  - Per-client shutdown delays
  - **Power event history** tracking mains power loss/restoration and shutdown events
  - **Comprehensive system status** with detailed 3-phase UPS metrics including:
    - Input measurements (voltage, current, frequency per phase)
    - Bypass line status
    - Output measurements (voltage, current, power, load percentage per phase)
    - Battery status (capacity, autonomy, voltage, current)
    - Environmental data (temperatures, energy consumption)
    - System status and alarms
- Allows administrators to:
  - Configure UPS URL and minimum battery threshold
  - Set individual shutdown delays for each client (prioritization)
  - View historical power events with timestamps and UPS metrics
- **No authentication** (security note below)

### 3. **UPS Client** (`UPSclient.py`)
- Deployed on **all machines** that need automated shutdown, except where UPSserver is running.
- Auto-discovers server via UDP broadcast
- Maintains TCP connection with heartbeats (30s + random 0-30s jitter)
- Receives two types of messages:
  - `ups_status`: Regular battery updates
  - `shutdown`: Critical command triggering system shutdown
- Implements exponential backoff for reconnection (10-60 seconds)
- Executes OS-appropriate shutdown commands (Linux/macOS)

## Key Features

- **Priority-based shutdown**: Each client can have a custom delay (0-N seconds), allowing critical services to shut down last
- **Power event tracking**: Automatically records mains power loss, restoration, and shutdown events with timestamps and UPS metrics
- **pfSense/OPNsense support**: Optionally shuts down a pfSense or OPNsense firewall via SSH before the server itself shuts down
- **Automatic discovery**: Clients find the server without manual IP configuration
- **Resilient connections**: Heartbeat monitoring, automatic reconnection, and timeout handling
- **Recovery mode**: Prevents immediate re-triggering of shutdown after power restoration
- **Logging**: Separate stdout/stderr logging integrated with systemd
- **Service integration**: Includes systemd service files and logrotate configurations

## Configuration

All configuration is managed via the web dashboard and persisted in SQLite database (`ups_clients.db`).

### UPS Settings
| Setting | Description | Default |
|---------|-------------|---------|
| `UPS_URL` | URL to the Riello UPS JSON API endpoint | `https://192.168.155.55/json/live_data.json` |
| `UPS_minimum_minutes` | Battery threshold (minutes) to trigger shutdown | `15` |

### pfSense/OPNsense SSH Shutdown (Optional)
The server can shut down a pfSense or OPNsense firewall via SSH before shutting itself down. This ensures the firewall is gracefully stopped.

| Setting | Description | Default |
|---------|-------------|---------|
| `pfsense_ssh_username` | SSH username for pfSense | `admin` |
| `pfsense_ssh_ip` | IP address of pfSense | `192.168.155.1` |
| `pfsense_ssh_key_path` | Path to SSH private key | `/root/.ssh/pfsense_id_rsa` |

**Note:** If any of these three settings is empty, the pfSense SSH shutdown will be skipped (with a warning logged).

#### pfSense SSH Setup
To enable pfSense shutdown, you need to:

1. **Generate an SSH key pair** on the UPS server (as root):
   ```bash
   sudo ssh-keygen -t rsa -b 4096 -f /root/.ssh/pfsense_id_rsa -N ""
   ```

2. **Copy the public key to pfSense**:
   - Log into pfSense web interface
   - Go to System → User Manager → Edit admin user
   - Paste the contents of `/root/.ssh/pfsense_id_rsa.pub` into "Authorized SSH Keys"
   - Save

3. **Enable SSH on pfSense**:
   - Go to System → Advanced → Admin Access
   - Enable "Secure Shell"
   - Save

4. **Test the connection** (as root on the UPS server):
   ```bash
   ssh -i /root/.ssh/pfsense_id_rsa admin@192.168.155.1 "echo OK"
   ```

5. **Configure via Dashboard**: Update the settings in the Configuration tab if your values differ from the defaults.

To disable pfSense shutdown, simply clear any of the three SSH settings in the dashboard.

## Workflow
 and power state
2. Clients maintain heartbeat connections to server
3. Power events are automatically tracked:
   - **Mains lost**: When utility power fails and UPS switches to battery
   - **Mains restored**: When utility power returns
   - **Shutdown initiated**: When system triggers shutdown due to low battery
4. When battery ≤ threshold:
   - Server sends shutdown commands to all clients with their configured delays
   - Clients execute shutdown after their respective delays
   - Server shuts down last with longest delay + buffer
5. This ensures graceful, prioritized shutdown of entire infrastructure

## Power Event Monitoring

The system tracks critical power events in the database with detailed metrics:

- **Event Type**: mains_lost, mains_restored, or shutdown_initiated
- **Timestamp**: Precise date and time of each event
- **UPS Metrics**: Input voltages (3-phase), battery current, autonomy
- **Detection Method**: 
  - Input voltage monitoring (< 50V indicates mains loss)
  - Battery current analysis (positive = discharging, negative = charging)

View events via:
- Dashboard **Power Events** tab (last 20 events)
- API endpoint: `GET /api/power_events?limit=N`
- Direct database query: `SELECT * FROM power_events ORDER BY event_time DESC;`
4. This ensures graceful, prioritized shutdown of entire infrastructure
---
################################################################################
# Server Deployment
**Server components should be deployed in the last machine to be shutdown.**

### Install UPSserver as a service

```bash
# Create installation directory
sudo mkdir -p /opt/UPSserver

# Copy server files from the server directory
sudo cp UPSserver.py /opt/UPSserver/
sudo cp UPSserver.service /etc/systemd/system/
sudo cp UPSserver.logrotate /etc/logrotate.d/UPSserver

# Create log files
sudo touch /var/log/UPSserver.log /var/log/UPSserver_error.log
sudo chmod 644 /var/log/UPSserver.log /var/log/UPSserver_error.log
```

**Important Note about User Privileges:**

The UPS server service **must run as root** because it needs to execute system shutdown commands when UPS battery is critical.

### Log rotation check (optional)
```bash
# Test logrotate configuration
sudo logrotate -d /etc/logrotate.d/UPSserver

# Force rotation
sudo logrotate -f /etc/logrotate.d/UPSserver
```

### Enable and start the service
```bash
# Reload systemd to recognize the new service
sudo systemctl daemon-reload

# Enable the service to start on boot
sudo systemctl enable UPSserver.service

# Start the service now
sudo systemctl start UPSserver.service

# Check if it's running
sudo systemctl status UPSserver.service
```

### Monitoring and logs
```bash
# View log files
tail -f /var/log/UPSserver.log -n 50
tail -f /var/log/UPSserver_error.log -n 50
```

### Security Considerations

The dashboard does not provide authentication at this moment.

### Useful commands
```bash
# Stop the service
sudo systemctl stop UPSserver.service

# Restart the service
sudo systemctl restart UPSserver.service

# Check service status
sudo systemctl status UPSserver.service

# Disable service (don't start on boot)
sudo systemctl disable UPSserver.service

# Re-enable service
sudo systemctl enable UPSserver.service
```

### Install UPSdashboard as a service
```bash
sudo cp UPSdashboard.py /opt/UPSserver/
sudo cp UPSdashboard.service /etc/systemd/system/
```
Create log files
```bash
sudo touch /var/log/UPSdashboard.log /var/log/UPSdashboard_error.log
sudo chmod 644 /var/log/UPSdashboard.log /var/log/UPSdashboard_error.log
```

### Setup log rotation
```bash
sudo cp UPSdashboard.logrotate /etc/logrotate.d/UPSdashboard
```

### Enable and start the service
```bash
# Reload systemd to recognize the new service
sudo systemctl daemon-reload

# Enable the service to start on boot
sudo systemctl enable UPSdashboard.service

# Start the service now
sudo systemctl start UPSdashboard.service

# Check if it's running
sudo systemctl status UPSdashboard.service
```

### Useful commands
```bash
# Stop the service
sudo systemctl stop UPSdashboard.service

# Restart the service
sudo systemctl restart UPSdashboard.service

# View logs
tail -f /var/log/UPSdashboard.log -n 50
tail -f /var/log/UPSdashboard_error.log -n 50
```
### Access the dashboard
Open your browser and navigate to:
```bash
http://your-server-ip:8080
```
################################################################################
# Client Deployment
To be installed on all machines that should be shutdown when UPS battery is bellow a threshold configured in the UPSdashboard.

### Install UPSclient as a service
```bash
sudo mkdir -p /opt/UPSclient
sudo cp UPSclient.py /opt/UPSclient/
sudo cp UPSclient.service /etc/systemd/system/
```
### Setup log rotation
```bash
# Copy logrotate configuration
sudo cp UPSclient.logrotate /etc/logrotate.d/UPSclient
```
### Enable and start the service
```bash
# Reload systemd to recognize the new service
sudo systemctl daemon-reload

# Enable the service to start on boot
sudo systemctl enable UPSclient.service

# Start the service
sudo systemctl start UPSclient.service

# Check if it's running
sudo systemctl status UPSclient.service
```

### Useful commands
```bash
# Stop the service
sudo systemctl stop UPSclient.service

# Restart the service
sudo systemctl restart UPSclient.service

# View logs
tail /var/log/UPSclient.log -n 50 -f
tail /var/log/UPSclient_error.log -n 50
```

### More details about the system in the [System details README](docs/README.md)

---
