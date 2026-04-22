#!/usr/bin/env python3
"""
Fixed Real-Time IMSI Monitor
"""

import requests
import time
import os
from datetime import datetime
import json

# Configuration
API_URL = "http://subhanscode.xo.je/imsi_api.php"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:89.0) Gecko/20100101 Firefox/89.0',
    'Accept': 'application/json'
}

print("="*60)
print("📡 REAL-TIME IMSI MONITOR (FIXED)")
print("="*60)
print(f"API URL: {API_URL}")
print("="*60)

def test_api():
    """Test if API is accessible"""
    try:
        response = requests.get(API_URL, headers=HEADERS, timeout=10)
        print(f"✅ API Response: {response.status_code}")
        print(f"📊 Data: {response.json()}")
        return True
    except Exception as e:
        print(f"❌ API Test Failed: {e}")
        return False

# Test connection first
if not test_api():
    print("\n⚠️  API not accessible. Check:")
    print("1. Your internet connection")
    print("2. The URL: http://subhanscode.xo.je/imsi_api.php")
    print("3. If the website is online")
    exit(1)

print("\n🔄 Starting monitor...\n")

last_id = 0
total = 0

try:
    while True:
        try:
            # Add headers and timeout
            response = requests.get(
                f"{API_URL}?action=recent&limit=50",
                headers=HEADERS,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('success') and 'data' in data:
                    records = data['data']
                    
                    for record in records:
                        if record.get('id', 0) > last_id:
                            last_id = record['id']
                            total += 1
                            
                            timestamp = record.get('timestamp', '')[:19]
                            operator = record.get('operator', 'Unknown')
                            imsi = record.get('imsi', '')[-8:]
                            
                            # Color coding
                            colors = {
                                'Telenor': '\033[95m',
                                'Zong': '\033[91m',
                                'Ufone': '\033[93m',
                                'Jazz': '\033[94m'
                            }
                            reset = '\033[0m'
                            color = colors.get(operator, '\033[90m')
                            
                            print(f"{color}[{timestamp}] {operator}: ...{imsi}{reset}")
                
                # Show stats every 10 seconds
                if int(time.time()) % 10 == 0:
                    print(f"\n📊 Total IMSIs: {total} | Last ID: {last_id}\n")
            
            time.sleep(3)
            
        except requests.exceptions.Timeout:
            print("⏳ Timeout, retrying...")
            time.sleep(5)
        except requests.exceptions.ConnectionError:
            print("🔌 Connection error, retrying...")
            time.sleep(5)
        except Exception as e:
            print(f"⚠️ Error: {e}")
            time.sleep(5)
            
except KeyboardInterrupt:
    print(f"\n\n👋 Monitoring stopped")
    print(f"📊 Final count: {total} IMSIs")
