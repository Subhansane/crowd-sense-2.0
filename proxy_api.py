#!/usr/bin/env python3
"""
Proxy API Server - Runs on your Ubuntu
Friend connects here, you fetch from InfinityFree
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
import json
from datetime import datetime

app = Flask(__name__)
CORS(app)  # Allow your friend to connect

# Headers that work
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'application/json',
}

INFINITY_URL = "http://subhanscode.xo.je/imsi_api.php"

@app.route('/')
def home():
    return jsonify({
        'name': 'IMSI Proxy API',
        'status': 'online',
        'endpoints': {
            '/stats': 'Get statistics',
            '/recent?limit=20': 'Get recent detections',
            '/operators': 'Get operator breakdown',
            '/live': 'Live streaming endpoint'
        }
    })

@app.route('/stats')
def get_stats():
    """Get statistics from InfinityFree"""
    try:
        r = requests.get(f"{INFINITY_URL}?action=stats", headers=HEADERS, timeout=10)
        return jsonify(r.json())
    except:
        return jsonify({'error': 'Could not fetch stats', 'data': []})

@app.route('/recent')
def get_recent():
    """Get recent detections"""
    limit = request.args.get('limit', 20)
    try:
        r = requests.get(f"{INFINITY_URL}?action=recent&limit={limit}", headers=HEADERS, timeout=10)
        return jsonify(r.json())
    except:
        return jsonify({'error': 'Could not fetch recent', 'data': []})

@app.route('/operators')
def get_operators():
    """Get operator breakdown"""
    try:
        r = requests.get(f"{INFINITY_URL}?action=operators", headers=HEADERS, timeout=10)
        return jsonify(r.json())
    except:
        return jsonify({'error': 'Could not fetch operators', 'data': []})

@app.route('/live')
def live_stream():
    """Server-sent events for live data"""
    def generate():
        last_id = 0
        while True:
            try:
                r = requests.get(f"{INFINITY_URL}?action=recent&limit=10", headers=HEADERS, timeout=5)
                data = r.json()
                
                if data.get('success') and 'data' in data:
                    for item in data['data']:
                        if item['id'] > last_id:
                            last_id = item['id']
                            yield f"data: {json.dumps(item)}\n\n"
            except:
                pass
            time.sleep(3)
    
    return app.response_class(generate(), mimetype='text/event-stream')

if __name__ == '__main__':
    print("="*60)
    print("🚀 IMSI Proxy API Server")
    print("="*60)
    
    # Get your IP
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    ip = s.getsockname()[0]
    s.close()
    
    print(f"\n📡 Server running at:")
    print(f"   Local:  http://localhost:5000")
    print(f"   Network: http://{ip}:5000")
    print(f"\n🔗 Share with friend:")
    print(f"   http://{ip}:5000")
    print(f"\n📊 Endpoints:")
    print(f"   Stats:     http://{ip}:5000/stats")
    print(f"   Recent:    http://{ip}:5000/recent?limit=20")
    print(f"   Operators: http://{ip}:5000/operators")
    print(f"   Live:      http://{ip}:5000/live")
    print("\n🛑 Press Ctrl+C to stop")
    print("="*60)
    
    app.run(host='0.0.0.0', port=5000, threaded=True)
