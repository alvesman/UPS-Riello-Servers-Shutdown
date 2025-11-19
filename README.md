# Riello UPS shutdown
# Server 
**The server components must be deployed in the last machine to be shutdown!**

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

The UPS server service **must run as root** because it needs to execute system shutdown commands when UPS battery is critical.

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
tail -f /var/log/UPSserver.log -n 50
tail -f /var/log/UPSserver_error.log -n 50
```

### Security Considerations

The dashboard does not provide authentication at his moment.

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
tail -f /var/log/UPSdashboard.log -n 50
tail -f /var/log/UPSdashboard_error.log -n 50
```
### Access the dashboard
Open your browser and navigate to:
```bash
http://your-server-ip:8501
```
# Client
To be installed on all machines that should be shutdown when UPS battery is bellow a threshold configured in the UPSdashboard.

### Install the UPSclient as a service
```bash
sudo mkdir -p /opt/UPSclient
sudo cp UPSclient.py /opt/UPSclient/
sudo cp UPSclient.service /etc/systemd/system/
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
tail /var/log/UPSclient.log -n 50 -f
tail /var/log/UPSclient.log -n 50
tail /var/log/UPSclient_error.log -n 50
```


sudo visudo
dtx ALL=(ALL) NOPASSWD: /sbin/shutdown, /bin/systemctl poweroff
