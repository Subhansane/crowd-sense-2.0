#!/usr/bin/env python3
"""
Firebase IMSI Uploader - Real-time cloud sync
"""

import firebase_admin
from firebase_admin import credentials, db
import os
import time
import re
from datetime import datetime
from pathlib import Path

# ==========================================
# CONFIGURATION
# ==========================================
# Your Firebase database URL (from your screenshot)
FIREBASE_URL = "https://imsi-crowd-data-default-rtdb.firebaseio.com/"
SOURCE_FILE = "imsi_output.txt"

# Initialize Firebase without credentials (using web API)
# For Python, we need the service account key
# Follow instructions below to get your key

print("="*60)
print("🔥 FIREBASE IMSI UPLOADER")
print("="*60)
print(f"📡 Monitoring: {SOURCE_FILE}")
print(f"☁️  Firebase URL: {FIREBASE_URL}")
print("="*60)

# Before running, you need to:
# 1. Go to Project Settings → Service Accounts
# 2. Click "Generate new private key"
# 3. Save the JSON file as "firebase-key.json" in this folder

# Check if service account key exists
if not os.path.exists("firebase-key.json"):
    print("\n❌ Missing firebase-key.json!")
    print("\n📋 To get the key:")
    print("1. Go to Firebase Console → Project Settings")
    print("2. Click 'Service Accounts' tab")
    print("3. Click 'Generate new private key'")
    print("4. Save the file as 'firebase-key.json' in this folder")
    print("\nThen run this script again.")
    exit(1)

# Initialize Firebase
cred = credentials.Certificate("firebase-key.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': FIREBASE_URL
})

print("✅ Firebase initialized!")

class FirebaseUploader:
    def __init__(self):
        self.last_position = 0
        self.upload_count = 0
        self.seen_ims = set()
        
        # Get reference to database
        self.ref = db.reference('/imsi_data')
        
    def parse_imsi_line(self, line):
        """Extract IMSI data from log line"""
        if not line or line.startswith('Nb IMSI') or line.startswith('stamp'):
            return None
        
        # Extract IMSI
        imsi_match = re.search(r'410\s+0[3467]\s+\d+', line)
        if not imsi_match:
            return None
        
        imsi_parts = imsi_match.group(0).split()
        mcc = imsi_parts[0]
        mnc = imsi_parts[1]
        imsi = imsi_parts[2]
        
        # Operator mapping
        operators = {
            '06': 'Telenor',
            '04': 'Zong',
            '03': 'Ufone',
            '01': 'Jazz',
            '07': 'Jazz'
        }
        operator = operators.get(mnc, 'Unknown')
        
        # Extract timestamp from line if available
        timestamp = datetime.now().isoformat()
        time_match = re.search(r'\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}', line)
        if time_match:
            timestamp = time_match.group(0).replace(' ', 'T')
        
        return {
            'imsi': f"{mcc}{mnc}{imsi}",
            'operator': operator,
            'mcc': mcc,
            'mnc': mnc,
            'timestamp': timestamp,
            'raw_line': line.strip()
        }
    
    def upload_to_firebase(self, data):
        """Upload IMSI data to Firebase"""
        try:
            # Use timestamp as key for real-time order
            key = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            
            # Create reference for this IMSI
            imsi_ref = self.ref.child(key)
            imsi_ref.set(data)
            
            # Update statistics
            stats_ref = db.reference('/stats')
            stats_ref.child('last_update').set(datetime.now().isoformat())
            stats_ref.child('total_uploads').transaction(lambda x: (x or 0) + 1)
            
            # Update operator counter
            op_counter_ref = db.reference(f'/stats/operators/{data["operator"]}')
            op_counter_ref.transaction(lambda x: (x or 0) + 1)
            
            # Track unique IMSIs
            if data['imsi'] not in self.seen_ims:
                self.seen_ims.add(data['imsi'])
                unique_ref = db.reference('/stats/unique_devices')
                unique_ref.set(len(self.seen_ims))
            
            return True
        except Exception as e:
            print(f"❌ Firebase error: {e}")
            return False
    
    def run(self):
        """Main loop"""
        print("\n👀 Monitoring for IMSI data...\n")
        
        if not os.path.exists(SOURCE_FILE):
            Path(SOURCE_FILE).touch()
        
        with open(SOURCE_FILE, 'r') as f:
            f.seek(0, 2)
            self.last_position = f.tell()
            
            while True:
                try:
                    line = f.readline()
                    if line:
                        data = self.parse_imsi_line(line)
                        if data:
                            if self.upload_to_firebase(data):
                                self.upload_count += 1
                                print(f"  🔥 [{self.upload_count}] {data['operator']}: ...{data['imsi'][-8:]}")
                    else:
                        time.sleep(1)
                        
                except KeyboardInterrupt:
                    print(f"\n\n👋 Stopped. Total uploads: {self.upload_count}")
                    break
                except Exception as e:
                    print(f"⚠️ Error: {e}")
                    time.sleep(5)

if __name__ == "__main__":
    uploader = FirebaseUploader()
    uploader.run()
