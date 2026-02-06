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
| GET | `/api/ups_full_status` | Get complete UPS status with all metrics |
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

### GET /api/ups_full_status

Returns complete, detailed UPS status with all available metrics from the live_data.json endpoint. This includes 3-phase input, bypass, output measurements, battery status, environmental data, and system alarms.

**Response**: JSON (Success)

```json
{
    "current_date": "06 Feb 08:27 WET 2026",
    "vin1": 227,
    "vin2": 227,
    "vin3": 228,
    "fin": 500,
    "ain1": 73,
    "ain2": 73,
    "ain3": 70,
    "vbyp1": 227,
    "vbyp2": 226,
    "vbyp3": 227,
    "fbyp": 500,
    "vout1": 230,
    "vout2": 229,
    "vout3": 229,
    "fout": 500,
    "aout1": 52,
    "aout2": 52,
    "aout3": 72,
    "apkout1": 100,
    "apkout2": 90,
    "apkout3": 123,
    "w1": 944,
    "w2": 924,
    "w3": 1456,
    "load1": 6,
    "load2": 6,
    "load3": 9,
    "vbatp": 2733,
    "vbatn": 2729,
    "abatp": -2,
    "abatn": -1,
    "autonomy": 475,
    "batcap": 100,
    "KWh": 0,
    "tsys": 27.0,
    "tbatext": 24.5,
    "alarms": [],
    "system_status": {
        "status": "LOAD ON INVERTER",
        "status_color": "#00AEF0",
        "input_color": "#00AEF0",
        "bypass_color": "#00AEF0",
        "system_color": "#00AEF0",
        "battery_color": "#00AEF0",
        "output_color": "#00AEF0",
        "sinottico": 5
    }
}
```

**Response**: JSON (Error)

```json
{
    "error": "Unable to fetch full UPS status"
}
```

**Response Fields**:

| Field | Type | Description |
|-------|------|-------------|
| `current_date` | string | Timestamp from UPS |
| `vin1`, `vin2`, `vin3` | integer | Input voltage per phase (Volts) |
| `fin` | integer | Input frequency (decihertz, divide by 10 for Hz) |
| `ain1`, `ain2`, `ain3` | integer | Input current per phase (Amperes) |
| `vbyp1`, `vbyp2`, `vbyp3` | integer | Bypass voltage per phase (Volts) |
| `fbyp` | integer | Bypass frequency (decihertz) |
| `vout1`, `vout2`, `vout3` | integer | Output voltage per phase (Volts) |
| `fout` | integer | Output frequency (decihertz) |
| `aout1`, `aout2`, `aout3` | integer | Output current per phase (Amperes) |
| `apkout1`, `apkout2`, `apkout3` | integer | Peak output current per phase (Amperes) |
| `w1`, `w2`, `w3` | integer | Active power per phase (Watts) |
| `load1`, `load2`, `load3` | integer | Load percentage per phase (0-100) |
| `vbatp`, `vbatn` | integer | Battery bus voltage (decivolts, divide by 10) |
| `abatp`, `abatn` | integer | Battery current (Amperes, negative = charging) |
| `autonomy` | integer | Estimated runtime in minutes |
| `batcap` | integer | Battery capacity percentage (0-100) |
| `KWh` | integer | Energy consumption in kilowatt-hours |
| `tsys` | float | System temperature (Celsius) |
| `tbatext` | float | Battery external temperature (Celsius) |
| `alarms` | array | List of active alarm strings (empty if none) |
| `system_status` | object | System status details with colors and mode |

**Status Codes**:
| Code | Description |
|------|-------------|
| 200 | Success |
| 500 | Unable to fetch full UPS status |

**Usage Notes**:
- This endpoint is used by the System Status tab in the dashboard
- Frequency values are in decihertz (multiply by 0.1 to get Hz)
- Battery voltages are in decivolts (multiply by 0.1 to get V)
- Negative battery current indicates charging; positive indicates discharging

**Example**:
```bash
curl http://localhost:8080/api/ups_full_status
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
