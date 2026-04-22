#!/usr/bin/env python3
"""
Robust IMSI Monitor - Handles various response types
"""

import requests
import time
import json
from datetime import datetime

API_URL = "http://subhanscode.xo.je/imsi_api.php"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
    'Accept': 'application/json, text/plain, */*'
}

def fetch_data(endpoint=""):
    """Fetch data with proper error handling"""
    try:
        url = f"{API_URL}{endpoint}"
        print(f"📡 Fetching: {url}")
        
        response = requests.get(url, headers=HEADERS, timeout=15)
        print(f"Status: {response.status_code}")
        print(f"Content-Type: {response.headers.get('Content-Type', 'unknown')}")
        
        if response.status_code == 200:
            # Try to parse as JSON
            try:
                data = response.json()
                print("✅ Valid JSON received")
                return data
            except json.JSONDecodeError as e:
                print(f"❌ JSON decode error: {e}")
                print(f"Raw response (first 200 chars): {response.text[:200]}")
                return None
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            return None
            
    except requests.exceptions.Timeout:
        print("❌ Timeout")
        return None
    except requests.exceptions.ConnectionError:
        print("❌ Connection error")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

# Test each endpoint
print("="*60)
print("📡 TESTING API ENDPOINTS")
print("="*60)

endpoints = [
    "",
    "?action=stats",
    "?action=recent&limit=5",
    "?action=operators"
]

for endpoint in endpoints:
    print(f"\n🔍 Testing: {API_URL}{endpoint}")
    data = fetch_data(endpoint)
    if data:
        print(f"✅ Success! Data keys: {list(data.keys())}")
        print(f"Preview: {str(data)[:200]}")
    print("-"*40)
    time.sleep(1)

print("\n✅ Test complete")
