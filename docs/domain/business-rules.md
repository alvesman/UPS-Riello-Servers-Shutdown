# Business Rules

This document describes the business rules, constraints, and operational logic embedded in the Riello UPS Servers Shutdown system.

## Core Business Rules

### Rule 1: Battery Threshold Shutdown

**Description**: When UPS battery autonomy falls at or below the configured threshold, all connected clients must be instructed to shut down.

**Implementation**: `UPSserver.py` - `_ups_monitor()` method

```python
if total_minutes <= ups_minimum_minutes:
    # Send shutdown commands to all clients
    for hostname in list(self.clients.keys()):
        shutdown_message = {
            'type': 'shutdown',
            'reason': 'low_power',
            'seconds_to_shutdown': seconds_to_shutdown,
            'total_minutes': total_minutes,
            'timestamp': time.time()
        }
        self._send_message_to_client_unsafe(hostname, shutdown_message)
```

**Parameters**:
- Default threshold: **15 minutes**
- Configurable via: Dashboard or database

---

### Rule 1a: Recovery Mode After Shutdown

**Description**: After a shutdown is issued, the server must not immediately re-trigger shutdowns if it restarts (e.g., due to power being restored before the shutdown completes). The server enters "recovery mode" and ignores shutdown triggers until the UPS battery has recovered significantly.

**Implementation**: `UPSserver.py` - `_ups_monitor()` and `_execute_shutdown()` methods

**How It Works**:
1. Just before executing a shutdown command, the server sets `shutdown_issued = 'true'` in the database
2. On startup, the server checks this flag and enters recovery mode if set
3. In recovery mode, shutdown triggers are ignored even if battery is below threshold
4. Recovery mode exits when UPS battery exceeds `threshold + 60 minutes`
5. Once recovery mode exits, the flag is cleared and normal operation resumes

```python
# Check on startup
self.recovery_mode = self._check_recovery_mode()

# Recovery mode logic in _ups_monitor
if self.recovery_mode:
    if total_minutes > recovery_threshold:  # threshold + 60 minutes
        self._exit_recovery_mode()
    else:
        # Ignore shutdown triggers, continue broadcasting status
        continue
```

**Parameters**:
- Recovery buffer: **60 minutes** above threshold
- Example: With 15-minute threshold, recovery requires **75 minutes** of autonomy

**Use Cases**:
1. **Brief Power Blip**: Power fails, shutdown triggers, power returns before shutdown completes. Server restarts in recovery mode and waits for full battery recharge.
2. **Shutdown Failure**: Shutdown command fails for any reason. Server continues in recovery mode preventing immediate re-trigger.
3. **Rapid Power Cycling**: Prevents repeated shutdown attempts during unstable power conditions.

**Log Messages**:
- Startup: `"Server starting in RECOVERY MODE - shutdown triggers will be ignored until UPS battery recovers"`
- Recovery: `"RECOVERY MODE: UPS battery (X min) still below recovery threshold (Y min) - shutdown triggers IGNORED"`
- Exit: `"Exited RECOVERY MODE - normal shutdown monitoring resumed"`

---

### Rule 2: Server Shuts Down Last

**Description**: The UPS server must always be the last machine to shut down, ensuring all clients receive their shutdown commands.

**Implementation**: Server waits for the maximum client delay plus a 30-second buffer.

```python
# Server shuts down after max client delay + 30s buffer
self._execute_shutdown(max_seconds_to_shutdown + 30)
```

**Rationale**: This ensures:
1. All clients receive shutdown commands
2. Clients with the longest delays complete their shutdown
3. Network services remain available during client shutdowns

---

### Rule 3: Priority-Based Client Shutdown

**Description**: Each client can have a unique shutdown delay, allowing administrators to prioritize which machines shut down first.

**Implementation**: `seconds_to_shutdown` field in `client_connections` table

| Delay | Interpretation |
|-------|----------------|
| 0 seconds | Shut down immediately (highest priority) |
| 30 seconds | Shut down after 30s delay |
| 60 seconds | Shut down after 60s delay |
| N seconds | Shut down after N seconds |

**Use Case Example**:
- Development servers: 0s delay (first to shut down)
- Application servers: 30s delay
- Database servers: 60s delay
- Primary infrastructure: Server itself (last)

---

### Rule 4: Heartbeat Timeout Detection

**Description**: Clients that fail to send heartbeats within the timeout period are considered disconnected.

**Implementation**: `UPSserver.py` - `_monitor_clients()` method

```python
HEARTBEAT_TIMEOUT = 90  # seconds

def is_alive(self) -> bool:
    return time.time() - self.last_heartbeat < HEARTBEAT_TIMEOUT
```

**Timing Breakdown**:
- Client heartbeat base interval: 30 seconds
- Random jitter: 0-30 seconds
- Buffer: 30 seconds
- **Total timeout**: 90 seconds

---

### Rule 5: Automatic Server Discovery

**Description**: Clients must be able to find the server without manual IP configuration.

