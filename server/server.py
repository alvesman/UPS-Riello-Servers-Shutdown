#!/usr/bin/env python3
"""
UPS Server - Listens for client broadcasts and manages client connections.
"""

import socket
import threading
import json
import time
import logging
import re
from typing import Dict, Tuple
import sys
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.chrome.options import Options
    from selenium.common.exceptions import TimeoutException, WebDriverException
except ImportError:
    print("Error: Selenium not installed", file=sys.stderr)
    print("Install with: pip install selenium", file=sys.stderr)
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
UDP_BROADCAST_PORT = 5225
TCP_SERVER_PORT = 5226

DISCOVERY_MESSAGE = b"UPS_DISCOVER"
HEARTBEAT_TIMEOUT = 90  # 90 seconds = 30s + max 30s random + 30s buffer

# UPS Monitoring Configuration
UPS_URL = 'https://192.168.155.55/'  # Default UPS dashboard URL
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
    """Class to read UPS minutes using get_total_minutes function."""
    @staticmethod
    def get_total_minutes(url, wait_time=5):
        """
        Extract total minutes of autonomy time
        
        Args:
            url (str): URL to the MPW-MCU dashboard
            wait_time (int): Seconds to wait for JavaScript to load
            
        Returns:
            int: Total minutes or None if failed
        """
        driver = None
        
        try:
            # Configure Chrome options (headless mode)
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--disable-web-security')
            chrome_options.add_argument('--ignore-certificate-errors')
            chrome_options.add_argument('--ignore-ssl-errors')
            chrome_options.add_argument('--disable-extensions')
            chrome_options.add_argument('--disable-logging')
            chrome_options.add_argument('--log-level=3')
            chrome_options.add_argument('--silent')
            
            # Initialize WebDriver
            driver = webdriver.Chrome(options=chrome_options)
            driver.set_page_load_timeout(30)
            
            # Load the page
            driver.get(url)
            
            # Wait for JavaScript to update values
            time.sleep(wait_time)
            
            # Try multiple selectors to find the autonomy element
            autonomy_element = None
            selectors = [
                'span.time.autonomy',
                'span.autonomy',
                '.time.autonomy',
                'span[class*="autonomy"]'
            ]
            
            for selector in selectors:
                try:
                    autonomy_element = driver.find_element(By.CSS_SELECTOR, selector)
                    if autonomy_element:
                        break
                except:
                    continue
            
            if not autonomy_element:
                return None
            
            autonomy_value = autonomy_element.text.strip()
            
            if not autonomy_value or autonomy_value == '-':
                return None
            
            # Parse HH:MM format
            match = re.match(r'^(\d{1,2}):(\d{2})$', autonomy_value)
            if match:
                hours, minutes = match.groups()
                total_minutes = int(hours) * 60 + int(minutes)
                return total_minutes
            
            return None
            
        except (TimeoutException, WebDriverException):
            return None
        except Exception:
            return None
        finally:
            if driver:
                driver.quit()
        
class UPSServer:
    """Main server class for UPS monitoring system."""
    
    def __init__(self):
        self.clients: Dict[str, ClientConnection] = {}
        self.running = False
        self.udp_socket = None
        self.tcp_socket = None
        self.lock = threading.Lock()
    
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
                        
                        self.udp_socket.sendto(response, addr)
                        logger.info(f"Sent discovery response to {addr}")
                
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
                # Get total minutes from UPS
                total_minutes = ReadUPSMinutes.get_total_minutes(UPS_URL)
                
                if total_minutes is not None:
                    # Broadcast to all connected clients
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

def main():
    """Main entry point."""
    server = UPSServer()
    server.start()

if __name__ == "__main__":
    main()
