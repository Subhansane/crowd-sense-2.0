#!/usr/bin/env python3
"""
Test connection to InfinityFree MySQL
"""

import pymysql
import socket

# Your InfinityFree details
CLOUD_CONFIG = {
    'host': 'sql201.infinityfree.com',
    'port': 3306,
    'user': 'if0_41388991',
    'password': 'YOUR_PASSWORD',  # CHANGE THIS!
    'database': 'if0_41388991_imsi_data',
}

print("="*60)
print("🔌 Testing InfinityFree Connection")
print("="*60)

# Test DNS resolution
try:
    ip = socket.gethostbyname(CLOUD_CONFIG['host'])
    print(f"✅ DNS resolved: {CLOUD_CONFIG['host']} -> {ip}")
except Exception as e:
    print(f"❌ DNS resolution failed: {e}")

# Test MySQL connection
try:
    conn = pymysql.connect(
        host=CLOUD_CONFIG['host'],
        port=CLOUD_CONFIG['port'],
        user=CLOUD_CONFIG['user'],
        password=CLOUD_CONFIG['password'],
        database=CLOUD_CONFIG['database'],
        connect_timeout=10
    )
    print("✅ Successfully connected to MySQL!")
    
    # Test query
    with conn.cursor() as cursor:
        cursor.execute("SELECT VERSION()")
        version = cursor.fetchone()
        print(f"   MySQL Version: {version[0]}")
    
    conn.close()
    print("✅ Connection test passed!")
    
except pymysql.err.OperationalError as e:
    print(f"❌ Connection failed: {e}")
    print("\n🔧 Troubleshooting tips:")
    print("   1. Make sure password is correct")
    print("   2. Check if remote MySQL is allowed")
    print("   3. Try adding your IP to remote MySQL settings")
    print("   4. Visit: http://sql201.infinityfree.com/phpmyadmin to verify login")
except Exception as e:
    print(f"❌ Unexpected error: {e}")

print("="*60)
