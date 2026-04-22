#!/usr/bin/env python3
"""
Real-Time IMSI Heatmap - Shows ONLY CURRENT DATA (Last 5 minutes)
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import asyncio
import json
import os
import re
import time
from datetime import datetime, timedelta
from collections import defaultdict
import threading

app = FastAPI(title="Live IMSI Heatmap - Current Only")

connected_clients = set()
last_position = 0
current_locations = []  # Now stores only recent data
operator_counts = defaultdict(int)
total_devices = set()

# ==========================================
# CONFIGURATION
# ==========================================
MAX_AGE_SECONDS = 300  # Only show data from last 5 minutes
CLEANUP_INTERVAL = 10  # Clean old data every 10 seconds

# ==========================================
# YOUR LOCATION
# ==========================================
YOUR_LOCATION = {"lat": 33.573864, "lon": 73.065655, "name": "📍 Your Location"}

# ==========================================
# CELL TOWER LOCATIONS (Update with actual towers near you)
# ==========================================
CELL_LOCATIONS = {
    ("359", "12911"): {"lat": 33.573864, "lon": 73.065655, "area": "Near You"},
}

def get_cell_location(lac, cell_id):
    key = (str(lac), str(cell_id))
    if key in CELL_LOCATIONS:
        return CELL_LOCATIONS[key]
    return {"lat": YOUR_LOCATION["lat"], "lon": YOUR_LOCATION["lon"], "area": "Unknown"}

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
        'timestamp': timestamp,
        'capture_time': datetime.now()
    }

def cleanup_old_data():
    """Remove data older than MAX_AGE_SECONDS"""
    global current_locations, operator_counts, total_devices
    now = datetime.now()
    cutoff = now - timedelta(seconds=MAX_AGE_SECONDS)
    
    # Keep only recent data
    old_count = len(current_locations)
    current_locations = [loc for loc in current_locations if loc['capture_time'] > cutoff]
    removed = old_count - len(current_locations)
    
    if removed > 0:
        # Recalculate statistics from remaining data
        operator_counts.clear()
        total_devices.clear()
        for loc in current_locations:
            operator_counts[loc['operator']] += 1
            total_devices.add(loc['imsi'])
        
        # Notify clients of update
        broadcast_data = {
            'type': 'refresh',
            'stats': {
                'total_locations': len(current_locations),
                'unique_devices': len(total_devices),
                'operators': dict(operator_counts)
            },
            'locations': [{'lat': l['lat'], 'lon': l['lon'], 'operator': l['operator']} 
                         for l in current_locations[-100:]]
        }
        
        for client in connected_clients.copy():
            try:
                asyncio.run_coroutine_threadsafe(
                    client.send_json(broadcast_data),
                    asyncio.get_event_loop()
                )
            except:
                pass

def monitor_imsi_file():
    global last_position, current_locations, operator_counts, total_devices
    imsi_file = "imsi_output.txt"
    if not os.path.exists(imsi_file):
        open(imsi_file, 'a').close()
    
    last_cleanup = time.time()
    
    while True:
        try:
            # Cleanup old data periodically
            if time.time() - last_cleanup > CLEANUP_INTERVAL:
                cleanup_old_data()
                last_cleanup = time.time()
            
            # Read new data
            with open(imsi_file, 'r') as f:
                f.seek(last_position)
                new_lines = f.readlines()
                last_position = f.tell()
                
                for line in new_lines:
                    data = parse_imsi_line(line)
                    if data:
                        current_locations.append(data)
                        operator_counts[data['operator']] += 1
                        total_devices.add(data['imsi'])
                        
                        broadcast_data = {
                            'type': 'new_imsi',
                            'data': {
                                'lat': data['lat'],
                                'lon': data['lon'],
                                'operator': data['operator'],
                                'display_imsi': data['display_imsi'],
                                'timestamp': data['timestamp']
                            },
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
    
    # Send only current data
    await websocket.send_json({
        'type': 'initial',
        'stats': {
            'total_locations': len(current_locations),
            'unique_devices': len(total_devices),
            'operators': dict(operator_counts)
        },
        'locations': [{'lat': l['lat'], 'lon': l['lon'], 'operator': l['operator']} 
                      for l in current_locations[-100:]]
    })
    
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        connected_clients.remove(websocket)

@app.get("/")
async def get_page():
    return HTMLResponse(f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Live IMSI Heatmap - Current Data Only</title>
        <meta charset="utf-8">
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <script src="https://unpkg.com/leaflet.heat@0.2.0/dist/leaflet-heat.js"></script>
        <style>
            body {{ margin: 0; font-family: 'Segoe UI', sans-serif; }}
            #map {{ height: 100vh; width: 100%; }}
            .sidebar {{
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
            }}
            .stats-panel {{
                position: absolute;
                bottom: 20px;
                left: 20px;
                background: rgba(0,0,0,0.8);
                color: white;
                padding: 12px;
                border-radius: 8px;
                z-index: 1000;
                font-size: 12px;
                min-width: 220px;
            }}
            .live-badge {{
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
            }}
            .age-badge {{
                position: absolute;
                top: 20px;
                left: 120px;
                background: #ff9900;
                color: white;
                padding: 5px 12px;
                border-radius: 20px;
                font-size: 12px;
                font-weight: bold;
                z-index: 1000;
            }}
            @keyframes pulse {{
                0% {{ opacity: 1; }}
                50% {{ opacity: 0.6; }}
                100% {{ opacity: 1; }}
            }}
            .operator-color {{
                display: inline-block;
                width: 10px;
                height: 10px;
                border-radius: 50%;
                margin-right: 5px;
            }}
        </style>
    </head>
    <body>
        <div id="map"></div>
        <div class="live-badge">🔴 LIVE</div>
        <div class="age-badge">⏱️ LAST 5 MIN ONLY</div>
        
        <div class="sidebar">
            <h3>📍 YOUR LOCATION</h3>
            <button id="gotoLocation" style="width:100%; padding:8px; background:#2a6f4f; border:none; color:white; border-radius:5px; cursor:pointer;">🎯 Go to My Location</button>
            <hr>
            <div id="info">Loading...</div>
        </div>
        
        <div class="stats-panel" id="stats-panel">
            Loading...
        </div>
        
        <script>
            var map = L.map('map').setView([33.573864, 73.065655], 14);
            L.tileLayer('https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}{{r}}.png', {{
                attribution: '&copy; OpenStreetMap',
                subdomains: 'abcd'
            }}).addTo(map);
            
            var heatLayer;
            var myMarker;
            var ws = new WebSocket(`ws://${{window.location.host}}/ws`);
            
            ws.onmessage = function(event) {{
                var data = JSON.parse(event.data);
                
                if (data.type === 'initial' || data.type === 'refresh') {{
                    updateStats(data.stats);
                    updateHeatmap(data.locations);
                }} else if (data.type === 'new_imsi') {{
                    updateStats(data.stats);
                    addToHeatmap(data.data);
                }}
            }};
            
            function updateStats(stats) {{
                var operatorsHtml = '';
                var colors = {{'Telenor': '#800080', 'Zong': '#ff4444', 'Ufone': '#ffaa00', 'Jazz': '#4444ff'}};
                for (var [op, count] of Object.entries(stats.operators)) {{
                    var color = colors[op] || '#888';
                    operatorsHtml += `<div><span class="operator-color" style="background: ${{color}}"></span>${{op}}: ${{count}}</div>`;
                }}
                
                document.getElementById('stats-panel').innerHTML = `
                    ⏱️ <strong>Current (Last 5 min)</strong><br>
                    📱 <strong>Devices:</strong> ${{stats.unique_devices || 0}}<br>
                    📊 <strong>Operators:</strong><br>${{operatorsHtml}}
                `;
                
                document.getElementById('info').innerHTML = `
                    📍 Lat: 33.573864<br>
                    Lon: 73.065655<br>
                    <span style="color:#aaa">Active detections: ${{stats.total_locations || 0}}</span>
                `;
            }}
            
            function updateHeatmap(locations) {{
                var points = locations.map(l => [l.lat, l.lon, 1]);
                if (heatLayer) map.removeLayer(heatLayer);
                heatLayer = L.heatLayer(points, {{
                    radius: 25,
                    blur: 15,
                    gradient: {{0.2: 'blue', 0.4: 'cyan', 0.6: 'lime', 0.8: 'yellow', 1.0: 'red'}}
                }}).addTo(map);
            }}
            
            function addToHeatmap(data) {{
                if (heatLayer) {{
                    heatLayer.addLatLngs([[data.lat, data.lon, 1]]);
                }}
            }}
            
            document.getElementById('gotoLocation').onclick = function() {{
                map.setView([33.573864, 73.065655], 16);
                if (!myMarker) {{
                    myMarker = L.marker([33.573864, 73.065655])
                        .bindPopup('<b>📍 Your Location</b>')
                        .addTo(map);
                }}
                myMarker.openPopup();
            }};
        </script>
    </body>
    </html>
    """)

if __name__ == "__main__":
    import uvicorn
    print("\n" + "="*60)
    print("📍 LIVE IMSI HEATMAP - CURRENT DATA ONLY")
    print("="*60)
    print("\n⏱️  ONLY showing data from LAST 5 MINUTES")
    print("🗑️  Old data automatically removed every 10 seconds")
    print(f"\n🎯 Your Location: {YOUR_LOCATION['lat']}, {YOUR_LOCATION['lon']}")
    print("\n🌐 Open: http://localhost:8000")
    print("📡 Watching: imsi_output.txt")
    print("\nPress Ctrl+C to stop\n")
    uvicorn.run(app, host="0.0.0.0", port=8000)
