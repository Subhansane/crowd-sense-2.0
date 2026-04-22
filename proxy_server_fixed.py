#!/usr/bin/env python3
"""
Fixed Proxy Server - Uses browser-like behavior to access InfinityFree
"""

from flask import Flask, jsonify, request, Response
from flask_cors import CORS
import requests
import time
import json
from datetime import datetime
import random
import socket

app = Flask(__name__)
CORS(app)

# Session that maintains cookies
session = requests.Session()

# Complete browser headers
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
})

INFINITY_URL = "http://subhanscode.xo.je"
API_URL = f"{INFINITY_URL}/imsi_api.php"

# First, visit the main site to get cookies
try:
    print("🌐 Initializing browser session...")
    session.get(INFINITY_URL, timeout=10)
    print("✅ Session initialized with cookies")
except Exception as e:
    print(f"⚠️ Session init warning: {e}")

def fetch_from_infinity(action, **params):
    """Fetch data with browser-like behavior"""
    try:
        # Build URL
        url = f"{API_URL}?action={action}"
        for key, value in params.items():
            url += f"&{key}={value}"
        
        # Add cache busters
        url += f"&_={int(time.time())}"
        url += f"&r={random.randint(1000, 9999)}"
        
        print(f"📡 Fetching: {url}")
        
        # Add random delay to mimic human behavior
        time.sleep(random.uniform(0.5, 1.5))
        
        # Make request with session (maintains cookies)
        response = session.get(
            url,
            timeout=15,
            allow_redirects=True
        )
        
        print(f"📊 Status: {response.status_code}")
        print(f"📋 Content-Type: {response.headers.get('Content-Type', 'unknown')}")
        
        if response.status_code == 200:
            # Try to parse JSON
            try:
                data = response.json()
                return data
            except:
                # If not JSON, might be the protection page
                if "aes.js" in response.text:
                    print("⚠️ Protection page detected, retrying with different headers...")
                    # Try with different headers
                    alt_headers = {
                        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
                        'Accept': 'application/json',
                    }
                    alt_response = requests.get(url, headers=alt_headers, timeout=10)
                    if alt_response.status_code == 200:
                        try:
                            return alt_response.json()
                        except:
                            pass
                
                return {"error": "Invalid response", "data": []}
        else:
            return {"error": f"HTTP {response.status_code}", "data": []}
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return {"error": str(e), "data": []}

@app.route('/')
def home():
    return jsonify({
        'name': 'IMSI Proxy (Fixed)',
        'status': 'online',
        'server_time': datetime.now().isoformat(),
        'endpoints': {
            '/stats': 'Get statistics',
            '/recent': 'Get recent detections',
            '/operators': 'Get operator breakdown'
        }
    })

@app.route('/stats')
def get_stats():
    """Get statistics"""
    data = fetch_from_infinity('stats')
    if 'error' not in data:
        return jsonify(data)
    return jsonify({'total_devices': 0, 'operators': [], 'timestamp': datetime.now().isoformat()})

@app.route('/recent')
def get_recent():
    """Get recent detections"""
    limit = request.args.get('limit', 20)
    data = fetch_from_infinity('recent', limit=limit)
    if 'error' not in data:
        return jsonify(data)
    return jsonify({'success': True, 'count': 0, 'data': []})

@app.route('/operators')
def get_operators():
    """Get operator breakdown"""
    data = fetch_from_infinity('operators')
    if 'error' not in data:
        return jsonify(data)
    return jsonify({'operators': []})

@app.route('/live')
def live_stream():
    """Server-sent events stream"""
    def generate():
        last_id = 0
        while True:
            data = fetch_from_infinity('recent', limit=10)
            if 'data' in data:
                for item in data['data']:
                    if item.get('id', 0) > last_id:
                        last_id = item['id']
                        yield f"data: {json.dumps(item)}\n\n"
            time.sleep(5)
    
    return Response(generate(), mimetype='text/event-stream')

if __name__ == '__main__':
    print("="*60)
    print("🚀 FIXED IMSI PROXY SERVER")
    print("="*60)
    
    # Get IP
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    
    print(f"\n📡 Server running at:")
    print(f"   Local:  http://localhost:5000")
    print(f"   Network: http://{local_ip}:5000")
    print(f"\n🔗 Share with friend:")
    print(f"   http://{local_ip}:5000")
    print(f"\n📊 Test endpoints:")
    print(f"   http://{local_ip}:5000/stats")
    print(f"   http://{local_ip}:5000/recent?limit=10")
    print(f"   http://{local_ip}:5000/operators")
    print("\n🛑 Press Ctrl+C to stop")
    print("="*60)
    
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
