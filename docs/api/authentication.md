# Authentication

This document describes the authentication and authorization mechanisms in the Riello UPS Servers Shutdown system.

## Current Implementation

**The system does not implement authentication or authorization.**

All components operate without credential verification:

| Component | Authentication | Authorization |
|-----------|---------------|---------------|
| UPS Dashboard | None | None |
| Server-Client TCP | None | None |
| Server-Client UDP | None | None |

## Security Implications

### Dashboard Access

- Anyone with network access to port 8080 can:
  - View all connected clients
  - View UPS configuration
  - Modify client shutdown delays
  - Modify UPS URL and battery threshold

### Server-Client Communication

- Any device on the network can:
  - Send discovery broadcasts
  - Connect to the server as a client
  - Receive UPS status updates
  - Receive shutdown commands

### UPS API Access

- The server connects to the UPS JSON API over HTTPS
- SSL certificate verification is disabled (`verify_mode = ssl.CERT_NONE`)
- This allows connection to UPS devices with self-signed certificates

## Design Rationale

The system is designed for **trusted internal networks** where:

1. All machines are under the same administrative control
2. Network access is restricted by firewall/VLAN
3. Physical security is maintained

## Recommended Network Security

Since the system lacks built-in authentication, implement security at the network level:

### Firewall Rules

```bash
# Allow UDP discovery only from local network
iptables -A INPUT -p udp --dport 5225 -s 192.168.1.0/24 -j ACCEPT
iptables -A INPUT -p udp --dport 5225 -j DROP

# Allow TCP connections only from local network
iptables -A INPUT -p tcp --dport 5226 -s 192.168.1.0/24 -j ACCEPT
iptables -A INPUT -p tcp --dport 5226 -j DROP

# Allow dashboard only from admin subnet
iptables -A INPUT -p tcp --dport 8080 -s 192.168.1.0/24 -j ACCEPT
iptables -A INPUT -p tcp --dport 8080 -j DROP
```

### VLAN Isolation

Consider placing all UPS-monitored machines on a dedicated VLAN:

```
┌─────────────────────────────────────────────────────┐
│                  Management VLAN                     │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐             │
│  │ Admin   │  │ UPS     │  │ Server  │             │
│  │ Browser │  │ Device  │  │         │             │
│  └─────────┘  └─────────┘  └─────────┘             │
│                                                      │
│  Ports: 8080 (dashboard), 5225-5226 (UPS system)   │
└─────────────────────────────────────────────────────┘
                        │
                   [Firewall]
                        │
┌─────────────────────────────────────────────────────┐
│                  Server VLAN                         │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐             │
│  │ Client 1│  │ Client 2│  │ Client N│             │
│  └─────────┘  └─────────┘  └─────────┘             │
│                                                      │
│  Outbound: 5225 UDP, 5226 TCP to Management VLAN   │
└─────────────────────────────────────────────────────┘
```

### Reverse Proxy with Authentication

For dashboard access control, use a reverse proxy:

**Nginx Example with Basic Auth:**

```nginx
server {
    listen 443 ssl;
    server_name ups-dashboard.example.com;
    
    ssl_certificate /etc/ssl/certs/ups-dashboard.crt;
    ssl_certificate_key /etc/ssl/private/ups-dashboard.key;
    
    auth_basic "UPS Dashboard";
    auth_basic_user_file /etc/nginx/.htpasswd;
    
    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

Create password file:
```bash
htpasswd -c /etc/nginx/.htpasswd admin
```

## Service Account Permissions

All services run as root for shutdown capability:

```ini
# UPSserver.service
[Service]
User=root
Group=root

# UPSdashboard.service
[Service]
User=root
Group=root

# UPSclient.service
[Service]
User=root
Group=root
```

### Permission Breakdown

| Permission | Required For | Component |
|------------|--------------|-----------|
| Root | System shutdown | Server, Client |
| Root | Database in /opt | Server, Dashboard |
| Network | Binding to ports < 1024 | Not required (ports > 1024) |

## SSH Key Authentication (Server-Specific)

The server includes optional SSH-based shutdown for pfSense firewall:

```python
subprocess.run([
    'ssh', 
    '-i', '/root/.ssh/pfsense_id_rsa', 
    'admin@192.168.155.1', 
    '/sbin/shutdown -p now'
], check=True)
```

This requires:
1. SSH key at `/root/.ssh/pfsense_id_rsa`
2. Public key in pfSense authorized_keys
3. Network connectivity to pfSense

## Security Best Practices

### For Production Deployment

1. **Network Isolation**: Keep UPS system on isolated VLAN
2. **Firewall Rules**: Restrict port access to known machines
3. **Reverse Proxy**: Add authentication for dashboard
4. **Monitoring**: Log and alert on unexpected connections
5. **Physical Security**: Protect server and network infrastructure

### For Development/Testing

1. Use VMs or containers for isolation
2. Run on localhost-only network
3. Don't expose ports to external networks

---

[← Back to Endpoints](endpoints.md) | [Next: Error Handling →](error-handling.md)
