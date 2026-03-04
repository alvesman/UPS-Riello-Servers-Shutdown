#!/usr/bin/env python3
"""
UPS Server - Listens for client broadcasts and manages client connections.
"""

import socket
import threading
import json
import time
import logging
import sqlite3
import platform
import subprocess
import sys
import urllib.request
import urllib.error
import ssl
from typing import Dict, Tuple
from datetime import datetime

# Configure logging with custom handlers
# INFO and WARNING go to stdout (captured by StandardOutput in systemd)
# ERROR and CRITICAL go to stderr (captured by StandardError in systemd)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Create formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Handler for INFO and WARNING -> stdout
stdout_handler = logging.StreamHandler(sys.stdout)
stdout_handler.setLevel(logging.INFO)
stdout_handler.setFormatter(formatter)
stdout_handler.addFilter(lambda record: record.levelno < logging.ERROR)

# Handler for ERROR and CRITICAL -> stderr
stderr_handler = logging.StreamHandler(sys.stderr)
stderr_handler.setLevel(logging.ERROR)
stderr_handler.setFormatter(formatter)

# Add handlers to logger
logger.addHandler(stdout_handler)
logger.addHandler(stderr_handler)

# Configuration
UDP_BROADCAST_PORT = 5225
TCP_SERVER_PORT = 5226

DISCOVERY_MESSAGE = b"UPS_DISCOVER"
HEARTBEAT_TIMEOUT = 90  # 90 seconds = 30s + max 30s random + 30s buffer

# UPS Monitoring Configuration
# curl -k https://192.168.155.55/json/live_data.json
UPS_URL = 'https://192.168.155.55/json/live_data.json'  # Default UPS data
UPS_CHECK_INTERVAL = 60  # Check UPS every 60 seconds

class ClientConnection:
    """Represents a connected client."""
    
    def __init__(self, hostname: str, address: Tuple[str, int], conn: socket.socket):
        self.hostname = hostname
        self.address = address
        self.conn = conn
        self.last_heartbeat = time.time()
        self.connected = True
    
    def update_heartbeat(self):
        """Update the last heartbeat timestamp."""
        self.last_heartbeat = time.time()
    
    def is_alive(self) -> bool:
        """Check if client is still alive based on heartbeat timeout."""
        return time.time() - self.last_heartbeat < HEARTBEAT_TIMEOUT

class ReadUPSMinutes:
    """Class to read UPS minutes using direct JSON API access."""
    @staticmethod
    def get_total_minutes(url):
        """
        Extract total minutes of autonomy time from UPS JSON API
        
        Args:
            url (str): URL to the UPS JSON endpoint (e.g., https://192.168.155.55/json/live_data.json)
        Returns:
            int: Total minutes or None if failed
        """
        try:
            logger.debug(f"Fetching UPS data from URL: {url}")
            
            # Create SSL context that doesn't verify certificates (like curl -k)
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            # Create request with SSL context
            request = urllib.request.Request(url)
            
            # Fetch the JSON data
            with urllib.request.urlopen(request, context=ssl_context, timeout=10) as response:
                data = response.read().decode('utf-8')
                json_data = json.loads(data)
                
                # Extract autonomy field
                if 'autonomy' not in json_data:
                    logger.warning(f"'autonomy' field not found in JSON response from {url}")
                    return None
                
                autonomy_minutes = json_data['autonomy']
                
                # Validate that it's a number
                if not isinstance(autonomy_minutes, (int, float)):
                    logger.warning(f"Invalid autonomy value type: {type(autonomy_minutes).__name__}")
                    return None
                
                # Convert to integer
                total_minutes = int(autonomy_minutes)
                logger.info(f"Successfully retrieved UPS autonomy: {total_minutes} minutes")
                return total_minutes
                
        except urllib.error.HTTPError as e:
            logger.error(f"HTTP error accessing UPS at {url}: {e.code} {e.reason}")
            return None
        except urllib.error.URLError as e:
            logger.error(f"URL error accessing UPS at {url}: {str(e.reason)}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response from {url}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in get_total_minutes: {type(e).__name__}")
            logger.error(f"Error details: {str(e)}")
            logger.error(f"URL: {url}")
            import traceback
            logger.error(f"Traceback:\n{traceback.format_exc()}")
            return None
        
