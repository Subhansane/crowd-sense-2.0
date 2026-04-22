#!/usr/bin/env python3
"""
MySQL IMSI Logger using PyMySQL (more compatible)
"""

import pymysql
import os
import time
import re
import datetime
from pathlib import Path

class MySQLIMSILogger:
    def __init__(self, host="0.0.0.0", user="imsi_user", password="your_strong_password", database="imsi_crowd_sensing"):
        self.host = host
        self.user = user
        self.password = password
        self.database = database
        self.last_position = 0
        self.running = True
        
        # Connect to MySQL using PyMySQL
        self.connect_db()
        
        # Get your IP address for friend
        self.get_ip_address()
        
    def connect_db(self):
        """Connect to MySQL database using PyMySQL"""
        try:
            self.conn = pymysql.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database,
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor
            )
            self.cursor = self.conn.cursor()
            print(f"✅ Connected to MySQL database: {self.database}")
        except Exception as e:
            print(f"❌ MySQL connection error: {e}")
            print("\n💡 Troubleshooting tips:")
            print("   1. Make sure MySQL is running: sudo systemctl status mysql")
            print("   2. Check credentials in the script")
            print("   3. Verify database exists: mysql -u root -p -e 'SHOW DATABASES;'")
            exit(1)
    
    def get_ip_address(self):
        """Get your IP address for friend to connect"""
        try:
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            print(f"\n📡 Your IP address: {ip}")
            print(f"🔗 Tell your friend to connect to: mysql -u {self.user} -p -h {ip} {self.database}")
            print(f"📊 Database: {self.database}, User: {self.user}\n")
        except:
            print("Run 'hostname -I' to see your IP address")
    
    def parse_imsi_line(self, line):
        """Extract IMSI data from log line"""
        # Look for IMSI pattern
        imsi_match = re.search(r'410 0[3467] \d+', line)
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
        
        # Extract MNC
        mnc = imsi.split()[1] if len(imsi.split()) > 1 else "00"
        
        # Extract timestamp
        timestamp = datetime.datetime.now()
        time_match = re.search(r'\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}', line)
        if time_match:
            try:
                timestamp = datetime.datetime.fromisoformat(time_match.group(0).replace(' ', 'T'))
            except:
                pass
        
        # Extract cell ID and LAC if present
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
            'lac': lac
        }
    
    def insert_to_mysql(self, data):
        """Insert IMSI data into MySQL using PyMySQL"""
        try:
            sql = """
                INSERT INTO imsi_captures 
                (timestamp, imsi, operator, mcc, mnc, cell_id, lac)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            self.cursor.execute(sql, (
                data['timestamp'],
                data['imsi'],
                data['operator'],
                data['mcc'],
                data['mnc'],
                data['cell_id'],
                data['lac']
            ))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"MySQL insert error: {e}")
            return False
    
    def run(self):
        """Main loop - monitor imsi_output.txt and insert to MySQL"""
        if not os.path.exists("imsi_output.txt"):
            Path("imsi_output.txt").touch()
        
        print("👀 Monitoring imsi_output.txt for new IMSI data...")
        print("📤 Sending to MySQL database in real-time\n")
        
        insert_count = 0
        
        with open("imsi_output.txt", "r") as f:
            # Go to end of file
            f.seek(0, 2)
            self.last_position = f.tell()
            
            while self.running:
                line = f.readline()
                if line:
                    data = self.parse_imsi_line(line)
                    if data:
                        if self.insert_to_mysql(data):
                            insert_count += 1
                            print(f"  ➕ Inserted: {data['operator']} - {data['imsi']} (Total: {insert_count})")
                else:
                    time.sleep(0.5)
                
                # Small status update every minute
                if int(time.time()) % 60 == 0:
                    print(f"\n📊 Status: {insert_count} IMSIs inserted so far\n")

if __name__ == "__main__":
    print("="*60)
    print("📡 MySQL IMSI Logger (PyMySQL Edition)")
    print("="*60)
    
    # You can change these credentials
    logger = MySQLIMSILogger(
        host="0.0.0.0",  # Listen on all interfaces
        user="imsi_user",
        password="your_strong_password",  # CHANGE THIS!
        database="imsi_crowd_sensing"
    )
    
    try:
        logger.run()
    except KeyboardInterrupt:
        print("\n\n👋 Stopping MySQL Logger")
        if hasattr(logger, 'conn'):
            logger.conn.close()
