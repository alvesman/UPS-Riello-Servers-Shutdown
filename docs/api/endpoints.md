# API Endpoints

This document provides a complete reference for the HTTP API endpoints exposed by the UPS Dashboard (`UPSdashboard.py`).

## Base URL

```
http://<server-ip>:8080
```

Default port is 8080, configurable via command-line argument:
```bash
python3 UPSdashboard.py 9000  # Run on port 9000
```

## Endpoints Overview

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Dashboard HTML page |
| GET | `/index.html` | Dashboard HTML page (alias) |
| GET | `/api/clients` | List all client connections |
| GET | `/api/config` | List all configuration values |
| GET | `/api/ups_status` | Get current UPS battery status |
| POST | `/api/update_shutdown` | Update client shutdown delay |
| POST | `/api/update_config` | Update configuration value |

---

## GET Endpoints

### GET / or /index.html

Returns the main dashboard HTML page.

**Response**: HTML document

**Status Codes**:
| Code | Description |
|------|-------------|
| 200 | Success - HTML page returned |

**Example**:
```bash
curl http://localhost:8080/
```

---

### GET /api/clients

Returns a list of all client connections from the database.

**Response**: JSON

```json
{
    "clients": [
        {
            "hostname": "server-01",
            "ip_address": "192.168.1.101",
            "port": 54321,
            "last_connection_time": "2024-01-15 14:30",
            "seconds_to_shutdown": 0
        },
        {
            "hostname": "server-02",
            "ip_address": "192.168.1.102",
            "port": 54322,
            "last_connection_time": "2024-01-15 14:28",
            "seconds_to_shutdown": 30
        }
    ]
}
```

**Response Fields**:

| Field | Type | Description |
|-------|------|-------------|
| `hostname` | string | Client machine hostname |
| `ip_address` | string | Client IP address |
| `port` | integer | Client connection port |
| `last_connection_time` | string | Formatted datetime (YYYY-MM-DD HH:MM) |
| `seconds_to_shutdown` | integer | Shutdown delay in seconds |

**Status Codes**:
| Code | Description |
|------|-------------|
| 200 | Success |

**Example**:
```bash
curl http://localhost:8080/api/clients
```

---

### GET /api/config

Returns all configuration values from the database.

**Response**: JSON

```json
{
    "config": [
        {
            "key": "UPS_URL",
            "value": "https://192.168.155.55/json/live_data.json"
        },
        {
            "key": "UPS_minimum_minutes",
            "value": "15"
        }
    ]
}
```

**Response Fields**:

| Field | Type | Description |
|-------|------|-------------|
| `key` | string | Configuration key name |
| `value` | string | Configuration value |

**Known Configuration Keys**:

| Key | Description | Default |
|-----|-------------|---------|
| `UPS_URL` | HTTPS URL to UPS JSON API | `https://192.168.155.55/json/live_data.json` |
| `UPS_minimum_minutes` | Battery threshold for shutdown | `15` |

**Status Codes**:
| Code | Description |
|------|-------------|
| 200 | Success |

**Example**:
```bash
curl http://localhost:8080/api/config
```

---

### GET /api/ups_status

Returns the current UPS battery status by querying the UPS directly.

**Response**: JSON (Success)

```json
{
    "total_minutes": 120,
    "status": "ok"
}
```

**Response**: JSON (Error)

```json
{
    "status": "error",
    "message": "Unable to fetch UPS status"
}
```

**Response Fields**:

| Field | Type | Description |
|-------|------|-------------|
| `total_minutes` | integer | Battery autonomy in minutes |
| `status` | string | "ok" or "error" |
| `message` | string | Error description (only on error) |

**Status Codes**:
| Code | Description |
|------|-------------|
| 200 | Success |
| 500 | Unable to fetch UPS status |

**Example**:
```bash
curl http://localhost:8080/api/ups_status
```

---

## POST Endpoints

### POST /api/update_shutdown

Updates the shutdown delay for a specific client.

**Request Body**: JSON

```json
{
    "hostname": "server-01",
    "seconds": 60
}
```

**Request Fields**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `hostname` | string | Yes | Client hostname to update |
| `seconds` | integer | Yes | New shutdown delay in seconds |

**Response**: JSON (Success)

```json
{
    "success": true,
    "message": "Updated server-01 shutdown time to 60 seconds"
}
```

**Response**: JSON (Error)

```json
{
    "success": false,
    "error": "Missing hostname or seconds"
}
```

**Status Codes**:
| Code | Description |
|------|-------------|
| 200 | Success |
| 400 | Missing or invalid parameters |
| 500 | Database error |

**Example**:
```bash
curl -X POST http://localhost:8080/api/update_shutdown \
    -H "Content-Type: application/json" \
    -d '{"hostname": "server-01", "seconds": 60}'
```

---

### POST /api/update_config

Updates a configuration value in the database.

**Request Body**: JSON

```json
{
    "key": "UPS_minimum_minutes",
    "value": "20"
}
```

**Request Fields**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `key` | string | Yes | Configuration key to update |
| `value` | string | Yes | New configuration value |

**Response**: JSON (Success)

```json
{
    "success": true,
    "message": "Updated UPS_minimum_minutes"
}
```

**Response**: JSON (Error)

```json
{
    "success": false,
    "error": "Missing key or value"
}
```

**Status Codes**:
| Code | Description |
|------|-------------|
| 200 | Success |
| 400 | Missing parameters |
| 500 | Database error |

**Example**:
```bash
curl -X POST http://localhost:8080/api/update_config \
    -H "Content-Type: application/json" \
    -d '{"key": "UPS_minimum_minutes", "value": "20"}'
```

---

## Error Responses

### 404 Not Found

Returned when accessing an unknown endpoint.

```json
(No JSON body - standard HTTP 404 page)
```

### 400 Bad Request

Returned when request body is invalid JSON.

```json
(No JSON body - standard HTTP 400 page)
```

### Database Error Page

When the database is not found:

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

## Content Types

### Request Headers

For POST requests:
```
Content-Type: application/json
```

### Response Headers

For API endpoints:
```
Content-Type: application/json
```

For HTML pages:
```
Content-Type: text/html; charset=utf-8
```

---

## Rate Limiting

The dashboard does not implement rate limiting. The web interface auto-refreshes every 30 seconds.

---

## CORS

The dashboard does not implement CORS headers. It is designed for same-origin access only.

---

[← Back to Business Rules](../domain/business-rules.md) | [Next: Authentication →](authentication.md)
