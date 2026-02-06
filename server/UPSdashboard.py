#!/usr/bin/env python3
"""
UPS Server Dashboard - HTTP server interface for monitoring and configuration
Run: python3 UPSdashboard.py [port]
Default port: 8080
"""

import sqlite3
import json
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from datetime import datetime

# Configuration
DB_PATH = 'ups_clients.db'
DEFAULT_PORT = 8080

def get_db_connection():
    """Create a database connection."""
    return sqlite3.connect(DB_PATH)

def load_client_connections():
    """Load all client connections from the database."""
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
                    # If parsing fails, keep the original string
                    pass
            clients.append(client_dict)
        return clients
    except Exception as e:
        print(f"Error loading client connections: {e}")
        return []

def load_configuration():
    """Load all configuration values from the database."""
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

def update_config_value(key: str, value: str):
    """Update a configuration value in the database."""
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

def update_client_shutdown_time(hostname: str, seconds: int):
    """Update the seconds_to_shutdown for a client."""
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

def get_ups_status():
    """Get current UPS status by reading from the UPS directly."""
    try:
        import urllib.request
        import ssl
        
        # Get UPS URL from configuration
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM configuration WHERE key = 'UPS_URL'")
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return None
        
        ups_url = result[0]
        
        # Create SSL context that doesn't verify certificates
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        # Fetch UPS data
        request = urllib.request.Request(ups_url)
        with urllib.request.urlopen(request, context=ssl_context, timeout=5) as response:
            data = response.read().decode('utf-8')
            json_data = json.loads(data)
            
            # Extract autonomy field (total minutes)
            if 'autonomy' in json_data:
                total_minutes = int(json_data['autonomy'])
                return {'total_minutes': total_minutes, 'status': 'ok'}
        
        return None
    except Exception as e:
        print(f"Error getting UPS status: {e}")
        return None

def get_ups_full_status():
    """Get complete UPS status with all fields from live_data.json."""
    try:
        import urllib.request
        import ssl
        
        # Get UPS URL from configuration
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM configuration WHERE key = 'UPS_URL'")
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return None
        
        ups_url = result[0]
        
        # Create SSL context that doesn't verify certificates
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        # Fetch UPS data
        request = urllib.request.Request(ups_url)
        with urllib.request.urlopen(request, context=ssl_context, timeout=5) as response:
            data = response.read().decode('utf-8')
            json_data = json.loads(data)
            return json_data
        
    except Exception as e:
        print(f"Error getting full UPS status: {e}")
        return None

class DashboardHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the UPS dashboard."""
    
    def log_message(self, format, *args):
        """Override to customize logging."""
        print(f"[{self.log_date_time_string()}] {format % args}")
    
    def do_GET(self):
        """Handle GET requests."""
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == '/' or parsed_path.path == '/index.html':
            self.serve_dashboard()
        elif parsed_path.path == '/api/clients':
            self.serve_clients_data()
        elif parsed_path.path == '/api/config':
            self.serve_config_data()
        elif parsed_path.path == '/api/ups_status':
            self.serve_ups_status()
        elif parsed_path.path == '/api/ups_full_status':
            self.serve_ups_full_status()
        else:
            self.send_error(404, "Page not found")
    
    def do_POST(self):
        """Handle POST requests."""
        parsed_path = urlparse(self.path)
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length).decode('utf-8')
        
        try:
            data = json.loads(post_data)
        except json.JSONDecodeError:
            self.send_error(400, "Invalid JSON")
            return
        
        if parsed_path.path == '/api/update_shutdown':
            self.handle_update_shutdown(data)
        elif parsed_path.path == '/api/update_config':
            self.handle_update_config(data)
        else:
            self.send_error(404, "Endpoint not found")
    
    def serve_dashboard(self):
        """Serve the main dashboard HTML page."""
        if not os.path.exists(DB_PATH):
            html = self.generate_error_page("Database not found", 
                                           f"Database file '{DB_PATH}' does not exist. Please start the UPS server first.")
        else:
            html = self.generate_dashboard_html()
        
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', len(html.encode('utf-8')))
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))
    
    def serve_clients_data(self):
        """Serve client connections data as JSON."""
        clients = load_client_connections()
        self.send_json_response({"clients": clients})
    
    def serve_config_data(self):
        """Serve configuration data as JSON."""
        config = load_configuration()
        self.send_json_response({"config": config})
    
    def serve_ups_status(self):
        """Serve UPS status data as JSON."""
        ups_status = get_ups_status()
        if ups_status:
            self.send_json_response(ups_status)
        else:
            self.send_json_response({"status": "error", "message": "Unable to fetch UPS status"}, 500)
    
    def serve_ups_full_status(self):
        """Serve complete UPS status data as JSON."""
        ups_full_status = get_ups_full_status()
        if ups_full_status:
            self.send_json_response(ups_full_status)
        else:
            self.send_json_response({"error": "Unable to fetch full UPS status"}, 500)
    
    def handle_update_shutdown(self, data):
        """Handle shutdown time update request."""
        hostname = data.get('hostname')
        seconds = data.get('seconds')
        
        if not hostname or seconds is None:
            self.send_json_response({"success": False, "error": "Missing hostname or seconds"}, 400)
            return
        
        try:
            seconds = int(seconds)
            if update_client_shutdown_time(hostname, seconds):
                self.send_json_response({"success": True, "message": f"Updated {hostname} shutdown time to {seconds} seconds"})
            else:
                self.send_json_response({"success": False, "error": "Failed to update database"}, 500)
        except ValueError:
            self.send_json_response({"success": False, "error": "Invalid seconds value"}, 400)
    
    def handle_update_config(self, data):
        """Handle configuration update request."""
        key = data.get('key')
        value = data.get('value')
        
        if not key or value is None:
            self.send_json_response({"success": False, "error": "Missing key or value"}, 400)
            return
        
        if update_config_value(key, value):
            self.send_json_response({"success": True, "message": f"Updated {key}"})
        else:
            self.send_json_response({"success": False, "error": "Failed to update database"}, 500)
    
    def send_json_response(self, data, status=200):
        """Send a JSON response."""
        json_data = json.dumps(data)
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', len(json_data.encode('utf-8')))
        self.end_headers()
        self.wfile.write(json_data.encode('utf-8'))
    
    def generate_error_page(self, title, message):
        """Generate an error page."""
        return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Error - UPS Dashboard</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }}
        .error-container {{ background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        h1 {{ color: #d32f2f; }}
        p {{ color: #666; line-height: 1.6; }}
    </style>
</head>
<body>
    <div class="error-container">
        <h1>⚠️ {title}</h1>
        <p>{message}</p>
    </div>
</body>
</html>"""
    
    def generate_dashboard_html(self):
        """Generate the main dashboard HTML with embedded JavaScript."""
        return """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🔌 UPS Server Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
            background: #1e1e2e;
            border-radius: 12px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.5);
            overflow: hidden;
            border: 1px solid #2a2a3e;
        }
        .header {
            background: linear-gradient(135deg, #0f3460 0%, #533483 100%);
            color: #e4e4e7;
            padding: 30px;
            text-align: center;
            border-bottom: 2px solid #3b82f6;
        }
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
            color: #ffffff;
        }
        .header p {
            color: #d4d4d8;
        }
        .nav {
            display: flex;
            background: #27293d;
            border-bottom: 2px solid #3f3f55;
        }
        .nav-btn {
            flex: 1;
            padding: 15px 30px;
            background: none;
            border: none;
            cursor: pointer;
            font-size: 16px;
            font-weight: 600;
            transition: all 0.3s;
            color: #a1a1aa;
        }
        .nav-btn:hover { 
            background: #2d2f41; 
            color: #e4e4e7;
        }
        .nav-btn.active {
            background: #1e1e2e;
            color: #60a5fa;
            border-bottom: 3px solid #3b82f6;
        }
        .content {
            padding: 30px;
            min-height: 400px;
            background: #1e1e2e;
        }
        .section {
            display: none;
        }
        .section.active {
            display: block;
            animation: fadeIn 0.3s;
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .section-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 25px;
            padding-bottom: 15px;
            border-bottom: 2px solid #3f3f55;
        }
        .section-header h2 {
            color: #e4e4e7;
            font-size: 1.8em;
        }
        .btn {
            padding: 10px 20px;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 600;
            transition: all 0.3s;
        }
        .btn-primary {
            background: #3b82f6;
            color: #ffffff;
        }
        .btn-primary:hover {
            background: #2563eb;
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(59, 130, 246, 0.4);
        }
        .btn-success {
            background: #10b981;
            color: #ffffff;
        }
        .btn-success:hover {
            background: #059669;
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(16, 185, 129, 0.4);
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
            background: #27293d;
            box-shadow: 0 2px 8px rgba(0,0,0,0.3);
            border-radius: 8px;
            overflow: hidden;
            border: 1px solid #3f3f55;
        }
        thead {
            background: linear-gradient(135deg, #0f3460 0%, #533483 100%);
            color: #ffffff;
        }
        th, td {
            padding: 15px;
            text-align: left;
            border-bottom: 1px solid #3f3f55;
        }
        th {
            font-weight: 600;
            text-transform: uppercase;
            font-size: 13px;
            letter-spacing: 0.5px;
        }
        td {
            color: #d4d4d8;
        }
        tbody tr {
            transition: background 0.2s;
        }
        tbody tr:hover {
            background: #2d2f41;
        }
        tbody tr:last-child td {
            border-bottom: none;
        }
        .form-group {
            margin-bottom: 20px;
        }
        .form-group label {
            display: block;
            margin-bottom: 8px;
            font-weight: 600;
            color: #e4e4e7;
        }
        .form-group select,
        .form-group input {
            width: 100%;
            padding: 12px;
            border: 2px solid #3f3f55;
            border-radius: 6px;
            font-size: 14px;
            transition: border-color 0.3s;
            background: #27293d;
            color: #e4e4e7;
        }
        .form-group select:focus,
        .form-group input:focus {
            outline: none;
            border-color: #3b82f6;
            background: #2d2f41;
        }
        .form-group select option {
            background: #27293d;
            color: #e4e4e7;
        }
        .form-row {
            display: grid;
            grid-template-columns: 1fr 1fr 200px;
            gap: 20px;
            align-items: end;
        }
        .alert {
            padding: 15px 20px;
            border-radius: 6px;
            margin-bottom: 20px;
            font-weight: 500;
            animation: slideIn 0.3s;
        }
        @keyframes slideIn {
            from { transform: translateX(-20px); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }
        .alert-success {
            background: #064e3b;
            color: #86efac;
            border: 1px solid #10b981;
        }
        .alert-error {
            background: #7f1d1d;
            color: #fca5a5;
            border: 1px solid #ef4444;
        }
        .alert-info {
            background: #1e3a8a;
            color: #93c5fd;
            border: 1px solid #3b82f6;
        }
        .badge {
            display: inline-block;
            padding: 6px 12px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 600;
            background: #3f3f55;
            color: #e4e4e7;
        }
        .footer {
            background: #27293d;
            padding: 15px 30px;
            text-align: center;
            color: #a1a1aa;
            font-size: 14px;
            border-top: 1px solid #3f3f55;
        }
        .loading {
            text-align: center;
            padding: 40px;
            color: #a1a1aa;
        }
        .spinner {
            border: 3px solid #3f3f55;
            border-top: 3px solid #3b82f6;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 0 auto 20px;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        h3 {
            color: #e4e4e7;
        }
        .ups-status-badge {
            display: inline-block;
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 14px;
            font-weight: 700;
            background: #10b981;
            color: #ffffff;
            margin-left: 15px;
            box-shadow: 0 2px 8px rgba(16, 185, 129, 0.3);
        }
        .ups-status-badge.warning {
            background: #f59e0b;
        }
        .ups-status-badge.error {
            background: #ef4444;
        }
        .status-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .status-card {
            background: linear-gradient(135deg, #27293d 0%, #2d2f41 100%);
            border: 2px solid #3f3f55;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            transition: transform 0.3s, box-shadow 0.3s;
        }
        .status-card:hover {
            transform: translateY(-4px);
            box-shadow: 0 8px 24px rgba(0,0,0,0.4);
        }
        .status-card-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 15px;
            padding-bottom: 12px;
            border-bottom: 2px solid #3f3f55;
        }
        .status-card-title {
            font-size: 14px;
            font-weight: 600;
            color: #a1a1aa;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .status-card-icon {
            font-size: 24px;
        }
        .status-card-value {
            font-size: 32px;
            font-weight: 700;
            color: #e4e4e7;
            margin-bottom: 8px;
        }
        .status-card-label {
            font-size: 13px;
            color: #71717a;
        }
        .status-indicator {
            display: inline-block;
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 13px;
            font-weight: 600;
            margin-top: 10px;
        }
        .status-ok {
            background: rgba(16, 185, 129, 0.2);
            color: #10b981;
            border: 1px solid #10b981;
        }
        .status-warning {
            background: rgba(245, 158, 11, 0.2);
            color: #f59e0b;
            border: 1px solid #f59e0b;
        }
        .status-error {
            background: rgba(239, 68, 68, 0.2);
            color: #ef4444;
            border: 1px solid #ef4444;
        }
        .phase-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 15px;
            margin-top: 15px;
        }
        .phase-card {
            background: #27293d;
            border: 1px solid #3f3f55;
            border-radius: 8px;
            padding: 15px;
            text-align: center;
        }
        .phase-card-title {
            font-size: 12px;
            font-weight: 600;
            color: #a1a1aa;
            text-transform: uppercase;
            margin-bottom: 10px;
        }
        .phase-card-value {
            font-size: 24px;
            font-weight: 700;
            color: #60a5fa;
            margin-bottom: 5px;
        }
        .phase-card-unit {
            font-size: 11px;
            color: #71717a;
        }
        .info-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 15px;
            margin-top: 20px;
        }
        .info-item {
            background: #27293d;
            border: 1px solid #3f3f55;
            border-radius: 8px;
            padding: 15px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .info-label {
            font-size: 13px;
            font-weight: 600;
            color: #a1a1aa;
        }
        .info-value {
            font-size: 16px;
            font-weight: 700;
            color: #e4e4e7;
        }
        .alarm-box {
            background: rgba(239, 68, 68, 0.1);
            border: 2px solid #ef4444;
            border-radius: 8px;
            padding: 15px;
            margin-top: 15px;
        }
        .alarm-box.no-alarms {
            background: rgba(16, 185, 129, 0.1);
            border-color: #10b981;
        }
        .alarm-title {
            font-size: 14px;
            font-weight: 600;
            margin-bottom: 8px;
            color: #ef4444;
        }
        .alarm-box.no-alarms .alarm-title {
            color: #10b981;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔌 UPS Server Dashboard</h1>
            <p id="header-subtitle">Monitor and configure UPS client connections</p>
        </div>
        
        <div class="nav">
            <button class="nav-btn active" onclick="showSection('system')">
                ⚡ System Status
            </button>
            <button class="nav-btn" onclick="showSection('clients')">
                📡 Client Connections
            </button>
            <button class="nav-btn" onclick="showSection('config')">
                ⚙️ Configuration
            </button>
        </div>
        
        <div class="content">
            <div id="alert-container"></div>
            
            <!-- Client Connections Section -->
            <div id="clients-section" class="section">
                <div class="section-header">
                    <h2>Client Connections</h2>
                    <button class="btn btn-primary" onclick="refreshData()">
                        🔄 Refresh
                    </button>
                </div>
                
                <div id="clients-content">
                    <div class="loading">
                        <div class="spinner"></div>
                        <p>Loading client data...</p>
                    </div>
                </div>
                
                <div id="edit-shutdown-section" style="margin-top: 40px; display: none;">
                    <h3 style="margin-bottom: 20px;">Edit Client Shutdown Delays</h3>
                    <div class="form-row">
                        <div class="form-group">
                            <label for="client-select">Select Client</label>
                            <select id="client-select" onchange="updateShutdownInput()">
                            </select>
                        </div>
                        <div class="form-group">
                            <label for="shutdown-seconds">Delay Shutdown in Seconds</label>
                            <input type="number" id="shutdown-seconds" min="0" max="3600" step="10" value="0">
                        </div>
                        <div class="form-group">
                            <label>&nbsp;</label>
                            <button class="btn btn-success" onclick="updateShutdownTime()" style="width: 100%;">
                                💾 Update
                            </button>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Configuration Section -->
            <div id="config-section" class="section">
                <div class="section-header">
                    <h2>Server Configuration</h2>
                    <button class="btn btn-primary" onclick="refreshData()">
                        🔄 Refresh
                    </button>
                </div>
                
                <div id="config-content">
                    <div class="loading">
                        <div class="spinner"></div>
                        <p>Loading configuration data...</p>
                    </div>
                </div>
                
                <div id="edit-config-section" style="margin-top: 40px; display: none;">
                    <h3 style="margin-bottom: 20px;">Edit Configuration</h3>
                    <div class="form-row">
                        <div class="form-group">
                            <label for="config-key-select">Configuration Key</label>
                            <select id="config-key-select" onchange="updateConfigInput()">
                            </select>
                        </div>
                        <div class="form-group">
                            <label for="config-value">Value</label>
                            <input type="text" id="config-value" value="">
                        </div>
                        <div class="form-group">
                            <label>&nbsp;</label>
                            <button class="btn btn-success" onclick="updateConfigValue()" style="width: 100%;">
                                💾 Update
                            </button>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- System Status Section -->
            <div id="system-section" class="section active">
                <div class="section-header">
                    <h2>UPS System Status</h2>
                    <button class="btn btn-primary" onclick="refreshSystemStatus()">
                        🔄 Refresh
                    </button>
                </div>
                
                <div id="system-content">
                    <div class="loading">
                        <div class="spinner"></div>
                        <p>Loading UPS system data...</p>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="footer">
            Database: """ + DB_PATH + """ | UPS Server Dashboard | Auto-refresh every 30 seconds
        </div>
    </div>
    
    <script>
        let clientsData = [];
        let configData = [];
        let currentSection = 'system';
        let upsStatusData = null;
        
        // Convert minutes to hours and minutes format
        function formatTime(totalMinutes) {
            if (totalMinutes === null || totalMinutes === undefined) {
                return 'N/A';
            }
            const hours = Math.floor(totalMinutes / 60);
            const minutes = totalMinutes % 60;
            if (hours > 0) {
                return `${hours}h ${minutes}m`;
            }
            return `${minutes}m`;
        }
        
        // Load UPS status
        async function loadUPSStatus() {
            try {
                const response = await fetch('/api/ups_status');
                const data = await response.json();
                upsStatusData = data;
                updateHeaderWithUPSStatus();
            } catch (error) {
                console.error('Error loading UPS status:', error);
                upsStatusData = null;
                updateHeaderWithUPSStatus();
            }
        }
        
        // Update header with UPS status
        function updateHeaderWithUPSStatus() {
            const subtitle = document.getElementById('header-subtitle');
            if (upsStatusData && upsStatusData.status === 'ok') {
                const timeStr = formatTime(upsStatusData.total_minutes);
                const badgeClass = upsStatusData.total_minutes > 30 ? '' : 
                                   upsStatusData.total_minutes > 15 ? 'warning' : 'error';
                subtitle.innerHTML = `Monitor and configure UPS client connections <span class="ups-status-badge ${badgeClass}">⚡ Battery: ${timeStr}</span>`;
            } else {
                subtitle.innerHTML = 'Monitor and configure UPS client connections <span class="ups-status-badge error">⚡ Battery: Unknown</span>';
            }
        }
        
        // Show/hide sections
        function showSection(section) {
            currentSection = section;
            document.querySelectorAll('.section').forEach(el => el.classList.remove('active'));
            document.querySelectorAll('.nav-btn').forEach(el => el.classList.remove('active'));
            
            if (section === 'system') {
                document.getElementById('system-section').classList.add('active');
                document.querySelectorAll('.nav-btn')[0].classList.add('active');
            } else if (section === 'clients') {
                document.getElementById('clients-section').classList.add('active');
                document.querySelectorAll('.nav-btn')[1].classList.add('active');
            } else if (section === 'config') {
                document.getElementById('config-section').classList.add('active');
                document.querySelectorAll('.nav-btn')[2].classList.add('active');
            }
        }
        
        // Show alerts
        function showAlert(message, type = 'success') {
            const container = document.getElementById('alert-container');
            const alert = document.createElement('div');
            alert.className = `alert alert-${type}`;
            alert.textContent = message;
            container.appendChild(alert);
            
            setTimeout(() => {
                alert.style.opacity = '0';
                setTimeout(() => alert.remove(), 300);
            }, 4000);
        }
        
        // Load clients data
        async function loadClients() {
            try {
                const response = await fetch('/api/clients');
                const data = await response.json();
                clientsData = data.clients;
                renderClientsTable();
                updateClientSelect();
            } catch (error) {
                document.getElementById('clients-content').innerHTML = 
                    '<div class="alert alert-error">Error loading client data: ' + error.message + '</div>';
            }
        }
        
        // Render clients table
        function renderClientsTable() {
            const content = document.getElementById('clients-content');
            
            if (clientsData.length === 0) {
                content.innerHTML = '<div class="alert alert-info">No client connections recorded yet.</div>';
                document.getElementById('edit-shutdown-section').style.display = 'none';
                return;
            }
            
            let html = '<p style="margin-bottom: 15px; color: #a1a1aa; font-weight: 600;">';
            html += `Total Clients: <span class="badge">${clientsData.length}</span></p>`;
            html += '<table><thead><tr>';
            html += '<th>Hostname</th><th>IP Address</th><th>Port</th>';
            html += '<th>Last Connection</th><th>Shutdown Delay (s)</th>';
            html += '</tr></thead><tbody>';
            
            clientsData.forEach(client => {
                html += '<tr>';
                html += `<td><strong>${client.hostname}</strong></td>`;
                html += `<td>${client.ip_address}</td>`;
                html += `<td>${client.port}</td>`;
                html += `<td>${client.last_connection_time || 'Never'}</td>`;
                html += `<td><span class="badge">${client.seconds_to_shutdown}</span></td>`;
                html += '</tr>';
            });
            
            html += '</tbody></table>';
            content.innerHTML = html;
            document.getElementById('edit-shutdown-section').style.display = 'block';
        }
        
        // Update client select dropdown
        function updateClientSelect() {
            const select = document.getElementById('client-select');
            select.innerHTML = '';
            
            clientsData.forEach(client => {
                const option = document.createElement('option');
                option.value = client.hostname;
                option.textContent = client.hostname;
                option.dataset.seconds = client.seconds_to_shutdown;
                select.appendChild(option);
            });
            
            updateShutdownInput();
        }
        
        // Update shutdown input based on selected client
        function updateShutdownInput() {
            const select = document.getElementById('client-select');
            const input = document.getElementById('shutdown-seconds');
            const selectedOption = select.options[select.selectedIndex];
            
            if (selectedOption) {
                input.value = selectedOption.dataset.seconds;
            }
        }
        
        // Update shutdown time
        async function updateShutdownTime() {
            const hostname = document.getElementById('client-select').value;
            const seconds = parseInt(document.getElementById('shutdown-seconds').value);
            
            try {
                const response = await fetch('/api/update_shutdown', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ hostname, seconds })
                });
                
                const result = await response.json();
                
                if (result.success) {
                    showAlert(result.message, 'success');
                    await loadClients();
                } else {
                    showAlert('Error: ' + result.error, 'error');
                }
            } catch (error) {
                showAlert('Error updating shutdown time: ' + error.message, 'error');
            }
        }
        
        // Load configuration data
        async function loadConfig() {
            try {
                const response = await fetch('/api/config');
                const data = await response.json();
                configData = data.config;
                renderConfigTable();
                updateConfigSelect();
            } catch (error) {
                document.getElementById('config-content').innerHTML = 
                    '<div class="alert alert-error">Error loading configuration: ' + error.message + '</div>';
            }
        }
        
        // Render config table
        function renderConfigTable() {
            const content = document.getElementById('config-content');
            
            if (configData.length === 0) {
                content.innerHTML = '<div class="alert alert-info">No configuration values found.</div>';
                document.getElementById('edit-config-section').style.display = 'none';
                return;
            }
            
            let html = '<p style="margin-bottom: 15px; color: #a1a1aa; font-weight: 600;">';
            html += `Total Configuration Values: <span class="badge">${configData.length}</span></p>`;
            html += '<table><thead><tr>';
            html += '<th>Key</th><th>Value</th>';
            html += '</tr></thead><tbody>';
            
            configData.forEach(config => {
                html += '<tr>';
                html += `<td><strong>${config.key}</strong></td>`;
                html += `<td>${config.value}</td>`;
                html += '</tr>';
            });
            
            html += '</tbody></table>';
            content.innerHTML = html;
            document.getElementById('edit-config-section').style.display = 'block';
        }
        
        // Update config select dropdown
        function updateConfigSelect() {
            const select = document.getElementById('config-key-select');
            select.innerHTML = '';
            
            configData.forEach(config => {
                const option = document.createElement('option');
                option.value = config.key;
                option.textContent = config.key;
                option.dataset.value = config.value;
                select.appendChild(option);
            });
            
            updateConfigInput();
        }
        
        // Update config input based on selected key
        function updateConfigInput() {
            const select = document.getElementById('config-key-select');
            const input = document.getElementById('config-value');
            const selectedOption = select.options[select.selectedIndex];
            
            if (selectedOption) {
                input.value = selectedOption.dataset.value;
            }
        }
        
        // Update config value
        async function updateConfigValue() {
            const key = document.getElementById('config-key-select').value;
            const value = document.getElementById('config-value').value;
            
            try {
                const response = await fetch('/api/update_config', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ key, value })
                });
                
                const result = await response.json();
                
                if (result.success) {
                    showAlert(result.message, 'success');
                    await loadConfig();
                } else {
                    showAlert('Error: ' + result.error, 'error');
                }
            } catch (error) {
                showAlert('Error updating configuration: ' + error.message, 'error');
            }
        }
        
        // Refresh current section data
        function refreshData() {
            if (currentSection === 'system') {
                loadSystemStatus();
            } else if (currentSection === 'clients') {
                loadClients();
            } else if (currentSection === 'config') {
                loadConfig();
            }
        }
        
        // Load full system status
        async function loadSystemStatus() {
            try {
                const response = await fetch('/api/ups_full_status');
                const data = await response.json();
                
                if (data.error) {
                    document.getElementById('system-content').innerHTML = 
                        '<div class="alert alert-error">Error loading system status: ' + data.error + '</div>';
                    return;
                }
                
                renderSystemStatus(data);
            } catch (error) {
                document.getElementById('system-content').innerHTML = 
                    '<div class="alert alert-error">Error loading system status: ' + error.message + '</div>';
            }
        }
        
        // Refresh system status only
        function refreshSystemStatus() {
            loadSystemStatus();
        }
        
        // Format frequency (divide by 10 to get Hz)
        function formatFrequency(value) {
            return value ? (value / 10).toFixed(1) + ' Hz' : 'N/A';
        }
        
        // Format voltage
        function formatVoltage(value) {
            return value ? value + ' V' : 'N/A';
        }
        
        // Format current
        function formatCurrent(value) {
            return value ? value + ' A' : 'N/A';
        }
        
        // Format power
        function formatPower(value) {
            return value ? value + ' W' : 'N/A';
        }
        
        // Format battery voltage (divide by 10)
        function formatBatteryVoltage(value) {
            return value ? (value / 10).toFixed(1) + ' V' : 'N/A';
        }
        
        // Format temperature
        function formatTemperature(value) {
            return value ? value + ' °C' : 'N/A';
        }
        
        // Get status badge class based on value
        function getStatusClass(status) {
            if (!status) return 'status-error';
            const statusUpper = status.toUpperCase();
            if (statusUpper.includes('INVERTER') || statusUpper.includes('NORMAL')) return 'status-ok';
            if (statusUpper.includes('BYPASS')) return 'status-warning';
            return 'status-error';
        }
        
        // Get battery status class
        function getBatteryClass(capacity) {
            if (capacity >= 80) return 'status-ok';
            if (capacity >= 50) return 'status-warning';
            return 'status-error';
        }
        
        // Get load status class
        function getLoadClass(load) {
            if (load <= 70) return 'status-ok';
            if (load <= 90) return 'status-warning';
            return 'status-error';
        }
        
        // Render system status
        function renderSystemStatus(data) {
            const content = document.getElementById('system-content');
            
            const statusClass = getStatusClass(data.system_status?.status || '');
            const batteryClass = getBatteryClass(data.batcap || 0);
            const maxLoad = Math.max(data.load1 || 0, data.load2 || 0, data.load3 || 0);
            const loadClass = getLoadClass(maxLoad);
            
            let html = `
                <!-- Overview Cards -->
                <div class="status-grid">
                    <div class="status-card">
                        <div class="status-card-header">
                            <span class="status-card-title">System Status</span>
                            <span class="status-card-icon">⚡</span>
                        </div>
                        <div class="status-card-value">${data.system_status?.status || 'Unknown'}</div>
                        <div class="status-card-label">Current Operating Mode</div>
                        <span class="status-indicator ${statusClass}">
                            ${data.system_status?.status || 'Unknown'}
                        </span>
                    </div>
                    
                    <div class="status-card">
                        <div class="status-card-header">
                            <span class="status-card-title">Battery Capacity</span>
                            <span class="status-card-icon">🔋</span>
                        </div>
                        <div class="status-card-value">${data.batcap || 0}%</div>
                        <div class="status-card-label">Autonomy: ${formatTime(data.autonomy || 0)}</div>
                        <span class="status-indicator ${batteryClass}">
                            ${data.batcap >= 80 ? 'Healthy' : data.batcap >= 50 ? 'Fair' : 'Low'}
                        </span>
                    </div>
                    
                    <div class="status-card">
                        <div class="status-card-header">
                            <span class="status-card-title">Load Status</span>
                            <span class="status-card-icon">📊</span>
                        </div>
                        <div class="status-card-value">${maxLoad}%</div>
                        <div class="status-card-label">Maximum Phase Load</div>
                        <span class="status-indicator ${loadClass}">
                            ${maxLoad <= 70 ? 'Normal' : maxLoad <= 90 ? 'High' : 'Critical'}
                        </span>
                    </div>
                </div>
                
                <!-- Alarms -->
                <h3 style="margin-top: 30px; margin-bottom: 15px;">🚨 System Alarms</h3>
            `;
            
            if (data.alarms && data.alarms.length > 0) {
                html += '<div class="alarm-box">';
                html += '<div class="alarm-title">⚠️ Active Alarms</div>';
                data.alarms.forEach(alarm => {
                    html += `<div style="color: #fca5a5; font-size: 14px; margin-top: 5px;">• ${alarm}</div>`;
                });
                html += '</div>';
            } else {
                html += '<div class="alarm-box no-alarms">';
                html += '<div class="alarm-title">✅ No Active Alarms</div>';
                html += '<div style="color: #86efac; font-size: 14px;">System operating normally</div>';
                html += '</div>';
            }
            
            html += `
                
                <!-- Input Measurements -->
                <h3 style="margin-top: 30px; margin-bottom: 15px;">⚡ Input Measurements (Mains)</h3>
                <div class="info-grid">
                    <div class="info-item">
                        <span class="info-label">Input Frequency</span>
                        <span class="info-value">${formatFrequency(data.fin)}</span>
                    </div>
                </div>
                <div class="phase-grid">
                    <div class="phase-card">
                        <div class="phase-card-title">Phase 1</div>
                        <div class="phase-card-value">${formatVoltage(data.vin1)}</div>
                        <div class="phase-card-unit">Current: ${formatCurrent(data.ain1)}</div>
                    </div>
                    <div class="phase-card">
                        <div class="phase-card-title">Phase 2</div>
                        <div class="phase-card-value">${formatVoltage(data.vin2)}</div>
                        <div class="phase-card-unit">Current: ${formatCurrent(data.ain2)}</div>
                    </div>
                    <div class="phase-card">
                        <div class="phase-card-title">Phase 3</div>
                        <div class="phase-card-value">${formatVoltage(data.vin3)}</div>
                        <div class="phase-card-unit">Current: ${formatCurrent(data.ain3)}</div>
                    </div>
                </div>
                
                <!-- Bypass Line -->
                <h3 style="margin-top: 30px; margin-bottom: 15px;">🔄 Bypass Line</h3>
                <div class="info-grid">
                    <div class="info-item">
                        <span class="info-label">Bypass Frequency</span>
                        <span class="info-value">${formatFrequency(data.fbyp)}</span>
                    </div>
                </div>
                <div class="phase-grid">
                    <div class="phase-card">
                        <div class="phase-card-title">Phase 1</div>
                        <div class="phase-card-value">${formatVoltage(data.vbyp1)}</div>
                    </div>
                    <div class="phase-card">
                        <div class="phase-card-title">Phase 2</div>
                        <div class="phase-card-value">${formatVoltage(data.vbyp2)}</div>
                    </div>
                    <div class="phase-card">
                        <div class="phase-card-title">Phase 3</div>
                        <div class="phase-card-value">${formatVoltage(data.vbyp3)}</div>
                    </div>
                </div>
                
                <!-- Output Measurements -->
                <h3 style="margin-top: 30px; margin-bottom: 15px;">📤 Output Measurements (Load)</h3>
                <div class="info-grid">
                    <div class="info-item">
                        <span class="info-label">Output Frequency</span>
                        <span class="info-value">${formatFrequency(data.fout)}</span>
                    </div>
                    <div class="info-item">
                        <span class="info-label">Total Power</span>
                        <span class="info-value">${(data.w1 || 0) + (data.w2 || 0) + (data.w3 || 0)} W</span>
                    </div>
                </div>
                <div class="phase-grid">
                    <div class="phase-card">
                        <div class="phase-card-title">Phase 1</div>
                        <div class="phase-card-value">${formatVoltage(data.vout1)}</div>
                        <div class="phase-card-unit">Current: ${formatCurrent(data.aout1)}</div>
                        <div class="phase-card-unit">Power: ${formatPower(data.w1)}</div>
                        <div class="phase-card-unit">Load: ${data.load1 || 0}%</div>
                        <div class="phase-card-unit">Peak: ${formatCurrent(data.apkout1)}</div>
                    </div>
                    <div class="phase-card">
                        <div class="phase-card-title">Phase 2</div>
                        <div class="phase-card-value">${formatVoltage(data.vout2)}</div>
                        <div class="phase-card-unit">Current: ${formatCurrent(data.aout2)}</div>
                        <div class="phase-card-unit">Power: ${formatPower(data.w2)}</div>
                        <div class="phase-card-unit">Load: ${data.load2 || 0}%</div>
                        <div class="phase-card-unit">Peak: ${formatCurrent(data.apkout2)}</div>
                    </div>
                    <div class="phase-card">
                        <div class="phase-card-title">Phase 3</div>
                        <div class="phase-card-value">${formatVoltage(data.vout3)}</div>
                        <div class="phase-card-unit">Current: ${formatCurrent(data.aout3)}</div>
                        <div class="phase-card-unit">Power: ${formatPower(data.w3)}</div>
                        <div class="phase-card-unit">Load: ${data.load3 || 0}%</div>
                        <div class="phase-card-unit">Peak: ${formatCurrent(data.apkout3)}</div>
                    </div>
                </div>
                
                <!-- Battery Status -->
                <h3 style="margin-top: 30px; margin-bottom: 15px;">🔋 Battery Status</h3>
                <div class="info-grid">
                    <div class="info-item">
                        <span class="info-label">Battery Capacity</span>
                        <span class="info-value">${data.batcap || 0}%</span>
                    </div>
                    <div class="info-item">
                        <span class="info-label">Autonomy Time</span>
                        <span class="info-value">${formatTime(data.autonomy || 0)}</span>
                    </div>
                    <div class="info-item">
                        <span class="info-label">Positive Bus Voltage</span>
                        <span class="info-value">${formatBatteryVoltage(data.vbatp)}</span>
                    </div>
                    <div class="info-item">
                        <span class="info-label">Negative Bus Voltage</span>
                        <span class="info-value">${formatBatteryVoltage(data.vbatn)}</span>
                    </div>
                    <div class="info-item">
                        <span class="info-label">Positive Current</span>
                        <span class="info-value">${formatCurrent(data.abatp)}</span>
                    </div>
                    <div class="info-item">
                        <span class="info-label">Negative Current</span>
                        <span class="info-value">${formatCurrent(data.abatn)}</span>
                    </div>
                </div>
                
                <!-- Environment & System -->
                <h3 style="margin-top: 30px; margin-bottom: 15px;">🌡️ Environment & Temperatures</h3>
                <div class="info-grid">
                    <div class="info-item">
                        <span class="info-label">System Temperature</span>
                        <span class="info-value">${formatTemperature(data.tsys)}</span>
                    </div>
                    <div class="info-item">
                        <span class="info-label">Battery Temperature</span>
                        <span class="info-value">${formatTemperature(data.tbatext)}</span>
                    </div>
                    <div class="info-item">
                        <span class="info-label">KWh Counter</span>
                        <span class="info-value">${data.KWh || 0} kWh</span>
                    </div>
                    <div class="info-item">
                        <span class="info-label">Last Update</span>
                        <span class="info-value">${data.current_date || 'N/A'}</span>
                    </div>
                </div>
                
                <!-- Power Summary Table -->
                <h3 style="margin-top: 30px; margin-bottom: 15px;">📊 Power Summary</h3>
            `;
            
            // Calculate power metrics
            const v1 = data.vout1 || 0;
            const v2 = data.vout2 || 0;
            const v3 = data.vout3 || 0;
            const a1 = data.aout1 || 0;
            const a2 = data.aout2 || 0;
            const a3 = data.aout3 || 0;
            const w1 = data.w1 || 0;
            const w2 = data.w2 || 0;
            const w3 = data.w3 || 0;
            
            // Apparent Power (kVA) = V × A / 1000
            const kva1 = (v1 * a1 / 1000).toFixed(2);
            const kva2 = (v2 * a2 / 1000).toFixed(2);
            const kva3 = (v3 * a3 / 1000).toFixed(2);
            const kvaTotal = (parseFloat(kva1) + parseFloat(kva2) + parseFloat(kva3)).toFixed(2);
            
            // Active Power (kW) = W / 1000
            const kw1 = (w1 / 1000).toFixed(2);
            const kw2 = (w2 / 1000).toFixed(2);
            const kw3 = (w3 / 1000).toFixed(2);
            const kwTotal = (parseFloat(kw1) + parseFloat(kw2) + parseFloat(kw3)).toFixed(2);
            
            // Power Factor = Active Power / Apparent Power
            const pf1 = parseFloat(kva1) > 0 ? (parseFloat(kw1) / parseFloat(kva1)).toFixed(2) : '0.00';
            const pf2 = parseFloat(kva2) > 0 ? (parseFloat(kw2) / parseFloat(kva2)).toFixed(2) : '0.00';
            const pf3 = parseFloat(kva3) > 0 ? (parseFloat(kw3) / parseFloat(kva3)).toFixed(2) : '0.00';
            const pfTotal = parseFloat(kvaTotal) > 0 ? (parseFloat(kwTotal) / parseFloat(kvaTotal)).toFixed(2) : '0.00';
            
            // Average load
            const avgLoad = Math.round(((data.load1 || 0) + (data.load2 || 0) + (data.load3 || 0)) / 3);
            
            html += `
                <table>
                    <thead>
                        <tr>
                            <th>Metric</th>
                            <th>Phase 1 (L1)</th>
                            <th>Phase 2 (L2)</th>
                            <th>Phase 3 (L3)</th>
                            <th>Total</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td><strong>Voltage</strong></td>
                            <td>${v1} V</td>
                            <td>${v2} V</td>
                            <td>${v3} V</td>
                            <td>—</td>
                        </tr>
                        <tr>
                            <td><strong>Current</strong></td>
                            <td>${a1} A</td>
                            <td>${a2} A</td>
                            <td>${a3} A</td>
                            <td>—</td>
                        </tr>
                        <tr>
                            <td><strong>Apparent Power (kVA)</strong></td>
                            <td>${kva1} kVA</td>
                            <td>${kva2} kVA</td>
                            <td>${kva3} kVA</td>
                            <td><strong>${kvaTotal} kVA</strong></td>
                        </tr>
                        <tr>
                            <td><strong>Active Power (kW)</strong></td>
                            <td>${kw1} kW</td>
                            <td>${kw2} kW</td>
                            <td>${kw3} kW</td>
                            <td><strong>${kwTotal} kW</strong></td>
                        </tr>
                        <tr>
                            <td><strong>Power Factor (PF)</strong></td>
                            <td>${pf1}</td>
                            <td>${pf2}</td>
                            <td>${pf3}</td>
                            <td><strong>${pfTotal}</strong></td>
                        </tr>
                        <tr>
                            <td><strong>Load Percentage</strong></td>
                            <td>${data.load1 || 0}%</td>
                            <td>${data.load2 || 0}%</td>
                            <td>${data.load3 || 0}%</td>
                            <td><strong>~${avgLoad}% Avg</strong></td>
                        </tr>
                    </tbody>
                </table>
            `;
            
            content.innerHTML = html;
        }
        
        // Refresh current section data
        function refreshData() {
            if (currentSection === 'clients') {
                loadClients();
            } else {
                loadConfig();
            }
        }
        
        // Initialize dashboard
        async function init() {
            await loadSystemStatus();
            await loadClients();
            await loadConfig();
            await loadUPSStatus();
            
            // Auto-refresh every 30 seconds
            setInterval(() => {
                if (currentSection === 'system') {
                    loadSystemStatus();
                } else if (currentSection === 'clients') {
                    loadClients();
                } else if (currentSection === 'config') {
                    loadConfig();
                }
            }, 30000);
            setInterval(loadUPSStatus, 30000);
        }
        
        // Start the dashboard
        init();
    </script>
</body>
</html>"""

def run_server(port=DEFAULT_PORT):
    """Run the HTTP server."""
    server_address = ('', port)
    httpd = HTTPServer(server_address, DashboardHandler)
    print(f"🔌 UPS Server Dashboard running at http://localhost:{port}")
    print(f"📊 Database: {DB_PATH}")
    print("Press Ctrl+C to stop the server")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n\nShutting down server...")
        httpd.shutdown()

def main():
    """Main entry point."""
    import sys
    
    port = DEFAULT_PORT
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print(f"Invalid port number. Using default port {DEFAULT_PORT}")
    
    run_server(port)

if __name__ == "__main__":
    main()