class UPSServer:
    """Main server class for UPS monitoring system."""
    
    def __init__(self, db_path: str = 'ups_clients.db'):
        self.clients: Dict[str, ClientConnection] = {}
        self.running = False
        self.udp_socket = None
        self.tcp_socket = None
        self.lock = threading.Lock()
        self.db_path = db_path
        self._init_database()
        self.consecutive_low_readings = 0  # Track consecutive low UPS readings
        self.REQUIRED_LOW_READINGS = 5  # Number of consecutive low readings before shutdown
        self.RECOVERY_BUFFER_MINUTES = 60  # Extra minutes above threshold required to exit recovery mode
        
        # Track mains power state
        self.mains_power_present = True  # Assume mains is present at startup
        self.INPUT_VOLTAGE_THRESHOLD = 50  # Voltage below this indicates mains lost
        
        # Check if we're recovering from a previous shutdown
        self.recovery_mode = self._check_recovery_mode()
        if self.recovery_mode:
            logger.warning("Server starting in RECOVERY MODE - shutdown triggers will be ignored until UPS battery recovers")
    
    def _init_database(self):
        """Initialize the SQLite database for tracking client connections."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create clients table if it doesn't exist
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS client_connections (
                    hostname TEXT PRIMARY KEY,
                    ip_address TEXT,
                    port INTEGER,
                    last_connection_time TEXT,
                    seconds_to_shutdown INTEGER DEFAULT 0
                )
            ''')
            
            # Create configuration table if it doesn't exist
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS configuration (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            ''')
            
            # Create power_events table if it doesn't exist
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS power_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    event_time TEXT NOT NULL,
                    vin1 INTEGER,
                    vin2 INTEGER,
                    vin3 INTEGER,
                    battery_current INTEGER,
                    autonomy INTEGER,
                    details TEXT
                )
            ''')
            
            # Insert default UPS_URL if not exists
            cursor.execute('''
                INSERT OR IGNORE INTO configuration (key, value)
                VALUES ('UPS_URL', ?)
            ''', (UPS_URL,))
            
            # Insert default UPS_minimum_minutes if not exists
            cursor.execute('''
                INSERT OR IGNORE INTO configuration (key, value)
                VALUES ('UPS_minimum_minutes', '15')
            ''')
            
            # Insert default pfSense SSH username if not exists
            cursor.execute('''
                INSERT OR IGNORE INTO configuration (key, value)
                VALUES ('pfsense_ssh_username', 'admin')
            ''')
            
            # Insert default pfSense SSH IP address if not exists
            cursor.execute('''
                INSERT OR IGNORE INTO configuration (key, value)
                VALUES ('pfsense_ssh_ip', '192.168.155.1')
            ''')
            
            # Insert default pfSense SSH key path if not exists
            cursor.execute('''
                INSERT OR IGNORE INTO configuration (key, value)
                VALUES ('pfsense_ssh_key_path', '/root/.ssh/pfsense_id_rsa')
            ''')
            
            # Insert default shutdown_issued flag if not exists
            # This flag is set to 'true' just before issuing a shutdown command
            # and is used to detect if we're recovering from a shutdown
            cursor.execute('''
                INSERT OR IGNORE INTO configuration (key, value)
                VALUES ('shutdown_issued', 'false')
            ''')
            
            conn.commit()
            conn.close()
            logger.info(f"Database initialized: {self.db_path}")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
    
    def _record_client_connection(self, hostname: str, address: Tuple[str, int]):
        """Record or update client connection in the database."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            ip_address, port = address
            current_time = datetime.now().isoformat()
            
            # Check if client exists
            cursor.execute('SELECT hostname FROM client_connections WHERE hostname = ?', (hostname,))
            result = cursor.fetchone()
            
            if result:
                # Update existing record
                cursor.execute('''
                    UPDATE client_connections 
                    SET ip_address = ?, port = ?, last_connection_time = ?
                    WHERE hostname = ?
                ''', (ip_address, port, current_time, hostname))
            else:
                # Insert new record
                cursor.execute('''
                    INSERT INTO client_connections (hostname, ip_address, port, last_connection_time)
                    VALUES (?, ?, ?, ?)
                ''', (hostname, ip_address, port, current_time))
            
            conn.commit()
            conn.close()
            logger.debug(f"Recorded connection for {hostname} at {current_time}")
        except Exception as e:
            logger.error(f"Failed to record client connection: {e}")
    
    def _update_heartbeat_time(self, hostname: str, address: Tuple[str, int]):
        """Update the last connection time when a heartbeat is received.
        
        This keeps the database updated with the most recent activity time.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            ip_address, port = address
            current_time = datetime.now().isoformat()
            
            cursor.execute('''\
                UPDATE client_connections 
                SET last_connection_time = ?, ip_address = ?, port = ?
                WHERE hostname = ?
            ''', (current_time, ip_address, port, hostname))
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to update heartbeat time: {e}")
    
    def get_client_history(self, hostname: str = None):
        """Get connection history for a specific client or all clients.
        
        Args:
            hostname: Optional hostname to filter by. If None, returns all clients.
            
        Returns:
            List of dictionaries containing client connection information.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if hostname:
                cursor.execute('''
                    SELECT hostname, ip_address, port, last_connection_time, seconds_to_shutdown
                    FROM client_connections
                    WHERE hostname = ?
                ''', (hostname,))
            else:
                cursor.execute('''
                    SELECT hostname, ip_address, port, last_connection_time, seconds_to_shutdown
                    FROM client_connections
                    ORDER BY last_connection_time DESC
                ''')
            
            results = cursor.fetchall()
            conn.close()
            
            return [
                {
                    'hostname': row[0],
                    'ip_address': row[1],
                    'port': row[2],
                    'last_connection_time': row[3],
                    'seconds_to_shutdown': row[4]
                }
                for row in results
            ]
        except Exception as e:
            logger.error(f"Failed to get client history: {e}")
            return []
    
    def get_config_value(self, key: str, default: str = None) -> str:
        """Get a configuration value from the database.
        
        Args:
            key: Configuration key to retrieve
            default: Default value if key is not found
            
        Returns:
            Configuration value or default
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT value FROM configuration WHERE key = ?', (key,))
            result = cursor.fetchone()
            
            conn.close()
            
            return result[0] if result else default
        except Exception as e:
            logger.error(f"Failed to get config value for {key}: {e}")
            return default
    
    def set_config_value(self, key: str, value: str):
        """Set a configuration value in the database.
        
        Args:
            key: Configuration key
            value: Configuration value
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO configuration (key, value)
                VALUES (?, ?)
            ''', (key, value))
            
            conn.commit()
            conn.close()
            logger.info(f"Configuration updated: {key} = {value}")
        except Exception as e:
            logger.error(f"Failed to set config value for {key}: {e}")
    
    def _check_recovery_mode(self) -> bool:
        """Check if the server is recovering from a previous shutdown.
        
        This is determined by checking if the 'shutdown_issued' flag is set
        to 'true' in the database. This flag is set just before the server
        issues shutdown commands and is cleared when the UPS battery
        recovers above the threshold plus a buffer.
        
        Returns:
            True if in recovery mode (shutdown was previously issued), False otherwise.
        """
        shutdown_issued = self.get_config_value('shutdown_issued', 'false')
        return shutdown_issued.lower() == 'true'
    
    def _set_shutdown_issued(self, issued: bool):
        """Set the shutdown_issued flag in the database.
        
        Args:
            issued: True to set the flag, False to clear it.
        """
        value = 'true' if issued else 'false'
        self.set_config_value('shutdown_issued', value)
        if issued:
            logger.critical("Shutdown issued flag SET - recovery mode will be active on next startup")
        else:
            logger.info("Shutdown issued flag CLEARED - normal operation resumed")
    
    def _exit_recovery_mode(self):
        """Exit recovery mode after UPS battery has recovered sufficiently."""
        self.recovery_mode = False
        self._set_shutdown_issued(False)
        self.consecutive_low_readings = 0
        logger.info("Exited RECOVERY MODE - normal shutdown monitoring resumed")
    
    def _record_power_event(self, event_type: str, vin1: int = None, vin2: int = None, vin3: int = None, 
                           battery_current: int = None, autonomy: int = None, details: str = None):
        """Record a power event in the database.
        
        Args:
            event_type: Type of event ('mains_lost', 'mains_restored', 'shutdown_initiated')
            vin1, vin2, vin3: Input voltages for three phases
            battery_current: Battery current (negative = charging, positive = discharging)
            autonomy: Battery autonomy in minutes
            details: Additional details as text
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            event_time = datetime.now().isoformat()
            
            cursor.execute('''
                INSERT INTO power_events (event_type, event_time, vin1, vin2, vin3, battery_current, autonomy, details)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (event_type, event_time, vin1, vin2, vin3, battery_current, autonomy, details))
            
            conn.commit()
            conn.close()
            logger.info(f"Power event recorded: {event_type} at {event_time}")
        except Exception as e:
            logger.error(f"Failed to record power event: {e}")
    
    def _check_mains_power_state(self, ups_data: dict) -> bool:
        """Check if mains power is present based on UPS data.
        
        Args:
            ups_data: Full UPS data dictionary from JSON API
            
        Returns:
            True if mains power is present, False if lost
        """
        # Get input voltages (all three phases)
        vin1 = ups_data.get('vin1', 0)
        vin2 = ups_data.get('vin2', 0)
        vin3 = ups_data.get('vin3', 0)
        
        # Get battery current (negative = charging, positive = discharging)
        battery_current = ups_data.get('abatp', 0)
        
        # Mains is considered present if:
        # 1. At least one input voltage is above threshold (typically ~220V)
        # 2. Battery current is negative (charging) or very low
        
        voltage_present = (vin1 > self.INPUT_VOLTAGE_THRESHOLD or 
                          vin2 > self.INPUT_VOLTAGE_THRESHOLD or 
                          vin3 > self.INPUT_VOLTAGE_THRESHOLD)
        
        battery_charging = battery_current < 5  # Negative or very low (not discharging significantly)
        
        # Mains is present if voltage is good OR battery is charging
        # (use OR because sometimes voltage readings might be unreliable)
        return voltage_present or battery_charging
    
    def _get_full_ups_data(self, url: str) -> dict:
        """Fetch complete UPS data from JSON API.
        
        Args:
            url: URL to the UPS JSON endpoint
            
        Returns:
            Dictionary with UPS data, or None if failed
        """
        try:
            logger.debug(f"Fetching full UPS data from URL: {url}")
            
            # Create SSL context that doesn't verify certificates
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            # Create request with SSL context
            request = urllib.request.Request(url)
            
            # Fetch the JSON data
            with urllib.request.urlopen(request, context=ssl_context, timeout=10) as response:
                data = response.read().decode('utf-8')
                json_data = json.loads(data)
                return json_data
                
        except Exception as e:
            logger.error(f"Failed to fetch full UPS data: {e}")
            return None
    
    def start(self):
        """Start the server."""
        logger.info("Starting UPS Server...")
        self.running = True
        
        # Start UDP broadcast listener
        udp_thread = threading.Thread(target=self._udp_listener, daemon=True)
        udp_thread.start()
        
        # Start TCP server
        tcp_thread = threading.Thread(target=self._tcp_server, daemon=True)
        tcp_thread.start()
        
        # Start client monitor
        monitor_thread = threading.Thread(target=self._monitor_clients, daemon=True)
        monitor_thread.start()
        
        # Start UPS monitor
        ups_thread = threading.Thread(target=self._ups_monitor, daemon=True)
        ups_thread.start()
        
        logger.info("UPS Server started successfully")
        
        # Keep main thread alive
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Received shutdown signal")
            self.stop()
    
    def stop(self):
        """Stop the server."""
        logger.info("Stopping UPS Server...")
        self.running = False
        
        # Close all client connections
        with self.lock:
            for client in self.clients.values():
                try:
                    client.conn.close()
                except:
                    pass
            self.clients.clear()
        
        # Close sockets
        if self.udp_socket:
            try:
                self.udp_socket.close()
            except:
                pass
        
        if self.tcp_socket:
            try:
                self.tcp_socket.close()
            except:
                pass
        
        logger.info("UPS Server stopped")
    
    def _udp_listener(self):
        """Listen for UDP broadcast messages from clients."""
        try:
            # Create UDP socket
            self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.udp_socket.bind(('', UDP_BROADCAST_PORT))
            
            logger.info(f"UDP listener started on port {UDP_BROADCAST_PORT}")
            
            while self.running:
                try:
                    self.udp_socket.settimeout(1.0)
                    data, addr = self.udp_socket.recvfrom(1024)
                    
                    if data == DISCOVERY_MESSAGE:
                        logger.info(f"Received discovery request from {addr}")
                        
                        # Send response with TCP server info
                        response = json.dumps({
                            'tcp_port': TCP_SERVER_PORT,
                            'server_ip': self._get_server_ip()
                        }).encode('utf-8')
                        
                        # Send to original address (works for local clients)
                        self.udp_socket.sendto(response, addr)
                        logger.info(f"Sent discovery response to {addr}")
                        
                        # Also broadcast (for relayed clients)
                        self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                        self.udp_socket.sendto(response, ('<broadcast>', UDP_BROADCAST_PORT))
                        logger.info(f"Broadcast discovery response on port {UDP_BROADCAST_PORT}")
                
                except socket.timeout:
                    continue
                except Exception as e:
                    if self.running:
                        logger.error(f"Error in UDP listener: {e}")
        
        except Exception as e:
            logger.error(f"Failed to start UDP listener: {e}")
    
    def _tcp_server(self):
        """TCP server for client connections."""
        try:
            # Create TCP socket
            self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.tcp_socket.bind(('', TCP_SERVER_PORT))
            self.tcp_socket.listen(5)
            
            logger.info(f"TCP server started on port {TCP_SERVER_PORT}")
            
            while self.running:
                try:
                    self.tcp_socket.settimeout(1.0)
                    conn, addr = self.tcp_socket.accept()
                    
                    # Handle client in separate thread
                    client_thread = threading.Thread(
                        target=self._handle_client,
                        args=(conn, addr),
                        daemon=True
                    )
                    client_thread.start()
                
                except socket.timeout:
                    continue
                except Exception as e:
                    if self.running:
                        logger.error(f"Error accepting connection: {e}")
        
        except Exception as e:
            logger.error(f"Failed to start TCP server: {e}")
    
    def _handle_client(self, conn: socket.socket, addr: Tuple[str, int]):
        """Handle a client connection."""
        try:
            # Receive client identification
            conn.settimeout(5.0)
            data = conn.recv(1024)
            
            if not data:
                logger.warning(f"No identification received from {addr}")
                conn.close()
                return
            
            client_info = json.loads(data.decode('utf-8'))
            hostname = client_info.get('hostname')
            
            if not hostname:
                logger.warning(f"Invalid identification from {addr}")
                conn.close()
                return
            
            logger.info(f"Client connected: {hostname} from {addr}")
            
            # Record connection in database
            self._record_client_connection(hostname, addr)
            
            # Create client connection object
            client = ClientConnection(hostname, addr, conn)
            
            with self.lock:
                # Remove old connection if exists
                if hostname in self.clients:
                    try:
                        self.clients[hostname].conn.close()
                    except:
                        pass
                
                self.clients[hostname] = client
            
            # Send welcome message
            welcome = json.dumps({'status': 'connected', 'message': 'Welcome to UPS Server'})
            conn.sendall(welcome.encode('utf-8') + b'\n')
            
            # Handle client messages
            conn.settimeout(1.0)
            buffer = ""
            
            while self.running and client.connected:
                try:
                    data = conn.recv(1024)
                    
                    if not data:
                        logger.info(f"Client {hostname} disconnected")
                        break
                    
                    buffer += data.decode('utf-8')
                    
                    # Process complete messages (newline-delimited)
                    while '\n' in buffer:
                        line, buffer = buffer.split('\n', 1)
                        
                        if line.strip():
                            try:
                                msg = json.loads(line)
                                
                                if msg.get('type') == 'heartbeat':
                                    client.update_heartbeat()
                                    logger.debug(f"Heartbeat from {hostname}")
                                    
                                    # Update database with heartbeat time
                                    self._update_heartbeat_time(hostname, addr)
                                    
                                    # Send heartbeat acknowledgment
                                    ack = json.dumps({'type': 'heartbeat_ack'})
                                    conn.sendall(ack.encode('utf-8') + b'\n')
                            
                            except json.JSONDecodeError:
                                logger.warning(f"Invalid JSON from {hostname}: {line}")
                
                except socket.timeout:
                    continue
                except Exception as e:
                    logger.error(f"Error handling client {hostname}: {e}")
                    break
        
        except Exception as e:
            logger.error(f"Error in client handler: {e}")
        
        finally:
            # Clean up
            with self.lock:
                if hostname in self.clients and self.clients[hostname].conn == conn:
                    del self.clients[hostname]
                    logger.info(f"Client {hostname} removed from active connections")
            
            try:
                conn.close()
            except:
                pass
    
    def _monitor_clients(self):
        """Monitor client connections and remove dead ones."""
        while self.running:
            time.sleep(10)  # Check every 10 seconds
            
            with self.lock:
                dead_clients = []
                
                for hostname, client in self.clients.items():
                    if not client.is_alive():
                        dead_clients.append(hostname)
                        logger.warning(f"Client {hostname} timed out")
                
                for hostname in dead_clients:
                    try:
                        self.clients[hostname].conn.close()
                    except:
                        pass
                    del self.clients[hostname]
    
    def _ups_monitor(self):
        """Monitor UPS status and broadcast total minutes to clients."""
        logger.info("UPS monitor started")
        
        while self.running:
            try:
                # Get UPS URL from database
                ups_url = self.get_config_value('UPS_URL', UPS_URL)
                
                # Get full UPS data (including voltages, battery current, etc.)
                ups_data = self._get_full_ups_data(ups_url)
                
                if ups_data is None:
                    logger.warning("Failed to retrieve UPS data")
                    time.sleep(UPS_CHECK_INTERVAL)
                    continue
                
                # Check mains power state
                mains_present = self._check_mains_power_state(ups_data)
                
                # Detect state change and record event
                if mains_present != self.mains_power_present:
                    if mains_present:
                        # Mains power restored
                        logger.warning("MAINS POWER RESTORED")
                        self._record_power_event(
                            'mains_restored',
                            vin1=ups_data.get('vin1'),
                            vin2=ups_data.get('vin2'),
                            vin3=ups_data.get('vin3'),
                            battery_current=ups_data.get('abatp'),
                            autonomy=ups_data.get('autonomy'),
                            details="Mains power has been restored"
                        )
                    else:
                        # Mains power lost
                        logger.critical("MAINS POWER LOST - UPS running on battery!")
                        self._record_power_event(
                            'mains_lost',
                            vin1=ups_data.get('vin1'),
                            vin2=ups_data.get('vin2'),
                            vin3=ups_data.get('vin3'),
                            battery_current=ups_data.get('abatp'),
                            autonomy=ups_data.get('autonomy'),
                            details="Mains power has been lost, running on battery"
                        )
                    
                    self.mains_power_present = mains_present
                
                # Get total minutes from UPS data
                total_minutes = ups_data.get('autonomy')
                
                if total_minutes is not None:
                    # Get minimum minutes threshold from configuration
                    ups_minimum_minutes_str = self.get_config_value('UPS_minimum_minutes', '15')
                    try:
                        ups_minimum_minutes = int(ups_minimum_minutes_str)
                    except ValueError:
                        ups_minimum_minutes = 15
                        logger.warning(f"Invalid UPS_minimum_minutes value, using default: 15")
                    
                    # Calculate recovery threshold (threshold + buffer)
                    recovery_threshold = ups_minimum_minutes + self.RECOVERY_BUFFER_MINUTES
                    
                    # If in recovery mode, check if we can exit
                    if self.recovery_mode:
                        if total_minutes > recovery_threshold:
                            logger.info(f"UPS battery ({total_minutes} min) exceeds recovery threshold ({recovery_threshold} min)")
                            self._exit_recovery_mode()
                        else:
                            logger.warning(f"RECOVERY MODE: UPS battery ({total_minutes} min) still below recovery threshold ({recovery_threshold} min) - shutdown triggers IGNORED")
                            # Still broadcast status to clients even in recovery mode
                            message = {
                                'type': 'ups_status',
                                'total_minutes': total_minutes,
                                'recovery_mode': True,
                                'recovery_threshold': recovery_threshold,
                                'timestamp': time.time()
                            }
                            logger.info(f"UPS Total Minutes: {total_minutes} - Broadcasting to clients (recovery mode)")
                            self.broadcast_message(message)
                            # Skip the rest of the loop iteration (don't process shutdown logic)
                            time.sleep(UPS_CHECK_INTERVAL)
                            continue
                    
                    # Normal operation: Check if we need to send shutdown command
                    if total_minutes <= ups_minimum_minutes:
                        self.consecutive_low_readings += 1
                        logger.warning(f"UPS battery critical! Total minutes ({total_minutes}) <= threshold ({ups_minimum_minutes}) - consecutive reading {self.consecutive_low_readings}/{self.REQUIRED_LOW_READINGS}")
                        
                        # Only trigger shutdown after REQUIRED_LOW_READINGS consecutive readings
                        if self.consecutive_low_readings >= self.REQUIRED_LOW_READINGS:
                            logger.critical(f"Shutdown threshold reached after {self.consecutive_low_readings} consecutive low readings!")
                            
                            # Get client history to fetch seconds_to_shutdown for each client
                            client_history = self.get_client_history()
                        
                            # Track maximum seconds_to_shutdown
                            max_seconds_to_shutdown = 0
                            
                            with self.lock:
                                for hostname in list(self.clients.keys()):
                                    # Find seconds_to_shutdown for this client
                                    seconds_to_shutdown = 0
                                    for client_data in client_history:
                                        if client_data['hostname'] == hostname:
                                            seconds_to_shutdown = client_data.get('seconds_to_shutdown', 0)
                                            break
                                    
                                    # Track maximum value
                                    max_seconds_to_shutdown = max(max_seconds_to_shutdown, seconds_to_shutdown)
                                    
                                    # Send shutdown message to client
                                    shutdown_message = {
                                        'type': 'shutdown',
                                        'reason': 'low_power',
                                        'seconds_to_shutdown': seconds_to_shutdown,
                                        'total_minutes': total_minutes,
                                        'timestamp': time.time()
                                    }
                                    
                                    self._send_message_to_client_unsafe(hostname, shutdown_message)
                                    logger.critical(f"Sent shutdown command to {hostname} with {seconds_to_shutdown}s delay")
                            
                            # Record shutdown initiation event
                            self._record_power_event(
                                'shutdown_initiated',
                                vin1=ups_data.get('vin1'),
                                vin2=ups_data.get('vin2'),
                                vin3=ups_data.get('vin3'),
                                battery_current=ups_data.get('abatp'),
                                autonomy=total_minutes,
                                details=f"Shutdown initiated after {self.consecutive_low_readings} consecutive low readings. Battery at {total_minutes} minutes (threshold: {ups_minimum_minutes})"
                            )
                            
                            # After notifying all clients, shutdown this server with the maximum delay
                            self._execute_shutdown(max_seconds_to_shutdown + 30) # Add a buffer. This code must run on the last machine to shut down

                    else:
                        # Reset consecutive low readings counter when above threshold
                        if self.consecutive_low_readings > 0:
                            logger.info(f"UPS battery recovered - resetting consecutive low readings counter (was {self.consecutive_low_readings})")
                            self.consecutive_low_readings = 0
                        
                        # Broadcast normal status to all connected clients
                        message = {
                            'type': 'ups_status',
                            'total_minutes': total_minutes,
                            'timestamp': time.time()
                        }
                        
                        logger.info(f"UPS Total Minutes: {total_minutes} - Broadcasting to clients")
                        self.broadcast_message(message)
                else:
                    logger.warning("Failed to retrieve UPS total minutes")
                
            except Exception as e:
                logger.error(f"Error in UPS monitor: {e}")
            
            # Wait for next check
            time.sleep(UPS_CHECK_INTERVAL)
    
    def _get_server_ip(self) -> str:
        """Get the server's local IP address.
        
        This determines which IP address clients should use to connect.
        The server binds to 0.0.0.0 (all interfaces), but clients need
        a specific IP address to connect to.
        """
        try:
            # Create a socket to determine local IP
            # This finds which interface would be used for external connectivity
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))  # Doesn't actually send data
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            # If the above fails, try to get hostname IP
            try:
                hostname = socket.gethostname()
                ip = socket.gethostbyname(hostname)
                if ip and ip != "127.0.0.1":
                    return ip
            except:
                pass
            
            # Last resort: return empty to signal client to use server's address from UDP response
            logger.warning("Could not determine server IP, client will use source address from UDP packet")
            return ""
    
    def _send_message_to_client_unsafe(self, hostname: str, message: dict):
        """Send a message to a specific client (internal, assumes lock is held)."""
        if hostname not in self.clients:
            logger.warning(f"Client {hostname} not found")
            return False
        
        client = self.clients[hostname]
        
        try:
            msg = json.dumps(message)
            client.conn.sendall(msg.encode('utf-8') + b'\n')
            logger.info(f"Sent message to {hostname}: {message}")
            return True
        except Exception as e:
            logger.error(f"Failed to send message to {hostname}: {e}")
            return False
    
    def send_message_to_client(self, hostname: str, message: dict):
        """Send a message to a specific client."""
        with self.lock:
            return self._send_message_to_client_unsafe(hostname, message)
    
    def broadcast_message(self, message: dict):
        """Send a message to all connected clients."""
        with self.lock:
            for hostname in list(self.clients.keys()):
                self._send_message_to_client_unsafe(hostname, message)
    
    def list_clients(self):
        """List all connected clients."""
        with self.lock:
            return [
                {
                    'hostname': client.hostname,
                    'address': client.address,
                    'last_heartbeat': client.last_heartbeat
                }
                for client in self.clients.values()
            ]
    
    def _execute_shutdown(self, seconds_to_shutdown: int):
        """Execute system shutdown after specified delay.
        
        Before executing the shutdown, this method sets the 'shutdown_issued' flag
        in the database. If the shutdown fails or is interrupted, this flag will
        cause the server to start in recovery mode on next startup, preventing
        immediate re-triggering of shutdown until the UPS battery recovers.
        """
        try:
            logger.critical(f"System shutdown initiated - waiting {seconds_to_shutdown} seconds...")
            
            # Wait for the specified delay
            time.sleep(seconds_to_shutdown)

            # Get pfSense SSH configuration from database
            pfsense_username = self.get_config_value('pfsense_ssh_username', 'admin')
            pfsense_ip = self.get_config_value('pfsense_ssh_ip', '192.168.155.1')
            pfsense_key_path = self.get_config_value('pfsense_ssh_key_path', '/root/.ssh/pfsense_id_rsa')
            
            # Guard: skip pfSense shutdown if any SSH parameter is empty
            if not pfsense_username or not pfsense_ip or not pfsense_key_path:
                logger.warning("Skipping pfSense SSH shutdown - one or more configuration values are empty: "
                              f"username='{pfsense_username}', ip='{pfsense_ip}', key_path='{pfsense_key_path}'")
            else:
                try:
                    logger.critical(f"pfSense shutdown using ssh to {pfsense_username}@{pfsense_ip} with key {pfsense_key_path}. Assuming running as root, no sudo needed.")
                    subprocess.run(['ssh', '-i', pfsense_key_path, f'{pfsense_username}@{pfsense_ip}', '/sbin/shutdown', '-p', 'now'], check=True)
                except subprocess.CalledProcessError as e:
                    logger.error(f"Failed to execute pfSense shutdown via SSH: {e}")
            
            logger.critical("Executing system shutdown NOW!")
            
            # Detect OS and execute appropriate shutdown command
            system = platform.system()
            
            if system == "Linux" or system == "Darwin":  # Linux or macOS
                # Set the shutdown_issued flag BEFORE executing shutdown
                # This ensures recovery mode is active if the server restarts
                # (e.g., power restored before shutdown completes, or shutdown fails)
                self._set_shutdown_issued(True)
                
                # Assume running as root, no sudo needed
                # -h = halt, now = immediately
                # Use full path since systemd services may not have /sbin in PATH
                subprocess.run(['/sbin/shutdown', '-h', 'now'], check=True)
            else:
                logger.error(f"Unsupported operating system: {system}")
                return
                
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to execute shutdown command: {e}")
        except Exception as e:
            logger.error(f"Error during shutdown execution: {e}")

def main():
    """Main entry point."""
    server = UPSServer()
    server.start()

if __name__ == "__main__":
    main()
