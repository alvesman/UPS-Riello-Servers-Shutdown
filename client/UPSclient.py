#!/usr/bin/env python3
"""
UPS Client - Discovers server and maintains connection for receiving messages.
"""

import socket
import threading
import json
import time
import random
import logging
import platform
import subprocess
import sys

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
DISCOVERY_MESSAGE = b"UPS_DISCOVER"
INITIAL_RETRY_INTERVAL = 10  # seconds
MAX_RETRY_INTERVAL = 60  # seconds
HEARTBEAT_BASE_INTERVAL = 30  # seconds
HEARTBEAT_RANDOM_MAX = 30  # seconds


class UPSClient:
    """Main client class for UPS monitoring system."""
    
    def __init__(self):
        self.hostname = platform.node()
        self.server_address = None
        self.tcp_socket = None
        self.connected = False
        self.running = False
        self.lock = threading.Lock()
    
    def start(self):
        """Start the client."""
        logger.info(f"Starting UPS Client (hostname: {self.hostname})...")
        self.running = True
        
        # Start discovery thread
        discovery_thread = threading.Thread(target=self._discovery_loop, daemon=True)
        discovery_thread.start()
        
        logger.info("UPS Client started")
        
        # Keep main thread alive
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Received shutdown signal")
            self.stop()
    
    def stop(self):
        """Stop the client."""
        logger.info("Stopping UPS Client...")
        self.running = False
        
        self._disconnect()
        
        logger.info("UPS Client stopped")
    
    def _discovery_loop(self):
        """Main discovery loop with retry logic."""
        retry_interval = INITIAL_RETRY_INTERVAL
        
        while self.running:
            if not self.connected:
                logger.info("Attempting to discover server...")
                
                if self._discover_server():
                    logger.info("Server discovered, attempting to connect...")
                    
                    if self._connect_to_server():
                        logger.info("Successfully connected to server")
                        retry_interval = INITIAL_RETRY_INTERVAL  # Reset retry interval
                        
                        # Start heartbeat thread
                        heartbeat_thread = threading.Thread(
                            target=self._heartbeat_loop,
                            daemon=True
                        )
                        heartbeat_thread.start()
                        
                        # Wait while connected
                        while self.running and self.connected:
                            time.sleep(1)
                    else:
                        logger.warning("Failed to connect to server")
                else:
                    logger.warning("Server discovery failed")
                
                # Calculate next retry interval with linear backoff
                if retry_interval < MAX_RETRY_INTERVAL:
                    retry_interval = min(retry_interval + 10, MAX_RETRY_INTERVAL)
                
                logger.info(f"Retrying discovery in {retry_interval} seconds...")
                time.sleep(retry_interval)
            else:
                time.sleep(1)
    
    def _discover_server(self) -> bool:
        """Broadcast discovery message and wait for server response."""
        try:
            # Create UDP socket for broadcasting
            udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            udp_socket.settimeout(5.0)
            
            # Try localhost first (for same-machine testing)
            # Many systems don't loop broadcast packets back to localhost
            try:
                logger.debug(f"Trying localhost discovery...")
                udp_socket.sendto(DISCOVERY_MESSAGE, ('127.0.0.1', UDP_BROADCAST_PORT))
                
                try:
                    data, server_addr = udp_socket.recvfrom(1024)
                    response = json.loads(data.decode('utf-8'))
                    
                    # Get server IP from response, or use source address from UDP packet
                    server_ip = response.get('server_ip', '')
                    if not server_ip or server_ip == '0.0.0.0':
                        # Use the source IP from the UDP response
                        server_ip = server_addr[0]
                        logger.debug(f"Using UDP source address: {server_ip}")
                    
                    tcp_port = response.get('tcp_port')
                    
                    if tcp_port:
                        self.server_address = (server_ip, tcp_port)
                        logger.info(f"Server found at {self.server_address}")
                        udp_socket.close()
                        return True
                
                except socket.timeout:
                    logger.debug("No response from localhost")
            
            except Exception as e:
                logger.debug(f"Localhost discovery failed: {e}")
            
            # Try broadcast to network
            broadcast_addr = ('<broadcast>', UDP_BROADCAST_PORT)
            udp_socket.sendto(DISCOVERY_MESSAGE, broadcast_addr)
            logger.debug(f"Sent discovery broadcast to {broadcast_addr}")
            
            # Wait for response
            try:
                data, server_addr = udp_socket.recvfrom(1024)
                response = json.loads(data.decode('utf-8'))
                
                # Get server IP from response, or use source address from UDP packet
                server_ip = response.get('server_ip', '')
                if not server_ip or server_ip == '0.0.0.0':
                    # Use the source IP from the UDP response
                    server_ip = server_addr[0]
                    logger.debug(f"Using UDP source address: {server_ip}")
                
                tcp_port = response.get('tcp_port')
                
                if tcp_port:
                    self.server_address = (server_ip, tcp_port)
                    logger.info(f"Server found at {self.server_address}")
                    udp_socket.close()
                    return True
            
            except socket.timeout:
                logger.debug("No server response received from broadcast")
            
            udp_socket.close()
            return False
        
        except Exception as e:
            logger.error(f"Error during discovery: {e}")
            return False
    
    def _connect_to_server(self) -> bool:
        """Connect to the server via TCP."""
        if not self.server_address:
            return False
        
        try:
            # Create TCP socket
            self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.tcp_socket.settimeout(10.0)
            
            # Connect to server
            self.tcp_socket.connect(self.server_address)
            logger.info(f"Connected to server at {self.server_address}")
            
            # Send identification
            identification = json.dumps({
                'hostname': self.hostname,
                'timestamp': time.time()
            })
            self.tcp_socket.sendall(identification.encode('utf-8'))
            
            # Wait for welcome message
            self.tcp_socket.settimeout(5.0)
            data = self.tcp_socket.recv(1024)
            
            if data:
                welcome = json.loads(data.decode('utf-8').strip())
                logger.info(f"Server says: {welcome.get('message', 'Connected')}")
                
                with self.lock:
                    self.connected = True
                
                # Start message receiver thread
                receiver_thread = threading.Thread(
                    target=self._receive_messages,
                    daemon=True
                )
                receiver_thread.start()
                
                return True
        
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            self._disconnect()
            return False
    
    def _disconnect(self):
        """Disconnect from server."""
        with self.lock:
            self.connected = False
        
        if self.tcp_socket:
            try:
                self.tcp_socket.close()
            except:
                pass
            self.tcp_socket = None
        
        self.server_address = None
        logger.info("Disconnected from server")
    
    def _heartbeat_loop(self):
        """Send periodic heartbeats to server."""
        while self.running and self.connected:
            try:
                # Calculate next heartbeat interval
                interval = HEARTBEAT_BASE_INTERVAL + random.randint(1, HEARTBEAT_RANDOM_MAX)
                logger.debug(f"Next heartbeat in {interval} seconds")
                
                time.sleep(interval)
                
                if not self.connected:
                    break
                
                # Send heartbeat
                heartbeat = json.dumps({
                    'type': 'heartbeat',
                    'timestamp': time.time()
                })
                
                with self.lock:
                    if self.tcp_socket and self.connected:
                        try:
                            self.tcp_socket.sendall(heartbeat.encode('utf-8') + b'\n')
                            logger.debug("Heartbeat sent")
                        except Exception as e:
                            logger.error(f"Failed to send heartbeat: {e}")
                            self._disconnect()
                            break
            
            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}")
                break
    
    def _receive_messages(self):
        """Receive messages from server."""
        buffer = ""
        
        try:
            self.tcp_socket.settimeout(1.0)
            
            while self.running and self.connected:
                try:
                    data = self.tcp_socket.recv(1024)
                    
                    if not data:
                        logger.warning("Connection closed by server")
                        self._disconnect()
                        break
                    
                    buffer += data.decode('utf-8')
                    
                    # Process complete messages (newline-delimited)
                    while '\n' in buffer:
                        line, buffer = buffer.split('\n', 1)
                        
                        if line.strip():
                            try:
                                message = json.loads(line)
                                self._handle_message(message)
                            except json.JSONDecodeError:
                                logger.warning(f"Invalid JSON received: {line}")
                
                except socket.timeout:
                    continue
                except Exception as e:
                    logger.error(f"Error receiving message: {e}")
                    self._disconnect()
                    break
        
        except Exception as e:
            logger.error(f"Error in message receiver: {e}")
            self._disconnect()
    
    def _handle_message(self, message: dict):
        """Handle a message received from server."""
        msg_type = message.get('type')
                
        if msg_type == 'heartbeat_ack':
            logger.debug("Heartbeat acknowledged")
        elif msg_type == 'ups_status':
            total_minutes = message.get('total_minutes')
            timestamp = message.get('timestamp')
            logger.info(f"UPS Status Update - Total Minutes: {total_minutes}, Timestamp: {timestamp}")

        elif msg_type == 'shutdown':
            reason = message.get('reason', 'No reason provided')
            seconds_to_shutdown = message.get('seconds_to_shutdown', 0)
            logger.warning(f"SHUTDOWN command received - Type: {msg_type}, Reason: {reason}, Seconds to shutdown: {seconds_to_shutdown}")
            # Implement the actual shutdown logic
            threading.Thread(target=self._execute_shutdown, args=(seconds_to_shutdown,), daemon=True).start()

        elif msg_type == 'command':
            command = message.get('command')
            logger.info(f"Command received: {command}")
            # Handle other commands here
        else:
            logger.info(f"Unknown message type received: {message}")
    
    def _execute_shutdown(self, seconds_to_shutdown: int):
        """Execute system shutdown after specified delay."""
        try:
            logger.critical(f"System shutdown initiated - waiting {seconds_to_shutdown} seconds...")
            
            # Wait for the specified delay
            time.sleep(seconds_to_shutdown)
            
            logger.critical("Executing system shutdown NOW!")
            
            # Detect OS and execute appropriate shutdown command
            system = platform.system()
            
            if system == "Linux" or system == "Darwin":  # Linux or macOS
                # Assume running as root, no sudo needed
                # -h = halt, now = immediately
                subprocess.run(['shutdown', '-h', 'now'], check=True)
            elif system == "Windows":
                # Windows shutdown command
                # /s = shutdown, /t 0 = timeout 0 seconds, /f = force
                subprocess.run(['shutdown', '/s', '/t', '0', '/f'], check=True)
            else:
                logger.error(f"Unsupported operating system: {system}")
                return
                
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to execute shutdown command: {e}")
        except Exception as e:
            logger.error(f"Error during shutdown execution: {e}")


def main():
    """Main entry point."""
    client = UPSClient()
    client.start()


if __name__ == "__main__":
    main()
