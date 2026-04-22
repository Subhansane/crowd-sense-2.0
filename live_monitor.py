#!/usr/bin/env python3
"""
Live IMSI Monitor - Updates in real-time
"""

import requests
import time
import os
from datetime import datetime

API_URL = "http://192.168.18.38:5000"

def clear_screen():
    os.system('clear' if os.name == 'posix' else 'cls')

def fetch_data():
    try:
        recent = requests.get(f"{API_URL}/recent?limit=20", timeout=3).json()
        stats = requests.get(f"{API_URL}/stats", timeout=3).json()
        return recent, stats
    except:
        return None, None

print("🚀 Live IMSI Monitor - Press Ctrl+C to stop")
time.sleep(2)

last_id = 0
while True:
    try:
        clear_screen()
        print("="*60)
        print(f"📡 LIVE IMSI MONITOR - {datetime.now().strftime('%H:%M:%S')}")
        print("="*60)
        
        recent, stats = fetch_data()
        
        if stats:
            print(f"\n📊 Total Devices: {stats.get('total_devices', 0)}")
            
        if recent and 'data' in recent:
            print(f"\n🕐 Recent Detections:")
            for item in recent['data']:
                if item['id'] > last_id:
                    last_id = item['id']
                    ts = item['timestamp'][:19]
                    op = item['operator']
                    imsi = item['imsi'][-8:]
                    print(f"  [{ts}] {op}: ...{imsi}")
        
        print(f"\n{'='*60}")
        print(f"🔄 Refreshing... (Last ID: {last_id})")
        time.sleep(5)
        
    except KeyboardInterrupt:
        print("\n\n👋 Monitor stopped")
        break
    except Exception as e:
        print(f"⚠️ Error: {e}")
        time.sleep(5)
