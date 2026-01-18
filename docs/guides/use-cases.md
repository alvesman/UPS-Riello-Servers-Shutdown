# Use Cases

This guide provides practical examples and code snippets for common operations with the Riello UPS Servers Shutdown system.

---

## Use Case 1: Monitoring UPS Battery Status

### Scenario
You want to programmatically check the current UPS battery status from an external application.

### Required API Call
```
GET /api/ups_status
```

### Implementation (Python)

```python
import requests

def get_ups_battery_status(dashboard_url: str = "http://localhost:8080") -> dict:
    """
    Fetch current UPS battery status from the dashboard API.
    
    Args:
        dashboard_url: Base URL of the UPS dashboard
        
    Returns:
        Dictionary with 'total_minutes' and 'status' keys
    """
    try:
        response = requests.get(f"{dashboard_url}/api/ups_status", timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        return {"status": "error", "message": str(e)}

# Example usage
if __name__ == "__main__":
    status = get_ups_battery_status("http://192.168.1.100:8080")
    
    if status.get("status") == "ok":
        minutes = status["total_minutes"]
        print(f"Battery remaining: {minutes} minutes")
        
        if minutes <= 15:
            print("WARNING: Battery low!")
    else:
        print(f"Error: {status.get('message', 'Unknown error')}")
```

### Implementation (Bash/curl)

```bash
#!/bin/bash

DASHBOARD_URL="http://192.168.1.100:8080"

# Get UPS status
response=$(curl -s "${DASHBOARD_URL}/api/ups_status")

# Parse with jq
status=$(echo "$response" | jq -r '.status')
minutes=$(echo "$response" | jq -r '.total_minutes')

if [ "$status" == "ok" ]; then
    echo "Battery remaining: ${minutes} minutes"
    
    if [ "$minutes" -le 15 ]; then
        echo "WARNING: Battery low!"
        # Send alert, etc.
    fi
else
    echo "Error fetching UPS status"
fi
```

---

## Use Case 2: Listing All Connected Clients

### Scenario
You want to retrieve a list of all client machines that have connected to the UPS server.

### Required API Call
```
GET /api/clients
```

### Implementation (Python)

```python
import requests
from datetime import datetime

def list_connected_clients(dashboard_url: str = "http://localhost:8080") -> list:
    """
    Retrieve list of all client connections from the UPS server.
    
    Args:
        dashboard_url: Base URL of the UPS dashboard
        
    Returns:
        List of client dictionaries with hostname, ip, last_connection, etc.
    """
    try:
        response = requests.get(f"{dashboard_url}/api/clients", timeout=5)
        response.raise_for_status()
        data = response.json()
        return data.get("clients", [])
    except requests.RequestException as e:
        print(f"Error fetching clients: {e}")
        return []

def print_client_report(dashboard_url: str = "http://localhost:8080"):
    """Print a formatted report of all connected clients."""
    clients = list_connected_clients(dashboard_url)
    
    if not clients:
        print("No clients found.")
        return
    
    print(f"\n{'Hostname':<20} {'IP Address':<15} {'Last Seen':<18} {'Shutdown Delay'}")
    print("-" * 70)
    
    for client in clients:
        hostname = client.get('hostname', 'Unknown')
        ip = client.get('ip_address', 'Unknown')
        last_seen = client.get('last_connection_time', 'Never')
        delay = client.get('seconds_to_shutdown', 0)
        
        print(f"{hostname:<20} {ip:<15} {last_seen:<18} {delay}s")
    
    print(f"\nTotal clients: {len(clients)}")

# Example usage
if __name__ == "__main__":
    print_client_report("http://192.168.1.100:8080")
```

---

## Use Case 3: Updating Client Shutdown Priority

### Scenario
You need to change the shutdown delay for a specific client to adjust its priority in the shutdown sequence.

### Required API Call
```
POST /api/update_shutdown
Content-Type: application/json

{"hostname": "client-name", "seconds": 60}
```

### Implementation (Python)

