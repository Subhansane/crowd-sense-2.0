#!/usr/bin/env python3
"""
Real-Time IMSI Heatmap with Custom Location
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

app = FastAPI(title="IMSI Heatmap")

connected_clients = set()
last_position = 0
current_locations = []
operator_counts = defaultdict(int)
total_devices = set()

# ==========================================
# YOUR LOCATION SHORTCUT (33.57386401733251, 73.0656552804851)
# ==========================================
YOUR_LOCATION = {"lat": 33.573864, "lon": 73.065655, "name": "📍 Your Location"}

# ==========================================
# CELL TOWER LOCATIONS (Update with actual towers near you)
# ==========================================
CELL_LOCATIONS = {
    # Add cell towers near your location here
    ("359", "12911"): {"lat": 33.573864, "lon": 73.065655, "area": "Near You"},
    ("359", "12913"): {"lat": 33.575000, "lon": 73.068000, "area": "Nearby Area 1"},
    ("359", "12914"): {"lat": 33.572000, "lon": 73.063000, "area": "Nearby Area 2"},
}

def get_cell_location(lac, cell_id):
    """Get GPS coordinates for cell tower"""
    key = (str(lac), str(cell_id))
    if key in CELL_LOCATIONS:
        return CELL_LOCATIONS[key]
    # Default: return your location if unknown
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
        'your_location': YOUR_LOCATION
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
        <title>IMSI Heatmap - Your Location</title>
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
                border-right: 3px solid #00ff00;
            }}
            .location-btn {{
                width: 100%;
                padding: 12px;
                margin: 8px 0;
                background: #2a6f4f;
                border: none;
                color: white;
                border-radius: 8px;
                cursor: pointer;
                font-size: 14px;
                font-weight: bold;
                transition: all 0.2s;
            }}
            .location-btn:hover {{
                background: #1e8a5e;
                transform: translateX(-5px);
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
                min-width: 200px;
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
        
        <div class="sidebar">
            <h3>📍 QUICK LOCATION</h3>
            <button class="location-btn" id="gotoMyLocation">🎯 Go to My Location</button>
            <hr style="margin: 10px 0;">
            <div id="location-info"></div>
        </div>
        
        <div class="stats-panel" id="stats-panel">
            Loading...
        </div>
        
        <script>
            var map = L.map('map').setView([33.573864, 73.065655], 15);
            L.tileLayer('https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}{{r}}.png', {{
                attribution: '&copy; OpenStreetMap',
                subdomains: 'abcd'
            }}).addTo(map);
            
            var heatLayer;
            var myMarker;
            var ws = new WebSocket(`ws://${{window.location.host}}/ws`);
            
            ws.onmessage = function(event) {{
                var data = JSON.parse(event.data);
                
                if (data.type === 'initial') {{
                    updateStats(data.stats);
                    updateHeatmap(data.locations);
                    
                    // Add marker for your location
                    if (!myMarker) {{
                        myMarker = L.marker([33.573864, 73.065655])
                            .bindPopup('<b>📍 Your Location</b><br>IMSI Data Center')
                            .addTo(map);
                    }}
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
                    📱 <strong>Devices:</strong> ${{stats.unique_devices || 0}}<br>
                    📊 <strong>Operators:</strong><br>${{operatorsHtml}}
                `;
                
                document.getElementById('location-info').innerHTML = `
                    <strong>📍 Your Location</strong><br>
                    Lat: 33.573864<br>
                    Lon: 73.065655<br>
                    <span style="color:#aaa; font-size:11px">Devices detected near you: ${{stats.total_locations || 0}}</span>
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
            
            document.getElementById('gotoMyLocation').onclick = function() {{
                map.setView([33.573864, 73.065655], 18);
                if (myMarker) {{
                    myMarker.openPopup();
                }}
            }};
        </script>
    </body>
    </html>
    """)

if __name__ == "__main__":
    import uvicorn
    print("\n" + "="*60)
    print("📍 IMSI HEATMAP - YOUR LOCATION")
    print("="*60)
    print(f"\n🎯 Your Location: 33.573864, 73.065655")
    print("\n🌐 Open: http://localhost:8000")
    print("📡 Watching: imsi_output.txt")
    print("\nPress Ctrl+C to stop\n")
    uvicorn.run(app, host="0.0.0.0", port=8000)
