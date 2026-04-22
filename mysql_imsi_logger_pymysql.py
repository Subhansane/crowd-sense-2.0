#!/usr/bin/env python3
"""
MySQL IMSI Logger using PyMySQL
Works with Python 3.12+ - No SSL issues!
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
                charset='utf8mb4'
            )
            self.cursor = self.conn.cursor()
            print(f"✅ Connected to MySQL database: {self.database}")
            
            # Test the connection
            self.cursor.execute("SELECT 1")
            print("✅ Database connection test passed")
            
        except Exception as e:
            print(f"❌ MySQL connection error: {e}")
            print("\n💡 Troubleshooting tips:")
            print("   1. Make sure MySQL is running: sudo systemctl status mysql")
            print("   2. Check if database exists: mysql -u root -p -e 'SHOW DATABASES;'")
            print("   3. Verify user permissions: mysql -u root -p -e \"SHOW GRANTS FOR 'imsi_user'@'%';\"")
            print("   4. Check if table exists: mysql -u imsi_user -p -e 'USE imsi_crowd_sensing; SHOW TABLES;'")
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
            print("\n📡 Run this command to see your IP:")
            print("   hostname -I | awk '{print $1}'")
    
    def parse_imsi_line(self, line):
        """Extract IMSI data from log line"""
        # Skip header lines
        if not line or line.startswith('Nb IMSI') or line.startswith('stamp'):
            return None
            
        # Look for IMSI pattern (410 06, 410 04, 410 03, 410 01/07)
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
        
        # Extract cell ID and LAC if present (from the end of line)
        cell_id = None
        lac = None
        # Look for numbers at the end like "359 ; 12911" or "58803 ; 18176"
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
        except pymysql.Error as e:
            print(f"❌ MySQL insert error: {e}")
            # Check if table exists
            if "doesn't exist" in str(e):
                print("💡 The table doesn't exist. Creating it now...")
                self.create_table()
            return False
    
    def create_table(self):
        """Create the imsi_captures table if it doesn't exist"""
        try:
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS imsi_captures (
                id INT AUTO_INCREMENT PRIMARY KEY,
                timestamp DATETIME,
                imsi VARCHAR(20),
                operator VARCHAR(20),
                mcc VARCHAR(3),
                mnc VARCHAR(3),
                cell_id INT,
                lac INT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_timestamp (timestamp),
                INDEX idx_operator (operator)
            )
            """
            self.cursor.execute(create_table_sql)
            self.conn.commit()
            print("✅ Table 'imsi_captures' created successfully")
            return True
        except Exception as e:
            print(f"❌ Failed to create table: {e}")
            return False
    
    def run(self):
        """Main loop - monitor imsi_output.txt and insert to MySQL"""
        if not os.path.exists("imsi_output.txt"):
            Path("imsi_output.txt").touch()
            print("📁 Created empty imsi_output.txt")
        
        # Ensure table exists
        self.create_table()
        
        print("\n👀 Monitoring imsi_output.txt for new IMSI data...")
        print("📤 Sending to MySQL database in real-time\n")
        
        insert_count = 0
        error_count = 0
        
        with open("imsi_output.txt", "r") as f:
            # Go to end of file
            f.seek(0, 2)
            self.last_position = f.tell()
            print(f"📊 Starting from position: {self.last_position} bytes")
            
            while self.running:
                try:
                    line = f.readline()
                    if line:
                        data = self.parse_imsi_line(line)
                        if data:
                            if self.insert_to_mysql(data):
                                insert_count += 1
                                print(f"  ➕ [{insert_count}] {data['operator']}: {data['imsi']}")
                    else:
                        time.sleep(0.5)
                    
                    # Status update every 30 seconds
                    if int(time.time()) % 30 == 0 and insert_count > 0:
                        print(f"\n📊 Status: {insert_count} IMSIs inserted so far\n")
                        
                except KeyboardInterrupt:
                    break
                except Exception as e:
                    error_count += 1
                    if error_count < 5:  # Only show first few errors
                        print(f"⚠️  Error: {e}")
                    time.sleep(1)

if __name__ == "__main__":
    print("="*60)
    print("📡 MySQL IMSI Logger (PyMySQL Edition)")
    print("="*60)
    print("✅ Compatible with Python 3.12+")
    print("="*60)
    
    # CHANGE THESE CREDENTIALS!
    DB_USER = "imsi_user"
    DB_PASSWORD = "project"  # <-- CHANGE THIS!
    DB_NAME = "imsi_crowd_sensing"
    
    print(f"\n🔧 Current settings:")
    print(f"   Database: {DB_NAME}")
    print(f"   User: {DB_USER}")
    print(f"   Password: {DB_PASSWORD}")
    print(f"\n⚠️  Make sure to update the password in the script!")
    
    logger = MySQLIMSILogger(
        host="0.0.0.0",
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )
    
    try:
        logger.run()
    except KeyboardInterrupt:
        print("\n\n👋 Stopping MySQL Logger")
        if hasattr(logger, 'conn'):
            logger.conn.close()
            print("✅ Database connection closed")

