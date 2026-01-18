# Error Handling

This document describes error handling mechanisms, error responses, and status codes used throughout the Riello UPS Servers Shutdown system.

## HTTP API Error Responses

### Dashboard API Errors

#### 400 Bad Request

Returned when request parameters are missing or invalid.

**Scenarios**:
- Missing required fields in POST body
- Invalid JSON in request body
- Invalid data types (e.g., non-numeric seconds)

**Response Format**:
```json
{
    "success": false,
    "error": "Error description"
}
```

**Examples**:

Missing hostname or seconds:
```json
{
    "success": false,
    "error": "Missing hostname or seconds"
}
```

Invalid seconds value:
```json
{
    "success": false,
    "error": "Invalid seconds value"
}
```

Missing key or value:
```json
{
    "success": false,
    "error": "Missing key or value"
}
```

#### 404 Not Found

Returned when accessing an unknown endpoint.

**Response**: Standard HTTP 404 page (no JSON body)

#### 500 Internal Server Error

Returned when server-side operations fail.

**Response Format**:
```json
{
    "success": false,
    "error": "Failed to update database"
}
```

**For UPS Status**:
```json
{
    "status": "error",
    "message": "Unable to fetch UPS status"
}
```

### Database Not Found Error

When the UPS server hasn't created the database yet:

```html
<!DOCTYPE html>
<html>
<head>
    <title>Error - UPS Dashboard</title>
</head>
<body>
    <div class="error-container">
        <h1>⚠️ Database not found</h1>
        <p>Database file 'ups_clients.db' does not exist. 
           Please start the UPS server first.</p>
    </div>
</body>
</html>
```

---

## Server Error Handling

### UPS API Errors

The `ReadUPSMinutes` class handles various UPS API errors:

| Error Type | Handling | Log Level |
|------------|----------|-----------|
| HTTP Error (4xx, 5xx) | Return `None` | ERROR |
| URL Error (connection failed) | Return `None` | ERROR |
| JSON Decode Error | Return `None` | ERROR |
| Missing 'autonomy' field | Return `None` | WARNING |
| Invalid autonomy type | Return `None` | WARNING |
| Unexpected exception | Return `None`, log traceback | ERROR |

**Code Example**:
```python
try:
    with urllib.request.urlopen(request, context=ssl_context, timeout=10) as response:
        data = response.read().decode('utf-8')
        json_data = json.loads(data)
        
        if 'autonomy' not in json_data:
            logger.warning(f"'autonomy' field not found in JSON response")
            return None
        
        return int(json_data['autonomy'])
        
except urllib.error.HTTPError as e:
    logger.error(f"HTTP error accessing UPS: {e.code} {e.reason}")
    return None
except urllib.error.URLError as e:
    logger.error(f"URL error accessing UPS: {str(e.reason)}")
    return None
except json.JSONDecodeError as e:
    logger.error(f"Failed to parse JSON response: {str(e)}")
    return None
```

### Database Errors

Database operations are wrapped in try-except blocks:

```python
try:
    conn = sqlite3.connect(self.db_path)
    cursor = conn.cursor()
    # ... operations ...
    conn.commit()
    conn.close()
except Exception as e:
    logger.error(f"Failed to initialize database: {e}")
```

### Connection Errors

#### Client Connection Handling

| Error | Server Response |
|-------|-----------------|
| No identification received | Close connection, log warning |
| Invalid JSON identification | Close connection, log warning |
| Missing hostname | Close connection, log warning |
| Connection reset | Remove from clients, log info |
| Socket timeout | Continue (expected behavior) |

#### Client Handler Cleanup

```python
finally:
    # Always clean up
    with self.lock:
        if hostname in self.clients and self.clients[hostname].conn == conn:
            del self.clients[hostname]
            logger.info(f"Client {hostname} removed from active connections")
    
    try:
        conn.close()
    except:
        pass
```

---

## Client Error Handling

### Discovery Errors

| Error | Client Response |
|-------|-----------------|
| Socket creation failed | Log error, retry after backoff |
| Broadcast send failed | Log error, retry |
| No server response | Retry after backoff |
| Invalid server response | Log warning, retry |

### Connection Errors

