# Riello UPS shutdown
pip3 install streamlit --break-system-packages

## Server 
The server components must be deployed in the last machine to be shutdown.

### Install the UPSserver as a service
```bash
sudo mkdir -p /opt/UPSserver
sudo cp UPSserver.py /opt/UPSserver/
sudo nano /etc/systemd/system/UPSserver.service
```
```bash
[Unit]
Description=Python UPSserver Service
After=network.target

[Service]
Type=simple
User=your-username
WorkingDirectory=/opt/UPSserver
ExecStart=/usr/bin/python3 /opt/UPSserver/UPSserver.py
Restart=always
RestartSec=30

# Optional: set environment variables if needed
# Environment="PYTHONUNBUFFERED=1"

# Optional: logging
StandardOutput=append:/var/log/UPSserver.log
StandardError=append:/var/log/UPSserver_error.log

[Install]
WantedBy=multi-user.target
```
### Setup log rotation
```bash
# Copy logrotate configuration
sudo cp UPSserver.logrotate /etc/logrotate.d/UPSserver

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
```

### Install the UPSdashboard as a service
```bash
sudo cp UPSdashboard.py /opt/UPSserver/
sudo nano /etc/systemd/system/UPSdashboard.service
```
```bash
[Unit]
Description=Python UPSdashboard Service (Streamlit)
After=network.target

[Service]
Type=simple
User=your-username
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
sudo nano /etc/systemd/system/UPSclient.service
```
```bash
[Unit]
Description=Python UPSclient Service
After=network.target

[Service]
Type=simple
User=your-username
WorkingDirectory=/path/to/your/script
ExecStart=/usr/bin/python3 /path/to/your/script/UPSclient.py
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
