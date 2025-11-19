# Riello UPS shutdown
pip3 install streamlit --break-system-packages

## Server 
The server components must be deployed in the last machine to be shutdown.

### Prerequisites

#### Install Python Dependencies

```bash
# Install system-wide Python packages (required for Selenium and Streamlit)
sudo pip3 install streamlit selenium pandas --break-system-packages
```

#### Install Google Chrome and ChromeDriver

The UPS server uses Selenium with Chrome in headless mode to monitor the UPS web interface. This requires Google Chrome and ChromeDriver to be installed.

**Automated Installation (Recommended):**

```bash
sudo python3 install_chrome.py
```

The script will:
- Remove snap Chromium if installed
- Install Google Chrome
- Detect Chrome version
- Install matching ChromeDriver
- Test Chrome headless mode
- Test Selenium integration

### Install the UPSserver as a service

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

The UPS server service **must run as root** for two critical reasons:
1. It needs to execute system shutdown commands when UPS battery is critical
2. Chrome/Selenium requires `--no-sandbox` flag in systemd service environments, which only works reliably as root

The service file (UPSserver.service) is already configured to run as root. If you need a more secure setup with a dedicated user, see the "Security Considerations" section below.

### Setup log rotation
```bash
# Logrotate configuration already copied in previous step
# Test logrotate configuration
sudo logrotate -d /etc/logrotate.d/UPSserver

# Force rotation (optional, for testing)
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
# View log files directly
tail -f /var/log/UPSserver.log
tail -f /var/log/UPSserver_error.log

# View recent logs
tail -n 50 /var/log/UPSserver.log

# View logs via journalctl
sudo journalctl -u UPSserver.service -f

# View recent logs via journalctl
sudo journalctl -u UPSserver.service -n 50

# Stop the service
sudo systemctl stop UPSserver.service

# Restart the service
sudo systemctl restart UPSserver.service
```

### Security Considerations

**Why the service runs as root:**
1. **System Shutdown Capability**: The server must execute `shutdown -h now` when UPS battery is critical. Only root can execute these commands.
2. **Chrome with --no-sandbox**: In systemd service environments without X11 display, Chrome requires the `--no-sandbox` flag, which only works reliably as root.

### Useful commands
```bash
# Stop the service
sudo systemctl stop UPSserver.service

# Restart the service
sudo systemctl restart UPSserver.service

# View logs
sudo journalctl -u UPSserver.service -f

# View recent logs
sudo journalctl -u UPSserver.service -n 50

# Check service status
sudo systemctl status UPSserver.service

# Disable service (don't start on boot)
sudo systemctl disable UPSserver.service

# Re-enable service
sudo systemctl enable UPSserver.service
```

### Install the UPSdashboard as a service
```bash
# Create log files
sudo touch /var/log/UPSdashboard.log /var/log/UPSdashboard_error.log
sudo chmod 644 /var/log/UPSdashboard.log /var/log/UPSdashboard_error.log
sudo cp UPSdashboard.py /opt/UPSserver/
sudo nano /etc/systemd/system/UPSdashboard.service
```
```bash
[Unit]
Description=Python UPSdashboard Service (Streamlit)
After=network.target

[Service]
Type=simple
# Run as root for consistency with UPSserver
User=root
Group=root
WorkingDirectory=/opt/UPSserver
ExecStart=/usr/bin/python3 -m streamlit run /opt/UPSserver/UPSdashboard.py --server.port=8501 --server.address=0.0.0.0
Restart=always
RestartSec=30

# Optional: set environment variables if needed
# Environment="PYTHONUNBUFFERED=1"

# Optional: logging
StandardOutput=append:/var/log/UPSdashboard.log
StandardError=append:/var/log/UPSdashboard_error.log

[Install]
WantedBy=multi-user.target
```

### Setup log rotation
```bash
# Copy logrotate configuration
sudo cp UPSdashboard.logrotate /etc/logrotate.d/UPSdashboard

# Test logrotate configuration
sudo logrotate -d /etc/logrotate.d/UPSdashboard

# Force rotation (optional, for testing)
sudo logrotate -f /etc/logrotate.d/UPSdashboard
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
sudo journalctl -u UPSdashboard.service -f

# View recent logs
sudo journalctl -u UPSdashboard.service -n 50

# Access the dashboard
# Open your browser and navigate to: http://your-server-ip:8501
```

## Client
To be installed on all machines that should be shutdown when UPS battery is bellow a threshold configured in the UPSdashboard.

### Install the UPSclient as a service
```bash
sudo mkdir -p /opt/UPSclient
sudo cp UPSclient.py /opt/UPSclient/

# Create log files
sudo touch /var/log/UPSclient.log /var/log/UPSclient_error.log
sudo chmod 644 /var/log/UPSclient.log /var/log/UPSclient_error.log

sudo nano /etc/systemd/system/UPSclient.service
```
```bash
[Unit]
Description=Python UPSclient Service
After=network.target

[Service]
Type=simple
# Run as root to ensure shutdown permissions
User=root
Group=root
WorkingDirectory=/opt/UPSclient
ExecStart=/usr/bin/python3 /opt/UPSclient/UPSclient.py
Restart=always
RestartSec=30

# Optional: set environment variables if needed
# Environment="PYTHONUNBUFFERED=1"

# Optional: logging
StandardOutput=append:/var/log/UPSclient.log
StandardError=append:/var/log/UPSclient_error.log

[Install]
WantedBy=multi-user.target
```
### Setup log rotation
```bash
# Copy logrotate configuration
sudo cp UPSclient.logrotate /etc/logrotate.d/UPSclient

# Test logrotate configuration
sudo logrotate -d /etc/logrotate.d/UPSclient

# Force rotation (optional, for testing)
sudo logrotate -f /etc/logrotate.d/UPSclient
```

### Enable and start the service
```bash
# Reload systemd to recognize the new service
sudo systemctl daemon-reload

# Enable the service to start on boot
sudo systemctl enable UPSclient.service

# Start the service now
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
sudo journalctl -u UPSclient.service -f

# View recent logs
sudo journalctl -u UPSclient.service -n 50
```
