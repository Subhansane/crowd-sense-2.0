#!/usr/bin/env python3
"""
Fixed IMSI Monitor - Bypasses InfinityFree bot protection
Run this to see real-time IMSI data
"""

import requests
import time
from datetime import datetime

# Browser headers to bypass protection
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'en-US,en;q=0.9',
    'Referer': 'http://subhanscode.xo.je/',
    'Origin': 'http://subhanscode.xo.je',
    'Connection': 'keep-alive',
}

API_URL = "http://subhanscode.xo.je/imsi_api.php"

print("="*60)
print("📡 IMSI MONITOR - REAL TIME")
print("="*60)
print(f"API: {API_URL}")
print("Press Ctrl+C to stop\n")
print("-"*60)

def fetch_recent(limit=20):
    """Fetch recent IMSI data"""
    try:
        url = f"{API_URL}?action=recent&limit={limit}"
        response = requests.get(url, headers=HEADERS, timeout=10)
        
        if response.status_code == 200:
            return response.json()
        else:
            return None
    except Exception as e:
        print(f"⚠️ Connection error: {e}")
        return None

# Main loop
last_id = 0
total = 0

try:
    while True:
        data = fetch_recent(50)
        
        if data and data.get('success') and 'data' in data:
            records = data['data']
            
            for record in records:
                record_id = record.get('id', 0)
                if record_id > last_id:
                    last_id = record_id
                    total += 1
                    
                    timestamp = record.get('timestamp', '')[:19]
                    operator = record.get('operator', 'Unknown')
                    imsi = record.get('imsi', '')
                    imsi_short = imsi[-8:] if imsi else 'N/A'
                    
                    print(f"[{timestamp}] {operator}: ...{imsi_short}")
            
            if records:
                print(f"\n📊 Total IMSIs seen: {total}\n")
        
        time.sleep(5)
        
except KeyboardInterrupt:
    print(f"\n\n👋 Monitoring stopped")
    print(f"📊 Final count: {total} IMSIs")