```python
import requests

def update_client_shutdown_delay(
    hostname: str, 
    seconds: int,
    dashboard_url: str = "http://localhost:8080"
) -> bool:
    """
    Update the shutdown delay for a specific client.
    
    Args:
        hostname: The client's hostname
        seconds: Delay in seconds before shutdown (0 = immediate)
        dashboard_url: Base URL of the UPS dashboard
        
    Returns:
        True if successful, False otherwise
    """
    try:
        response = requests.post(
            f"{dashboard_url}/api/update_shutdown",
            json={"hostname": hostname, "seconds": seconds},
            timeout=5
        )
        response.raise_for_status()
        result = response.json()
        
        if result.get("success"):
            print(f"Updated {hostname} shutdown delay to {seconds} seconds")
            return True
        else:
            print(f"Failed: {result.get('error', 'Unknown error')}")
            return False
            
    except requests.RequestException as e:
        print(f"Error updating shutdown delay: {e}")
        return False

# Example: Configure shutdown priorities
def configure_shutdown_priorities(dashboard_url: str = "http://localhost:8080"):
    """Configure a typical shutdown priority scheme."""
    
    priorities = [
        # First tier: Development/Test (immediate shutdown)
        ("dev-server-01", 0),
        ("test-vm-01", 0),
        
        # Second tier: Web/Application servers
        ("web-server-01", 30),
        ("web-server-02", 30),
        ("app-server-01", 30),
        
        # Third tier: Caching/Queue servers
        ("redis-01", 45),
        ("rabbitmq-01", 45),
        
        # Fourth tier: Database replicas
        ("db-replica-01", 60),
        ("db-replica-02", 60),
        
        # Fifth tier: Primary database
        ("db-primary-01", 90),
    ]
    
    for hostname, delay in priorities:
        update_client_shutdown_delay(hostname, delay, dashboard_url)

if __name__ == "__main__":
    configure_shutdown_priorities("http://192.168.1.100:8080")
```

---

## Use Case 4: Updating UPS Configuration

### Scenario
You need to change the UPS URL or battery threshold programmatically.

### Required API Call
```
POST /api/update_config
Content-Type: application/json

{"key": "UPS_minimum_minutes", "value": "20"}
```

### Implementation (Python)

```python
import requests

def update_ups_config(
    key: str, 
    value: str,
    dashboard_url: str = "http://localhost:8080"
) -> bool:
    """
    Update a UPS server configuration value.
    
    Args:
        key: Configuration key (UPS_URL or UPS_minimum_minutes)
        value: New value to set
        dashboard_url: Base URL of the UPS dashboard
        
    Returns:
        True if successful, False otherwise
    """
    try:
        response = requests.post(
            f"{dashboard_url}/api/update_config",
            json={"key": key, "value": value},
            timeout=5
        )
        response.raise_for_status()
        result = response.json()
        
        if result.get("success"):
            print(f"Updated {key} = {value}")
            return True
        else:
            print(f"Failed: {result.get('error', 'Unknown error')}")
            return False
            
    except requests.RequestException as e:
        print(f"Error updating configuration: {e}")
        return False

def set_ups_url(url: str, dashboard_url: str = "http://localhost:8080") -> bool:
    """Set the UPS JSON API URL."""
    return update_ups_config("UPS_URL", url, dashboard_url)

def set_battery_threshold(minutes: int, dashboard_url: str = "http://localhost:8080") -> bool:
    """Set the minimum battery threshold for shutdown."""
    return update_ups_config("UPS_minimum_minutes", str(minutes), dashboard_url)

# Example usage
if __name__ == "__main__":
    dashboard = "http://192.168.1.100:8080"
    
    # Update UPS URL
    set_ups_url("https://192.168.1.50/json/live_data.json", dashboard)
    
    # Set battery threshold to 20 minutes
    set_battery_threshold(20, dashboard)
```

---

## Use Case 5: Building a Monitoring Dashboard

### Scenario
You want to create a custom monitoring script that checks UPS status and client connections periodically.

