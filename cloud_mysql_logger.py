#!/usr/bin/env python3
"""
Cloud MySQL IMSI Logger
Automatically uploads to cloud database - accessible 24/7
"""

import pymysql
import os
import time
import re
import datetime
from pathlib import Path
import socket

# ==========================================
# CLOUD DATABASE CONFIGURATION
# Replace these with your cloud MySQL details
# ==========================================
CLOUD_CONFIG = {
    'host': 'us-east-1.railway.app',  # Your cloud host
    'port': 3306,                       # Your cloud port
    'user': 'avnadmin',                  # Your cloud username
    'password': 'your_cloud_password',   # Your cloud password
    'database': 'imsi_data',              # Your cloud database name
    'ssl': {'ssl': {'ca': '/etc/ssl/certs/ca-certificates.crt'}}  # For SSL connections
}

class CloudMySQLIMSIUploader:
    def __init__(self, config=CLOUD_CONFIG):
        self.config = config
        self.last_position = 0
        self.running = True
        self.upload_count = 0
        self.error_count = 0
        self.last_upload_time = time.time()
        
        # Local cache for offline periods
        self.cache_file = Path("imsi_upload_cache.json")
        self.cache = self.load_cache()
        
        # Test connection
        self.test_connection()
        
    def load_cache(self):
        """Load cached IMSIs for offline periods"""
        import json
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r') as f:
                    return json.load(f)
            except:
                return []
        return []
    
    def save_cache(self):
        """Save IMSIs to cache when offline"""
        import json
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(self.cache, f)
        except:
            pass
    
    def test_connection(self):
        """Test cloud database connection"""
        try:
            conn = pymysql.connect(
                host=self.config['host'],
                port=self.config['port'],
                user=self.config['user'],
                password=self.config['password'],
                database=self.config['database'],
                connect_timeout=10
            )
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")
            conn.close()
            print(f"✅ Connected to cloud database at {self.config['host']}")
            print(f"📊 Database: {self.config['database']}")
            return True
        except Exception as e:
            print(f"⚠️  Cannot connect to cloud: {e}")
            print("📁 Will cache data locally and upload when online")
            return False
    
    def ensure_table_exists(self, conn):
        """Create table if it doesn't exist"""
        with conn.cursor() as cursor:
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
                    INDEX idx_operator (operator),
                    INDEX idx_imsi (imsi)
                )
            """)
            conn.commit()
    
    def get_source_ip(self):
        """Get your public IP for identification"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "unknown"
    
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
        
        mnc = imsi.split()[1] if len(imsi.split()) > 1 else "00"
        
        # Extract timestamp
        timestamp = datetime.datetime.now()
        time_match = re.search(r'\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}', line)
        if time_match:
            try:
                timestamp = datetime.datetime.fromisoformat(time_match.group(0).replace(' ', 'T'))
            except:
                pass
        
        # Extract cell ID and LAC
        cell_id = None
        lac = None
        cell_match = re.search(r'(\d+)\s*;\s*(\d+)\s*$', line)
        if cell_match:
            lac = cell_match.group(1)
            cell_id = cell_match.group(2)
        
        return {
            'timestamp': timestamp,
            'imsi': imsi,
            'operator': operator,
            'mcc': '410',
            'mnc': mnc,
            'cell_id': cell_id,
            'lac': lac,
            'source_ip': self.get_source_ip()
        }
    
    def upload_to_cloud(self, data):
        """Upload single IMSI to cloud database"""
        try:
            conn = pymysql.connect(
                host=self.config['host'],
                port=self.config['port'],
                user=self.config['user'],
                password=self.config['password'],
                database=self.config['database'],
                connect_timeout=10
            )
            
            self.ensure_table_exists(conn)
            
            with conn.cursor() as cursor:
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
                conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"⚠️  Upload failed: {e}")
            return False
    
    def process_cache(self):
        """Try to upload cached data"""
        if not self.cache:
            return
        
        print(f"📦 Processing {len(self.cache)} cached items...")
        success = []
        failed = []
        
        for item in self.cache:
            if self.upload_to_cloud(item):
                success.append(item)
            else:
                failed.append(item)
            time.sleep(0.1)  # Rate limiting
        
        # Update cache
        self.cache = failed
        self.save_cache()
        
        if success:
            print(f"✅ Uploaded {len(success)} cached items")
        if failed:
            print(f"⏳ {len(failed)} items remain in cache")
    
    def run(self):
        """Main loop - monitor and upload to cloud"""
        if not os.path.exists("imsi_output.txt"):
            Path("imsi_output.txt").touch()
        
        # Try to upload any cached data first
        self.process_cache()
        
        print("\n👀 Monitoring for new IMSI data...")
        print("☁️  Auto-uploading to cloud database")
        print("🔗 Your friends can access anytime at:")
        print(f"   Host: {self.config['host']}")
        print(f"   Port: {self.config['port']}")
        print(f"   Database: {self.config['database']}")
        print(f"   User: {self.config['user']}")
        print("\n📁 Data is cached locally if cloud is unreachable\n")
        
        with open("imsi_output.txt", "r") as f:
            f.seek(0, 2)
            self.last_position = f.tell()
            
            while self.running:
                try:
                    line = f.readline()
                    if line:
                        data = self.parse_imsi_line(line)
                        if data:
                            # Try cloud upload
                            if self.upload_to_cloud(data):
                                self.upload_count += 1
                                print(f"  ☁️ [{self.upload_count}] {data['operator']}: {data['imsi']}")
                            else:
                                # Cache for later
                                self.cache.append(data)
                                self.save_cache()
                                print(f"  📦 Cached {data['operator']}: {data['imsi']} (cloud offline)")
                    else:
                        time.sleep(0.5)
                    
                    # Periodically try to upload cache
                    if time.time() - self.last_upload_time > 60:  # Every minute
                        if self.cache:
                            self.process_cache()
                        self.last_upload_time = time.time()
                        
                except KeyboardInterrupt:
                    break
                except Exception as e:
                    self.error_count += 1
                    if self.error_count < 5:
                        print(f"⚠️  Error: {e}")
                    time.sleep(1)

if __name__ == "__main__":
    print("="*70)
    print("☁️  CLOUD MySQL IMSI UPLOADER")
    print("="*70)
    print("✅ Auto-uploads to cloud database")
    print("✅ Friends can access 24/7")
    print("✅ Offline caching included")
    print("="*70)
    
    uploader = CloudMySQLIMSIUploader()
    
    try:
        uploader.run()
    except KeyboardInterrupt:
        print("\n\n👋 Stopping Cloud Uploader")
        if uploader.cache:
            uploader.save_cache()
            print(f"📦 {len(uploader.cache)} items cached for next time")
