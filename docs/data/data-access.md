# Data Access Patterns

This document describes the data access patterns and database operations used in the Riello UPS Servers Shutdown system.

## Overview

The system uses SQLite for data persistence with direct SQL queries. There is no ORM layer - all database operations use the Python `sqlite3` module directly.

## Connection Management

### Connection Pattern

Each database operation creates a new connection, performs the operation, and closes the connection:

```python
try:
    conn = sqlite3.connect(self.db_path)
    cursor = conn.cursor()
    
    # Perform operation
    cursor.execute(...)
    
    conn.commit()  # For write operations
    conn.close()
except Exception as e:
    logger.error(f"Database error: {e}")
```

### Why This Pattern?

1. **Thread Safety**: Each thread gets its own connection
2. **Simplicity**: No connection pool management needed
3. **Reliability**: Connections don't become stale
4. **SQLite Compatibility**: Works well with SQLite's file-based locking

---

## Data Access by Component

### UPS Server Data Access

#### Initialize Database

**Method**: `UPSServer._init_database()`

**Purpose**: Create tables and default configuration on startup

```python
def _init_database(self):
    try:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS client_connections (...)
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS configuration (...)
        ''')
        
        cursor.execute('''
            INSERT OR IGNORE INTO configuration (key, value)
            VALUES ('UPS_URL', ?)
        ''', (UPS_URL,))
        
        cursor.execute('''
            INSERT OR IGNORE INTO configuration (key, value)
            VALUES ('UPS_minimum_minutes', '15')
        ''')
        
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
```

#### Record Client Connection

**Method**: `UPSServer._record_client_connection(hostname, address)`

**Purpose**: Insert or update client when they connect

```python
def _record_client_connection(self, hostname: str, address: Tuple[str, int]):
    try:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        ip_address, port = address
        current_time = datetime.now().isoformat()
        
        # Check if client exists
        cursor.execute('SELECT hostname FROM client_connections WHERE hostname = ?', (hostname,))
        result = cursor.fetchone()
        
        if result:
            # Update existing record
            cursor.execute('''
                UPDATE client_connections 
                SET ip_address = ?, port = ?, last_connection_time = ?
                WHERE hostname = ?
            ''', (ip_address, port, current_time, hostname))
        else:
            # Insert new record
            cursor.execute('''
                INSERT INTO client_connections (hostname, ip_address, port, last_connection_time)
                VALUES (?, ?, ?, ?)
            ''', (hostname, ip_address, port, current_time))
        
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Failed to record client connection: {e}")
```

#### Update Heartbeat Time

**Method**: `UPSServer._update_heartbeat_time(hostname, address)`

**Purpose**: Update last connection time on each heartbeat

```python
def _update_heartbeat_time(self, hostname: str, address: Tuple[str, int]):
    try:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        ip_address, port = address
        current_time = datetime.now().isoformat()
        
        cursor.execute('''
            UPDATE client_connections 
            SET last_connection_time = ?, ip_address = ?, port = ?
            WHERE hostname = ?
        ''', (current_time, ip_address, port, hostname))
        
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Failed to update heartbeat time: {e}")
```

#### Get Client History

**Method**: `UPSServer.get_client_history(hostname=None)`

**Purpose**: Retrieve client connection records

```python
def get_client_history(self, hostname: str = None):
    try:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if hostname:
            cursor.execute('''
                SELECT hostname, ip_address, port, last_connection_time, seconds_to_shutdown
                FROM client_connections
                WHERE hostname = ?
            ''', (hostname,))
        else:
            cursor.execute('''
                SELECT hostname, ip_address, port, last_connection_time, seconds_to_shutdown
                FROM client_connections
                ORDER BY last_connection_time DESC
            ''')
        
        results = cursor.fetchall()
        conn.close()
        
        return [
            {
                'hostname': row[0],
                'ip_address': row[1],
                'port': row[2],
                'last_connection_time': row[3],
                'seconds_to_shutdown': row[4]
            }
            for row in results
        ]
    except Exception as e:
        logger.error(f"Failed to get client history: {e}")
        return []
```

#### Get Configuration Value

**Method**: `UPSServer.get_config_value(key, default=None)`

**Purpose**: Read a configuration setting

