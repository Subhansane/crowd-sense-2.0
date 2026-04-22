#!/usr/bin/env python3
"""
Real-Time IMSI Heatmap - Strong Colors & Auto-Refresh
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
import random

app = FastAPI(title="Live IMSI Heatmap")

connected_clients = set()
last_position = 0
current_locations = []
operator_counts = defaultdict(int)
total_devices = set()

# ==========================================
# CONFIGURATION
# ==========================================
MAX_AGE_SECONDS = 300  # 5 minutes
CLEANUP_INTERVAL = 10
YOUR_LOCATION = {"lat": 33.573864, "lon": 73.065655, "name": "📍 Your Location"}

# ==========================================
# CELL TOWER LOCATIONS - Add more for better coverage
# ==========================================
CELL_LOCATIONS = {
    ("359", "12911"): {"lat": 33.573864, "lon": 73.065655, "area": "Your Area"},
    ("359", "12913"): {"lat": 33.575000, "lon": 73.068000, "area": "Nearby"},
    ("359", "12914"): {"lat": 33.572000, "lon": 73.063000, "area": "Nearby 2"},
    ("58803", "18176"): {"lat": 33.684400, "lon": 73.047900, "area": "Islamabad"},
    ("12345", "67890"): {"lat": 31.549700, "lon": 74.343600, "area": "Lahore"},
}

def get_cell_location(lac, cell_id):
    key = (str(lac), str(cell_id))
    if key in CELL_LOCATIONS:
        return CELL_LOCATIONS[key]
    # Return random location around your area for unknown cells
    return {"lat": YOUR_LOCATION["lat"] + random.uniform(-0.01, 0.01), 
            "lon": YOUR_LOCATION["lon"] + random.uniform(-0.01, 0.01), 
            "area": "Unknown"}

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
    global current_locations, operator_counts, total_devices
    now = datetime.now()
    cutoff = now - timedelta(seconds=MAX_AGE_SECONDS)
    
    old_count = len(current_locations)
    current_locations = [loc for loc in current_locations if loc['capture_time'] > cutoff]
    
    if old_count != len(current_locations):
        operator_counts.clear()
        total_devices.clear()
        for loc in current_locations:
            operator_counts[loc['operator']] += 1
            total_devices.add(loc['imsi'])
        
        broadcast_data = {
            'type': 'refresh',
            'stats': {
                'total_locations': len(current_locations),
                'unique_devices': len(total_devices),
                'operators': dict(operator_counts)
            },
            'locations': [{'lat': l['lat'], 'lon': l['lon'], 'operator': l['operator'], 'weight': 2} 
                         for l in current_locations]
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
            if time.time() - last_cleanup > CLEANUP_INTERVAL:
                cleanup_old_data()
                last_cleanup = time.time()
            
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
                                'weight': 3  # Higher weight = stronger color
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
                
                time.sleep(1)  # Faster refresh
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
        'locations': [{'lat': l['lat'], 'lon': l['lon'], 'operator': l['operator'], 'weight': 2} 
                      for l in current_locations]
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
        <title>Live IMSI Heatmap</title>
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
            .refresh-badge {{
                position: absolute;
                bottom: 20px;
                right: 20px;
                background: #333;
                color: white;
                padding: 5px 12px;
                border-radius: 20px;
                font-size: 11px;
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
        <div class="refresh-badge">🔄 Auto-refresh every 1s</div>
        
        <div class="sidebar">
            <h3>📍 YOUR LOCATION</h3>
            <button id="gotoLocation" style="width:100%; padding:8px; background:#2a6f4f; border:none; color:white; border-radius:5px; cursor:pointer;">🎯 Go to My Location</button>
            <hr>
            <div id="info"></div>
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
            var allPoints = [];
            
            var ws = new WebSocket(`ws://${{window.location.host}}/ws`);
            
            ws.onmessage = function(event) {{
                var data = JSON.parse(event.data);
                
                if (data.type === 'initial' || data.type === 'refresh') {{
                    updateStats(data.stats);
                    allPoints = data.locations.map(l => [l.lat, l.lon, l.weight || 1]);
                    updateHeatmap();
                }} else if (data.type === 'new_imsi') {{
                    updateStats(data.stats);
                    allPoints.push([data.data.lat, data.data.lon, data.data.weight || 2]);
                    updateHeatmap();
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
                    ⏱️ <strong>Current Activity (Last 5 min)</strong><br>
                    📱 <strong>Active Devices:</strong> ${{stats.unique_devices || 0}}<br>
                    📊 <strong>Detections:</strong> ${{stats.total_locations || 0}}<br>
                    📡 <strong>Operators:</strong><br>${{operatorsHtml}}
                `;
                
                document.getElementById('info').innerHTML = `
                    📍 <strong>Your Location</strong><br>
                    Lat: 33.573864<br>
                    Lon: 73.065655<br>
                    <span style="color:#0f0">🎯 Click button to zoom</span>
                `;
            }}
            
            function updateHeatmap() {{
                if (heatLayer) map.removeLayer(heatLayer);
                
                // Stronger gradient for better visibility
                heatLayer = L.heatLayer(allPoints, {{
                    radius: 30,
                    blur: 20,
                    maxZoom: 18,
                    minOpacity: 0.4,
                    gradient: {{
                        0.0: 'blue',
                        0.3: 'cyan',
                        0.5: 'lime',
                        0.7: 'yellow',
                        1.0: 'red'
                    }}
                }}).addTo(map);
            }}
            
            document.getElementById('gotoLocation').onclick = function() {{
                map.setView([33.573864, 73.065655], 16);
                if (!myMarker) {{
                    myMarker = L.marker([33.573864, 73.065655])
                        .bindPopup('<b>📍 Your Location</b><br>IMSI Data Center')
                        .addTo(map);
                }}
                myMarker.openPopup();
            }};
            
            // Force refresh every 2 seconds
            setInterval(function() {{
                if (heatLayer) {{
                    // Subtle animation to show it's alive
                    document.querySelector('.live-badge').style.opacity = '0.7';
                    setTimeout(() => {{
                        document.querySelector('.live-badge').style.opacity = '1';
                    }}, 200);
                }}
            }}, 2000);
        </script>
    </body>
    </html>
    """)

if __name__ == "__main__":
    import uvicorn
    print("\n" + "="*60)
    print("🔥 LIVE IMSI HEATMAP - STRONG COLORS")
    print("="*60)
    print("\n📡 Watching: imsi_output.txt")
    print("🎨 Heatmap colors: Blue → Cyan → Green → Yellow → Red")
    print("🔴 Red spots = High activity | 🔵 Blue = Low activity")
    print("\n🌐 Open: http://localhost:8000")
    print("\nPress Ctrl+C to stop\n")
    uvicorn.run(app, host="0.0.0.0", port=8000)
