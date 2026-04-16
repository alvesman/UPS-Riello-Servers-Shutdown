# Recipe: Build UPS-Riello-Servers-Shutdown from Scratch

> **How to use this file**: Feed each prompt below to GitHub Copilot (or any AI coding assistant) **one at a time, in order**, starting from an empty repository. Each prompt builds on the files created by previous ones. Wait for each prompt to complete before moving to the next.
>
> This recipe focuses exclusively on the working system — server, client, dashboard, and deployment artifacts. Documentation is excluded.

---

## Prompt 1 — Project Scaffolding and README

> Create a new project called "UPS-Riello-Servers-Shutdown". This is a distributed UPS (Uninterruptible Power Supply) monitoring and automated shutdown system for Riello UPS units. It protects multiple servers by gracefully shutting them down when the UPS battery reaches critical levels.
>
> Create this directory structure (empty directories for now, we will add files in subsequent steps):
>
> server/
> client/
>
> Create a comprehensive README.md at the project root. The README must include ALL of the following sections with exact details:
>
> ## Architecture
> Three components:
>
> ### 1. UPS Server (UPSserver.py)
> - Runs on the LAST machine to be shut down
> - Monitors a Riello UPS device via HTTPS JSON API (https://<UPS_DEVICE_IP>/json/live_data.json) where UPS_DEVICE_IP is a constant defined in the code (default: 192.168.155.55, configurable via the dashboard). The UPS uses a self-signed SSL certificate, so all HTTPS requests to this endpoint must disable certificate verification (equivalent to curl's `-k` / `--insecure` flag). In Python, this means creating an `ssl.SSLContext` with certificate verification disabled and passing it to `urllib.request.urlopen`.
> - Polls the UPS every 60 seconds to check battery autonomy (remaining minutes)
> - Manages client connections via UDP discovery (port 5225) and TCP communication (port 5226)
> - Stores client information and configuration in SQLite database (ups_clients.db)
> - When battery drops below threshold (default: 15 minutes): sends shutdown commands to all connected clients with configurable delays, then shuts itself down last (after max client delay + 30s buffer)
> - Tracks client heartbeats (90-second timeout) to detect disconnections
>
> ### 2. UPS Dashboard (UPSdashboard.py)
> - Web-based management interface (default port 8080)
> - Provides real-time monitoring of: connected clients with hostnames/IPs/last connection times, UPS configuration (URL, threshold), per-client shutdown delays, power event history tracking mains power loss/restoration/shutdown events, comprehensive 3-phase UPS metrics (input voltage/current/frequency per phase, bypass status, output measurements, battery status including capacity/autonomy/voltage/current, environmental data, system alarms)
> - Allows administrators to: configure UPS URL and minimum battery threshold, set individual shutdown delays for each client
> - Protected by access code authentication
>
> ### 3. UPS Client (UPSclient.py)
> - Deployed on ALL machines needing automated shutdown (except the one running UPSserver)
> - Auto-discovers server via UDP broadcast
> - Maintains TCP connection with heartbeats (30s base + random 1-30s jitter)
> - Receives ups_status and shutdown messages
> - Implements linear backoff for reconnection (10-60 seconds, +10s per failure)
> - Executes OS-appropriate shutdown commands (Linux/macOS)
>
> ## Key Features section:
> - Priority-based shutdown (custom delay 0-N seconds per client)
> - Power event tracking (mains_lost, mains_restored, shutdown_initiated with timestamps and UPS metrics)
> - pfSense/OPNsense support: optional SSH shutdown of firewall before server shutdown
> - Automatic discovery: clients find server without manual IP config
> - Resilient connections: heartbeat monitoring, auto-reconnection, timeout handling
> - Recovery mode: prevents immediate re-triggering after power restoration
> - Logging: separate stdout/stderr integrated with systemd
> - Service integration: systemd service files and logrotate configurations
>
> ## Configuration section with tables:
>
> ### UPS Settings table:
> | Setting | Description | Default |
> |---------|-------------|---------|
> | UPS_URL | URL to Riello UPS JSON API endpoint | https://192.168.155.55/json/live_data.json |
> | UPS_minimum_minutes | Battery threshold (minutes) to trigger shutdown | 15 |
>
> ### pfSense/OPNsense SSH Shutdown table:
> | Setting | Description | Default |
> |---------|-------------|---------|
> | pfsense_ssh_username | SSH username for pfSense | admin |
> | pfsense_ssh_ip | IP address of pfSense | 192.168.155.1 |
> | pfsense_ssh_key_path | Path to SSH private key | /root/.ssh/pfsense_id_rsa |
>
> Note: if any of the three pfSense settings is empty, SSH shutdown is skipped.
>
> Include a pfSense SSH Setup subsection with numbered steps:
> 1. Generate SSH key pair (ssh-keygen -t rsa -b 4096 -f /root/.ssh/pfsense_id_rsa -N "")
> 2. Copy public key to pfSense web interface (System → User Manager → admin → Authorized SSH Keys)
> 3. Enable SSH on pfSense (System → Advanced → Admin Access)
> 4. Test connection (ssh -i /root/.ssh/pfsense_id_rsa admin@192.168.155.1 "echo OK")
> 5. Configure via Dashboard
>
> ## Workflow section explaining:
> 1. Server polls UPS every 60 seconds and tracks power state (mains present vs. battery)
> 2. Clients maintain heartbeat connections (30s base + random jitter)
> 3. Power events auto-tracked: mains_lost (input voltage drops below 50V), mains_restored (voltage returns), shutdown_initiated (battery critical)
> 4. When battery ≤ threshold for 5 consecutive readings: server sends shutdown commands with configured delays, clients execute after delays, server shuts down last
> 5. Recovery mode prevents re-triggering until battery exceeds threshold + 60 min buffer
> 6. Graceful prioritized shutdown of entire infrastructure
>
> ## Power Event Monitoring section:
> - Event types: mains_lost, mains_restored, shutdown_initiated
> - Stored with timestamp, 3-phase input voltages, battery current, autonomy
> - Detection: input voltage < 50V = mains lost, positive battery current = discharging
> - Viewable via Dashboard Power Events tab, API GET /api/power_events?limit=N, or direct SQLite query
>
> ## Server Deployment section with full bash commands:
> - mkdir -p /opt/UPSserver
> - Copy UPSserver.py to /opt/UPSserver/
> - Copy UPSserver.service to /etc/systemd/system/
> - Copy UPSserver.logrotate to /etc/logrotate.d/UPSserver
> - Create log files: /var/log/UPSserver.log and /var/log/UPSserver_error.log (chmod 644 for initial creation; logrotate maintains permissions thereafter)
> - Note: service must run as root for shutdown commands
> - Log rotation test commands
> - systemctl daemon-reload, enable, start, status commands
> - Monitoring commands (tail -f on log files)
> - Security note: dashboard is protected by access code authentication (see Prompts 5-6)
> - Useful commands: stop, restart, status, disable, enable
>
> ### Dashboard deployment:
> - Copy UPSdashboard.py to /opt/UPSserver/
> - Copy UPSdashboard.service to /etc/systemd/system/
> - Create log files: /var/log/UPSdashboard.log and /var/log/UPSdashboard_error.log
> - Copy UPSdashboard.logrotate to /etc/logrotate.d/UPSdashboard
> - systemctl daemon-reload, enable, start
> - Access at http://your-server-ip:8080
>
> ## Client Deployment section:
> - mkdir -p /opt/UPSclient
> - Copy UPSclient.py to /opt/UPSclient/
> - Copy UPSclient.service to /etc/systemd/system/
> - Copy UPSclient.logrotate to /etc/logrotate.d/UPSclient
> - systemctl daemon-reload, enable, start
> - View logs commands
>
> Note: The deployment sections above list the high-level steps (directory creation, file copy destinations, systemctl commands). The exact contents of the .service and .logrotate files are defined in Prompts 7-8. The README should present the deployment steps as shown above but tell the reader to consult the actual .service and .logrotate files for their contents, rather than inlining those file contents into the README.
>
> Known limitations to mention in the README:
> - Client rows in client_connections are never deleted. Decommissioned clients remain as historical records. To remove them, use sqlite3 directly on ups_clients.db.
> - The dashboard access code is stored in plaintext in the SQLite database. For environments where this is a concern, restrict network access to the dashboard port (8080) and change the default code immediately after first login.

---

## Riello UPS JSON API Reference (for Prompts 2, 3, 5, and 6)

> **Before implementing any prompt that references UPS JSON fields** (Prompts 2, 3, 5, and 6), fetch and read the following URLs to understand the Riello UPS `live_data.json` API. Build a complete field-name-to-meaning mapping table from these sources.

### URLs to fetch:

1. **NetMan Troubleshooting Guide (rev05)** — lists all JSON field names:
   https://www.rielloupsamerica.com/uploads/file/954/3954/NETMAN_TROUBLESHOOT_rev05.pdf

2. **NetMan Troubleshooting Guide (rev06)** — updated version:
   https://www.riello-ups.com/uploads/file/428/4428/NETMAN_TROUBLESHOOT_rev06.pdf

3. **NetMan 208 User Manual** — JSON section (pages 34-37), MODBUS register tables (pages 93-95), BACnet object descriptions (pages 96-97):
   https://www.manualslib.com/manual/3093060/Riello-Ups-Netman208.html

4. **NetMan 208 Official Manual PDF**:
   https://www.riello-ups.com/uploads/file/614/3614/0MNACCSA8ENUB__MAN_ACC_NETMAN_208_EN_.pdf

5. **Riello SNMP MIB** — maps OIDs to human-readable measurement descriptions:
   https://github.com/librenms/librenms/blob/master/mibs/riello/RIELLOUPS-MIB

6. **Siemens Riello UPS device properties** — field configuration reference:
   https://mybuilding.siemens.com/D037871569805/Help/EngineeringHelp/en-US/14803629451.html

### How to build the mapping:

- The Troubleshooting Guides list the JSON field names (e.g., `vin1`, `vin2`, `vin3`, `fin`, `vbyp1`, `autonomy`, `batcap`, `abatp`, etc.)
- The **MODBUS register tables** in the NetMan 208 manual provide measurement descriptions and units (e.g., "Input voltage (Ph-N) V1", "Input frequency Hz/10", "Battery capacity %")
- The **BACnet object descriptions** provide additional human-readable measurement names
- The **SNMP MIB** provides detailed descriptions for each measurement OID
- **Infer semantics and units by cross-referencing** the JSON field names with the MODBUS/BACnet/SNMP descriptions. Field name patterns help: `v` = voltage, `a`/`i` = current (amps), `f` = frequency, `w` = power (watts), `p`/`load` = load %, `t` = temperature, numbers `1/2/3` = phase, `bat`/`b` = battery, `in` = input, `out` = output, `byp` = bypass
- **Key scaling rules** (from MODBUS tables): frequency values are in **decihertz** (÷10 for Hz), battery bus voltages (`vbatp`/`vbatn`) are in **decivolts** (÷10 for V), power values may be in deciWatts or Watts depending on the field
- **Sign conventions**: negative `abatp`/`abatn` = battery charging, positive = discharging

> If any URL is inaccessible, use the remaining sources and the field name patterns to infer the semantics. The mapping must cover at minimum: `vin1-3`, `ain1-3`, `fin`, `vbyp1-3`, `fbyp`, `vout1-3`, `aout1-3`, `fout`, `w1-3`, `load1-3`, `vbatp`, `vbatn`, `abatp`, `abatn`, `autonomy`, `batcap`, `tsys`, `tbatext`, `KWh`, `alarms`, `system_status`.

---

## Prompt 2 — UPS Server: Core Infrastructure

> Create server/UPSserver.py — the core UPS server component. Use ONLY Python standard library modules (no external dependencies).
>
> IMPORTANT: Before implementing, fetch and read the URLs listed in the "Riello UPS JSON API Reference" section above to understand the UPS JSON field names, their semantics, and units. Use this knowledge when implementing fields like 'autonomy', 'abatp', 'vin1/vin2/vin3', etc.
>
> The file must include:
>
> ## Imports (exact list):
> socket, threading, json, time, logging, sqlite3, platform, subprocess, sys, urllib.request, urllib.error, ssl, typing.Dict, typing.Tuple, datetime.datetime
>
> ## Logging Setup:
> Configure a custom dual-handler logging system:
> - Logger name: __name__, level: INFO
> - Format: '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
> - stdout_handler: StreamHandler(sys.stdout), level INFO, with filter that only passes records where levelno < ERROR
> - stderr_handler: StreamHandler(sys.stderr), level ERROR
> This ensures INFO/WARNING go to stdout (captured by systemd StandardOutput) and ERROR/CRITICAL go to stderr (captured by systemd StandardError).
>
> ## Constants:
> UDP_BROADCAST_PORT = 5225
> TCP_SERVER_PORT = 5226
> DISCOVERY_MESSAGE = b"UPS_DISCOVER"
> HEARTBEAT_TIMEOUT = 90  # 90 seconds = 30s base + up to 30s random jitter + 30s safety buffer
> UPS_URL = 'https://192.168.155.55/json/live_data.json'  # Default, configurable via DB
> UPS_CHECK_INTERVAL = 60  # seconds
>
> ## Class: ClientConnection
> Represents a connected client with:
> - __init__(self, hostname: str, address: Tuple[str, int], conn: socket.socket): stores hostname, address, conn, last_heartbeat=time.time(), connected=True
> - update_heartbeat(): sets last_heartbeat to current time
> - is_alive() -> bool: returns True if time since last_heartbeat < HEARTBEAT_TIMEOUT
>
> ## Class: ReadUPSMinutes
> Static class to read UPS data:
> - @staticmethod get_total_minutes(url): Fetches JSON from url using urllib.request with SSL context that disables certificate verification (like curl -k), timeout=10s. Extracts 'autonomy' field from JSON response. Validates it's a number, converts to int, returns it. Handles HTTPError, URLError, JSONDecodeError, and generic exceptions with full traceback logging. Returns None on any failure.
>
> ## Class: UPSServer
> Main server class with __init__(self, db_path='ups_clients.db'):
> - Instance variables: clients (Dict[str, ClientConnection]), running=False, udp_socket=None, tcp_socket=None, lock=threading.Lock(), db_path
> - self.consecutive_low_readings = 0
> - self.REQUIRED_LOW_READINGS = 5
> - self.RECOVERY_BUFFER_MINUTES = 60
> - self.mains_power_present = True  # Assume mains present at startup
> - self.INPUT_VOLTAGE_THRESHOLD = 50
> - Calls self._init_database()
> - Checks recovery mode from DB on startup: self.recovery_mode = self._check_recovery_mode()
>
> ### _init_database():
> Creates 3 tables if they don't exist:
>
> Table client_connections:
>   - hostname TEXT PRIMARY KEY
>   - ip_address TEXT
>   - port INTEGER
>   - last_connection_time TEXT
>   - seconds_to_shutdown INTEGER DEFAULT 0
>
> Table configuration:
>   - key TEXT PRIMARY KEY
>   - value TEXT NOT NULL
>
> Table power_events:
>   - id INTEGER PRIMARY KEY AUTOINCREMENT
>   - event_type TEXT NOT NULL
>   - event_time TEXT NOT NULL
>   - vin1 INTEGER
>   - vin2 INTEGER
>   - vin3 INTEGER
>   - battery_current INTEGER
>   - autonomy INTEGER
>   - details TEXT
>
> Insert default config values (INSERT OR IGNORE):
>   - UPS_URL: 'https://192.168.155.55/json/live_data.json'
>   - UPS_minimum_minutes: '15'
>   - pfsense_ssh_username: 'admin'
>   - pfsense_ssh_ip: '192.168.155.1'
>   - pfsense_ssh_key_path: '/root/.ssh/pfsense_id_rsa'
>   - shutdown_issued: 'false'
>
> ### Database helper methods:
> - _record_client_connection(hostname, address): Upsert into client_connections with current ISO timestamp
> - _update_heartbeat_time(hostname, address): Update last_connection_time and ip/port for hostname
> - get_client_history(hostname=None): Return list of dicts from client_connections (filter by hostname if provided, else all, ordered by last_connection_time DESC)
> - get_config_value(key, default=None) -> str: Query configuration table, return value or default
> - set_config_value(key, value): INSERT OR REPLACE into configuration table
>
> ### Recovery mode methods:
> - _check_recovery_mode() -> bool: Returns True if DB config 'shutdown_issued' == 'true'
> - _set_shutdown_issued(issued: bool): Sets 'shutdown_issued' to 'true'/'false' in DB
> - _exit_recovery_mode(): Sets recovery_mode=False, clears shutdown_issued flag, resets consecutive_low_readings
>
> Note: recovery_mode is effectively set to True when _execute_shutdown calls _set_shutdown_issued(True). Since _execute_shutdown terminates the machine, recovery_mode=True is read from the DB on next startup via _check_recovery_mode() in __init__. There is no in-process assignment of self.recovery_mode = True because the process does not survive shutdown.
>
> ### Power event methods:
> - _record_power_event(event_type, vin1=None, vin2=None, vin3=None, battery_current=None, autonomy=None, details=None): Insert into power_events with current ISO timestamp
> - _check_mains_power_state(ups_data: dict) -> bool: Checks vin1/vin2/vin3 against INPUT_VOLTAGE_THRESHOLD (50V) and battery current (abatp field). Returns True if any voltage > threshold OR abatp <= 0 (battery idle or charging). Note: abatp > 0 means discharging, abatp <= 0 means charging or idle — this cleanly distinguishes "mains present" from "running on battery".
> - _get_full_ups_data(url) -> dict: Same SSL-disabled fetch as ReadUPSMinutes but returns entire JSON dict
>
> ### Server lifecycle:
> - start(): Sets running=True, starts 4 daemon threads (UDP listener, TCP server, client monitor, UPS monitor), keeps main thread alive with sleep loop, handles KeyboardInterrupt
> - stop(): Sets running=False, closes all client connections, clears clients dict, closes sockets
>
> ### _udp_listener():
> - Binds UDP socket to ('', 5225) with SO_REUSEADDR
> - On receiving DISCOVERY_MESSAGE: responds with JSON {"tcp_port": 5226, "server_ip": self._get_server_ip()}
> - Sends response both to original address AND as broadcast on port 5225
> - 1-second timeout for non-blocking operation
>
> ### _tcp_server():
> - Binds TCP socket to ('', 5226) with SO_REUSEADDR, listen(5)
> - Accepts connections, spawns _handle_client thread per connection
> - 1-second timeout for non-blocking operation
>
> ### _handle_client(conn, addr):
> - Receives identification JSON with 'hostname' field (5s timeout)
> - Records connection in DB
> - Creates ClientConnection, replaces old connection if hostname already exists
> - Sends welcome: {"status": "connected", "message": "Welcome to UPS Server"}
> - Loops reading newline-delimited JSON messages
> - On heartbeat message: updates heartbeat, updates DB, sends {"type": "heartbeat_ack"}
> - On malformed JSON: log warning with raw data and client address, skip the message (do not disconnect)
> - On unrecognized message type (not heartbeat): log info with the message type and client hostname, skip (no response sent)
> - Cleanup: removes client from dict, closes connection
>
> ### _monitor_clients():
> - Every 10 seconds, checks all clients with is_alive()
> - Removes timed-out clients, closes their connections
>
> ### _get_server_ip():
> - Creates UDP socket, connects to 8.8.8.8:80 (doesn't send data), gets local IP from getsockname()
> - Fallback: socket.gethostname() → gethostbyname()
> - Last resort: returns "" (client uses UDP source address)
>
> ### Messaging methods:
> - _send_message_to_client_unsafe(hostname, message): Sends JSON + newline to client (assumes lock held)
> - send_message_to_client(hostname, message): Acquires lock, calls unsafe version
> - broadcast_message(message): Acquires lock, sends to all clients
> - list_clients(): Returns list of dicts with hostname, address, last_heartbeat
>
> Note: The shutdown message format sent to clients is: {"type": "shutdown", "reason": "low_power", "seconds_to_shutdown": <int>, "total_minutes": <int>, "timestamp": <float>}. See Prompt 3 step 9.c for full details.
>
> ### main():
> Creates UPSServer() and calls start().
>
> if __name__ == "__main__": main()

---

## Prompt 3 — UPS Server: Monitoring, Shutdown, and Power Events

> Add the _ups_monitor method and _execute_shutdown method to the UPSServer class in server/UPSserver.py. Use ONLY Python standard library modules (no external dependencies). These implement the core UPS monitoring loop and shutdown logic.
>
> IMPORTANT: Refer to the "Riello UPS JSON API Reference" section above for the UPS JSON field names, semantics, and units. Fetch those URLs if you haven't already. Fields like 'abatp', 'vin1/vin2/vin3', 'autonomy' come from the Riello live_data.json API.
>
> ### _ups_monitor():
> This method runs in the UPS monitor daemon thread. It loops while self.running:
>
> 1. Get UPS URL from DB config (fallback to default UPS_URL constant)
> 2. Fetch full UPS data using _get_full_ups_data(url). If None, log warning, sleep UPS_CHECK_INTERVAL, continue.
> 3. Check mains power state using _check_mains_power_state(ups_data)
> 4. Detect state changes: compute new_state = _check_mains_power_state(ups_data); if new_state != self.mains_power_present, record the event; then update self.mains_power_present = new_state:
>    - If mains restored: log WARNING, record 'mains_restored' power event with vin1/vin2/vin3 from ups_data, battery_current from ups_data['abatp'], autonomy from ups_data['autonomy']
>    - If mains lost: log CRITICAL, record 'mains_lost' power event with same fields
>    - Update self.mains_power_present
> 5. Get total_minutes from ups_data['autonomy']
> 6. Get UPS_minimum_minutes from DB config (default '15', parse to int)
> 7. Calculate recovery_threshold = ups_minimum_minutes + self.RECOVERY_BUFFER_MINUTES (60)
>
> 8. If in recovery_mode:
>    - If total_minutes > recovery_threshold: call _exit_recovery_mode()
>    - Else: log warning (recovery mode active, triggers ignored), broadcast ups_status message WITH recovery_mode=True and recovery_threshold fields, sleep, continue (skip shutdown logic)
>
> 9. Normal operation — if total_minutes <= ups_minimum_minutes:
>    - Increment consecutive_low_readings
>    - Log warning with current count vs REQUIRED_LOW_READINGS (5)
>    - If consecutive_low_readings >= REQUIRED_LOW_READINGS:
>      a. Get client_history from DB (has seconds_to_shutdown per client)
>      b. Track max_seconds_to_shutdown = 0
>      c. Under lock, for each connected client:
>         - Look up their seconds_to_shutdown from client_history (default 0)
>         - Track maximum
>         - Send shutdown message: {"type": "shutdown", "reason": "low_power", "seconds_to_shutdown": <client's delay>, "total_minutes": total_minutes, "timestamp": time.time()}
>         - Log CRITICAL for each client
>      d. Record 'shutdown_initiated' power event with details string including consecutive readings count and battery level
>      e. Call self._execute_shutdown(max_seconds_to_shutdown + 30) — the +30 is a buffer so server shuts down AFTER all clients
>
> 10. If total_minutes > ups_minimum_minutes:
>     - Reset consecutive_low_readings to 0 if it was > 0 (log info about recovery). Note: this covers the normal-operation reset. The recovery-mode reset is handled by _exit_recovery_mode() in step 8. Between these two branches, consecutive_low_readings is always reset whenever conditions improve.
>     - Broadcast normal ups_status: {"type": "ups_status", "total_minutes": total_minutes, "timestamp": time.time()}
>
> 11. Sleep UPS_CHECK_INTERVAL (60 seconds)
>
> ### _execute_shutdown(seconds_to_shutdown):
> This method handles shutting down the server machine itself:
>
> 1. Log CRITICAL about shutdown initiation and wait time
> 2. time.sleep(seconds_to_shutdown) — wait for clients to shut down first
> 3. Get pfSense SSH config from DB: pfsense_ssh_username, pfsense_ssh_ip, pfsense_ssh_key_path
> 4. If ANY of the three pfSense values is empty: log warning and skip pfSense shutdown
> 5. Otherwise: execute subprocess.run(['ssh', '-i', key_path, 'user@ip', '/sbin/shutdown', '-p', 'now'], check=True). Log CRITICAL before, catch CalledProcessError.
> 6. Log CRITICAL "Executing system shutdown NOW!"
> 7. Detect OS with platform.system()
> 8. For Linux or Darwin: set shutdown_issued flag to True in DB FIRST, then execute subprocess.run(['/sbin/shutdown', '-h', 'now'], check=True)
> 9. For other OS: log error about unsupported OS
> 10. Catch CalledProcessError and generic Exception

---

## Prompt 4 — UPS Client

> Create client/UPSclient.py — the lightweight client daemon. Use ONLY Python standard library. The file must include:
>
> ## Imports:
> socket, threading, json, time, random, logging, platform, subprocess, sys
>
> ## Logging Setup:
> Identical dual-handler pattern as the server:
> - Logger name: __name__, level: INFO
> - Format: '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
> - stdout_handler for INFO/WARNING (with filter: levelno < ERROR)
> - stderr_handler for ERROR/CRITICAL
>
> ## Constants:
> UDP_BROADCAST_PORT = 5225
> DISCOVERY_MESSAGE = b"UPS_DISCOVER"
> INITIAL_RETRY_INTERVAL = 10
> MAX_RETRY_INTERVAL = 60
> HEARTBEAT_BASE_INTERVAL = 30
> HEARTBEAT_RANDOM_MAX = 30
>
> ## Class: UPSClient
>
> ### __init__():
> - self.hostname = platform.node()
> - self.server_address = None
> - self.tcp_socket = None
> - self.connected = False
> - self.running = False
> - self.lock = threading.Lock()
>
> ### start():
> - Log info with hostname
> - Set running = True
> - Start daemon thread running _discovery_loop
> - Keep main thread alive with sleep(1) loop
> - Handle KeyboardInterrupt → call stop()
>
> ### stop():
> - Set running = False
> - Call _disconnect()
>
> ### _discovery_loop():
> Main reconnection loop with linear backoff:
> - retry_interval starts at INITIAL_RETRY_INTERVAL (10)
> - While running and not connected:
>   1. Call _discover_server()
>   2. If found, call _connect_to_server()
>   3. If connected: reset retry_interval, start heartbeat thread, wait while connected
>   4. On failure: increase retry_interval by 10 (cap at MAX_RETRY_INTERVAL=60), sleep
> - While running and connected: sleep(1)
>
> ### _discover_server() -> bool:
> 1. Create UDP socket with SO_BROADCAST, timeout 5s
> 2. FIRST try localhost (127.0.0.1): send DISCOVERY_MESSAGE, wait for JSON response
> 3. Parse response: extract server_ip (if empty or '0.0.0.0', use source address from UDP packet), extract tcp_port
> 4. If localhost fails, try broadcast: send to ('<broadcast>', 5225), parse same way
> 5. Set self.server_address = (server_ip, tcp_port)
> 6. Return True on success, False on any failure
>
> ### _connect_to_server() -> bool:
> 1. Create TCP socket, timeout 10s
> 2. Connect to self.server_address
> 3. Send identification JSON: {"hostname": self.hostname, "timestamp": time.time()}
> 4. Wait for welcome message (timeout 5s), parse JSON
> 5. Set connected = True under lock
> 6. Start daemon thread for _receive_messages
> 7. Return True on success, False on failure (call _disconnect on error)
>
> ### _disconnect():
> 1. Set connected = False under lock
> 2. Close tcp_socket, set to None
> 3. Set server_address = None
>
> ### _heartbeat_loop():
> While running and connected:
> 1. Calculate interval = HEARTBEAT_BASE_INTERVAL + random.randint(1, HEARTBEAT_RANDOM_MAX) — note: 1 to 30, not 0 to 30 (avoids zero jitter which would cause unnecessarily tight heartbeat intervals)
> 2. Sleep for interval
> 3. If not connected: break
> 4. Send heartbeat JSON under lock: {"type": "heartbeat", "timestamp": time.time()} followed by newline (\n)
> 5. On send failure: log error, call _disconnect, break
>
> ### _receive_messages():
> Buffer-based newline-delimited JSON reader:
> 1. Set socket timeout to 1.0s
> 2. Loop while running and connected
> 3. Recv 1024 bytes, append to buffer
> 4. If empty data: server disconnected, call _disconnect, break
> 5. While '\n' in buffer: split on first '\n', parse JSON, call _handle_message
> 6. Handle socket.timeout (continue), other exceptions (disconnect)
>
> ### _handle_message(message: dict):
> Switch on message type field:
> - 'heartbeat_ack': log debug
> - 'ups_status': log INFO with total_minutes and timestamp. If recovery_mode present, note it.
> - 'shutdown': log WARNING with reason, seconds_to_shutdown. Start daemon thread calling _execute_shutdown(seconds_to_shutdown)
> - 'command': log info with command value
> - other: log info about unknown message type
>
> ### _execute_shutdown(seconds_to_shutdown: int):
> 1. Log CRITICAL about waiting N seconds
> 2. time.sleep(seconds_to_shutdown)
> 3. Log CRITICAL "Executing system shutdown NOW!"
> 4. Detect OS: Linux or Darwin → subprocess.run(['/sbin/shutdown', '-h', 'now'], check=True)
> 5. Other OS → log error
> 6. Handle CalledProcessError and generic Exception
>
> ### main():
> Create UPSClient() and call start().
>
> if __name__ == "__main__": main()

---

## Prompt 5 — Dashboard: Backend (HTTP Server + API)

> Create server/UPSdashboard.py — the web dashboard HTTP server. Use ONLY Python standard library. This prompt covers the backend; the next prompt will add the full HTML frontend.
>
> IMPORTANT: Refer to the "Riello UPS JSON API Reference" section above for UPS JSON field names and semantics when implementing get_ups_status() and get_ups_full_status().
>
> ## Imports:
> sqlite3, json, os, secrets, http.server.HTTPServer, http.server.BaseHTTPRequestHandler, urllib.parse.urlparse, urllib.parse.parse_qs, datetime.datetime, http.cookies.SimpleCookie
>
> ## Configuration:
> DB_PATH = 'ups_clients.db'
> DEFAULT_PORT = 8080
> DEFAULT_ACCESS_CODE = 'ups-riello-r2ut'
>
> IMPORTANT: Change this default access code before production deployment via the Configuration tab in the dashboard.
>
> Security note: The access code is stored in plaintext in the SQLite configuration table. This is acceptable for a LAN-only admin tool, but be aware that anyone with read access to ups_clients.db can retrieve it. For higher-security environments, restrict filesystem and network access to the dashboard.
>
> ## Session Management:
> - active_sessions = set() — in-memory session storage
> - create_session() -> str: Generate token with secrets.token_urlsafe(32), add to set, return
> - validate_session(token) -> bool: Return token in active_sessions
> - destroy_session(token): Discard from set
>
> ## Authentication Functions:
> - initialize_access_code(): INSERT OR IGNORE 'access_code' with DEFAULT_ACCESS_CODE into configuration table
> - verify_access_code(code) -> bool: Query DB for access_code config, compare with provided code
>
> ## Database Helper Functions:
> - get_db_connection(): Return sqlite3.connect(DB_PATH)
> - load_client_connections(): SELECT hostname, ip_address, port, last_connection_time, seconds_to_shutdown FROM client_connections ORDER BY last_connection_time DESC. Format timestamps to '%Y-%m-%d %H:%M'. Return list of dicts.
> - load_configuration(): SELECT key, value FROM configuration ORDER BY key. Return list of dicts.
> - load_power_events(limit=100): SELECT all fields FROM power_events ORDER BY event_time DESC LIMIT ?. Format timestamps to '%Y-%m-%d %H:%M:%S' into event_time_formatted field. Return list of dicts.
> - update_config_value(key, value): INSERT OR REPLACE into configuration. Return True/False.
> - update_client_shutdown_time(hostname, seconds): UPDATE client_connections SET seconds_to_shutdown. Return True/False.
>
> ## UPS Status Functions:
> - get_ups_status(): Read UPS_URL from DB, fetch JSON with SSL verification disabled (timeout 5s), extract 'autonomy', return {"total_minutes": int, "status": "ok"} or None. Note: the 5s timeout is intentionally shorter than the server's 10s (ReadUPSMinutes) because the dashboard serves interactive web requests and should not block a browser for 10s.
> - get_ups_full_status(): Same fetch but return entire JSON dict or None
>
> ## Class: DashboardHandler(BaseHTTPRequestHandler)
>
> ### Helper methods:
> - log_message(format, *args): Override to print with timestamp
> - get_session_token() -> str: Extract session_token from Cookie header using SimpleCookie
> - is_authenticated() -> bool: Validate session token
> - send_json_response(data, status=200): Send JSON with proper Content-Type and Content-Length headers
> - redirect_to_login(): Send 302 to /login
>
> ### do_GET():
> Route by parsed path:
> - /login → serve_login_page() (no auth required)
> - /logout → handle_logout() (clears session cookie, redirects to /login)
> - All other routes require authentication (redirect to /login if not authenticated):
>   - / or /index.html → serve_dashboard()
>   - /api/clients → serve_clients_data()
>   - /api/config → serve_config_data()
>   - /api/ups_status → serve_ups_status()
>   - /api/ups_full_status → serve_ups_full_status()
>   - /api/power_events → serve_power_events() (accepts ?limit=N query param, default 100)
>   - anything else → 404
>
> ### do_POST():
> - /api/login → handle_login (no auth required): validate access code, create session, set cookie: session_token=<token>; Path=/; HttpOnly; Max-Age=86400
> - All other routes require authentication (return 401 JSON if not):
>   - /api/update_shutdown → handle_update_shutdown: requires hostname and seconds in JSON body
>   - /api/update_config → handle_update_config: requires key and value in JSON body
>   - anything else → 404
>
> ### handle_login(data):
> - Require 'code' field
> - Verify with verify_access_code()
> - On success: create session, set HttpOnly cookie with 24h max-age, return {"success": true}
> - On failure: return 401 {"success": false, "error": "Invalid access code"}
>
> ### handle_logout():
> - Destroy session if token exists
> - Set expired cookie (Max-Age=0)
> - Redirect to /login
>
> ### serve_dashboard():
> - Check if DB_PATH exists, show error page if not
> - Otherwise call generate_dashboard_html() and serve as text/html
>
> ### Handler method specifications:
> - serve_login_page(): Calls generate_login_html(), sends result as text/html response
> - serve_clients_data(): Calls load_client_connections(), sends result as JSON response
> - serve_config_data(): Calls load_configuration(), sends result as JSON response
> - serve_ups_status(): Calls get_ups_status(), sends as JSON response (or 503 with error JSON if None)
> - serve_ups_full_status(): Calls get_ups_full_status(), sends as JSON response (or 503 with error JSON if None)
> - serve_power_events(): Parses ?limit=N query param (default 100), calls load_power_events(limit), sends as JSON
> - handle_update_shutdown(): Reads JSON body, extracts hostname and seconds, calls update_client_shutdown_time(), sends success/failure JSON
> - handle_update_config(): Reads JSON body, extracts key and value, calls update_config_value(), sends success/failure JSON
>
> ### Error page generation:
> - generate_error_page(title, message): Simple HTML error page with dark theme
>
> ## Server startup:
> At the bottom:
> - Initialize access code in DB
> - Parse optional port from command line args (default 8080)
> - Print startup message
> - Create HTTPServer(('', port), DashboardHandler)
> - server.serve_forever()
>
> For now, create placeholder methods:
> - generate_login_html(): return a minimal "<!-- Login page placeholder -->" string
> - generate_dashboard_html(): return a minimal "<!-- Dashboard placeholder -->" string
>
> We will fill these in the next prompt.

---

## Prompt 6 — Dashboard: Full Embedded HTML/CSS/JS Frontend

> Replace the generate_login_html() and generate_dashboard_html() placeholder methods in server/UPSdashboard.py with full implementations. Use ONLY Python standard library modules (no external dependencies). These methods return complete HTML strings with embedded CSS and JavaScript. No external files or CDNs — everything is inline.
>
> IMPORTANT: Refer to the "Riello UPS JSON API Reference" section above and fetch those URLs if you haven't already. The System Status tab displays UPS metrics using JSON field names from the Riello live_data.json API. Use the field mapping you built (from MODBUS tables, BACnet descriptions, SNMP MIB, and field name patterns) to display correct labels, units, and scaling (e.g., frequency ÷10 for Hz, battery voltage ÷10 for V).
>
> ## generate_login_html():
> Return a complete HTML page with:
> - Title: "🔌 Login - UPS Dashboard"
> - Dark theme: body background linear-gradient(135deg, #1a1a2e 0%, #16213e 100%), min-height 100vh, centered flexbox
> - Font: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif
> - Login container: background #1e1e2e, border-radius 12px, box-shadow 0 20px 60px rgba(0,0,0,0.5), border 1px solid #2a2a3e, max-width 400px, padding 40px
> - Header with "🔌 UPS Dashboard" title (white, 2em) and "Enter access code to continue" subtitle (#a1a1aa)
> - Form with:
>   - Label "Access Code" (#d4d4d8)
>   - Password input field: background #27293d, border 1px solid #3f3f55, border-radius 6px, color #e4e4e7, focus border-color #3b82f6
>   - Submit button: full width, background linear-gradient(135deg, #3b82f6, #2563eb), white text, border-radius 6px, hover brightness 1.1, active transform scale(0.98)
>   - Error message div (hidden by default, red background)
> - JavaScript: fetch POST to /api/login with JSON {code: input.value}, on success redirect to /, on error show message, handle Enter key
>
> ## generate_dashboard_html():
> Return a massive complete HTML page with all of the following. This is a single-page app with tabbed navigation. All data fetching is done via the /api/* endpoints using JavaScript fetch().
>
> ### Header:
> - Fixed bar at top, background #1a1a2e, border-bottom 1px solid #2a2a3e
> - Left: "🔌 UPS Dashboard" title
> - Center: Real-time battery status indicator showing "⚡ Battery: XX min" — fetched from /api/ups_status every 30 seconds. Color-coded: green (>30 min), yellow (15-30), red (<15)
> - Right: Logout button (links to /logout)
>
> ### Navigation Tabs:
> 4 tabs below header: "System Status", "Client Connections", "Power Events", "Configuration"
> - Active tab: border-bottom 2px solid #3b82f6, color white
> - Inactive: color #a1a1aa, hover color white
> - Tabs switch content panels via JavaScript (show/hide divs)
>
> ### Tab 1 — System Status:
> Section cards with dark backgrounds (#1e1e2e), rounded corners, subtle borders (#2a2a3e):
>
> Card "Input Measurements":
> - 3-column grid showing Phase 1, Phase 2, Phase 3
> - Each phase shows: Voltage (vin1/vin2/vin3), Current (ain1/ain2/ain3), Frequency (fin)
> - Values fetched from /api/ups_full_status
>
> Card "Bypass Status":
> - 3-column: Voltage (vbyp1/vbyp2/vbyp3), Frequency (fbyp)
>
> Card "Output Measurements":
> - 3-column: Voltage (vout1/vout2/vout3), Current (aout1/aout2/aout3), Power (w1/w2/w3), Load % (load1/load2/load3)
> - Calculate total kVA and kW from sum of phase values
>
> Card "Battery Status":
> - Capacity % (batcap), Autonomy min (autonomy), Voltage (vbatp, and vbatn for negative bus if available), Current (abatp)
> - Visual battery level bar (colored green/yellow/red by percentage)
>
> Card "Environmental":
> - System Temperature (tsys), External/Battery Temperature (tbatext), Energy (KWh)
>
> Card "System Status":
> - UPS Status code (system_status), Alarm Status (alarms)
> - Human-readable status descriptions
>
> Refresh button to reload all data
>
> ### Tab 2 — Client Connections:
> - Table with columns: Hostname, IP Address, Port, Last Connection, Shutdown Delay (seconds)
> - Data from /api/clients
> - The Shutdown Delay column has editable input fields (number type)
> - "Save" button per row that POSTs to /api/update_shutdown with {"hostname": hostname, "seconds": value}
> - Refresh button
> - Styled table: dark rows, alternating slightly different backgrounds, hover highlights
>
> ### Tab 3 — Power Events:
> - Table with columns: ID, Event Type, Time, V-in 1, V-in 2, V-in 3, Battery Current, Autonomy, Details
> - Data from /api/power_events
> - Event type badges: mains_lost (red), mains_restored (green), shutdown_initiated (orange/amber)
> - Refresh button
> - Show last 100 events by default
>
> ### Tab 4 — Configuration:
> - Table with columns: Key, Value, Action
> - Data from /api/config
> - Value column has editable input fields (text type)
> - "Save" button per row that POSTs to /api/update_config with {"key": key, "value": value}
> - Note: there is no "Delete" action for configuration keys. Keys added by mistake must be corrected via the Value field or removed directly from the SQLite database.
> - Refresh button
>
> ### Global Styling:
> - Dark theme throughout: backgrounds #16213e / #1a1a2e / #1e1e2e / #27293d
> - Text colors: white for headings, #d4d4d8 for body, #a1a1aa for secondary
> - Accent: #3b82f6 (blue) for buttons, active states, links
> - Cards: rounded corners (8-12px), subtle shadows, 1px solid #2a2a3e borders
> - Tables: full width, border-collapse, dark striped rows
> - Inputs: dark backgrounds (#27293d), light borders (#3f3f55), focus glow
> - Buttons: gradient backgrounds, hover brightness, smooth transitions
> - Success/error alert notifications that auto-dismiss after 3 seconds
> - Responsive layout with CSS grid and flexbox
> - Smooth transitions on tab switches
>
> ### JavaScript Logic:
> - On page load: fetch all data, populate all tabs, start 30s battery status auto-refresh
> - switchTab(tabName) function to show/hide content panels and update active tab styling
> - fetchClients(), fetchConfig(), fetchPowerEvents(), fetchUPSStatus(), fetchUPSFullStatus() functions
> - updateShutdown(hostname, seconds), updateConfig(key, value) functions with fetch POST
> - showAlert(message, type) function for success/error notifications
> - refreshSystemStatus() function that fetches /api/ups_full_status and updates all metric displays
> - Format numbers to appropriate decimal places
> - Handle API errors gracefully with user-visible messages

---

## Prompt 7 — Systemd Service Files

> Create three systemd service files:
>
> ### server/UPSserver.service:
> [Unit]
> Description=UPS Server - Listens for client broadcasts and manages client connections
> After=network.target network-online.target
> Wants=network-online.target
>
> [Service]
> Type=simple
> User=root
> Group=root
> WorkingDirectory=/opt/UPSserver
> Environment=PATH=/usr/local/bin:/usr/bin:/bin
> Environment=PYTHONUNBUFFERED=1
> StandardOutput=append:/var/log/UPSserver.log
> StandardError=append:/var/log/UPSserver_error.log
> Restart=always
> RestartSec=30
> ExecStart=/usr/bin/python3 /opt/UPSserver/UPSserver.py
> KillMode=mixed
> KillSignal=SIGTERM
> TimeoutStopSec=30
>
> [Install]
> WantedBy=multi-user.target
>
> ### server/UPSdashboard.service:
> [Unit]
> Description=Python UPSdashboard Service (HTTP)
> After=network.target
>
> [Service]
> Type=simple
> User=root
> Group=root
> WorkingDirectory=/opt/UPSserver
> Restart=always
> RestartSec=30
> ExecStart=/usr/bin/python3 /opt/UPSserver/UPSdashboard.py
> StandardOutput=append:/var/log/UPSdashboard.log
> StandardError=append:/var/log/UPSdashboard_error.log
>
> [Install]
> WantedBy=multi-user.target
>
> ### client/UPSclient.service:
> [Unit]
> Description=Python UPSclient Service
> After=network.target
>
> [Service]
> Type=simple
> User=root
> Group=root
> WorkingDirectory=/opt/UPSclient
> Restart=always
> RestartSec=30
> ExecStart=/usr/bin/python3 /opt/UPSclient/UPSclient.py
> StandardOutput=append:/var/log/UPSclient.log
> StandardError=append:/var/log/UPSclient_error.log
>
> [Install]
> WantedBy=multi-user.target

---

## Prompt 8 — Logrotate Configuration Files

> Create three logrotate configuration files with IDENTICAL structure (only file/service names differ):
>
> ### server/UPSserver.logrotate:
> Rotates: /var/log/UPSserver.log and /var/log/UPSserver_error.log
> Post-rotate: systemctl restart UPSserver.service
>
> ### server/UPSdashboard.logrotate:
> Rotates: /var/log/UPSdashboard.log and /var/log/UPSdashboard_error.log
> Post-rotate: systemctl restart UPSdashboard.service
>
> ### client/UPSclient.logrotate:
> Rotates: /var/log/UPSclient.log and /var/log/UPSclient_error.log
> Post-rotate: systemctl restart UPSclient.service
>
> All three use this exact configuration block (substitute SERVICE_NAME):
>
> /var/log/SERVICE_NAME.log /var/log/SERVICE_NAME_error.log {
>     daily
>     rotate 7
>     maxage 7
>     maxsize 10M
>     compress
>     delaycompress
>     missingok
>     notifempty
>     create 0644 root root
>     dateext
>     dateformat -%Y%m%d
>     extension .log
>     postrotate
>         systemctl restart SERVICE_NAME.service > /dev/null 2>&1 || true
>     endscript
> }

---

## Verification

After completing all 8 prompts, verify:

1. **Server starts**: `cd server && python3 UPSserver.py` — should initialize DB, start UDP/TCP listeners
2. **Dashboard starts**: `cd server && python3 UPSdashboard.py` — should serve on port 8080
3. **Client starts**: `cd client && python3 UPSclient.py` — should broadcast discovery
4. **No external deps**: `grep -rE "^(import|from) (requests|flask|fastapi|aiohttp|httpx)" . --include="*.py"` — should return nothing
5. **All files present**: verify all `.py`, `.service`, and `.logrotate` files exist
6. **Dashboard accessible**: open http://localhost:8080, login with `ups-riello-r2ut`, verify 4 tabs render