```python
def get_config_value(self, key: str, default: str = None) -> str:
    try:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT value FROM configuration WHERE key = ?', (key,))
        result = cursor.fetchone()
        
        conn.close()
        
        return result[0] if result else default
    except Exception as e:
        logger.error(f"Failed to get config value for {key}: {e}")
        return default
```

#### Set Configuration Value

**Method**: `UPSServer.set_config_value(key, value)`

**Purpose**: Update a configuration setting

```python
def set_config_value(self, key: str, value: str):
    try:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO configuration (key, value)
            VALUES (?, ?)
        ''', (key, value))
        
        conn.commit()
        conn.close()
        logger.info(f"Configuration updated: {key} = {value}")
    except Exception as e:
        logger.error(f"Failed to set config value for {key}: {e}")
```

---

### Dashboard Data Access

#### Get Database Connection

**Function**: `get_db_connection()`

**Purpose**: Helper to create database connections

```python
DB_PATH = 'ups_clients.db'

def get_db_connection():
    """Create a database connection."""
    return sqlite3.connect(DB_PATH)
```

#### Load Client Connections

**Function**: `load_client_connections()`

**Purpose**: Retrieve all clients with formatted timestamps

```python
def load_client_connections():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT hostname, ip_address, port, last_connection_time, seconds_to_shutdown
            FROM client_connections
            ORDER BY last_connection_time DESC
        """)
        columns = [description[0] for description in cursor.description]
        rows = cursor.fetchall()
        conn.close()
        
        clients = []
        for row in rows:
            client_dict = dict(zip(columns, row))
            if client_dict.get('last_connection_time'):
                try:
                    dt_object = datetime.fromisoformat(client_dict['last_connection_time'])
                    client_dict['last_connection_time'] = dt_object.strftime('%Y-%m-%d %H:%M')
                except (ValueError, TypeError):
                    pass
            clients.append(client_dict)
        return clients
    except Exception as e:
        print(f"Error loading client connections: {e}")
        return []
```

#### Load Configuration

**Function**: `load_configuration()`

**Purpose**: Retrieve all configuration values

```python
def load_configuration():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT key, value FROM configuration ORDER BY key")
        columns = [description[0] for description in cursor.description]
        rows = cursor.fetchall()
        conn.close()
        return [dict(zip(columns, row)) for row in rows]
    except Exception as e:
        print(f"Error loading configuration: {e}")
        return []
```

#### Update Configuration Value

**Function**: `update_config_value(key, value)`

**Purpose**: Update or insert a configuration value

```python
def update_config_value(key: str, value: str):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO configuration (key, value)
            VALUES (?, ?)
        ''', (key, value))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error updating configuration: {e}")
        return False
```

#### Update Client Shutdown Time

**Function**: `update_client_shutdown_time(hostname, seconds)`

**Purpose**: Update a client's shutdown delay

```python
def update_client_shutdown_time(hostname: str, seconds: int):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE client_connections
            SET seconds_to_shutdown = ?
            WHERE hostname = ?
        ''', (seconds, hostname))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error updating shutdown time: {e}")
        return False
```

---

## Data Access Patterns Summary

| Pattern | Usage | Example |
|---------|-------|---------|
| Create on First Use | Tables and default config | `_init_database()` |
| Upsert | Client connections | `INSERT OR REPLACE` / Check then Update |
| Read All | Client list, config list | `SELECT ... ORDER BY` |
| Read One | Single config value | `SELECT ... WHERE key = ?` |
| Update | Heartbeat time, shutdown delay | `UPDATE ... WHERE` |

---

## Error Handling Pattern

All data access follows this error handling pattern:

```python
def data_operation():
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Perform operation
        
        conn.commit()  # If writing
        conn.close()
        return result  # Or True for success
    except Exception as e:
        logger.error(f"Error description: {e}")
        return default_value  # Or False for failure
```

---

## Concurrency Considerations

### Read Operations
- Multiple concurrent reads are safe
- SQLite handles read locking automatically

### Write Operations
- SQLite uses file-level locking
- Concurrent writes are serialized
- Short transactions minimize contention

### Best Practices Used
1. Keep transactions short
2. Close connections promptly
3. Handle exceptions gracefully
4. Use parameterized queries (prevents SQL injection)

---

[← Back to Database Schema](database-schema.md) | [Next: Getting Started →](../guides/getting-started.md)