### Implementation (Python)

```python
import requests
import time
from datetime import datetime

class UPSMonitor:
    """Monitor UPS status and client connections."""
    
    def __init__(self, dashboard_url: str = "http://localhost:8080"):
        self.dashboard_url = dashboard_url
        self.warning_threshold = 30  # minutes
        self.critical_threshold = 15  # minutes
    
    def get_ups_status(self) -> dict:
        """Get current UPS battery status."""
        try:
            response = requests.get(
                f"{self.dashboard_url}/api/ups_status", 
                timeout=5
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException:
            return {"status": "error", "total_minutes": None}
    
    def get_clients(self) -> list:
        """Get list of connected clients."""
        try:
            response = requests.get(
                f"{self.dashboard_url}/api/clients", 
                timeout=5
            )
            response.raise_for_status()
            return response.json().get("clients", [])
        except requests.RequestException:
            return []
    
    def check_status(self):
        """Check and report UPS and client status."""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n=== UPS Status Check: {now} ===")
        
        # Check UPS battery
        ups = self.get_ups_status()
        if ups.get("status") == "ok":
            minutes = ups["total_minutes"]
            hours = minutes // 60
            mins = minutes % 60
            
            if minutes <= self.critical_threshold:
                status = "🔴 CRITICAL"
            elif minutes <= self.warning_threshold:
                status = "🟡 WARNING"
            else:
                status = "🟢 OK"
            
            print(f"Battery: {status} - {hours}h {mins}m remaining")
        else:
            print("Battery: ❌ Unable to fetch status")
        
        # Check clients
        clients = self.get_clients()
        print(f"Connected clients: {len(clients)}")
        
        for client in clients:
            hostname = client.get('hostname', 'Unknown')
            last_seen = client.get('last_connection_time', 'Unknown')
            delay = client.get('seconds_to_shutdown', 0)
            print(f"  - {hostname}: last seen {last_seen}, delay {delay}s")
    
    def run(self, interval: int = 60):
        """Run continuous monitoring."""
        print(f"Starting UPS monitor (checking every {interval}s)")
        print(f"Dashboard URL: {self.dashboard_url}")
        print("Press Ctrl+C to stop")
        
        try:
            while True:
                self.check_status()
                time.sleep(interval)
        except KeyboardInterrupt:
            print("\nMonitoring stopped.")

# Example usage
if __name__ == "__main__":
    monitor = UPSMonitor("http://192.168.1.100:8080")
    monitor.run(interval=30)  # Check every 30 seconds
```

---

## Use Case 6: Integrating with Alert Systems

### Scenario
You want to send alerts (email, Slack, etc.) when battery drops below threshold.

### Implementation (Python with Slack webhook)

