#!/usr/bin/env python3
"""
HTTP Uploader for InfinityFree
Sends data to your website's PHP API
"""

import requests
import sqlite3
import json
import time
from datetime import datetime
import os
import re

# Your website URL
API_URL = "http://subhanscode.xo.je/imsi_api.php"

class HTTPUploader:
    def __init__(self):
        self.last_id = 0
        self.running = True
        
    def get_new_data(self):
        """Get new data from SQLite database"""
        conn = sqlite3.connect('crowd_sense_data.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM detection_events 
            WHERE id > ? 
            ORDER BY id ASC
        """, (self.last_id,))
        
        rows = cursor.fetchall()
        if rows:
            self.last_id = rows[-1]['id']
        
        conn.close()
        return [dict(row) for row in rows]
    
    def send_to_cloud(self, data):
        """Send data to PHP API"""
        try:
            response = requests.post(
                f"{API_URL}?action=insert",
                json={
                    'timestamp': data['timestamp'],
                    'imsi': data['imsi'],
                    'operator': 'Telenor',  # You'll need to map this
                    'mcc': '410',
                    'mnc': '06',
                    'cell_id': 0,
                    'lac': 0,
                    'source_ip': 'ubuntu'
                },
                timeout=10
            )
            return response.status_code == 200
        except:
            return False
    
    def run(self):
        print("="*60)
        print("🌐 InfinityFree HTTP Uploader")
        print("="*60)
        print(f"📤 Uploading to: {API_URL}")
        print("👀 Monitoring for new data...")
        print("="*60)
        
        while self.running:
            try:
                new_data = self.get_new_data()
                for data in new_data:
                    if self.send_to_cloud(data):
                        print(f"✅ Uploaded: {data['imsi']}")
                    else:
                        print(f"❌ Failed: {data['imsi']}")
                
                time.sleep(5)
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Error: {e}")
                time.sleep(10)

if __name__ == "__main__":
    uploader = HTTPUploader()
    uploader.run()
