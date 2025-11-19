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
        return [dict(zip(columns, row)) for row in rows]
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
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔌 UPS Server Dashboard</h1>
            <p>Monitor and configure UPS client connections</p>
        </div>
        
        <div class="nav">
            <button class="nav-btn active" onclick="showSection('clients')">
                📡 Client Connections
            </button>
            <button class="nav-btn" onclick="showSection('config')">
                ⚙️ Configuration
            </button>
        </div>
        
        <div class="content">
            <div id="alert-container"></div>
            
            <!-- Client Connections Section -->
            <div id="clients-section" class="section active">
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
                    <h3 style="margin-bottom: 20px;">Edit Client Shutdown Times</h3>
                    <div class="form-row">
                        <div class="form-group">
                            <label for="client-select">Select Client</label>
                            <select id="client-select" onchange="updateShutdownInput()">
                            </select>
                        </div>
                        <div class="form-group">
                            <label for="shutdown-seconds">Seconds to Shutdown</label>
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
        </div>
        
        <div class="footer">
            Database: """ + DB_PATH + """ | UPS Server Dashboard | Auto-refresh every 30 seconds
        </div>
    </div>
    
    <script>
        let clientsData = [];
        let configData = [];
        let currentSection = 'clients';
        
        // Show/hide sections
        function showSection(section) {
            currentSection = section;
            document.querySelectorAll('.section').forEach(el => el.classList.remove('active'));
            document.querySelectorAll('.nav-btn').forEach(el => el.classList.remove('active'));
            
            if (section === 'clients') {
                document.getElementById('clients-section').classList.add('active');
                document.querySelectorAll('.nav-btn')[0].classList.add('active');
            } else {
                document.getElementById('config-section').classList.add('active');
                document.querySelectorAll('.nav-btn')[1].classList.add('active');
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
            if (currentSection === 'clients') {
                loadClients();
            } else {
                loadConfig();
            }
        }
        
        // Initialize dashboard
        async function init() {
            await loadClients();
            await loadConfig();
            
            // Auto-refresh every 30 seconds
            setInterval(refreshData, 30000);
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