```python
import requests
import time

class UPSAlertSystem:
    """Monitor UPS and send alerts when battery is low."""
    
    def __init__(
        self, 
        dashboard_url: str,
        slack_webhook_url: str = None,
        warning_threshold: int = 30,
        critical_threshold: int = 15
    ):
        self.dashboard_url = dashboard_url
        self.slack_webhook_url = slack_webhook_url
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold
        self.last_alert_level = None
    
    def get_battery_minutes(self) -> int:
        """Get current battery minutes remaining."""
        try:
            response = requests.get(
                f"{self.dashboard_url}/api/ups_status", 
                timeout=5
            )
            response.raise_for_status()
            data = response.json()
            if data.get("status") == "ok":
                return data["total_minutes"]
        except requests.RequestException:
            pass
        return None
    
    def send_slack_alert(self, message: str, level: str = "warning"):
        """Send alert to Slack channel."""
        if not self.slack_webhook_url:
            print(f"ALERT [{level}]: {message}")
            return
        
        color = "#ff0000" if level == "critical" else "#ffcc00"
        
        payload = {
            "attachments": [{
                "color": color,
                "title": f"UPS Alert - {level.upper()}",
                "text": message,
                "footer": "UPS Monitoring System"
            }]
        }
        
        try:
            requests.post(self.slack_webhook_url, json=payload, timeout=5)
        except requests.RequestException as e:
            print(f"Failed to send Slack alert: {e}")
    
    def check_and_alert(self):
        """Check battery and send alerts if needed."""
        minutes = self.get_battery_minutes()
        
        if minutes is None:
            if self.last_alert_level != "error":
                self.send_slack_alert(
                    "Unable to fetch UPS battery status!", 
                    "critical"
                )
                self.last_alert_level = "error"
            return
        
        current_level = None
        
        if minutes <= self.critical_threshold:
            current_level = "critical"
            message = (
                f"🔴 CRITICAL: UPS battery at {minutes} minutes!\n"
                f"Shutdown sequence will begin soon."
            )
        elif minutes <= self.warning_threshold:
            current_level = "warning"
            message = (
                f"🟡 WARNING: UPS battery at {minutes} minutes.\n"
                f"Monitor power situation."
            )
        else:
            # Battery OK - send recovery alert if we were in alert state
            if self.last_alert_level in ["warning", "critical"]:
                self.send_slack_alert(
                    f"🟢 RECOVERED: UPS battery now at {minutes} minutes.",
                    "info"
                )
            current_level = None
        
        # Send alert if level changed (avoid spam)
        if current_level and current_level != self.last_alert_level:
            self.send_slack_alert(message, current_level)
        
        self.last_alert_level = current_level
    
    def run(self, interval: int = 60):
        """Run continuous alert monitoring."""
        print(f"Starting UPS alert system (checking every {interval}s)")
        
        try:
            while True:
                self.check_and_alert()
                time.sleep(interval)
        except KeyboardInterrupt:
            print("\nAlert system stopped.")

# Example usage
if __name__ == "__main__":
    alert_system = UPSAlertSystem(
        dashboard_url="http://192.168.1.100:8080",
        slack_webhook_url="https://hooks.slack.com/services/YOUR/WEBHOOK/URL",
        warning_threshold=30,
        critical_threshold=15
    )
    alert_system.run(interval=30)
```

---

## Use Case 7: Bulk Configuration from File

### Scenario
You want to configure multiple clients from a YAML or JSON configuration file.

### Configuration File (YAML)

```yaml
# ups_config.yaml
ups:
  url: "https://192.168.1.50/json/live_data.json"
  minimum_minutes: 20

clients:
  # Development tier - shutdown first
  - hostname: dev-server-01
    delay: 0
  - hostname: test-vm-01
    delay: 0
  
  # Application tier
  - hostname: web-server-01
    delay: 30
  - hostname: web-server-02
    delay: 30
  - hostname: app-server-01
    delay: 30
  
  # Data tier - shutdown last
  - hostname: db-replica-01
    delay: 60
  - hostname: db-primary-01
    delay: 90
```

### Implementation (Python)

```python
import yaml
import requests

def load_config(config_file: str) -> dict:
    """Load configuration from YAML file."""
    with open(config_file, 'r') as f:
        return yaml.safe_load(f)

def apply_config(config: dict, dashboard_url: str = "http://localhost:8080"):
    """Apply configuration to UPS system."""
    
    # Update UPS configuration
    ups_config = config.get('ups', {})
    
    if 'url' in ups_config:
        print(f"Setting UPS URL: {ups_config['url']}")
        requests.post(
            f"{dashboard_url}/api/update_config",
            json={"key": "UPS_URL", "value": ups_config['url']},
            timeout=5
        )
    
    if 'minimum_minutes' in ups_config:
        print(f"Setting battery threshold: {ups_config['minimum_minutes']} minutes")
        requests.post(
            f"{dashboard_url}/api/update_config",
            json={"key": "UPS_minimum_minutes", "value": str(ups_config['minimum_minutes'])},
            timeout=5
        )
    
    # Update client shutdown delays
    clients = config.get('clients', [])
    
    for client in clients:
        hostname = client.get('hostname')
        delay = client.get('delay', 0)
        
        if hostname:
            print(f"Setting {hostname} delay: {delay}s")
            response = requests.post(
                f"{dashboard_url}/api/update_shutdown",
                json={"hostname": hostname, "seconds": delay},
                timeout=5
            )
            
            result = response.json()
            if not result.get('success'):
                print(f"  Warning: {result.get('error', 'Unknown error')}")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Apply UPS configuration from file')
    parser.add_argument('config_file', help='Path to YAML configuration file')
    parser.add_argument('--url', default='http://localhost:8080', 
                        help='Dashboard URL')
    
    args = parser.parse_args()
    
    config = load_config(args.config_file)
    apply_config(config, args.url)
    print("Configuration applied successfully!")

if __name__ == "__main__":
    main()
```

