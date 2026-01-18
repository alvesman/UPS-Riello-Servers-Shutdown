# Entity Relationships

This document describes how the various components and entities in the Riello UPS Servers Shutdown system interact with each other.

## Component Relationship Diagram

```mermaid
graph TB
    subgraph "External Systems"
        UPS[Riello UPS<br/>Hardware]
        BROWSER[Admin Browser]
    end
    
    subgraph "Server Layer"
        SERVER[UPSServer]
        DASHBOARD[DashboardHandler]
        DB[(SQLite Database)]
    end
    
    subgraph "Client Layer"
        CLIENT1[UPSClient 1]
        CLIENT2[UPSClient 2]
        CLIENTN[UPSClient N]
    end
    
    UPS -->|HTTPS JSON| SERVER
    SERVER <-->|Read/Write| DB
    DASHBOARD <-->|Read/Write| DB
    BROWSER <-->|HTTP| DASHBOARD
    
    SERVER <-->|UDP Discovery| CLIENT1
    SERVER <-->|UDP Discovery| CLIENT2
    SERVER <-->|UDP Discovery| CLIENTN
    
    SERVER <-->|TCP Connection| CLIENT1
    SERVER <-->|TCP Connection| CLIENT2
    SERVER <-->|TCP Connection| CLIENTN
```

## Data Flow Relationships

### 1. UPS → Server Relationship

```mermaid
sequenceDiagram
    participant UPS as Riello UPS
    participant Monitor as UPS Monitor Thread
    participant Server as UPSServer
    
    loop Every 60 seconds
        Monitor->>UPS: GET /json/live_data.json
        UPS-->>Monitor: {"autonomy": N}
        Monitor->>Server: Update battery status
        
        alt Battery > Threshold
            Server->>Server: Broadcast ups_status to clients
        else Battery ≤ Threshold
            Server->>Server: Send shutdown to all clients
            Server->>Server: Schedule self-shutdown
        end
    end
```

### 2. Server ↔ Client Relationship

```mermaid
sequenceDiagram
    participant Client as UPSClient
    participant UDP as UDP Listener
    participant TCP as TCP Server
    participant Handler as Client Handler
    
    Note over Client,Handler: Discovery Phase
    Client->>UDP: UPS_DISCOVER (broadcast)
    UDP-->>Client: {tcp_port, server_ip}
    
    Note over Client,Handler: Connection Phase
    Client->>TCP: TCP Connect
    TCP->>Handler: New connection
    Client->>Handler: {hostname, timestamp}
    Handler-->>Client: {status: connected}
    
    Note over Client,Handler: Maintenance Phase
    loop Every 30-60 seconds
        Client->>Handler: {type: heartbeat}
        Handler-->>Client: {type: heartbeat_ack}
    end
    
    Note over Client,Handler: Status Updates
    Handler->>Client: {type: ups_status, total_minutes: N}
    
    Note over Client,Handler: Shutdown Phase
    Handler->>Client: {type: shutdown, seconds_to_shutdown: N}
    Client->>Client: Execute shutdown after delay
```

### 3. Dashboard ↔ Database Relationship

```mermaid
sequenceDiagram
    participant Browser as Admin Browser
    participant Dashboard as DashboardHandler
    participant DB as SQLite Database
    
    Note over Browser,DB: Read Operations
    Browser->>Dashboard: GET /api/clients
    Dashboard->>DB: SELECT * FROM client_connections
    DB-->>Dashboard: Client records
    Dashboard-->>Browser: JSON response
    
    Browser->>Dashboard: GET /api/config
    Dashboard->>DB: SELECT * FROM configuration
    DB-->>Dashboard: Config records
    Dashboard-->>Browser: JSON response
    
    Note over Browser,DB: Write Operations
    Browser->>Dashboard: POST /api/update_shutdown
    Dashboard->>DB: UPDATE client_connections SET seconds_to_shutdown
    DB-->>Dashboard: Success
    Dashboard-->>Browser: {success: true}
    
    Browser->>Dashboard: POST /api/update_config
    Dashboard->>DB: INSERT OR REPLACE INTO configuration
    DB-->>Dashboard: Success
    Dashboard-->>Browser: {success: true}
```

