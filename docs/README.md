# Riello UPS Servers Shutdown - Documentation

Welcome to the comprehensive documentation for the **Riello UPS Servers Shutdown** system - a distributed UPS monitoring and automated shutdown solution designed for Riello UPS units.

## Quick Navigation

### Architecture
- [System Overview](architecture/overview.md) - High-level architecture and component interactions
- [Project Structure](architecture/project-structure.md) - Repository organization and file layout
- [Dependencies](architecture/dependencies.md) - External libraries and system requirements

### Domain Model
- [Entities](domain/entities.md) - Core data structures and classes
- [Relationships](domain/relationships.md) - Component interactions and data flow
- [Business Rules](domain/business-rules.md) - System constraints and operational logic

### API Reference
- [Endpoints](api/endpoints.md) - Dashboard HTTP API documentation
- [Authentication](api/authentication.md) - Security considerations
- [Error Handling](api/error-handling.md) - Error responses and status codes

### Services
- [Service Reference](services/service-reference.md) - All services and their responsibilities

### Data Layer
- [Database Schema](data/database-schema.md) - SQLite database structure
- [Data Access](data/data-access.md) - Database operations and patterns

### Guides
- [Getting Started](guides/getting-started.md) - Setup and configuration instructions
- [Use Cases](guides/use-cases.md) - Common workflows with code examples

---

## System Overview

The Riello UPS Servers Shutdown system is a Python-based distributed solution that:

1. **Monitors** a Riello UPS device via its HTTPS JSON API
2. **Tracks** connected client machines through UDP discovery and TCP connections
3. **Coordinates** graceful shutdowns when battery levels reach critical thresholds
4. **Provides** a web-based dashboard for monitoring and configuration

```
┌─────────────────┐     HTTPS/JSON      ┌─────────────────┐
│   Riello UPS    │◄───────────────────►│   UPS Server    │
│   (Hardware)    │                     │  (UPSserver.py) │
└─────────────────┘                     └────────┬────────┘
                                                 │
                           ┌─────────────────────┼─────────────────────┐
                           │                     │                     │
                    ┌──────▼──────┐       ┌──────▼──────┐       ┌──────▼──────┐
                    │ UPS Client  │       │ UPS Client  │       │ UPS Client  │
                    │  Machine 1  │       │  Machine 2  │       │  Machine N  │
                    └─────────────┘       └─────────────┘       └─────────────┘
```

## Key Features

- **Priority-based shutdown**: Custom delays per client for controlled shutdown sequences
- **Automatic discovery**: UDP broadcast-based server discovery eliminates manual IP configuration
- **Resilient connections**: Heartbeat monitoring with automatic reconnection
- **Web dashboard**: Real-time monitoring and configuration interface
- **Cross-platform support**: Works on Linux, macOS, and Windows
- **Systemd integration**: Production-ready service files and log rotation

## Quick Start

### Server Deployment

```bash
# Create installation directory
sudo mkdir -p /opt/UPSserver

# Copy server files
sudo cp server/UPSserver.py /opt/UPSserver/
sudo cp server/UPSdashboard.py /opt/UPSserver/
sudo cp server/UPSserver.service /etc/systemd/system/
sudo cp server/UPSdashboard.service /etc/systemd/system/

# Enable and start services
sudo systemctl daemon-reload
sudo systemctl enable --now UPSserver.service
sudo systemctl enable --now UPSdashboard.service
```

### Client Deployment

```bash
# Create installation directory
sudo mkdir -p /opt/UPSclient

# Copy client files
sudo cp client/UPSclient.py /opt/UPSclient/
sudo cp client/UPSclient.service /etc/systemd/system/

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable --now UPSclient.service
```

## Documentation Formats

This documentation is available in two formats:

1. **Markdown** - Located in the `docs/` directory
2. **Static HTML Website** - Located in `docs/webdocs/` - Open `index.html` in your browser

---

*Documentation generated for Riello UPS Servers Shutdown System*
