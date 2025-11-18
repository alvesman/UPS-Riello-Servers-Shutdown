



# install the UPSclient as a service
```bash
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
# Enable and start the service
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

# Useful commands
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