## Entity Cardinality

```
┌─────────────────┐     1:N     ┌─────────────────┐
│   UPSServer     │────────────►│ ClientConnection│
└─────────────────┘             └─────────────────┘

┌─────────────────┐     1:1     ┌─────────────────┐
│   UPSServer     │────────────►│ SQLite Database │
└─────────────────┘             └─────────────────┘

┌─────────────────┐     1:1     ┌─────────────────┐
│   UPSClient     │────────────►│   UPSServer     │
└─────────────────┘             └─────────────────┘

┌─────────────────┐     N:1     ┌─────────────────┐
│ DashboardHandler│────────────►│ SQLite Database │
└─────────────────┘             └─────────────────┘
```

## Database Relationships

### Tables and Relationships

```mermaid
erDiagram
    client_connections {
        TEXT hostname PK
        TEXT ip_address
        INTEGER port
        TEXT last_connection_time
        INTEGER seconds_to_shutdown
    }
    
    configuration {
        TEXT key PK
        TEXT value
    }
```

### Entity-to-Table Mapping

| Entity | Table | Relationship |
|--------|-------|--------------|
| `ClientConnection` | `client_connections` | Each connected client has a row |
| UPS URL | `configuration` | Stored with key `UPS_URL` |
| Battery Threshold | `configuration` | Stored with key `UPS_minimum_minutes` |

## Thread Relationships

### Server Thread Hierarchy

```
Main Thread
├── UDP Listener Thread
│   └── Handles discovery broadcasts
├── TCP Server Thread
│   └── Client Handler Thread (per client)
│       └── Handles messages for one client
├── Client Monitor Thread
│   └── Checks heartbeat timeouts
└── UPS Monitor Thread
    └── Polls UPS and broadcasts status
```

### Client Thread Hierarchy

```
Main Thread
└── Discovery Loop Thread
    ├── Heartbeat Loop Thread (when connected)
    │   └── Sends periodic heartbeats
    └── Message Receiver Thread (when connected)
        └── Processes server messages
```

## State Relationships

### Connection States

```mermaid
stateDiagram-v2
    [*] --> Disconnected: Client starts
    Disconnected --> Discovering: Start discovery
    Discovering --> Connecting: Server found
    Discovering --> Disconnected: Timeout (retry)
    Connecting --> Connected: Success
    Connecting --> Disconnected: Failed
    Connected --> Disconnected: Heartbeat timeout
    Connected --> Disconnected: Server closed
    Connected --> ShuttingDown: Shutdown command
    ShuttingDown --> [*]: System shutdown
```

### Server States

```mermaid
stateDiagram-v2
    [*] --> Starting: Server starts
    Starting --> Running: All threads started
    Running --> Running: Normal operation
    Running --> Shutdown: Battery critical
    Running --> Stopping: Manual stop
    Shutdown --> Stopping: After client notifications
    Stopping --> [*]: Cleanup complete
```

## Message Flow Matrix

| From | To | Message Type | Trigger |
|------|-----|--------------|---------|
| Client | Server | `UPS_DISCOVER` | Discovery broadcast |
| Server | Client | Discovery response | Discovery request received |
| Client | Server | Identification | TCP connection established |
| Server | Client | Welcome | Client identified |
| Client | Server | `heartbeat` | Heartbeat interval |
| Server | Client | `heartbeat_ack` | Heartbeat received |
| Server | Clients | `ups_status` | UPS poll (battery OK) |
| Server | Clients | `shutdown` | Battery critical |

## Dependency Injection Points

The system uses minimal dependency injection, primarily through constructor parameters:

| Class | Injectable Dependency | Default Value |
|-------|----------------------|---------------|
| `UPSServer` | `db_path` | `'ups_clients.db'` |
| `DashboardHandler` | None | Uses global `DB_PATH` |
| `UPSClient` | None | No external dependencies |

---

[← Back to Entities](entities.md) | [Next: Business Rules →](business-rules.md)