**Implementation**: UDP broadcast discovery on port 5225

```python
DISCOVERY_MESSAGE = b"UPS_DISCOVER"

# Client broadcasts discovery
udp_socket.sendto(DISCOVERY_MESSAGE, ('<broadcast>', 5225))

# Server responds with connection details
response = {
    'tcp_port': 5226,
    'server_ip': self._get_server_ip()
}
```

**Fallback Behavior**:
1. Try localhost first (for same-machine testing)
2. Broadcast to network
3. Use server's UDP response source address if `server_ip` is empty

---

### Rule 6: Reconnection with Backoff

**Description**: Clients must attempt to reconnect to the server with exponential backoff to avoid overwhelming the network.

**Implementation**: `UPSclient.py` - `_discovery_loop()` method

```python
INITIAL_RETRY_INTERVAL = 10  # seconds
MAX_RETRY_INTERVAL = 60  # seconds

# Linear backoff
if retry_interval < MAX_RETRY_INTERVAL:
    retry_interval = min(retry_interval + 10, MAX_RETRY_INTERVAL)
```

**Backoff Sequence**: 10s → 20s → 30s → 40s → 50s → 60s (max)

---

### Rule 7: UPS Polling Interval

**Description**: The UPS battery status must be checked at regular intervals to detect power issues.

**Implementation**: `UPSserver.py` - `_ups_monitor()` method

```python
UPS_CHECK_INTERVAL = 60  # seconds
```

**Rationale**: 60-second intervals balance between:
- Timely detection of power issues
- Minimal load on UPS API
- Sufficient time to send shutdown commands

---

### Rule 8: Database Persistence

**Description**: Client connection history and configuration must persist across server restarts.

**Implementation**: SQLite database with two tables

**Tables Created**:
```sql
CREATE TABLE IF NOT EXISTS client_connections (
    hostname TEXT PRIMARY KEY,
    ip_address TEXT,
    port INTEGER,
    last_connection_time TEXT,
    seconds_to_shutdown INTEGER DEFAULT 0
)

CREATE TABLE IF NOT EXISTS configuration (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
)
```

**Default Configuration Values**:
| Key | Default Value |
|-----|---------------|
| `UPS_URL` | `https://192.168.155.55/json/live_data.json` |
| `UPS_minimum_minutes` | `15` |

---

### Rule 9: Cross-Platform Shutdown Commands

**Description**: Shutdown commands must be appropriate for the operating system.

**Implementation**: Both server and client detect OS and use appropriate commands

```python
system = platform.system()

if system == "Linux" or system == "Darwin":
    subprocess.run(['shutdown', '-h', 'now'], check=True)
elif system == "Windows":
    subprocess.run(['shutdown', '/s', '/t', '0', '/f'], check=True)
```

| OS | Command |
|----|---------|
| Linux | `shutdown -h now` |
| macOS | `shutdown -h now` |
| Windows | `shutdown /s /t 0 /f` |

---

### Rule 10: Root Privilege Requirement

**Description**: Services must run as root to execute system shutdown commands.

**Implementation**: Systemd service files specify `User=root`

```ini
[Service]
User=root
Group=root
```

**Security Note**: This is required for shutdown capability but should be considered in security planning.

---

## Validation Rules

### Configuration Validation

| Field | Validation | Error Handling |
|-------|------------|----------------|
| `UPS_URL` | Must be valid HTTPS URL | Falls back to default |
| `UPS_minimum_minutes` | Must be positive integer | Falls back to 15 |
| `seconds_to_shutdown` | Must be non-negative integer | Rejects invalid values |
| `shutdown_issued` | Must be 'true' or 'false' | Falls back to 'false' |

### Connection Validation

| Check | Response |
|-------|----------|
| No hostname in identification | Close connection |
| Invalid JSON message | Log warning, continue |
| Unknown message type | Log and ignore |

---

## Constraints Summary

| Constraint | Value | Location |
|------------|-------|----------|
| UDP Discovery Port | 5225 | `UPSserver.py`, `UPSclient.py` |
| TCP Server Port | 5226 | `UPSserver.py`, `UPSclient.py` |
| Dashboard Port | 8080 | `UPSdashboard.py` |
| Heartbeat Timeout | 90 seconds | `UPSserver.py` |
| UPS Poll Interval | 60 seconds | `UPSserver.py` |
| Min Retry Interval | 10 seconds | `UPSclient.py` |
| Max Retry Interval | 60 seconds | `UPSclient.py` |
| Heartbeat Base | 30 seconds | `UPSclient.py` |
| Heartbeat Jitter | 0-30 seconds | `UPSclient.py` |
| Server Shutdown Buffer | 30 seconds | `UPSserver.py` |
| Default Battery Threshold | 15 minutes | `UPSserver.py` |
| Recovery Buffer | 60 minutes | `UPSserver.py` |
| Consecutive Low Readings | 5 | `UPSserver.py` |

---

[← Back to Relationships](relationships.md) | [Next: API Endpoints →](../api/endpoints.md)