### Usage

```bash
python apply_config.py ups_config.yaml --url http://192.168.1.100:8080
```

---

## Use Case 8: Health Check Script

### Scenario
You want a simple health check script for monitoring systems (Nagios, Prometheus, etc.).

### Implementation (Python)

```python
#!/usr/bin/env python3
"""
UPS Health Check Script
Exit codes:
  0 = OK
  1 = WARNING
  2 = CRITICAL
  3 = UNKNOWN
"""

import sys
import requests

def check_ups_health(dashboard_url: str, warn: int = 30, crit: int = 15) -> tuple:
    """
    Check UPS health status.
    
    Returns:
        Tuple of (exit_code, message)
    """
    try:
        # Check UPS status
        response = requests.get(f"{dashboard_url}/api/ups_status", timeout=5)
        response.raise_for_status()
        ups_data = response.json()
        
        if ups_data.get("status") != "ok":
            return 3, "UNKNOWN - Unable to fetch UPS status"
        
        minutes = ups_data["total_minutes"]
        
        # Check clients
        response = requests.get(f"{dashboard_url}/api/clients", timeout=5)
        response.raise_for_status()
        clients = response.json().get("clients", [])
        client_count = len(clients)
        
        # Determine status
        if minutes <= crit:
            return 2, f"CRITICAL - Battery: {minutes}min, Clients: {client_count}"
        elif minutes <= warn:
            return 1, f"WARNING - Battery: {minutes}min, Clients: {client_count}"
        else:
            return 0, f"OK - Battery: {minutes}min, Clients: {client_count}"
            
    except requests.Timeout:
        return 2, "CRITICAL - Dashboard timeout"
    except requests.RequestException as e:
        return 2, f"CRITICAL - Connection error: {e}"
    except Exception as e:
        return 3, f"UNKNOWN - {e}"

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='UPS Health Check')
    parser.add_argument('--url', default='http://localhost:8080',
                        help='Dashboard URL')
    parser.add_argument('--warning', type=int, default=30,
                        help='Warning threshold (minutes)')
    parser.add_argument('--critical', type=int, default=15,
                        help='Critical threshold (minutes)')
    
    args = parser.parse_args()
    
    exit_code, message = check_ups_health(args.url, args.warning, args.critical)
    print(message)
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
```

### Usage

```bash
# Basic check
./health_check.py --url http://192.168.1.100:8080

# Custom thresholds
./health_check.py --url http://192.168.1.100:8080 --warning 45 --critical 20

# Nagios/Icinga integration
check_ups!http://192.168.1.100:8080!30!15
```

---

## Summary

| Use Case | API Endpoints Used |
|----------|-------------------|
| Monitor battery status | `GET /api/ups_status` |
| List connected clients | `GET /api/clients` |
| Update shutdown priority | `POST /api/update_shutdown` |
| Update UPS configuration | `POST /api/update_config` |
| Build monitoring dashboard | All GET endpoints |
| Integrate with alert systems | `GET /api/ups_status` |
| Bulk configuration | All POST endpoints |
| Health checks | `GET /api/ups_status`, `GET /api/clients` |

---

[← Back to Getting Started](getting-started.md) | [Back to Documentation Index →](../README.md)