| Error | Client Response |
|-------|-----------------|
| TCP connection failed | Disconnect, retry discovery |
| Socket timeout | Continue (normal) |
| Connection closed by server | Disconnect, retry discovery |
| Invalid JSON from server | Log warning, continue |

### Shutdown Errors

```python
try:
    subprocess.run(['shutdown', '-h', 'now'], check=True)
except subprocess.CalledProcessError as e:
    logger.error(f"Failed to execute shutdown command: {e}")
except Exception as e:
    logger.error(f"Error during shutdown execution: {e}")
```

---

## Logging Levels

The system uses Python's logging module with split handlers:

| Level | Output | Use Case |
|-------|--------|----------|
| DEBUG | stdout | Detailed diagnostic info |
| INFO | stdout | Normal operational messages |
| WARNING | stdout | Unexpected but recoverable issues |
| ERROR | stderr | Errors that don't stop operation |
| CRITICAL | stderr | Shutdown commands and fatal errors |

### Log Format

```
%(asctime)s - %(name)s - %(levelname)s - %(message)s
```

**Example**:
```
2024-01-15 14:30:45,123 - __main__ - INFO - UPS Server started successfully
2024-01-15 14:31:45,456 - __main__ - ERROR - Failed to connect to UPS
```

### Log Routing in Systemd

```ini
StandardOutput=append:/var/log/UPSserver.log
StandardError=append:/var/log/UPSserver_error.log
```

This routes:
- INFO, WARNING → `/var/log/UPSserver.log`
- ERROR, CRITICAL → `/var/log/UPSserver_error.log`

---

## Error Recovery Strategies

### Automatic Recovery

| Component | Strategy | Implementation |
|-----------|----------|----------------|
| Client reconnection | Linear backoff (10-60s) | `_discovery_loop()` |
| Dead client detection | Monitor thread (10s interval) | `_monitor_clients()` |
| UPS polling failure | Log and continue polling | `_ups_monitor()` |
| Service restart | Systemd auto-restart | `Restart=always` |

### Manual Intervention Required

| Scenario | Indicator | Resolution |
|----------|-----------|------------|
| UPS offline | Persistent UPS errors in log | Check UPS network/power |
| Database corruption | SQL errors | Restore from backup or recreate |
| Network partition | Multiple client timeouts | Check network infrastructure |
| Service crash loop | Rapid restarts in journald | Check logs, fix configuration |

---

## Status Codes Summary

### HTTP Status Codes

| Code | Meaning | Dashboard Usage |
|------|---------|-----------------|
| 200 | OK | Successful request |
| 400 | Bad Request | Invalid parameters |
| 404 | Not Found | Unknown endpoint |
| 500 | Internal Server Error | Database/UPS errors |

### Internal Status Values

| Status | Context | Meaning |
|--------|---------|---------|
| `"ok"` | UPS status | Successfully retrieved |
| `"error"` | UPS status | Failed to retrieve |
| `"connected"` | Welcome message | Client accepted |
| `true` | API success | Operation succeeded |
| `false` | API success | Operation failed |

---

## Debugging Errors

### Check Service Status

```bash
# Server status
sudo systemctl status UPSserver.service

# Dashboard status
sudo systemctl status UPSdashboard.service

# Client status
sudo systemctl status UPSclient.service
```

### View Logs

```bash
# Server logs
tail -f /var/log/UPSserver.log
tail -f /var/log/UPSserver_error.log

# Dashboard logs
tail -f /var/log/UPSdashboard.log

# Client logs
tail -f /var/log/UPSclient.log
```

### Common Error Patterns

| Log Pattern | Likely Cause | Solution |
|-------------|--------------|----------|
| "HTTP error accessing UPS: 401" | UPS requires auth | Check UPS credentials |
| "URL error accessing UPS" | Network issue | Check connectivity to UPS |
| "Failed to initialize database" | Permission issue | Check /opt/UPSserver permissions |
| "Client X timed out" | Client network/crash | Check client machine |
| "Failed to execute shutdown" | Permission issue | Verify root privileges |

---

[← Back to Authentication](authentication.md) | [Next: Service Reference →](../services/service-reference.md)
