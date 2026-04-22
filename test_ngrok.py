#!/usr/bin/env python3
import requests

API_URL = "https://endlessly-ungirlish-kandy.ngrok-free.dev"
headers = {'ngrok-skip-browser-warning': 'true'}

print("📡 Testing ngrok connection...")
try:
    stats = requests.get(f"{API_URL}/stats", headers=headers, timeout=10).json()
    print(f"✅ Success! Stats: {stats}")
except Exception as e:
    print(f"❌ Error: {e}")
