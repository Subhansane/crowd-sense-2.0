#!/usr/bin/env python3
"""
Ultimate IMSI Drive Manager
- Continuously uploads new IMSI data
- Maintains clean unique IMSI files
- Updates statistics in real-time
"""

import os
import time
import re
import json
from datetime import datetime
from collections import defaultdict
import threading

# ==========================================
# CONFIGURATION
# ==========================================
SOURCE_FILE = "imsi_output.txt"
GDRIVE_FOLDER = "google:IMSI_Data"
LOCAL_CACHE = "/tmp/imsi_cache"
CHECK_INTERVAL = 10  # seconds
CLEANUP_INTERVAL = 300  # 5 minutes

class IMSIDriveManager:
    def __init__(self):
        self.unique_ims = {}  # IMSI -> latest data
        self.recent_uploads = []
        self.stats = {
            'total_uploads': 0,
            'unique_devices': 0,
            'last_cleanup': None,
            'operator_counts': defaultdict(int)
        }
        
        # Create directories
        os.makedirs(LOCAL_CACHE, exist_ok=True)
        
        print("="*70)
        print("🚀 ULTIMATE IMSI DRIVE MANAGER")
        print("="*70)
        print(f"📁 Watching: {SOURCE_FILE}")
        print(f"☁️  Uploading to: {GDRIVE_FOLDER}")
        print(f"⏱️  Upload interval: {CHECK_INTERVAL}s")
        print(f"🧹 Cleanup interval: {CLEANUP_INTERVAL}s")
        print("="*70)
        
        # Create Drive folder
        os.system(f"rclone mkdir {GDRIVE_FOLDER}")
        
        # Load existing unique IMSIs if any
        self.load_existing_data()
    
    def load_existing_data(self):
        """Load previously saved unique IMSIs"""
        try:
            os.system(f"rclone copy {GDRIVE_FOLDER}/unique_imsi.json {LOCAL_CACHE}/ 2>/dev/null")
            if os.path.exists(f"{LOCAL_CACHE}/unique_imsi.json"):
                with open(f"{LOCAL_CACHE}/unique_imsi.json", 'r') as f:
                    data = json.load(f)
                    self.unique_ims = data.get('ims', {})
                    self.stats['unique_devices'] = len(self.unique_ims)
                    print(f"✅ Loaded {len(self.unique_ims)} existing unique IMSIs")
        except:
            pass
    
    def extract_imsi_data(self, line):
        """Extract IMSI and metadata from line"""
        # Look for IMSI pattern
        imsi_match = re.search(r'410\s+0[3467]\s+\d+', line)
        if not imsi_match:
            return None
        
        parts = imsi_match.group(0).split()
        imsi_full = f"{parts[0]}{parts[1]}{parts[2]}"
        
        # Get timestamp
        timestamp = datetime.now().isoformat()
        time_match = re.search(r'\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}', line)
        if time_match:
            timestamp = time_match.group(0).replace(' ', 'T')
        
        # Determine operator
        mnc = parts[1]
        operator = {
            '06': 'Telenor',
            '04': 'Zong',
            '03': 'Ufone',
            '01': 'Jazz',
            '07': 'Jazz'
        }.get(mnc, 'Unknown')
        
        return {
            'imsi': imsi_full,
            'display': imsi_match.group(0),
            'operator': operator,
            'timestamp': timestamp,
            'mnc': mnc,
            'raw_line': line.strip()
        }
    
    def update_unique_ims(self, data):
        """Update unique IMSI database"""
        imsi = data['imsi']
        
        if imsi not in self.unique_ims:
            # New IMSI
            self.unique_ims[imsi] = {
                'first_seen': data['timestamp'],
                'last_seen': data['timestamp'],
                'operator': data['operator'],
                'count': 1,
                'mnc': data['mnc']
            }
            self.stats['operator_counts'][data['operator']] += 1
            self.stats['unique_devices'] = len(self.unique_ims)
            return True  # New device
        else:
            # Update existing
            self.unique_ims[imsi]['last_seen'] = data['timestamp']
            self.unique_ims[imsi]['count'] += 1
            return False  # Duplicate
    
    def upload_realtime(self, data):
        """Upload new data immediately"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save to temp file
        temp_file = f"{LOCAL_CACHE}/latest.txt"
        with open(temp_file, 'a') as f:
            f.write(data['raw_line'] + '\n')
        
        # Upload as new file
        filename = f"imsi_{timestamp}.txt"
        with open(f"{LOCAL_CACHE}/{filename}", 'w') as f:
            f.write(data['raw_line'])
        
        os.system(f"rclone copy {LOCAL_CACHE}/{filename} {GDRIVE_FOLDER}/realtime/")
        os.system(f"rclone copy {LOCAL_CACHE}/latest.txt {GDRIVE_FOLDER}/latest.txt")
        
        self.stats['total_uploads'] += 1
        print(f"  ☁️ [{self.stats['total_uploads']}] {data['operator']}: ...{data['imsi'][-8:]}")
        
        # Cleanup
        os.remove(f"{LOCAL_CACHE}/{filename}")
    
    def generate_clean_files(self):
        """Generate clean unique IMSI files"""
        print("\n🧹 Generating clean unique files...")
        
        # Group by operator
        operator_files = defaultdict(list)
        
        for imsi, info in self.unique_ims.items():
            operator_files[info['operator']].append((imsi, info))
        
        # Create master file
        master_file = f"{LOCAL_CACHE}/MASTER_unique.txt"
        with open(master_file, 'w') as f:
            f.write(f"# UNIQUE IMSIs - Generated {datetime.now()}\n")
            f.write(f"# Total Devices: {len(self.unique_ims)}\n")
            f.write("#" + "="*60 + "\n\n")
            
            for imsi, info in sorted(self.unique_ims.items()):
                f.write(f"{imsi} | {info['operator']} | "
                       f"First: {info['first_seen']} | "
                       f"Last: {info['last_seen']} | "
                       f"Count: {info['count']}\n")
        
        # Create operator files
        for operator, devices in operator_files.items():
            op_file = f"{LOCAL_CACHE}/{operator}_unique.txt"
            with open(op_file, 'w') as f:
                f.write(f"# {operator} UNIQUE DEVICES - {len(devices)} phones\n")
                f.write("#" + "="*50 + "\n")
                for imsi, info in sorted(devices):
                    f.write(f"{imsi} | Last seen: {info['last_seen']} | Count: {info['count']}\n")
        
        # Create statistics
        stats_file = f"{LOCAL_CACHE}/STATS.txt"
        with open(stats_file, 'w') as f:
            f.write("="*60 + "\n")
            f.write("IMSI DRIVE MANAGER STATISTICS\n")
            f.write("="*60 + "\n")
            f.write(f"Generated: {datetime.now()}\n\n")
            f.write(f"Total Unique Devices: {len(self.unique_ims)}\n")
            f.write(f"Total Uploads: {self.stats['total_uploads']}\n\n")
            f.write("By Operator:\n")
            for op, count in self.stats['operator_counts'].items():
                f.write(f"  {op}: {count} devices\n")
        
        # Upload all clean files
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        clean_folder = f"{GDRIVE_FOLDER}/cleaned_{timestamp}"
        os.system(f"rclone mkdir {clean_folder}")
        
        files_to_upload = [
            "MASTER_unique.txt",
            "STATS.txt",
            "Telenor_unique.txt",
            "Zong_unique.txt",
            "Ufone_unique.txt",
            "Jazz_unique.txt"
        ]
        
        for filename in files_to_upload:
            filepath = f"{LOCAL_CACHE}/{filename}"
            if os.path.exists(filepath):
                os.system(f"rclone copy {filepath} {clean_folder}/")
                print(f"  ✅ Uploaded: {filename}")
        
        # Also save unique IMSI database for next run
        with open(f"{LOCAL_CACHE}/unique_imsi.json", 'w') as f:
            json.dump({
                'ims': self.unique_ims,
                'stats': dict(self.stats)
            }, f)
        os.system(f"rclone copy {LOCAL_CACHE}/unique_imsi.json {GDRIVE_FOLDER}/")
        
        print(f"✅ Clean files uploaded to: {clean_folder}")
        self.stats['last_cleanup'] = datetime.now().isoformat()
    
    def monitor_and_upload(self):
        """Main monitoring loop"""
        print("\n👀 Monitoring for new IMSIs... (Press Ctrl+C to stop)\n")
        
        last_position = 0
        last_cleanup = time.time()
        
        while True:
            try:
                if os.path.exists(SOURCE_FILE):
                    with open(SOURCE_FILE, 'r') as f:
                        f.seek(last_position)
                        new_lines = f.readlines()
                        last_position = f.tell()
                        
                        for line in new_lines:
                            data = self.extract_imsi_data(line)
                            if data:
                                # Update unique database
                                is_new = self.update_unique_ims(data)
                                
                                # Always upload real-time
                                self.upload_realtime(data)
                                
                                if is_new:
                                    print(f"     ✨ NEW DEVICE! Total unique: {self.stats['unique_devices']}")
                
                # Periodic cleanup
                if time.time() - last_cleanup > CLEANUP_INTERVAL:
                    self.generate_clean_files()
                    last_cleanup = time.time()
                
                time.sleep(CHECK_INTERVAL)
                
            except KeyboardInterrupt:
                print("\n\n🛑 Stopping...")
                # Final cleanup
                self.generate_clean_files()
                break
            except Exception as e:
                print(f"⚠️ Error: {e}")
                time.sleep(30)
    
    def run(self):
        """Start the manager"""
        try:
            self.monitor_and_upload()
        except KeyboardInterrupt:
            print("\n\n👋 Drive Manager Stopped")
            print(f"📊 Final Statistics:")
            print(f"   Unique Devices: {self.stats['unique_devices']}")
            print(f"   Total Uploads: {self.stats['total_uploads']}")
            for op, count in self.stats['operator_counts'].items():
                print(f"   {op}: {count}")

if __name__ == "__main__":
    manager = IMSIDriveManager()
    manager.run()
