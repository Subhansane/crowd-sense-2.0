#!/usr/bin/env python3
"""
Auto-upload IMSI data to InfinityFree via HTTP
No direct MySQL connection needed!
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
# CONFIGURATION
# ==========================================
UPLOAD_URL = "http://subhanscode.xo.je/imsi_upload.php"
API_TOKEN = "your-secret-token-123"  # Same as in PHP file
CACHE_FILE = "upload_cache.json"
MAX_CACHE_SIZE = 1000

class AutoUploader:
    def __init__(self):
        self.last_position = 0
        self.upload_count = 0
        self.cache = []
        self.running = True
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
            # Keep only last MAX_CACHE_SIZE
            self.cache = self.cache[-MAX_CACHE_SIZE:]
            with open(CACHE_FILE, 'w') as f:
                json.dump(self.cache, f)
        except:
            pass
    
    def parse_imsi_line(self, line):
        """Extract IMSI data from log line"""
        if not line or line.startswith('Nb IMSI') or line.startswith('stamp'):
            return None
        
        imsi_match = re.search(r'410\s+0[3467]\s+\d+', line)
        if not imsi_match:
            return None
        
        imsi = imsi_match.group(0)
        
        # Determine operator
        operator = "Unknown"
        if "410 06" in imsi:
            operator = "Telenor"
        elif "410 04" in imsi:
            operator = "Zong"
        elif "410 03" in imsi:
            operator = "Ufone"
        elif "410 01" in imsi or "410 07" in imsi:
            operator = "Jazz"
        
        # Extract timestamp
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        time_match = re.search(r'\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}', line)
        if time_match:
            timestamp = time_match.group(0).replace('T', ' ')
        
        # Extract LAC and Cell ID
        lac = None
        cell_id = None
        cell_match = re.search(r'(\d+)\s*;\s*(\d+)\s*$', line)
        if cell_match:
            lac = cell_match.group(1)
            cell_id = cell_match.group(2)
        
        return {
            'timestamp': timestamp,
            'imsi': imsi,
            'operator': operator,
            'mcc': '410',
            'cell_id': cell_id or 0,
            'lat': lac or 0,
            'source_ip': self.source_ip
        }
    
    def upload_to_website(self, data):
        """Send data to PHP endpoint"""
        try:
            response = requests.post(
                UPLOAD_URL,
                json=data,
                headers={
                    'X-API-Token': API_TOKEN,
                    'Content-Type': 'application/json'
                },
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get('success', False)
            return False
        except Exception as e:
            print(f"  ⚠️ Upload error: {e}")
            return False
    
    def process_cache(self):
        """Try to upload cached items"""
        if not self.cache:
            return
        
        print(f"\n📦 Processing {len(self.cache)} cached items...")
        success = []
        failed = []
        
        for item in self.cache:
            if self.upload_to_website(item):
                success.append(item)
                self.upload_count += 1
                print(f"  ✅ Uploaded cached: {item['operator']} - {item['imsi']}")
            else:
                failed.append(item)
            time.sleep(0.5)  # Rate limiting
        
        self.cache = failed
        self.save_cache()
        
        if success:
            print(f"✅ Successfully uploaded {len(success)} cached items")
        if failed:
            print(f"⏳ {len(failed)} items remain in cache")
    
    def run(self):
        """Main loop"""
        print("\n" + "="*70)
        print("🚀 INFINITYFREE AUTO-UPLOADER")
        print("="*70)
        print(f"📤 Uploading to: {UPLOAD_URL}")
        print(f"🔌 Source IP: {self.source_ip}")
        print(f"📦 Cache file: {CACHE_FILE}")
        print("="*70 + "\n")
        
        # Ensure file exists
        if not os.path.exists("imsi_output.txt"):
            Path("imsi_output.txt").touch()
            print("📁 Created imsi_output.txt")
        
        # Try to upload any cached data first
        self.process_cache()
        
        # Monitor file
        with open("imsi_output.txt", "r") as f:
            # Go to end of file
            f.seek(0, 2)
            self.last_position = f.tell()
            last_cache_retry = time.time()
            
            print("👀 Monitoring for new IMSI data...\n")
            
            while self.running:
                try:
                    line = f.readline()
                    if line:
                        data = self.parse_imsi_line(line)
                        if data:
                            # Try to upload
                            if self.upload_to_website(data):
                                self.upload_count += 1
                                print(f"  ✅ [{self.upload_count}] {data['operator']}: {data['imsi']}")
                            else:
                                # Cache for later
                                self.cache.append(data)
                                self.save_cache()
                                print(f"  📦 Cached: {data['operator']} (will retry)")
                    else:
                        time.sleep(1)
                    
                    # Retry cache every 5 minutes
                    if time.time() - last_cache_retry > 300:
                        if self.cache:
                            self.process_cache()
                        last_cache_retry = time.time()
                    
                    # Show stats every minute
                    if int(time.time()) % 60 == 0 and self.upload_count > 0:
                        print(f"\n📊 Stats: {self.upload_count} uploaded, {len(self.cache)} cached\n")
                        
                except KeyboardInterrupt:
                    break
                except Exception as e:
                    print(f"⚠️ Error: {e}")
                    time.sleep(5)

if __name__ == "__main__":
    uploader = AutoUploader()
    
    try:
        uploader.run()
    except KeyboardInterrupt:
        print("\n\n👋 Stopping uploader...")
        if uploader.cache:
            uploader.save_cache()
            print(f"📦 {len(uploader.cache)} items saved to cache for next time")
