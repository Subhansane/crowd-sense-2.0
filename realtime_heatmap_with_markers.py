#!/usr/bin/env python3
"""
Real-Time IMSI Heatmap with Location Shortcuts
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

app = FastAPI(title="IMSI Heatmap with Locations")

connected_clients = set()
last_position = 0
current_locations = []
operator_counts = defaultdict(int)
total_devices = set()

# ==========================================
# LOCATION MAPPING (Add your shortcuts here!)
# ==========================================
CELL_LOCATIONS = {
    # Karachi
    ("359", "12911"): {"lat": 24.8607, "lon": 67.0011, "area": "Saddar, Karachi"},
    ("359", "12913"): {"lat": 24.8510, "lon": 67.0350, "area": "Defence, Karachi"},
    ("359", "12914"): {"lat": 24.8610, "lon": 67.0150, "area": "Civic Center, Karachi"},
    
    # Islamabad
    ("58803", "18176"): {"lat": 33.6844, "lon": 73.0479, "area": "Blue Area, Islamabad"},
    
    # Lahore
    ("12345", "67890"): {"lat": 31.5497, "lon": 74.3436, "area": "Gulberg, Lahore"},
    
    # Add more locations here as you discover them
}

# ==========================================
# PRE-DEFINED LOCATION SHORTCUTS
# These markers will always show on the map
# ==========================================
LOCATION_SHORTCUTS = [
    {"name": "📍 Saddar, Karachi", "lat": 24.8607, "lon": 67.0011, "color": "red"},
    {"name": "📍 Defence, Karachi", "lat": 24.8510, "lon": 67.0350, "color": "orange"},
    {"name": "📍 Blue Area, Islamabad", "lat": 33.6844, "lon": 73.0479, "color": "green"},
    {"name": "📍 Gulberg, Lahore", "lat": 31.5497, "lon": 74.3436, "color": "blue"},
    {"name": "📍 DHA, Karachi", "lat": 24.8250, "lon": 67.0700, "color": "purple"},
    {"name": "📍 Clifton, Karachi", "lat": 24.8150, "lon": 67.0350, "color": "cyan"},
]

def get_cell_location(lac, cell_id):
    key = (str(lac), str(cell_id))
    if key in CELL_LOCATIONS:
        return CELL_LOCATIONS[key]
    return {"lat": 30.3753, "lon": 69.3451, "area": "Unknown"}

def parse_imsi_line(line):
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
    
    operators = {'06': 'Telenor', '04': 'Zong', '03': 'Ufone', '01': 'Jazz', '07': 'Jazz'}
    operator = operators.get(mnc, 'Unknown')
    
    parts = [p.strip() for p in line.split(';')]
    lac, cell_id = None, None
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

threading.Thread(target=monitor_imsi_file, daemon=True).start()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_clients.add(websocket)
    
    await websocket.send_json({
        'type': 'initial',
        'stats': {
            'total_locations': len(current_locations),
            'unique_devices': len(total_devices),
            'operators': dict(operator_counts)
        },
        'locations': current_locations[-100:],
        'shortcuts': LOCATION_SHORTCUTS
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
        <title>IMSI Heatmap with Location Shortcuts</title>
        <meta charset="utf-8">
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <script src="https://unpkg.com/leaflet.heat@0.2.0/dist/leaflet-heat.js"></script>
        <style>
            body { margin: 0; font-family: 'Segoe UI', sans-serif; }
            #map { height: 100vh; width: 100%; }
            
            .sidebar {
                position: absolute;
                top: 20px;
                right: 20px;
                background: rgba(0,0,0,0.85);
                color: white;
                padding: 15px;
                border-radius: 12px;
                z-index: 1000;
                width: 260px;
                backdrop-filter: blur(10px);
                border-right: 3px solid #00ff00;
                max-height: 80vh;
                overflow-y: auto;
            }
            
            .sidebar h3 {
                margin: 0 0 10px 0;
                color: #00ff00;
                font-size: 16px;
            }
            
            .location-btn {
                width: 100%;
                padding: 10px;
                margin: 5px 0;
                background: #333;
                border: none;
                color: white;
                border-radius: 6px;
                cursor: pointer;
                text-align: left;
                font-size: 14px;
                transition: all 0.2s;
            }
            
            .location-btn:hover {
                background: #555;
                transform: translateX(-5px);
            }
            
            .stats-panel {
                position: absolute;
                bottom: 20px;
                left: 20px;
                background: rgba(0,0,0,0.8);
                color: white;
                padding: 12px;
                border-radius: 8px;
                z-index: 1000;
                font-size: 12px;
                min-width: 200px;
            }
            
            .live-badge {
                position: absolute;
                top: 20px;
                left: 20px;
                background: #ff0000;
                color: white;
                padding: 5px 12px;
                border-radius: 20px;
                font-size: 12px;
                font-weight: bold;
                z-index: 1000;
                animation: pulse 1s infinite;
            }
            
            @keyframes pulse {
                0% { opacity: 1; }
                50% { opacity: 0.6; }
                100% { opacity: 1; }
            }
            
            .operator-color {
                display: inline-block;
                width: 10px;
                height: 10px;
                border-radius: 50%;
                margin-right: 5px;
            }
        </style>
    </head>
    <body>
        <div id="map"></div>
        <div class="live-badge">🔴 LIVE</div>
        
        <div class="sidebar">
            <h3>📍 QUICK LOCATIONS</h3>
            <div id="location-buttons"></div>
            <hr style="margin: 10px 0;">
            <div id="area-stats"></div>
        </div>
        
        <div class="stats-panel" id="stats-panel">
            Loading...
        </div>
        
        <script>
            var map = L.map('map').setView([30.3753, 69.3451], 6);
            L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
                attribution: '&copy; OpenStreetMap',
                subdomains: 'abcd'
            }).addTo(map);
            
            var heatLayer;
            var markers = {};
            var shortcuts = [];
            
            var ws = new WebSocket(`ws://${window.location.host}/ws`);
            
            ws.onmessage = function(event) {
                var data = JSON.parse(event.data);
                
                if (data.type === 'initial') {
                    shortcuts = data.shortcuts;
                    updateStats(data.stats);
                    updateHeatmap(data.locations);
                    addLocationButtons(data.shortcuts);
                } else if (data.type === 'new_imsi') {
                    updateStats(data.stats);
                    addToHeatmap(data.data);
                }
            };
            
            function updateStats(stats) {
                var operatorsHtml = '';
                var colors = {'Telenor': '#800080', 'Zong': '#ff4444', 'Ufone': '#ffaa00', 'Jazz': '#4444ff'};
                for (var [op, count] of Object.entries(stats.operators)) {
                    var color = colors[op] || '#888';
                    operatorsHtml += `<div><span class="operator-color" style="background: ${color}"></span>${op}: ${count}</div>`;
                }
                
                document.getElementById('stats-panel').innerHTML = `
                    📱 <strong>Devices:</strong> ${stats.unique_devices || 0}<br>
                    📊 <strong>Operators:</strong><br>${operatorsHtml}
                `;
            }
            
            function updateHeatmap(locations) {
                var points = locations.map(l => [l.lat, l.lon, 1]);
                if (heatLayer) map.removeLayer(heatLayer);
                heatLayer = L.heatLayer(points, {
                    radius: 25,
                    blur: 15,
                    gradient: {0.2: 'blue', 0.4: 'cyan', 0.6: 'lime', 0.8: 'yellow', 1.0: 'red'}
                }).addTo(map);
            }
            
            function addToHeatmap(data) {
                var points = [[data.lat, data.lon, 1]];
                if (heatLayer) {
                    heatLayer.addLatLngs(points);
                } else {
                    heatLayer = L.heatLayer(points, {radius: 25}).addTo(map);
                }
            }
            
            function addLocationButtons(locations) {
                var container = document.getElementById('location-buttons');
                container.innerHTML = '';
                
                locations.forEach(function(loc) {
                    var btn = document.createElement('button');
                    btn.className = 'location-btn';
                    btn.innerHTML = `📍 ${loc.name}`;
                    btn.onclick = function() {
                        map.setView([loc.lat, loc.lon], 14);
                        
                        // Add a temporary marker
                        L.marker([loc.lat, loc.lon])
                            .bindPopup(`<b>${loc.name}</b><br>Click to view IMSI data`)
                            .addTo(map)
                            .openPopup();
                        
                        // Show area stats
                        fetch(`/api/area/${loc.lat}/${loc.lon}`)
                            .then(r => r.json())
                            .then(data => {
                                document.getElementById('area-stats').innerHTML = `
                                    <strong>📍 ${loc.name}</strong><br>
                                    Devices: ${data.devices}<br>
                                    Operators: ${Object.entries(data.operators).map(([k,v]) => `${k}:${v}`).join(', ')}
                                `;
                            });
                    };
                    container.appendChild(btn);
                });
            }
            
            // Add a custom marker for each location shortcut
            function addMarkers() {
                shortcuts.forEach(function(loc) {
                    var marker = L.marker([loc.lat, loc.lon])
                        .bindPopup(`<b>${loc.name}</b><br>Click to see IMSI data in this area`)
                        .addTo(map);
                    markers[loc.name] = marker;
                });
            }
            
            // Call after shortcuts are loaded
            setTimeout(() => {
                if (shortcuts.length) addMarkers();
            }, 2000);
        </script>
    </body>
    </html>
    """)

@app.get("/api/area/{lat}/{lon}")
async def get_area_stats(lat: float, lon: float, radius: float = 5.0):
    """Get IMSI stats for a specific area"""
    area_devices = []
    for loc in current_locations:
        # Calculate distance (simple approximation)
        dist = ((loc['lat'] - lat)**2 + (loc['lon'] - lon)**2)**0.5
        if dist < radius:
            area_devices.append(loc)
    
    area_operators = defaultdict(int)
    for d in area_devices:
        area_operators[d['operator']] += 1
    
    return {
        'devices': len(area_devices),
        'operators': dict(area_operators),
        'radius_km': radius
    }

if __name__ == "__main__":
    import uvicorn
    print("\n" + "="*60)
    print("📍 IMSI HEATMAP WITH LOCATION SHORTCUTS")
    print("="*60)
    print("\n🌐 Open: http://localhost:8000")
    print("📡 Watching: imsi_output.txt")
    print("\n📍 Location shortcuts on the right sidebar")
    print("   Click any location to zoom in")
    print("\nPress Ctrl+C to stop\n")
    uvicorn.run(app, host="0.0.0.0", port=8000)
