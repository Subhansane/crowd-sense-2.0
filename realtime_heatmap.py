#!/usr/bin/env python3
"""
Real-Time IMSI Heatmap Server
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import asyncio
import json
import os
import re
import time
from datetime import datetime
from collections import defaultdict
import threading
import random

app = FastAPI(title="Real-Time IMSI Heatmap")

# Store connected clients
connected_clients = set()
last_position = 0
current_locations = []
operator_counts = defaultdict(int)
total_devices = set()

# ==========================================
# LOCATION MAPPING (Add more as you discover)
# ==========================================
CELL_LOCATIONS = {
    # Karachi area
    ("359", "12911"): {"lat": 24.8607, "lon": 67.0011, "area": "Saddar"},
    ("359", "12913"): {"lat": 24.8510, "lon": 67.0350, "area": "Defence"},
    ("359", "12914"): {"lat": 24.8610, "lon": 67.0150, "area": "Civic Center"},
    
    # Islamabad area
    ("58803", "18176"): {"lat": 33.6844, "lon": 73.0479, "area": "Blue Area"},
    
    # Lahore area (example)
    ("12345", "67890"): {"lat": 31.5497, "lon": 74.3436, "area": "Gulberg"},
}

def get_cell_location(lac, cell_id):
    """Get GPS coordinates for cell tower"""
    key = (str(lac), str(cell_id))
    if key in CELL_LOCATIONS:
        return CELL_LOCATIONS[key]
    # Default location (center of Pakistan)
    return {"lat": 30.3753, "lon": 69.3451, "area": "Unknown"}

def parse_imsi_line(line):
    """Extract IMSI data from log line"""
    if not line or line.startswith('Nb IMSI') or line.startswith('stamp'):
        return None
    
    imsi_match = re.search(r'410\s+0[3467]\s+\d+', line)
    if not imsi_match:
        return None
    
    imsi_parts = imsi_match.group(0).split()
    mcc = imsi_parts[0]
    mnc = imsi_parts[1]
    imsi_number = imsi_parts[2]
    full_imsi = f"{mcc}{mnc}{imsi_number}"
    display_imsi = f"{mcc} {mnc} {imsi_number}"
    
    # Operator mapping
    operators = {
        '06': 'Telenor',
        '04': 'Zong',
        '03': 'Ufone',
        '01': 'Jazz',
        '07': 'Jazz'
    }
    operator = operators.get(mnc, 'Unknown')
    
    # Extract LAC and CellID
    parts = [p.strip() for p in line.split(';')]
    lac = None
    cell_id = None
    
    if len(parts) >= 11:
        lac = parts[9]
        cell_id = parts[10]
    
    location = get_cell_location(lac, cell_id)
    
    timestamp = datetime.now().isoformat()
    time_match = re.search(r'\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}', line)
    if time_match:
        timestamp = time_match.group(0).replace(' ', 'T')
    
    return {
        'imsi': full_imsi,
        'display_imsi': display_imsi,
        'operator': operator,
        'lac': lac,
        'cell_id': cell_id,
        'lat': location['lat'],
        'lon': location['lon'],
        'area': location['area'],
        'timestamp': timestamp
    }

def monitor_imsi_file():
    """Monitor imsi_output.txt for new data"""
    global last_position, current_locations, operator_counts, total_devices
    
    imsi_file = "imsi_output.txt"
    if not os.path.exists(imsi_file):
        open(imsi_file, 'a').close()
    
    while True:
        try:
            with open(imsi_file, 'r') as f:
                f.seek(last_position)
                new_lines = f.readlines()
                last_position = f.tell()
                
                for line in new_lines:
                    data = parse_imsi_line(line)
                    if data:
                        current_locations.append(data)
                        if len(current_locations) > 500:
                            current_locations = current_locations[-500:]
                        
                        operator_counts[data['operator']] += 1
                        total_devices.add(data['imsi'])
                        
                        broadcast_data = {
                            'type': 'new_imsi',
                            'data': data,
                            'stats': {
                                'total_locations': len(current_locations),
                                'unique_devices': len(total_devices),
                                'operators': dict(operator_counts)
                            }
                        }
                        
                        for client in connected_clients.copy():
                            try:
                                asyncio.run_coroutine_threadsafe(
                                    client.send_json(broadcast_data),
                                    asyncio.get_event_loop()
                                )
                            except:
                                pass
                
                time.sleep(2)
        except Exception as e:
            print(f"Monitor error: {e}")
            time.sleep(5)

# Start file monitoring
threading.Thread(target=monitor_imsi_file, daemon=True).start()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_clients.add(websocket)
    
    # Send initial data
    await websocket.send_json({
        'type': 'initial',
        'stats': {
            'total_locations': len(current_locations),
            'unique_devices': len(total_devices),
            'operators': dict(operator_counts)
        },
        'locations': current_locations[-100:]
    })
    
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        connected_clients.remove(websocket)

@app.get("/")
async def get_page():
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Live IMSI Heatmap</title>
        <meta charset="utf-8">
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <script src="https://unpkg.com/leaflet.heat@0.2.0/dist/leaflet-heat.js"></script>
        <style>
            body { margin: 0; font-family: Arial; }
            #map { height: 100vh; width: 100%; }
            .panel {
                position: absolute;
                top: 20px;
                left: 20px;
                background: rgba(0,0,0,0.8);
                color: white;
                padding: 15px;
                border-radius: 8px;
                z-index: 1000;
                min-width: 250px;
            }
            .live { color: red; animation: pulse 1s infinite; }
            @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.5; } }
        </style>
    </head>
    <body>
        <div id="map"></div>
        <div class="panel">
            <h2>📡 LIVE IMSI HEATMAP</h2>
            <div id="stats">Loading...</div>
        </div>
        
        <script>
            var map = L.map('map').setView([30.3753, 69.3451], 5);
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(map);
            
            var heatLayer;
            var ws = new WebSocket(`ws://${window.location.host}/ws`);
            
            ws.onmessage = function(event) {
                var data = JSON.parse(event.data);
                if (data.type === 'initial' || data.type === 'new_imsi') {
                    document.getElementById('stats').innerHTML = `
                        📱 Devices: ${data.stats.unique_devices}<br>
                        📊 Operators: ${Object.entries(data.stats.operators).map(([k,v]) => `${k}:${v}`).join(', ')}
                    `;
                    updateHeatmap(data.locations || []);
                }
            };
            
            function updateHeatmap(locations) {
                var points = locations.map(l => [l.lat, l.lon, 1]);
                if (heatLayer) map.removeLayer(heatLayer);
                heatLayer = L.heatLayer(points, {radius: 25}).addTo(map);
            }
        </script>
    </body>
    </html>
    """)

@app.get("/api/heatmap")
async def get_heatmap():
    return current_locations[-200:]

if __name__ == "__main__":
    import uvicorn
    print("\n" + "="*60)
    print("🔥 REAL-TIME IMSI HEATMAP SERVER")
    print("="*60)
    print("\n🌐 Open in browser: http://localhost:8000")
    print("📡 Watching: imsi_output.txt")
    print("\nPress Ctrl+C to stop\n")
    uvicorn.run(app, host="0.0.0.0", port=8000)
