#!/usr/bin/env python3
"""
Real-time monitor for ALL IMSI data
"""

import requests
import time
import os
from datetime import datetime

API_URL = "http://subhanscode.xo.je/imsi_api.php"
LAST_ID_FILE = "last_id.txt"

def get_last_id():
    """Get last processed ID"""
    if os.path.exists(LAST_ID_FILE):
        with open(LAST_ID_FILE, 'r') as f:
            return int(f.read().strip())
    return 0

def save_last_id(last_id):
    """Save last processed ID"""
    with open(LAST_ID_FILE, 'w') as f:
        f.write(str(last_id))

def fetch_new_data(last_id):
    """Fetch new data since last ID"""
    response = requests.get(f"{API_URL}?action=recent&limit=1000")
    if response.status_code == 200:
        data = response.json()
        if data.get('success'):
            records = data.get('data', [])
            # Filter records newer than last_id
            new_records = [r for r in records if r.get('id', 0) > last_id]
            return new_records
    return []

def main():
    print("="*80)
    print("🔄 REAL-TIME IMSI DATA MONITOR")
    print("="*80)
    print("Watching for new IMSI data...\n")
    
    last_id = get_last_id()
    total_seen = 0
    
    try:
        while True:
            new_data = fetch_new_data(last_id)
            
            if new_data:
                for record in new_data:
                    total_seen += 1
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] "
                          f"#{record['id']} - {record['operator']}: "
                          f"{record['imsi']}")
                    
                    if record['id'] > last_id:
                        last_id = record['id']
                
                save_last_id(last_id)
                print(f"\n📊 Total records seen: {total_seen}\n")
            
            time.sleep(5)
            
    except KeyboardInterrupt:
        print("\n\n👋 Monitoring stopped")
        print(f"📊 Final count: {total_seen} records")

if __name__ == "__main__":
    main()
