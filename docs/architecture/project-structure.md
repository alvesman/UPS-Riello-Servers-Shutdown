# Project Structure

This document describes the organization of the Riello UPS Servers Shutdown repository.

## Directory Layout

```
UPS-Riello-Servers-Shutdown/
│
├── README.md                    # Main project documentation
├── LICENSE                      # Project license
│
├── server/                      # Server-side components
│   ├── UPSserver.py            # Main UPS monitoring server (776 lines)
│   ├── UPSserver.service       # Systemd service file for server
│   ├── UPSserver.logrotate     # Log rotation configuration
│   │
│   ├── UPSdashboard.py         # Web dashboard interface (974 lines)
│   ├── UPSdashboard.service    # Systemd service file for dashboard
│   ├── UPSdashboard.logrotate  # Dashboard log rotation
│   │
│   └── __pycache__/            # Python bytecode cache (generated)
│
├── client/                      # Client-side components
│   ├── UPSclient.py            # Client application (399 lines)
│   ├── UPSclient.service       # Systemd service file for client
│   └── UPSclient.logrotate     # Client log rotation configuration
│
└── docs/                        # Documentation (this folder)
    ├── README.md               # Documentation index
    ├── architecture/           # Architecture documentation
    ├── domain/                 # Domain model documentation
    ├── api/                    # API documentation
    ├── services/               # Service documentation
    ├── data/                   # Data layer documentation
    ├── guides/                 # User guides
    └── webdocs/                # Static HTML documentation website
```

## File Descriptions

### Server Components (`server/`)

#### UPSserver.py
The core server application responsible for:
- Monitoring the Riello UPS via HTTPS JSON API
- Managing client connections via UDP discovery and TCP
- Storing client data and configuration in SQLite
- Coordinating shutdown sequences

**Key Classes:**
- `ClientConnection` - Represents a connected client
- `ReadUPSMinutes` - Extracts battery autonomy from UPS API
- `UPSServer` - Main server class with all coordination logic

#### UPSdashboard.py
A self-contained web dashboard providing:
- Real-time client monitoring
- UPS configuration management
- Per-client shutdown delay settings
- Auto-refreshing interface

**Key Classes:**
- `DashboardHandler` - HTTP request handler extending `BaseHTTPRequestHandler`

**Key Functions:**
- `load_client_connections()` - Retrieves client data from database
- `load_configuration()` - Retrieves configuration values
- `get_ups_status()` - Fetches current UPS battery status

#### Service Files
| File | Purpose |
|------|---------|
| `UPSserver.service` | Systemd unit file for UPS server daemon |
| `UPSdashboard.service` | Systemd unit file for web dashboard |

#### Log Rotation Files
| File | Purpose |
|------|---------|
| `UPSserver.logrotate` | Daily rotation, 7-day retention, 10MB max |
| `UPSdashboard.logrotate` | Dashboard log rotation configuration |

### Client Components (`client/`)

#### UPSclient.py
The client application deployed on each machine:
- Discovers server via UDP broadcast
- Maintains persistent TCP connection
- Receives and executes shutdown commands

**Key Classes:**
- `UPSClient` - Main client class handling discovery, connection, and shutdown

#### Service Files
| File | Purpose |
|------|---------|
| `UPSclient.service` | Systemd unit file for client daemon |
| `UPSclient.logrotate` | Client log rotation configuration |

## Installation Paths

### Server Installation
```
/opt/UPSserver/
├── UPSserver.py
├── UPSdashboard.py
└── ups_clients.db          # Created at runtime
```

### Client Installation
```
/opt/UPSclient/
└── UPSclient.py
```

### Service Files
```
/etc/systemd/system/
├── UPSserver.service
├── UPSdashboard.service
└── UPSclient.service
```

### Log Files
```
/var/log/
├── UPSserver.log
├── UPSserver_error.log
├── UPSdashboard.log
├── UPSdashboard_error.log
├── UPSclient.log
└── UPSclient_error.log
```

### Log Rotation Configuration
```
/etc/logrotate.d/
├── UPSserver
├── UPSdashboard
└── UPSclient
```

## Code Metrics

| Component | Lines of Code | Classes | Functions |
|-----------|---------------|---------|-----------|
| UPSserver.py | 776 | 3 | 20+ |
| UPSdashboard.py | 974 | 1 | 10+ |
| UPSclient.py | 399 | 1 | 10+ |
| **Total** | **2,149** | **5** | **40+** |

## Runtime Artifacts

The following files are created during operation:

| File | Location | Purpose |
|------|----------|---------|
| `ups_clients.db` | `/opt/UPSserver/` | SQLite database with clients and configuration |
| `*.log` | `/var/log/` | Application logs (stdout) |
| `*_error.log` | `/var/log/` | Error logs (stderr) |

---

[← Back to Overview](overview.md) | [Next: Dependencies →](dependencies.md)
